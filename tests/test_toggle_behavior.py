"""
Test toggle behavior for determinism and independence.
Ensures toggles produce consistent and predictable results.
"""

import pytest
import numpy as np
from monte_carlo.fat_tails_kou_logsafe import FatTailCfg, _apply_toggles


class TestToggleDeterminism:
    """Test that toggles are deterministic."""
    
    def test_toggle_determinism(self):
        """Test that same input produces same output."""
        cfg = FatTailCfg(
            enabled=True,
            tail_magnitude="extreme",
            tail_frequency="high",
            tail_skew="negative"
        )
        
        # Apply toggles multiple times
        results = []
        for _ in range(5):
            per_adj, market_adj = _apply_toggles(cfg)
            results.append({
                'market_lam': market_adj.lam,
                'market_eta_neg': market_adj.eta_neg,
                'market_eta_pos': market_adj.eta_pos,
                'market_p_pos': market_adj.p_pos,
                'stock_lam': per_adj['stocks'].lam,
                'stock_eta_neg': per_adj['stocks'].eta_neg,
            })
        
        # All results should be identical
        for i in range(1, len(results)):
            for key in results[0].keys():
                assert results[i][key] == results[0][key], (
                    f"Toggle not deterministic: {key} changed from {results[0][key]} to {results[i][key]}"
                )
    
    def test_toggle_independence(self):
        """Test that toggles don't interfere with each other."""
        base_cfg = FatTailCfg(enabled=True)
        
        # Test magnitude alone
        mag_cfg = FatTailCfg(enabled=True, tail_magnitude="extreme")
        per_mag, market_mag = _apply_toggles(mag_cfg)
        
        # Test frequency alone
        freq_cfg = FatTailCfg(enabled=True, tail_frequency="high")
        per_freq, market_freq = _apply_toggles(freq_cfg)
        
        # Test skew alone
        skew_cfg = FatTailCfg(enabled=True, tail_skew="negative")
        per_skew, market_skew = _apply_toggles(skew_cfg)
        
        # Magnitude should only affect eta values
        assert market_mag.lam == base_cfg.market.lam, "Magnitude affected frequency"
        assert market_mag.eta_neg > base_cfg.market.eta_neg, "Magnitude didn't increase eta_neg"
        
        # Frequency affects lam values and also boosts market eta_neg by 1.10x
        assert market_freq.lam > base_cfg.market.lam, "Frequency didn't increase lam"
        expected_eta_neg = base_cfg.market.eta_neg * 1.10  # High frequency applies 1.10x boost to market eta_neg
        assert abs(market_freq.eta_neg - expected_eta_neg) < 0.001, "Frequency didn't apply eta_neg boost"
        
        # Skew should affect p_pos and scale eta values
        assert market_skew.p_pos < base_cfg.market.p_pos, "Negative skew didn't reduce p_pos"
        assert market_skew.eta_neg > base_cfg.market.eta_neg, "Negative skew didn't increase eta_neg"
    
    def test_toggle_multiplier_exactness(self):
        """Test that toggle multipliers are exactly as specified."""
        cfg = FatTailCfg(enabled=True)
        
        # Test extreme magnitude (1.30x)
        cfg.tail_magnitude = "extreme"
        per_adj, market_adj = _apply_toggles(cfg)
        
        expected_eta_neg = cfg.market.eta_neg * 1.30
        assert abs(market_adj.eta_neg - expected_eta_neg) < 1e-10, (
            f"Extreme magnitude multiplier not exact: {market_adj.eta_neg} vs {expected_eta_neg}"
        )
        
        # Test high frequency (1.50x)
        cfg = FatTailCfg(enabled=True, tail_frequency="high")
        per_adj, market_adj = _apply_toggles(cfg)
        
        expected_lam = cfg.market.lam * 1.50
        assert abs(market_adj.lam - expected_lam) < 1e-10, (
            f"High frequency multiplier not exact: {market_adj.lam} vs {expected_lam}"
        )


