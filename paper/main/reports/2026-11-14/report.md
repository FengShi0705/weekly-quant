# Weekly rebalance — signal date 2026-11-13

- Broker: **t212**, base currency **GBP**
- Account equity (managed): **10,049.04 GBP**, cash before trades 440.68
- Market regime exposure: **100%**

## Orders to place

Place sells first, then buys. Prices are the last close and only a guide: use limit orders a little through the current quote. London prices are in pence (GBp).

_No trades needed this week._

## Target portfolio

Sector mix: Tech 7, Financials 6, Industrials 1, Health 1 (cap 15 per sector).

|   rank | ticker   | name                   | country   | sector      |   score |   target_weight |   target_value_GBP | held   |
|-------:|:---------|:-----------------------|:----------|:------------|--------:|----------------:|-------------------:|:-------|
|      1 | PANW     | Palo Alto Networks     | US        | Tech        |   0.477 |          0.0653 |             656.54 | True   |
|      2 | AMAT     | Applied Materials      | US        | Tech        |   0.439 |          0.0653 |             656.54 | True   |
|      5 | STAN.L   | Standard Chartered     | UK        | Financials  |   0.414 |          0.0653 |             656.54 | True   |
|      6 | RR.L     | Rolls-Royce            | UK        | Industrials |   0.399 |          0.0653 |             656.54 | True   |
|      7 | INGA.AS  | ING Group              | NL        | Financials  |   0.378 |          0.0653 |             656.54 | True   |
|      8 | LRCX     | Lam Research           | US        | Tech        |   0.377 |          0.0653 |             656.54 | True   |
|     11 | BNP.PA   | BNP Paribas            | FR        | Financials  |   0.362 |          0.0653 |             656.54 | True   |
|     12 | IFX.DE   | Infineon               | DE        | Tech        |   0.359 |          0.0653 |             656.54 | True   |
|     19 | UBSG.SW  | UBS Group              | CH        | Financials  |   0.328 |          0.0653 |             656.54 | True   |
|     20 | BBVA.MC  | BBVA                   | ES        | Financials  |   0.324 |          0.0653 |             656.54 | True   |
|     23 | BAYN.DE  | Bayer                  | DE        | Health      |   0.317 |          0.0653 |             656.54 | True   |
|     37 | TXN      | Texas Instruments      | US        | Tech        |   0.241 |          0.0653 |             656.54 | True   |
|     40 | MU       | Micron Technology      | US        | Tech        |   0.227 |          0.0653 |             656.54 | True   |
|     67 | BARC.L   | Barclays               | UK        | Financials  |   0.13  |          0.0653 |             656.54 | True   |
|     92 | AMD      | Advanced Micro Devices | US        | Tech        |   0.058 |          0.0653 |             656.54 | True   |

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
