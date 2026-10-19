"""Stage 2 real-data run (research/preregistration_stage2.md).

Starts each refit from the Stage 1 models saved by
`research/stage1.py --tag run3_main_10seeds --save-models` (same refit schedule), fine-tunes them with
closed-loop soft rollouts, then runs one continuous closed-loop backtest with the deployed rules.
Writes research/results/stage2/<tag>/ and appends to research/trials.csv.

Usage: python research/stage2.py [--tag main] [--seeds 3] [--gamma 2.0] [--note "..."]
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
sys.path.insert(0, str(ROOT / "research"))

from stage1 import nw_t, rank  # noqa: E402
from wq import deep, stage2  # noqa: E402
from wq.backtest import benchmark_returns, metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402

OUT = ROOT / "research" / "results" / "stage2"
LEDGER = ROOT / "research" / "trials.csv"
STAGE1_MODELS = ROOT / "research" / "models" / "stage1_run3_main_10seeds"
STAGE1_SCORES = ROOT / "research" / "results" / "stage1" / "run1_main_3seeds" / "tx_scores.parquet"


def perf(res, bench):
    m = metrics(res["ret"])
    yr = pd.DataFrame({"s": res["ret"], "b": bench.reindex(res.index)}).dropna()
    by_year = (1 + yr).groupby(yr.index.year).prod() - 1
    active = by_year["s"] - by_year["b"]
    return {"final_value": float(res["equity"].iloc[-1]), "cagr": m["cagr"], "ann_vol": m["ann_vol"],
            "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"], "turnover": float(res["turnover"].mean()),
            "cost_per_year": float((res["cost"] / res["equity"]).sum() / (len(res) / 52)),
            "active_vs_equal_weight": float(active.mean()),
            "active_t": float(active.mean() / active.std() * np.sqrt(len(active)))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="main")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--gamma", type=float, default=2.0)
    ap.add_argument("--note", default="")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    start = pd.Timestamp(cfg["backtest"]["start"])
    dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    s1cfg = deep.Stage1Config()
    scfg = stage2.Stage2Config(gamma=args.gamma)
    seeds = list(range(args.seeds))
    if args.smoke:
        scfg = dataclasses.replace(scfg, steps=5)
        seeds = [0]

    weeks, vocab = deep.build_weeks(panel, universe, s1cfg.features)
    plan = deep.refit_plan(weeks, dates, s1cfg)
    if args.smoke:
        plan = plan[:2]                    # the first refits' Stage 1 models are saved first
    d, _ = stage2.build_dense(panel, cal, px, universe, cfg, div_tax)
    row_of = {w: i for i, w in enumerate(d.weeks)}
    out = OUT / (args.tag if not args.smoke else "smoke")
    models_dir = ROOT / "research" / "models" / f"stage2_{args.tag}"
    models_dir.mkdir(parents=True, exist_ok=True)
    offset = 0

    jobs = []
    for i, (window, _, _, chunk) in enumerate(plan):
        k = i + offset
        train_idx = [row_of[w.week] for w in window if d.known[row_of[w.week]]]
        for s in seeds:
            jobs.append((f"refit{k:03d}_seed{s}", STAGE1_MODELS / f"refit{k:03d}_seed{s}.pt", train_idx,
                         s * 1000 + k + 7, models_dir / f"refit{k:03d}_seed{s}.pt"))
    t0 = time.time()
    print(f"Stage 2: {len(plan)} refits x {len(seeds)} seeds, {scfg.steps} steps each", flush=True)
    stage2.train_all(d, vocab, jobs, scfg, s1cfg)
    minutes = (time.time() - t0) / 60

    import torch
    models = {}
    for i, (_, _, _, chunk) in enumerate(plan):
        k = i + offset
        ms = []
        for s in seeds:
            m = deep.make_model(d.x.shape[2], vocab, s1cfg, two_heads=True)
            m.load_state_dict(torch.load(models_dir / f"refit{k:03d}_seed{s}.pt"))
            m.eval()
            ms.append(m)
        for w in chunk:
            models[w.date] = ms
    eval_dates = [dt for dt in dates if dt in models]
    row_date = {dt: i for i, dt in enumerate(d.dates)}

    def stage2_fn(T, shares, equity, price):
        return stage2.policy_scores(models[T], d, row_date[T], shares, equity, price, scfg)

    dep = stage2.deployed_cfg(cfg)
    res2, trades2 = stage2.simulate_policy(stage2_fn, panel, cal, px, universe, fx, dep, eval_dates, div_tax)

    # Comparison arms on the same weeks.
    tx = pd.read_parquet(STAGE1_SCORES)["tx"]
    lgb = pd.read_parquet(cfg["paths"]["reports"] / "backtest" / "scores.parquet")
    base = baseline_score(panel).reindex(tx.index)
    arms = smooth_scores(pd.DataFrame({"tx_blend": 0.7 * rank(tx) + 0.3 * rank(base)}), 4)
    arms["incumbent"] = lgb["score"].reindex(arms.index)
    arms["tx_raw"] = rank(tx)
    arms = arms[arms.index.get_level_values("date").isin(eval_dates)].dropna(subset=["incumbent"])
    bench = benchmark_returns(panel, eval_dates)
    results = {"stage2": res2}
    results["incumbent"], _ = simulate(arms, panel, cal, px, universe, fx, cfg, "incumbent", div_tax=div_tax)
    results["stage1_tx_blend"], _ = simulate(arms, panel, cal, px, universe, fx, cfg, "tx_blend", div_tax=div_tax)
    results["stage1_deployed_rules"], _ = simulate(arms, panel, cal, px, universe, fx, dep, "tx_raw", div_tax=div_tax)

    out.mkdir(parents=True, exist_ok=True)
    perf_all = {k: perf(v, bench) for k, v in results.items()}
    for k, v in results.items():
        v.to_csv(out / f"weekly_{k}.csv")
    trades2.to_csv(out / "trades_stage2.csv", index=False)
    diff = (results["stage2"]["ret"] - results["stage1_tx_blend"]["ret"]).dropna()
    gate = {"weekly_return_diff_vs_stage1_blend": float(diff.mean()), "nw_t": float(nw_t(diff)),
            "max_drawdown": perf_all["stage2"]["max_drawdown"],
            "pass": bool(diff.mean() > 0 and perf_all["stage2"]["max_drawdown"] > -0.30)}
    result = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "minutes": round(minutes, 1),
              "stage2_config": dataclasses.asdict(scfg), "seeds": seeds, "weeks": len(eval_dates),
              "gate": gate, "performance": perf_all}
    (out / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    if not args.smoke:
        h = hashlib.sha1(json.dumps(dataclasses.asdict(scfg), sort_keys=True).encode()).hexdigest()[:10]
        row = pd.DataFrame([{"run_at": result["run_at"], "stage": 2, "tag": args.tag, "config": h,
                             "seeds": len(seeds), "weeks": len(eval_dates), "ic_tx": np.nan, "ic_lgbm": np.nan,
                             "gate_t": gate["nw_t"], "gate_pass": gate["pass"], "note": args.note}])
        row.to_csv(LEDGER, mode="a", header=False, index=False)
    print(json.dumps(gate, indent=2))
    print(pd.DataFrame(perf_all).T.round(4).to_string())


if __name__ == "__main__":
    main()
