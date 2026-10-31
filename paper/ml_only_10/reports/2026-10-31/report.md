# Weekly rebalance — signal date 2026-10-30

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,607.44 GBP**, cash before trades 192.05
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

_No trades needed this week._

## Target portfolio

Sector mix: Tech 6, Health 1, Industrials 1, Financials 1, ConsDisc 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | AMAT     | Applied Materials      | US        | Tech        |   0.494 |           0.098 |             941.53 | True   |
|      2 | IFX.DE   | Infineon               | DE        | Tech        |   0.493 |           0.098 |             941.53 | True   |
|      4 | LRCX     | Lam Research           | US        | Tech        |   0.481 |           0.098 |             941.53 | True   |
|      5 | BAYN.DE  | Bayer                  | DE        | Health      |   0.477 |           0.098 |             941.53 | True   |
|      7 | ODFL     | Old Dominion Freight   | US        | Industrials |   0.458 |           0.098 |             941.53 | True   |
|     10 | GLE.PA   | Societe Generale       | FR        | Financials  |   0.44  |           0.098 |             941.53 | True   |
|     16 | TXN      | Texas Instruments      | US        | Tech        |   0.413 |           0.098 |             941.53 | True   |
|     24 | AMD      | Advanced Micro Devices | US        | Tech        |   0.366 |           0.098 |             941.53 | True   |
|     25 | KER.PA   | Kering                 | FR        | ConsDisc    |   0.356 |           0.098 |             941.53 | True   |
|     51 | MU       | Micron Technology      | US        | Tech        |   0.223 |           0.098 |             941.53 | True   |

## What the model is leaning on (feature importance, gain)

|            |   gain |
|:-----------|-------:|
| rev_1w     |  210.1 |
| mom_3      |  207.1 |
| beta       |  206.6 |
| rev_1m     |  205   |
| dv_trend   |  203.6 |
| mom_12_1   |  199.4 |
| log_dv60   |  194.4 |
| vol_60     |  192.9 |
| vol_ratio  |  186.7 |
| dist_high  |  177.5 |
| idio_vol   |  174   |
| skew_60    |  169.3 |
| mom_6_1    |  159.2 |
| max_ret_21 |  155.8 |
| ma200      |  144.6 |

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
