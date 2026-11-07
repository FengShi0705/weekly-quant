# Weekly rebalance — signal date 2026-11-06

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,235.61 GBP**, cash before trades 112.10
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| SELL   | BAYN.DE  | Bayer  | DE        |   4.3837 |             55.58 | EUR         |          203.31 |           0.51 | resize   |

## Target portfolio

Sector mix: Tech 7, Financials 6, Health 1, Industrials 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | PANW     | Palo Alto Networks     | US        | Tech        |   0.474 |          0.0653 |             603.39 | True   |
|      2 | AMAT     | Applied Materials      | US        | Tech        |   0.455 |          0.0653 |             603.39 | True   |
|      3 | BAYN.DE  | Bayer                  | DE        | Health      |   0.449 |          0.0653 |             603.39 | True   |
|      4 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.428 |          0.0653 |             603.39 | True   |
|      6 | LRCX     | Lam Research           | US        | Tech        |   0.421 |          0.0653 |             603.39 | True   |
|      8 | INGA.AS  | ING Group              | NL        | Financials  |   0.414 |          0.0653 |             603.39 | True   |
|      9 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.406 |          0.0653 |             603.39 | True   |
|     13 | BNP.PA   | BNP Paribas            | FR        | Financials  |   0.384 |          0.0653 |             603.39 | True   |
|     14 | IFX.DE   | Infineon               | DE        | Tech        |   0.374 |          0.0653 |             603.39 | True   |
|     17 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.341 |          0.0653 |             603.39 | True   |
|     19 | UBSG.SW  | UBS Group              | CH        | Financials  |   0.328 |          0.0653 |             603.39 | True   |
|     27 | TXN      | Texas Instruments      | US        | Tech        |   0.306 |          0.0653 |             603.39 | True   |
|     34 | MU       | Micron Technology      | US        | Tech        |   0.274 |          0.0653 |             603.39 | True   |
|     45 | AMD      | Advanced Micro Devices | US        | Tech        |   0.219 |          0.0653 |             603.39 | True   |
|     59 | BARC.L   | Barclays               | UK        | Financials  |   0.168 |          0.0653 |             603.39 | True   |

## What the model is leaning on (feature importance, gain)

| gain   |
|--------|

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
