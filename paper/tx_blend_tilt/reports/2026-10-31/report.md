# Weekly rebalance — signal date 2026-10-30

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,787.96 GBP**, cash before trades 0.95
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name            | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:----------------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| SELL   | ISP.MI   | Intesa Sanpaolo | IT        |  50.8996 |             5.889 | EUR         |          250.55 |           0.63 | resize   |

## Target portfolio

Sector mix: Tech 5, Financials 5, Industrials 2, Materials 2, Health 1 (cap 5 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | MU       | Micron Technology      | US        | Tech        |   0.467 |          0.098  |             959.22 | True   |
|      2 | UCG.MI   | UniCredit              | IT        | Financials  |   0.464 |          0.0933 |             913.54 | True   |
|      3 | SAN.MC   | Banco Santander        | ES        | Financials  |   0.462 |          0.0887 |             867.87 | True   |
|      4 | AMD      | Advanced Micro Devices | US        | Tech        |   0.453 |          0.084  |             822.19 | True   |
|      5 | AMAT     | Applied Materials      | US        | Tech        |   0.451 |          0.0793 |             776.51 | True   |
|      6 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.449 |          0.0747 |             730.83 | True   |
|      7 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.447 |          0.07   |             685.16 | True   |
|      8 | LRCX     | Lam Research           | US        | Tech        |   0.444 |          0.0653 |             639.48 | True   |
|      9 | ISP.MI   | Intesa Sanpaolo        | IT        | Financials  |   0.438 |          0.0607 |             593.8  | True   |
|     15 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.397 |          0.056  |             548.13 | True   |
|     17 | IFX.DE   | Infineon               | DE        | Tech        |   0.392 |          0.0513 |             502.45 | True   |
|     22 | BAYN.DE  | Bayer                  | DE        | Health      |   0.363 |          0.0467 |             456.77 | True   |
|     23 | AAL.L    | Anglo American         | UK        | Materials   |   0.356 |          0.042  |             411.09 | True   |
|     28 | ANTO.L   | Antofagasta            | UK        | Materials   |   0.343 |          0.0373 |             365.42 | True   |
|     29 | CAT      | Caterpillar            | US        | Industrials |   0.34  |          0.0327 |             319.74 | True   |

## What the model is leaning on (feature importance, gain)

| gain   |
|--------|

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
