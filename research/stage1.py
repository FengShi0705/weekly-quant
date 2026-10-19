"""Stage 1 real-data run: transformer ranker vs LightGBM (research/preregistration_stage1.md).

Needs the LightGBM backtest's per-stock scores (reports/backtest/scores.parquet, written by
`python -m wq backtest`). Writes research/results/stage1/ and appends a row to research/trials.csv.

Usage: python research/stage1.py [--note "why this run"]
"""
import argparse
import dataclasses
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wq import deep  # noqa: E402
from wq.backtest import benchmark_returns, metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402

OUT = ROOT / "research" / "results" / "stage1"
LEDGER = ROOT / "research" / "trials.csv"


def rank(s):
    return s.groupby(level="date").rank(pct=True) - 0.5


def weekly_ic(score, panel):
    df = pd.DataFrame({"s": score}).join(panel[["fwd_ret_1w"]]).dropna()
    return df.groupby(level="date").apply(lambda g: g["s"].rank().corr(g["fwd_ret_1w"].rank()) if len(g) >= 10
                                          else np.nan).dropna()


def nw_t(x, lags=4):
    """Newey-West t-statistic of the mean of x."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n, e = len(x), x - x.mean()
    var = e @ e / n
    for k in range(1, lags + 1):
        var += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / np.sqrt(var / n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="")
    ap.add_argument("--smoke", action="store_true", help="tiny run on the last year to check the pipeline; "
                    "writes to research/results/stage1_smoke and skips the trial ledger")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    start = pd.Timestamp(cfg["backtest"]["start"])
    dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    lgb = pd.read_parquet(cfg["paths"]["reports"] / "backtest" / "scores.parquet")

    scfg = deep.Stage1Config()
    out = OUT
    if args.smoke:
        scfg = dataclasses.replace(scfg, seeds=(0,), max_epochs=2, patience=1)
        dates, out = dates[-52:], OUT.parent / "stage1_smoke"
    weeks, vocab = deep.build_weeks(panel, universe, scfg.features)
    t0 = time.time()
    print(f"Stage 1: {len(dates)} weeks, {len(scfg.seeds)} seeds, refit every {scfg.refit_every_weeks} weeks")
    tx, log = deep.walk_forward_tx(weeks, vocab, dates, scfg)
    minutes = (time.time() - t0) / 60
    out.mkdir(parents=True, exist_ok=True)
    tx.to_parquet(out / "tx_scores.parquet")
    log.to_csv(out / "refit_log.csv", index=False)

    # Traded scores for each arm, all smoothed like the deployed strategy.
    k = cfg["model"]["score_smoothing_weeks"]
    base = baseline_score(panel).reindex(tx.index)
    raw = pd.DataFrame({"tx": rank(tx["tx"]), "tx_blend": 0.7 * rank(tx["tx"]) + 0.3 * rank(base)})
    arms = smooth_scores(raw, k)
    arms["incumbent"] = lgb["score"].reindex(arms.index)
    arms["lgbm_ml"] = lgb["ml"].reindex(arms.index)
    arms["fifty_fifty"] = 0.5 * rank(arms["incumbent"]) + 0.5 * rank(arms["tx_blend"])
    arms = arms.dropna(subset=["incumbent"])

    ic = pd.DataFrame({c: weekly_ic(arms[c], panel) for c in arms.columns})
    ic_tx_raw = weekly_ic(tx["tx"], panel)
    diff = (ic["tx"] - ic["lgbm_ml"]).dropna()
    ic_summary = {c: {"mean": float(ic[c].mean()), "nw_t": float(nw_t(ic[c]))} for c in ic.columns}
    ic_summary["tx_unsmoothed"] = {"mean": float(ic_tx_raw.mean()), "nw_t": float(nw_t(ic_tx_raw))}
    gate = {"ic_diff_tx_minus_lgbm": float(diff.mean()), "nw_t": float(nw_t(diff)),
            "pass": bool(nw_t(diff) > -1)}

    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    bench = benchmark_returns(panel, arms.index.get_level_values("date").unique())
    perf = {}
    for arm in ("incumbent", "tx", "tx_blend", "fifty_fifty"):
        res, _ = simulate(arms, panel, cal, px, universe, fx, cfg, arm, div_tax=div_tax)
        m = metrics(res["ret"])
        yr = pd.DataFrame({"s": res["ret"], "b": bench.reindex(res.index)}).dropna()
        by_year = (1 + yr).groupby(yr.index.year).prod() - 1
        active = by_year["s"] - by_year["b"]
        perf[arm] = {"final_value": float(res["equity"].iloc[-1]), "cagr": m["cagr"], "ann_vol": m["ann_vol"],
                     "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
                     "turnover": float(res["turnover"].mean()),
                     "cost_per_year": float((res["cost"] / res["equity"]).sum() / (len(res) / 52)),
                     "active_vs_equal_weight": float(active.mean()),
                     "active_t": float(active.mean() / active.std() * np.sqrt(len(active)))}
        res.to_csv(out / f"weekly_{arm}.csv")

    result = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "minutes": round(minutes, 1),
              "config": dataclasses.asdict(scfg), "ic": ic_summary, "gate": gate, "performance": perf,
              "epochs": log["epochs"].describe().to_dict()}
    (out / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    cfg_hash = hashlib.sha1(json.dumps(dataclasses.asdict(scfg), sort_keys=True).encode()).hexdigest()[:10]
    row = pd.DataFrame([{"run_at": result["run_at"], "stage": 1, "config": cfg_hash, "seeds": len(scfg.seeds),
                         "weeks": len(ic), "ic_tx": ic_summary["tx"]["mean"], "ic_lgbm": ic_summary["lgbm_ml"]["mean"],
                         "gate_t": gate["nw_t"], "gate_pass": gate["pass"], "note": args.note}])
    if not args.smoke:
        row.to_csv(LEDGER, mode="a", header=not LEDGER.exists(), index=False)
    print(json.dumps({"ic": ic_summary, "gate": gate}, indent=2))
    print(pd.DataFrame(perf).T.round(4).to_string())


if __name__ == "__main__":
    main()
