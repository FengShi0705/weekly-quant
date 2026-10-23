"""Information only (decides nothing): does each new feature predict next week's return on its own, and
does it still predict once the current transformer score (Stage 1 run 3, smoothed) is accounted for?

Usage: python research/feature_diagnostics.py   ->  research/results/features/diagnostics.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from ranker_variants import smoothed_rank  # noqa: E402
from stage1 import nw_t  # noqa: E402
from wq import features_extra  # noqa: E402
from wq.backtest import prepare  # noqa: E402
from wq.config import load_config  # noqa: E402
from wq.data import load_cached, load_dividends, load_universe  # noqa: E402


def main():
    cfg = load_config(str(ROOT / "config.yaml"))
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    earn = pd.read_parquet(cfg["data"]["cache_dir"] / "earnings.parquet")
    x = features_extra.build("all", px, close, volume, universe, load_dividends(cfg), earn, cal.index).reindex(panel.index)
    x = x.groupby(level="date").rank(pct=True) - 0.5
    tx = pd.read_parquet(ROOT / "research/results/stage1/run3_main_10seeds/tx_scores.parquet")["tx"]
    score = smoothed_rank(tx, cfg["model"]["score_smoothing_weeks"])
    df = x.join(score.rename("score")).join(panel[["fwd_ret_1w"]]).dropna(subset=["score", "fwd_ret_1w"])
    df["y"] = df.groupby(level="date")["fwd_ret_1w"].rank(pct=True) - 0.5
    # the part of each week's return ranks the current score does not explain
    def resid(g):
        b = np.polyfit(g["score"], g["y"], 1)
        return g["y"] - np.polyval(b, g["score"])
    df["y_res"] = df.groupby(level="date", group_keys=False).apply(resid)
    rows = []
    for f in features_extra.SETS["all"]:
        g = df[[f, "y", "y_res"]].dropna()
        ic = g.groupby(level="date").apply(lambda h: h[f].corr(h["y"], method="spearman") if len(h) >= 20 else np.nan).dropna()
        icr = g.groupby(level="date").apply(lambda h: h[f].corr(h["y_res"], method="spearman") if len(h) >= 20 else np.nan).dropna()
        rows.append({"feature": f, "ic": ic.mean(), "ic_t": nw_t(ic), "ic_beyond_model": icr.mean(), "ic_beyond_model_t": nw_t(icr),
                     "corr_with_score": df[[f, "score"]].dropna().corr().iloc[0, 1]})
    out = pd.DataFrame(rows).set_index("feature").round(4)
    out.to_csv(ROOT / "research/results/features/diagnostics.csv")
    print(out.to_string())


if __name__ == "__main__":
    main()
