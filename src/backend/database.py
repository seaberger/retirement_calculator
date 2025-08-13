"""
Database configuration and models for the retirement calculator.
"""

from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, Session

# Create data directory path relative to project root
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "retire.db"

# SQLite engine configuration
engine = create_engine(
    f"sqlite:///{DB_PATH}", 
    connect_args={"check_same_thread": False}
)

# Base class for SQLAlchemy models
Base = declarative_base()


class ScenarioRow(Base):
    """Database model for storing saved scenarios"""
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False)
    payload = Column(Text, nullable=False)  # JSON string of Scenario


# Create tables if they don't exist
Base.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session"""
    return Session(engine)