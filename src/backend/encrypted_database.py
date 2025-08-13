"""
Encrypted database layer for sensitive financial data.
Uses Fernet symmetric encryption from cryptography library.
"""

import os
import json
import base64
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EncryptionManager:
    """Manages encryption/decryption of sensitive data."""
    
    def __init__(self, key: Optional[str] = None):
        """Initialize with encryption key from environment or parameter."""
        if key:
            self.key = key
        else:
            # Get from environment or generate warning key
            env_key = os.getenv('DB_ENCRYPTION_KEY')
            if not env_key:
                print("WARNING: No DB_ENCRYPTION_KEY found in environment. Using default key (NOT SECURE!)")
                env_key = "default-development-key-change-this"
            
            # Derive a proper encryption key from the password
            self.key = self._derive_key(env_key)
        
        self.fernet = Fernet(self.key)
        self.enabled = os.getenv('DB_ENCRYPTION_ENABLED', 'true').lower() == 'true'
    
    def _derive_key(self, password: str) -> bytes:
        """Derive a Fernet-compatible key from a password."""
        # Use PBKDF2 to derive a key from the password
        salt = b'retirement-calc-salt-v1'  # In production, use a random salt per user
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64-encoded encrypted data."""
        if not self.enabled:
            return data
        
        if data is None:
            return None
            
        encrypted = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64-encoded encrypted data and return original string."""
        if not self.enabled:
            return encrypted_data
        
        if encrypted_data is None:
            return None
            
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            # If decryption fails, might be unencrypted data from migration
            print(f"Decryption failed, returning as-is: {e}")
            return encrypted_data
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary by converting to JSON first."""
        if not self.enabled:
            return json.dumps(data)
        
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt and return as dictionary."""
        if not self.enabled:
            return json.loads(encrypted_data)
        
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)


class EncryptedScenarioRow:
    """Wrapper for ScenarioRow with automatic encryption/decryption."""
    
    def __init__(self, scenario_row, encryption_manager: EncryptionManager):
        self.row = scenario_row
        self.enc = encryption_manager
    
    @property
    def name(self):
        """Name is not encrypted for searching."""
        return self.row.name
    
    @property
    def payload(self):
        """Decrypt payload on access."""
        return self.enc.decrypt(self.row.payload)
    
    @payload.setter
    def payload(self, value: str):
        """Encrypt payload on setting."""
        self.row.payload = self.enc.encrypt(value)
    
    def to_dict(self):
        """Return decrypted dictionary representation."""
        return {
            'id': self.row.id,
            'name': self.row.name,
            'payload': self.payload  # This will be decrypted
        }


# Global encryption manager instance
_encryption_manager = None

def get_encryption_manager() -> EncryptionManager:
    """Get or create the global encryption manager."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def generate_new_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode('utf-8')


def test_encryption():
    """Test that encryption is working correctly."""
    manager = get_encryption_manager()
    
    # Test string encryption
    original = "Sensitive financial data: $1,500,000"
    encrypted = manager.encrypt(original)
    decrypted = manager.decrypt(encrypted)
    
    assert original == decrypted, "String encryption/decryption failed"
    assert encrypted != original if manager.enabled else encrypted == original
    
    # Test dictionary encryption
    original_dict = {
        "balance": 1500000,
        "accounts": ["401k", "IRA"],
        "sensitive": True
    }
    encrypted_dict = manager.encrypt_dict(original_dict)
    decrypted_dict = manager.decrypt_dict(encrypted_dict)
    
    assert original_dict == decrypted_dict, "Dict encryption/decryption failed"
    
    print("✅ Encryption tests passed!")
    if manager.enabled:
        print(f"   Original: {original[:20]}...")
        print(f"   Encrypted: {encrypted[:20]}...")
    else:
        print("   ⚠️  Encryption is DISABLED (DB_ENCRYPTION_ENABLED=false)")
    
    return True


if __name__ == "__main__":
    # Run tests when module is executed directly
    test_encryption()
    
    # Show how to generate a new key
    print(f"\nTo generate a new encryption key:")
    print(f"  python -c 'from encrypted_database import generate_new_key; print(generate_new_key())'")
    print(f"\nAdd this to your .env file:")
    print(f"  DB_ENCRYPTION_KEY=<your-generated-key>")