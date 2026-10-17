"""Pre-registered research run. Selection uses Jan 2016 - Jun 2024 only (three sub-periods).
Jul 2024 - Oct 2026 is reported but was already viewed, so it is not used to choose."""
import copy, itertools, pickle, sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wq.config import load_config
from wq.data import load_cached, load_universe
from wq.backtest import prepare, simulate, metrics
from wq.model import walk_forward, smooth_scores

OUT = Path(__file__).resolve().parent.parent / "reports" / "research"
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = pd.Timestamp("2024-07-01")
SUB = [("2016-18", "2016-01-01", "2019-01-01"), ("2019-21", "2019-01-01", "2022-01-01"), ("2022-24H1", "2022-01-01", "2024-07-01")]
base = load_config(Path(__file__).resolve().parent.parent / "config.yaml")
close, vol, fx = load_cached(base); u = load_universe(base)
panel, cal, px = prepare(base, close, vol, fx, u)
dates = [d for d in cal.index if d >= pd.Timestamp(base["backtest"]["start"]) and pd.notna(cal.loc[d, "exec_date"])]

def blend(raw, w):
    g = raw.groupby(level="date")
    ml_r = g["ml"].rank(pct=True) - 0.5
    b_r = g["baseline"].rank(pct=True) - 0.5
    out = raw.copy()
    out["score"] = b_r if w == 0 else w * ml_r + (1 - w) * b_r
    return smooth_scores(out, base["model"]["score_smoothing_weeks"])

def evaluate(name, scores, cfg):
    res, _ = simulate(scores, panel, cal, px, u, fx, cfg, "score")
    r = res["ret"]
    dev, hold = metrics(r[r.index < SPLIT]), metrics(r[r.index >= SPLIT])
    row = {"variant": name, "dev_cagr": dev["cagr"], "dev_sharpe": dev["sharpe"], "dev_mdd": dev["max_drawdown"],
           "hold_cagr": hold["cagr"], "hold_sharpe": hold["sharpe"], "turnover": res["turnover"].mean()}
    for lab, a, b in SUB:
        m = metrics(r[(r.index >= a) & (r.index < b)])
        row[f"sh_{lab}"] = m["sharpe"]
    print(f"{name:42s} dev CAGR {row['dev_cagr']:6.1%} Sh {row['dev_sharpe']:.2f} MDD {row['dev_mdd']:6.1%} | "
          f"sub Sh {row['sh_2016-18']:.2f}/{row['sh_2019-21']:.2f}/{row['sh_2022-24H1']:.2f} | "
          f"hold CAGR {row['hold_cagr']:6.1%} Sh {row['hold_sharpe']:.2f} | turn {row['turnover']:.1%}", flush=True)
    return row

arms = {
    "M0 trees, base features": {},
    "M1 trees + resid/sector momentum": {"extra_features": ["resid_mom_12_1", "sector_mom_12_1"]},
    "M2 linear, base features": {"type": "ridge"},
    "M3 linear + resid/sector momentum": {"type": "ridge", "extra_features": ["resid_mom_12_1", "sector_mom_12_1"]},
}
raw = {}
for name, over in arms.items():
    t0 = time.time()
    c = copy.deepcopy(base); c["model"].update(over)
    raw[name] = walk_forward(panel, c, dates, verbose=False)
    pickle.dump(raw[name], open(OUT / f"raw_{name[:2]}.pkl", "wb"))
    print(f"[scored {name} in {time.time() - t0:.0f}s]", flush=True)

rows = []
print("\n=== Stage A: portfolio settings on the current model (M0) ===", flush=True)
for w, n, wt in itertools.product([0.0, 0.3, 0.5, 0.7, 1.0], [10, 15, 20, 25], ["equal", "inverse_vol"]):
    c = copy.deepcopy(base); c["portfolio"].update(n_positions=n, weighting=wt)
    rows.append({"stage": "A", "ml_weight": w, "n": n, "weighting": wt,
                 **evaluate(f"A ml={w:.1f} n={n} {wt}", blend(raw["M0 trees, base features"], w), c)})
print("\n=== Stage B: model variants at current settings (ml=0.7, n=15, equal) ===", flush=True)
for name in arms:
    rows.append({"stage": "B", "ml_weight": 0.7, "n": 15, "weighting": "equal",
                 **evaluate(f"B {name}", blend(raw[name], 0.7), base)})
pd.DataFrame(rows).to_csv(OUT / "phase1b_variants.csv", index=False)
print("DONE", flush=True)
