from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, conint, confloat
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, Session

# ============================
# SQLite setup
# ============================
# Create data directory path relative to project root
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "retire.db"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Base = declarative_base()

class ScenarioRow(Base):
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False)
    payload = Column(Text, nullable=False)  # JSON string of Scenario

Base.metadata.create_all(engine)

# ============================
# Monte Carlo inputs
# ============================
class LumpEvent(BaseModel):
    age: int
    amount: float
    description: str = ""

class IncomeStream(BaseModel):
    start_age: int
    end_age: int
    monthly: float
    cola: float = 0.02  # annual growth

class ConsultingLadder(BaseModel):
    start_age: int = 55
    years: conint(ge=0, le=20) = 5
    start_amount: float = 25000
    growth: float = 0.10  # annual growth

class ToyPurchase(BaseModel):
    age: int
    amount: float
    description: str

class Account(BaseModel):
    kind: str  # "401k", "IRA", "Taxable", "Cash", "Crypto"
    balance: float
    # allocation by asset class (sum <= 1.0; residual treated as cash)
    stocks: float = 0.0
    bonds: float = 0.0
    crypto: float = 0.0
    cds: float = 0.0
    cash: float = 0.0

class BlackSwanEvent(BaseModel):
    enabled: bool = False
    age: int = 67  # Age when the event occurs
    portfolio_drop: float = 0.25  # Percentage drop (0.25 = 25% drop)

class CapitalMarketAssumptions(BaseModel):
    # Expected returns and vols (nominal) — can be overridden in UI
    exp_ret: Dict[str, float] = Field(
        default_factory=lambda: {"stocks": 0.08, "bonds": 0.045, "crypto": 0.20, "cds": 0.04, "cash": 0.03}
    )
    vol: Dict[str, float] = Field(
        default_factory=lambda: {"stocks": 0.17, "bonds": 0.07, "crypto": 0.80, "cds": 0.02, "cash": 0.01}
    )
    # Correlations between asset classes
    corr: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "stocks": {"stocks": 1.0, "bonds": 0.2, "crypto": 0.5, "cds": -0.1, "cash": -0.2},
            "bonds":  {"stocks": 0.2, "bonds": 1.0, "crypto": 0.1, "cds": 0.3,  "cash": 0.2},
            "crypto": {"stocks": 0.5, "bonds": 0.1, "crypto": 1.0, "cds": 0.0,  "cash": -0.1},
            "cds":    {"stocks": -0.1, "bonds": 0.3, "crypto": 0.0, "cds": 1.0,  "cash": 0.4},
            "cash":   {"stocks": -0.2, "bonds": 0.2, "crypto": -0.1, "cds": 0.4,  "cash": 1.0},
        }
    )
    # Fat tails config (research-calibrated: df 10-15 for subtle fat tails)
    fat_tails: bool = True
    t_df: int = 12  # degrees of freedom for Student-t (12=subtle, 8=moderate, 6=strong)
    tail_boost: float = 1.0  # skewness: <1.0 negative, 1.0 neutral, >1.0 positive
    tail_prob: float = 0.020   # 2.0% = standard frequency (not used currently)

class Taxes(BaseModel):
    effective_rate: float = 0.20  # applied to taxable withdrawals and taxable income
    taxable_portfolio_ratio: float = 0.75
    taxable_income_ratio: float = 0.80

class Spending(BaseModel):
    base_annual: float = 100000
    reduced_annual: float = 70000
    reduce_at_age: int = 57
    inflation: float = 0.02

class Scenario(BaseModel):
    name: str = "Base"
    current_age: int = 55
    end_age: int = 90
    accounts: List[Account]
    cma: CapitalMarketAssumptions = CapitalMarketAssumptions()
    taxes: Taxes = Taxes()
    spending: Spending = Spending()
    consulting: ConsultingLadder = ConsultingLadder()
    incomes: List[IncomeStream] = Field(default_factory=list)
    lumps: List[LumpEvent] = Field(default_factory=list)
    toys: List[ToyPurchase] = Field(default_factory=list)
    black_swan: BlackSwanEvent = BlackSwanEvent()
    sims: conint(ge=500, le=100000) = 10000

# ============================
# Monte Carlo engine
# ============================
ASSETS = ["stocks", "bonds", "crypto", "cds", "cash"]

