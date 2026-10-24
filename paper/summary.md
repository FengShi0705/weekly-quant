# Paper trading

Simulated fills at the Monday close after each signal, with the backtest's cost model.

| strategy      | since      | latest     |    value | return   |   trades |   costs |   dividend tax | Vanguard FTSE All-World buy & hold   | Vanguard S&P 500 buy & hold   |
|:--------------|:-----------|:-----------|---------:|:---------|---------:|--------:|---------------:|:-------------------------------------|:------------------------------|
| main          | 2026-10-16 | 2026-10-23 |  9641.82 | -3.58%   |       15 |   34.8  |              0 | -1.81%                               | -1.64%                        |
| ml_only_10    | 2026-10-16 | 2026-10-23 |  9559.05 | -4.41%   |       10 |   32.08 |              0 | -1.81%                               | -1.64%                        |
| tx_blend      | 2026-10-23 | 2026-10-23 | 10000    | +0.00%   |        0 |    0    |              0 | +0.00%                               | +0.00%                        |
| tx_blend_tilt | 2026-10-23 | 2026-10-23 | 10000    | +0.00%   |        0 |    0    |              0 | +0.00%                               | +0.00%                        |
