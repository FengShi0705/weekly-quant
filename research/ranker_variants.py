"""Ranker improvement trials (research/preregistration_rankers.md).

Usage: python research/ranker_variants.py --variant {lgbm_cat,tx_history,tx_market,ensemble} [--note ...]
Writes research/results/rankers/<variant>/ and appends to research/trials.csv.
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

from stage1 import nw_t, rank, weekly_ic  # noqa: E402
from stage2 import perf  # noqa: E402
from wq import deep  # noqa: E402
from wq.backtest import benchmark_returns, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.features import FEATURES, MARKET_COLS, market_context, weekly_history  # noqa: E402
from wq.model import baseline_score, smooth_scores, walk_forward  # noqa: E402

OUT = ROOT / "research" / "results" / "rankers"
RUNS = ROOT / "research" / "results" / "stage1"


def smoothed_rank(s, k=4):
    return smooth_scores(rank(s).to_frame("s"), k)["s"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, choices=["lgbm_cat", "tx_history", "tx_market", "ensemble"])
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    v = args.variant
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    start = pd.Timestamp(cfg["backtest"]["start"])
    dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    k = cfg["model"]["score_smoothing_weeks"]
    lgb = pd.read_parquet(cfg["paths"]["reports"] / "backtest" / "scores.parquet")
    tx3 = pd.read_parquet(RUNS / "run1_main_3seeds" / "tx_scores.parquet")["tx"]
    tx10 = pd.read_parquet(RUNS / "run3_main_10seeds" / "tx_scores.parquet")["tx"]
    base = baseline_score(panel)
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = 5
    out = OUT / v
    out.mkdir(parents=True, exist_ok=True)

    if v == "lgbm_cat":
        c = copy.deepcopy(cfg)
        c["model"]["categorical"] = True
        raw = walk_forward(panel, c, dates)
        raw.to_parquet(out / "raw_scores.parquet")
        sm = smooth_scores(raw, k)
        new = sm["ml"]
        refs = {"lgbm": lgb["ml"], "tx_10seeds": smoothed_rank(tx10, k)}
        traded, trade_cfg = sm["score"], cfg                      # as `main` would trade it
    else:
        if v == "ensemble":
            new = 0.5 * rank(smoothed_rank(tx10, k)) + 0.5 * rank(lgb["ml"].reindex(tx10.index))
            refs = {"tx_10seeds": smoothed_rank(tx10, k)}
        else:
            if v == "tx_history":
                extra = weekly_history(px, cal.index)
                feats = FEATURES + list(extra.columns)
                p2 = panel.join(extra)
            else:
                extra = market_context(px, cal.index)
                extra.index.name = "date"
                feats = FEATURES + MARKET_COLS
                p2 = panel.join(extra, on="date")
            scfg = dataclasses.replace(deep.Stage1Config(), features=feats)
            weeks, vocab = deep.build_weeks(p2, universe, feats)
            tx, log = deep.walk_forward_tx(weeks, vocab, dates, scfg)
            tx.to_parquet(out / "tx_scores.parquet")
            log.to_csv(out / "refit_log.csv", index=False)
            new = smoothed_rank(tx["tx"], k)
            refs = {"tx_run1_same_seeds": smoothed_rank(tx3, k)}
        new_raw = new
        traded = 0.7 * rank(new_raw) + 0.3 * rank(smooth_scores(base.to_frame("b"), k)["b"].reindex(new_raw.index))
        trade_cfg = capped

    ic_new = weekly_ic(new, panel)
    comparisons = {}
    for name, ref in refs.items():
        ic_ref = weekly_ic(ref.reindex(new.index), panel)
        diff = (ic_new - ic_ref).dropna()
        comparisons[name] = {"ic_variant": float(ic_new.mean()), "ic_reference": float(ic_ref.mean()),
                             "diff": float(diff.mean()), "nw_t": float(nw_t(diff))}
    arms = pd.DataFrame({"traded": traded}).dropna()
    arms = arms[arms.index.get_level_values("date").isin(dates)]
    res, _ = simulate(arms, panel, cal, px, universe, fx, trade_cfg, "traded", div_tax=div_tax)
    bench = benchmark_returns(panel, arms.index.get_level_values("date").unique())
    p = perf(res, bench)
    res.to_csv(out / "weekly.csv")
    key = "lgbm" if v == "lgbm_cat" else list(refs)[0]
    gate = {"vs": key, **comparisons[key],
            "pass": bool(comparisons[key]["nw_t"] >= 2.5 and (v == "lgbm_cat" or p["max_drawdown"] > -0.30))}
    result = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "variant": v,
              "comparisons": comparisons, "gate": gate, "backtest": p}
    (out / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    row = pd.DataFrame([{"run_at": result["run_at"], "stage": "ranker", "tag": v, "config": v,
                         "seeds": 5 if v == "lgbm_cat" else (10 if v == "ensemble" else 3), "weeks": len(ic_new),
                         "ic_tx": comparisons[key]["ic_variant"], "ic_lgbm": comparisons[key]["ic_reference"],
                         "gate_t": gate["nw_t"], "gate_pass": gate["pass"], "note": args.note}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps({"comparisons": comparisons, "gate": gate}, indent=2))
    print({k2: round(v2, 4) for k2, v2 in p.items()})


if __name__ == "__main__":
    main()
