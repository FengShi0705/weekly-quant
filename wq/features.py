"""Point-in-time features and labels on a weekly grid.

Timeline for each week T:
  - signal date  = last trading day of week T (features use prices up to and including this close)
  - exec date    = next trading day (you place orders Monday; we assume Monday's close as the fill)
  - label        = return from exec(T) to exec(T + h), only known after exec(T + h)
"""
import numpy as np
import pandas as pd

FEATURES = [
    "mom_12_1", "mom_6_1", "mom_3", "rev_1w", "rev_1m",
    "vol_60", "vol_ratio", "dist_high", "ma200", "beta", "idio_vol",
    "skew_60", "max_ret_21", "log_dv60", "dv_trend",
]


def weekly_calendar(daily_index):
    """Return a DataFrame indexed by signal date with the matching exec date (NaT for the last week)."""
    idx = pd.DatetimeIndex(daily_index).sort_values()
    s = pd.Series(idx, index=idx)
    signal = s.groupby(idx.to_period("W-FRI")).max().to_numpy()
    pos = idx.get_indexer(signal)
    exec_dates = [idx[p + 1] if p + 1 < len(idx) else pd.NaT for p in pos]
    return pd.DataFrame({"exec_date": exec_dates}, index=pd.DatetimeIndex(signal, name="date"))


def _daily_features(px, volume):
    r = px.pct_change(fill_method=None)
    mkt = r.mean(axis=1)

    f = {}
    f["mom_12_1"] = px.shift(21) / px.shift(252) - 1
    f["mom_6_1"] = px.shift(21) / px.shift(126) - 1
    f["mom_3"] = px / px.shift(63) - 1
    f["rev_1w"] = px / px.shift(5) - 1
    f["rev_1m"] = px / px.shift(21) - 1
    f["vol_60"] = r.rolling(60, min_periods=40).std()
    f["vol_ratio"] = r.rolling(20, min_periods=15).std() / r.rolling(120, min_periods=80).std()
    f["dist_high"] = px / px.rolling(252, min_periods=200).max() - 1
    f["ma200"] = px / px.rolling(200, min_periods=150).mean() - 1

    w, mp = 252, 200
    mean_r = r.rolling(w, min_periods=mp).mean()
    mean_m = mkt.rolling(w, min_periods=mp).mean()
    cov = r.mul(mkt, axis=0).rolling(w, min_periods=mp).mean().sub(mean_r.mul(mean_m, axis=0))
    var_m = mkt.rolling(w, min_periods=mp).var(ddof=0)
    beta = cov.div(var_m, axis=0)
    var_r = r.rolling(w, min_periods=mp).var(ddof=0)
    f["beta"] = beta
    f["idio_vol"] = np.sqrt((var_r - beta.pow(2).mul(var_m, axis=0)).clip(lower=0))

    f["skew_60"] = r.rolling(60, min_periods=40).skew()
    f["max_ret_21"] = r.rolling(21, min_periods=15).max()
    dv = px * volume.reindex_like(px)
    f["log_dv60"] = np.log(dv.rolling(60, min_periods=40).mean().replace(0, np.nan))
    f["dv_trend"] = np.log(dv.rolling(20, min_periods=15).mean() / dv.rolling(120, min_periods=80).mean())
    return f, dv


def market_index(px):
    """Equal-weight index of the universe, used for the benchmark and the regime filter."""
    r = px.pct_change(fill_method=None).mean(axis=1).fillna(0)
    return (1 + r).cumprod()


def build_panel(px_base, volume, universe, cfg):
    """Long panel indexed by (date, ticker) with ranked features, eligibility and forward returns.

    px_base: daily close in base currency (tickers as columns).
    """
    px = px_base.sort_index().ffill(limit=5)
    cal = weekly_calendar(px.index)
    feats, dv = _daily_features(px, volume)

    ucfg = cfg["universe"]
    history = px.notna().cumsum()
    dv60 = dv.rolling(60, min_periods=40).mean()
    fresh = px_base.reindex(px.index).notna().astype(float).rolling(5, min_periods=1).max() > 0
    eligible = (history >= ucfg["min_price_history_days"]) & (dv60 >= ucfg["min_dollar_volume_60d"]) & fresh

    sig = cal.index
    px_exec = px.reindex(cal["exec_date"].dropna())
    px_exec.index = cal.index[cal["exec_date"].notna()]
    px_exec = px_exec.reindex(sig)
    h = cfg["model"]["label_horizon_weeks"]

    cols = {name: f.reindex(sig).stack(future_stack=True) for name, f in feats.items()}
    cols["fwd_ret_1w"] = (px_exec.shift(-1) / px_exec - 1).stack(future_stack=True)
    cols["fwd_ret"] = (px_exec.shift(-h) / px_exec - 1).stack(future_stack=True)
    cols["eligible"] = eligible.reindex(sig).fillna(False).stack(future_stack=True)
    panel = pd.DataFrame(cols)
    panel.index.names = ["date", "ticker"]
    panel = panel[panel["eligible"].astype(bool)].drop(columns="eligible")

    # Cross-sectional rank-normalisation removes market-wide level shifts in every feature.
    g = panel.groupby(level="date")
    raw_dv = panel["log_dv60"].copy()
    for c in FEATURES:
        panel[c] = g[c].rank(pct=True) - 0.5
    panel["raw_log_dv60"] = raw_dv
    panel["label"] = g["fwd_ret"].rank(pct=True) - 0.5
    panel["country"] = panel.index.get_level_values("ticker").map(universe["country"])

    week_no = pd.Series(np.arange(len(sig)), index=sig)
    panel["week"] = panel.index.get_level_values("date").map(week_no).astype(int)
    return panel, cal, px
