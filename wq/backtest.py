"""Weekly walk-forward backtest using the same portfolio rules as the live run."""
import numpy as np
import pandas as pd

from .data import to_base, usd_per_base
from .features import build_panel, market_index
from .model import information_coefficients, walk_forward
from .portfolio import execute, generate_orders, regime_exposure, select_targets

VARIANTS = ["score", "ml", "baseline"]


def prepare(cfg, close_local, volume, fx_usd, universe):
    px_base = to_base(close_local, universe["currency"], fx_usd, cfg["account"]["base_currency"])
    return build_panel(px_base, volume, universe, cfg)


def simulate(scores, panel, cal, px, universe, fx_usd, cfg, variant="score"):
    base = cfg["account"]["base_currency"]
    px_val = px.ffill()
    mkt_w = market_index(px).reindex(cal.index, method="ffill")
    cash, shares = float(cfg["account"]["capital"]), {}
    rows, trades = [], []
    for T in scores.index.get_level_values("date").unique():
        e = cal.loc[T, "exec_date"]
        if pd.isna(e):
            break
        price = px_val.loc[e]
        equity = cash + sum(q * price[t] for t, q in shares.items())
        s = scores.xs(T, level="date")[variant]
        expo = regime_exposure(mkt_w, T, cfg)
        targets = select_targets(s, set(shares), universe, price, equity, cfg, expo)
        orders = generate_orders(shares, targets, price, equity, universe, cfg)
        shares, cash, cost, filled = execute(orders, shares, cash, price, universe, cfg,
                                             usd_per_base(fx_usd, base, e))
        rows.append({"signal_date": T, "exec_date": e, "equity": equity, "cash_after": cash,
                     "positions": len(shares), "exposure": expo, "cost": cost,
                     "turnover": sum(o["value"] for o in filled) / equity if equity > 0 else 0.0})
        trades += [{"signal_date": T, "exec_date": e, **o} for o in filled]
    res = pd.DataFrame(rows).set_index("signal_date")
    res["ret"] = res["equity"].shift(-1) / res["equity"] - 1
    return res, pd.DataFrame(trades)


def benchmark_returns(panel, dates):
    """Equal-weight return of every eligible stock, from exec(T) to exec(T+1), no costs."""
    return panel["fwd_ret_1w"].groupby(level="date").mean().reindex(dates)


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


def run(cfg, close_local, volume, fx_usd, universe, verbose=True):
    panel, cal, px = prepare(cfg, close_local, volume, fx_usd, universe)
    start = pd.Timestamp(cfg["backtest"]["start"])
    pred_dates = [d for d in cal.index if d >= start and pd.notna(cal.loc[d, "exec_date"])]
    if verbose:
        print(f"Walk-forward over {len(pred_dates)} weeks, {panel.index.get_level_values('ticker').nunique()} stocks")
    scores = walk_forward(panel, cfg, pred_dates, verbose=verbose)
    ic = information_coefficients(scores, panel)

    results, summary = {}, {"ic": ic_summary(ic)}
    for v in VARIANTS:
        res, trades = simulate(scores, panel, cal, px, universe, fx_usd, cfg, v)
        results[v] = (res, trades)
        m = metrics(res["ret"])
        m["avg_weekly_turnover"] = res["turnover"].mean()
        m["total_costs"] = res["cost"].sum()
        m["costs_pct_of_capital_per_year"] = res["cost"].sum() / cfg["account"]["capital"] / (len(res) / 52)
        summary[v] = m
    bench = benchmark_returns(panel, results["score"][0].index)
    summary["benchmark_equal_weight"] = metrics(bench)
    return {"summary": summary, "results": results, "benchmark": bench, "ic": ic, "scores": scores}
