# Pre-registration: Phase 3, looking beyond the ranker

Written 21 Oct 2026, before any of these tests has been run. The ranker trials showed that more
price-and-volume inputs or a different network add nothing (`research/RESULTS.md`). This phase tests three
different directions, each with one decision rule set now. Every run is logged in `research/trials.csv`.

The bar to beat is `tx_blend`: 0.7 transformer (10 seeds, `run3_main_10seeds`) + 0.3 momentum, today's
rules, at most 5 names per sector. Backtest Jan 2016 – Oct 2026 after Trading 212 costs and dividend tax:
30.5% a year, Sharpe 1.34, worst drop −26.3%, 15.1% bootstrap chance of a drop beyond 30% within 5 years.
All tests assume a £10,000 GBP Trading 212 Stocks & Shares ISA.

Three tests with one primary comparison each. At t ≥ 2.0 (one-sided p ≈ 0.023 each), the chance of at
least one false pass is about 7%. Passing earns a place in paper trading next to `main` and `tx_blend`;
it does not move real money (PLAN.md §15 rules apply).

## A. New information: earnings announcements (`research/earnings_trial.py`)

The only free point-in-time data not yet used. Yahoo's earnings history gives each announcement's date
and time, and the EPS surprise against the consensus estimate at the time. Coverage is patchy for UK and
Swiss companies that report half-yearly; it is reported, and missing values get the usual missing flags.

Three features per stock and signal date (`wq/earnings.py`), using only announcements whose reaction
window had closed by the signal date's close, and only if within the last 65 trading days:

- `ear`: the stock's return minus the equal-weight universe's over the three closes around the reaction
  day (the close before it, the reaction day's close and the next close). The reaction day is the
  announcement day, or the next trading day if the announcement came at or after 14:00 UTC.
- `sue`: Yahoo's EPS surprise (%), clipped to ±100 and log-scaled.
- `earn_age`: trading days since the reaction day, divided by 65.

Like every other input, they are ranked across stocks each week. The model is the Stage 1 transformer
with these three inputs added, nothing else changed: seeds 0–2, compared with Stage 1 run 1 (same seeds).

- **Primary:** the paired weekly IC difference of the smoothed scores, with Newey–West t (4 lags).
- **Pass** if t ≥ 2.0 and the traded blend (sector cap 5) has a backtest worst drop no worse than −30%.
- **After a pass:** a 10-seed re-run must keep the sign against `run3_main_10seeds` (t > 1). It then
  joins paper trading as `tx_earn`.
- **Secondary, information only:** LightGBM with the same three inputs against the deployed LightGBM.

## B. Trading every day instead of every week (`research/daily_trial.py`)

Trading 212 charges no commission, so daily trading is possible. FX fees and stamp duty still apply.

- **Models and blend:** the same saved 10-seed models (`run3_main_10seeds`), no retraining. Every trading
  day from 8 Jan 2016, features are computed at that day's close and scored by the models of the refit
  block that day falls in. The blend is 0.7 rank(transformer) + 0.3 rank(momentum), as `tx_blend`,
  averaged over the last 20 trading days (instead of the last 4 weeks).
- **Trading:** next day's close under today's rules: hold band 150, 30% drift band, £75 minimum,
  idle-cash top-up, sector cap 5.
- **Weekly comparison arm:** `tx_blend` as it is, re-run in the same script.
- **Primary:** the daily arm's account value is read on the weekly arm's Monday fill dates. The test is
  the paired difference in weekly net returns, Newey–West t (4 lags).
- **Pass** if t ≥ 2.0 and the worst drop is no worse than −30%.
- **Information only:** trading every 4 weeks (weekly scores, orders only every fourth Monday).

Caveat whatever the result: Trading 212 bans unattended algorithmic trading, so live daily orders would
need a human approval every day.

## C. Other strategy families: index ETFs and leveraged index trend (`research/etf_trial.py`)

No stock picking, so no survivorship bias: these are real funds you could have bought. All instruments
are in Trading 212's instrument list (checked through the API on 21 Oct 2026). Whether the leveraged
products can be held in the ISA (rather than the Invest account) is not confirmed and must be checked in
the app before anything is traded.

**Setup:**
- Prices are Yahoo closes in GBP (USD lines converted).
- Signals are taken at the close; trades fill at the next close.
- Costs: 0.15% FX fee on non-GBP lines; 0.10% spread and slippage on ETFs, 0.20% on leveraged products.
  ETFs pay no stamp duty.
- Cash earns the GBP overnight rate (Xtrackers XSTR).
- Window: Jan 2016 – Oct 2026.

**Strategies:**

| Arm | Rule | Instruments |
|---|---|---|
| C1 | Buy and hold the S&P 500 (reference) | VUSA |
| C2 | Dual momentum (Antonacci GEM), monthly. If the S&P 500's 12-month return beats cash, hold whichever of the S&P 500 and the world ex-US had the higher 12-month return; otherwise UK gilts | VUSA / VXUS (VEU's prices before VXUS existed) / IGLT |
| C3 | Multi-asset trend (Faber), monthly: one fifth each in US stocks, European stocks, UK property, gilts and gold, each held only while above its 10-month average, otherwise cash | VUSA, VEUR, IUKP, IGLT, SGLN |
| C4 | S&P 500 2x, held while the S&P 500 closes above its 200-day average (checked daily), otherwise cash | XS2D (USD line) |
| C5 | As C4 with 3x | 3LUS (GBX line) |
| C6 | 2x, no trend filter | XS2D |
| C7 | 50% `tx_blend` + 50% C4, rebalanced monthly | — |

