"""Price, volume and FX download (Yahoo Finance via yfinance) with a local parquet cache.

All prices are dividend/split adjusted. Everything downstream works in the account's
base currency, so a EUR stock's return already includes the EUR/base FX move.
"""
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd


def load_universe(cfg):
    u = pd.read_csv(cfg["universe"]["file"])
    u = u[u["region"].isin(cfg["universe"]["regions"])]
    broker = cfg["account"]["broker"]
    u = u[u["brokers"].str.split("|").apply(lambda b: broker in b)]
    return u.drop_duplicates("ticker").set_index("ticker")


def quote_currency(ccy):
    """Yahoo quotes London stocks in pence ('GBp'). Return (ISO currency, multiplier)."""
    if ccy == "GBp":
        return "GBP", 0.01
    return ccy, 1.0


def _strip_tz(idx):
    idx = pd.DatetimeIndex(idx)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def _yf_download(tickers, start, batch_size=50, retries=4):
    import yfinance as yf

    closes, volumes = [], []
    for i in range(0, len(tickers), batch_size):
        chunk = list(tickers[i:i + batch_size])
        for attempt in range(retries):
            try:
                df = yf.download(chunk, start=start, auto_adjust=True, progress=False,
                                 threads=True, group_by="column")
                break
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** (attempt + 1))
        if df.empty:
            continue
        close, vol = df["Close"], df["Volume"]
        if isinstance(close, pd.Series):
            close, vol = close.to_frame(chunk[0]), vol.to_frame(chunk[0])
        closes.append(close)
        volumes.append(vol)
        print(f"  downloaded {min(i + batch_size, len(tickers))}/{len(tickers)}")
    close = pd.concat(closes, axis=1)
    volume = pd.concat(volumes, axis=1)
    close.index = _strip_tz(close.index)
    volume.index = _strip_tz(volume.index)
    close = close.dropna(axis=1, how="all").sort_index()
    return close, volume.reindex(columns=close.columns).sort_index()


def clean_spikes(close, threshold=0.4):
    """Blank single-day bad prints (e.g. a 100x pence/pound mix-up) that fully reverse next day."""
    r = close.pct_change(fill_method=None)
    spike = (r.abs() > threshold) & (r.shift(-1).abs() > threshold) & (np.sign(r) != np.sign(r.shift(-1)))
    return close.mask(spike)


def download(cfg):
    universe = load_universe(cfg)
    tickers = list(universe.index)
    start = cfg["data"]["start"]
    print(f"Downloading {len(tickers)} stocks from {start} ...")
    close, volume = _yf_download(tickers, start)

    etfs = cfg["benchmarks"]["etfs"]
    ccys = ({quote_currency(c)[0] for c in universe["currency"]} | {cfg["account"]["base_currency"]}
            | {quote_currency(e["currency"])[0] for e in etfs.values()})
    ccys.discard("USD")
    fx_tickers = [f"{c}USD=X" for c in sorted(ccys)]
    print(f"Downloading FX: {', '.join(fx_tickers)}")
    fx_close, _ = _yf_download(fx_tickers, start)
    fx_usd = fx_close.rename(columns=lambda t: t[:3])

    print(f"Downloading benchmark ETFs: {', '.join(etfs)}")
    etf_close, _ = _yf_download(list(etfs), start)

    missing = sorted(set(tickers) - set(close.columns))
    cache = cfg["data"]["cache_dir"]
    cache.mkdir(parents=True, exist_ok=True)
    clean_spikes(close).to_parquet(cache / "close_local.parquet")
    volume.to_parquet(cache / "volume.parquet")
    fx_usd.to_parquet(cache / "fx_usd.parquet")
    clean_spikes(etf_close).to_parquet(cache / "etf_close.parquet")
    meta = {"downloaded_at": datetime.now(timezone.utc).isoformat(), "last_date": str(close.index.max().date()),
            "n_stocks": close.shape[1], "missing": missing}
    (cache / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved {close.shape[1]} stocks through {meta['last_date']}. Missing: {missing or 'none'}")
    return meta


def load_cached(cfg):
    cache = cfg["data"]["cache_dir"]
    if not (cache / "close_local.parquet").exists():
        raise FileNotFoundError(f"No cached data in {cache}. Run `python -m wq download` first.")
    close = pd.read_parquet(cache / "close_local.parquet")
    volume = pd.read_parquet(cache / "volume.parquet")
    fx_usd = pd.read_parquet(cache / "fx_usd.parquet")
    return close, volume, fx_usd


def load_benchmarks(cfg, fx_usd):
    """Benchmark ETF prices in base currency, or None if they haven't been downloaded."""
    path = cfg["data"]["cache_dir"] / "etf_close.parquet"
    if not path.exists():
        return None
    etfs = cfg["benchmarks"]["etfs"]
    close = pd.read_parquet(path)
    return to_base(close, {t: etfs[t]["currency"] for t in close.columns if t in etfs}, fx_usd,
                   cfg["account"]["base_currency"])


def to_base(close_local, currency_by_ticker, fx_usd, base):
    """Convert local-currency prices to the base currency. fx_usd[c] = USD per 1 unit of c."""
    fx = fx_usd.reindex(close_local.index).ffill()
    base_in_usd = 1.0 if base == "USD" else fx[base]
    out = {}
    for t in close_local.columns:
        ccy, mult = quote_currency(currency_by_ticker[t])
        usd = 1.0 if ccy == "USD" else fx[ccy]
        out[t] = close_local[t] * mult * usd / base_in_usd
    return pd.DataFrame(out, index=close_local.index)


def usd_per_base(fx_usd, base, date=None):
    if base == "USD":
        return 1.0
    s = fx_usd[base].ffill()
    return float(s.loc[:date].iloc[-1] if date is not None else s.iloc[-1])
