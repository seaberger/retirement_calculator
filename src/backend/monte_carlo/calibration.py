"""
Calibration tools for fine-tuning fat-tail parameters.
Targets U.S. equity historical data (50-100 years).
"""

import numpy as np
from typing import Dict, Callable, Optional, Tuple, Any
from dataclasses import dataclass
import copy


@dataclass
class HistoricalTargets:
    """Target bands based on U.S. equity historical data (annual returns)."""
    mean_low: float = 0.075      # 7.5% nominal lower bound
    mean_high: float = 0.090     # 9.0% nominal upper bound
    std_low: float = 0.15        # 15% volatility lower bound
    std_high: float = 0.20       # 20% volatility upper bound
    skew_low: float = -0.7       # Left skew lower bound
    skew_high: float = -0.3      # Left skew upper bound
    excess_kurt_low: float = 3.0  # Excess kurtosis lower bound
    excess_kurt_high: float = 7.0 # Excess kurtosis upper bound
    q05_low: float = -0.28       # 5th percentile lower bound
    q05_high: float = -0.22      # 5th percentile upper bound
    q01_low: float = -0.45       # 1st percentile lower bound
    q01_high: float = -0.35      # 1st percentile upper bound
    es05_low: float = -0.36      # Expected shortfall (5%) lower bound
    es05_high: float = -0.30      # Expected shortfall (5%) upper bound
    
    # Note: Extreme black swan events (-37% in 2008, -34% COVID) are handled
    # by the separate Black Swan feature, not the fat-tail algorithm


def compute_distribution_metrics(returns: np.ndarray) -> Dict[str, float]:
    """
    Compute key distribution metrics for annual returns.
    
    Args:
        returns: Array of annual returns (decimal format)
    
    Returns:
        Dictionary with mean, std, skew, kurtosis, quantiles, and ES
    """
    from scipy import stats
    
    mean = np.mean(returns)
    std = np.std(returns)
    skew = stats.skew(returns)
    excess_kurt = stats.kurtosis(returns)  # Already excess kurtosis in scipy
    
    q05 = np.percentile(returns, 5)
    q01 = np.percentile(returns, 1)
    q10 = np.percentile(returns, 10)
    q25 = np.percentile(returns, 25)
    q50 = np.percentile(returns, 50)
    q75 = np.percentile(returns, 75)
    q90 = np.percentile(returns, 90)
    q95 = np.percentile(returns, 95)
    q99 = np.percentile(returns, 99)
    
    # Expected shortfall (conditional value at risk)
    es05 = np.mean(returns[returns <= q05]) if np.any(returns <= q05) else q05
    es01 = np.mean(returns[returns <= q01]) if np.any(returns <= q01) else q01
    
    return {
        "mean": mean,
        "std": std,
        "skew": skew,
        "excess_kurt": excess_kurt,
        "q01": q01,
        "q05": q05,
        "q10": q10,
        "q25": q25,
        "q50": q50,
        "q75": q75,
        "q90": q90,
        "q95": q95,
        "q99": q99,
        "es01": es01,
        "es05": es05,
    }


def validate_against_targets(
    metrics: Dict[str, float],
    targets: HistoricalTargets = HistoricalTargets()
) -> Dict[str, Dict[str, Any]]:
    """
    Validate distribution metrics against historical targets.
    
    Returns:
        Dictionary with pass/fail status and details for each metric
    """
    results = {}
    
    # Check each metric against targets
    checks = [
        ("mean", metrics["mean"], targets.mean_low, targets.mean_high),
        ("std", metrics["std"], targets.std_low, targets.std_high),
        ("skew", metrics["skew"], targets.skew_low, targets.skew_high),
        ("excess_kurt", metrics["excess_kurt"], targets.excess_kurt_low, targets.excess_kurt_high),
        ("q05", metrics["q05"], targets.q05_low, targets.q05_high),
        ("q01", metrics["q01"], targets.q01_low, targets.q01_high),
        ("es05", metrics["es05"], targets.es05_low, targets.es05_high),
    ]
    
    for name, value, low, high in checks:
        in_range = low <= value <= high
        results[name] = {
            "value": value,
            "target_range": (low, high),
            "in_range": in_range,
            "status": "✅" if in_range else "❌",
            "deviation": 0 if in_range else min(abs(value - low), abs(value - high))
        }
    
    # Overall validation
    all_pass = all(r["in_range"] for r in results.values())
    results["overall"] = {
        "all_pass": all_pass,
        "status": "✅ All metrics within historical ranges" if all_pass else "❌ Some metrics out of range",
        "pass_count": sum(1 for r in results.values() if r.get("in_range", False)),
        "total_checks": len(checks)
    }
    
    return results


