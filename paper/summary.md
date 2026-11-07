# Paper trading

Simulated fills at the Monday close after each signal, with the backtest's cost model.

| strategy      | since      | latest     |   value | return   |   trades |   costs |   dividend tax | Vanguard FTSE All-World buy & hold   | Vanguard S&P 500 buy & hold   |
|:--------------|:-----------|:-----------|--------:|:---------|---------:|--------:|---------------:|:-------------------------------------|:------------------------------|
| main          | 2026-10-16 | 2026-11-06 | 9366.37 | -6.34%   |       15 |   34.8  |           0.53 | -4.46%                               | -4.79%                        |
| ml_only_10    | 2026-10-16 | 2026-11-06 | 8968.62 | -10.31%  |       10 |   32.08 |           0.8  | -4.46%                               | -4.79%                        |
| tx_blend      | 2026-10-23 | 2026-11-06 | 9480.17 | -5.20%   |       15 |   39.49 |           1.35 | -2.70%                               | -3.20%                        |
| tx_blend_tilt | 2026-10-23 | 2026-11-06 | 9457.78 | -5.42%   |       16 |   39.95 |           1.93 | -2.70%                               | -3.20%                        |
