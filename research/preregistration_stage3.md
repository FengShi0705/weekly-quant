# Pre-registration: Stage 3 (GRPO through the exact rules)

Written 20 Oct 2026, before any Stage 3 result. Stage 2 failed its gate (`research/preregistration_stage2.md`):
trained on soft weights but traded with a hard top 15, its scores near the cut-off kept swapping names
(23.8% weekly turnover). Stage 3 trains on exactly the rules it is traded with. Code: `wq/stage3.py`,
run with `research/stage3.py`; every real-data run is logged in `research/trials.csv`.

## Fixed settings

- Start: the Stage 1 models of `run3_main_10seeds`, seeds 0–2, one per quarterly refit; training uses only
  weeks whose next-week returns were known at the refit.
- Policy: masked Plackett–Luce over z-scored main-head scores / τ, τ = 0.15; 15 names, at most 6 per
  country and 5 per sector. Holdings and per-stock buy/sell costs are inputs. Dropout is off during
  GRPO, so the policy sampled and trained is the one deployed.
- Set after the pipeline smoke test (3 steps, no real result used): τ = 0.5 made sampled portfolios differ
  from the deployed top 15 by about 10 of 15 names (measured on Stage 1 scores only, no returns);
  τ = 0.15 makes it about 4. Dropout had been left on, which made the KL reading meaningless.
- Each step: 32 random training weeks, each with a starting portfolio near the Stage 1 top 15 (0–3 names
  swapped at random, weights jittered, 2–12% cash), 64 sampled portfolios per week pushed through the
  exact order rules (`stage3.construct`, tested equal to `generate_orders` + `execute`) with Trading
  212 costs. Reward = next week's net log return (dividend tax included) − γ/2 × ex-ante weekly
  variance, γ = 2, ρ = 0.3.
- Advantage: reward minus the mean of the week's other 63 samples, divided by one standard deviation
  across the batch (no per-week scaling). Loss: −advantage × log-probability + 0.05 × exact KL to the
  frozen Stage 1 policy + 0.5 × the Stage 1 ranking loss on the return head. On-policy, 100 steps,
  AdamW lr 3e-5, no early stopping.
- Deployed (and evaluated) rules: top 15 main-head scores within the country and sector caps, equal
  weight, 30% drift band, £75 minimum, idle-cash top-up, real costs; no hold band, no smoothing.

## Arms (same weeks, costs and dividend tax)

| Arm | |
|---|---|
| Stage 3 | the GRPO policy, closed loop, deployed rules |
| Stage 1 blend, seeds 0–2, sector cap 5 | same seeds as Stage 3's starting models: the like-for-like bar |
| Stage 1 blend, 10 seeds, sector cap 5 | the `tx_blend` paper candidate |
| Incumbent | today's live strategy |

## Decision rule

Stage 3 replaces `tx_blend` as the candidate only if all hold:

- its mean weekly net return beats the like-for-like Stage 1 blend with Newey–West t ≥ 1;
- its worst backtest drop is no worse than −30%;
- its bootstrap chance of a drop beyond 30% within 5 years is no higher than the `tx_blend` candidate's.

Otherwise `tx_blend` stays the candidate and the result is recorded. Either way, nothing is traded on this
run alone: a replacement candidate would join paper trading under the rules in PLAN.md §15.

## Known limits

Same period, universe and survivorship caveats as Stages 1–2. Three seeds is a development budget. τ, β,
γ and the step budget are judgement calls, not tuned; changing any is a new, logged trial.