def fit_tail_scales(
    sim_fn: Callable,
    base_cfg: Any,
    targets: Dict[str, float],
    assets_idx: int = 0,
    tries: int = 20,
    sims: int = 150_000
) -> Dict[str, float]:
    """
    Find optimal magnitude and frequency scales to match tail targets.
    
    Args:
        sim_fn: Function that takes (cfg) and returns (years, sims, assets) returns
        base_cfg: Base configuration object
        targets: Dict with 'q05', 'q01', 'es05' targets for equities
        assets_idx: Index of stocks in asset array
        tries: Number of random tries
        sims: Number of simulations per try
    
    Returns:
        Dictionary with best scale_mag, scale_freq, and error
    """
    rng = np.random.default_rng(42)
    best = {"error": float('inf'), "scale_mag": 1.0, "scale_freq": 1.0}
    
    for _ in range(tries):
        # Explore scaling factors
        scale_mag = rng.uniform(0.9, 1.3)
        scale_freq = rng.uniform(0.9, 1.5)
        
        # Apply scales to config
        cfg = copy.deepcopy(base_cfg)
        
        # Scale market jumps
        cfg.market.eta_neg *= scale_mag
        cfg.market.eta_pos *= scale_mag
        cfg.market.lam *= scale_freq
        
        # Scale per-asset jumps
        for asset_params in cfg.per_asset.values():
            asset_params.eta_neg *= scale_mag
            asset_params.eta_pos *= scale_mag
            asset_params.lam *= scale_freq
        
        # Run simulation for one year
        returns = sim_fn(cfg, n_years=1, n_sims=sims)
        
        # Extract stock returns
        stock_returns = returns[0, :, assets_idx]
        
        # Compute metrics
        q05 = np.percentile(stock_returns, 5)
        q01 = np.percentile(stock_returns, 1)
        es05 = np.mean(stock_returns[stock_returns <= q05]) if np.any(stock_returns <= q05) else q05
        
        # Compute error
        error = 0
        if "q05" in targets:
            error += abs(q05 - targets["q05"]) / max(1e-9, abs(targets["q05"]))
        if "q01" in targets:
            error += abs(q01 - targets["q01"]) / max(1e-9, abs(targets["q01"]))
        if "es05" in targets:
            error += abs(es05 - targets["es05"]) / max(1e-9, abs(targets["es05"]))
        
        if error < best["error"]:
            best = {
                "error": error,
                "scale_mag": scale_mag,
                "scale_freq": scale_freq,
                "q05": q05,
                "q01": q01,
                "es05": es05
            }
    
    return best


def compute_sequence_risk(
    returns: np.ndarray,
    years: int = 3,
    threshold: float = -0.30
) -> float:
    """
    Compute probability of cumulative returns below threshold over N years.
    
    Args:
        returns: Array of shape (n_years, n_sims) with annual returns
        years: Number of consecutive years to consider
        threshold: Cumulative return threshold (e.g., -0.30 for 30% loss)
    
    Returns:
        Probability of N-year cumulative return <= threshold
    """
    if returns.shape[0] < years:
        raise ValueError(f"Need at least {years} years of data")
    
    n_sims = returns.shape[1]
    n_windows = returns.shape[0] - years + 1
    
    # Calculate rolling N-year cumulative returns
    bad_sequences = 0
    for start in range(n_windows):
        window = returns[start:start + years, :]
        # Cumulative return: (1+r1)*(1+r2)*...*(1+rN) - 1
        cum_returns = np.prod(1 + window, axis=0) - 1
        bad_sequences += np.sum(cum_returns <= threshold)
    
    return bad_sequences / (n_windows * n_sims)


