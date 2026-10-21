"""Earnings announcements from Yahoo: dates and EPS surprises, and point-in-time features built from them.

A feature for signal date T uses only announcements whose reaction window had closed by T's close.
"""
import time

import numpy as np
import pandas as pd

EARN_FEATURES = ["ear", "sue", "earn_age"]
WINDOW = 65          # an announcement counts for about a quarter of trading days


def fetch(tickers, path, pause=1.5, retries=3, verbose=True):
    """Download each ticker's earnings history (past and scheduled) to one parquet file. Resumable."""
    done = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    have = set(done["ticker"]) if len(done) else set()
    import yfinance as yf
    rows = [done] if len(done) else []
    for i, t in enumerate(tickers):
        if t in have:
            continue
        e = None
        for k in range(retries):
            try:
                e = yf.Ticker(t).get_earnings_dates(limit=100)
                break
            except Exception as ex:                       # rate limits: back off and retry
                if verbose:
                    print(f"{t}: {type(ex).__name__} {str(ex)[:80]}", flush=True)
                time.sleep(pause * 4 * (k + 1))
        if e is None or len(e) == 0:
            e = pd.DataFrame({"ts": [pd.NaT]})
        else:
            e = e.reset_index().rename(columns={"Earnings Date": "ts", "EPS Estimate": "eps_est",
                                                "Reported EPS": "eps_rep", "Surprise(%)": "surprise"})
            e["ts"] = pd.to_datetime(e["ts"], utc=True)
        e["ticker"] = t
        rows.append(e[[c for c in ["ticker", "ts", "eps_est", "eps_rep", "surprise"] if c in e]])
        if verbose and i % 20 == 0:
            print(f"{i + 1}/{len(tickers)} {t}: {len(e)} rows", flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(path)
        time.sleep(pause)
    return pd.concat(rows, ignore_index=True)


def reaction_day(ts, trading_days):
    """First trading day whose close comes after the announcement.

    Announcements before 14:00 UTC (before European closes and US opens) move that day's close;
    later ones (US after-close, European evening) move the next day's. Date-only rows from Yahoo arrive
    as midnight UTC and count as that day.
    """
    day = ts.tz_convert("UTC").tz_localize(None).normalize()
    after = ts.tz_convert("UTC").hour >= 14
    i = trading_days.searchsorted(day)
    if after and i < len(trading_days) and trading_days[i] == day:
        i += 1
    return trading_days[i] if i < len(trading_days) else pd.NaT


def events(raw, trading_days):
    """Past announcements per ticker with their reaction day; duplicates within 5 days merged."""
    e = raw.dropna(subset=["ts"]).copy()
    e["day"] = [reaction_day(t, trading_days) for t in e["ts"]]
    e = e.dropna(subset=["day"]).sort_values(["ticker", "day"])
    e = e[e.groupby("ticker")["day"].diff().dt.days.fillna(99) > 5]
    return e[["ticker", "day", "surprise"]].reset_index(drop=True)


def features(raw, px, signal_dates):
    """(date, ticker) -> ear, sue, earn_age.

    ear: the stock's return minus the equal-weight universe's, from the close before the reaction day
         to the close after it (3 closes), for the latest announcement whose window ended by the signal
         date and within the last 65 trading days.
    sue: Yahoo's EPS surprise for that announcement (%), clipped to +-100 and log-scaled.
    earn_age: trading days since that reaction day, / 65.
    """
    days = px.index
    p = px.ffill()
    mkt = (1 + px.pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod().to_numpy()
    ev = events(raw, days)
    pos = pd.Series(np.arange(len(days)), index=days)
    out = []
    for t, g in ev.groupby("ticker"):
        if t not in px.columns:
            continue
        ix = pos.reindex(g["day"]).to_numpy()
        ok = (ix >= 1) & (ix + 1 < len(days))
        g, ix = g[ok], ix[ok].astype(int)
        c = p[t].to_numpy()
        ear = (c[ix + 1] / c[ix - 1] - 1) - (mkt[ix + 1] / mkt[ix - 1] - 1)
        known = ix + 1                                           # window complete at this close
        out.append(pd.DataFrame({"ticker": t, "known": known, "react": ix, "ear": ear,
                                 "sue": g["surprise"].to_numpy(dtype=float)}))
    if not out:
        return pd.DataFrame(columns=EARN_FEATURES)
    ev = pd.concat(out, ignore_index=True).sort_values("known")
    sig = pd.Series(pos.reindex(pd.DatetimeIndex(signal_dates)).to_numpy(), index=pd.DatetimeIndex(signal_dates))
    sig = sig.dropna().astype(int)
    grid = pd.DataFrame({"date": sig.index, "spos": sig.to_numpy()}).sort_values("spos")
    res = []
    for t, g in ev.groupby("ticker"):
        m = pd.merge_asof(grid, g.rename(columns={"known": "spos"}), on="spos", direction="backward")
        age = m["spos"] - m["react"]
        fresh = age <= WINDOW
        s = m["sue"].clip(-100, 100)
        res.append(pd.DataFrame({"date": m["date"], "ticker": t,
                                 "ear": m["ear"].where(fresh),
                                 "sue": (np.sign(s) * np.log1p(s.abs())).where(fresh),
                                 "earn_age": (age / WINDOW).where(fresh)}))
    return pd.concat(res).set_index(["date", "ticker"]).sort_index()
