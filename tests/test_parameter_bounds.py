"""
Test parameter bounds and guardrails for the fat-tail algorithm.
Ensures parameters stay within reasonable ranges.
"""

import pytest
import numpy as np
from monte_carlo.fat_tails_kou_logsafe import FatTailCfg, _apply_toggles


class TestParameterBounds:
    """Test that parameters stay within acceptable bounds."""
    
    def test_standard_t_df(self):
        """Test that Standard configuration uses t_df = 6.0."""
        cfg = FatTailCfg(
            enabled=True,
            tail_magnitude="standard",
            tail_frequency="standard",
            tail_skew="neutral"
        )
        
        assert cfg.t_df == 6.0, f"Standard t_df should be 6.0, got {cfg.t_df}"
    
    def test_market_lam_bounds(self):
        """Test that market lambda doesn't exceed 0.25 in Standard."""
        cfg = FatTailCfg(enabled=True)
        
        assert cfg.market.lam == 0.25, f"Standard market lam should be 0.25, got {cfg.market.lam}"
        
        # Even with high frequency, shouldn't exceed reasonable bounds
        cfg.tail_frequency = "high"
        per_adj, market_adj = _apply_toggles(cfg)
        
        # 0.25 * 1.5 = 0.375
        assert market_adj.lam <= 0.40, (
            f"High frequency market lam {market_adj.lam} exceeds 0.40"
        )
    
    def test_floor_values(self):
        """Test that floor values are appropriate."""
        cfg = FatTailCfg(enabled=True)
        
        # Standard floors
        assert cfg.floors["stocks"] == -0.60, "Standard stock floor should be -60%"
        assert cfg.floors["bonds"] == -0.25, "Bond floor should be -25%"
        assert cfg.floors["crypto"] == -0.85, "Crypto floor should be -85%"
        
        # Extreme floors
        assert cfg.extreme_floors["stocks"] == -0.70, "Extreme stock floor should be -70%"
    
    def test_toggle_multipliers(self):
        """Test that toggle multipliers are within specified ranges."""
        cfg = FatTailCfg(enabled=True)
        
        # Test extreme magnitude multiplier
        cfg.tail_magnitude = "extreme"
        per_adj, market_adj = _apply_toggles(cfg)
        
        # Should apply 1.30x to magnitudes
        expected_eta_neg = cfg.market.eta_neg * 1.30
        assert abs(market_adj.eta_neg - expected_eta_neg) < 0.001, (
            f"Extreme magnitude multiplier incorrect: {market_adj.eta_neg} vs {expected_eta_neg}"
        )
        
        # Test high frequency multiplier
        cfg = FatTailCfg(enabled=True, tail_frequency="high")
        per_adj, market_adj = _apply_toggles(cfg)
        
        # Should apply 1.50x to frequencies
        expected_lam = cfg.market.lam * 1.50
        assert abs(market_adj.lam - expected_lam) < 0.001, (
            f"High frequency multiplier incorrect: {market_adj.lam} vs {expected_lam}"
        )
    
    def test_black_swan_coordination(self):
        """Test that Black Swan coordination reduces market eta_neg."""
        cfg = FatTailCfg(enabled=True, black_swan_active=False)
        per_adj_normal, market_adj_normal = _apply_toggles(cfg)
        
        cfg.black_swan_active = True
        per_adj_bs, market_adj_bs = _apply_toggles(cfg)
        
        # With Black Swan active, market eta_neg should be reduced to max 0.070
        assert market_adj_bs.eta_neg <= 0.070, (
            f"Black Swan active: market eta_neg {market_adj_bs.eta_neg} > 0.070"
        )
        
        # Should be less than or equal to normal
        assert market_adj_bs.eta_neg <= market_adj_normal.eta_neg, (
            "Black Swan coordination should reduce market eta_neg"
        )
    
    def test_skew_adjustments(self):
        """Test that skew adjustments are applied correctly."""
        cfg = FatTailCfg(enabled=True, tail_skew="negative")
        per_adj, market_adj = _apply_toggles(cfg)
        
        # Negative skew should reduce p_pos by 0.05
        expected_p_pos = cfg.market.p_pos - 0.05
        assert abs(market_adj.p_pos - expected_p_pos) < 0.001, (
            f"Negative skew p_pos adjustment incorrect: {market_adj.p_pos} vs {expected_p_pos}"
        )
        
        # Should also scale eta_neg by 1.10
        expected_eta_neg = cfg.market.eta_neg * 1.10
        assert abs(market_adj.eta_neg - expected_eta_neg) < 0.001, (
            f"Negative skew eta_neg scaling incorrect: {market_adj.eta_neg} vs {expected_eta_neg}"
        )
    
    def test_parameter_combinations(self):
        """Test that parameter combinations don't produce extreme values."""
        # Most extreme combination
        cfg = FatTailCfg(
            enabled=True,
            tail_magnitude="extreme",
            tail_frequency="high",
            tail_skew="negative"
        )
        per_adj, market_adj = _apply_toggles(cfg)
        
        # Even with all extreme settings, parameters should be bounded
        assert market_adj.lam <= 0.50, "Combined settings: market lam too high"
        assert market_adj.eta_neg <= 0.15, "Combined settings: market eta_neg too high"
        assert market_adj.p_pos >= 0.20, "Combined settings: p_pos too low"
    
    def test_idiosyncratic_jump_cap(self):
        """Test that idiosyncratic jumps are capped at 1 per year."""
        cfg = FatTailCfg(enabled=True)
        
        assert cfg.max_idio_jumps_per_year == 1, (
            f"Idiosyncratic jumps should be capped at 1/year, got {cfg.max_idio_jumps_per_year}"
        )


class TestParameterValidation:
    """Test parameter validation and error handling."""
    
    def test_invalid_magnitude(self):
        """Test that invalid magnitude values are handled."""
        cfg = FatTailCfg(enabled=True)
        cfg.tail_magnitude = "invalid"
        
        # Should default to standard behavior
        per_adj, market_adj = _apply_toggles(cfg)
        assert market_adj.eta_neg == cfg.market.eta_neg  # No multiplier applied
    
    def test_probability_bounds(self):
        """Test that probabilities stay within [0, 1]."""
        cfg = FatTailCfg(enabled=True)
        
        # Test extreme p_pos adjustments
        cfg.market.p_pos = 0.95
        cfg.tail_skew = "positive"
        per_adj, market_adj = _apply_toggles(cfg)
        
        assert 0.0 <= market_adj.p_pos <= 1.0, (
            f"p_pos {market_adj.p_pos} outside [0, 1]"
        )
        
        # Test extreme negative
        cfg.market.p_pos = 0.05
        cfg.tail_skew = "negative"
        per_adj, market_adj = _apply_toggles(cfg)
        
        assert 0.0 <= market_adj.p_pos <= 1.0, (
            f"p_pos {market_adj.p_pos} outside [0, 1]"
        )
    
    def test_sequence_risk_bounds(self):
        """Test that sequence risk parameters are reasonable."""
        cfg = FatTailCfg(
            enabled=True,
            sequence_risk_boost=1.1,
            early_retirement_years=10
        )
        
        assert cfg.sequence_risk_boost >= 1.0, "Sequence risk boost should be >= 1.0"
        assert cfg.sequence_risk_boost <= 1.5, "Sequence risk boost should be <= 1.5"
        assert cfg.early_retirement_years >= 0, "Early retirement years should be >= 0"
        assert cfg.early_retirement_years <= 20, "Early retirement years should be <= 20"