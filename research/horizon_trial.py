"""Phase 3, test D: the Stage 1 transformer trained on 4- or 13-week labels (research/preregistration_phase3.md).

Usage: python research/horizon_trial.py --horizon {4,13} [--note ...]
Writes research/results/phase3/horizon_<h>/ and appends to research/trials.csv.
"""
import argparse
import copy
import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from ranker_variants import smoothed_rank  # noqa: E402
from risk_overlays import p_drop  # noqa: E402
from stage1 import nw_t, rank, weekly_ic  # noqa: E402
from wq import deep  # noqa: E402
from wq.backtest import metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402

RUN1 = ROOT / "research" / "results" / "stage1" / "run1_main_3seeds"


def ic_against(score, ret):
    """Weekly Spearman IC of a score against a forward return column."""
    df = pd.DataFrame({"s": score, "r": ret}).dropna()
    return df.groupby(level="date").apply(lambda g: g["s"].rank().corr(g["r"].rank()) if len(g) >= 10
                                          else np.nan).dropna()


def blend_backtest(tx, panel, cal, px, universe, fx, cfg, div_tax, k):
    base = baseline_score(panel).reindex(tx.index)
    s = smooth_scores(pd.DataFrame({"s": 0.7 * rank(tx) + 0.3 * rank(base)}), k)["s"]
    res, _ = simulate(s.to_frame("score"), panel, cal, px, universe, fx, cfg, div_tax=div_tax)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, required=True, choices=[4, 13])
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    h = args.horizon
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    ch = copy.deepcopy(cfg)
    ch["model"]["label_horizon_weeks"] = h
    panel_h, _, _ = prepare(ch, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    start = pd.Timestamp(cfg["backtest"]["start"])
    dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    k = cfg["model"]["score_smoothing_weeks"]
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = 5
    out = ROOT / "research" / "results" / "phase3" / f"horizon_{h}"
    out.mkdir(parents=True, exist_ok=True)

    scfg = dataclasses.replace(deep.Stage1Config(), label_horizon=h)
    weeks, vocab = deep.build_weeks(panel_h, universe)
    tx, log = deep.walk_forward_tx(weeks, vocab, dates, scfg)
    tx.to_parquet(out / "tx_scores.parquet")
    log.to_csv(out / "refit_log.csv", index=False)
    tx1 = pd.read_parquet(RUN1 / "tx_scores.parquet")["tx"]
    new, ref = smoothed_rank(tx["tx"], k), smoothed_rank(tx1, k).reindex(tx.index)

    ic_h_new, ic_h_ref = ic_against(new, panel_h["fwd_ret"]), ic_against(ref, panel_h["fwd_ret"])
    d_h = (ic_h_new - ic_h_ref).dropna()
    ic_1_new, ic_1_ref = weekly_ic(new, panel), weekly_ic(ref, panel)
    d_1 = (ic_1_new - ic_1_ref).dropna()
    comp = {f"ic_{h}w_variant": float(ic_h_new.mean()), f"ic_{h}w_reference": float(ic_h_ref.mean()),
            "diff": float(d_h.mean()), "nw_t": float(nw_t(d_h, lags=2 * h)), "weeks": len(d_h),
            "ic_1w_variant": float(ic_1_new.mean()), "ic_1w_reference": float(ic_1_ref.mean()),
            "ic_1w_nw_t": float(nw_t(d_1))}

    res = blend_backtest(tx["tx"], panel, cal, px, universe, fx, capped, div_tax, k)
    res_ref = blend_backtest(tx1, panel, cal, px, universe, fx, capped, div_tax, k)
    res.to_csv(out / "weekly.csv")
    m = metrics(res["ret"])
    dr = (res["ret"] - res_ref["ret"]).dropna()
    bt = {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
          "turnover": float(res["turnover"].mean()), "p_drop_over_30pct_5y": p_drop(res["ret"].dropna()),
          "run1_blend_cagr": metrics(res_ref["ret"])["cagr"],
          "weekly_return_diff_per_year_vs_run1_blend": float(dr.mean() * 52), "weekly_return_diff_nw_t": float(nw_t(dr))}
    gate = {**comp, "pass": bool(comp["nw_t"] >= 2.3 and comp["ic_1w_nw_t"] > -2 and bt["max_drawdown"] > -0.30)}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"run_at": now, "horizon_weeks": h, "gate": gate, "backtest": bt}
    (out / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    row = pd.DataFrame([{"run_at": now, "stage": "phase3", "tag": f"D_labels_{h}w", "config": f"horizon{h}",
                         "seeds": 3, "weeks": len(d_h), "ic_tx": comp[f"ic_{h}w_variant"],
                         "ic_lgbm": comp[f"ic_{h}w_reference"], "gate_t": comp["nw_t"], "gate_pass": gate["pass"],
                         "note": args.note or f"{h}-week IC vs run 1; CAGR {bt['cagr']:.3f}, MDD {bt['max_drawdown']:.3f}"}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps(result, indent=2, default=float))


if __name__ == "__main__":
    main()
