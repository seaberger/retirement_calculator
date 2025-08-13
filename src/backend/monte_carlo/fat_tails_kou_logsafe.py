"""
Kou Log-Safe Fat-Tail Algorithm: Realistic market dynamics with mathematical safety.
Implements Kou double-exponential jumps in log-space to prevent impossible returns.
Calibrated to achieve 2-5% impact on success rates, matching industry best practices.
"""

from dataclasses import dataclass, field
from typing import Dict, Sequence, Optional
import numpy as np


# ============================
# Configuration Classes
# ============================
@dataclass
class KouLog:
    """Parameters for Kou jump process in log space."""
    lam: float      # annual jump intensity
    p_pos: float    # P(positive jump)
    eta_pos: float  # mean +jump size (LOG-return scale)
    eta_neg: float  # mean -jump size (LOG-return scale, applied negative)


@dataclass
class MarketJumpLog:
    """Market-wide jump configuration."""
    lam: float = 0.25          # Optimized: ~22% annual probability
    p_pos: float = 0.40
    eta_pos: float = 0.055     # Optimized for 2-5% portfolio impact
    eta_neg: float = 0.075     # Calibrated to historical tail risk
    affected_assets: Sequence[str] = ("stocks", "crypto")
    bond_beta: float = 0.10    # fraction of market jump applied to bonds (flight-to-quality)


@dataclass
class FatTailCfg:
    """Complete fat-tail configuration."""
    enabled: bool = True
    t_df: float = 6.0          # Optimized via fractional factorial design
    tail_magnitude: str = "standard"   # "standard" | "extreme"
    tail_frequency: str = "standard"   # "standard" | "high"
    tail_skew: str = "neutral"         # "negative" | "neutral" | "positive"
    
    # Coordination with Black Swan feature
    black_swan_active: bool = False  # Set True when Black Swan is enabled
    
    # Sequence risk enhancement (optional)
    early_retirement_years: int = 10  # Years to apply sequence risk boost
    sequence_risk_boost: float = 1.1  # Multiplier for early years (1.0 = disabled)
    
    # Baseline per-asset jump params (LOG space). Calibrated to U.S. equity history.
    per_asset: Dict[str, KouLog] = field(default_factory=lambda: {
        "stocks": KouLog(0.20, 0.40, 0.030, 0.075),   # Optimized: meets all targets
        "bonds":  KouLog(0.03, 0.50, 0.006, 0.012),   # minimal jumps
        "crypto": KouLog(0.90, 0.45, 0.140, 0.170),   # higher volatility asset
        "cds":    KouLog(0.00, 0.50, 0.000, 0.000),   # no jumps
        "cash":   KouLog(0.00, 0.50, 0.000, 0.000),   # no jumps
    })
    market: MarketJumpLog = field(default_factory=MarketJumpLog)
    
    # Hard annual floors in arithmetic space (prevents unrealistic wipeouts)
    floors: Dict[str, float] = field(default_factory=lambda: {
        "stocks": -0.60, "bonds": -0.25, "crypto": -0.85, "cds": -0.05, "cash": -0.02
    })
    extreme_floors: Dict[str, float] = field(default_factory=lambda: {
        "stocks": -0.70, "bonds": -0.25, "crypto": -0.85, "cds": -0.05, "cash": -0.02
    })
    max_idio_jumps_per_year: int = 1
    seed: Optional[int] = None


# ============================
# Helper Functions
# ============================
def _arith_to_log_cov(mu_arith: np.ndarray, cov_arith: np.ndarray) -> np.ndarray:
    """
    Approximate log-return covariance from arithmetic covariance.
    Var[log(1+r_i)] ≈ Var[r_i] / (1+mu_i)^2, Cov scaled similarly.
    """
    scale = 1.0 / (1.0 + mu_arith)
    S = np.outer(scale, scale)
    return cov_arith * S


def _t_shocks_log(years: int, sims: int, chol_log: np.ndarray, df: float, rng) -> np.ndarray:
    """
    Zero-mean, vol-preserving Student-t shocks in log space, correlated via chol_log.
    """
    YS, A = years * sims, chol_log.shape[0]
    z = rng.standard_t(df, size=(YS, A))
    if df > 2:
        z *= np.sqrt((df - 2.0) / df)  # unit-variance t, then correlate
    return (z @ chol_log.T).reshape(years, sims, A)


def _jump_sizes_log(n: int, p_pos: float, eta_pos: float, eta_neg: float, rng) -> np.ndarray:
    """Draw jump sizes from double-exponential distribution in log space."""
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


def _apply_toggles(cfg: FatTailCfg):
    """Apply UI toggles with calibrated multipliers for realistic impact."""
    # Calibrated for 2-5% (standard), 4-8% (extreme), 3-6% (high freq) impact
    mag = 1.30 if cfg.tail_magnitude == "extreme" else 1.00
    freq = 1.50 if cfg.tail_frequency == "high" else 1.00  # Updated to 1.5x per recommendation
    
    # High frequency also needs magnitude boost for market jumps
    high_freq_mag_boost = 1.10 if cfg.tail_frequency == "high" else 1.00
    
    skew = {"negative": -0.05, "neutral": 0.0, "positive": +0.05}[cfg.tail_skew]
    skew_mag_scale = {"negative": 1.10, "neutral": 1.00, "positive": 0.95}[cfg.tail_skew]

    per_adj = {}
    for k, p in cfg.per_asset.items():
        per_adj[k] = KouLog(
            lam=p.lam * freq,
            p_pos=float(np.clip(p.p_pos + skew, 0.05, 0.95)),
            eta_pos=p.eta_pos * mag * (0.95 if cfg.tail_skew == "positive" else 1.0),
            eta_neg=p.eta_neg * mag * skew_mag_scale
        )
    
    mk = cfg.market
    
    # Adjust market eta_neg if Black Swan is active to avoid double-counting
    market_eta_neg_base = mk.eta_neg
    if cfg.black_swan_active:
        market_eta_neg_base = min(mk.eta_neg, 0.070)  # Reduce to 0.070 when Black Swan ON
    
    market_adj = MarketJumpLog(
        lam=mk.lam * freq,
        p_pos=float(np.clip(mk.p_pos + skew, 0.05, 0.95)),
        eta_pos=mk.eta_pos * mag * (0.95 if cfg.tail_skew == "positive" else 1.0),
        eta_neg=market_eta_neg_base * mag * high_freq_mag_boost * skew_mag_scale,
        affected_assets=tuple(mk.affected_assets),
        bond_beta=mk.bond_beta
    )
    return per_adj, market_adj


