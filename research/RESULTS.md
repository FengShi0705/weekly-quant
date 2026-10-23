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
| Ranker: LightGBM + country/sector | `lgbm_cat` | t ≥ 2.5 vs LightGBM | **Fail**: IC 0.025 vs 0.019, t 1.3 (and below the transformer, t −1.5) |
| Ranker: transformer + 26-week return history | `tx_history` | t ≥ 2.5 vs Stage 1 run 1 | **Fail**: IC 0.031 vs 0.033, t −0.5 |
| Ranker: transformer + market backdrop | `tx_market` | t ≥ 2.5 vs Stage 1 run 1 | **Fail**: IC 0.032 vs 0.033, t −0.6 |
| Ranker: 50/50 transformer + LightGBM | `ensemble` | t ≥ 2.5 vs the 10-seed transformer | **Fail**: IC 0.029 vs 0.032, t −1.2 |

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
3. **The ranker is at its limit on this data.** Country and sector inputs add about 0.006 IC to either
   model, and the transformer adds about 0.007 over LightGBM with or without them. A return history,
   the market backdrop, or averaging with LightGBM added nothing. With only 245 stocks and price/volume
   inputs, further gains probably need more breadth (a larger, survivorship-free universe) or new
   information (fundamentals, news), not a different network.
4. **Backtest returns are a poor judge between variants.** Returns of the same arm moved by several
   points between runs (seeds, a UK-only data fix), while ICs were stable. Gates use IC or paired
   differences, and the candidate is judged in paper trading.

## Decisions

- `tx_blend` (Stage 1 blend with a 5-per-sector cap) is paper traded from 24 Oct 2026 next to `main`,
  under the rules in PLAN.md §15 (at least 26 weeks before any switch).
- Stages 2 and 3 are closed as specified. Reopening them needs a materially different design (for
  example multi-week rollouts from the policy's own holdings, or keeping the hold band and learning
  only its width), pre-registered as new trials.

## Phase 3: beyond the ranker (21 Oct 2026)

Pre-registered in `research/preregistration_phase3.md`. The bar is `tx_blend` (30.5% a year, Sharpe 1.34,
worst drop −26.3%, 15.1% chance of a >30% drop within 5 years), for a £10,000 Trading 212 ISA.

| Test | Gate | Result |
|---|---|---|
| A. Earnings announcements as inputs (Yahoo dates and EPS surprises) | paired IC t ≥ 2 vs Stage 1 run 1 | **Fail**: IC 0.031 vs 0.033, t −1.1 (backtest 31.2%, worst drop −27.8%) |
| B. Trade every day (same models, 20-day score average) | paired weekly return t ≥ 2 vs weekly | **Fail**: 29.4% vs 30.5%, t −0.5, worst drop −27.9% |
| B2. Trade every 4 weeks, all four starting weeks | average paired t ≥ 2, all four ahead | **Fail**: 31.9 / 29.7 / 24.9 / 29.8%, t −1.0 |
| C. Index ETFs and leveraged index trend (no stock picking) | CAGR > 30.5%, drop ≥ −30%, drop risk ≤ 15% | **Fail**: no arm passes |
| D4. Transformer trained on 4-week returns | paired 4-week IC t ≥ 2.3 vs run 1 | **Fail**: 4-week IC 0.054 vs 0.064, t −1.5 |
| D13. Transformer trained on 13-week returns | paired 13-week IC t ≥ 2.3 vs run 1 | **Fail**: 13-week IC 0.068 vs 0.102, t −2.4 |
| E. Transformer with up to 10 years of training history | paired IC t ≥ 2 vs run 1 | **Fail**: IC 0.029 vs 0.033, t −1.4, worse in 2016–19 and 2020–26 |
| F. `tx_blend` hold band 90 / 120, score average 2 / 8 weeks | paired weekly return t ≥ 2.5, ahead in all 3 sub-periods | **Fail**: best is 2-week average, +2.7 pts/yr, t 1.6, behind in 2016–18 |
| G. Holdings: 10 or 20 names (blend), 10 names (transformer only) | paired weekly return t ≥ 2.4, all 3 sub-periods, drop ≥ −30%, drop risk ≤ 20% | **Fail**: 10 names 33.3%, +2.6 pts/yr, t 1.4, ahead in all sub-periods, drop risk 20.2%; 20 names 26.0%, t −2.2 |
| H. Analyst rating and price-target changes (Yahoo, US stocks only) as transformer inputs | paired IC t ≥ 2 vs run 1 | **Fail**: IC 0.030 vs 0.033, t −1.3; US stocks alone 0.035 vs 0.037, t −0.9 |
| I. Wikipedia page views (attention) as transformer inputs | paired IC t ≥ 2 vs run 1 | **Not run**: Wikimedia rate-limits this environment's shared network address (HTTP 429 on every request) |
| J1. Score-tilted weights (best holding 1.5×, lowest 0.5× the equal weight) | paired weekly return t ≥ 2.4, all 3 sub-periods, drop ≥ −30%, drop risk ≤ 20% | **Fail (narrowly)**: 32.8% vs 30.5%, +2.1 pts/yr, t 2.23, ahead in all 3 sub-periods, worst drop −26.3%, drop risk 18% |
| J2. Let winners run (no trimming above target) | as J1 | **Fail**: 40.1% a year, t 2.16, but worst drop −37.0% and a 52% chance of a >30% drop within 5 years |
| K. Replication of J1's score tilt on LightGBM `main` | paired weekly return t ≥ 2, all 3 sub-periods, risk limits | **Replicates**: 28.4% vs 26.1%, +2.0 pts/yr, t 2.35, ahead in all 3 sub-periods, worst drop −23.4% (unchanged) |

