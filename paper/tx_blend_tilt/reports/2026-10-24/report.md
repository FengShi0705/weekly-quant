# Weekly rebalance — signal date 2026-10-23

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **10,000.00 GBP**, cash before trades 10,000.00
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name                   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-----------------------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| BUY    | AAL.L    | Anglo American         | UK        |  11.5862 |          3625     | GBp         |          420    |           2.52 | enter    |
| BUY    | AMAT     | Applied Materials      | US        |   2.3163 |           377.24  | USD         |          653.31 |           1.63 | enter    |
| BUY    | AMD      | Advanced Micro Devices | US        |   1.9324 |           516.79  | USD         |          746.66 |           1.87 | enter    |
| BUY    | ANTO.L   | Antofagasta            | UK        |  12.3415 |          3025     | GBp         |          373.33 |           2.24 | enter    |
| BUY    | BAYN.DE  | Bayer                  | DE        |  12.586  |            44.21  | EUR         |          466.66 |           1.17 | enter    |
| BUY    | BBVA.MC  | BBVA                   | ES        |  37.6135 |            22.19  | EUR         |          700    |           3.15 | enter    |
| BUY    | CAT      | Caterpillar            | US        |   0.6359 |           687     | USD         |          326.63 |           0.82 | enter    |
| BUY    | IFX.DE   | Infineon               | DE        |  13.385  |            49.885 | EUR         |          560    |           1.4  | enter    |
| BUY    | ISP.MI   | Intesa Sanpaolo        | IT        | 171.531  |             5.839 | EUR         |          840    |           3.78 | enter    |
| BUY    | LRCX     | Lam Research           | US        |   3.5263 |           230.1   | USD         |          606.66 |           1.52 | enter    |
| BUY    | MU       | Micron Technology      | US        |   1.3513 |           877.55  | USD         |          886.61 |           2.22 | enter    |
| BUY    | RR.L     | Rolls-Royce            | UK        |  40.7536 |          1259.6   | GBp         |          513.33 |           3.08 | enter    |
| BUY    | SAN.MC   | Banco Santander        | ES        |  96.9051 |            11.484 | EUR         |          933.33 |           4.2  | enter    |
| BUY    | STAN.L   | Standard Chartered     | UK        |  40.0471 |          1981     | GBp         |          793.33 |           4.76 | enter    |
| BUY    | UCG.MI   | UniCredit              | IT        |  16.3084 |            71.65  | EUR         |          980    |           4.41 | enter    |

## Target portfolio

Sector mix: Financials 5, Tech 5, Industrials 2, Materials 2, Health 1 (cap 5 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | UCG.MI   | UniCredit              | IT        | Financials  |   0.472 |          0.098  |             980    | False  |
|      2 | SAN.MC   | Banco Santander        | ES        | Financials  |   0.472 |          0.0933 |             933.33 | False  |
|      3 | MU       | Micron Technology      | US        | Tech        |   0.462 |          0.0887 |             886.67 | False  |
|      4 | ISP.MI   | Intesa Sanpaolo        | IT        | Financials  |   0.447 |          0.084  |             840    | False  |
|      5 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.446 |          0.0793 |             793.33 | False  |
|      6 | AMD      | Advanced Micro Devices | US        | Tech        |   0.444 |          0.0747 |             746.67 | False  |
|      7 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.443 |          0.07   |             700    | False  |
|      8 | AMAT     | Applied Materials      | US        | Tech        |   0.437 |          0.0653 |             653.33 | False  |
|      9 | LRCX     | Lam Research           | US        | Tech        |   0.428 |          0.0607 |             606.67 | False  |
|     10 | IFX.DE   | Infineon               | DE        | Tech        |   0.414 |          0.056  |             560    | False  |
|     18 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.387 |          0.0513 |             513.33 | False  |
|     23 | BAYN.DE  | Bayer                  | DE        | Health      |   0.374 |          0.0467 |             466.67 | False  |
|     26 | AAL.L    | Anglo American         | UK        | Materials   |   0.359 |          0.042  |             420    | False  |
|     27 | ANTO.L   | Antofagasta            | UK        | Materials   |   0.352 |          0.0373 |             373.33 | False  |
|     28 | CAT      | Caterpillar            | US        | Industrials |   0.347 |          0.0327 |             326.67 | False  |

## What the model is leaning on (feature importance, gain)

| gain   |
|--------|

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
