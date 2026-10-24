# Weekly rebalance — signal date 2026-10-23

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **10,000.00 GBP**, cash before trades 10,000.00
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name                   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-----------------------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| BUY    | AAL.L    | Anglo American         | UK        |  18.0229 |          3625     | GBp         |          653.33 |           3.92 | enter    |
| BUY    | AMAT     | Applied Materials      | US        |   2.3163 |           377.24  | USD         |          653.31 |           1.63 | enter    |
| BUY    | AMD      | Advanced Micro Devices | US        |   1.6908 |           516.79  | USD         |          653.31 |           1.63 | enter    |
| BUY    | ANTO.L   | Antofagasta            | UK        |  21.5977 |          3025     | GBp         |          653.33 |           3.92 | enter    |
| BUY    | BAYN.DE  | Bayer                  | DE        |  17.6204 |            44.21  | EUR         |          653.33 |           1.63 | enter    |
| BUY    | BBVA.MC  | BBVA                   | ES        |  35.1059 |            22.19  | EUR         |          653.33 |           2.94 | enter    |
| BUY    | CAT      | Caterpillar            | US        |   1.2719 |           687     | USD         |          653.31 |           1.63 | enter    |
| BUY    | IFX.DE   | Infineon               | DE        |  15.6159 |            49.885 | EUR         |          653.33 |           1.63 | enter    |
| BUY    | ISP.MI   | Intesa Sanpaolo        | IT        | 133.413  |             5.839 | EUR         |          653.33 |           2.94 | enter    |
| BUY    | LRCX     | Lam Research           | US        |   3.7975 |           230.1   | USD         |          653.32 |           1.63 | enter    |
| BUY    | MU       | Micron Technology      | US        |   0.9957 |           877.55  | USD         |          653.3  |           1.63 | enter    |
| BUY    | RR.L     | Rolls-Royce            | UK        |  51.8683 |          1259.6   | GBp         |          653.33 |           3.92 | enter    |
| BUY    | SAN.MC   | Banco Santander        | ES        |  67.8335 |            11.484 | EUR         |          653.33 |           2.94 | enter    |
| BUY    | STAN.L   | Standard Chartered     | UK        |  32.9799 |          1981     | GBp         |          653.33 |           3.92 | enter    |
| BUY    | UCG.MI   | UniCredit              | IT        |  10.8723 |            71.65  | EUR         |          653.33 |           2.94 | enter    |

## Target portfolio

Sector mix: Financials 5, Tech 5, Industrials 2, Materials 2, Health 1 (cap 5 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | UCG.MI   | UniCredit              | IT        | Financials  |   0.472 |          0.0653 |             653.33 | False  |
|      2 | SAN.MC   | Banco Santander        | ES        | Financials  |   0.472 |          0.0653 |             653.33 | False  |
|      3 | MU       | Micron Technology      | US        | Tech        |   0.462 |          0.0653 |             653.33 | False  |
|      4 | ISP.MI   | Intesa Sanpaolo        | IT        | Financials  |   0.447 |          0.0653 |             653.33 | False  |
|      5 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.446 |          0.0653 |             653.33 | False  |
|      6 | AMD      | Advanced Micro Devices | US        | Tech        |   0.444 |          0.0653 |             653.33 | False  |
|      7 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.443 |          0.0653 |             653.33 | False  |
|      8 | AMAT     | Applied Materials      | US        | Tech        |   0.437 |          0.0653 |             653.33 | False  |
|      9 | LRCX     | Lam Research           | US        | Tech        |   0.428 |          0.0653 |             653.33 | False  |
|     10 | IFX.DE   | Infineon               | DE        | Tech        |   0.414 |          0.0653 |             653.33 | False  |
|     18 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.387 |          0.0653 |             653.33 | False  |
|     23 | BAYN.DE  | Bayer                  | DE        | Health      |   0.374 |          0.0653 |             653.33 | False  |
|     26 | AAL.L    | Anglo American         | UK        | Materials   |   0.359 |          0.0653 |             653.33 | False  |
|     27 | ANTO.L   | Antofagasta            | UK        | Materials   |   0.352 |          0.0653 |             653.33 | False  |
|     28 | CAT      | Caterpillar            | US        | Industrials |   0.347 |          0.0653 |             653.33 | False  |

## What the model is leaning on (feature importance, gain)

| gain   |
|--------|

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