class Engine:
    def __init__(self, scenario: Scenario):
        self.sc = scenario
        self.horizon = scenario.end_age - scenario.current_age
        self._prep_cov()

    def _prep_cov(self):
        # Build covariance matrix from vols & correlations
        vols = np.array([self.sc.cma.vol[a] for a in ASSETS])
        corr = np.array([[self.sc.cma.corr[i][j] for j in ASSETS] for i in ASSETS])
        self.cov = np.outer(vols, vols) * corr
        self.chol = np.linalg.cholesky(self.cov)
        self.mu = np.array([self.sc.cma.exp_ret[a] for a in ASSETS])

    def _draw_returns(self, n_years: int, n_sims: int) -> np.ndarray:
        """
        Draw fat-tailed returns using Lévy process: Student-t diffusion + Kou jumps
        Based on the research document for realistic market dynamics
        """
        # Use the improved fat-tail engine if enabled
        if self.sc.cma.fat_tails:
            # Map UI settings to the fat-tail engine parameters
            # Magnitude: df controls Student-t tail heaviness
            # Frequency: controls jump intensity (lambda)
            # Skewness: controls jump direction bias
            
            # Determine magnitude setting from df
            if self.sc.cma.t_df <= 5:
                magnitude = "extreme"
            else:
                magnitude = "standard"
            
            # Determine frequency setting from tail_prob
            if self.sc.cma.tail_prob >= 0.04:
                frequency = "high"
            else:
                frequency = "standard"
            
            # Determine skew from tail_boost
            if self.sc.cma.tail_boost < 0.9:
                skew = "negative"
            elif self.sc.cma.tail_boost > 1.1:
                skew = "positive"
            else:
                skew = "neutral"
            
            # Use the fat-tail generator
            rets = self._draw_fat_tailed_returns(
                mu=self.mu,
                chol=self.chol,
                assets=ASSETS,
                n_years=n_years,
                n_sims=n_sims,
                t_df=self.sc.cma.t_df,
                tail_magnitude=magnitude,
                tail_frequency=frequency,
                tail_skew=skew
            )
        else:
            # Standard normal returns without fat tails
            z = np.random.normal(size=(n_years, n_sims, len(ASSETS)))
            z_corr = z @ self.chol.T
            rets = self.mu + z_corr
        
        return rets  # shape [years, sims, assets]
    
    def _draw_fat_tailed_returns(self, mu, chol, assets, n_years, n_sims, 
                                  t_df, tail_magnitude, tail_frequency, tail_skew):
        """
        Calibrated fat-tail implementation (Option A - Hyperparameter tuning):
        - Reduced magnitude: 2-5% extra volatility (not 8-12%)
        - Reduced frequency: 10-15% annual probability (not per simulation)
        - Gentle skew adjustments: ±5% (not ±10%)
        - Mean correction to preserve expected returns
        """
        rng = np.random.default_rng(None)
        A = len(assets)
        
        # 1) Generate base returns using normal distribution
        z = rng.standard_normal(size=(n_years, n_sims, A))
        z_corr = z @ chol.T
        
        # Start with base returns (arithmetic)
        rets = mu.reshape(1, 1, A) + z_corr
        
        # 2) Add calibrated market stress events
        # Historical: ~10% chance of >20% decline per year
        # But we want subtle impact on multi-year simulations
        
        if tail_frequency == "standard":
            stress_prob = 0.10  # 10% annual chance (historical)
        else:  # high frequency
            stress_prob = 0.15  # 15% annual chance (1.5x historical, not 2x)
        
        # Stress magnitude: 2-5% range for standard
        if tail_magnitude == "standard":
            stress_base = 0.03  # 3% base stress magnitude
        else:  # extreme
            stress_base = 0.04  # 4% base (1.33x standard, not 1.6x)
        
        # Apply stress events with calibrated skew
        stress_events = rng.random((n_years, n_sims)) < stress_prob
        n_stress = int(stress_events.sum())
        
        if n_stress > 0:
            # Gentle skew adjustments (±5%, not ±10%)
            if tail_skew == "negative":
                p_up = 0.40  # 40% up, 60% down (gentle negative skew)
            elif tail_skew == "positive":
                p_up = 0.60  # 60% up, 40% down (gentle positive skew)
            else:  # neutral
                p_up = 0.45  # 45% up, 55% down (slight negative bias is realistic)
            
            # Draw stress directions
            stress_directions = rng.random(n_stress) < p_up
            
            # Vary stress magnitude slightly for realism (2-5% range)
            stress_magnitudes = stress_base + rng.normal(0, 0.01, n_stress)  # ±1% variation
            stress_magnitudes = np.clip(stress_magnitudes, 0.02, 0.05)  # Keep in 2-5% range
            
            # Apply direction
            stress_sizes = np.where(stress_directions, stress_magnitudes, -stress_magnitudes)
            
            # Create stress adjustment matrix
            stress_adjustments = np.zeros((n_years, n_sims))
            stress_adjustments[stress_events] = stress_sizes
            
            # Apply to assets with realistic correlations
            for i, asset in enumerate(assets):
                if asset == "stocks":
                    rets[:, :, i] += stress_adjustments  # Full impact on stocks
                elif asset == "crypto":
                    rets[:, :, i] += 1.5 * stress_adjustments  # 150% impact on crypto
                elif asset == "bonds":
                    # Bonds: flight-to-quality (negative correlation in stress)
                    rets[:, :, i] -= 0.2 * stress_adjustments  # 20% opposite movement
        
        # 3) Mean correction to preserve expected returns
        # Calculate actual mean after stress events
        if n_stress > 0:
            for i, asset in enumerate(assets):
                actual_mean = np.mean(rets[:, :, i])
                target_mean = mu[i]
                # Add small drift correction to preserve expected return
                drift_correction = (target_mean - actual_mean) * 0.5  # Partial correction
                rets[:, :, i] += drift_correction
        
        # 4) Apply realistic annual return bounds (calibrated to history)
        for i, asset in enumerate(assets):
            if asset == "crypto":
                # Crypto: can be extreme but not infinite
                rets[:, :, i] = np.clip(rets[:, :, i], -0.85, 3.00)
            elif asset == "stocks":
                # Stocks: historical bounds with fat-tail allowance
                if tail_magnitude == "extreme":
                    rets[:, :, i] = np.clip(rets[:, :, i], -0.70, 1.00)  # Extreme: -70% floor
                else:
                    rets[:, :, i] = np.clip(rets[:, :, i], -0.60, 0.80)  # Standard: -60% floor
            elif asset == "bonds":
                # Bonds: tighter bounds
                rets[:, :, i] = np.clip(rets[:, :, i], -0.25, 0.35)
            elif asset == "cds":
                # CDs: minimal volatility
                rets[:, :, i] = np.clip(rets[:, :, i], -0.05, 0.10)
            else:  # cash
                # Cash: nearly risk-free
                rets[:, :, i] = np.clip(rets[:, :, i], -0.02, 0.08)
        
        return rets

    def _account_allocation_vector(self) -> np.ndarray:
        # Weighted allocation across all accounts by balance
        balances = np.array([acc.balance for acc in self.sc.accounts], dtype=float)
        if balances.sum() <= 0:
            raise ValueError("Total account balance must be > 0")
        weights_by_acc = balances / balances.sum()
        # For each account, map to assets
        W = np.zeros((len(self.sc.accounts), len(ASSETS)))
        for i, acc in enumerate(self.sc.accounts):
            alloc = np.array([acc.stocks, acc.bonds, acc.crypto, acc.cds, acc.cash], dtype=float)
            if alloc.sum() == 0:
                alloc[-1] = 1.0  # default to cash if unspecified
            W[i] = alloc / alloc.sum()
        # Overall portfolio asset weights:
        port_w = (weights_by_acc[:, None] * W).sum(axis=0)
        return port_w  # length = len(ASSETS)

    def _year_income(self, age: int) -> float:
        # Regular income (pre-retirement working income)
        inc = 0.0
        if self.sc.consulting.start_age <= age < self.sc.consulting.start_age + self.sc.consulting.years:
            k = age - self.sc.consulting.start_age
            inc += self.sc.consulting.start_amount * ((1 + self.sc.consulting.growth) ** k)
        # Retirement income streams (Social Security, pensions, consulting, etc.)
        for s in self.sc.incomes:
            if s.start_age <= age <= s.end_age:
                years_since = age - s.start_age
                amt = s.monthly * 12.0 * ((1 + s.cola) ** years_since)
                inc += amt
        return inc

    def _year_spend(self, age: int, year0_spend_state: Dict[str, float]) -> float:
        base = self.sc.spending.base_annual
        if age >= self.sc.spending.reduce_at_age:
            base = self.sc.spending.reduced_annual
        # Inflate from scenario start
        years = age - self.sc.current_age
        return base * ((1 + self.sc.spending.inflation) ** years)

    def run(self) -> Dict[str, Any]:
        nY = self.horizon + 1
        nS = self.sc.sims
        port_w = self._account_allocation_vector()
        # initial portfolio
        init_bal = sum(acc.balance for acc in self.sc.accounts)
        balances = np.zeros((nY, nS))
        balances[0, :] = init_bal

        rets = self._draw_returns(nY - 1, nS)  # per year except starting point
        # Map portfolio return each year from asset returns and weights
        port_rets = (rets @ port_w)

        # Build lump sums by age for quick lookup
        lump_by_age = {e.age: e.amount for e in self.sc.lumps}
        toys_by_age = {}
        for t in self.sc.toys:
            toys_by_age.setdefault(t.age, 0.0)
            toys_by_age[t.age] += t.amount

        # Iterate per year
        for yi in range(1, nY):
            age = self.sc.current_age + yi

            income = self._year_income(age)
            spend = self._year_spend(age, {})

            # Taxes (simple effective-rate approach)
            taxable_income = income * self.sc.taxes.taxable_income_ratio
            tax_on_income = taxable_income * self.sc.taxes.effective_rate
            net_income = max(income - tax_on_income, 0.0)

            # Net withdrawal = spend - net income
            net_wd = max(spend - net_income, 0.0)
            # tax on portfolio withdrawal, approximated
            taxable_wd = net_wd * self.sc.taxes.taxable_portfolio_ratio
            tax_on_wd = taxable_wd * self.sc.taxes.effective_rate
            net_wd_after_tax = net_wd + tax_on_wd

            # Apply lump sums at START of year
            lump = lump_by_age.get(age, 0.0)
            toys = toys_by_age.get(age, 0.0)
            
            # Mid-year withdrawal approach:
            # 1. Start with previous balance plus any lump sums
            start_balance = balances[yi-1, :] + lump
            
            # 2. Apply Black Swan event if configured (BEFORE growth)
            if self.sc.black_swan.enabled and age == self.sc.black_swan.age:
                # Apply the portfolio drop to all simulations at this age
                start_balance = start_balance * (1.0 - self.sc.black_swan.portfolio_drop)
            
            # 3. Apply half year's growth
            half_year_return = port_rets[yi-1, :] / 2.0
            mid_year_balance = start_balance * (1.0 + half_year_return)
            
            # 4. Apply withdrawals and toy purchases at mid-year
            after_withdrawal = mid_year_balance - toys - net_wd_after_tax
            
            # 5. Apply remaining half year's growth
            end_balance = after_withdrawal * (1.0 + half_year_return)
            
            # 6. Ensure non-negative balance
            balances[yi, :] = np.maximum(end_balance, 0.0)

        # Summaries
        median_path = np.median(balances, axis=1)
        p20_path = np.percentile(balances, 20, axis=1)
        p80_path = np.percentile(balances, 80, axis=1)
        end_balances = balances[-1, :]
        summary = {
            "ages": list(range(self.sc.current_age, self.sc.end_age + 1)),
            "median": median_path.tolist(),
            "p20": p20_path.tolist(),
            "p80": p80_path.tolist(),
            "end_balance_percentiles": {
                "p20": float(np.percentile(end_balances, 20)),
                "p50": float(np.percentile(end_balances, 50)),
                "p80": float(np.percentile(end_balances, 80)),
            },
            "success_prob": float((end_balances > 0).mean()),
        }
        return summary

