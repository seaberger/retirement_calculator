"""
Option B: Log-safe fat-tail engine with Student-t body and Kou jumps.
Works in log space to prevent impossible returns (<-100%).
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
    lam: float = 0.20          # Bernoulli p = 1 - exp(-lam)  (~18% per year)
    p_pos: float = 0.40
    eta_pos: float = 0.035     # log-space magnitudes are smaller than arithmetic %
    eta_neg: float = 0.075
    affected_assets: Sequence[str] = ("stocks", "crypto")
    bond_beta: float = 0.10    # fraction of market jump applied to bonds


@dataclass
class FatTailCfg:
    """Complete fat-tail configuration."""
    enabled: bool = True
    t_df: float = 6.0          # vol-preserving Student-t body
    tail_magnitude: str = "standard"   # "standard" | "extreme"
    tail_frequency: str = "standard"   # "standard" | "high"
    tail_skew: str = "neutral"         # "negative" | "neutral" | "positive"
    
    # Baseline per-asset jump params (LOG space). Calibrated for realistic impact.
    per_asset: Dict[str, KouLog] = field(default_factory=lambda: {
        "stocks": KouLog(0.30, 0.40, 0.030, 0.060),   # gentle, historically plausible
        "bonds":  KouLog(0.02, 0.50, 0.006, 0.012),
        "crypto": KouLog(0.90, 0.45, 0.140, 0.170),
        "cds":    KouLog(0.00, 0.50, 0.000, 0.000),
        "cash":   KouLog(0.00, 0.50, 0.000, 0.000),
    })
    market: MarketJumpLog = field(default_factory=MarketJumpLog)
    
    # Hard annual floors in arithmetic space (prevents unrealistic wipeouts)
    floors: Dict[str, float] = field(default_factory=lambda: {
        "stocks": -0.60, "bonds": -0.25, "crypto": -0.85, "cds": -0.05, "cash": -0.02
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
    """Apply UI toggles with mild, realistic multipliers."""
    # Aiming for 2-5% success-rate impact, not 25-30%
    mag = 1.30 if cfg.tail_magnitude == "extreme" else 1.00
    freq = 1.40 if cfg.tail_frequency == "high" else 1.00
    skew = {"negative": -0.05, "neutral": 0.0, "positive": +0.05}[cfg.tail_skew]

    per_adj = {}
    for k, p in cfg.per_asset.items():
        per_adj[k] = KouLog(
            lam=p.lam * freq,
            p_pos=float(np.clip(p.p_pos + skew, 0.05, 0.95)),
            eta_pos=p.eta_pos * mag,
            eta_neg=p.eta_neg * mag
        )
    
    mk = cfg.market
    market_adj = MarketJumpLog(
        lam=mk.lam * freq,
        p_pos=float(np.clip(mk.p_pos + skew, 0.05, 0.95)),
        eta_pos=mk.eta_pos * mag,
        eta_neg=mk.eta_neg * mag,
        affected_assets=tuple(mk.affected_assets),
        bond_beta=mk.bond_beta
    )
    return per_adj, market_adj


# ============================
# Main API
# ============================
def draw_fat_tailed_returns_optionB(
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

    def _simulate_block(Y, S, mu_log_local):
        """Simulate returns for Y years and S scenarios."""
        body = _t_shocks_log(Y, S, chol_log, df, rng)
        logr = mu_log_local + body

        # Market co-jump: at most 1 per year (Bernoulli)
        if market_adj.lam > 0:
            p_event = 1.0 - np.exp(-market_adj.lam)  # ≈ lam for small lam
            M = rng.random((Y, S)) < p_event
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
        for k, j in idx.items():
            floor = cfg.floors.get(k, -0.90)
            r[:, :, j] = np.maximum(r[:, :, j], floor)
        return r

    # Mean-correction: pilot simulation to ensure E[R] ≈ mu_arith after jumps
    if cfg.enabled and mean_correct_pilot > 0:
        pilot = _simulate_block(1, mean_correct_pilot, mu_log)
        m_sim = pilot.mean(axis=(0, 1))  # (A,)
        delta = np.log1p(mu_arith) - np.log1p(np.clip(m_sim, -0.95, 5.0))
        mu_log = mu_log + delta.reshape(1, 1, A)

    return _simulate_block(n_years, n_sims, mu_log)