# Weekly rebalance — signal date 2026-11-13

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,766.58 GBP**, cash before trades 528.53
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name                   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-----------------------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| SELL   | AMD      | Advanced Micro Devices | US        |   2.46   |            534.06 | USD         |          992.93 |           2.5  | exit     |
| BUY    | KER.PA   | Kering                 | FR        |   0.8599 |            184.64 | EUR         |          132.6  |           0.86 | resize   |
| BUY    | LRCX     | Lam Research           | US        |   0.6773 |            225.92 | USD         |          115.65 |           0.29 | resize   |
| BUY    | MU       | Micron Technology      | US        |   0.1471 |            778.31 | USD         |           86.53 |           0.22 | resize   |
| BUY    | PANW     | Palo Alto Networks     | US        |   3.93   |            322.24 | USD         |          957.12 |           2.39 | enter    |

## Target portfolio

Sector mix: Tech 6, Industrials 1, Financials 1, Health 1, ConsDisc 1 (cap 15 per sector).

|   rank | ticker   | name                 | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:---------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | IFX.DE   | Infineon             | DE        | Tech        |   0.494 |           0.098 |             957.12 | True   |
|      2 | PANW     | Palo Alto Networks   | US        | Tech        |   0.492 |           0.098 |             957.12 | False  |
|      4 | AMAT     | Applied Materials    | US        | Tech        |   0.476 |           0.098 |             957.12 | True   |
|      5 | ODFL     | Old Dominion Freight | US        | Industrials |   0.465 |           0.098 |             957.12 | True   |
|     10 | GLE.PA   | Societe Generale     | FR        | Financials  |   0.422 |           0.098 |             957.12 | True   |
|     16 | LRCX     | Lam Research         | US        | Tech        |   0.411 |           0.098 |             957.12 | True   |
|     35 | BAYN.DE  | Bayer                | DE        | Health      |   0.276 |           0.098 |             957.12 | True   |
|     37 | TXN      | Texas Instruments    | US        | Tech        |   0.267 |           0.098 |             957.12 | True   |
|     51 | KER.PA   | Kering               | FR        | ConsDisc    |   0.227 |           0.098 |             957.12 | True   |
|     78 | MU       | Micron Technology    | US        | Tech        |   0.132 |           0.098 |             957.12 | True   |

## What the model is leaning on (feature importance, gain)

|            |   gain |
|:-----------|-------:|
| rev_1w     |  216.3 |
| mom_3      |  215.5 |
| beta       |  213.1 |
| rev_1m     |  207.8 |
| dv_trend   |  201.6 |
| mom_12_1   |  194.3 |
| log_dv60   |  192.1 |
| vol_ratio  |  187.7 |
| vol_60     |  181.1 |
| idio_vol   |  178.4 |
| dist_high  |  172.5 |
| skew_60    |  172.1 |
| mom_6_1    |  160.1 |
| max_ret_21 |  150.2 |
| ma200      |  147.8 |

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