# ============================
# FastAPI app
# ============================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Retirement Calculator API", "docs": "Visit /docs for API documentation"}

@app.get("/api/default_scenario")
def default_scenario() -> Scenario:
    sc = Scenario(
        name="Example",
        current_age=45,
        end_age=90,
        accounts=[
            Account(kind="401k", balance=800_000, stocks=0.7, bonds=0.3),
            Account(kind="Taxable", balance=400_000, stocks=0.6, bonds=0.3, cash=0.1),
            Account(kind="IRA", balance=300_000, stocks=0.6, bonds=0.4),
        ],
        consulting=ConsultingLadder(start_age=46, years=9, start_amount=100_000, growth=0.02),  # Income starts at age 46 (year after current_age)
        spending=Spending(base_annual=80_000, reduced_annual=60_000, reduce_at_age=65, inflation=0.025),
        incomes=[
            IncomeStream(start_age=55, end_age=60, monthly=2000, cola=0.02), # Post-retirement consulting
            IncomeStream(start_age=67, end_age=90, monthly=3000, cola=0.02), # Social Security
            IncomeStream(start_age=67, end_age=90, monthly=2000, cola=0.02), # Spouse Social Security
        ],
        lumps=[
            LumpEvent(age=65, amount=200_000, description="Home downsizing"),
        ],
        toys=[ToyPurchase(age=65, amount=30_000, description="Dream vacation")],
    )
    return sc

@app.post("/api/simulate")
def simulate(scenario: Scenario):
    try:
        eng = Engine(scenario)
        out = eng.run()
        return out
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/scenarios")
def list_scenarios():
    with Session(engine) as s:
        rows = s.query(ScenarioRow).all()
        return [{"id": r.id, "name": r.name} for r in rows]

@app.get("/api/scenarios/{sid}")
def get_scenario(sid: int):
    with Session(engine) as s:
        row = s.get(ScenarioRow, sid)
        if not row:
            raise HTTPException(404, "Not found")
        return json.loads(row.payload)

@app.post("/api/scenarios")
def save_scenario(scenario: Scenario):
    with Session(engine) as s:
        # upsert by name
        row = s.query(ScenarioRow).filter_by(name=scenario.name).first()
        if row is None:
            row = ScenarioRow(name=scenario.name, payload=scenario.model_dump_json())
            s.add(row)
        else:
            row.payload = scenario.model_dump_json()
        s.commit()
        return {"id": row.id, "name": row.name}