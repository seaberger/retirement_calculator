"""
Core Monte Carlo simulation engine for retirement planning.
"""

from typing import Dict, Any, Optional
import numpy as np

try:
    # Try relative imports (when running as module)
    from ..models import Scenario
    from ..config import ASSETS, DEFAULT_FAT_TAIL_ENGINE
except ImportError:
    # Fall back to absolute imports
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from models import Scenario
    from config import ASSETS, DEFAULT_FAT_TAIL_ENGINE


class Engine:
    """Monte Carlo simulation engine for retirement scenarios."""
    
    def __init__(self, scenario: Scenario, fat_tail_engine: Optional[str] = None):
        """
        Initialize the Monte Carlo engine.
        
        Args:
            scenario: The retirement scenario to simulate
            fat_tail_engine: Which fat-tail implementation to use 
                           ("kou_logsafe", "research", or "current")
        """
        self.sc = scenario
        self.horizon = scenario.end_age - scenario.current_age
        self.fat_tail_engine = fat_tail_engine or DEFAULT_FAT_TAIL_ENGINE
        self._prep_cov()

    def _prep_cov(self):
        """Build covariance matrix from volatilities and correlations."""
        vols = np.array([self.sc.cma.vol[a] for a in ASSETS])
        corr = np.array([[self.sc.cma.corr[i][j] for j in ASSETS] for i in ASSETS])
        self.cov = np.outer(vols, vols) * corr
        self.chol = np.linalg.cholesky(self.cov)
        self.mu = np.array([self.sc.cma.exp_ret[a] for a in ASSETS])

    def _draw_returns(self, n_years: int, n_sims: int) -> np.ndarray:
        """
        Draw returns using selected fat-tail engine or normal distribution.
        
        Returns:
            Array of shape (n_years, n_sims, n_assets) with annual returns
        """
        if self.sc.cma.fat_tails:
            # Determine UI settings
            magnitude = "extreme" if self.sc.cma.t_df <= 5 else "standard"
            frequency = "high" if self.sc.cma.tail_prob >= 0.04 else "standard"
            
            if self.sc.cma.tail_boost < 0.9:
                skew = "negative"
            elif self.sc.cma.tail_boost > 1.1:
                skew = "positive"
            else:
                skew = "neutral"
            
            # Select fat-tail engine
            if self.fat_tail_engine == "kou_logsafe":
                from .fat_tails_kou_logsafe import draw_fat_tailed_returns_kou_logsafe, FatTailCfg
                cfg = FatTailCfg(
                    enabled=True,
                    t_df=self.sc.cma.t_df,
                    tail_magnitude=magnitude,
                    tail_frequency=frequency,
                    tail_skew=skew
                )
                return draw_fat_tailed_returns_kou_logsafe(
                    mu_arith=self.mu,
                    cov_arith=self.cov,
                    assets=ASSETS,
                    n_years=n_years,
                    n_sims=n_sims,
                    cfg=cfg
                )
            elif self.fat_tail_engine == "research":
                from .fat_tails_research import draw_fat_tailed_returns, FatTailConfig
                cfg = FatTailConfig(
                    enabled=True,
                    t_df=self.sc.cma.t_df,
                    tail_magnitude=magnitude,
                    tail_frequency=frequency,
                    tail_skew=skew
                )
                return draw_fat_tailed_returns(
                    mu=self.mu,
                    chol=self.chol,
                    assets=ASSETS,
                    n_years=n_years,
                    n_sims=n_sims,
                    cfg=cfg
                )
            else:  # "current" - use existing implementation
                return self._draw_fat_tailed_returns_current(
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
            return rets

    def _draw_fat_tailed_returns_current(self, mu, chol, assets, n_years, n_sims, 
                                         t_df, tail_magnitude, tail_frequency, tail_skew):
        """Current implementation (kept for comparison)."""
        rng = np.random.default_rng(None)
        A = len(assets)
        
        # Generate base returns using normal distribution
        z = rng.standard_normal(size=(n_years, n_sims, A))
        z_corr = z @ chol.T
        rets = mu.reshape(1, 1, A) + z_corr
        
        # Add calibrated market stress events
        if tail_frequency == "standard":
            stress_prob = 0.10
        else:
            stress_prob = 0.15
        
        if tail_magnitude == "standard":
            stress_base = 0.03
        else:
            stress_base = 0.04
        
        stress_events = rng.random((n_years, n_sims)) < stress_prob
        n_stress = int(stress_events.sum())
        
        if n_stress > 0:
            if tail_skew == "negative":
                p_up = 0.40
            elif tail_skew == "positive":
                p_up = 0.60
            else:
                p_up = 0.45
            
            stress_directions = rng.random(n_stress) < p_up
            stress_magnitudes = stress_base + rng.normal(0, 0.01, n_stress)
            stress_magnitudes = np.clip(stress_magnitudes, 0.02, 0.05)
            stress_sizes = np.where(stress_directions, stress_magnitudes, -stress_magnitudes)
            
            stress_adjustments = np.zeros((n_years, n_sims))
            stress_adjustments[stress_events] = stress_sizes
            
            for i, asset in enumerate(assets):
                if asset == "stocks":
                    rets[:, :, i] += stress_adjustments
                elif asset == "crypto":
                    rets[:, :, i] += 1.5 * stress_adjustments
                elif asset == "bonds":
                    rets[:, :, i] -= 0.2 * stress_adjustments
        
        # Mean correction
        if n_stress > 0:
            for i, asset in enumerate(assets):
                actual_mean = np.mean(rets[:, :, i])
                target_mean = mu[i]
                drift_correction = (target_mean - actual_mean) * 0.5
                rets[:, :, i] += drift_correction
        
        # Apply realistic bounds
        for i, asset in enumerate(assets):
            if asset == "crypto":
                rets[:, :, i] = np.clip(rets[:, :, i], -0.85, 3.00)
            elif asset == "stocks":
                if tail_magnitude == "extreme":
                    rets[:, :, i] = np.clip(rets[:, :, i], -0.70, 1.00)
                else:
                    rets[:, :, i] = np.clip(rets[:, :, i], -0.60, 0.80)
            elif asset == "bonds":
                rets[:, :, i] = np.clip(rets[:, :, i], -0.25, 0.35)
            elif asset == "cds":
                rets[:, :, i] = np.clip(rets[:, :, i], -0.05, 0.10)
            else:  # cash
                rets[:, :, i] = np.clip(rets[:, :, i], -0.02, 0.08)
        
        return rets

    def _account_allocation_vector(self) -> np.ndarray:
        """Calculate weighted allocation across all accounts by balance."""
        balances = np.array([acc.balance for acc in self.sc.accounts], dtype=float)
        if balances.sum() <= 0:
            raise ValueError("Total account balance must be > 0")
        weights_by_acc = balances / balances.sum()
        
        # Map each account to assets
        W = np.zeros((len(self.sc.accounts), len(ASSETS)))
        for i, acc in enumerate(self.sc.accounts):
            alloc = np.array([acc.stocks, acc.bonds, acc.crypto, acc.cds, acc.cash], dtype=float)
            if alloc.sum() == 0:
                alloc[-1] = 1.0  # default to cash if unspecified
            W[i] = alloc / alloc.sum()
        
        # Overall portfolio asset weights
        port_w = (weights_by_acc[:, None] * W).sum(axis=0)
        return port_w

    def _year_income(self, age: int) -> float:
        """Calculate total income for a given age."""
        inc = 0.0
        
        # Consulting income
        if self.sc.consulting.start_age <= age < self.sc.consulting.start_age + self.sc.consulting.years:
            k = age - self.sc.consulting.start_age
            inc += self.sc.consulting.start_amount * ((1 + self.sc.consulting.growth) ** k)
        
        # Retirement income streams
        for s in self.sc.incomes:
            if s.start_age <= age <= s.end_age:
                years_since = age - s.start_age
                amt = s.monthly * 12.0 * ((1 + s.cola) ** years_since)
                inc += amt
        
        return inc

    def _year_spend(self, age: int, year0_spend_state: Dict[str, float]) -> float:
        """Calculate spending for a given age."""
        base = self.sc.spending.base_annual
        if age >= self.sc.spending.reduce_at_age:
            base = self.sc.spending.reduced_annual
        
        # Inflate from scenario start
        years = age - self.sc.current_age
        return base * ((1 + self.sc.spending.inflation) ** years)

    def run(self) -> Dict[str, Any]:
        """
        Run the Monte Carlo simulation.
        
        Returns:
            Dictionary with simulation results including percentiles and success probability
        """
        nY = self.horizon + 1
        nS = self.sc.sims
        port_w = self._account_allocation_vector()
        
        # Initial portfolio balance
        init_bal = sum(acc.balance for acc in self.sc.accounts)
        balances = np.zeros((nY, nS))
        balances[0, :] = init_bal

        # Draw returns for all years
        rets = self._draw_returns(nY - 1, nS)
        port_rets = (rets @ port_w)

        # Build lump sums and toys by age
        lump_by_age = {e.age: e.amount for e in self.sc.lumps}
        toys_by_age = {}
        for t in self.sc.toys:
            toys_by_age.setdefault(t.age, 0.0)
            toys_by_age[t.age] += t.amount

        # Simulate each year
        for yi in range(1, nY):
            age = self.sc.current_age + yi

            income = self._year_income(age)
            spend = self._year_spend(age, {})

            # Taxes
            taxable_income = income * self.sc.taxes.taxable_income_ratio
            tax_on_income = taxable_income * self.sc.taxes.effective_rate
            net_income = max(income - tax_on_income, 0.0)

            # Net withdrawal
            net_wd = max(spend - net_income, 0.0)
            taxable_wd = net_wd * self.sc.taxes.taxable_portfolio_ratio
            tax_on_wd = taxable_wd * self.sc.taxes.effective_rate
            net_wd_after_tax = net_wd + tax_on_wd

            # Apply lump sums
            lump = lump_by_age.get(age, 0.0)
            toys = toys_by_age.get(age, 0.0)
            
            # Mid-year withdrawal approach
            start_balance = balances[yi-1, :] + lump
            
            # Apply Black Swan event if configured
            if self.sc.black_swan.enabled and age == self.sc.black_swan.age:
                start_balance = start_balance * (1.0 - self.sc.black_swan.portfolio_drop)
            
            # Apply half year's growth
            half_year_return = port_rets[yi-1, :] / 2.0
            mid_year_balance = start_balance * (1.0 + half_year_return)
            
            # Apply withdrawals and toy purchases
            after_withdrawal = mid_year_balance - toys - net_wd_after_tax
            
            # Apply remaining half year's growth
            end_balance = after_withdrawal * (1.0 + half_year_return)
            
            # Ensure non-negative balance
            balances[yi, :] = np.maximum(end_balance, 0.0)

        # Calculate summary statistics
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