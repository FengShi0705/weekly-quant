# weekly-quant

A weekly, long-only, global equity strategy for a small account (10k) traded by hand on
Trading 212 or Interactive Brokers. A LightGBM ranking model, blended with a momentum baseline,
scores ~290 large caps each weekend. You get an order sheet to place on Monday.

See **[PLAN.md](PLAN.md)** for the full design, the validation rules and the roadmap.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp holdings.example.csv holdings.csv     # your positions + cash (kept out of git)
```

Edit `config.yaml`: set `base_currency` (USD/GBP/EUR), `capital` and `broker` (`t212` or `ibkr`).

## Use

```bash
python -m wq download    # ~2-5 min: prices, volume, FX from Yahoo Finance into data/cache/
python -m wq backtest    # walk-forward backtest vs buy & hold and monthly investing in index funds
                         #   -> reports/backtest/ (summary.json, equity.png, dca.png, trades)
python -m wq weekly      # refresh data, score this week -> reports/<date>/orders.csv + report.md
python -m pytest         # mechanics and leak tests on synthetic data
```

### Weekly routine

1. Weekend: `python -m wq weekly`
2. Monday: place the orders in `reports/<date>/orders.csv` (sells first). London prices are in pence.
3. After fills: update `holdings.csv` with actual shares and cash:

```csv
ticker,shares
AAPL,3.2154
SAP.DE,2.5
CASH,412.50
```

## Paper trading

`python -m wq paper` advances every strategy in `paper/strategies.yaml` by one week. It fills last week's
orders at the Monday close, records account value next to buy & hold of index funds, and plans this
week's orders. State and weekly order sheets are kept in `paper/<strategy>/`, and `paper/summary.md`
compares the strategies. A scheduled cloud run does this every Saturday.
A strategy with `model: {type: transformer}` is scored by the transformer models in `paper/models/tx/` (needs PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cpu`).

`python -m wq t212 [--execute]` trades the main strategy in a **Trading 212 Practice** account through
Trading 212's API. It can only reach the Practice (demo) server and is a dry run unless you pass
`--execute`. Each week it plans orders from the account's real positions and cash with the strategy's
rules. It never copies the simulated ledger, so after a rejected order the two can hold different stocks.
It also writes `paper/t212_practice/comparison.md`: real
fill prices and fees next to the cost model, the account's value next to the simulated ledger's, and the
holdings that differ between the two.
`--retry-rejected` resends only the latest week's orders that Trading 212 rejected (for example for lack of
free cash before the sells filled). Credentials: Practice API keys stored as a network secret on the cloud environment for
`demo.trading212.com` (type Username and password: username = API key, password = API secret), or as the
`T212_API_KEY` and `T212_API_SECRET` environment variables.
Unmapped tickers can be fixed in `paper/t212_overrides.yaml` (`yahoo_ticker: T212_TICKER`).

## Layout

| Path | Purpose |
|---|---|
| `config.yaml` | every setting and cost assumption |
| `universe/global_large_caps.csv` | tradable stocks: Yahoo ticker, country, currency, lot size, brokers |
| `wq/data.py` | download, cache, currency conversion |
| `wq/features.py` | weekly calendar, point-in-time features, labels |
| `wq/model.py` | walk-forward LightGBM, momentum baseline, IC |
| `wq/portfolio.py`, `wq/costs.py` | selection rules, order generation, broker costs |
| `wq/backtest.py` | historical simulation with the live rules |
| `wq/weekly.py` | this week's order sheet and report |
| `wq/paper.py`, `wq/t212.py` | paper-trading ledger and Trading 212 Practice mirror |
| `paper/` | paper-trading state, weekly order sheets and summary |

## Caveats

The universe is today's large caps, so backtests carry survivorship bias. Compare against the
equal-weight benchmark of the same universe, which is reported automatically. Yahoo Finance is
free but unofficial: check reference prices against your broker before trading. This is a research
tool, not investment advice.
