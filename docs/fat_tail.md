# ============================
# FAT-TAIL ENGINE (drop-in)
# ============================
# Usage:
# rets = draw_fat_tailed_returns(
#     mu=mu_vec,                 # (n_assets,) annual arithmetic expected returns
#     chol=chol_cov,             # (n_assets,n_assets) Cholesky of annual covariance (arithmetic)
#     assets=["stocks","bonds","crypto","cds","cash"],
#     n_years=35,
#     n_sims=10_000,
#     cfg=FatTailConfig()        # tweak params/toggles below
# )
# Returns shape: (n_years, n_sims, n_assets) in *arithmetic* return space.

from dataclasses import dataclass, field
from typing import Dict, Sequence, Optional
import numpy as np

# -----------------------------
# Configuration dataclasses
# -----------------------------
@dataclass
class KouParams:
    lam: float      # annual Poisson intensity (frequency)
    p_pos: float    # probability a jump is positive
    eta_pos: float  # mean *positive* jump size on arithmetic RETURN scale (e.g., 0.06 -> +6%)
    eta_neg: float  # mean *negative* jump size on arithmetic RETURN scale (applied as -Exp(mean=eta_neg))

@dataclass
class MarketJump:
    lam: float = 0.50
    p_pos: float = 0.35
    eta_pos: float = 0.05
    eta_neg: float = 0.10
    affected_assets: Sequence[str] = ("stocks", "crypto")  # who gets full market jump
    bond_beta: float = 0.20                                # fraction of market jump applied to bonds

@dataclass
class FatTailConfig:
    enabled: bool = True
    # Diffusion body (fat-ish) — Student-t df; set very large (e.g., 1e6) to approximate normal
    t_df: float = 5.0
    # Toggles: "standard"/"extreme" for magnitude, "standard"/"high" for frequency, skew: "negative"/"neutral"/"positive"
    tail_magnitude: str = "standard"
    tail_frequency: str = "standard"
    tail_skew: str = "neutral"
    # Per-asset Kou jump settings (baseline = "Standard U.S. history" ballpark; calibrate to taste)
    per_asset: Dict[str, KouParams] = field(default_factory=lambda: {
        "stocks": KouParams(lam=0.80, p_pos=0.35, eta_pos=0.06, eta_neg=0.12),
        "bonds":  KouParams(lam=0.10, p_pos=0.50, eta_pos=0.02, eta_neg=0.03),
        "crypto": KouParams(lam=1.80, p_pos=0.40, eta_pos=0.20, eta_neg=0.25),
        "cds":    KouParams(lam=0.00, p_pos=0.50, eta_pos=0.00, eta_neg=0.00),
        "cash":   KouParams(lam=0.00, p_pos=0.50, eta_pos=0.00, eta_neg=0.00),
    })
    market: MarketJump = field(default_factory=MarketJump)
    seed: Optional[int] = None

# -----------------------------
# Core generators
# -----------------------------
def _student_t_correlated(years: int, sims: int, n_assets: int, chol: np.ndarray, df: float, rng: np.random.Generator) -> np.ndarray:
    """
    Returns a (years, sims, n_assets) array of *zero-mean* correlated Student-t shocks.
    'chol' is the Cholesky of the annual *arithmetic* covariance matrix.
    """
    Z = rng.standard_t(df, size=(years * sims, n_assets))  # i.i.d. t
    C = Z @ chol.T                                         # correlate (on flat)
    return C.reshape(years, sims, n_assets)                # reshape to (Y,S,A)

def _double_exponential_jump(n: int, p_pos: float, eta_pos: float, eta_neg: float, rng: np.random.Generator) -> np.ndarray:
    """
    Draw n jump sizes from an asymmetric Laplace (double-exponential) on *arithmetic return* scale.
    Positive jumps: +Exp(mean=eta_pos); Negative: -Exp(mean=eta_neg).
    """
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

