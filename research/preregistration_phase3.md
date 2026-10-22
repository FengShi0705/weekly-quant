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

## Addendum, 21 Oct 2026: D, transformer labels matched to the holding period (`research/horizon_trial.py`)

Added after tests A–C, before writing D. `tx_blend` keeps a holding for about 8 months on average (about
18 swaps a year across 15 names). Its transformer is trained to rank next week's returns. Phase 1 tested
4-week labels for LightGBM only, on the tuning period, and kept 1 week; the transformer has never been
tried with longer labels.

- **Variants:** D4 and D13. The Stage 1 transformer, everything unchanged, except that the label is the
  rank of the return from the next Monday's close over 4 (D4) or 13 (D13) weeks. Seeds 0–2.
- **Purge:** a training week is used only once its label is known (t + h ≤ T − 1), and the inner
  validation block starts after the last fit week's label has ended.
- **Compared with** Stage 1 run 1 (seeds 0–2, 1-week labels).
- **Primary:** the paired weekly IC of the smoothed scores against the h-week forward return. Newey–West
  t with 2h lags, because the returns overlap.
- **Pass** if all three hold:
  - t ≥ 2.3 (two variants);
  - the 1-week IC is not significantly worse (t > −2);
  - the traded blend (0.7 transformer + 0.3 momentum, sector cap 5, today's rules) has a backtest worst
    drop no worse than −30%.
- **After a pass:** a 10-seed re-run must keep the sign (t > 1). The variant then joins paper trading.
- **Reported, not used to decide:** the backtest, and the paired weekly net-return difference against
  `tx_blend`.

Blocked, so not run: point-in-time US fundamentals from SEC XBRL (the SEC requires a contact email in
every request, which needs the account owner's consent) and Yahoo analyst rating changes (the endpoint
is refusing requests; to be retried).

## Addendum, 21 Oct 2026: E (longer training window) and F (portfolio settings for the transformer)

Added while D was running, before any D, E or F result.

**E. Ten years of training history** (`research/window_trial.py`). Stage 1 trains on the last 260 weeks,
the same window as LightGBM. With data from 2010, up to 520 weeks are available by the 2020s.
- **Change:** the Stage 1 transformer with `train_window_weeks` = 520. The window grows until it reaches
  10 years; the minimum is still 156 weeks. Nothing else changes. Seeds 0–2.
- **Primary:** paired weekly 1-week IC of the smoothed scores against Stage 1 run 1, Newey–West t (4 lags).
- **Pass** if t ≥ 2.0 and the traded blend (sector cap 5) has a backtest worst drop no worse than −30%.
- **After a pass:** a 10-seed re-run must keep the sign (t > 1).

**F. Hold band and score smoothing re-tuned for `tx_blend`** (`research/settings_trial.py`). The top-150
hold band and 4-week score average were chosen for LightGBM on Jan 2016 – Jun 2024 (PLAN.md §13). The
transformer's scores may behave differently.
- **Fixed:** the 10-seed scores, the 0.7/0.3 blend and the sector cap 5.
- **Variants:** F1 hold band 90, F2 hold band 120, F3 2-week score average, F4 8-week score average.
- **Primary:** the paired weekly net-return difference against `tx_blend` (band 150, 4 weeks),
  Newey–West t (4 lags).
- **Pass** if all three hold:
  - t ≥ 2.5 (four variants);
  - the difference is positive in each of 2016–18, 2019–21 and 2022–26;
  - the worst drop is no worse than −30%.
- **After a pass:** it joins paper trading as a `tx_blend` variant.

## Addendum, 22 Oct 2026: G, number of holdings for the transformer (`research/positions_trial.py`)

Added after tests A–F, before running G. `tx_blend` turns over about 4% a week, so its return is set by
which names it holds rather than how it trades; with the ranker at its limit, concentration is the lever
left on this data. In Phase 1b (LightGBM), ML only with 10 names beat 15 names in the tuning period
(35.9% vs 29.0%) and the holdout (20.8% vs 17.0%). `ml_only_10` is paper traded for that reason. The
transformer's equivalent has not been tested.

- **Fixed:** the 10-seed scores and today's rules. The sector cap scales with the number of holdings,
  about a third of it.
- **Variants:**
  - G1: 0.7/0.3 blend, 10 names, at most 4 per sector;
  - G2: 0.7/0.3 blend, 20 names, at most 7 per sector;
  - G3: transformer only (no momentum), 10 names, at most 4 per sector, the counterpart of `ml_only_10`.
- **Primary:** the paired weekly net-return difference against `tx_blend`, Newey–West t (4 lags).
- **Pass** if all of these hold:
  - t ≥ 2.4 (three variants);
  - the difference is positive in each of 2016–18, 2019–21 and 2022–26;
  - your limit holds: a backtest worst drop no worse than −30%, and a bootstrap chance of a drop beyond
    30% within 5 years no higher than 20% (`tx_blend`: 15%).
- **After a pass:** it joins paper trading.

## Addendum, 22 Oct 2026: H, analyst rating changes (`research/analyst_trial.py`)

Added after G, before fetching the data. Yahoo's analyst history, refused earlier, now loads. It covers US
stocks only (136 of 247), from 2012: each rating action's timestamp, firm, old and new grade, and the
old and new price target. Rating and target revisions are a documented short-horizon signal, which fits
weekly scoring. They are also new information, not derived from prices.

- **Inputs** (`wq/analyst.py`), using only actions dated at least one day before the signal date:
  - `rev_net_4w`: upgrades minus downgrades over the last 4 weeks;
  - `rev_net_13w`: the same over 13 weeks;
  - `pt_rev_4w`: the mean log change in price target over the last 4 weeks, from actions with both
    targets.
  Non-US stocks are missing, with the usual flags. Every input is ranked across stocks each week.
- **Model:** the Stage 1 transformer with these three inputs, nothing else changed. Seeds 0–2, against
  Stage 1 run 1.
- **Primary:** the paired weekly IC of the smoothed scores across all stocks, Newey–West t (4 lags).
- **Information:** the same IC on US stocks only.
- **Pass** if t ≥ 2.0 and the traded blend (sector cap 5) has a worst drop no worse than −30%.
- **After a pass:** a 10-seed re-run must keep the sign (t > 1). It then joins paper trading.

## Addendum, 22 Oct 2026: I, Wikipedia attention (`research/attention_trial.py`)

Added after H, before fetching the data. This is the last free source of new information reachable
without an account or personal contact details. Daily English Wikipedia page views per company
(Wikimedia API, human views only) exist from 1 Jul 2015. Unusual attention is a documented predictor of
short-term price pressure and reversal, mostly in smaller stocks. The prior for large caps is low.

- **Mapping:** each stock's article is found with Wikipedia search on its name and checked by hand,
  before any page views are downloaded.
- **Known limit:** renamed articles (e.g. Facebook → Meta Platforms) lose their views under the old title.
- **Inputs** (`wq/attention.py`), using views up to the day before the signal date:
  - `attn_1w`: log of the last 5 days' mean daily views over the mean of the 52 weeks before;
  - `attn_4w`: the same with the last 20 days;
  - `attn_level`: log of the mean daily views over the last 52 weeks.
  Each is missing until a stock has 52 weeks of views (so from about mid-2016), and ranked across stocks
  each week.
- **Model:** the Stage 1 transformer with these three inputs, nothing else changed. Seeds 0–2, against
  Stage 1 run 1.
- **Primary:** the paired weekly IC of the smoothed scores, all weeks, Newey–West t (4 lags).
- **Information:** the same from 2017.
- **Pass** if t ≥ 2.0 and the traded blend (sector cap 5) has a worst drop no worse than −30%.
- **After a pass:** a 10-seed re-run must keep the sign (t > 1).

**I: not run (22 Oct 2026).** Wikimedia answers every request from this environment's shared outbound
address with HTTP 429 (rate-limited), even single ones. Before the block, 16 article titles had been
found and no page views downloaded. The code (`wq/attention.py`, tested) and `research/attention_trial.py`
are ready if it can be run from another network.

## Addendum, 22 Oct 2026: J, leaning on the top picks without cutting to 10 names (`research/weights_trial.py`)

Added after G–I, before writing the code. In G, returns rose as holdings shrank (20 names 26.0%, 15
names 30.5%, 10 names 33.3%), which suggests the model's top picks carry most of the value. But 10
names raised the drop risk. These two variants keep 15 names and lean on the top in other ways. Both
keep the 10-seed `tx_blend` scores and all other rules.

- **J1, score-tilted weights:** the 15 holdings, sorted by score, get target weights falling linearly from
  1.5× to 0.5× the equal weight (the same total). Option `portfolio.weighting: score_tilt`.
- **J2, let winners run:** a kept holding above its target is not trimmed, however far it has drifted.
  Underweight holdings are still topped up as today. Option `portfolio.trim_overweight: false`.
- **Primary:** the paired weekly net-return difference against `tx_blend`, Newey–West t (4 lags).
- **Pass** if all of these hold:
  - t ≥ 2.4;
  - the difference is positive in each of 2016–18, 2019–21 and 2022–26;
  - a backtest worst drop no worse than −30%;
  - a bootstrap chance of a drop beyond 30% within 5 years of no more than 20%.

This is the last variant test on the current data. The trial count in `research/trials.csv` is the
context for any pass.
