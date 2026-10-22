"""New feature sets for the Stage 1 transformer (research/preregistration_features.md).

Usage: python research/feature_sets_trial.py --set {peer,shape,calendar,fx,all} [--note ...]
Writes research/results/features/<set>/ and appends to research/trials.csv. Resumable (per-fit cache).
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

from horizon_trial import RUN1  # noqa: E402
from ranker_variants import smoothed_rank  # noqa: E402
from risk_overlays import p_drop  # noqa: E402
from stage1 import nw_t, rank, weekly_ic  # noqa: E402
from wq import deep, features, features_extra  # noqa: E402
from wq.backtest import metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402


def tilt_backtest(tx, panel, cal, px, universe, fx, cfg, div_tax, k):
    """The tx_blend_tilt strategy on these transformer scores."""
    base = baseline_score(panel).reindex(tx.index)
    s = smooth_scores(pd.DataFrame({"s": 0.7 * rank(tx) + 0.3 * rank(base)}), k)["s"]
    c = copy.deepcopy(cfg)
    c["portfolio"].update(max_per_sector=5, weighting="score_tilt")
    res, _ = simulate(s.to_frame("score"), panel, cal, px, universe, fx, c, div_tax=div_tax)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=list(features_extra.SETS))
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_yield = load_dividends(cfg)
    div_tax = dividend_tax_per_share(px, div_yield, universe, cfg)
    start = pd.Timestamp(cfg["backtest"]["start"])
    dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    k = cfg["model"]["score_smoothing_weeks"]
    out = ROOT / "research" / "results" / "features" / args.set
    (out / "cache").mkdir(parents=True, exist_ok=True)

    earn_path = cfg["data"]["cache_dir"] / "earnings.parquet"
    earn = pd.read_parquet(earn_path) if earn_path.exists() else None
    extra = features_extra.build(args.set, px, close, volume, universe, div_yield, earn, cal.index)
    extra = extra.reindex(panel.index)
    extra = extra.groupby(level="date").rank(pct=True) - 0.5
    p2 = panel.join(extra)
    live = p2[p2.index.get_level_values("date") >= start]
    coverage = {f: float(live[f].notna().mean()) for f in extra.columns}
    print("coverage", json.dumps({f: round(v, 3) for f, v in coverage.items()}), flush=True)

    feats = features.FEATURES + features_extra.SETS[args.set]
    scfg = dataclasses.replace(deep.Stage1Config(), features=feats, cache_dir=str(out / "cache"))
    weeks, vocab = deep.build_weeks(p2, universe, feats)
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
            "diff_by_period": {p: float(d[(yr >= a) & (yr <= b)].mean())
                               for p, (a, b) in {"2016-18": (2016, 2018), "2019-21": (2019, 2021), "2022-26": (2022, 2026)}.items()}}

    res = tilt_backtest(tx["tx"], panel, cal, px, universe, fx, cfg, div_tax, k)
    res_ref = tilt_backtest(tx1, panel, cal, px, universe, fx, cfg, div_tax, k)
    res.to_csv(out / "weekly.csv")
    m, mr = metrics(res["ret"]), metrics(res_ref["ret"])
    dr = (res["ret"] - res_ref["ret"]).dropna()
    bt = {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
          "turnover": float(res["turnover"].mean()), "p_drop_over_30pct_5y": float(p_drop(res["ret"].dropna())),
          "reference_cagr": mr["cagr"], "reference_max_drawdown": mr["max_drawdown"],
          "weekly_return_diff_per_year": float(dr.mean() * 52), "weekly_return_diff_nw_t": float(nw_t(dr))}
    gate = {**comp, "pass": bool(comp["nw_t"] >= 2.4 and bt["max_drawdown"] > -0.30 and bt["p_drop_over_30pct_5y"] <= 0.20)}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out / "summary.json").write_text(json.dumps({"run_at": now, "set": args.set, "features": features_extra.SETS[args.set],
                                                  "coverage": coverage, "gate": gate, "backtest": bt}, indent=2, default=float))
    row = pd.DataFrame([{"run_at": now, "stage": "features", "tag": f"features_{args.set}", "config": args.set,
                         "seeds": 3, "weeks": len(d), "ic_tx": comp["ic_variant"], "ic_lgbm": comp["ic_reference"],
                         "gate_t": comp["nw_t"], "gate_pass": gate["pass"],
                         "note": args.note or f"tilt CAGR {bt['cagr']:.3f} vs {bt['reference_cagr']:.3f}, MDD {bt['max_drawdown']:.3f}"}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps({"gate": gate, "backtest": bt}, indent=2, default=float))


if __name__ == "__main__":
    main()
