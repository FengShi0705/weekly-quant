"""Risk controls on the Stage 1 transformer blend's scores (10-seed run), no retraining.

Variants: base; sector cap 5 per 15; volatility target (exposure = clip(18% / trailing 26-week realised
volatility of the strategy, 0.5, 1)); both. Reports CAGR, Sharpe, worst drop and the bootstrap chance of
a drop beyond 30% within 5 years. Logged in research/trials.csv.
"""
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
from stage1 import rank  # noqa: E402
from wq import stage2  # noqa: E402
from wq.backtest import metrics, prepare  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.costs import dividend_tax_per_share  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402
from wq.model import baseline_score, smooth_scores  # noqa: E402

OUT = ROOT / "research" / "results" / "risk_overlays"


def p_drop(r, limit=-0.30, weeks=260, n=5000, block=8, seed=0):
    rng = np.random.default_rng(seed)
    r = np.asarray(r)
    hits = 0
    for _ in range(n):
        idx = []
        while len(idx) < weeks:
            s = rng.integers(0, len(r))
            idx += [(s + j) % len(r) for j in range(rng.geometric(1 / block))]
        eq = np.cumprod(1 + r[np.array(idx[:weeks])])
        hits += (eq / np.maximum.accumulate(eq) - 1).min() < limit
    return hits / n


def vol_target(target=0.18, window=26, floor=0.5):
    def fn(T, rows):
        if len(rows) < window + 1:
            return 1.0
        eq = np.array([r["equity"] for r in rows[-(window + 1):]])
        vol = np.std(eq[1:] / eq[:-1] - 1, ddof=1) * np.sqrt(52)
        return float(np.clip(target / vol, floor, 1.0)) if vol > 0 else 1.0
    return fn


def main():
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    div_tax = dividend_tax_per_share(px, load_dividends(cfg), universe, cfg)
    tx = pd.read_parquet(ROOT / "research/results/stage1/run3_main_10seeds/tx_scores.parquet")["tx"]
    base = baseline_score(panel).reindex(tx.index)
    scores = smooth_scores(pd.DataFrame({"s": 0.7 * rank(tx) + 0.3 * rank(base)}), 4)["s"]
    dates = scores.index.get_level_values("date").unique()
    capped = copy.deepcopy(cfg)
    capped["portfolio"]["max_per_sector"] = 5
    variants = {"base": (cfg, None), "sector_cap_5": (capped, None), "vol_target_18": (cfg, vol_target()),
                "both": (capped, vol_target())}
    fn = lambda T, sh, eq, pr: scores.xs(T, level="date")
    out, rows = {}, []
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (c, expo) in variants.items():
        res, _ = stage2.simulate_policy(fn, panel, cal, px, universe, fx, c, dates, div_tax, exposure_fn=expo)
        res.to_csv(OUT / f"weekly_{name}.csv")
        m = metrics(res["ret"])
        out[name] = {"cagr": m["cagr"], "ann_vol": m["ann_vol"], "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
                     "mean_exposure": float(res["exposure"].mean()),
                     "p_drop_over_30pct_5y": p_drop(res["ret"].dropna())}
        print(name, {k: round(v, 4) for k, v in out[name].items()}, flush=True)
    (OUT / "summary.json").write_text(json.dumps(out, indent=2))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for name, m in out.items():
        rows.append({"run_at": now, "stage": "risk", "tag": f"tx_blend_{name}", "config": name, "seeds": 10,
                     "weeks": len(dates), "ic_tx": np.nan, "ic_lgbm": np.nan, "gate_t": np.nan, "gate_pass": np.nan,
                     "note": f"risk overlay on Stage 1 blend: CAGR {m['cagr']:.3f}, Sharpe {m['sharpe']:.2f}, "
                             f"MDD {m['max_drawdown']:.3f}, P(>30% drop in 5y) {m['p_drop_over_30pct_5y']:.3f}"})
    pd.DataFrame(rows).to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)


if __name__ == "__main__":
    main()
