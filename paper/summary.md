# Paper trading

Simulated fills at the Monday close after each signal, with the backtest's cost model.

| strategy      | since      | latest     |   value | return   |   trades |   costs |   dividend tax | Vanguard FTSE All-World buy & hold   | Vanguard S&P 500 buy & hold   |
|:--------------|:-----------|:-----------|--------:|:---------|---------:|--------:|---------------:|:-------------------------------------|:------------------------------|
| main          | 2026-10-16 | 2026-10-30 | 9789.51 | -2.10%   |       15 |   34.8  |           0.53 | -0.95%                               | -0.95%                        |
| ml_only_10    | 2026-10-16 | 2026-10-30 | 9607.44 | -3.93%   |       10 |   32.08 |           0.8  | -0.95%                               | -0.95%                        |
| tx_blend      | 2026-10-23 | 2026-10-30 | 9808.62 | -1.91%   |       15 |   39.49 |           1.35 | +0.88%                               | +0.70%                        |
| tx_blend_tilt | 2026-10-23 | 2026-10-30 | 9787.96 | -2.12%   |       15 |   39.32 |           1.93 | +0.88%                               | +0.70%                        |