C6 and C7 are information only. The Nasdaq-100 equivalents of C4 and C5 (LQQ3) are reported for
information but cannot become candidates, because choosing the Nasdaq after 2016–2026 is hindsight.

**Long-history risk check (for C4 and C5):**
- Built from the S&P 500 total-return index since 1988, in USD.
- Leveraged returns = L × daily index return − (L − 1) × the 3-month T-bill rate − the product's fee
  (0.60% for 2x, 0.75% for 3x).
- The same trend rule and costs as above.
- Before relying on it, the synthetic series is checked against the real products' prices for 2016–2026.

**A C-arm becomes a paper-trading candidate only if all of these hold:**
1. its 2016–2026 CAGR after costs beats `tx_blend`'s 30.5%;
2. its 2016–2026 worst drop is no worse than −30%;
3. its bootstrap chance of a drop beyond 30% within 5 years, on the 1988–2026 history where it exists,
   is no higher than `tx_blend`'s 15.1%.

The bootstrap is the same as `research/risk_overlays.py`: 8-week blocks, 5,000 paths.

`tx_blend`'s backtest is inflated by survivorship bias and the C-arms' are not. An arm that falls short
of 30.5% but comes within a few points with lower risk is reported as competitive, not as a candidate.

## Known limits

- **Shared data:** all three tests use 2016–2026, the period already used for every earlier trial.
- **Short-window bias:** a strong US bull market favours anything holding the S&P 500, and above all
  the leveraged arms. That is why C4/C5 need the 1988–2026 risk check (which includes 2000–02 and 2008).
- **Universe bias:** Tests A and B inherit the hand-picked universe's survivorship bias.

## Addendum, 21 Oct 2026: B2, trading every 4 weeks (`research/frequency_trial.py`)

Added after test B, before running B2. Test B's information arm (orders every fourth Monday, starting
from the first week) made 32.4% a year against weekly `tx_blend`'s 30.5%, with almost the same costs (0.58%
vs 0.63% a year). One schedule cannot separate an effect from path noise, so B2 runs all four
starting weeks. Disclosure: the first of the four is the information arm already seen.

- **Arms:** `tx_blend` scores and rules as they are. Orders are placed only every fourth week (offsets
  0, 1, 2, 3). The account is valued every week, with dividend tax charged every week as usual.
- **Primary:** each offset's weekly net return minus weekly `tx_blend`'s, averaged across the four offsets
  week by week. Newey–West t (4 lags).
- **Pass** if t ≥ 2.0, every offset's worst drop is no worse than −30%, and every offset's CAGR is above
  weekly `tx_blend`'s.
- **After a pass:** it joins paper trading as `tx_blend_4w`. Fewer order batches would also make the
  human approval of live orders easier.
- **Information only:** every 2 weeks (offsets 0, 1).
