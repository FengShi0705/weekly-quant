# Weekly rebalance — signal date 2026-10-16

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **10,000.00 GBP**, cash before trades 10,000.00
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name                   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-----------------------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| BUY    | AMAT     | Applied Materials      | US        |   3.1781 |            409.29 | USD         |          980    |           2.45 | enter    |
| BUY    | AMD      | Advanced Micro Devices | US        |   2.46   |            528.75 | USD         |          979.97 |           2.45 | enter    |
| BUY    | BAYN.DE  | Bayer                  | DE        |  26.0917 |             44.46 | EUR         |          980    |           2.45 | enter    |
| BUY    | GLE.PA   | Societe Generale       | FR        |  17.9934 |             64.47 | EUR         |          980    |           5.39 | enter    |
| BUY    | IFX.DE   | Infineon               | DE        |  22.1423 |             52.39 | EUR         |          980    |           2.45 | enter    |
| BUY    | KER.PA   | Kering                 | FR        |   5.347  |            216.95 | EUR         |          979.99 |           5.39 | enter    |
| BUY    | LRCX     | Lam Research           | US        |   4.9282 |            263.94 | USD         |          979.98 |           2.45 | enter    |
| BUY    | MU       | Micron Technology      | US        |   1.48   |            878.84 | USD         |          979.93 |           2.45 | enter    |
| BUY    | ODFL     | Old Dominion Freight   | US        |   6.9293 |            187.72 | USD         |          980    |           2.45 | enter    |
| BUY    | TXN      | Texas Instruments      | US        |   4.7047 |            276.48 | USD         |          979.99 |           2.45 | enter    |

## Target portfolio

Sector mix: Tech 6, Financials 1, Industrials 1, Health 1, ConsDisc 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | LRCX     | Lam Research           | US        | Tech        |   0.494 |           0.098 |                980 | False  |
|      2 | MU       | Micron Technology      | US        | Tech        |   0.493 |           0.098 |                980 | False  |
|      3 | AMAT     | Applied Materials      | US        | Tech        |   0.487 |           0.098 |                980 | False  |
|      4 | IFX.DE   | Infineon               | DE        | Tech        |   0.477 |           0.098 |                980 | False  |
|      5 | AMD      | Advanced Micro Devices | US        | Tech        |   0.474 |           0.098 |                980 | False  |
|      6 | GLE.PA   | Societe Generale       | FR        | Financials  |   0.462 |           0.098 |                980 | False  |
|      7 | ODFL     | Old Dominion Freight   | US        | Industrials |   0.461 |           0.098 |                980 | False  |
|      8 | TXN      | Texas Instruments      | US        | Tech        |   0.457 |           0.098 |                980 | False  |
|      9 | BAYN.DE  | Bayer                  | DE        | Health      |   0.453 |           0.098 |                980 | False  |
|     12 | KER.PA   | Kering                 | FR        | ConsDisc    |   0.443 |           0.098 |                980 | False  |

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