def generate_calibration_report(
    sim_fn: Callable,
    cfg: Any,
    assets_idx: int = 0,
    n_years: int = 30,
    n_sims: int = 100_000
) -> str:
    """
    Generate a comprehensive calibration report for current parameters.
    
    Args:
        sim_fn: Function that returns (years, sims, assets) returns
        cfg: Configuration object
        assets_idx: Index of stocks in asset array
        n_years: Number of years to simulate
        n_sims: Number of simulations
    
    Returns:
        Formatted report string
    """
    # Run simulation
    returns = sim_fn(cfg, n_years=n_years, n_sims=n_sims)
    stock_returns = returns[:, :, assets_idx]
    
    # Compute annual metrics (first year for distribution)
    annual_returns = stock_returns[0, :]
    metrics = compute_distribution_metrics(annual_returns)
    
    # Validate against targets
    validation = validate_against_targets(metrics)
    
    # Compute sequence risk
    seq_risk_3yr = compute_sequence_risk(stock_returns, years=3, threshold=-0.30)
    seq_risk_5yr = compute_sequence_risk(stock_returns, years=5, threshold=-0.40)
    
    # Generate report
    report = []
    report.append("=" * 70)
    report.append("FAT-TAIL CALIBRATION REPORT")
    report.append("=" * 70)
    report.append("")
    
    report.append("ANNUAL RETURN DISTRIBUTION (Stocks)")
    report.append("-" * 40)
    report.append(f"Mean:           {metrics['mean']*100:6.2f}%  Target: [7.5%, 9.0%]  {validation['mean']['status']}")
    report.append(f"Std Dev:        {metrics['std']*100:6.2f}%  Target: [15%, 20%]    {validation['std']['status']}")
    report.append(f"Skewness:       {metrics['skew']:6.3f}   Target: [-0.7, -0.3]  {validation['skew']['status']}")
    report.append(f"Excess Kurt:    {metrics['excess_kurt']:6.2f}   Target: [3, 7]        {validation['excess_kurt']['status']}")
    report.append("")
    
    report.append("TAIL RISK METRICS")
    report.append("-" * 40)
    report.append(f"Q01 (1st %ile): {metrics['q01']*100:6.2f}%  Target: [-45%, -35%]  {validation['q01']['status']}")
    report.append(f"Q05 (5th %ile): {metrics['q05']*100:6.2f}%  Target: [-28%, -22%]  {validation['q05']['status']}")
    report.append(f"ES 5% (CVaR):   {metrics['es05']*100:6.2f}%  Target: [-36%, -30%]  {validation['es05']['status']}")
    report.append("")
    
    report.append("SEQUENCE RISK")
    report.append("-" * 40)
    report.append(f"P(3-yr ≤ -30%): {seq_risk_3yr*100:6.2f}%  Target: [8%, 15%]")
    report.append(f"P(5-yr ≤ -40%): {seq_risk_5yr*100:6.2f}%  Target: [3%, 8%]")
    report.append("")
    
    report.append("PERCENTILE DISTRIBUTION")
    report.append("-" * 40)
    for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        key = f"q{p:02d}"
        if key in metrics:
            report.append(f"P{p:02d}: {metrics[key]*100:7.2f}%")
    report.append("")
    
    report.append("VALIDATION SUMMARY")
    report.append("-" * 40)
    report.append(validation["overall"]["status"])
    report.append(f"Metrics in range: {validation['overall']['pass_count']}/{validation['overall']['total_checks']}")
    
    return "\n".join(report)