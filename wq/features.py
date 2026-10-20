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
# Optional, switched on with model.extra_features in config.yaml.
EXTRA_FEATURES = ["resid_mom_12_1", "sector_mom_12_1"]
# Integer country and sector codes, used as LightGBM categorical features with model.categorical: true.
CATEGORICAL = ["country_id", "sector_id"]


def feature_list(cfg):
    extra = cfg["model"].get("extra_features") or []
    unknown = set(extra) - set(EXTRA_FEATURES)
    if unknown:
        raise ValueError(f"unknown extra_features: {sorted(unknown)}")
    return FEATURES + list(extra) + (CATEGORICAL if cfg["model"].get("categorical") else [])


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
    # Momentum of the part of each return the market doesn't explain (12-1 months).
    resid = r - beta.shift(1).mul(mkt, axis=0)
    f["resid_mom_12_1"] = resid.rolling(231, min_periods=180).sum().shift(21)
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

    panel["country"] = panel.index.get_level_values("ticker").map(universe["country"])
    panel["sector"] = panel.index.get_level_values("ticker").map(universe["sector"])
    for c in ("country", "sector"):                         # stable codes: sorted names of the whole universe
        codes = {v: i for i, v in enumerate(sorted(universe[c].astype(str).unique()))}
        panel[f"{c}_id"] = panel[c].astype(str).map(codes).astype(int)
    # 12-1 momentum ranked only against the same sector, so a hot sector doesn't dominate.
    panel["sector_mom_12_1"] = panel.groupby([panel.index.get_level_values("date"), "sector"])["mom_12_1"].rank(pct=True) - 0.5

    # Cross-sectional rank-normalisation removes market-wide level shifts in every feature.
    g = panel.groupby(level="date")
    panel["raw_log_dv60"] = panel["log_dv60"]
    panel["raw_vol_60"] = panel["vol_60"]
    for c in FEATURES + ["resid_mom_12_1"]:
        panel[c] = g[c].rank(pct=True) - 0.5
    panel["label"] = g["fwd_ret"].rank(pct=True) - 0.5

    week_no = pd.Series(np.arange(len(sig)), index=sig)
    panel["week"] = panel.index.get_level_values("date").map(week_no).astype(int)
    return panel, cal, px


def weekly_history(px, signal_dates, lags=26):
    """Each stock's last `lags` weekly returns up to each signal date (close to close), z-scored across
    stocks per date and clipped at ±5. Columns hist_0 (the week ending on the signal date) .. hist_{lags-1}.
    Long frame indexed by (date, ticker). Pass the full calendar of signal dates: lags are counted in it."""
    ps = px.ffill(limit=5).reindex(signal_dates)
    r = ps / ps.shift(1) - 1
    cols = {}
    for k in range(lags):
        x = r.shift(k)
        z = x.sub(x.mean(axis=1), axis=0).div(x.std(axis=1).replace(0, np.nan), axis=0).clip(-5, 5)
        cols[f"hist_{k}"] = z.stack(future_stack=True)
    out = pd.DataFrame(cols)
    out.index.names = ["date", "ticker"]
    return out


MARKET_COLS = ["mkt_ret_4w", "mkt_ret_12w", "mkt_ret_52w", "mkt_vol_60", "dispersion_1w"]


def market_context(px, signal_dates):
    """The market backdrop on each signal date, the same for every stock: equal-weight index return over
    4, 12 and 52 weeks, its daily volatility over 60 days, and the cross-sectional spread of last week's
    stock returns. Squashed with tanh onto roughly [-1, 1]. Indexed by date."""
    idx = market_index(px)
    r = idx.pct_change()
    ps = px.ffill(limit=5)
    week_ret = ps / ps.shift(5) - 1
    raw = pd.DataFrame({
        "mkt_ret_4w": idx / idx.shift(20) - 1, "mkt_ret_12w": idx / idx.shift(60) - 1,
        "mkt_ret_52w": idx / idx.shift(252) - 1, "mkt_vol_60": r.rolling(60, min_periods=40).std(),
        "dispersion_1w": week_ret.std(axis=1),
    }).reindex(signal_dates)
    scale = {"mkt_ret_4w": 0.05, "mkt_ret_12w": 0.10, "mkt_ret_52w": 0.20, "mkt_vol_60": 0.015, "dispersion_1w": 0.03}
    return np.tanh(raw / pd.Series(scale)).fillna(0.0)
