# Weekly Global Equity Strategy — Plan

## 1. Goal and constraints

| Item | Decision |
|---|---|
| Asset class | Global listed equities (US, UK, Europe, Switzerland; Nordics/Canada via IBKR) |
| Capital | 10,000 for the test phase |
| Brokers | Trading 212 or Interactive Brokers (switch in `config.yaml`) |
| Frequency | Weekly. Signal on Friday's close, orders placed by hand on Monday |
| Direction | Long-only (no shorting, no leverage, no derivatives) |
| Execution | Manual, from an order sheet the system writes each week |

## 2. Approach: an ML model at the core, news and events as features later

The core is a **cross-sectional ranking model**. Each week it scores every stock in the universe
on how likely it is to beat the others over the next week. We buy the top names.

Why not an LLM agent that reads the news and decides the trades?

- **It can't be backtested honestly.** An LLM already knows what happened after its training data
  started, so a historical test of a news-reading agent leaks the future.
- **Headline news is priced in within minutes.** A weekly strategy can't beat that.
- **Its decisions vary from run to run**, which makes them hard to audit or explain.

News and event analysis *is* useful for slower information: earnings-call tone, guidance
changes, filing language, M&A or litigation flags. It enters in Phase 4, as timestamped
numeric features that the ML model can weigh and the backtest can test.

## 3. Architecture

```
            ┌──────────────┐   prices, volume, FX (Yahoo Finance, free)
            │ wq/data.py   │── cached as parquet in data/cache/
            └──────┬───────┘
                   ▼
            ┌──────────────┐   15 price/volume features, ranked across stocks each week
            │ features.py  │── labels: next-week return rank (exec Monday → next Monday)
            └──────┬───────┘
                   ▼
            ┌──────────────┐   LightGBM, walk-forward: retrain every 4 weeks on a rolling 5 years,
            │ model.py     │── blended 70/30 with a transparent momentum baseline
            └──────┬───────┘
                   ▼
            ┌──────────────┐   top-15, hold band, country cap, regime filter,
            │ portfolio.py │── lot sizes / fractional shares, minimum trade size
            │ costs.py     │── broker commissions, FX fees, stamp duty, slippage
            └──────┬───────┘
          ┌────────┴─────────┐
          ▼                  ▼
   backtest.py          weekly.py
   (history)            (this week's orders.csv + report.md)
```

The backtest and the live run call **the same** selection, ordering and cost functions, so the
backtest simulates the rules you will actually trade.

## 4. Data

**Now (free):** Yahoo Finance via `yfinance`, with adjusted daily prices, volume and FX rates
back to 2010. No API key is needed.

Known limitations, which the plan accounts for:

1. **Survivorship bias.** The universe is *today's* large caps. A backtest from 2016 therefore
   only contains companies that went on to succeed, which flatters every strategy. To reduce this,
   always compare against the **equal-weight benchmark built from the same universe**, which
   carries the same bias. Treat the strategy's excess return over that benchmark as an upper bound.
2. **No point-in-time fundamentals.** Yahoo's fundamentals are restated and only cover a few
   years, so v1 uses price and volume features only. These are point-in-time by construction.
3. **Unofficial source.** Yahoo can change without notice or return bad prints. The pipeline drops
   single-day 100x spikes, and the order sheet always shows the reference price so you can
   sanity-check it.

**Upgrade path, when the strategy earns it:**

- Survivorship-free US data with delisted stocks: Norgate Data or Sharadar (~$30–60/month)
- Global prices and fundamentals: EODHD or FMP (~$20–80/month)
- Live quotes: IBKR market-data subscriptions, if you trade there

## 5. Features (v1)

Every feature uses data up to the signal date only, and is converted to a percentile rank across
stocks each week.

| Group | Features |
|---|---|
| Momentum | 12-1 month, 6-1 month, 3 month |
| Short-term reversal | 1 week, 1 month |
| Risk | 60-day volatility, 20/120-day volatility ratio, beta, idiosyncratic volatility, 60-day skew, max daily return (21d) |
| Trend | distance from 52-week high, distance from 200-day average |
| Liquidity / attention | log 60-day traded value, 20/120-day traded value trend |

Returns are measured in the **account's base currency**, so FX moves are part of what the
model predicts. A EUR stock that rose 5% while EUR fell 5% is flat for a USD account.

## 6. Model and validation

- **Label:** the cross-sectional rank of each stock's return from Monday's close (the assumed fill)
  to the next Monday's close. The model predicts *relative* performance, not market direction.
- **Walk-forward:** at each week T, train only on labels fully known before T. The test suite
  enforces this embargo.
- **Retraining:** every 4 weeks, on a rolling 260-week window, with at least 156 weeks of
  history before the first prediction.
- **Three variants are reported side by side:** ML only, momentum baseline only, and the blend.
  If ML can't beat the simple baseline after costs, we trade the baseline. That's a valid outcome.
- **Leak tests (in `tests/`):** on synthetic pure-noise prices the model must show no skill.
  With a planted signal it must find it. Changing future prices must not change past features.

