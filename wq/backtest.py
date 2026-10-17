"""Weekly walk-forward backtest using the same portfolio rules as the live run."""
import numpy as np
import pandas as pd

from .costs import trade_cost
from .data import to_base, usd_per_base
from .features import build_panel, market_index
from .model import information_coefficients, smooth_scores, walk_forward
from .portfolio import execute, generate_orders, regime_exposure, select_targets

VARIANTS = ["score", "ml", "baseline"]


def prepare(cfg, close_local, volume, fx_usd, universe):
    px_base = to_base(close_local, universe["currency"], fx_usd, cfg["account"]["base_currency"])
    return build_panel(px_base, volume, universe, cfg)


def simulate(scores, panel, cal, px, universe, fx_usd, cfg, variant="score", capital=None, deposits=None):
    """deposits: optional Series signal_date -> cash added before that week's trades."""
    base = cfg["account"]["base_currency"]
    px_val = px.ffill()
    mkt_w = market_index(px).reindex(cal.index, method="ffill")
    cash = float(cfg["account"]["capital"] if capital is None else capital)
    shares, rows, trades = {}, [], []
    for T in scores.index.get_level_values("date").unique():
        e = cal.loc[T, "exec_date"]
        if pd.isna(e):
            break
        price = px_val.loc[e]
        deposit = float(deposits.get(T, 0.0)) if deposits is not None else 0.0
        cash += deposit
        equity = cash + sum(q * price[t] for t, q in shares.items())
        s = scores.xs(T, level="date")[variant]
        expo = regime_exposure(mkt_w, T, cfg)
        vol = panel.xs(T, level="date")["raw_vol_60"]
        targets = select_targets(s, set(shares), universe, price, equity, cfg, expo, vol)
        orders = generate_orders(shares, targets, price, equity, universe, cfg, cash)
        shares, cash, cost, filled = execute(orders, shares, cash, price, universe, cfg,
                                             usd_per_base(fx_usd, base, e))
        rows.append({"signal_date": T, "exec_date": e, "deposit": deposit, "equity": equity, "cash_after": cash,
                     "positions": len(shares), "exposure": expo, "cost": cost,
                     "turnover": sum(o["value"] for o in filled) / equity if equity > 0 else 0.0})
        trades += [{"signal_date": T, "exec_date": e, **o} for o in filled]
    res = pd.DataFrame(rows).set_index("signal_date")
    # Weekly return excludes next week's deposit, so CAGR and Sharpe measure investment skill only.
    res["ret"] = (res["equity"].shift(-1) - res["deposit"].shift(-1)) / res["equity"] - 1
    return res, pd.DataFrame(trades)


def benchmark_returns(panel, dates):
    """Equal-weight return of every eligible stock, from exec(T) to exec(T+1), no costs."""
    return panel["fwd_ret_1w"].groupby(level="date").mean().reindex(dates)


def monthly_deposits(dates, amount):
    """Deposit `amount` on the first signal date of each calendar month."""
    dates = pd.DatetimeIndex(dates)
    first = pd.Series(dates, index=dates).groupby(dates.to_period("M")).min()
    return pd.Series(np.where(dates.isin(first), float(amount), 0.0), index=dates)


def etf_value(etf_px, cal, dates, cfg, currency, capital=0.0, deposits=None):
    """Value of buying an ETF with `capital` up front plus any deposits, and never selling.

    etf_px: daily ETF price in base currency. Returns a Series indexed by signal date (pre-deposit
    value at that week's exec date, matching simulate()'s equity column).
    """
    exec_dates = pd.DatetimeIndex(cal.loc[dates, "exec_date"])
    # ETF trades on fewer days than the global calendar (e.g. UK bank holidays): use its last close.
    p = etf_px.reindex(etf_px.index.union(exec_dates)).ffill().reindex(exec_dates).to_numpy()
    units, values = 0.0, []
    for i, T in enumerate(dates):
        values.append(units * p[i])
        cash = (capital if i == 0 else 0.0) + (float(deposits.get(T, 0.0)) if deposits is not None else 0.0)
        if cash > 0 and p[i] > 0:
            cost = trade_cost(cash, cash / p[i], "ETF", currency, "buy", cfg)
            units += (cash - cost) / p[i]
    v = pd.Series(values, index=dates)
    v.iloc[0] = capital
    return v