Test C, Jan 2016 – Oct 2026, GBP, after Trading 212 costs (real funds on Trading 212):

| Arm | CAGR | Sharpe | Worst drop | Chance of a >30% drop within 5 years |
|---|---|---|---|---|
| `tx_blend` (bar) | 30.5% | 1.34 | −26.3% | 15% |
| C1 Buy & hold S&P 500 (VUSA) | 16.3% | 1.10 | −25.5% | 5% |
| C2 Dual momentum (S&P 500 / world ex-US / gilts) | 8.9% | 0.60 | −29.1% | 31% |
| C3 Multi-asset trend (five ETFs, 10-month average) | 6.7% | 1.02 | −9.9% | 0% |
| C4 S&P 500 2x, 200-day trend filter (XS2D) | 13.9% | 0.67 | −45.4% | 52% (1988–2026) |
| C5 S&P 500 3x, 200-day trend filter (3LUS) | 20.0% | 0.71 | −58.0% | 88% (1988–2026) |
| C6 S&P 500 2x, buy & hold | 25.7% | 0.90 | −58.1% | 72% |
| C7 Half `tx_blend`, half C4 | 22.6% | 1.11 | −29.7% | 27% |
| Nasdaq-100 3x trend (LQQ3; hindsight, information only) | 38.0% | 0.95 | −51.0% | 96% |

Over 1988–2026 (synthetic, USD) the 200-day filter cuts the S&P 500's worst drop from −55% to −22%, but
leverage brings it back: −47% at 2x and −62% at 3x, both in 2000–02. The synthetic series match the real
products closely over 2016–2026 (3LUS 33.8% vs 33.8% a year; XS2D 25.1% vs 26.6%).

What was learned:

1. **Earnings announcements and analyst revisions add nothing the prices don't already carry.** The reaction to the latest
   announcement, the EPS surprise and its age were available for 77% of stock-weeks (98% in the US, 26%
   in the UK). The transformer did slightly worse with them. LightGBM did slightly better (information
   only: IC 0.021 vs 0.019, t 1.3), still far below the transformer's 0.032. Post-earnings drift in
   large caps is small, and what there is is probably already carried by the 1–3 month return inputs.
   Analyst upgrades, downgrades and price-target changes (US stocks, 2012 onwards) did no better, on the
   US stocks or overall. In large caps both are fast, widely followed news, already in the price by
   the time a weekly model trades.
2. **One-week labels are the right target, even for a portfolio that holds for months.** Trained on
   4- or 13-week returns, the transformer ranked those longer returns *worse* than the model trained on
   next week's returns (13-week IC 0.068 vs 0.102). Overlapping long labels give fewer independent
   training signals, and the 4-week score average already turns weekly scores into a slower signal.
3. **Five years of training history is enough; more hurts.** With up to 10 years the transformer ranked
   worse in both halves of the period. Markets change, and older weeks dilute the recent ones.
4. **Concentration is the closest thing to an improvement, but it is not established.** Returns rise as
   holdings shrink (20 names 26.0%, 15 names 30.5%, 10 names 33.3%), and 20 names is significantly
   worse than 15 (t −2.2). That suggests the top of the ranking carries real value. But 10 names beats 15
   by only t 1.4, and its chance of a drop beyond 30% within 5 years rises to 20%.
5. **The strongest lead: weight the top picks more, within today's 15 names and risk.** Score-tilted
   weights made +2.1 points a year (t 2.23, just short of the 2.4 bar), in every sub-period, with the
   same worst drop. Letting winners run made far more (40.1% a year) only by concentrating into a few
   winners, with a −37% worst drop that breaks the 30% limit. Together with G, the evidence points one
   way: the model's top-ranked stocks carry most of the value. The tilt then replicated on LightGBM's
   `main` (test K: +2.0 points a year, t 2.35, every sub-period), so it is paper traded as
   `tx_blend_tilt`. The costs are higher (0.9% vs 0.6% a year): target weights move with the ranks.
