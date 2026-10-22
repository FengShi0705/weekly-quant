"""Wikipedia page views per company (public attention), and point-in-time features built from them.

A feature for signal date T uses views up to the day before T.
"""
import json
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

ATTENTION_FEATURES = ["attn_1w", "attn_4w", "attn_level"]
UA = "weekly-quant-research/1.0 (https://github.com/FengShi0705/weekly-quant)"


def _get(url, pause=3.0, retries=8, verbose=True):
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.load(r)
            time.sleep(pause)
            return out
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                time.sleep(pause)
                return None
            wait = pause * 2 ** (k + 1)
            if verbose:
                print(f"  HTTP {ex.code}, waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"gave up on {url}")


def search_titles(names, path, verbose=True):
    """Top English Wikipedia search hit for '<name> company', per ticker. Resumable CSV; review by hand."""
    done = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["ticker", "name", "title", "snippet"])
    for t, name in names.items():
        if t in set(done["ticker"]):
            continue
        q = urllib.parse.quote(f"{name} company")
        res = _get(f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json"
                   f"&srlimit=1&srprop=snippet", verbose=verbose)
        hit = (res or {}).get("query", {}).get("search", [{}])
        hit = hit[0] if hit else {}
        snip = hit.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")[:100]
        done = pd.concat([done, pd.DataFrame([{"ticker": t, "name": name, "title": hit.get("title", ""), "snippet": snip}])])
        done.to_csv(path, index=False)
        if verbose:
            print(f"{t}: {hit.get('title', '')}", flush=True)
    return done


def fetch_views(titles, path, start="20150701", end="20261031", verbose=True):
    """Daily human page views per ticker's article. titles: Series ticker -> article title. Resumable."""
    done = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    have = set(done.columns)
    for t, title in titles.items():
        if t in have or not title:
            continue
        art = urllib.parse.quote(title.replace(" ", "_"), safe="")
        res = _get("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
                   f"{art}/daily/{start}/{end}", verbose=verbose)
        items = (res or {}).get("items", [])
        s = pd.Series({pd.Timestamp(i["timestamp"][:8]): float(i["views"]) for i in items}, name=t, dtype=float)
        done = pd.concat([done, s], axis=1)
        done.to_parquet(path)
        if verbose:
            print(f"{t}: {len(s)} days", flush=True)
    return done


def features(views, signal_dates):
    """(date, ticker) -> attn_1w, attn_4w, attn_level, from views up to the day before each signal date."""
    v = views.sort_index().asfreq("D")
    base = v.rolling(364, min_periods=300).mean()
    last5, last20 = v.rolling(5, min_periods=4).mean(), v.rolling(20, min_periods=16).mean()
    prior = base.shift(20)                                   # the 52 weeks before the recent window
    raw = {"attn_1w": np.log((last5 + 1) / (prior + 1)), "attn_4w": np.log((last20 + 1) / (prior + 1)),
           "attn_level": np.log(base + 1)}
    sig = pd.DatetimeIndex(signal_dates)
    cols = {k: f.reindex(sig - pd.Timedelta(days=1)).set_axis(sig).stack(future_stack=True) for k, f in raw.items()}
    out = pd.DataFrame(cols)
    out.index.names = ["date", "ticker"]
    return out.dropna(how="all")
