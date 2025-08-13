"""
Research-based fat-tail engine using Student-t and Kou jumps in arithmetic space.
Based on academic literature for realistic market dynamics.
"""

import copy
from dataclasses import dataclass, field
from typing import Dict, Sequence, Optional
import numpy as np


# ============================
# Configuration Classes
# ============================
@dataclass
class KouParams:
    """Parameters for Kou jump process."""
    lam: float      # annual Poisson intensity (frequency)
    p_pos: float    # probability a jump is positive
    eta_pos: float  # mean positive jump size on arithmetic RETURN scale
    eta_neg: float  # mean negative jump size on arithmetic RETURN scale


@dataclass
class MarketJump:
    """Market-wide jump configuration."""
    lam: float = 0.25
    p_pos: float = 0.35
    eta_pos: float = 0.05
    eta_neg: float = 0.08
    affected_assets: Sequence[str] = ("stocks", "crypto")
    bond_beta: float = 0.20


@dataclass
class FatTailConfig:
    """Complete fat-tail configuration."""
    enabled: bool = True
    t_df: float = 12.0  # Calibrated default: Higher df for less extreme body
    tail_magnitude: str = "standard"
    tail_frequency: str = "standard"
    tail_skew: str = "neutral"
    
    # Per-asset jumps: Calibrated for more realistic impact
    per_asset: Dict[str, KouParams] = field(default_factory=lambda: {
        "stocks": KouParams(lam=0.15, p_pos=0.35, eta_pos=0.04, eta_neg=0.08),  # Reduced
        "bonds":  KouParams(lam=0.05, p_pos=0.50, eta_pos=0.01, eta_neg=0.02),  # Reduced
        "crypto": KouParams(lam=0.50, p_pos=0.40, eta_pos=0.15, eta_neg=0.20),  # Reduced
        "cds":    KouParams(lam=0.00, p_pos=0.50, eta_pos=0.00, eta_neg=0.00),
        "cash":   KouParams(lam=0.00, p_pos=0.50, eta_pos=0.00, eta_neg=0.00),
    })
    market: MarketJump = field(default_factory=MarketJump)
    seed: Optional[int] = None


# ============================
# Helper Functions  
# ============================
def _student_t_correlated(years: int, sims: int, n_assets: int, 
                          chol: np.ndarray, df: float, rng: np.random.Generator) -> np.ndarray:
    """Generate correlated Student-t shocks with variance preservation."""
    Z = rng.standard_t(df, size=(years * sims, n_assets))
    # Scale shocks to preserve target covariance: Var(t) = df/(df-2)
    if df > 2.0:
        Z *= np.sqrt((df - 2) / df)
    C = Z @ chol.T
    return C.reshape(years, sims, n_assets)


def _double_exponential_jump(n: int, p_pos: float, eta_pos: float, 
                             eta_neg: float, rng: np.random.Generator) -> np.ndarray:
    """Draw jump sizes from double-exponential (Laplace) distribution."""
    if n <= 0:
        return np.empty(0, dtype=float)
    u = rng.random(n)
    pos = u < p_pos
    sizes = np.empty(n, dtype=float)
    if pos.any():
        sizes[pos] = rng.exponential(scale=max(1e-12, eta_pos), size=pos.sum())
    if (~pos).any():
        sizes[~pos] = -rng.exponential(scale=max(1e-12, eta_neg), size=(~pos).sum())
    return sizes


