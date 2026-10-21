"""Phase 3, test B2: `tx_blend` with orders only every 4th (or 2nd) week (research/preregistration_phase3.md).

Usage: python research/frequency_trial.py [--note ...]
Writes research/results/phase3/frequency/ and appends to research/trials.csv.
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
from wq.backtest import metrics, prepare  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax, dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe, usd_per_base  # noqa: E402
from wq.features import market_index  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402
from wq.portfolio import execute, generate_orders, regime_exposure, select_targets  # noqa: E402

RUN = ROOT / "research" / "results" / "stage1" / "run3_main_10seeds"
OUT = ROOT / "research" / "results" / "phase3" / "frequency"


def simulate_every(scores, panel, cal, px, universe, fx_usd, cfg, every=1, offset=0, div_tax=None):
    """backtest.simulate, but orders are generated only on weeks i with i % every == offset.
    The account is still valued, and dividend tax charged, every week."""
    base = cfg["account"]["base_currency"]
    px_val = px.ffill()
    mkt_w = market_index(px).reindex(cal.index, method="ffill")
    cash = float(cfg["account"]["capital"])
    shares, rows, prev_e = {}, [], None
    for i, T in enumerate(scores.index.get_level_values("date").unique()):
        e = cal.loc[T, "exec_date"]
        if pd.isna(e):
            break
        price = px_val.loc[e]
        withheld = dividend_tax(shares, div_tax, prev_e, e)
        cash -= withheld
        prev_e = e
        equity = cash + sum(q * price[t] for t, q in shares.items())
        cost, turnover = 0.0, 0.0
        if i % every == offset:
            s = scores.xs(T, level="date")
            expo = regime_exposure(mkt_w, T, cfg)
            vol = panel.xs(T, level="date")["raw_vol_60"]
            targets = select_targets(s, set(shares), universe, price, equity, cfg, expo, vol)
            orders = generate_orders(shares, targets, price, equity, universe, cfg, cash)
            shares, cash, cost, filled = execute(orders, shares, cash, price, universe, cfg,
                                                 usd_per_base(fx_usd, base, e))
            turnover = sum(o["value"] for o in filled) / equity if equity > 0 else 0.0
        rows.append({"signal_date": T, "exec_date": e, "equity": equity, "cost": cost, "turnover": turnover})
    res = pd.DataFrame(rows).set_index("signal_date")
    res["ret"] = res["equity"].shift(-1) / res["equity"] - 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = 5
    tx = pd.read_parquet(RUN / "tx_scores.parquet")["tx"]
    base = baseline_score(panel).reindex(tx.index)
    s = smooth_scores(pd.DataFrame({"s": 0.7 * rank(tx) + 0.3 * rank(base)}), cfg["model"]["score_smoothing_weeks"])["s"]
    OUT.mkdir(parents=True, exist_ok=True)

    run = lambda every, off: simulate_every(s, panel, cal, px, universe, fx, capped, every, off, div_tax)
    weekly = run(1, 0)
    years = len(weekly) / 52

    def summary(res):
        m = metrics(res["ret"])
        return {"cagr": m["cagr"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
                "cost_per_year": float((res["cost"] / res["equity"]).sum() / years),
                "turnover_per_week": float(res["turnover"].mean()), "p_drop_over_30pct_5y": p_drop(res["ret"].dropna())}

    arms = {"weekly": summary(weekly)}
    diffs = {}
    for every, offs in [(4, range(4)), (2, range(2))]:
        for off in offs:
            name = f"every{every}_offset{off}"
            res = run(every, off)
            res.to_csv(OUT / f"{name}.csv")
            arms[name] = summary(res)
            d = (res["ret"] - weekly["ret"]).dropna()
            arms[name]["diff_per_year"] = float(d.mean() * 52)
            arms[name]["nw_t_alone"] = float(nw_t(d))
            diffs[name] = d
            print(name, {k: round(v, 4) for k, v in arms[name].items()}, flush=True)
    avg4 = pd.concat([diffs[f"every4_offset{o}"] for o in range(4)], axis=1).mean(axis=1)
    four = [arms[f"every4_offset{o}"] for o in range(4)]
    gate = {"diff_per_year": float(avg4.mean() * 52), "nw_t": float(nw_t(avg4)), "weeks": len(avg4),
            "all_beat_weekly_cagr": all(a["cagr"] > arms["weekly"]["cagr"] for a in four),
            "all_drops_ok": all(a["max_drawdown"] > -0.30 for a in four)}
    gate["pass"] = bool(gate["nw_t"] >= 2.0 and gate["all_beat_weekly_cagr"] and gate["all_drops_ok"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (OUT / "summary.json").write_text(json.dumps({"run_at": now, "arms": arms, "gate": gate}, indent=2, default=float))
    cagrs = ", ".join(f"{a['cagr']:.3f}" for a in four)
    row = pd.DataFrame([{"run_at": now, "stage": "phase3", "tag": "B2_every_4_weeks", "config": "every4",
                         "seeds": 10, "weeks": len(avg4), "ic_tx": "", "ic_lgbm": "", "gate_t": gate["nw_t"],
                         "gate_pass": gate["pass"],
                         "note": args.note or f"offset CAGRs {cagrs} vs weekly {arms['weekly']['cagr']:.3f}"}])
    row.to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps(gate, indent=2, default=float))


if __name__ == "__main__":
    main()
