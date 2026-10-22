"""Phase 3, test G: number of holdings for the transformer strategy (research/preregistration_phase3.md).

Usage: python research/positions_trial.py [--note ...]
Writes research/results/phase3/positions/ and appends to research/trials.csv.
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
from stage1 import nw_t, rank  # noqa: E402
from wq.backtest import metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402

RUN = ROOT / "research" / "results" / "stage1" / "run3_main_10seeds"
OUT = ROOT / "research" / "results" / "phase3" / "positions"
# name: (transformer weight, holdings, per-sector cap)
VARIANTS = {"G0_tx_blend": (0.7, 15, 5), "G1_blend_10": (0.7, 10, 4), "G2_blend_20": (0.7, 20, 7),
            "G3_tx_only_10": (1.0, 10, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    tx = pd.read_parquet(RUN / "tx_scores.parquet")["tx"]
    base = baseline_score(panel).reindex(tx.index)
    k = cfg["model"]["score_smoothing_weeks"]
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, (w, n, cap) in VARIANTS.items():
        c = copy.deepcopy(cfg)
        c["portfolio"]["n_positions"], c["portfolio"]["max_per_sector"] = n, cap
        s = smooth_scores(pd.DataFrame({"s": w * rank(tx) + (1 - w) * rank(base)}), k)["s"]
        res[name], _ = simulate(s.to_frame("score"), panel, cal, px, universe, fx, c, div_tax=div_tax)
        res[name].to_csv(OUT / f"{name}.csv")
    years = len(res["G0_tx_blend"]) / 52
    out, gates = {}, {}
    for name, r in res.items():
        m = metrics(r["ret"])
        out[name] = {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
                     "cost_per_year": float((r["cost"] / r["equity"]).sum() / years),
                     "turnover": float(r["turnover"].mean()), "p_drop_over_30pct_5y": float(p_drop(r["ret"].dropna()))}
        if name == "G0_tx_blend":
            continue
        d = (r["ret"] - res["G0_tx_blend"]["ret"]).dropna()
        yr = d.index.year
        by = {p: float(d[(yr >= a) & (yr <= b)].mean() * 52) for p, (a, b) in PERIODS.items()}
        g = {"diff_per_year": float(d.mean() * 52), "nw_t": float(nw_t(d)), "by_period": by}
        g["pass"] = bool(g["nw_t"] >= 2.4 and all(v > 0 for v in by.values()) and m["max_drawdown"] > -0.30
                         and out[name]["p_drop_over_30pct_5y"] <= 0.20)
        gates[name] = g
        print(name, {k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in {**out[name], **g}.items()}, flush=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (OUT / "summary.json").write_text(json.dumps({"run_at": now, "arms": out, "gates": gates}, indent=2, default=float))
    rows = [{"run_at": now, "stage": "phase3", "tag": f"G_{n}", "config": n, "seeds": 10, "weeks": "",
             "ic_tx": "", "ic_lgbm": "", "gate_t": g["nw_t"], "gate_pass": g["pass"],
             "note": args.note or (f"CAGR {out[n]['cagr']:.3f} vs {out['G0_tx_blend']['cagr']:.3f}, "
                                   f"MDD {out[n]['max_drawdown']:.3f}, P(>30% in 5y) {out[n]['p_drop_over_30pct_5y']:.3f}")}
            for n, g in gates.items()]
    pd.DataFrame(rows).to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print("tx_blend", {k2: round(v, 4) for k2, v in out["G0_tx_blend"].items()})


if __name__ == "__main__":
    main()
