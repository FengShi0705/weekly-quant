# Trading 212 Practice vs simulation (main)

**15 fills.** Value-weighted cost per trade: real **169 bps** (price vs the day's close +144 bps + fees 24 bps) against the model's **36 bps**: 4.7x the model (the go-live rule asks for no more than about 2x).

Price vs close is noisy for any single trade (orders sent at the weekend fill at the open, the model assumes the close); only the average over many trades means much.

| signal_date   | fill_day   | ticker   | side   |   shares |   value_GBP |   vs_close_bps |   real_fees_bps |   real_total_bps |   model_cost_bps |
|:--------------|:-----------|:---------|:-------|---------:|------------:|---------------:|----------------:|-----------------:|-----------------:|
| 2026-10-16    | 2026-10-19 | TXN      | buy    |   3.1365 |      667    |          263.6 |            15   |            278.6 |               25 |
| 2026-10-16    | 2026-10-19 | AMD      | buy    |   1.64   |      680.15 |          273.2 |            15   |            288.2 |               25 |
| 2026-10-16    | 2026-10-19 | AMAT     | buy    |   2.1187 |      677.58 |          317.8 |            15.1 |            332.9 |               25 |
| 2026-10-16    | 2026-10-19 | MU       | buy    |   0.9867 |      676.65 |          100.5 |            14.9 |            115.4 |               25 |
| 2026-10-16    | 2026-10-19 | PANW     | buy    |   2.5356 |      675.38 |          232   |            15   |            247   |               25 |
| 2026-10-16    | 2026-10-19 | LRCX     | buy    |   3.2855 |      680.67 |          144   |            15   |            159   |               25 |
| 2026-10-16    | 2026-10-19 | STAN.L   | buy    |  30.716  |      647.19 |          134.7 |            50.1 |            184.7 |               60 |
| 2026-10-16    | 2026-10-19 | RR.L     | buy    |  48.373  |      647.23 |           48.1 |            50.1 |             98.1 |               60 |
| 2026-10-16    | 2026-10-19 | BARC.L   | buy    | 151      |      639.64 |          146.1 |            50   |            196.1 |               60 |
| 2026-10-16    | 2026-10-19 | BAYN.DE  | buy    |  17.394  |      651.09 |          244.2 |            15.1 |            259.3 |               25 |
| 2026-10-16    | 2026-10-19 | BNP.PA   | buy    |   8.636  |      640.26 |           82.4 |            55   |            137.4 |               65 |
| 2026-10-16    | 2026-10-19 | IFX.DE   | buy    |  14.761  |      651.3  |          -22.8 |            15   |             -7.8 |               25 |
| 2026-10-16    | 2026-10-19 | INGA.AS  | buy    |  25.727  |      648.39 |          144   |            15   |            159   |               25 |
| 2026-10-16    | 2026-10-19 | BBVA.MC  | buy    |  33.363  |      644.46 |           92.4 |            15.1 |            107.4 |               45 |
| 2026-10-16    | 2026-10-19 | UBSG.SW  | buy    |  18.022  |      636.77 |          -61.4 |            15.1 |            -46.3 |               25 |

## Account value

At each weekend run, both valued at Friday's close.

| date       |   Trading 212 |   simulated |   difference |
|:-----------|--------------:|------------:|-------------:|
| 2026-10-18 |       9999.99 |    10000    |        -0.01 |
| 2026-10-24 |       9426.27 |     9641.82 |      -215.55 |

## Holdings that differ

Valued at the 2026-10-23 close. Lists stocks held in only one account, and stocks in both whose share counts are more than 5% apart (smaller gaps from fill prices and rounding are left out).

Both accounts hold the same stocks.

| ticker   | name   | held in   | Trading 212 shares   | simulated shares   |   Trading 212 value |   simulated value |   difference |
|:---------|:-------|:----------|:---------------------|:-------------------|--------------------:|------------------:|-------------:|
| CASH     |        |           |                      |                    |               112.1 |            243.29 |      -131.19 |
