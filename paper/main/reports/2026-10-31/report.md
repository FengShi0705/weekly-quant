# Weekly rebalance — signal date 2026-10-30

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **9,789.51 GBP**, cash before trades 242.76
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

_No trades needed this week._

## Target portfolio

Sector mix: Tech 7, Financials 6, Health 1, Industrials 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | BAYN.DE  | Bayer                  | DE        | Health      |   0.475 |          0.0653 |             639.58 | True   |
|      2 | PANW     | Palo Alto Networks     | US        | Tech        |   0.459 |          0.0653 |             639.58 | True   |
|      3 | AMAT     | Applied Materials      | US        | Tech        |   0.452 |          0.0653 |             639.58 | True   |
|      4 | INGA.AS  | ING Group              | NL        | Financials  |   0.451 |          0.0653 |             639.58 | True   |
|      5 | LRCX     | Lam Research           | US        | Tech        |   0.437 |          0.0653 |             639.58 | True   |
|      6 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.434 |          0.0653 |             639.58 | True   |
|      9 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.406 |          0.0653 |             639.58 | True   |
|     10 | BNP.PA   | BNP Paribas            | FR        | Financials  |   0.403 |          0.0653 |             639.58 | True   |
|     11 | IFX.DE   | Infineon               | DE        | Tech        |   0.402 |          0.0653 |             639.58 | True   |
|     14 | AMD      | Advanced Micro Devices | US        | Tech        |   0.386 |          0.0653 |             639.58 | True   |
|     16 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.374 |          0.0653 |             639.58 | True   |
|     18 | UBSG.SW  | UBS Group              | CH        | Financials  |   0.361 |          0.0653 |             639.58 | True   |
|     19 | TXN      | Texas Instruments      | US        | Tech        |   0.358 |          0.0653 |             639.58 | True   |
|     33 | MU       | Micron Technology      | US        | Tech        |   0.289 |          0.0653 |             639.58 | True   |
|     47 | BARC.L   | Barclays               | UK        | Financials  |   0.212 |          0.0653 |             639.58 | True   |

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
