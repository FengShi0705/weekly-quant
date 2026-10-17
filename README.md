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
python -m wq backtest    # walk-forward backtest -> reports/backtest/ (summary.json, equity.png, trades)
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

## Caveats

The universe is today's large caps, so backtests carry survivorship bias. Compare against the
equal-weight benchmark of the same universe, which is reported automatically. Yahoo Finance is
free but unofficial: check reference prices against your broker before trading. This is a research
tool, not investment advice.
