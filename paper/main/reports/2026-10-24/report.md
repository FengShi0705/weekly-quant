# Weekly rebalance — signal date 2026-10-23

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,641.82 GBP**, cash before trades 243.29
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

_No trades needed this week._

## Target portfolio

Sector mix: Tech 7, Financials 6, Health 1, Industrials 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | BAYN.DE  | Bayer                  | DE        | Health      |   0.476 |          0.0653 |             629.93 | True   |
|      2 | AMAT     | Applied Materials      | US        | Tech        |   0.436 |          0.0653 |             629.93 | True   |
|      3 | INGA.AS  | ING Group              | NL        | Financials  |   0.436 |          0.0653 |             629.93 | True   |
|      4 | LRCX     | Lam Research           | US        | Tech        |   0.434 |          0.0653 |             629.93 | True   |
|      5 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.427 |          0.0653 |             629.93 | True   |
|      6 | PANW     | Palo Alto Networks     | US        | Tech        |   0.425 |          0.0653 |             629.93 | True   |
|      7 | IFX.DE   | Infineon               | DE        | Tech        |   0.421 |          0.0653 |             629.93 | True   |
|      8 | BNP.PA   | BNP Paribas            | FR        | Financials  |   0.411 |          0.0653 |             629.93 | True   |
|     10 | AMD      | Advanced Micro Devices | US        | Tech        |   0.391 |          0.0653 |             629.93 | True   |
|     11 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.39  |          0.0653 |             629.93 | True   |
|     12 | UBSG.SW  | UBS Group              | CH        | Financials  |   0.387 |          0.0653 |             629.93 | True   |
|     14 | TXN      | Texas Instruments      | US        | Tech        |   0.38  |          0.0653 |             629.93 | True   |
|     15 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.38  |          0.0653 |             629.93 | True   |
|     20 | MU       | Micron Technology      | US        | Tech        |   0.359 |          0.0653 |             629.93 | True   |
|     24 | BARC.L   | Barclays               | UK        | Financials  |   0.337 |          0.0653 |             629.93 | True   |

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
