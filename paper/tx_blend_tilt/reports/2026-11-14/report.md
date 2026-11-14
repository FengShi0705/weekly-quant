# Weekly rebalance — signal date 2026-11-13

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **10,176.75 GBP**, cash before trades 685.95
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name                   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-----------------------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| BUY    | AAL.L    | Anglo American         | UK        |   2.2891 |           3765    | GBp         |           86.18 |           0.52 | resize   |
| BUY    | AMD      | Advanced Micro Devices | US        |   0.3031 |            534.06 | USD         |          122.34 |           0.31 | resize   |
| BUY    | BBVA.MC  | BBVA                   | ES        |  10.639  |             23.57 | EUR         |          209.42 |           0.94 | resize   |
| BUY    | CAT      | Caterpillar            | US        |   0.2016 |            600.2  | USD         |           91.45 |           0.23 | resize   |
| BUY    | LRCX     | Lam Research           | US        |   0.6458 |            225.92 | USD         |          110.27 |           0.28 | resize   |
| BUY    | MU       | Micron Technology      | US        |   0.3441 |            778.31 | USD         |          202.41 |           0.51 | resize   |

## Target portfolio

Sector mix: Tech 5, Financials 5, Industrials 2, Materials 2, Health 1 (cap 5 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | MU       | Micron Technology      | US        | Tech        |   0.471 |          0.098  |             997.32 | True   |
|      2 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.455 |          0.0933 |             949.83 | True   |
|      3 | AMD      | Advanced Micro Devices | US        | Tech        |   0.453 |          0.0887 |             902.34 | True   |
|      4 | AMAT     | Applied Materials      | US        | Tech        |   0.449 |          0.084  |             854.85 | True   |
|      5 | SAN.MC   | Banco Santander        | ES        | Financials  |   0.439 |          0.0793 |             807.36 | True   |
|      6 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.434 |          0.0747 |             759.86 | True   |
|      7 | LRCX     | Lam Research           | US        | Tech        |   0.431 |          0.07   |             712.37 | True   |
|     10 | UCG.MI   | UniCredit              | IT        | Financials  |   0.408 |          0.0653 |             664.88 | True   |
|     12 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.399 |          0.0607 |             617.39 | True   |
|     15 | ISP.MI   | Intesa Sanpaolo        | IT        | Financials  |   0.381 |          0.056  |             569.9  | True   |
|     19 | AAL.L    | Anglo American         | UK        | Materials   |   0.368 |          0.0513 |             522.41 | True   |
|     23 | IFX.DE   | Infineon               | DE        | Tech        |   0.34  |          0.0467 |             474.92 | True   |
|     26 | ANTO.L   | Antofagasta            | UK        | Materials   |   0.328 |          0.042  |             427.42 | True   |
|     30 | CAT      | Caterpillar            | US        | Industrials |   0.304 |          0.0373 |             379.93 | True   |
|     41 | BAYN.DE  | Bayer                  | DE        | Health      |   0.262 |          0.0327 |             332.44 | True   |

## What the model is leaning on (feature importance, gain)

| gain   |
|--------|

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
