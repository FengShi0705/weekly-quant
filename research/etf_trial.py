"""Phase 3, test C: index ETF and leveraged index trend strategies (research/preregistration_phase3.md).

No stock picking: real funds on Trading 212, priced in GBP, Jan 2016 – Oct 2026, plus a synthetic
1988–2026 history of the leveraged S&P 500 arms for the risk check.

Usage: python research/etf_trial.py [--refresh]
Writes research/results/phase3/etf/ and appends to research/trials.csv.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from risk_overlays import p_drop  # noqa: E402

OUT = ROOT / "research" / "results" / "phase3" / "etf"
CACHE = ROOT / "data" / "cache" / "phase3_etf.parquet"
START = pd.Timestamp("2016-01-08")
TX_BLEND = ROOT / "research" / "results" / "risk_overlays" / "weekly_sector_cap_5.csv"

PRICE = ["^SP500TR", "^GSPC", "^IRX", "GBPUSD=X", "^NDX", "QQQ", "VEU", "VUSA.L", "VXUS.L", "IGLT.L",
         "SGLN.L", "VEUR.L", "IUKP.L", "XSTR.L", "XS2D.L", "3LUS.L", "LQQ3.L"]
DISTRIBUTING = ["VUSA.L", "IGLT.L", "VEUR.L", "IUKP.L", "XSTR.L"]      # total return = close + dividends
USD = ["VEU", "XS2D.L", "QQQ"]
ETF_COST, LEV_COST, FX_FEE = 0.0010, 0.0020, 0.0015
FEES = {2: 0.0060, 3: 0.0075}                                         # XS2D 0.60%, WisdomTree 3x 0.75%


def download(refresh=False):
    if CACHE.exists() and not refresh:
        return pd.read_parquet(CACHE)
    import yfinance as yf
    d = yf.download(PRICE, start="1985-01-01", auto_adjust=False, progress=False, threads=False)
    out = {f"close|{t}": d["Close"][t] for t in PRICE}
    out.update({f"adj|{t}": d["Adj Close"][t] for t in PRICE})
    for t in DISTRIBUTING:
        dv = yf.Ticker(t).dividends
        dv.index = dv.index.tz_localize(None).normalize()
        out[f"div|{t}"] = dv
    df = pd.DataFrame(out).sort_index()
    df.to_parquet(CACHE)
    return df


def total_return(close, div):
    c = close.dropna()
    d = div.reindex(c.index).fillna(0.0) if div is not None else 0.0
    return ((c + d) / c.shift(1)).fillna(1.0).cumprod()


def lev_daily(r_index, rf, L, fee):
    """Daily return of an L-times daily-reset fund: L x index - (L-1) x financing - fee."""
    return L * r_index - (L - 1) * rf - fee / 252


def gbp_returns(raw):
    """London-day GBP daily returns of every instrument, plus synthetic leveraged series."""
    close = lambda t: raw[f"close|{t}"].dropna()
    fx = close("GBPUSD=X")                                              # USD per GBP
    days = close("VUSA.L").index
    days = days[days >= "2014-06-01"]
    tr = {t: total_return(close(t), raw.get(f"div|{t}")) for t in DISTRIBUTING}
    tr["SGLN.L"], tr["3LUS.L"], tr["LQQ3.L"], tr["VXUS.L"] = (close(t) for t in ["SGLN.L", "3LUS.L", "LQQ3.L", "VXUS.L"])
    for t in ["VEU", "XS2D.L"]:
        tr[t] = raw[f"adj|{t}"].dropna() / fx.reindex(raw[f"adj|{t}"].dropna().index, method="ffill")
    lvl = pd.DataFrame({t: s.reindex(days, method="ffill") for t, s in tr.items()})
    r = lvl.pct_change(fill_method=None)
    # World ex-US: VXUS (the UCITS fund on Trading 212) once it has a price, VEU before.
    r["EXUS"] = r["VXUS.L"].where(lvl["VXUS.L"].notna() & lvl["VXUS.L"].shift(1).notna(), r["VEU"])
    r["CASH"] = r["XSTR.L"]

    # Synthetic leveraged funds from the total-return indices, in GBP (unhedged).
    us = synthetic_usd(raw)
    fx_d = fx.reindex(days, method="ffill")
    for name, col in [("SP2", "sp_2x"), ("SP3", "sp_3x"), ("NQ2", "nq_2x"), ("NQ3", "nq_3x")]:
        lvl_usd = (1 + us[col]).cumprod().reindex(days, method="ffill")
        r[f"{name}_syn"] = (lvl_usd / fx_d).pct_change(fill_method=None)
    # Real products, with Yahoo's bad prints replaced: a day more than 15% away from the synthetic
    # (London closes 4.5 hours before New York, so smaller gaps on volatile days are genuine).
    repaired = {}
    for real, syn in [("XS2D.L", "SP2_syn"), ("3LUS.L", "SP3_syn"), ("LQQ3.L", "NQ3_syn")]:
        bad = (r[real] - r[syn]).abs() > 0.15
        repaired[real] = [str(d.date()) for d in r.index[bad]]
        r[real] = r[real].where(~bad, r[syn])
    return r.fillna(0.0).iloc[1:], repaired


def synthetic_usd(raw):
    """US-day USD returns: S&P 500 TR and Nasdaq-100 TR, levered 2x/3x, and the T-bill."""
    sp = raw["close|^SP500TR"].dropna()
    days = sp.index
    r_sp = sp.pct_change()
    irx = raw["close|^IRX"].reindex(days, method="ffill") / 100
    rf = irx.shift(1) / 252
    qqq = raw["adj|QQQ"].reindex(days)
    r_nq = qqq.pct_change() + 0.0020 / 252                      # QQQ's 0.20% fee added back
    gspc, ndx = raw["close|^GSPC"].reindex(days), raw["close|^NDX"].reindex(days, method="ffill")
    return pd.DataFrame({
        "sp": r_sp, "rf": rf, "nq": r_nq,
        "sp_2x": lev_daily(r_sp, rf, 2, FEES[2]), "sp_3x": lev_daily(r_sp, rf, 3, FEES[3]),
        "nq_2x": lev_daily(r_nq, rf, 2, FEES[2]), "nq_3x": lev_daily(r_nq, rf, 3, FEES[3]),
        "sp_up": gspc > gspc.rolling(200).mean(), "nq_up": ndx > ndx.rolling(200).mean(),
    }).iloc[1:]


def run(r, targets, cost, start):
    """Daily account: targets (decision date -> weights) are traded at the next day's close.

    r: daily returns by asset (row d = close d-1 to close d). cost: one-way cost per asset.
    Returns (equity Series, sum of each trade's cost as a fraction of the account, number of trades).
    """
    r = r[r.index >= start].fillna(0.0)
    assets = list(targets.columns)
    cost = np.array([cost.get(a, 0.0) for a in assets])
    R = r[assets].to_numpy()
    T = targets.reindex(r.index).to_numpy()
    h = np.zeros(len(assets))
    h[assets.index("CASH")] = 1.0
    eq, pending, paid, switches = [], None, 0.0, 0
    for i in range(len(r)):
        h = h * (1 + R[i])
        if pending is not None:
            V = h.sum()
            traded = np.abs(pending * V - h)
            c = float(traded @ cost)
            if traded.sum() > 1e-9:
                switches += 1
            paid += c / V
            h = pending * (V - c)
            pending = None
        if not np.isnan(T[i]).any():
            w = h / h.sum()
            if np.abs(T[i] - w).max() > 1e-6:
                pending = T[i]
        eq.append(h.sum())
    return pd.Series(eq, index=r.index), paid, switches


def month_ends(idx):
    s = pd.Series(idx, index=idx)
    return pd.DatetimeIndex(s.groupby(idx.to_period("M")).max().to_numpy())


def strategies(r, raw):
    """Target weights for each arm (row = decision date)."""
    days = r.index
    us = synthetic_usd(raw)
    # Decided on London day d from the US close of the same date (after London's close), so run()
    # trades it at the next London close.
    up_sp = us["sp_up"].reindex(days, method="ffill").fillna(False).astype(bool)
    up_nq = us["nq_up"].reindex(days, method="ffill").fillna(False).astype(bool)

    def hold(asset, cols):
        w = pd.DataFrame(0.0, index=days, columns=cols)
        w[asset] = 1.0
        return w

    def trend(asset, up):
        w = pd.DataFrame(0.0, index=days, columns=[asset, "CASH"])
        w[asset] = up.astype(float)
        w["CASH"] = 1 - w[asset]
        return w

    out = {"C1_sp500_buy_hold": hold("VUSA.L", ["VUSA.L", "CASH"])}
    # C2 dual momentum, decided on the last trading day of each month.
    lvl = (1 + r).cumprod()
    me = month_ends(days)
    m = lvl.reindex(me)
    r12 = m / m.shift(12) - 1
    g = pd.DataFrame(np.nan, index=days, columns=["VUSA.L", "EXUS", "IGLT.L", "CASH"])
    for d in me[12:]:
        w = {k: 0.0 for k in g.columns}
        if r12.loc[d, "VUSA.L"] > r12.loc[d, "CASH"]:
            w["VUSA.L" if r12.loc[d, "VUSA.L"] >= r12.loc[d, "EXUS"] else "EXUS"] = 1.0
        else:
            w["IGLT.L"] = 1.0
        g.loc[d] = pd.Series(w)
    out["C2_dual_momentum"] = g
    # C3 multi-asset trend: a fifth each, above the 10-month average, else cash.
    sleeves = ["VUSA.L", "VEUR.L", "IUKP.L", "IGLT.L", "SGLN.L"]
    sma = m[sleeves].rolling(10).mean()
    f = pd.DataFrame(np.nan, index=days, columns=sleeves + ["CASH"])
    for d in me[10:]:
        on = (m.loc[d, sleeves] > sma.loc[d]).astype(float) / len(sleeves)
        f.loc[d, sleeves] = on.to_numpy()
        f.loc[d, "CASH"] = 1 - on.sum()
    out["C3_multi_asset_trend"] = f
    out["C4_sp500_2x_trend"] = trend("XS2D.L", up_sp)
    out["C5_sp500_3x_trend"] = trend("3LUS.L", up_sp)
    out["C6_sp500_2x_buy_hold"] = hold("XS2D.L", ["XS2D.L", "CASH"])
    out["info_sp500_1x_trend"] = trend("VUSA.L", up_sp)
    out["info_nasdaq_3x_trend"] = trend("LQQ3.L", up_nq)
    out["info_nasdaq_2x_trend_synthetic"] = trend("NQ2_syn", up_nq)
    return out


COSTS = {"VUSA.L": ETF_COST, "EXUS": ETF_COST, "IGLT.L": ETF_COST, "VEUR.L": ETF_COST, "IUKP.L": ETF_COST,
         "SGLN.L": ETF_COST, "XS2D.L": LEV_COST + FX_FEE, "3LUS.L": LEV_COST, "LQQ3.L": LEV_COST,
         "NQ2_syn": LEV_COST + FX_FEE, "CASH": 0.0}


def weekly(eq):
    w = eq.resample("W-FRI").last().dropna()
    return w.pct_change().dropna()


def summarise(eq, paid=None, switches=None):
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    wr = weekly(eq)
    out = {"cagr": float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1),
           "ann_vol": float(wr.std() * np.sqrt(52)), "sharpe": float(wr.mean() / wr.std() * np.sqrt(52)),
           "max_drawdown_daily": float((eq / eq.cummax() - 1).min()),
           "max_drawdown_weekly": float(((1 + wr).cumprod() / (1 + wr).cumprod().cummax() - 1).min()),
           "p_drop_over_30pct_5y": float(p_drop(wr.to_numpy())),
           "worst_drop_trough": str((eq / eq.cummax() - 1).idxmin().date())}
    if paid is not None:
        out["cost_per_year"] = float(paid / years)
        out["switches_per_year"] = float(switches / years)
    return out


def long_history(raw):
    """1988-2026, USD, synthetic: the trend rule on S&P 500 1x/2x/3x, cash in T-bills."""
    us = synthetic_usd(raw).dropna(subset=["sp"])
    us = us[us.index >= "1989-01-01"]                       # after the first 200-day average exists
    res = {}
    for name, col, c in [("sp500_1x_trend", "sp", ETF_COST), ("sp500_2x_trend", "sp_2x", LEV_COST + FX_FEE),
                         ("sp500_3x_trend", "sp_3x", LEV_COST), ("sp500_buy_hold", "sp", 0.0),
                         ("sp500_2x_buy_hold", "sp_2x", 0.0)]:
        r = pd.DataFrame({"A": us[col], "CASH": us["rf"]})
        w = pd.DataFrame({"A": 1.0, "CASH": 0.0}, index=us.index)
        if "trend" in name:
            w["A"] = us["sp_up"].astype(float)              # signal at close d, run() trades at close d+1
            w["CASH"] = 1 - w["A"]
        eq, paid, sw = run(r, w, {"A": c, "CASH": 0.0}, us.index[0])
        s = summarise(eq, paid, sw)
        dd = eq / eq.cummax() - 1
        s["worst_drop_by_era"] = {era: float(dd[a:b].min()) for era, (a, b) in
                                  {"1989-1999": ("1989", "1999"), "2000-2009": ("2000", "2009"),
                                   "2010-2015": ("2010", "2015"), "2016-2026": ("2016", "2026")}.items()}
        res[name] = s
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    raw = download(args.refresh)
    r, repaired = gbp_returns(raw)
    OUT.mkdir(parents=True, exist_ok=True)

    # Synthetic vs real products, 2016-2026 (GBP, repaired days excluded from the correlation).
    track = {}
    rr = r[r.index >= START]
    for real, syn in [("XS2D.L", "SP2_syn"), ("3LUS.L", "SP3_syn"), ("LQQ3.L", "NQ3_syn")]:
        yrs = len(rr) / 252
        track[real] = {"bad_prints_replaced": [d for d in repaired[real] if d >= str(START.date())],
                       "real_cagr": float((1 + rr[real]).prod() ** (1 / yrs) - 1),
                       "synthetic_cagr": float((1 + rr[syn]).prod() ** (1 / yrs) - 1),
                       "weekly_corr": float(weekly((1 + rr[real]).cumprod()).corr(weekly((1 + rr[syn]).cumprod())))}
    print(json.dumps(track, indent=2), flush=True)

    arms, curves = {}, {}
    for name, w in strategies(r, raw).items():
        eq, paid, sw = run(r, w, COSTS, START)
        curves[name] = eq
        arms[name] = summarise(eq, paid, sw)
        print(name, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in arms[name].items()}, flush=True)

    # tx_blend (weekly, Monday fills) and the 50/50 mix with C4, rebalanced on the first fill of each month.
    tx = pd.read_csv(TX_BLEND, parse_dates=["signal_date", "exec_date"])
    tx_eq = tx.set_index("exec_date")["equity"]
    c4 = curves["C4_sp500_2x_trend"].reindex(tx_eq.index, method="ffill")
    a, b = tx_eq.pct_change().fillna(0), c4.pct_change().fillna(0)
    v1, v2, mix = 0.5, 0.5, []
    for i, d in enumerate(tx_eq.index):
        v1, v2 = v1 * (1 + a.iloc[i]), v2 * (1 + b.iloc[i])
        if i == 0 or d.month != tx_eq.index[i - 1].month:
            v1 = v2 = (v1 + v2) / 2
        mix.append(v1 + v2)
    mix = pd.Series(mix, index=tx_eq.index)
    for name, s in [("tx_blend_reference", tx_eq), ("C7_half_tx_blend_half_C4", mix)]:
        wr = s.pct_change().dropna()
        eqw = (1 + wr).cumprod()
        yrs = len(wr) / 52
        arms[name] = {"cagr": float(eqw.iloc[-1] ** (1 / yrs) - 1), "ann_vol": float(wr.std() * np.sqrt(52)),
                      "sharpe": float(wr.mean() / wr.std() * np.sqrt(52)),
                      "max_drawdown_weekly": float((eqw / eqw.cummax() - 1).min()),
                      "p_drop_over_30pct_5y": p_drop(wr.to_numpy())}
        print(name, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in arms[name].items()}, flush=True)
    corr = float(a.corr(b))

    longh = long_history(raw)
    for k, v in longh.items():
        print("long", k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()}, flush=True)

    bar = arms["tx_blend_reference"]
    gates = {}
    for name in ["C1_sp500_buy_hold", "C2_dual_momentum", "C3_multi_asset_trend", "C4_sp500_2x_trend", "C5_sp500_3x_trend"]:
        s = arms[name]
        lh = {"C4_sp500_2x_trend": "sp500_2x_trend", "C5_sp500_3x_trend": "sp500_3x_trend"}.get(name)
        risk = longh[lh]["p_drop_over_30pct_5y"] if lh else s["p_drop_over_30pct_5y"]
        gates[name] = {"beats_cagr": bool(s["cagr"] > bar["cagr"]), "drop_ok": bool(s["max_drawdown_daily"] >= -0.30),
                       "risk_ok": bool(risk <= 0.151), "risk_used": float(risk)}
        gates[name]["candidate"] = bool(gates[name]["beats_cagr"] and gates[name]["drop_ok"] and gates[name]["risk_ok"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = {"run_at": now, "tracking": track, "arms": arms, "weekly_corr_tx_blend_vs_C4": corr,
              "long_history_usd": longh, "gates": gates}
    (OUT / "summary.json").write_text(json.dumps(result, indent=2, default=float))
    pd.DataFrame(curves).to_csv(OUT / "equity_daily.csv")
    rows = [{"run_at": now, "stage": "phase3", "tag": f"C_{k}", "config": "etf", "seeds": "", "weeks": "",
             "ic_tx": "", "ic_lgbm": "", "gate_t": "", "gate_pass": g["candidate"],
             "note": f"CAGR {arms[k]['cagr']:.3f}, MDD {arms[k]['max_drawdown_daily']:.3f}, P(>30% in 5y) {g['risk_used']:.3f}"}
            for k, g in gates.items()]
    pd.DataFrame(rows).to_csv(ROOT / "research" / "trials.csv", mode="a", header=False, index=False)
    print(json.dumps(gates, indent=2, default=float))


if __name__ == "__main__":
    main()
