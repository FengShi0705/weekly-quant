# Pre-registration: ranker improvements

Written 20 Oct 2026, before any of these variants has been run. The Stage 1 transformer is the only
stage that added value (`research/RESULTS.md`); these trials try to improve the ranker. Run with
`research/ranker_variants.py --variant <name>`; every run is logged in `research/trials.csv`.

## Variants (four, decided now)

| Variant | Change | Compared with (same weeks, paired) |
|---|---|---|
| `lgbm_cat` | LightGBM given country and sector as categorical features (otherwise the deployed model, weekly retraining, 5 seeds) | the deployed LightGBM; also the transformer (10 seeds) |
| `tx_history` | Stage 1 transformer plus each stock's last 26 weekly returns (z-scored across stocks per week) | Stage 1 run 1 (same seeds 0–2, same settings) |
| `tx_market` | Stage 1 transformer plus the market backdrop on every token: equal-weight index return over 4, 12, 52 weeks, its 60-day volatility, last week's cross-sectional return spread | Stage 1 run 1 (seeds 0–2) |
| `ensemble` | 0.5 rank(transformer, 10 seeds) + 0.5 rank(LightGBM), both smoothed as traded | the transformer (10 seeds) |

All Stage 1 settings are otherwise unchanged. The extra inputs use only prices up to the signal date
(tested in `tests/test_pipeline.py`).

## Decision rules

The statistic is the paired difference in weekly Spearman IC of the smoothed (traded) scores, with a
Newey–West t-statistic (4 lags). Four variants are tested, so the bar is t ≥ 2.5 rather than 2.

- `tx_history` / `tx_market`: replaces the `tx_blend` ranker if t ≥ 2.5 against run 1 and its traded
  blend (5-per-sector cap) keeps its backtest worst drop no worse than −30%. A replacement is re-run
  with 10 seeds before going live, and joins paper trading under PLAN.md §15.
- `ensemble`: replaces the `tx_blend` score if t ≥ 2.5 against the 10-seed transformer.
- `lgbm_cat`: if t ≥ 2.5 against the deployed LightGBM, it becomes the change proposed for `main` at
  its paper-trading review (not before). Separately, if its IC is not below the transformer's (paired
  t > 0), that is recorded as evidence that the transformer's gain comes from the category inputs.

Backtest returns are reported but do not decide.