6. **The LightGBM-era portfolio settings still suit the transformer.** A narrower hold band trades more
   (1.2–1.9% a year in costs vs 0.6%) for no reliable gain; neither a shorter nor a longer score average
   beat 4 weeks in every sub-period.
7. **Trading more often does not help.** Daily trading made the same trades a few days earlier or later,
   with the same costs (0.62% vs 0.63% a year), and 0.9 points a year less. Zero commission doesn't
   matter much here: the costs that bind are the FX fee and stamp duty, which a hold band already keeps low.
8. **Backtest CAGR is dominated by the path.** The same scores and rules, traded every 4 weeks, made
   anything from 24.9% to 31.9% a year depending only on which week the schedule started. A single
   backtest figure is worth about ±3–4 points; only paired tests separate variants.
9. **No ETF strategy competes on return without breaking the 30% drop limit.** Trend filters on
   unlevered funds cut drawdowns sharply but returned 7–10% a year in 2016–2026 (fast V-shaped recoveries
   whipsawed them). Leveraged index funds earn more only by taking drops of 45–60%. The survivorship
   bias in `tx_blend`'s backtest (its universe is today's large caps) is real, but it would have to be
   worth more than 10 points a year to change this ranking.

Decisions:

- **One change: `tx_blend_tilt` joins the simulated paper ledger from 24 Oct 2026** (K's pre-registered
  consequence). It is `tx_blend` with score-tilted weights. It does not go into the Trading 212 Practice
  account or the ISA. `main` is unchanged until its own review, where the tilt is a candidate change.
- Everything else stays: `tx_blend` stays the candidate next to `main`.
- **Exhausted with the data we have:**
  - the network and its inputs;
  - its training target and history length;
  - learned trading rules;
  - trading frequency;
  - the portfolio settings, the number of holdings and their weights;
  - free earnings and analyst data;
  - index and leveraged ETF strategies.
- **Blocked here:** Wikipedia page views (test I). The code is ready to run from another network.
- **What is left needs new data, and is your decision:**
  - a larger, survivorship-free universe with point-in-time fundamentals (paid data, roughly $20–80 a
    month), which adds breadth and value, quality and revision signals;
  - news and filings scored as features (PLAN.md §11, Phase 4), for example historical news tone from
    GDELT on Google BigQuery, which would fit the £100 research budget.
  - point-in-time US fundamentals from SEC XBRL filings (free, but the SEC requires a contact email in
    every request, so it needs your consent to use yours).

## New feature sets for the transformer (22–23 Oct 2026)

Pre-registered in `research/preregistration_features.md`. Each set was added to the Stage 1 transformer
(seeds 0–2) and compared with Stage 1 run 1 on the same weeks. Bar: paired IC t ≥ 2.4. The backtest
trades each as `tx_blend_tilt` does; the baseline is the same strategy on run 1's scores (31.7% a year).

| Set | Inputs | IC (run 1: 0.0329) | Paired t | Traded as `tx_blend_tilt`: CAGR, worst drop | Result |
|---|---|---|---|---|---|
| `peer` | stock vs sector returns (1w, 1m, 3m, 12-1m); sector and country momentum and 1-month return | 0.0330 | 0.06 | 30.1%, −24.9% | Fail |
| `shape` | information discreteness, downside beta, worst 1-year drop, distance from 1-year low, Amihud illiquidity, abnormal volume | 0.0331 | 0.10 | 27.2%, −26.1% | Fail |
| `calendar` | earnings expected next week, dividend expected within 4 weeks, 12-month dividend yield, same-month seasonality | 0.0334 | 0.22 | 26.4%, −27.4% | Fail |
| `fx` | quote currency's 1-, 3- and 12-month return against GBP | 0.0267 | −2.72 | 29.5%, −27.8% | Fail (significantly worse) |
| `all` | all 21 together | 0.0315 | −0.44 | 28.1%, −26.2% | Fail |

Why nothing helped (information only, `research/feature_diagnostics.py` → `research/results/features/diagnostics.csv`):
each new feature's own weekly IC against next week's return, and its IC against the part of the return the
current transformer score does not explain.

- **No signal:** most features have none on their own (|t| < 2): the FX, seasonality, volume, illiquidity
  and most peer inputs.
- **Some signal, largely already in the model:** a few do predict on their own, but the score already
  carries most of it. Sector momentum and dividend yield are correlated 0.34 and −0.40 with the score,
  and their IC beyond the model falls to |t| < 1.
- **Some signal beyond the score:** information discreteness (IC −0.015, t −2.8: momentum built from
  many small moves lasts longer, as published), downside beta (t 2.1) and within-sector 1-week reversal
  (t −1.9).
- **Why these don't count yet:** they were picked out of 21 after seeing the results. By chance alone
  about one in 21 would show |t| ≈ 2. And the transformer did not gain from them when given them in
  training. Using them now would be selection on this data. They are candidates for a pre-registered
  test on new data (live weeks), not a change today.
