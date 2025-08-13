"""
Shared fixtures for fat-tail algorithm testing.
"""

import sys
import os
import pytest
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

from models import Scenario, Account, Spending
from monte_carlo.fat_tails_kou_logsafe import FatTailCfg, KouLog, MarketJumpLog


@pytest.fixture
def standard_portfolio_scenario():
    """Standard 60/40 portfolio scenario for testing."""
    return {
        "name": "TestScenario",
        "current_age": 55,
        "end_age": 90,
        "accounts": [
            {
                "kind": "401k",
                "balance": 1500000,
                "stocks": 0.6,
                "bonds": 0.4,
                "crypto": 0.0,
                "cds": 0.0,
                "cash": 0.0
            }
        ],
        "spending": {
            "base_annual": 60000,
            "reduced_annual": 60000,
            "reduce_at_age": 65,
            "inflation": 0.025
        },
        "consulting": {
            "start_age": 55,
            "years": 0,
            "start_amount": 0,
            "growth": 0
        },
        "incomes": [],
        "lumps": [],
        "toys": [],
        "sims": 10000,
        "taxes": {
            "effective_rate": 0.15,
            "taxable_income_ratio": 1.0,
            "taxable_portfolio_ratio": 0.5
        },
        "black_swan": {
            "enabled": False,
            "age": 60,
            "portfolio_drop": 0.5
        }
    }


@pytest.fixture
def equity_only_scenario():
    """100% equity portfolio for distribution testing."""
    return {
        "name": "EquityTest",
        "current_age": 55,
        "end_age": 56,  # Single year for distribution testing
        "accounts": [
            {
                "kind": "401k",
                "balance": 1000000,
                "stocks": 1.0,
                "bonds": 0.0,
                "crypto": 0.0,
                "cds": 0.0,
                "cash": 0.0
            }
        ],
        "spending": {
            "base_annual": 0,
            "reduced_annual": 0,
            "reduce_at_age": 65,
            "inflation": 0.0
        },
        "sims": 50000,  # More simulations for distribution testing
    }


@pytest.fixture
def standard_fat_tail_cfg():
    """Standard fat-tail configuration."""
    return FatTailCfg(
        enabled=True,
        t_df=6.0,
        tail_magnitude="standard",
        tail_frequency="standard",
        tail_skew="neutral",
        black_swan_active=False
    )


@pytest.fixture
def equity_params():
    """Standard equity return parameters."""
    return {
        "mu": np.array([0.08]),  # 8% expected return
        "sigma": np.array([0.17]),  # 17% volatility
        "cov": np.array([[0.17**2]])  # Covariance matrix
    }


@pytest.fixture
def portfolio_params():
    """60/40 portfolio parameters."""
    mu_stocks = 0.08
    mu_bonds = 0.04
    sigma_stocks = 0.17
    sigma_bonds = 0.08
    corr = 0.1
    
    mu = np.array([mu_stocks, mu_bonds])
    cov = np.array([
        [sigma_stocks**2, corr * sigma_stocks * sigma_bonds],
        [corr * sigma_stocks * sigma_bonds, sigma_bonds**2]
    ])
    
    return {
        "mu": mu,
        "cov": cov,
        "weights": np.array([0.6, 0.4])  # 60/40 weights
    }


@pytest.fixture
def tolerance():
    """Tolerance for statistical tests."""
    return {
        "impact": 0.5,  # 0.5% tolerance for impact tests
        "quantile": 0.02,  # 2% tolerance for quantiles
        "mean": 0.01,  # 1% tolerance for mean
        "std": 0.02,  # 2% tolerance for standard deviation
    }


@pytest.fixture
def run_simulation():
    """Factory fixture for running simulations."""
    def _run(scenario_dict, fat_tail_cfg=None):
        from models import Scenario
        from monte_carlo import Engine
        
        scenario = Scenario(**scenario_dict)
        
        if fat_tail_cfg:
            # Monkey-patch the config for testing
            import monte_carlo.fat_tails_kou_logsafe as kou_module
            original_init = kou_module.FatTailCfg.__init__
            
            def custom_init(self, **kwargs):
                for key, value in fat_tail_cfg.__dict__.items():
                    setattr(self, key, value)
            
            kou_module.FatTailCfg.__init__ = custom_init
            
        eng = Engine(scenario, fat_tail_engine="kou_logsafe")
        result = eng.run()
        
        if fat_tail_cfg:
            # Restore original
            kou_module.FatTailCfg.__init__ = original_init
            
        return result
    
    return _run