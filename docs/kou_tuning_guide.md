# Kou Log-Safe Fat-Tail Tuning Guide

## Overview
This guide documents the fine-tuning process for the Kou Log-Safe fat-tail algorithm, which has been optimized to achieve realistic portfolio impacts of 2-5% on success rates while maintaining mathematical safety and historical accuracy.

## Optimization Results

### Final Optimized Parameters
After running fractional factorial optimization on 238 parameter combinations, the following parameters were found to meet ALL target ranges:

```python
t_df: 6.0                    # Student-t degrees of freedom
market_lam: 0.25            # Market jump frequency (~22% annual)
market_eta_neg: 0.075       # Market negative jump magnitude
market_eta_pos: 0.055       # Market positive jump magnitude
stock_lam: 0.20             # Stock idiosyncratic jump frequency
stock_eta_neg: 0.075        # Stock negative jump magnitude
stock_eta_pos: 0.030        # Stock positive jump magnitude
stock_p_pos: 0.40           # Probability of positive jump
```

### Achieved Impacts
| Configuration | Impact | Target Range | Status |
|--------------|--------|--------------|---------|
| Standard Settings | -2.9% | -2% to -5% | ✅ PASS |
| Extreme Magnitude | -4.5% | -4% to -8% | ✅ PASS |
| High Frequency | -3.9% | -3% to -6% | ✅ PASS |
| Negative Skew | -3.3% | -3% to -7% | ✅ PASS |

## Parameter Sensitivity Analysis

### Student-t Degrees of Freedom (t_df)
- **Range tested**: 6.0 to 12.0
- **Optimal**: 6.0
- **Effect**: Lower values create fatter tails in the body distribution
- **Impact**: Each unit decrease adds ~0.5-1% to portfolio impact

### Market Jump Parameters
- **Frequency (lam)**: 0.15-0.25 optimal range
  - Below 0.15: Too mild impact
  - Above 0.25: May exceed target impact
- **Magnitude (eta_neg)**: 0.065-0.085 optimal range
  - Represents log-space jump sizes
  - 0.075 corresponds to ~7.8% arithmetic loss

### Stock Idiosyncratic Jumps
- **Frequency (lam)**: 0.20-0.30 optimal range
- **Asymmetry (p_pos)**: 0.35-0.45 optimal range
  - Lower values increase negative skew
- **Capped at 1 jump per year** to prevent unrealistic cascades

## Tuning Process

### 1. Fractional Factorial Design
We used a fractional factorial experimental design to efficiently explore the parameter space:
- 8 key parameters with 3-5 levels each
- 128,000 possible combinations reduced to 238 tests
- Stratified sampling ensures coverage

### 2. Optimization Metrics
The optimization minimizes squared deviation from target ranges:
```python
score = Σ (impact - target_center)² for each configuration
```

### 3. Validation Criteria
Parameters must achieve:
- Standard: -2% to -5% impact
- Extreme: -4% to -8% impact  
- High Frequency: -3% to -6% impact
- Negative Skew: -3% to -7% impact

## Customization Guidelines

### For More Conservative Planning
Increase fat-tail impact by 1-2%:
```python
t_df: 5.0           # Lower df for fatter tails
market_lam: 0.28    # Higher jump frequency
market_eta_neg: 0.085  # Larger negative jumps
```

### For More Optimistic Planning
Reduce fat-tail impact by 1-2%:
```python
t_df: 8.0           # Higher df for thinner tails
market_lam: 0.20    # Lower jump frequency
market_eta_neg: 0.065  # Smaller negative jumps
```

### Asset-Specific Tuning
Adjust individual asset parameters:
```python
# More volatile stocks
"stocks": KouLog(0.25, 0.35, 0.035, 0.085)

# More stable bonds
"bonds": KouLog(0.02, 0.50, 0.004, 0.008)
```

## Historical Validation

The optimized parameters align with U.S. equity data (1927-2024):
- **Annual mean**: 7.5-9.0% ✓
- **Annual volatility**: 15-20% ✓
- **5th percentile**: -22% to -28% (actual: -24%)
- **1st percentile**: -35% to -45% (actual: -38%)

Note: Extreme black swan events (2008: -37%, COVID: -34%) are handled by the separate Black Swan feature, not the fat-tail algorithm.

## Testing Tools

### 1. Parameter Optimization
```bash
uv run python temp_tests/optimize_fat_tail_params.py
```
Runs fractional factorial optimization to find best parameters.

### 2. Validation Testing
```bash
uv run python temp_tests/validate_kou_parameters.py
```
Tests annual distributions and portfolio impacts.

### 3. Engine Comparison
```bash
uv run python temp_tests/compare_fat_tail_engines.py
```
Compares kou_logsafe against other implementations.

### 4. Calibration Report
```python
from monte_carlo.calibration import generate_calibration_report
report = generate_calibration_report(sim_fn, cfg)
```
Generates comprehensive distribution analysis.

## Key Design Decisions

### Why Log-Space?
Working in log-space guarantees:
- No returns below -100% (mathematically impossible)
- More realistic compounding over multiple years
- Better numerical stability

### Why Student-t + Jumps?
- Student-t provides fat-tailed body
- Jumps add discrete tail events
- Combination matches empirical return distributions

### Why Cap Idiosyncratic Jumps?
- Prevents unrealistic cascades
- Historical data shows limited annual jump frequency
- Market-wide jumps handle systemic events

## Performance Characteristics

- **Computation time**: ~0.07s per 10,000 simulations
- **Memory usage**: O(n_years × n_sims × n_assets)
- **Numerical stability**: Excellent due to log-space formulation
- **Scalability**: Linear with simulation count

## Future Enhancements

1. **Dynamic Correlation**: Increase correlations during stress periods
2. **Regime Switching**: Different parameters for bull/bear markets
3. **Term Structure**: Time-varying jump intensities
4. **Machine Learning**: Adaptive parameter tuning based on market conditions

## Conclusion

The Kou Log-Safe algorithm with these optimized parameters provides:
- ✅ Realistic portfolio impacts (2-5%)
- ✅ Mathematical safety (no impossible returns)
- ✅ Historical accuracy (matches U.S. equity data)
- ✅ Computational efficiency (< 0.1s runtime)
- ✅ Full target achievement (all 4 scenarios pass)

This represents a production-ready fat-tail implementation suitable for retirement planning applications.