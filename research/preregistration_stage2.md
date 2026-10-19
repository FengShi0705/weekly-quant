# Pre-registration: Stage 2 (cost-aware fine-tuning)

Written 19 Oct 2026, after Stage 1 passed its gate (`research/preregistration_stage1.md`, run 1) and
before any Stage 2 result. Code: `wq/stage2.py`, run with `research/stage2.py`. Every real-data run is
logged in `research/trials.csv`.

## What is tested

Whether fine-tuning the Stage 1 transformer on net-of-cost returns, with holdings as an input, trades
better than the Stage 1 scores pushed through today's hand-made rules (4-week smoothing and the
top-150 hold band).

## Fixed settings

- Starting point: the Stage 1 models of the 10-seed run (`run3_main_10seeds`), seeds 0–2, one per
  refit (the same quarterly schedule and 260-week windows; Stage 2 trains only on weeks whose returns
  were known by the refit date).
- `Stage2Config` defaults: 8-week rollouts, 4 per step, 300 steps (fixed, no early stopping, because
  52-week validation scores proved too noisy in Stage 1), AdamW lr 1e-4, soft top-15 temperature
  annealed from 1.0 to 0.1 on z-scored scores, risk aversion γ = 2 (annual) with ρ = 0.3, anchor 0.1 to
  the frozen Stage 1 scores, return-head ranking loss weight 0.5.
- Costs: per-stock Trading 212 buy and sell rates from `config.yaml` (FX fee, stamp duty and FTT,
  10 bps slippage); returns net of dividend tax.
- Deployed rules for the Stage 2 policy: top 15 scores within the 6-per-country cap, equal weight,
  30% drift band, £75 minimum, idle-cash top-up, real costs. **No** top-150 hold band and **no**
  score smoothing: the model sees its holdings and decides what to keep.

## Arms (same weeks, costs and dividend tax)

| Arm | |
|---|---|
| Stage 2 | the fine-tuned policy, closed loop, deployed rules |
| Stage 1 blend | 0.7 rank(Stage 1) + 0.3 rank(momentum), smoothed, today's rules (the Stage 1 winner) |
| Stage 1, deployed rules | rank(Stage 1) with no smoothing and no hold band, to show what the rules were doing |
| Incumbent | today's live strategy |

## Decision rule for moving to Stage 3

- **Pass:** Stage 2's mean weekly net return is above the Stage 1 blend's on the same weeks (any
  t-statistic; it is reported), and its maximum drawdown is no worse than −30%.
- **Fail:** otherwise. Stage 3 would then fine-tune a policy that doesn't beat the simpler rules,
  so the Stage 1 blend stays the candidate.

This gate only decides whether to continue research. It is not evidence for trading: Stage 2 cannot
be separated from the alternatives at conventional significance with 10 years of weekly data.
Adoption needs the full protocol (10 seeds, sub-periods, double costs, paper trading).

## Known limits

- Same period and universe caveats as Stage 1.
- γ = 2 is a judgement, not a calibrated value. If the Stage 2 policy's worst drop exceeds −30%, a
  higher γ is a new trial, logged as such.