def _apply_toggles_to_params(per_asset: Dict[str, KouParams], market: MarketJump,
                             magnitude: str, frequency: str, skew_mode: str) -> Dict[str, KouParams]:
    mag_mult = 1.6 if magnitude == "extreme" else 1.0
    freq_mult = 2.0 if frequency == "high" else 1.0
    skew_shift = {"negative": -0.10, "neutral": 0.0, "positive": +0.10}.get(skew_mode, 0.0)

    out = {}
    for name, p in per_asset.items():
        out[name] = KouParams(
            lam = p.lam * freq_mult,
            p_pos = float(np.clip(p.p_pos + skew_shift, 0.05, 0.95)),
            eta_pos = p.eta_pos * mag_mult,
            eta_neg = p.eta_neg * mag_mult,
        )
    # mutate market in-place effect via return too
    market.p_pos = float(np.clip(market.p_pos + skew_shift, 0.05, 0.95))
    market.lam   = market.lam * freq_mult
    market.eta_pos *= mag_mult
    market.eta_neg *= mag_mult
    return out

# -----------------------------
# Public API
# -----------------------------
def draw_fat_tailed_returns(
    mu: np.ndarray,             # (A,) annual arithmetic expected returns by asset
    chol: np.ndarray,           # (A,A) Cholesky of annual arithmetic covariance (matches assets order)
    assets: Sequence[str],      # list/tuple of asset names aligned to mu/chol
    n_years: int,
    n_sims: int,
    cfg: FatTailConfig,
) -> np.ndarray:
    """
    Heavy-tail generator: correlated Student-t diffusion + Kou double-exponential jumps.
    - Adds a *market* jump for co-movement (applies to specified assets; bonds get a fraction via bond_beta).
    - Adds *idiosyncratic* jumps per-asset.
    Returns arithmetic returns with shape (n_years, n_sims, n_assets).
    """
    rng = np.random.default_rng(cfg.seed)
    assets = list(assets)
    A = len(assets)

    # 1) Body: correlated Student-t shocks around zero; then add mu
    df = cfg.t_df if cfg.enabled else 1e9  # ~normal when disabled
    body = _student_t_correlated(n_years, n_sims, A, chol, df, rng)  # zero-mean shocks
    rets = body + mu.reshape(1, 1, A)  # broadcast mu into (Y,S,A)

    if not cfg.enabled:
        return rets  # pure (approx) normal/t diffusion

    # 2) Prepare jump params with toggles
    pmap = _apply_toggles_to_params(
        per_asset=dict(cfg.per_asset),           # copy
        market=cfg.market,                       # modifies skew/freq/mag on market too
        magnitude=cfg.tail_magnitude,
        frequency=cfg.tail_frequency,
        skew_mode=cfg.tail_skew,
    )
    # quick index helpers
    idx = {a:i for i,a in enumerate(assets)}
    affected_idx = [idx[a] for a in cfg.market.affected_assets if a in idx]
    bond_i = idx.get("bonds", None)

    # Flatten year/sim to vector for fast Poisson & bincount
    YS = n_years * n_sims

    # 3) MARKET JUMPS (co-jumps)
    if cfg.market.lam > 0:
        m_counts = rng.poisson(lam=cfg.market.lam, size=YS)               # number of market jumps per (year,sim)
        total_m = int(m_counts.sum())
        if total_m > 0:
            m_sizes = _double_exponential_jump(total_m, cfg.market.p_pos, cfg.market.eta_pos, cfg.market.eta_neg, rng)
            # accumulate to each (year,sim)
            m_bins = np.bincount(np.repeat(np.arange(YS), m_counts), weights=m_sizes, minlength=YS)
            m_bins = m_bins.reshape(n_years, n_sims)  # shape (Y,S)

            # apply to chosen assets fully
            if affected_idx:
                for j in affected_idx:
                    rets[:, :, j] += m_bins

            # bonds get fraction (optional)
            if bond_i is not None and cfg.market.bond_beta != 0:
                rets[:, :, bond_i] += cfg.market.bond_beta * m_bins

    # 4) IDIOSYNCRATIC JUMPS (per asset)
    for a_name, p in pmap.items():
        j = idx.get(a_name, None)
        if j is None or p.lam <= 0:
            continue
        counts = rng.poisson(lam=p.lam, size=YS)
        total = int(counts.sum())
        if total == 0:
            continue
        sizes = _double_exponential_jump(total, p.p_pos, p.eta_pos, p.eta_neg, rng)
        bins = np.bincount(np.repeat(np.arange(YS), counts), weights=sizes, minlength=YS)
        rets[:, :, j] += bins.reshape(n_years, n_sims)

    return rets

