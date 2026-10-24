# Weekly rebalance — signal date 2026-10-23

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,559.05 GBP**, cash before trades 192.85
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

_No trades needed this week._

## Target portfolio

Sector mix: Tech 6, Health 1, Industrials 1, Financials 1, ConsDisc 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | IFX.DE   | Infineon               | DE        | Tech        |   0.492 |           0.098 |             936.79 | True   |
|      2 | AMAT     | Applied Materials      | US        | Tech        |   0.49  |           0.098 |             936.79 | True   |
|      3 | LRCX     | Lam Research           | US        | Tech        |   0.488 |           0.098 |             936.79 | True   |
|      4 | BAYN.DE  | Bayer                  | DE        | Health      |   0.476 |           0.098 |             936.79 | True   |
|      6 | ODFL     | Old Dominion Freight   | US        | Industrials |   0.457 |           0.098 |             936.79 | True   |
|      7 | GLE.PA   | Societe Generale       | FR        | Financials  |   0.455 |           0.098 |             936.79 | True   |
|      9 | TXN      | Texas Instruments      | US        | Tech        |   0.432 |           0.098 |             936.79 | True   |
|     14 | KER.PA   | Kering                 | FR        | ConsDisc    |   0.41  |           0.098 |             936.79 | True   |
|     25 | AMD      | Advanced Micro Devices | US        | Tech        |   0.373 |           0.098 |             936.79 | True   |
|     35 | MU       | Micron Technology      | US        | Tech        |   0.326 |           0.098 |             936.79 | True   |

## What the model is leaning on (feature importance, gain)

|            |   gain |
|:-----------|-------:|
| rev_1w     |  218.3 |
| mom_3      |  217   |
| mom_12_1   |  210.3 |
| rev_1m     |  204.6 |
| beta       |  200   |
| dv_trend   |  199.3 |
| vol_ratio  |  197.6 |
| log_dv60   |  197.6 |
| vol_60     |  190.5 |
| skew_60    |  173.7 |
| idio_vol   |  172.5 |
| dist_high  |  171.2 |
| mom_6_1    |  162.4 |
| max_ret_21 |  148.8 |
| ma200      |  137.3 |

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
