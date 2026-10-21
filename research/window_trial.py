"""Phase 3, test E: the Stage 1 transformer with up to 10 years of training history
(research/preregistration_phase3.md).

Usage: python research/window_trial.py [--note ...]
Writes research/results/phase3/window_520/ and appends to research/trials.csv.
"""
import argparse
import copy
import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from horizon_trial import RUN1, blend_backtest  # noqa: E402
from ranker_variants import smoothed_rank  # noqa: E402
from risk_overlays import p_drop  # noqa: E402
from stage1 import nw_t, weekly_ic  # noqa: E402
from wq import deep  # noqa: E402
from wq.backtest import metrics, prepare  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402

WINDOW = 520


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    start = pd.Timestamp(cfg["backtest"]["start"])
    dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    k = cfg["model"]["score_smoothing_weeks"]
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = 5
    out = ROOT / "research" / "results" / "phase3" / f"window_{WINDOW}"
    out.mkdir(parents=True, exist_ok=True)

    scfg = dataclasses.replace(deep.Stage1Config(), train_window_weeks=WINDOW)
    weeks, vocab = deep.build_weeks(panel, universe)
    tx, log = deep.walk_forward_tx(weeks, vocab, dates, scfg)
    tx.to_parquet(out / "tx_scores.parquet")
    log.to_csv(out / "refit_log.csv", index=False)
    tx1 = pd.read_parquet(RUN1 / "tx_scores.parquet")["tx"]
    new, ref = smoothed_rank(tx["tx"], k), smoothed_rank(tx1, k).reindex(tx.index)
    ic_new, ic_ref = weekly_ic(new, panel), weekly_ic(ref, panel)
    d = (ic_new - ic_ref).dropna()
    yr = d.index.year
    comp = {"ic_variant": float(ic_new.mean()), "ic_reference": float(ic_ref.mean()), "diff": float(d.mean()),
            "nw_t": float(nw_t(d)), "weeks": len(d),
            "diff_2016_19": float(d[yr <= 2019].mean()), "diff_2020_26": float(d[yr >= 2020].mean())}
    res = blend_backtest(tx["tx"], panel, cal, px, universe, fx, capped, div_tax, k)
    res.to_csv(out / "weekly.csv")
    m = metrics(res["ret"])
    bt = {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
          "turnover": float(res["turnover"].mean()), "p_drop_over_30pct_5y": p_drop(res["ret"].dropna())}
    gate = {**comp, "pass": bool(comp["nw_t"] >= 2.0 and bt["max_drawdown"] > -0.30)}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out / "summary.json").write_text(json.dumps({"run_at": now, "gate": gate, "backtest": bt}, indent=2, default=float))
    row = pd.DataFrame([{"run_at": now, "stage": "phase3", "tag": f"E_window_{WINDOW}", "config": f"window{WINDOW}",
                         "seeds": 3, "weeks": len(d), "ic_tx": comp["ic_variant"], "ic_lgbm": comp["ic_reference"],
                         "gate_t": comp["nw_t"], "gate_pass": gate["pass"],
                         "note": args.note or f"CAGR {bt['cagr']:.3f}, MDD {bt['max_drawdown']:.3f}"}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps({"gate": gate, "backtest": bt}, indent=2, default=float))


if __name__ == "__main__":
    main()