def _apply_toggles_to_params(cfg: FatTailConfig) -> FatTailConfig:
    """Apply UI toggles to create adjusted parameters."""
    # Create a deep copy to avoid mutating the original
    new_cfg = copy.deepcopy(cfg)

    # Conservative multipliers for realistic impact
    mag_mult = 1.6 if new_cfg.tail_magnitude == "extreme" else 1.0
    freq_mult = 2.0 if new_cfg.tail_frequency == "high" else 1.0
    skew_shift = {"negative": -0.15, "neutral": 0.0, "positive": +0.15}.get(new_cfg.tail_skew, 0.0)

    # Adjust per-asset params
    for name, p in new_cfg.per_asset.items():
        p.lam *= freq_mult
        p.p_pos = float(np.clip(p.p_pos + skew_shift, 0.05, 0.95))
        p.eta_pos *= mag_mult
        p.eta_neg *= mag_mult

    # Adjust market jump params
    m = new_cfg.market
    m.lam *= freq_mult
    m.p_pos = float(np.clip(m.p_pos + skew_shift, 0.05, 0.95))
    m.eta_pos *= mag_mult
    m.eta_neg *= mag_mult
    
    return new_cfg


# ============================
# Main API
# ============================
def draw_fat_tailed_returns(
    mu: np.ndarray,             # (A,) arithmetic means
    chol: np.ndarray,           # (A,A) Cholesky of arithmetic covariance
    assets: Sequence[str],      # asset names
    n_years: int,
    n_sims: int,
    cfg: FatTailConfig,
) -> np.ndarray:
    """
    Generate fat-tailed returns using Student-t body and Kou jumps.
    
    Returns:
        Array of shape (years, sims, assets) with annual arithmetic returns
    """
    rng = np.random.default_rng(cfg.seed)
    A = len(assets)

    # 1) Body: correlated Student-t shocks
    body = _student_t_correlated(n_years, n_sims, A, chol, cfg.t_df, rng)
    rets = body + mu.reshape(1, 1, A)

    if not cfg.enabled:
        return rets

    # 2) Apply toggles to a copy of the params
    p_cfg = _apply_toggles_to_params(cfg)
    idx = {a: i for i, a in enumerate(assets)}
    affected_idx = [idx[a] for a in p_cfg.market.affected_assets if a in idx]
    bond_i = idx.get("bonds", None)
    YS = n_years * n_sims

    # 3) Market Jumps
    if p_cfg.market.lam > 0:
        m_counts = rng.poisson(lam=p_cfg.market.lam, size=YS)
        total_m = int(m_counts.sum())
        if total_m > 0:
            m_sizes = _double_exponential_jump(total_m, p_cfg.market.p_pos, 
                                              p_cfg.market.eta_pos, p_cfg.market.eta_neg, rng)
            m_bins = np.bincount(np.repeat(np.arange(YS), m_counts), 
                               weights=m_sizes, minlength=YS).reshape(n_years, n_sims)
            if affected_idx:
                for j in affected_idx:
                    rets[:, :, j] += m_bins
            if bond_i is not None and p_cfg.market.bond_beta != 0:
                rets[:, :, bond_i] += p_cfg.market.bond_beta * m_bins

    # 4) Idiosyncratic Jumps
    for a_name, p in p_cfg.per_asset.items():
        j = idx.get(a_name)
        if j is None or p.lam <= 0:
            continue
        counts = rng.poisson(lam=p.lam, size=YS)
        total = int(counts.sum())
        if total == 0:
            continue
        sizes = _double_exponential_jump(total, p.p_pos, p.eta_pos, p.eta_neg, rng)
        bins = np.bincount(np.repeat(np.arange(YS), counts), weights=sizes, minlength=YS)
        rets[:, :, j] += bins.reshape(n_years, n_sims)
    
    # 5) Apply realistic floors to prevent impossible returns
    for i, asset in enumerate(assets):
        if asset == "crypto":
            rets[:, :, i] = np.clip(rets[:, :, i], -0.85, 3.00)
        elif asset == "stocks":
            floor = -0.70 if cfg.tail_magnitude == "extreme" else -0.60
            rets[:, :, i] = np.clip(rets[:, :, i], floor, 1.00)
        elif asset == "bonds":
            rets[:, :, i] = np.clip(rets[:, :, i], -0.25, 0.35)
        elif asset == "cds":
            rets[:, :, i] = np.clip(rets[:, :, i], -0.05, 0.10)
        else:  # cash
            rets[:, :, i] = np.clip(rets[:, :, i], -0.02, 0.08)
    
    return rets