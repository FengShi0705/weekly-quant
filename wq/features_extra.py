"""Extra point-in-time feature sets for the transformer (research/preregistration_features.md).

Every feature for signal date T uses prices, volumes, dividends and earnings dates up to T's close only.
Values are raw; callers rank them across stocks each week like the core features.
"""
import warnings

import numpy as np
import pandas as pd

SETS = {
    "peer": ["sec_rel_1w", "sec_rel_1m", "sec_rel_3m", "sec_rel_12_1", "sec_mom_12_1", "sec_ret_1m",
             "cty_mom_12_1", "cty_ret_1m"],
    "shape": ["info_disc", "down_beta", "max_dd_1y", "dist_low", "amihud", "abn_volume"],
    "calendar": ["earn_next_1w", "div_next_4w", "div_yield_12m", "season_month"],
    "fx": ["fx_1m", "fx_3m", "fx_12m"],
}
SETS["all"] = [f for s in ("peer", "shape", "calendar", "fx") for f in SETS[s]]


def _group_mean(frame, groups):
    """Each column replaced by the mean of its group's columns (same row)."""
    out = pd.DataFrame(index=frame.index, columns=frame.columns, dtype=float)
    for _, cols in groups.groupby(groups).groups.items():
        cols = [c for c in cols if c in frame.columns]
        if cols:
            m = frame[cols].mean(axis=1)
            for c in cols:
                out[c] = m
    return out


def peer(px, universe):
    ret = {"1w": px / px.shift(5) - 1, "1m": px / px.shift(21) - 1, "3m": px / px.shift(63) - 1,
           "12_1": px.shift(21) / px.shift(252) - 1}
    sec, cty = universe["sector"].reindex(px.columns), universe["country"].reindex(px.columns)
    out = {f"sec_rel_{k}": v - _group_mean(v, sec) for k, v in ret.items()}
    out["sec_mom_12_1"], out["sec_ret_1m"] = _group_mean(ret["12_1"], sec), _group_mean(ret["1m"], sec)
    out["cty_mom_12_1"], out["cty_ret_1m"] = _group_mean(ret["12_1"], cty), _group_mean(ret["1m"], cty)
    return out


def _max_drawdown(px, signal_dates, window=252):
    a = px.to_numpy()
    pos = px.index.get_indexer(signal_dates)
    out = np.full((len(signal_dates), a.shape[1]), np.nan)
    for i, p in enumerate(pos):
        if p < window - 1:
            continue
        w = a[p - window + 1:p + 1]
        ok = np.isfinite(w).sum(axis=0) >= 200
        peak = np.fmax.accumulate(w, axis=0)
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            dd = np.nanmin(w / peak - 1, axis=0)
        out[i] = np.where(ok, dd, np.nan)
    return pd.DataFrame(out, index=signal_dates, columns=px.columns)


def shape(px, volume, signal_dates):
    r = px.pct_change(fill_method=None)
    mkt = r.mean(axis=1)
    mom = px.shift(21) / px.shift(252) - 1
    up = (r > 0).astype(float).where(r.notna()).rolling(231, min_periods=180).mean().shift(21)
    dn = (r < 0).astype(float).where(r.notna()).rolling(231, min_periods=180).mean().shift(21)
    down = mkt < 0
    r_d, m_d = r.where(down, np.nan), mkt.where(down)
    beta = r_d.rolling(252, min_periods=60).cov(m_d).div(m_d.rolling(252, min_periods=60).var(), axis=0)
    dv = (px * volume.reindex_like(px)).replace(0, np.nan)
    vol = volume.reindex_like(px).replace(0, np.nan)
    return {
        "info_disc": np.sign(mom) * (dn - up),
        "down_beta": beta,
        "max_dd_1y": _max_drawdown(px, signal_dates),
        "dist_low": px / px.rolling(252, min_periods=200).min() - 1,
        "amihud": np.log((r.abs() / dv).rolling(60, min_periods=40).mean() * 1e6 + 1e-12),
        "abn_volume": np.log(vol.rolling(5, min_periods=4).mean() / vol.rolling(252, min_periods=200).mean()),
    }


