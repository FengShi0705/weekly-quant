# Research log: transformer and RL stages

Design: `docs/GRPO transformer portfolio design.md`. Every real-data run is in `research/trials.csv`.
Universe: the 245 hand-picked stocks tradable on Trading 212 (survivorship-biased, PLAN.md §4),
weekly signals Jan 2016 – Oct 2026, Trading 212 costs and dividend tax, £10,000.

## Results

| Stage | Run | Pre-registered gate | Result |
|---|---|---|---|
| 1. Transformer ranker (stocks as tokens, IC + ListNet loss) | run 1, 3 seeds | IC not worse than LightGBM (paired t > −1) | **Pass**: IC 0.033 vs 0.019, t +2.2 |
| 1. ablation: no country/sector/currency | run 2 | (information) | IC 0.026: about half the gain is the architecture, half the category inputs |
| 1. re-check | run 3, 10 seeds | as run 1 | **Pass**: IC 0.032 vs 0.019, t +2.2; ahead in 8 of 11 years and in the 2024–26 holdout |
| 2. Cost-aware fine-tuning, soft 8-week rollouts | run 1, 3 seeds | net return above the Stage 1 blend, worst drop ≥ −30% | **Fail**: same net return, 23.8% weekly turnover, worst drop −31.6% |
| 3. GRPO through the exact rules | run 1, 3 seeds | beat the Stage 1 blend with t ≥ 1, worst drop ≥ −30%, drop risk no higher | **Fail**: 21.1% CAGR, 45.6% weekly turnover, worst drop −33.3%, t −2.2 |
| Risk controls on the Stage 1 blend | 4 variants | (exploratory) | 5-per-sector cap: 30.5%, Sharpe 1.34, chance of a >30% drop in 5 years 15.1% (19.5% without) |

Backtest of the arms that matter (2016–2026, after costs and dividend tax):

| | CAGR | Sharpe | Worst drop | Weekly turnover | Chance of a >30% drop within 5 years |
|---|---|---|---|---|---|
| Current strategy (LightGBM blend, `main`) | 26.1% | 1.26 | −23.5% | 5.7% | 13% |
| **Stage 1 blend, 5-per-sector cap (`tx_blend`)** | **30.5%** | **1.34** | −26.3% | 3.8% | 15% |
| Stage 2 policy | 28.6% | 1.13 | −31.6% | 23.8% | — |
| Stage 3 (GRPO) policy | 21.1% | 0.95 | −33.3% | 45.6% | 42% |

## What was learned

1. **The transformer ranks better than LightGBM** on the same weeks (IC 0.032 vs 0.019). Half of that
   comes from country and sector information LightGBM never had, half from attention across stocks and
   the ranking loss. This is the only stage that added value.
2. **Learning when to trade failed twice.** Both RL-style stages were meant to replace the hand-made
   hold band and score smoothing (which cut costs from 7.7% to 0.8% a year) with a learned,
   cost-aware rule. Neither learned to keep holdings:
   - Stage 2 learned on smooth weights but traded a hard top 15, so names near the cut-off flipped.
   - Stage 3 trained on the exact rules but its one-week reward is too weak: a swap costs about 0.03% of
     the account, against about 0.3% of weekly noise per holding, and its training portfolios were fresh
     near-top-15 sets rather than the policy's own aging holdings. Its behaviour stayed close to the
     Stage 1 scores with no hold band (46% vs 42% weekly turnover).
   This matches the design report's prior: for a £10k account that cannot move prices, a policy gradient
   mostly re-estimates noisily what simple rules already do.
3. **Backtest returns are a poor judge between variants.** Returns of the same arm moved by several
   points between runs (seeds, a UK-only data fix), while ICs were stable. Gates use IC or paired
   differences, and the candidate is judged in paper trading.

## Decisions

- `tx_blend` (Stage 1 blend with a 5-per-sector cap) is paper traded from 24 Oct 2026 next to `main`,
  under the rules in PLAN.md §15 (at least 26 weeks before any switch).
- Stages 2 and 3 are closed as specified. Reopening them needs a materially different design (for
  example multi-week rollouts from the policy's own holdings, or keeping the hold band and learning
  only its width), pre-registered as new trials.
