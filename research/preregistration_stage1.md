# Pre-registration: Stage 1 transformer vs LightGBM

Written 19 Oct 2026, before any real-data result of the transformer. Design: `docs/GRPO transformer
portfolio design.md`. Code: `wq/deep.py`, run with `research/stage1.py`. Every run of the real-data
script appends a row to `research/trials.csv`, including failed or abandoned ones, so the number of
trials is known when results are judged.

## What is tested

A stocks-as-tokens transformer ranker (Stage 1) against the deployed LightGBM model, on identical data,
weeks, portfolio rules and costs. Stage 1 sees exactly LightGBM's inputs: the 15 ranked price/volume
features (plus missing flags) and country, sector and currency. No holdings, no extra history.

## Fixed settings (no tuning on the evaluation period)

- Data: the Yahoo cache downloaded 18 Oct 2026 (corrected London dividends), 245 stocks, Trading 212
  costs from `config.yaml` as of commit 8fd5bb8 (FR 0.4%, IT 0.2%, dividend tax).
- Evaluation weeks: every signal week from 2 Jan 2016 to the latest with a known next-week return
  (the same weeks as the LightGBM backtest).
- Model: `Stage1Config` defaults: d_model 64, 4 heads, 2 blocks, dropout 0.2, AdamW lr 3e-4, weight
  decay 1e-3, 8 weeks per batch, loss = minus weekly IC + 0.5 × ListNet (temperature 0.5).
- Training: same 260-week window as LightGBM (labels known by the signal date). Epochs chosen by IC on
  the window's last 52 weeks (after a 1-week purge), patience 5, at most 40; then retrained on all
  260 weeks for that many epochs. Refit every 13 weeks. Seeds 0, 1, 2, scores z-scored per week and
  averaged.
- Portfolio rules for every arm: the deployed ones (4-week score smoothing, 15 names, top-150 hold
  band, 6 per country, 30% drift band, £75 minimum, idle-cash top-up), with costs and dividend tax.

## Arms

| Arm | Traded score |
|---|---|
| A. Incumbent | 0.7 rank(LightGBM) + 0.3 rank(momentum baseline), smoothed (the deployed strategy) |
| B. Transformer | rank(transformer), smoothed |
| C. Transformer blend | 0.7 rank(transformer) + 0.3 rank(momentum baseline), smoothed |
| D. 50/50 | average of the ranks of A's and C's traded scores |

## Decision rule for moving to Stage 2

The primary statistic is the weekly Spearman IC of the traded (smoothed) score against next week's
return, compared with LightGBM's smoothed ML score on the same weeks. Differences use a Newey–West
t-statistic with 4 lags (smoothing makes weekly ICs overlap).

- **Pass:** the transformer's IC is not worse than LightGBM's by more than one standard error
  (paired t > −1), and the look-ahead and placebo tests in `tests/test_deep.py` pass. Stage 2 then
  starts from these Stage 1 models.
- **Fail:** paired t ≤ −1. The transformer does not rank as well as LightGBM on the same information,
  so Stages 2–3 would be built on a weaker ranker. Stop, record the result, and test only whether
  arm D adds anything.

Backtest returns (CAGR, Sharpe, maximum drawdown, net return over the equal-weight universe) are
reported for all arms but **do not decide** this gate: 10 years of weekly returns cannot separate
strategies whose returns are this correlated (see `research_notes/.../validation_overfitting.md`).
No arm is adopted for trading from this run; adoption needs the full protocol in the design report.

## Known limits

- The 2016–2026 period has been used to tune LightGBM's settings, and the 2024–2026 holdout has been
  viewed many times, so it favours the incumbent if anything.
- The universe is hand-picked and survivorship-biased (PLAN.md §4); this affects all arms alike.
- Three seeds is a development budget. A pass is re-checked with 10 seeds before any Stage 2 result
  is relied on.
