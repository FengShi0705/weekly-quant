"""Phase 3, test A: earnings-announcement inputs for the Stage 1 transformer (research/preregistration_phase3.md).

Usage: python research/earnings_trial.py [--secondary] [--note ...]
  default      transformer + ear/sue/earn_age, seeds 0-2, against Stage 1 run 1 (the gated test)
  --secondary  LightGBM + the same inputs against the deployed LightGBM (information only)
Needs data/cache/earnings.parquet (wq.earnings.fetch). Writes research/results/phase3/earnings[_lgbm]/.
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

from ranker_variants import smoothed_rank  # noqa: E402
from risk_overlays import p_drop  # noqa: E402
from stage1 import nw_t, rank, weekly_ic  # noqa: E402
from wq import deep, earnings, features  # noqa: E402
from wq.backtest import metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores, walk_forward  # noqa: E402

RUNS = ROOT / "research" / "results" / "stage1"


def earnings_panel(cfg, close, panel, cal):
    """The panel with ear/sue/earn_age added, ranked across stocks each week like every other input."""
    raw = pd.read_parquet(cfg["data"]["cache_dir"] / "earnings.parquet")
    ef = earnings.features(raw, close.sort_index(), cal.index)
    ef = ef.groupby(level="date").rank(pct=True) - 0.5
    return panel.join(ef.reindex(panel.index))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secondary", action="store_true")
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
    p2 = earnings_panel(cfg, close, panel, cal)
    live = p2[p2.index.get_level_values("date") >= start]
    coverage = {c: float(live[c].notna().mean()) for c in earnings.EARN_FEATURES}
    by_region = live["ear"].notna().groupby(live.index.get_level_values("ticker").map(universe["region"])).mean()
    coverage["ear_by_region"] = {r: float(v) for r, v in by_region.items()}
    print("coverage", json.dumps(coverage), flush=True)
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = 5

    if args.secondary:
        out = ROOT / "research" / "results" / "phase3" / "earnings_lgbm"
        out.mkdir(parents=True, exist_ok=True)
        features.EXTRA_FEATURES.extend(earnings.EARN_FEATURES)
        c = copy.deepcopy(cfg)
        c["model"]["extra_features"] = list(earnings.EARN_FEATURES)
        raw = walk_forward(p2, c, dates)
        raw.to_parquet(out / "raw_scores.parquet")
        new = smooth_scores(raw, k)["ml"]
        ref = pd.read_parquet(cfg["paths"]["reports"] / "backtest" / "scores.parquet")["ml"]
        tag, seeds = "A_earnings_lgbm_secondary", 5
    else:
        out = ROOT / "research" / "results" / "phase3" / "earnings"
        out.mkdir(parents=True, exist_ok=True)
        feats = features.FEATURES + earnings.EARN_FEATURES
        scfg = dataclasses.replace(deep.Stage1Config(), features=feats)
        weeks, vocab = deep.build_weeks(p2, universe, feats)
        tx, log = deep.walk_forward_tx(weeks, vocab, dates, scfg)
        tx.to_parquet(out / "tx_scores.parquet")
        log.to_csv(out / "refit_log.csv", index=False)
        new = smoothed_rank(tx["tx"], k)
        ref = smoothed_rank(pd.read_parquet(RUNS / "run1_main_3seeds" / "tx_scores.parquet")["tx"], k)
        tag, seeds = "A_earnings_tx", 3

    ic_new = weekly_ic(new, panel)
    ic_ref = weekly_ic(ref.reindex(new.index), panel)
    diff = (ic_new - ic_ref).dropna()
    comp = {"ic_variant": float(ic_new.mean()), "ic_reference": float(ic_ref.mean()),
            "diff": float(diff.mean()), "nw_t": float(nw_t(diff)), "weeks": len(diff)}
    if args.secondary:
        traded, trade_cfg = smooth_scores(raw, k)["score"], cfg          # as `main` would trade it
    else:                                                                # as `tx_blend` trades it
        base = baseline_score(panel).reindex(tx.index)
        traded = smooth_scores(pd.DataFrame({"s": 0.7 * rank(tx["tx"]) + 0.3 * rank(base)}), k)["s"]
        trade_cfg = capped
    res, _ = simulate(traded.to_frame("score"), panel, cal, px, universe, fx, trade_cfg, div_tax=div_tax)
    res.to_csv(out / "weekly.csv")
    m = metrics(res["ret"])
    bt = {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
          "turnover": float(res["turnover"].mean()), "p_drop_over_30pct_5y": p_drop(res["ret"].dropna())}
    gate = {**comp, "pass": bool(not args.secondary and comp["nw_t"] >= 2.0 and bt["max_drawdown"] > -0.30)}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"run_at": now, "test": tag, "coverage": coverage, "gate": gate, "backtest": bt}
    (out / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    row = pd.DataFrame([{"run_at": now, "stage": "phase3", "tag": tag, "config": "earnings", "seeds": seeds,
                         "weeks": len(diff), "ic_tx": comp["ic_variant"], "ic_lgbm": comp["ic_reference"],
                         "gate_t": comp["nw_t"], "gate_pass": gate["pass"],
                         "note": args.note or f"CAGR {bt['cagr']:.3f}, MDD {bt['max_drawdown']:.3f}"}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps(result, indent=2, default=float))


if __name__ == "__main__":
    main()
