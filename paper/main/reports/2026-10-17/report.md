# Weekly rebalance — signal date 2026-10-16

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **10,000.00 GBP**, cash before trades 10,000.00
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name                   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-----------------------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| BUY    | AMAT     | Applied Materials      | US        |   2.1187 |            409.29 | USD         |          653.32 |           1.63 | enter    |
| BUY    | AMD      | Advanced Micro Devices | US        |   1.64   |            528.75 | USD         |          653.31 |           1.63 | enter    |
| BUY    | BARC.L   | Barclays               | UK        | 151.007  |            432.65 | GBp         |          653.33 |           3.92 | enter    |
| BUY    | BAYN.DE  | Bayer                  | DE        |  17.3945 |             44.46 | EUR         |          653.33 |           1.63 | enter    |
| BUY    | BBVA.MC  | BBVA                   | ES        |  33.3632 |             23.18 | EUR         |          653.33 |           2.94 | enter    |
| BUY    | BNP.PA   | BNP Paribas            | FR        |   8.636  |             89.55 | EUR         |          653.33 |           3.59 | enter    |
| BUY    | IFX.DE   | Infineon               | DE        |  14.7615 |             52.39 | EUR         |          653.33 |           1.63 | enter    |
| BUY    | INGA.AS  | ING Group              | NL        |  25.7272 |             30.06 | EUR         |          653.33 |           1.63 | enter    |
| BUY    | LRCX     | Lam Research           | US        |   3.2855 |            263.94 | USD         |          653.33 |           1.63 | enter    |
| BUY    | MU       | Micron Technology      | US        |   0.9867 |            878.84 | USD         |          653.31 |           1.63 | enter    |
| BUY    | PANW     | Palo Alto Networks     | US        |   2.5356 |            342    | USD         |          653.33 |           1.63 | enter    |
| BUY    | RR.L     | Rolls-Royce            | UK        |  48.3735 |           1350.6  | GBp         |          653.33 |           3.92 | enter    |
| BUY    | STAN.L   | Standard Chartered     | UK        |  30.7161 |           2127    | GBp         |          653.33 |           3.92 | enter    |
| BUY    | TXN      | Texas Instruments      | US        |   3.1365 |            276.48 | USD         |          653.33 |           1.63 | enter    |
| BUY    | UBSG.SW  | UBS Group              | CH        |  18.0221 |             39.63 | CHF         |          653.33 |           1.63 | enter    |

## Target portfolio

Sector mix: Tech 7, Financials 6, Health 1, Industrials 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | MU       | Micron Technology      | US        | Tech        |   0.476 |          0.0653 |             653.33 | False  |
|      2 | AMD      | Advanced Micro Devices | US        | Tech        |   0.462 |          0.0653 |             653.33 | False  |
|      3 | BAYN.DE  | Bayer                  | DE        | Health      |   0.459 |          0.0653 |             653.33 | False  |
|      4 | LRCX     | Lam Research           | US        | Tech        |   0.441 |          0.0653 |             653.33 | False  |
|      5 | AMAT     | Applied Materials      | US        | Tech        |   0.433 |          0.0653 |             653.33 | False  |
|      6 | IFX.DE   | Infineon               | DE        | Tech        |   0.432 |          0.0653 |             653.33 | False  |
|      7 | INGA.AS  | ING Group              | NL        | Financials  |   0.427 |          0.0653 |             653.33 | False  |
|      8 | PANW     | Palo Alto Networks     | US        | Tech        |   0.419 |          0.0653 |             653.33 | False  |
|      9 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.415 |          0.0653 |             653.33 | False  |
|     10 | TXN      | Texas Instruments      | US        | Tech        |   0.414 |          0.0653 |             653.33 | False  |
|     11 | UBSG.SW  | UBS Group              | CH        | Financials  |   0.406 |          0.0653 |             653.33 | False  |
|     14 | BNP.PA   | BNP Paribas            | FR        | Financials  |   0.382 |          0.0653 |             653.33 | False  |
|     15 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.38  |          0.0653 |             653.33 | False  |
|     18 | BARC.L   | Barclays               | UK        | Financials  |   0.371 |          0.0653 |             653.33 | False  |
|     19 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.371 |          0.0653 |             653.33 | False  |

## What the model is leaning on (feature importance, gain)

|            |   gain |
|:-----------|-------:|
| mom_3      |  223.7 |
| beta       |  219.2 |
| rev_1w     |  216.4 |
| mom_12_1   |  211   |
| dv_trend   |  203.9 |
| rev_1m     |  197.3 |
| vol_ratio  |  187.3 |
| skew_60    |  185.7 |
| vol_60     |  185.2 |
| log_dv60   |  184   |
| idio_vol   |  170.6 |
| dist_high  |  169.7 |
| max_ret_21 |  161.5 |
| mom_6_1    |  159.9 |
| ma200      |  153.9 |

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
