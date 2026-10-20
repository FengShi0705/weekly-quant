"""Stage 3 real-data run: GRPO through the exact live rules (research/preregistration_stage3.md).

Starts each refit from the Stage 1 models saved by
`research/stage1.py --tag run3_main_10seeds --save-models` (same refit schedule), fine-tunes them with
GRPO (sampled 15-stock portfolios through the exact live order rules and Trading 212 costs), then runs one
continuous closed-loop backtest with the deployed rules: top 15 scores, at most 6 per country and 5 per
sector, no hold band, no smoothing. Writes research/results/stage3/<tag>/ and appends to
research/trials.csv.

Usage: python research/stage3.py [--tag main] [--seeds 3] [--note "..."] [--smoke]
"""
import argparse
import copy
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

from risk_overlays import p_drop  # noqa: E402
from stage1 import nw_t, rank  # noqa: E402
from stage2 import perf  # noqa: E402
from wq import deep, stage2, stage3  # noqa: E402
from wq.backtest import benchmark_returns, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402

OUT = ROOT / "research" / "results" / "stage3"
LEDGER = ROOT / "research" / "trials.csv"
STAGE1_MODELS = ROOT / "research" / "models" / "stage1_run3_main_10seeds"
STAGE1_RUNS = ROOT / "research" / "results" / "stage1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="main")
    ap.add_argument("--seeds", type=int, default=3)
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
    scfg = stage3.Stage3Config()
    seeds = list(range(args.seeds))
    weeks, vocab = deep.build_weeks(panel, universe, s1cfg.features)
    plan = deep.refit_plan(weeks, dates, s1cfg)
    if args.smoke:
        scfg = dataclasses.replace(scfg, steps=3, group=16, weeks_per_step=8)
        seeds, plan = [0], plan[:2]
    d, _ = stage2.build_dense(panel, cal, px, universe, cfg, div_tax)
    row_of = {w: i for i, w in enumerate(d.weeks)}
    out = OUT / ("smoke" if args.smoke else args.tag)
    models_dir = ROOT / "research" / "models" / f"stage3_{'smoke' if args.smoke else args.tag}"
    models_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for k, (window, _, _, _) in enumerate(plan):
        train_idx = [row_of[w.week] for w in window if d.known[row_of[w.week]]]
        for s in seeds:
            jobs.append((f"refit{k:03d}_seed{s}", STAGE1_MODELS / f"refit{k:03d}_seed{s}.pt", train_idx,
                         s * 1000 + k + 11, models_dir / f"refit{k:03d}_seed{s}.pt"))
    t0 = time.time()
    print(f"Stage 3: {len(plan)} refits x {len(seeds)} seeds, {scfg.steps} steps of {scfg.weeks_per_step} weeks"
          f" x {scfg.group} portfolios", flush=True)
    logs = stage3.train_all(d, vocab, jobs, scfg, s1cfg)
    minutes = (time.time() - t0) / 60

    import torch
    models = {}
    for k, (_, _, _, chunk) in enumerate(plan):
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
    s2cfg = stage2.Stage2Config()

    def stage3_fn(T, shares, equity, price):
        return stage2.policy_scores(models[T], d, row_date[T], shares, equity, price, s2cfg)

    dep = stage2.deployed_cfg(cfg)
    dep["portfolio"]["max_per_sector"] = scfg.max_per_sector
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = scfg.max_per_sector
    results = {}
    results["stage3"], trades3 = stage2.simulate_policy(stage3_fn, panel, cal, px, universe, fx, dep, eval_dates,
                                                        div_tax)

    # Comparison arms on the same weeks: the Stage 1 blend with the same 3 seeds (0-2) and with all 10
    # (the tx_blend paper candidate), both with the 5-per-sector cap, and the incumbent.
    lgb = pd.read_parquet(cfg["paths"]["reports"] / "backtest" / "scores.parquet")
    arms = {}
    for name, run in (("blend_3seeds", "run1_main_3seeds"), ("blend_10seeds", "run3_main_10seeds")):
        tx = pd.read_parquet(STAGE1_RUNS / run / "tx_scores.parquet")["tx"]
        base = baseline_score(panel).reindex(tx.index)
        arms[name] = smooth_scores(pd.DataFrame({"s": 0.7 * rank(tx) + 0.3 * rank(base)}), 4)["s"]
    arms["incumbent"] = lgb["score"]
    arms = pd.DataFrame(arms)
    arms = arms[arms.index.get_level_values("date").isin(eval_dates)].dropna(subset=["incumbent"])
    results["stage1_blend_cap5_3seeds"], _ = simulate(arms, panel, cal, px, universe, fx, capped, "blend_3seeds",
                                                      div_tax=div_tax)
    results["stage1_blend_cap5_10seeds"], _ = simulate(arms, panel, cal, px, universe, fx, capped, "blend_10seeds",
                                                       div_tax=div_tax)
    results["incumbent"], _ = simulate(arms, panel, cal, px, universe, fx, cfg, "incumbent", div_tax=div_tax)

    bench = benchmark_returns(panel, eval_dates)
    perf_all = {k: perf(v, bench) for k, v in results.items()}
    for k, v in results.items():
        perf_all[k]["p_drop_over_30pct_5y"] = p_drop(v["ret"].dropna(), n=2000) if not args.smoke else np.nan
    out.mkdir(parents=True, exist_ok=True)
    for k, v in results.items():
        v.to_csv(out / f"weekly_{k}.csv")
    trades3.to_csv(out / "trades_stage3.csv", index=False)
    (out / "training_logs.json").write_text(json.dumps(logs))
    diff = (results["stage3"]["ret"] - results["stage1_blend_cap5_3seeds"]["ret"]).dropna()
    s3, ref = perf_all["stage3"], perf_all["stage1_blend_cap5_10seeds"]
    gate = {"weekly_return_diff_vs_stage1_blend": float(diff.mean()), "nw_t": float(nw_t(diff)),
            "max_drawdown": s3["max_drawdown"], "p_drop_over_30pct_5y": s3["p_drop_over_30pct_5y"],
            "candidate_p_drop": ref["p_drop_over_30pct_5y"],
            "pass": bool(nw_t(diff) >= 1 and s3["max_drawdown"] > -0.30
                         and s3["p_drop_over_30pct_5y"] <= ref["p_drop_over_30pct_5y"])}
    result = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "minutes": round(minutes, 1),
              "stage3_config": dataclasses.asdict(scfg), "seeds": seeds, "weeks": len(eval_dates),
              "gate": gate, "performance": perf_all,
              "training_end": {k: v[-1] for k, v in logs.items()}}
    (out / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    if not args.smoke:
        h = hashlib.sha1(json.dumps(dataclasses.asdict(scfg), sort_keys=True).encode()).hexdigest()[:10]
        row = pd.DataFrame([{"run_at": result["run_at"], "stage": 3, "tag": args.tag, "config": h,
                             "seeds": len(seeds), "weeks": len(eval_dates), "ic_tx": np.nan, "ic_lgbm": np.nan,
                             "gate_t": gate["nw_t"], "gate_pass": gate["pass"], "note": args.note}])
        row.to_csv(LEDGER, mode="a", header=False, index=False)
    print(json.dumps(gate, indent=2, default=float))
    print(pd.DataFrame(perf_all).T.round(4).to_string())


if __name__ == "__main__":
    main()
