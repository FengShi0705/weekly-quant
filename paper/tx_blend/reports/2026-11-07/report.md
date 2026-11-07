# Weekly rebalance — signal date 2026-11-06

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,480.17 GBP**, cash before trades -1.25
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| SELL   | BAYN.DE  | Bayer  | DE        |    4.242 |             55.58 | EUR         |          196.74 |           0.49 | resize   |

## Target portfolio

Sector mix: Tech 5, Financials 5, Industrials 2, Materials 2, Health 1 (cap 5 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | MU       | Micron Technology      | US        | Tech        |   0.472 |          0.0653 |             619.37 | True   |
|      2 | AMD      | Advanced Micro Devices | US        | Tech        |   0.463 |          0.0653 |             619.37 | True   |
|      3 | AMAT     | Applied Materials      | US        | Tech        |   0.453 |          0.0653 |             619.37 | True   |
|      4 | SAN.MC   | Banco Santander        | ES        | Financials  |   0.449 |          0.0653 |             619.37 | True   |
|      5 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.448 |          0.0653 |             619.37 | True   |
|      6 | LRCX     | Lam Research           | US        | Tech        |   0.445 |          0.0653 |             619.37 | True   |
|      7 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.441 |          0.0653 |             619.37 | True   |
|      8 | UCG.MI   | UniCredit              | IT        | Financials  |   0.439 |          0.0653 |             619.37 | True   |
|     11 | ISP.MI   | Intesa Sanpaolo        | IT        | Financials  |   0.408 |          0.0653 |             619.37 | True   |
|     13 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.403 |          0.0653 |             619.37 | True   |
|     19 | IFX.DE   | Infineon               | DE        | Tech        |   0.36  |          0.0653 |             619.37 | True   |
|     22 | AAL.L    | Anglo American         | UK        | Materials   |   0.355 |          0.0653 |             619.37 | True   |
|     24 | ANTO.L   | Antofagasta            | UK        | Materials   |   0.334 |          0.0653 |             619.37 | True   |
|     27 | CAT      | Caterpillar            | US        | Industrials |   0.323 |          0.0653 |             619.37 | True   |
|     36 | BAYN.DE  | Bayer                  | DE        | Health      |   0.298 |          0.0653 |             619.37 | True   |

## What the model is leaning on (feature importance, gain)

| gain   |
|--------|

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
