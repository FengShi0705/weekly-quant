"""Phase 3, test H: analyst rating and price-target changes as transformer inputs
(research/preregistration_phase3.md).

Usage: python research/analyst_trial.py [--note ...]
Needs data/cache/analyst.parquet (wq.analyst.fetch). Writes research/results/phase3/analyst/.
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
from wq import analyst, deep, features  # noqa: E402
from wq.backtest import metrics, prepare  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402

OUT = ROOT / "research" / "results" / "phase3" / "analyst"


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
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cache").mkdir(exist_ok=True)

    af = analyst.features(pd.read_parquet(cfg["data"]["cache_dir"] / "analyst.parquet"), cal.index)
    af = af.groupby(level="date").rank(pct=True) - 0.5
    p2 = panel.join(af.reindex(panel.index))
    live = p2[p2.index.get_level_values("date") >= start]
    us = live.index.get_level_values("ticker").map(universe["region"]) == "US"
    coverage = {"any_action_13w_all": float((live["rev_net_13w"].notna()).mean()),
                "pt_rev_4w_us": float(live.loc[us, "pt_rev_4w"].notna().mean())}
    print("coverage", coverage, flush=True)

    feats = features.FEATURES + analyst.ANALYST_FEATURES
    scfg = dataclasses.replace(deep.Stage1Config(), features=feats, cache_dir=str(OUT / "cache"))
    weeks, vocab = deep.build_weeks(p2, universe, feats)
    tx, log = deep.walk_forward_tx(weeks, vocab, dates, scfg)
    tx.to_parquet(OUT / "tx_scores.parquet")
    log.to_csv(OUT / "refit_log.csv", index=False)
    tx1 = pd.read_parquet(RUN1 / "tx_scores.parquet")["tx"]
    new, ref = smoothed_rank(tx["tx"], k), smoothed_rank(tx1, k).reindex(tx.index)
    ic_new, ic_ref = weekly_ic(new, panel), weekly_ic(ref, panel)
    d = (ic_new - ic_ref).dropna()
    us_idx = new.index[new.index.get_level_values("ticker").map(universe["region"]) == "US"]
    ic_us_new, ic_us_ref = weekly_ic(new.reindex(us_idx), panel), weekly_ic(ref.reindex(us_idx), panel)
    d_us = (ic_us_new - ic_us_ref).dropna()
    comp = {"ic_variant": float(ic_new.mean()), "ic_reference": float(ic_ref.mean()), "diff": float(d.mean()),
            "nw_t": float(nw_t(d)), "weeks": len(d),
            "us_only": {"ic_variant": float(ic_us_new.mean()), "ic_reference": float(ic_us_ref.mean()),
                        "nw_t": float(nw_t(d_us))}}
    res = blend_backtest(tx["tx"], panel, cal, px, universe, fx, capped, div_tax, k)
    res.to_csv(OUT / "weekly.csv")
    m = metrics(res["ret"])
    bt = {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
          "turnover": float(res["turnover"].mean()), "p_drop_over_30pct_5y": float(p_drop(res["ret"].dropna()))}
    gate = {**comp, "pass": bool(comp["nw_t"] >= 2.0 and bt["max_drawdown"] > -0.30)}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (OUT / "summary.json").write_text(json.dumps({"run_at": now, "coverage": coverage, "gate": gate, "backtest": bt},
                                                 indent=2, default=float))
    row = pd.DataFrame([{"run_at": now, "stage": "phase3", "tag": "H_analyst_tx", "config": "analyst", "seeds": 3,
                         "weeks": len(d), "ic_tx": comp["ic_variant"], "ic_lgbm": comp["ic_reference"],
                         "gate_t": comp["nw_t"], "gate_pass": gate["pass"],
                         "note": args.note or f"CAGR {bt['cagr']:.3f}, MDD {bt['max_drawdown']:.3f}"}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps({"gate": gate, "backtest": bt}, indent=2, default=float))


if __name__ == "__main__":
    main()
