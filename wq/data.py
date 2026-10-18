"""Price, volume and FX download (Yahoo Finance via yfinance) with a local parquet cache.

All prices are dividend/split adjusted (see total_return), and each stock's daily dividend yield is
cached too. Everything downstream works in the account's base currency, so a EUR stock's return
already includes the EUR/base FX move.
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


def total_return(close_raw, close_adj, pence=()):
    """Dividend-adjusted closes rebuilt from Yahoo's raw (split-adjusted) and adjusted closes.

    Each ex-date's dividend yield is the jump in the ratio of the two series. Yahoo applies London
    (GBp) dividends about 100x too small, a pence/pounds mix-up that leaves its adjusted closes for
    London stocks close to price-only. So for the `pence` columns, a yield that is implausibly small
    but plausible at 100x is scaled up. Returns (adjusted closes, dividend yield as a fraction of the
    previous close), with the adjusted closes equal to the raw closes on the last day, as Yahoo's are.
    """
    y = 1 - (close_raw / close_raw.shift(1)) / (close_adj / close_adj.shift(1))
    y = y.where(y > 1e-6, 0.0).fillna(0.0)
    pence = [c for c in y.columns if c in set(pence)]
    if pence:
        p = y[pence]
        y[pence] = p.where(~((p < 5e-4) & (p * 100 >= 1e-3) & (p * 100 <= 0.25)), p * 100)
    y = y.where(y < 0.3, 0.0)                                  # a 30%+ "dividend" is a data error
    c = close_raw.ffill()
    tr = ((c / c.shift(1)) / (1 - y)).fillna(1.0).cumprod()
    tr = tr * (c.iloc[-1] / tr.iloc[-1])
    return tr.where(close_raw.notna()), y


def _yf_download(tickers, start, currencies=None, batch_size=50, retries=4):
    """Returns (dividend-adjusted closes, volumes, dividend yields). currencies: ticker -> currency."""
    import yfinance as yf

    currencies = currencies if currencies is not None else {}
    pence = [t for t in tickers if currencies.get(t) == "GBp"]
    closes, volumes = [], []
    for i in range(0, len(tickers), batch_size):
        chunk = list(tickers[i:i + batch_size])
        for attempt in range(retries):
            try:
                df = yf.download(chunk, start=start, auto_adjust=False, progress=False,
                                 threads=True, group_by="column")
                break
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** (attempt + 1))
        if df.empty:
            continue
        raw, adj, vol = df["Close"], df["Adj Close"], df["Volume"]
        if isinstance(raw, pd.Series):
            raw, adj, vol = raw.to_frame(chunk[0]), adj.to_frame(chunk[0]), vol.to_frame(chunk[0])
        closes.append((raw, adj))
        volumes.append(vol)
        print(f"  downloaded {min(i + batch_size, len(tickers))}/{len(tickers)}")
    raw = pd.concat([r for r, _ in closes], axis=1)
    adj = pd.concat([a for _, a in closes], axis=1)
    volume = pd.concat(volumes, axis=1)
    for df in (raw, adj, volume):
        df.index = _strip_tz(df.index)
    raw = raw.dropna(axis=1, how="all").sort_index()
    close, div = total_return(raw, adj.reindex(index=raw.index, columns=raw.columns), pence)
    return close, volume.reindex(columns=close.columns).sort_index(), div


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
    close, volume, div = _yf_download(tickers, start, universe["currency"].to_dict())

    etfs = cfg["benchmarks"]["etfs"]
    ccys = ({quote_currency(c)[0] for c in universe["currency"]} | {cfg["account"]["base_currency"]}
            | {quote_currency(e["currency"])[0] for e in etfs.values()})
    ccys.discard("USD")
    fx_tickers = [f"{c}USD=X" for c in sorted(ccys)]
    print(f"Downloading FX: {', '.join(fx_tickers)}")
    fx_close, _, _ = _yf_download(fx_tickers, start)
    fx_usd = fx_close.rename(columns=lambda t: t[:3])

    print(f"Downloading benchmark ETFs: {', '.join(etfs)}")
    etf_close, _, _ = _yf_download(list(etfs), start, {t: e["currency"] for t, e in etfs.items()})

    missing = sorted(set(tickers) - set(close.columns))
    cache = cfg["data"]["cache_dir"]
    cache.mkdir(parents=True, exist_ok=True)
    clean_spikes(close).to_parquet(cache / "close_local.parquet")
    volume.to_parquet(cache / "volume.parquet")
    div.to_parquet(cache / "div_yield.parquet")
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


def load_dividends(cfg):
    """Daily dividend yields (fraction of the previous close), or None if they haven't been downloaded."""
    path = cfg["data"]["cache_dir"] / "div_yield.parquet"
    return pd.read_parquet(path) if path.exists() else None


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