**Metrics:** information coefficient (IC: the weekly rank correlation between score and the next
week's return) with its t-stat, CAGR, volatility, Sharpe, max drawdown, turnover, and costs as a
share of capital per year. The blend is always compared with the equal-weight benchmark.

## 7. Portfolio rules

| Rule | Default | Why |
|---|---|---|
| Positions | 15, equal weight | ~650 each at 10k. Enough to diversify, few enough to trade by hand |
| Hold band | keep a holding while it ranks in the top 45 | Cuts turnover and costs substantially |
| Country cap | max 6 per country | Avoids a US-only portfolio by accident |
| Cash buffer | 2% | Covers fees and FX |
| Minimum trade | 75 | Skips trades too small to be worth the costs |
| Drift rule | resize only if >30% off target | Fewer tiny top-ups |
| Regime filter | 50% exposure when the universe is below its 40-week average | Cuts drawdowns in bear markets |
| Lots | JP/HK board lots (100+ shares) | These markets are excluded by default because one lot can exceed a position at 10k |

## 8. Costs and broker choice at 10k

| | Trading 212 | IBKR Pro (tiered) |
|---|---|---|
| Commission | 0 | US ~$0.0035/share, min $0.35. EU ~0.05%, min ~€1.25–1.5 |
| FX | 0.15% on each trade in a non-base currency | ~0.002% (min ~$2 per conversion; hold USD/EUR balances) |
| Fractional shares | Most US/EU stocks | US and some EU |
| Universe | US, UK, major EU | Global, including Nordics, Canada, Japan and Hong Kong |
| Taxes (both) | UK stamp duty 0.5%, France FTT 0.3%, Italy 0.1%, Spain 0.2% (on buys) | same |

Rule of thumb: Trading 212 is cheaper when you trade mostly in your account's own currency.
IBKR is cheaper when you trade a lot in other currencies. Run the backtest with each
`broker` setting, since both cost models are built in. Check every number against your own
statements and update `config.yaml`.

## 9. Risk management

- **Position limits:** at most ~6.5% per name. No leverage, no shorting.
- **Regime filter:** halves exposure in broad downtrends.
- **Kill switches.** Stop trading and review if any of these happen:
  - drawdown exceeds 20% from the peak
  - live IC is negative on average over 12 consecutive weeks
  - live results trail the backtest by more than 2 standard deviations over 6 months
- **Data checks:** the order sheet shows reference prices. Don't place an order whose price looks
  wrong against the broker's quote.
- **Human in the loop:** you approve every trade.

## 10. Weekly operating routine

1. **Weekend:** run `python -m wq weekly`. It refreshes data, retrains on all realised labels,
   scores the universe and writes `reports/<date>/orders.csv` and `report.md`.
2. **Monday:** place sells first, then buys. Use limit orders a little through the quote.
   London prices are in pence.
3. **After fills:** update `holdings.csv` with the actual shares and your cash balance.
4. **Monthly:** compare live results against the backtest and check the kill switches.

## 11. Roadmap

| Phase | What | Exit criteria |
|---|---|---|
| **0. Build** (done) | Data pipeline, features, walk-forward model, cost-aware backtest, weekly order sheet, tests | Tests pass |
| **1. Real-data backtest** | Run `download` + `backtest`. Test sensitivity to `n_positions` 10/15/20, `hold_rank` 30/45/60, `ml_weight` 0/0.5/0.7/1, regime filter on/off, and both brokers | **Go** if, after costs: the blend's IC averages >0.02 with t>2, it beats the equal-weight benchmark in most rolling 1-year windows, and results hold across settings (not one lucky parameter set). Otherwise fall back to the baseline or stop |
| **2. Paper trading** | 8–12 weeks of weekly runs without money. Record what you *would* have traded and at what prices | Live IC and turnover are in line with the backtest |
| **3. Live, 10k** | Trade the order sheet weekly. Track costs and slippage against the model's estimates | Kill switches not hit. Costs close to the model's estimates |
| **4. News and event features** | Use the Claude API to score earnings-call transcripts, filings (8-K/10-Q) and news on a timestamped, point-in-time basis. Candidate features: guidance-change score, tone change versus last quarter, event flags (M&A, litigation, management change). Add them as model features and test them only on data dated *after* the scoring model's training cutoff | A feature adds IC out of sample, after the cutoff |
| **5. Better data** | Survivorship-free and point-in-time fundamental data. Add value, quality and earnings-revision factors | Improvement survives the cleaner data |
| **6. Automation** | Generate orders through the IBKR API (`ib_async`), still with human approval. Trading 212 also offers a public API: check availability for your account | Scale capital only after 6+ months of live tracking |

## 12. Honest expectations

- The edge in large-cap weekly stock selection is **small**: a good IC is 0.02–0.05. Most of the
  return comes from staying invested in equities. The model's job is to tilt toward the better names
  without losing the edge to costs.
- Backtests on today's large caps are **optimistic** (survivorship bias). Expect live results
  to be worse.
- At 10k, **costs and FX fees matter**. The hold band and minimum trade size exist for this reason.
- This is a research tool, not investment advice. Results are not guaranteed.
