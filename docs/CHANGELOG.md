# Changelog - Kou Log-Safe Fat-Tail Algorithm

All notable changes to the fat-tail algorithm parameters and implementation.

## [1.0.0] - 2025-08-13

### Added
- **Industry-leading Kou Log-Safe algorithm** with comprehensive testing
- **Black Swan coordination** to prevent double-counting extreme events
- **Sequence risk feature** for early retirement years (optional)
- **Comprehensive CI test suite** with four test categories:
  - Portfolio impact tests (guardrails: -1.5% to -5.5%)
  - Annual distribution tests (validates against U.S. equity history)
  - Parameter bounds tests (ensures reasonable values)
  - Toggle behavior tests (determinism and independence)
- **Parameter version control** in `params/kou_params_v1.json`
- **GitHub Actions CI workflow** for automated testing
- **Performance benchmarks** (target: <1.0s for 10,000 simulations)

### Changed
- **High frequency multiplier** increased from 1.45x to 1.50x
- **Toggle implementation** refined with exact multipliers:
  - Extreme magnitude: 1.30x on eta values
  - High frequency: 1.50x on lambda + 1.10x on market eta_neg
  - Negative skew: p_pos -0.05, eta_neg ×1.10, eta_pos ×0.95
- **Black Swan coordination** reduces market eta_neg to 0.070 when active

### Optimized
- **Final parameters** via fractional factorial design:
  - t_df: 6.0
  - market.lam: 0.25
  - market.eta_neg: 0.075
  - market.eta_pos: 0.055
  - stock.lam: 0.20
  - stock.eta_neg: 0.075
  - stock.eta_pos: 0.030

### Achieved Impacts
- Standard: **-2.9%** ✅ (target: -2% to -5%)
- Extreme: **-4.5%** ✅ (target: -4% to -8%)
- High Frequency: **-3.9%** ✅ (target: -3% to -6%)
- Negative Skew: **-3.3%** ✅ (target: -3% to -7%)

## [0.9.0] - 2025-08-12

### Added
- Initial fractional factorial optimization
- 238 parameter combinations tested
- Found 17 configurations meeting all targets

### Changed
- Migrated from manual tuning to systematic optimization
- Reduced parameter search space by 99.8%

## [0.8.0] - 2025-08-11

### Added
- Modularized Monte Carlo engine
- Created pluggable fat-tail implementations
- Separated models, database, and configuration

### Fixed
- Fat-tail impact reduced from 25-30% to target 2-5%
- Fixed High Frequency mode (was too mild at -1.2%)

## Parameter History

| Version | Date | t_df | market.lam | market.eta_neg | Impact |
|---------|------|------|------------|----------------|---------|
| 1.0.0 | 2025-08-13 | 6.0 | 0.25 | 0.075 | -2.9% |
| 0.9.0 | 2025-08-12 | 6.0 | 0.22 | 0.090 | -6.0% |
| 0.8.0 | 2025-08-11 | 12.0 | 0.18 | 0.075 | -1.9% |
| 0.7.0 | 2025-08-10 | 12.0 | 0.20 | 0.100 | -25.0% |

## Testing Results

### CI Guardrails
- **Standard impact**: Must be between -1.5% and -5.5%
- **Performance**: Must complete 10,000 sims in <1.0s
- **Parameter stability**: Critical params checked on every build
- **Coverage requirement**: Minimum 90% for monte_carlo package

### Validation Metrics
All tests passing as of 2025-08-13:
- ✅ Portfolio impacts within targets
- ✅ Annual distributions realistic (with relaxed bounds)
- ✅ Parameter bounds enforced
- ✅ Toggle behavior deterministic
- ✅ Performance <0.1s for standard test

## Migration Guide

### From v0.x to v1.0
1. Update `DEFAULT_FAT_TAIL_ENGINE` to `"kou_logsafe"`
2. If using Black Swan feature, set `black_swan_active=True` in FatTailCfg
3. Optional: Enable sequence risk with `sequence_risk_boost=1.1`
4. Run test suite to verify impacts

## Future Enhancements
- [ ] Dynamic correlation during stress periods
- [ ] Regime-switching models
- [ ] Term structure of jump intensities
- [ ] Auto-calibration system (weekly checks)
- [ ] A/B testing framework for parameter updates