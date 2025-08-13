"""
Pydantic models for the retirement calculator.
All data models and validation logic.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field, conint, confloat


# ============================
# Event Models
# ============================
class LumpEvent(BaseModel):
    """One-time lump sum event (inheritance, home sale, etc.)"""
    age: int
    amount: float
    description: str = ""


class ToyPurchase(BaseModel):
    """Major purchase event (car, vacation, etc.)"""
    age: int
    amount: float
    description: str


# ============================
# Income Models
# ============================
class IncomeStream(BaseModel):
    """Recurring income stream (Social Security, pension, etc.)"""
    start_age: int
    end_age: int
    monthly: float
    cola: float = 0.02  # annual cost of living adjustment


class ConsultingLadder(BaseModel):
    """Post-retirement consulting income that tapers off"""
    start_age: int = 55
    years: conint(ge=0, le=20) = 5
    start_amount: float = 25000
    growth: float = 0.10  # annual growth rate


# ============================
# Portfolio Models
# ============================
class Account(BaseModel):
    """Investment account with asset allocation"""
    kind: str  # "401k", "IRA", "Taxable", "Cash", "Crypto"
    balance: float
    # Allocation by asset class (sum <= 1.0; residual treated as cash)
    stocks: float = 0.0
    bonds: float = 0.0
    crypto: float = 0.0
    cds: float = 0.0
    cash: float = 0.0


class BlackSwanEvent(BaseModel):
    """Sudden portfolio drop at a specific age"""
    enabled: bool = False
    age: int = 67  # Age when the event occurs
    portfolio_drop: float = 0.25  # Percentage drop (0.25 = 25% drop)


# ============================
# Market Assumptions
# ============================
class CapitalMarketAssumptions(BaseModel):
    """Expected returns, volatilities, and correlations for asset classes"""
    
    # Expected returns and volatilities (nominal, annual)
    exp_ret: Dict[str, float] = Field(
        default_factory=lambda: {
            "stocks": 0.08, 
            "bonds": 0.045, 
            "crypto": 0.20, 
            "cds": 0.04, 
            "cash": 0.03
        }
    )
    vol: Dict[str, float] = Field(
        default_factory=lambda: {
            "stocks": 0.17, 
            "bonds": 0.07, 
            "crypto": 0.80, 
            "cds": 0.02, 
            "cash": 0.01
        }
    )
    
    # Correlation matrix between asset classes
    corr: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "stocks": {"stocks": 1.0, "bonds": 0.2, "crypto": 0.5, "cds": -0.1, "cash": -0.2},
            "bonds":  {"stocks": 0.2, "bonds": 1.0, "crypto": 0.1, "cds": 0.3,  "cash": 0.2},
            "crypto": {"stocks": 0.5, "bonds": 0.1, "crypto": 1.0, "cds": 0.0,  "cash": -0.1},
            "cds":    {"stocks": -0.1, "bonds": 0.3, "crypto": 0.0, "cds": 1.0,  "cash": 0.4},
            "cash":   {"stocks": -0.2, "bonds": 0.2, "crypto": -0.1, "cds": 0.4,  "cash": 1.0},
        }
    )
    
    # Fat-tail configuration
    fat_tails: bool = True
    t_df: int = 12  # degrees of freedom for Student-t (12=subtle, 8=moderate, 6=strong)
    tail_boost: float = 1.0  # skewness: <1.0 negative, 1.0 neutral, >1.0 positive
    tail_prob: float = 0.020  # 2.0% = standard frequency (placeholder)


# ============================
# Tax & Spending Models
# ============================
class Taxes(BaseModel):
    """Tax configuration for retirement planning"""
    effective_rate: float = 0.20  # Applied to taxable withdrawals and income
    taxable_portfolio_ratio: float = 0.75  # Portion of portfolio withdrawals that are taxable
    taxable_income_ratio: float = 0.80  # Portion of income that is taxable


class Spending(BaseModel):
    """Annual spending configuration"""
    base_annual: float = 100000
    reduced_annual: float = 70000
    reduce_at_age: int = 57
    inflation: float = 0.02  # Annual inflation rate


# ============================
# Main Scenario Model
# ============================
class Scenario(BaseModel):
    """Complete retirement scenario configuration"""
    name: str = "Base"
    current_age: int = 55
    end_age: int = 90
    
    # Financial components
    accounts: List[Account]
    cma: CapitalMarketAssumptions = CapitalMarketAssumptions()
    taxes: Taxes = Taxes()
    spending: Spending = Spending()
    
    # Income sources
    consulting: ConsultingLadder = ConsultingLadder()
    incomes: List[IncomeStream] = Field(default_factory=list)
    
    # One-time events
    lumps: List[LumpEvent] = Field(default_factory=list)
    toys: List[ToyPurchase] = Field(default_factory=list)
    black_swan: BlackSwanEvent = BlackSwanEvent()
    
    # Simulation parameters
    sims: conint(ge=500, le=100000) = 10000


# ============================
# Response Models
# ============================
class SimulationResult(BaseModel):
    """Results from a Monte Carlo simulation"""
    ages: List[int]
    median: List[float]
    p20: List[float]
    p80: List[float]
    end_balance_percentiles: Dict[str, float]
    success_prob: float