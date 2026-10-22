# Pre-registration: new feature sets for the transformer

Written 22 Oct 2026, before any of these features has been computed on real data. Inputs tried so far:
- **Helped:** country, sector and currency information (Stage 1).
- **Added nothing:** a 26-week return history, the market backdrop, earnings reactions and surprises,
  analyst revisions.

These four sets are well-documented signal families that the model has not been given explicitly. All
are built from data already on hand (prices, volumes, currencies, dividends, earnings dates), using only
information up to each signal date.

Code: `wq/features_extra.py` (tested for no look-ahead). Runner: `research/feature_sets_trial.py --set <name>`.
Every run is logged in `research/trials.csv`.

## The sets

| Set | Inputs | Why |
|---|---|---|
| `peer` | the stock's 1-week, 1-month, 3-month and 12-1-month return minus its sector's average; its sector's average 12-1-month and 1-month return; its country's average 12-1-month and 1-month return | industry and country momentum; within-industry reversal is stronger than plain reversal |
| `shape` | information discreteness (sign of 12-1-month return × (share of down days − share of up days), Da, Gurun & Warachka); downside beta (beta on days the market fell, 1 year); worst drop over 1 year; distance above the 1-year low; Amihud illiquidity (mean of |return| / traded value, 60 days, log); abnormal volume (last 5 days' over last year's average, log) | momentum built from many small moves lasts longer; downside risk; liquidity and attention |
| `calendar` | earnings announcement expected next week (a past announcement 52 or 13 weeks earlier, ±3 days); dividend expected in the next 4 weeks (an ex-date 52 weeks earlier); trailing 12-month dividend yield; same-calendar-month seasonality (mean return in the coming month over the previous 5 years) | earnings-announcement premium; dividend-month premium; dividend yield as a value signal; return seasonality (Heston & Sadka) |
| `fx` | the stock's quote currency's return against GBP over 1, 3 and 12 months | currency momentum, which matters for GBP returns on foreign stocks |
| `all` | all of the above together | the sets may each add a little |

As before, every input is ranked across stocks each week, and missing values (for example no earnings
dates) get missing flags.

## Test

- **Model:** the Stage 1 transformer with the set's inputs added, nothing else changed. Seeds 0–2.
- **Compared with** Stage 1 run 1 (same seeds).
- **Primary:** the paired weekly IC of the smoothed scores, Newey–West t (4 lags).
- **Pass** if all three hold:
  - t ≥ 2.4 (five variants; one-sided p ≈ 0.008 each);
  - the traded strategy has a backtest worst drop no worse than −30%;
  - its chance of a drop beyond 30% within 5 years is no more than 20%.
- **Traded strategy:** the current best, `tx_blend_tilt` (0.7 transformer + 0.3 momentum, at most 5 per
  sector, score-tilted weights, today's rules and Trading 212 costs).
- **Reported, not used to decide:** the backtest, and the paired weekly net-return difference against the
  same strategy on Stage 1 run 1's scores.
- **After a pass:** a 10-seed re-run must keep the sign (t > 1). The new inputs then go into a paper
  strategy next to `tx_blend_tilt` (simulated only).

If several sets pass, the one with the highest t is re-run first. Backtest returns do not decide.
