"""Analyst rating and price-target changes from Yahoo, and point-in-time features built from them.

A feature for signal date T uses only actions dated at least one calendar day before T.
"""
import time

import numpy as np
import pandas as pd

ANALYST_FEATURES = ["rev_net_4w", "rev_net_13w", "pt_rev_4w"]


def fetch(tickers, path, pause=1.5, retries=3, verbose=True):
    """Download each ticker's rating-action history to one parquet file. Resumable."""
    import yfinance as yf
    done = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    have = set(done["ticker"]) if len(done) else set()
    rows = [done] if len(done) else []
    for i, t in enumerate(tickers):
        if t in have:
            continue
        u = None
        for k in range(retries):
            try:
                u = yf.Ticker(t).upgrades_downgrades
                break
            except Exception as ex:
                if verbose:
                    print(f"{t}: {type(ex).__name__} {str(ex)[:80]}", flush=True)
                time.sleep(pause * 4 * (k + 1))
        if u is None or len(u) == 0:
            u = pd.DataFrame({"ts": [pd.NaT]})
        else:
            u = u.reset_index().rename(columns={"GradeDate": "ts", "Action": "action",
                                                "currentPriceTarget": "pt", "priorPriceTarget": "pt_prior"})
        u["ticker"] = t
        rows.append(u[[c for c in ["ticker", "ts", "action", "pt", "pt_prior"] if c in u]])
        if verbose and i % 20 == 0:
            print(f"{i + 1}/{len(tickers)} {t}: {len(u)} rows", flush=True)
        pd.concat(rows, ignore_index=True).to_parquet(path)
        time.sleep(pause)
    return pd.concat(rows, ignore_index=True)


def features(raw, signal_dates):
    """(date, ticker) -> rev_net_4w, rev_net_13w, pt_rev_4w.

    rev_net_*: upgrades minus downgrades dated in [T - window, T - 1 day].
    pt_rev_4w: mean log(new target / old target) over actions in the last 4 weeks with both targets > 0.
    Tickers with no history at all are left out (missing).
    """
    a = raw.dropna(subset=["ts"]).copy()
    a["day"] = pd.to_datetime(a["ts"]).dt.tz_localize(None).dt.normalize()
    a["net"] = a["action"].map({"up": 1.0, "down": -1.0}).fillna(0.0)
    ok = (a["pt"] > 0) & (a["pt_prior"] > 0)
    a["ptr"] = np.where(ok, np.log(a["pt"].where(ok, 1.0) / a["pt_prior"].where(ok, 1.0)), np.nan)
    sig = pd.DatetimeIndex(signal_dates)
    out = []
    for t, g in a.groupby("ticker"):
        daily = g.groupby("day").agg(net=("net", "sum"), ptr_sum=("ptr", "sum"), ptr_n=("ptr", "count"))
        cum = daily.cumsum()
        def upto(days_back_end, days_back_start):
            """Sums over actions dated in [T - start, T - end] for each signal date T."""
            hi = cum.reindex(sig - pd.Timedelta(days=days_back_end), method="ffill").fillna(0.0).to_numpy()
            lo = cum.reindex(sig - pd.Timedelta(days=days_back_start + 1), method="ffill").fillna(0.0).to_numpy()
            return hi - lo
        w4, w13 = upto(1, 28), upto(1, 91)
        cols = list(cum.columns)
        net4, net13 = w4[:, cols.index("net")], w13[:, cols.index("net")]
        n4 = w4[:, cols.index("ptr_n")]
        pt4 = np.where(n4 > 0, w4[:, cols.index("ptr_sum")] / np.where(n4 > 0, n4, 1), np.nan)
        out.append(pd.DataFrame({"date": sig, "ticker": t, "rev_net_4w": net4, "rev_net_13w": net13, "pt_rev_4w": pt4}))
    if not out:
        return pd.DataFrame(columns=ANALYST_FEATURES)
    return pd.concat(out).set_index(["date", "ticker"]).sort_index()