# -----------------------------
# Mini sanity test (optional)
# -----------------------------
if __name__ == "__main__":
    # Example shapes/inputs
    assets = ["stocks","bonds","crypto","cds","cash"]
    A = len(assets)
    mu = np.array([0.08, 0.03, 0.18, 0.045, 0.02])  # nominal annual means (arithmetic)
    # toy covariance for demo (vols: 17%, 6%, 70%, 1%, 0.5%; rho: simple)
    vols = np.array([0.17, 0.06, 0.70, 0.01, 0.005])
    corr = np.array([
        [1.00, -0.20,  0.35, 0.00, 0.00],
        [-0.20, 1.00, -0.05, 0.00, 0.00],
        [0.35, -0.05,  1.00, 0.00, 0.00],
        [0.00,  0.00,  0.00, 1.00, 0.10],
        [0.00,  0.00,  0.00, 0.10, 1.00],
    ])
    cov = np.outer(vols, vols) * corr
    chol = np.linalg.cholesky(cov)

    cfg = FatTailConfig(
        enabled=True,
        t_df=5,
        tail_magnitude="standard",   # "standard" or "extreme"
        tail_frequency="standard",   # "standard" or "high"
        tail_skew="negative",        # "negative" | "neutral" | "positive"
        seed=42
    )

    R = draw_fat_tailed_returns(mu, chol, assets, n_years=35, n_sims=50_000, cfg=cfg)
    # quick sanity: print 1y equity left-tail quantiles
    stocks = R[:, :, assets.index("stocks")].ravel()
    q05, q01 = np.quantile(stocks, [0.05, 0.01])
    print("Stocks Q05/Q01:", round(q05,3), round(q01,3))

Notes
Arithmetic space: this sits directly on your annual arithmetic returns (fits retirement cash-flow modeling cleanly). If your chol is on log returns, switch the diffusion block to log, add jumps in log space, then convert with np.exp(logr)-1.
Toggles map exactly to your product language:
Magnitude: eta_pos/eta_neg × 1.6 when “extreme”.
Frequency: λ × 2 when “high”.
Skew: p_pos ± 0.10 (clipped to [0.05, 0.95]).
Market co-jumps: equity assets share the same shock each (year,sim); bonds get a small fraction (bond_beta) to reflect occasional correlation spikes in crises.
Start with the provided baselines; when you finish calibration, overwrite per_asset and market values with your fitted parameters.

Totally—here’s the idea behind that fat-tail block, in plain English and just enough math to be useful.

# What problem it solves

Retirement sims need **annual, multi-asset returns** that

* keep your target **mean/vol/correlation**,
* but also show **fat tails** (more big up/downs than a normal),
* with controllable **frequency**, **magnitude**, and **skew** of tail events,
* and rare **co-crashes** across risky assets.

# How it does that (high level)

Each year & simulation, per asset:

1. Draw a **correlated “diffusion” shock** (body of the distribution) using a **Student-t** instead of a normal → naturally fatter body than Gaussian.
2. Add **jumps** from a **Kou double-exponential** process:

   * a **market jump** shared across chosen assets (e.g., stocks & crypto), and a small fraction to bonds (co-movement in crises),
   * plus **idiosyncratic jumps** per asset.
3. Add the asset’s **expected return** (mu).
   Result: an **arithmetic return** array shaped `(years, sims, assets)`.

# The moving parts

### 1) Correlated diffusion (Student-t)

```python
_student_t_correlated(..., chol, df)
```

* We sample independent Student-t shocks and multiply by **Cholesky** of the **annual covariance** to impose your correlation/vol structure.
* `df` controls how “fat” the body is (lower df → fatter). Setting `df≈1e6` ≈ normal.

**Tip:** a standard t has variance `df/(df-2)`. If you want the **unconditional vol** to match your covariance exactly, scale the t-shocks by `sqrt((df-2)/df)` (or compute chol for that scale). The snippet keeps it simple; you can add that scale if desired.

### 2) Jumps (fat tails)

**Kou jump process** = Poisson number of jumps each year; **jump sizes** are **double-exponential** (a.k.a. asymmetric Laplace):