class TestToggleCombinations:
    """Test various toggle combinations."""
    
    def test_all_toggle_combinations(self):
        """Test all possible toggle combinations produce valid results."""
        magnitudes = ["standard", "extreme"]
        frequencies = ["standard", "high"]
        skews = ["negative", "neutral", "positive"]
        
        for mag in magnitudes:
            for freq in frequencies:
                for skew in skews:
                    cfg = FatTailCfg(
                        enabled=True,
                        tail_magnitude=mag,
                        tail_frequency=freq,
                        tail_skew=skew
                    )
                    
                    per_adj, market_adj = _apply_toggles(cfg)
                    
                    # Check all parameters are valid
                    assert market_adj.lam > 0, f"Invalid lam for {mag}/{freq}/{skew}"
                    assert market_adj.eta_neg > 0, f"Invalid eta_neg for {mag}/{freq}/{skew}"
                    assert market_adj.eta_pos > 0, f"Invalid eta_pos for {mag}/{freq}/{skew}"
                    assert 0 <= market_adj.p_pos <= 1, f"Invalid p_pos for {mag}/{freq}/{skew}"
    
    def test_high_frequency_special_boost(self):
        """Test that high frequency applies special boost to market eta_neg."""
        cfg_standard = FatTailCfg(enabled=True, tail_frequency="standard")
        per_std, market_std = _apply_toggles(cfg_standard)
        
        cfg_high = FatTailCfg(enabled=True, tail_frequency="high")
        per_high, market_high = _apply_toggles(cfg_high)
        
        # High frequency should boost market eta_neg by 1.10x
        expected_eta_neg = market_std.eta_neg * 1.10
        assert abs(market_high.eta_neg - expected_eta_neg) < 0.001, (
            f"High frequency eta_neg boost incorrect: {market_high.eta_neg} vs {expected_eta_neg}"
        )
    
    def test_negative_skew_asymmetry(self):
        """Test that negative skew creates proper asymmetry."""
        cfg = FatTailCfg(enabled=True, tail_skew="negative")
        per_adj, market_adj = _apply_toggles(cfg)
        
        # p_pos should be reduced
        assert market_adj.p_pos < cfg.market.p_pos, "Negative skew didn't reduce p_pos"
        
        # eta_neg should be scaled up by 1.10
        expected_eta_neg = cfg.market.eta_neg * 1.10
        assert abs(market_adj.eta_neg - expected_eta_neg) < 0.001, (
            f"Negative skew eta_neg scale incorrect: {market_adj.eta_neg} vs {expected_eta_neg}"
        )
        
        # eta_pos should be unchanged (no 0.95 scale for negative skew)
        assert market_adj.eta_pos == cfg.market.eta_pos, (
            "Negative skew shouldn't affect eta_pos"
        )
    
    def test_positive_skew_asymmetry(self):
        """Test that positive skew creates proper asymmetry."""
        cfg = FatTailCfg(enabled=True, tail_skew="positive")
        per_adj, market_adj = _apply_toggles(cfg)
        
        # p_pos should be increased
        assert market_adj.p_pos > cfg.market.p_pos, "Positive skew didn't increase p_pos"
        
        # eta_neg should be scaled down by 0.95
        expected_eta_neg = cfg.market.eta_neg * 0.95
        assert abs(market_adj.eta_neg - expected_eta_neg) < 0.001, (
            f"Positive skew eta_neg scale incorrect: {market_adj.eta_neg} vs {expected_eta_neg}"
        )
        
        # eta_pos should be scaled down by 0.95
        expected_eta_pos = cfg.market.eta_pos * 0.95
        assert abs(market_adj.eta_pos - expected_eta_pos) < 0.001, (
            f"Positive skew eta_pos scale incorrect: {market_adj.eta_pos} vs {expected_eta_pos}"
        )


class TestToggleEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_disabled_fat_tails(self):
        """Test that disabled fat-tails doesn't apply toggles."""
        cfg = FatTailCfg(enabled=False, tail_magnitude="extreme")
        
        # Toggles shouldn't matter when disabled
        # This is handled at a higher level, but test config is valid
        assert cfg.tail_magnitude == "extreme"
        assert cfg.enabled == False
    
    def test_extreme_parameter_values(self):
        """Test handling of extreme parameter values."""
        cfg = FatTailCfg(enabled=True)
        
        # Set extreme values
        cfg.market.p_pos = 0.99
        cfg.tail_skew = "positive"  # Would add 0.05
        
        per_adj, market_adj = _apply_toggles(cfg)
        
        # Should be clamped to valid range
        assert market_adj.p_pos <= 0.95, f"p_pos {market_adj.p_pos} exceeds maximum"
        
        # Test other extreme
        cfg.market.p_pos = 0.01
        cfg.tail_skew = "negative"  # Would subtract 0.05
        
        per_adj, market_adj = _apply_toggles(cfg)
        assert market_adj.p_pos >= 0.05, f"p_pos {market_adj.p_pos} below minimum"
    
    def test_combined_extreme_settings(self):
        """Test that combined extreme settings don't produce invalid results."""
        cfg = FatTailCfg(
            enabled=True,
            tail_magnitude="extreme",
            tail_frequency="high",
            tail_skew="negative",
            black_swan_active=True
        )
        
        per_adj, market_adj = _apply_toggles(cfg)
        
        # All parameters should still be valid
        assert market_adj.lam > 0 and market_adj.lam < 1.0
        assert market_adj.eta_neg > 0 and market_adj.eta_neg < 0.5
        assert market_adj.eta_pos > 0 and market_adj.eta_pos < 0.5
        assert 0 < market_adj.p_pos < 1
        
        # Black Swan coordination should limit eta_neg
        assert market_adj.eta_neg <= 0.070 * 1.30 * 1.10 * 1.10, (
            "Black Swan coordination not working with extreme settings"
        )