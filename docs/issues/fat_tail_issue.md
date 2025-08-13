# Fat-Tail Implementation Produces Unrealistic Portfolio Failures

## Problem Summary
Our current fat-tail implementation reduces portfolio success rates by 25-30% (from ~68% to ~38%), which is far too extreme compared to industry-standard implementations like Honest Math that show 2-5% impact.

## Current Implementation Issues

### 1. Excessive Impact on Success Rates
- **Baseline scenario**: 67.65% success rate
- **With fat-tails enabled**: 38.40% success rate  
- **Actual impact**: -29.25% absolute reduction
- **Target impact**: -2% to -5% absolute reduction

### 2. Root Causes Identified

#### a) Stress Event Frequency Too High
- Currently using 10% annual probability
- Over 35 years, this compounds to excessive tail events
- Should consider 2-3% annual probability instead

#### b) Inadequate Mean Correction
- Stress events drag down expected returns
- Current 50% drift correction is insufficient
- Need full mean preservation after adding jumps

#### c) Compounding Effects
- Independent annual draws ignore mean reversion
- No consideration of market recovery after crashes
- Violates research showing annual returns are closer to normal than daily returns

### 3. Research Findings

From Kitces/academic research:
- Annual returns don't exhibit fat tails like daily returns (CLT effect)
- Monte Carlo may actually OVERSTATE retirement risk vs historical data
- Markets exhibit mean reversion over long horizons (Campbell & Shiller)
- Fat-tails should add realistic volatility, not catastrophic failures

From Honest Math documentation:
- Uses Lévy process (likely NIG or tempered stable)
- Three toggles: Magnitude, Frequency, Skewness
- "Standard" calibrated to historical U.S. markets
- Impact is subtle (2-5% on success rates)

## Proposed Solution: Implement Proper Lévy Process

### Option 1: Normal Inverse Gaussian (NIG) Process
```python
def draw_nig_returns(mu, sigma, n_years, n_sims, alpha=1.5, beta=-0.5, delta=0.02):
    """
    Normal Inverse Gaussian process for realistic fat tails
    - Preserves mean and variance exactly
    - Adds controlled skewness and kurtosis
    - Well-established in academic literature
    """
    # Implementation details...
```

### Option 2: Tempered Stable Process
Based on the included `fat_tail.md` documentation:
- Student-t diffusion body with vol-preserving scaling
- Kou double-exponential jumps (rare, small magnitude)
- Market co-jumps affecting correlated assets
- Proper mean correction and realistic floors

### Option 3: Simplified Historical Calibration
- Use normal distribution base (annual returns are approximately normal)
- Add rare stress events (2-3% annual probability)
- Stress magnitude: 3-5% additional volatility
- Include mean reversion mechanism
- Calibrate to historical S&P 500 tail statistics

## Implementation Requirements

### 1. Calibration Targets
- Annual equity returns Q05: ~-22%
- Annual equity returns Q01: ~-35%
- Success rate impact: 2-5% absolute reduction
- Preserve unconditional mean returns

### 2. User Controls (Match Honest Math)
- **Magnitude**: Standard / Extreme
- **Frequency**: Standard / High  
- **Skewness**: Negative / Neutral / Positive

### 3. Testing Requirements
- Validate against historical S&P 500 data
- Compare with Honest Math calculator results
- Ensure Black Swan events work independently
- Test across different portfolio allocations

## Acceptance Criteria

1. Fat-tails reduce success rate by 2-5% (not 25-30%)
2. Annual return distribution matches historical statistics
3. User toggles produce intuitive, graduated effects
4. Implementation is computationally efficient
5. Code is well-documented with citations

## References

- Kitces: "Monte Carlo Analysis Risk Fat Tails vs Safe Withdrawal Rates"
- Campbell & Shiller: "Valuation Ratios and Long-Run Stock Market Outlook"
- arXiv papers on NIG, tempered stable distributions
- Honest Math documentation on Lévy processes

## Next Steps

1. Create new branch: `fix/realistic-fat-tails`
2. Implement one of the proposed solutions
3. Calibrate to historical data
4. Test against known benchmarks
5. Document the mathematical approach