* Positive jump: `+Exp(mean=eta_pos)`
* Negative jump: `−Exp(mean=eta_neg)`
* **Skew** is controlled by `p_pos` (prob of positive) and the asymmetry between `eta_pos` and `eta_neg`.

We use two jump layers:

* **Market jumps**: same jump amount hits all “affected” assets that year (stocks, crypto), and a fraction hits bonds via `bond_beta`.
* **Idiosyncratic jumps**: per-asset, drawn independently.

This creates realistic **co-crashes** and **left-tail heaviness** without killing speed.

### 3) Toggles → model knobs

* **Magnitude** (“standard” / “extreme”): multiply `eta_pos` & `eta_neg` (e.g., ×1.6).
* **Frequency** (“standard” / “high”): multiply Poisson intensity `λ` (e.g., ×2).
* **Skew** (“negative” / “neutral” / “positive”): shift `p_pos` by ±0.10 (clamped to \[0.05, 0.95]).
  These map directly to your product wording.

### 4) Per-asset baselines (calibrate later)

```python
"stocks": KouParams(lam=0.80, p_pos=0.35, eta_pos=0.06, eta_neg=0.12),
"bonds" : KouParams(lam=0.10, p_pos=0.50, eta_pos=0.02, eta_neg=0.03),
"crypto": KouParams(lam=1.80, p_pos=0.40, eta_pos=0.20, eta_neg=0.25),
```

These are **starting points**. After you calibrate to history (your separate step), drop in your fitted numbers.

# Data shapes & integration

* **Inputs**

  * `mu`: `(A,)` annual **arithmetic** expected returns by asset
  * `chol`: `(A,A)` **Cholesky** of the annual **arithmetic** covariance (matching asset order)
  * `assets`: names aligned to `mu/chol` (e.g., `["stocks","bonds","crypto","cds","cash"]`)
  * `n_years`, `n_sims`, `cfg` (fat-tail settings)
* **Output**

  * `(years, sims, assets)` array of **arithmetic** returns in **nominal** terms — ready to feed into your cash-flow engine.

# Why arithmetic space?

For retirement planning you typically project **balances** year-over-year. Working in arithmetic return space lets you sum shocks & jumps and then apply directly to balances. You *can* do this in log space (add everything in logs, then `exp−1`), but keep it consistent across your whole pipeline.

# Practical notes / gotchas

* **Student-t variance** (important): if you keep `df=5`, diffusion variance is larger than normal. Either (a) accept that as part of fat-tail “body”, or (b) scale t-shocks to preserve your target covariance (see tip above).
* **Mean control**: jumps add to the unconditional mean. If you must hit a precise overall mean (e.g., 8%), you may adjust `mu` downward slightly during calibration so `mu + E[jumps]` matches target.
* **Side effect**: `_apply_toggles_to_params` mutates `cfg.market` (so repeated calls reuse adjusted values). If you call this generator multiple times with the same `cfg`, consider passing a copy or re-instantiating `cfg` to avoid cumulative changes.
* **Bonds in crises**: `bond_beta=0.20` means bonds catch 20% of market jump. You can set `0.0` to avoid, or even negative to reflect flight-to-quality on bad equity years.

# How to calibrate it (quick recipe)

1. Choose targets (annual): mean, σ, **Q05/Q01**, **ES5%**, skew, kurtosis.
2. Grid/random search over `λ, p_pos, eta_pos, eta_neg, df` to minimize weighted error to those targets (you already have this plan).
3. Store the winning params as your **“Standard”** pack.
4. Your toggles (“Extreme/High/Skew”) are deterministic transforms of that pack.

# Tiny “what happens if…” intuition

* **Frequency ↑** (`λ×2`): same average jump size, **more** jumps → tails get heavier and multi-year sequences worsen.
* **Magnitude ↑** (`η×1.6`): same count of jumps, **bigger** jumps → fatter tails and deeper drawdowns.
* **Skew negative** (`p_pos−=0.10` and typically `eta_neg > eta_pos`): more/larger **down** jumps → worse left tail & sequence risk (what you want to stress).

If you want, I can tweak two details in the code:

* add the **t-variance scaling** so your unconditional covariance matches exactly even with t-shocks, and
* stop in-place mutation of `cfg.market` so repeated calls are pure.
