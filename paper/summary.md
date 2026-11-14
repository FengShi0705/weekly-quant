# Paper trading

Simulated fills at the Monday close after each signal, with the backtest's cost model.

| strategy      | since      | latest     |    value | return   |   trades |   costs |   dividend tax | Vanguard FTSE All-World buy & hold   | Vanguard S&P 500 buy & hold   |
|:--------------|:-----------|:-----------|---------:|:---------|---------:|--------:|---------------:|:-------------------------------------|:------------------------------|
| main          | 2026-10-16 | 2026-11-13 | 10049    | +0.49%   |       16 |   35.3  |           0.53 | -0.87%                               | -1.02%                        |
| ml_only_10    | 2026-10-16 | 2026-11-13 |  9766.58 | -2.33%   |       11 |   32.92 |           0.8  | -0.87%                               | -1.02%                        |
| tx_blend      | 2026-10-23 | 2026-11-13 | 10174.2  | +1.74%   |       16 |   39.99 |           1.35 | +0.95%                               | +0.64%                        |
| tx_blend_tilt | 2026-10-23 | 2026-11-13 | 10176.8  | +1.77%   |       19 |   42.53 |           1.93 | +0.95%                               | +0.64%                        |
