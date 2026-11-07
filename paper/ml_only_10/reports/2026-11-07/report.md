# Weekly rebalance — signal date 2026-11-06

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **8,968.62 GBP**, cash before trades 192.05
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

| side   | ticker   | name   | country   |   shares |   ref_price_local | quote_ccy   |   est_value_GBP |   est_cost_GBP | reason   |
|:-------|:---------|:-------|:----------|---------:|------------------:|:------------|----------------:|---------------:|:---------|
| SELL   | BAYN.DE  | Bayer  | DE        |   7.1404 |             55.58 | EUR         |          331.16 |           0.83 | resize   |

## Target portfolio

Sector mix: Tech 6, Industrials 1, Health 1, Financials 1, ConsDisc 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | IFX.DE   | Infineon               | DE        | Tech        |   0.495 |           0.098 |             878.92 | True   |
|      2 | AMAT     | Applied Materials      | US        | Tech        |   0.493 |           0.098 |             878.92 | True   |
|      7 | LRCX     | Lam Research           | US        | Tech        |   0.458 |           0.098 |             878.92 | True   |
|      8 | ODFL     | Old Dominion Freight   | US        | Industrials |   0.457 |           0.098 |             878.92 | True   |
|      9 | BAYN.DE  | Bayer                  | DE        | Health      |   0.453 |           0.098 |             878.92 | True   |
|     15 | GLE.PA   | Societe Generale       | FR        | Financials  |   0.417 |           0.098 |             878.92 | True   |
|     24 | TXN      | Texas Instruments      | US        | Tech        |   0.362 |           0.098 |             878.92 | True   |
|     34 | KER.PA   | Kering                 | FR        | ConsDisc    |   0.279 |           0.098 |             878.92 | True   |
|     54 | MU       | Micron Technology      | US        | Tech        |   0.199 |           0.098 |             878.92 | True   |
|     83 | AMD      | Advanced Micro Devices | US        | Tech        |   0.123 |           0.098 |             878.92 | True   |

## What the model is leaning on (feature importance, gain)

|            |   gain |
|:-----------|-------:|
| mom_3      |  212.5 |
| rev_1w     |  210.4 |
| rev_1m     |  207.6 |
| dv_trend   |  205.7 |
| beta       |  205.7 |
| mom_12_1   |  202.6 |
| vol_ratio  |  197.7 |
| log_dv60   |  192.1 |
| vol_60     |  188.9 |
| skew_60    |  174.1 |
| dist_high  |  169.5 |
| idio_vol   |  167.8 |
| max_ret_21 |  155.6 |
| ma200      |  148.7 |
| mom_6_1    |  147.2 |

## After you trade

Update `holdings.csv` with your actual filled share quantities and the cash balance from your broker, so next week's run starts from what you really hold.