# ============================
# Main API
# ============================
def draw_fat_tailed_returns_kou_logsafe(
    mu_arith: np.ndarray,         # (A,) arithmetic means (decimals)
    cov_arith: np.ndarray,        # (A,A) arithmetic covariance
    assets: Sequence[str],        # names aligned to vectors/matrices
    n_years: int,
    n_sims: int,
    cfg: FatTailCfg,
    mean_correct_pilot: int = 40_000
) -> np.ndarray:
    """
    Returns (years, sims, assets) in arithmetic space using:
    - Student-t log-diffusion
    - Kou (double-exponential) jumps in log space
    - One market co-jump/year (Bernoulli)
    - Capped idiosyncratic jumps
    - Drift auto-correction
    - Asset-specific floors
    
    This approach prevents impossible returns (<-100%) and provides
    realistic fat-tail behavior with 2-5% impact on success rates.
    """
    rng = np.random.default_rng(cfg.seed)
    assets = list(assets)
    A = len(assets)

    # Convert to log-space covariance
    cov_log = _arith_to_log_cov(mu_arith, cov_arith)
    chol_log = np.linalg.cholesky(cov_log + 1e-18 * np.eye(A))  # small jitter for stability

    df = cfg.t_df if cfg.enabled else 1e9
    mu_log = np.log1p(mu_arith).reshape(1, 1, A)

    per_adj, market_adj = _apply_toggles(cfg)
    idx = {a: i for i, a in enumerate(assets)}
    aff_idx = [idx[a] for a in market_adj.affected_assets if a in idx]
    bonds_i = idx.get("bonds")

    def _simulate_block(Y, S, mu_log_local, year_offset=0):
        """Simulate returns for Y years and S scenarios."""
        body = _t_shocks_log(Y, S, chol_log, df, rng)
        logr = mu_log_local + body

        # Market co-jump: at most 1 per year (Bernoulli)
        if market_adj.lam > 0:
            # Apply sequence risk boost for early retirement years
            lam_effective = market_adj.lam
            if cfg.sequence_risk_boost > 1.0:
                for y in range(Y):
                    if year_offset + y < cfg.early_retirement_years:
                        # Use year-specific boosted lambda
                        pass  # Will handle per-year below
            
            # Generate market jumps with potential sequence risk adjustment
            M = np.zeros((Y, S), dtype=bool)
            for y in range(Y):
                year_lam = market_adj.lam
                if cfg.sequence_risk_boost > 1.0 and (year_offset + y) < cfg.early_retirement_years:
                    year_lam *= cfg.sequence_risk_boost
                    year_lam = min(year_lam, 0.35)  # Cap at reasonable level
                p_event = 1.0 - np.exp(-year_lam)
                M[y, :] = rng.random(S) < p_event
            n = int(M.sum())
            if n > 0:
                m_sizes = _jump_sizes_log(n, market_adj.p_pos, 
                                         market_adj.eta_pos, market_adj.eta_neg, rng)
                m_full = np.zeros((Y, S))
                m_full[M] = m_sizes
                for j in aff_idx:
                    logr[:, :, j] += m_full
                if bonds_i is not None and market_adj.bond_beta:
                    logr[:, :, bonds_i] += market_adj.bond_beta * m_full

        # Idiosyncratic jumps: cap to 1/year/asset (keeps tails realistic)
        YS = Y * S
        for name, p in per_adj.items():
            j = idx.get(name)
            if j is None or p.lam <= 0:
                continue
            counts = np.minimum(rng.poisson(p.lam, size=YS), cfg.max_idio_jumps_per_year)
            tot = int(counts.sum())
            if tot == 0:
                continue
            sizes = _jump_sizes_log(tot, p.p_pos, p.eta_pos, p.eta_neg, rng)
            bins = np.bincount(np.repeat(np.arange(YS), counts), 
                              weights=sizes, minlength=YS)
            logr[:, :, j] += bins.reshape(Y, S)

        # Convert to arithmetic and apply floors
        r = np.expm1(logr)  # exp(log_r) - 1, guarantees r > -1
        
        # Use extreme floors if extreme magnitude is selected
        floors_to_use = cfg.extreme_floors if cfg.tail_magnitude == "extreme" else cfg.floors
        
        for k, j in idx.items():
            floor = floors_to_use.get(k, -0.90)
            r[:, :, j] = np.maximum(r[:, :, j], floor)
        return r

    # Mean-correction: pilot simulation to ensure E[R] ≈ mu_arith after jumps
    if cfg.enabled and mean_correct_pilot > 0:
        pilot = _simulate_block(1, mean_correct_pilot, mu_log)
        m_sim = pilot.mean(axis=(0, 1))  # (A,)
        delta = np.log1p(mu_arith) - np.log1p(np.clip(m_sim, -0.95, 5.0))
        mu_log = mu_log + delta.reshape(1, 1, A)

    return _simulate_block(n_years, n_sims, mu_log, year_offset=0)