def xirr(dates, flows):
    """Money-weighted annual return for dated cash flows (deposits negative, final value positive)."""
    t = np.array([(d - dates[0]).days / 365.25 for d in dates])
    f = np.asarray(flows, dtype=float)

    def npv(r):
        return (f / (1 + r) ** t).sum()

    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return np.nan
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def dca_summary(values, deposits, final_date):
    """values: pre-deposit value per signal date. The last row's value is the final value."""
    deps = deposits.reindex(values.index).fillna(0.0)
    final = float(values.iloc[-1])
    invested = float(deps.iloc[:-1].sum())
    flows = list(-deps.iloc[:-1]) + [final]
    dates = list(values.index[:-1]) + [final_date]
    return {"invested": invested, "final_value": final, "gain": final - invested, "xirr": xirr(dates, flows)}


def metrics(r):
    r = r.dropna()
    if len(r) < 2:
        return {}
    eq = (1 + r).cumprod()
    years = len(r) / 52
    return {
        "weeks": len(r),
        "cagr": eq.iloc[-1] ** (1 / years) - 1,
        "ann_vol": r.std() * np.sqrt(52),
        "sharpe": r.mean() / r.std() * np.sqrt(52) if r.std() > 0 else np.nan,
        "max_drawdown": (eq / eq.cummax() - 1).min(),
        "best_week": r.max(),
        "worst_week": r.min(),
        "pct_weeks_up": (r > 0).mean(),
    }


def ic_summary(ic):
    return {c: {"mean": ic[c].mean(), "t_stat": ic[c].mean() / ic[c].std() * np.sqrt(ic[c].count()),
                "pct_positive": (ic[c] > 0).mean()} for c in ic.columns}


def run(cfg, close_local, volume, fx_usd, universe, etf_px=None, verbose=True):
    panel, cal, px = prepare(cfg, close_local, volume, fx_usd, universe)
    start = pd.Timestamp(cfg["backtest"]["start"])
    pred_dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    if verbose:
        print(f"Walk-forward over {len(pred_dates)} weeks, {panel.index.get_level_values('ticker').nunique()} stocks")
    scores = smooth_scores(walk_forward(panel, cfg, pred_dates, verbose=verbose),
                           cfg["model"]["score_smoothing_weeks"])
    ic = information_coefficients(scores, panel)
    capital = float(cfg["account"]["capital"])

    results, summary = {}, {"ic": ic_summary(ic)}
    for v in VARIANTS:
        res, trades = simulate(scores, panel, cal, px, universe, fx_usd, cfg, v)
        results[v] = (res, trades)
        m = metrics(res["ret"])
        m["final_value"] = float(res["equity"].iloc[-1])
        m["avg_weekly_turnover"] = res["turnover"].mean()
        m["total_costs"] = res["cost"].sum()
        m["cost_drag_per_year"] = (res["cost"] / res["equity"]).sum() / (len(res) / 52)
        summary[v] = m
    dates = results["score"][0].index
    bench = benchmark_returns(panel, dates)
    summary["benchmark_equal_weight"] = metrics(bench) | {"final_value": capital * float((1 + bench.iloc[:-1]).prod())}
    curves = {"score": results["score"][0]["equity"], "equal_weight": capital * (1 + bench.shift(1).fillna(0)).cumprod()}

    # Real-world alternatives: buy & hold an index fund, and monthly fixed-amount investing (DCA).
    dca, by_year_cols = {}, {"strategy": results["score"][0]["ret"], "equal_weight": bench}
    if etf_px is not None:
        deposits = monthly_deposits(dates, cfg["benchmarks"]["dca_monthly"])
        final_date = results["score"][0]["exec_date"].iloc[-1]
        res_dca, _ = simulate(scores, panel, cal, px, universe, fx_usd, cfg, "score", capital=0.0, deposits=deposits)
        dca["strategy"] = res_dca["equity"] - res_dca["deposit"]
        summary["dca_strategy"] = dca_summary(dca["strategy"], deposits, final_date)
        etfs = cfg["benchmarks"]["etfs"]
        for t in etf_px.columns:
            ccy = etfs[t]["currency"]
            hold = etf_value(etf_px[t], cal, dates, cfg, ccy, capital=capital)
            r = hold.shift(-1) / hold - 1
            summary[f"buy_hold_{t}"] = metrics(r) | {"final_value": float(hold.iloc[-1])}
            curves[t] = hold
            by_year_cols[t] = r
            dca[t] = etf_value(etf_px[t], cal, dates, cfg, ccy, deposits=deposits)
            summary[f"dca_{t}"] = dca_summary(dca[t], deposits, final_date)
        dca["deposited"] = deposits.cumsum().shift(1).fillna(0.0)

    by_year = pd.DataFrame(by_year_cols)
    by_year = (1 + by_year).groupby(by_year.index.year).prod(min_count=1) - 1
    return {"summary": summary, "results": results, "benchmark": bench, "ic": ic, "scores": scores,
            "by_year": by_year, "curves": curves, "dca": dca}
