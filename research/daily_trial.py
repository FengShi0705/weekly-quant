"""Phase 3, test B: trading `tx_blend` every day instead of every week (research/preregistration_phase3.md).

The saved 10-seed Stage 1 models (run3_main_10seeds) score every trading day's features; the blend is
averaged over the last 20 trading days and traded at the next close under today's rules. Compared with
the weekly `tx_blend` on the weekly arm's Monday fill dates. Information arm: orders every fourth week.

Usage: python research/daily_trial.py [--note ...]
Writes research/results/phase3/daily/ and appends to research/trials.csv.
"""
import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from risk_overlays import p_drop  # noqa: E402
from stage1 import nw_t, rank  # noqa: E402
from wq import deep  # noqa: E402
from wq.backtest import metrics, prepare, simulate  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe, to_base  # noqa: E402
from wq.features import build_panel, daily_calendar  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402

RUN = ROOT / "research" / "results" / "stage1" / "run3_main_10seeds"
MODELS = ROOT / "research" / "models" / "stage1_run3_main_10seeds"
OUT = ROOT / "research" / "results" / "phase3" / "daily"


def daily_tx(panel_d, universe, refits, seeds=range(10)):
    """Score every day with the models of the refit block it falls in; seeds z-scored per day, averaged."""
    torch = deep._torch()
    torch.set_num_threads(4)
    cfg = deep.Stage1Config()
    first = pd.Timestamp(refits["first_date"].min())
    weeks, vocab = deep.build_weeks(panel_d[panel_d.index.get_level_values("date") >= first], universe)
    starts = refits.sort_values("refit")
    bounds = list(pd.to_datetime(starts["first_date"])) + [pd.Timestamp.max]
    rows = []
    for i, (r, lo) in enumerate(zip(starts["refit"], bounds[:-1])):
        days = [w for w in weeks if lo <= w.date < bounds[i + 1]]
        if not days:
            continue
        for s in seeds:
            m = deep.make_model(weeks[0].x.shape[1], vocab, cfg)
            m.load_state_dict(torch.load(MODELS / f"refit{int(r):03d}_seed{s}.pt"))
            for w, sc in zip(days, deep._score(m, days)):
                rows.append(pd.DataFrame({"date": w.date, "ticker": w.tickers, "tx": sc, "seed": s}))
        print(f"  refit {int(r)}: {len(days)} days scored", flush=True)
    return deep._average_seeds(pd.concat(rows))["tx"]


def blend(tx, panel, k):
    base = baseline_score(panel).reindex(tx.index)
    return smooth_scores(pd.DataFrame({"s": 0.7 * rank(tx) + 0.3 * rank(base)}), k)["s"]


def on_dates(res, exec_dates):
    """Account value read on the given fill dates (before that day's trades)."""
    eq = res.set_index("exec_date")["equity"]
    return eq.reindex(exec_dates)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel_w, cal_w, px = prepare(cfg, close, volume, fx, universe)
    px_base = to_base(close, universe["currency"], fx, cfg["account"]["base_currency"])
    panel_d, cal_d, _ = build_panel(px_base, volume, universe, cfg, calendar=daily_calendar)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = 5
    OUT.mkdir(parents=True, exist_ok=True)

    tx_w = pd.read_parquet(RUN / "tx_scores.parquet")["tx"]
    refits = pd.read_csv(RUN / "refit_log.csv")[["refit", "first_date"]].drop_duplicates()
    path = OUT / "tx_daily.parquet"
    if path.exists():
        tx_d = pd.read_parquet(path)["tx"]
    else:
        tx_d = daily_tx(panel_d, universe, refits)
        tx_d.to_frame().to_parquet(path)
    # The same models on the same Friday features must give the weekly run's scores.
    both = pd.DataFrame({"w": tx_w, "d": tx_d.reindex(tx_w.index)}).dropna()
    check = float((both["w"] - both["d"]).abs().max())
    print(f"Friday scores: daily vs weekly run, max difference {check:.2e} over {len(both)} rows", flush=True)
    assert check < 1e-4, "daily scoring does not reproduce the weekly scores"

    k = cfg["model"]["score_smoothing_weeks"]
    s_w = blend(tx_w, panel_w, k)
    s_d = blend(tx_d, panel_d, 5 * k)
    res_w, tr_w = simulate(s_w.to_frame("score"), panel_w, cal_w, px, universe, fx, capped, div_tax=div_tax)
    res_d, tr_d = simulate(s_d.to_frame("score"), panel_d, cal_d, px, universe, fx, capped, div_tax=div_tax)
    dates_w = s_w.index.get_level_values("date").unique()
    res_4, tr_4 = simulate(s_w[s_w.index.get_level_values("date").isin(dates_w[::4])].to_frame("score"),
                           panel_w, cal_w, px, universe, fx, capped, div_tax=div_tax)
    for name, r in [("weekly", res_w), ("daily", res_d), ("every4", res_4)]:
        r.to_csv(OUT / f"{name}.csv")

    ex = res_w["exec_date"]
    eq_d = on_dates(res_d, ex)
    r_d = pd.Series(eq_d.shift(-1).to_numpy() / eq_d.to_numpy() - 1, index=res_w.index)
    r_w = res_w["ret"]
    diff = (r_d - r_w).dropna()
    years = len(res_w) / 52

    def summary(r, res):
        m = metrics(r)
        return {"cagr": m["cagr"], "ann_vol": m["ann_vol"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
                "cost_per_year": float((res["cost"] / res["equity"]).sum() / years),
                "turnover_per_week": float(res["turnover"].sum() / len(res_w)),
                "days_with_trades_per_year": float((res["turnover"] > 0).sum() / years),
                "p_drop_over_30pct_5y": p_drop(r.dropna())}

    out = {"weekly": summary(r_w, res_w), "daily": summary(r_d, res_d)}
    e4 = res_4.set_index("exec_date")["equity"]
    r4 = (e4.shift(-1) / e4 - 1).dropna()
    eq4 = (1 + r4).cumprod()
    out["every4_info"] = {"cagr": float(eq4.iloc[-1] ** (1 / (len(r4) * 4 / 52)) - 1),
                          "sharpe": float(r4.mean() / r4.std() * np.sqrt(13)),
                          "max_drawdown_4weekly": float((eq4 / eq4.cummax() - 1).min()),
                          "cost_per_year": float((res_4["cost"] / res_4["equity"]).sum() / years)}
    gate = {"diff_mean_weekly": float(diff.mean()), "diff_per_year": float(diff.mean() * 52),
            "nw_t": float(nw_t(diff)), "weeks": len(diff)}
    gate["pass"] = bool(gate["nw_t"] >= 2.0 and out["daily"]["max_drawdown"] > -0.30)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"run_at": now, "friday_check_max_diff": check, "arms": out, "gate": gate,
              "orders": {"weekly": len(tr_w), "daily": len(tr_d), "every4": len(tr_4)}}
    (OUT / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    row = pd.DataFrame([{"run_at": now, "stage": "phase3", "tag": "B_daily_trading", "config": "daily",
                         "seeds": 10, "weeks": len(diff), "ic_tx": "", "ic_lgbm": "", "gate_t": gate["nw_t"],
                         "gate_pass": gate["pass"],
                         "note": args.note or (f"daily CAGR {out['daily']['cagr']:.3f} vs weekly {out['weekly']['cagr']:.3f}, "
                                               f"MDD {out['daily']['max_drawdown']:.3f}")}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps(result, indent=2, default=float))


if __name__ == "__main__":
    main()