def _expected_flag(event_days, signal_dates, lags, lo, hi):
    """1 if a past event day d (d < T) projected by any lag lands in (T + lo, T + hi] days, else 0."""
    sig = pd.DatetimeIndex(signal_dates)
    out = np.zeros(len(sig))
    ev = np.sort(pd.DatetimeIndex(event_days).values)
    for lag in lags:
        proj = ev + np.timedelta64(lag, "D")
        a = np.searchsorted(proj, (sig + pd.Timedelta(days=lo)).values, side="right")
        b = np.searchsorted(proj, (sig + pd.Timedelta(days=hi)).values, side="right")
        out = np.maximum(out, (b > a).astype(float))      # lag > hi, so every counted event is before T
    return out


def calendar(px, div_yield, earnings_raw, signal_dates):
    sig = pd.DatetimeIndex(signal_dates)
    earn = {}
    if earnings_raw is not None and len(earnings_raw):
        e = earnings_raw.dropna(subset=["ts"])
        for t, g in e.groupby("ticker"):
            days = pd.to_datetime(g["ts"]).dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
            # an announcement 52 or 13 weeks earlier projected into next week (T+1 .. T+7), +-3 days;
            # missing until the stock's first announcement is in the past (coverage is point-in-time too)
            flag = _expected_flag(days, sig, (364, 91), -3, 10)
            earn[t] = np.where(sig > days.min(), flag, np.nan)
    earn_df = pd.DataFrame(earn, index=sig).reindex(columns=px.columns)
    out = {"earn_next_1w": earn_df}
    dy = div_yield.reindex(columns=px.columns) if div_yield is not None else pd.DataFrame(0.0, index=px.index, columns=px.columns)
    dy = dy.reindex(px.index).fillna(0.0)
    div = {t: _expected_flag(dy.index[dy[t] > 0], sig, (364,), 0, 28) for t in px.columns}
    out["div_next_4w"] = pd.DataFrame(div, index=sig)
    out["div_yield_12m"] = dy.rolling(252, min_periods=200).sum().where(px.notna())
    out["season_month"] = _seasonality(px, sig)
    return out


def _seasonality(px, sig, years=5, min_years=3):
    """Mean return in the coming calendar month (the month of the next trading day) over the previous years."""
    m_end = px.groupby(px.index.to_period("M")).last()
    m_ret = m_end / m_end.shift(1) - 1
    nxt = px.index.searchsorted(sig, side="right")
    coming = [px.index[min(i, len(px.index) - 1)].to_period("M") for i in nxt]
    rows = []
    for T, M in zip(sig, coming):
        past = [M - 12 * k for k in range(1, years + 1)]
        past = [p for p in past if p in m_ret.index and p.end_time < T]
        vals = m_ret.loc[past] if past else None
        if vals is None or len(vals) < min_years:
            rows.append(pd.Series(np.nan, index=px.columns))
        else:
            rows.append(vals.mean().where(vals.notna().sum() >= min_years))
    return pd.DataFrame(rows, index=sig)


def fx(px, close_local):
    rate = px / close_local.reindex_like(px).ffill(limit=5)
    return {"fx_1m": rate / rate.shift(21) - 1, "fx_3m": rate / rate.shift(63) - 1,
            "fx_12m": rate / rate.shift(252) - 1}


def build(set_name, px, close_local, volume, universe, div_yield, earnings_raw, signal_dates):
    """Raw (unranked) features of one set, indexed by (date, ticker)."""
    sig = pd.DatetimeIndex(signal_dates)
    parts = {}
    names = SETS[set_name]
    if any(f in names for f in SETS["peer"]):
        parts.update(peer(px, universe))
    if any(f in names for f in SETS["shape"]):
        parts.update(shape(px, volume, sig))
    if any(f in names for f in SETS["calendar"]):
        parts.update(calendar(px, div_yield, earnings_raw, sig))
    if any(f in names for f in SETS["fx"]):
        parts.update(fx(px, close_local))
    cols = {}
    for f in names:
        v = parts[f].reindex(sig)
        cols[f] = v.replace([np.inf, -np.inf], np.nan).stack(future_stack=True)
    out = pd.DataFrame(cols)
    out.index.names = ["date", "ticker"]
    return out
