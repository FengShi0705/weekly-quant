"""Phase 3, test K: score-tilted weights replicated on `main` (LightGBM blend) (research/preregistration_phase3.md).

Usage: python research/tilt_replication.py [--note ...]
Writes research/results/phase3/tilt_replication/ and appends to research/trials.csv.
"""
import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from risk_overlays import p_drop  # noqa: E402
from settings_trial import PERIODS  # noqa: E402
from stage1 import nw_t  # noqa: E402
from wq.backtest import metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402

OUT = ROOT / "research" / "results" / "phase3" / "tilt_replication"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    scores = pd.read_parquet(cfg["paths"]["reports"] / "backtest" / "scores.parquet")[["score"]]
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, weighting in [("main_equal", "equal"), ("main_score_tilt", "score_tilt")]:
        c = copy.deepcopy(cfg)
        c["portfolio"]["weighting"] = weighting
        res[name], _ = simulate(scores, panel, cal, px, universe, fx, c, div_tax=div_tax)
        res[name].to_csv(OUT / f"{name}.csv")
    years = len(res["main_equal"]) / 52
    out = {}
    for name, r in res.items():
        m = metrics(r["ret"])
        out[name] = {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
                     "cost_per_year": float((r["cost"] / r["equity"]).sum() / years),
                     "p_drop_over_30pct_5y": float(p_drop(r["ret"].dropna()))}
    d = (res["main_score_tilt"]["ret"] - res["main_equal"]["ret"]).dropna()
    yr = d.index.year
    by = {p: float(d[(yr >= a) & (yr <= b)].mean() * 52) for p, (a, b) in PERIODS.items()}
    t = out["main_score_tilt"]
    gate = {"diff_per_year": float(d.mean() * 52), "nw_t": float(nw_t(d)), "by_period": by}
    gate["replicates"] = bool(gate["nw_t"] >= 2.0 and all(v > 0 for v in by.values())
                              and t["max_drawdown"] > -0.30 and t["p_drop_over_30pct_5y"] <= 0.20)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (OUT / "summary.json").write_text(json.dumps({"run_at": now, "arms": out, "gate": gate}, indent=2, default=float))
    row = pd.DataFrame([{"run_at": now, "stage": "phase3", "tag": "K_tilt_replication_main", "config": "score_tilt",
                         "seeds": 5, "weeks": len(d), "ic_tx": "", "ic_lgbm": "", "gate_t": gate["nw_t"],
                         "gate_pass": gate["replicates"],
                         "note": args.note or f"main CAGR {t['cagr']:.3f} tilted vs {out['main_equal']['cagr']:.3f} equal"}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps({"arms": out, "gate": gate}, indent=2, default=float))


if __name__ == "__main__":
    main()
