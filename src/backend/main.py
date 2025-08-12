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
    # Fat tails config (based on research: 5-10 df is typical for financial returns)
    fat_tails: bool = True
    t_df: int = 8  # degrees of freedom for Student-t (8=standard magnitude, 5=extreme magnitude)
    tail_boost: float = 1.0  # skewness: <1.0 negative, 1.0 neutral, >1.0 positive
    tail_prob: float = 0.025   # 2.5% = standard frequency (matches historical U.S. markets)

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
        SAFE fat-tail generator using log-domain Student-t + Kou jumps
        Prevents unrealistic wipeouts with proper safety rails
        """
        rng = np.random.default_rng(None)
        A = len(assets)
        
        # Convert arithmetic parameters to log space for safer calculations
        # Log drift approximation: mu_log ≈ ln(1 + mu_arith)
        mu_log = np.log1p(mu)
        
        # For log-domain covariance, we need to adjust the Cholesky
        # Approximation: σ_log ≈ σ_arith for small volatilities
        # More accurate: σ_log = sqrt(ln(1 + (σ_arith/1+μ)²))
        # For simplicity, use the arithmetic Cholesky scaled down slightly
        chol_log = chol * 0.95  # Slight reduction for log space
        
        # 1) Diffusion body in log space with Student-t
        df = t_df if t_df > 0 else 1e6
        YS = n_years * n_sims
        
        # Draw Student-t samples with variance preservation
        z = rng.standard_t(df, size=(YS, A))
        if df > 2:
            scale = np.sqrt((df - 2.0) / df)  # Scale to unit variance
            z *= scale
        
        # Correlate and reshape
        shocks = (z @ chol_log.T).reshape(n_years, n_sims, A)
        
        # Start with log returns = drift + diffusion
        logr = mu_log.reshape(1, 1, A) + shocks
        
        # 2) Jump parameters in LOG space (safer)
        jump_params = {
            "stocks": {"lam": 0.40, "p_pos": 0.35, "eta_pos": 0.05, "eta_neg": 0.09},
            "bonds":  {"lam": 0.05, "p_pos": 0.50, "eta_pos": 0.01, "eta_neg": 0.02},
            "crypto": {"lam": 1.20, "p_pos": 0.40, "eta_pos": 0.18, "eta_neg": 0.22},
            "cds":    {"lam": 0.00, "p_pos": 0.50, "eta_pos": 0.00, "eta_neg": 0.00},
            "cash":   {"lam": 0.00, "p_pos": 0.50, "eta_pos": 0.00, "eta_neg": 0.00},
        }
        
        # Market jump parameters (Bernoulli to prevent multiple crashes per year)
        market_lam = 0.30
        market_p_pos = 0.35
        market_eta_pos = 0.04
        market_eta_neg = 0.08
        bond_beta = 0.10
        
        # Safety parameters
        min_annual_return = -0.70 if tail_magnitude == "standard" else -0.80
        max_idio_jumps_per_year = 2
        
        # Apply magnitude/frequency/skew adjustments
        mag_mult = 1.6 if tail_magnitude == "extreme" else 1.0
        freq_mult = 2.0 if tail_frequency == "high" else 1.0
        skew_shift = {"negative": -0.10, "neutral": 0.0, "positive": 0.10}[tail_skew]
        
        # Adjust parameters
        for asset in jump_params:
            jump_params[asset]["lam"] *= freq_mult
            jump_params[asset]["p_pos"] = float(np.clip(jump_params[asset]["p_pos"] + skew_shift, 0.05, 0.95))
            jump_params[asset]["eta_pos"] *= mag_mult
            jump_params[asset]["eta_neg"] *= mag_mult
        
        market_lam *= freq_mult
        market_p_pos = float(np.clip(market_p_pos + skew_shift, 0.05, 0.95))
        market_eta_pos *= mag_mult
        market_eta_neg *= mag_mult
        
        # Helper: draw jump sizes in log space
        def draw_jump_sizes_log(n, p_pos, eta_pos, eta_neg):
            if n <= 0:
                return np.empty(0)
            u = rng.random(n)
            pos = u < p_pos
            out = np.empty(n)
            if pos.any():
                out[pos] = rng.exponential(scale=max(1e-12, eta_pos), size=pos.sum())
            if (~pos).any():
                out[~pos] = -rng.exponential(scale=max(1e-12, eta_neg), size=(~pos).sum())
            return out
        
        # 3) Market jump: Bernoulli (at most 1 per year to prevent pileups)
        if market_lam > 0:
            p_event = 1.0 - np.exp(-market_lam)  # Bernoulli probability
            M = rng.random((n_years, n_sims)) < p_event
            n_events = int(M.sum())
            if n_events > 0:
                m_sizes = draw_jump_sizes_log(n_events, market_p_pos, market_eta_pos, market_eta_neg)
                m_full = np.zeros((n_years, n_sims))
                m_full[M] = m_sizes
                
                # Apply to affected assets
                for i, asset in enumerate(assets):
                    if asset in ["stocks", "crypto"]:
                        logr[:, :, i] += m_full
                    elif asset == "bonds" and bond_beta != 0:
                        logr[:, :, i] += bond_beta * m_full
        
        # 4) Idiosyncratic jumps with cap to prevent pileups
        for i, asset in enumerate(assets):
            if asset not in jump_params:
                continue
            params = jump_params[asset]
            if params["lam"] <= 0:
                continue
            
            # Draw Poisson then cap at max jumps per year
            counts = np.minimum(
                rng.poisson(params["lam"], size=YS),
                max_idio_jumps_per_year
            )
            total = int(counts.sum())
            if total > 0:
                sizes = draw_jump_sizes_log(total, params["p_pos"], params["eta_pos"], params["eta_neg"])
                bins = np.bincount(np.repeat(np.arange(YS), counts), weights=sizes, minlength=YS)
                logr[:, :, i] += bins.reshape(n_years, n_sims)
        
        # 5) Convert to arithmetic returns with hard floor
        r = np.expm1(logr)  # exp(logr) - 1, guarantees r > -1
        
        # Apply annual floor (e.g., -70% standard, -80% extreme)
        np.maximum(r, min_annual_return, out=r)
        
        # Also apply reasonable ceilings to prevent outliers
        for i, asset in enumerate(assets):
            if asset == "crypto":
                np.minimum(r[:, :, i], 3.00, out=r[:, :, i])
            elif asset == "stocks":
                np.minimum(r[:, :, i], 1.00, out=r[:, :, i])
            elif asset == "bonds":
                np.minimum(r[:, :, i], 0.40, out=r[:, :, i])
            else:  # CDs and cash
                np.minimum(r[:, :, i], 0.15, out=r[:, :, i])
        
        return r

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
            
            # 2. Apply half year's growth
            half_year_return = port_rets[yi-1, :] / 2.0
            mid_year_balance = start_balance * (1.0 + half_year_return)
            
            # 3. Apply withdrawals and toy purchases at mid-year
            after_withdrawal = mid_year_balance - toys - net_wd_after_tax
            
            # 4. Apply remaining half year's growth
            end_balance = after_withdrawal * (1.0 + half_year_return)
            
            # 5. Ensure non-negative balance
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