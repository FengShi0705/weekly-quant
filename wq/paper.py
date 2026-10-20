"""Paper trading: one simulated account per strategy, run weekly.

Each run, for every strategy in paper/strategies.yaml:
  1. fill last run's orders at the close of the execution day (the Monday after the signal), with the
     same cost model and cash rules as the backtest, and deduct the dividend tax withheld on what was
     held since the last run;
  2. value the account at the latest close, next to buy & hold of the benchmark funds;
  3. score this week and save the new orders, to be filled at the next run.

State lives in paper/<strategy>/ and is committed to git, so any machine can continue it:
  holdings.csv, pending_orders.csv, ledger.csv (every fill), nav.csv (weekly value),
  raw_scores.csv (weekly model scores) and reports/<date>/ (the order sheet).
"""
import copy

import pandas as pd
import yaml

from .backtest import prepare
from .costs import dividend_tax, dividend_tax_per_share
from .data import load_benchmarks, load_dividends, usd_per_base
from .portfolio import execute
from .weekly import plan, read_holdings


def deep_merge(base, over):
    for k, v in over.items():
        base[k] = deep_merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return base


def strategy_configs(cfg, spec_path):
    spec = yaml.safe_load(spec_path.read_text())
    out = {}
    for name, over in spec["strategies"].items():
        c = deep_merge(copy.deepcopy(cfg), over or {})
        d = spec_path.parent / name
        c["account"]["capital"] = spec["start_capital"]
        c["paths"].update(holdings=d / "holdings.csv", reports=d / "reports", score_history=d / "raw_scores.csv")
        c["paper_dir"] = d
        out[name] = c
    return out


def write_holdings(path, shares, cash):
    rows = [{"ticker": t, "shares": round(q, 6)} for t, q in sorted(shares.items()) if q > 0]
    rows.append({"ticker": "CASH", "shares": round(cash, 2)})
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _append_csv(path, df, key=None):
    if path.exists():
        old = pd.read_csv(path)
        if key is not None:
            old = old[~old[key].astype(str).isin(df[key].astype(str))]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(path, index=False)


def exec_date(cfg, px):
    """The day last run's orders fill: the first trading day after their signal date (None if not yet)."""
    path = cfg["paper_dir"] / "pending_orders.csv"
    if not path.exists():
        return None
    later = px.index[px.index > pd.Timestamp(pd.read_csv(path)["signal_date"].iloc[0])]
    return later[0] if len(later) else None


def fill_pending(cfg, px, universe, fx_usd):
    """Fill last run's orders at the close of the first trading day after their signal date."""
    d = cfg["paper_dir"]
    path = d / "pending_orders.csv"
    if not path.exists():
        return []
    pending = pd.read_csv(path, parse_dates=["signal_date"])
    signal = pending["signal_date"].iloc[0]
    e = exec_date(cfg, px)
    if e is None:
        print(f"  orders from {signal.date()} can't be filled yet (no later prices)")
        return []
    price = px.ffill().loc[e]
    shares, cash = read_holdings(cfg["paths"]["holdings"], cfg["account"]["capital"])
    orders = [{"ticker": r.ticker, "side": r.side, "shares": float(r.shares),
               "value": float(r.shares) * float(price[r.ticker]), "reason": r.reason}
              for r in pending.itertuples() if pd.notna(price.get(r.ticker))]
    base = cfg["account"]["base_currency"]
    shares, cash, cost, filled = execute(orders, shares, cash, price, universe, cfg, usd_per_base(fx_usd, base, e))
    write_holdings(cfg["paths"]["holdings"], shares, cash)
    if filled:
        rows = pd.DataFrame([{"signal_date": signal.date(), "exec_date": e.date(), "ticker": o["ticker"],
                              "side": o["side"], "shares": round(o["shares"], 6),
                              "price_" + base: round(o["value"] / o["shares"], 4),
                              "value_" + base: round(o["value"], 2), "cost_" + base: round(o["cost"], 2),
                              "reason": o["reason"]} for o in filled])
        _append_csv(d / "ledger.csv", rows)
    path.unlink()
    print(f"  filled {len(filled)} orders at the {e.date()} close (costs {cost:,.2f} {base})")
    return filled


def charge_dividend_tax(cfg, cum_tax, start, end):
    """Deduct from cash the dividend tax withheld on the current holdings between two days."""
    path = cfg["paths"]["holdings"]
    shares, cash = read_holdings(path, cfg["account"]["capital"])
    tax = dividend_tax(shares, cum_tax, start, end)
    if tax:
        write_holdings(path, shares, cash - tax)
    return tax


def last_nav_date(cfg):
    path = cfg["paper_dir"] / "nav.csv"
    return pd.Timestamp(pd.read_csv(path)["date"].iloc[-1]) if path.exists() else None


def record_nav(cfg, px, etf_px, dividend_tax=0.0):
    d = cfg["paper_dir"]
    shares, cash = read_holdings(cfg["paths"]["holdings"], cfg["account"]["capital"])
    last = px.index[-1]
    price = px.ffill().loc[last]
    equity = cash + sum(q * price[t] for t, q in shares.items())
    row = {"date": last.date(), "equity": round(equity, 2), "cash": round(cash, 2), "positions": len(shares),
           "dividend_tax": round(dividend_tax, 2)}
    if etf_px is not None:
        etf = etf_px.ffill().loc[:last].iloc[-1]
        row |= {f"{t}_price": round(float(v), 4) for t, v in etf.items()}
    _append_csv(d / "nav.csv", pd.DataFrame([row]), key="date")
    return equity


def save_pending(cfg, result):
    if not result["orders"]:
        return
    pd.DataFrame([{"signal_date": result["signal_date"].date(), "ticker": o["ticker"], "side": o["side"],
                   "shares": round(o["shares"], 6), "reason": o["reason"]} for o in result["orders"]]
                 ).to_csv(cfg["paper_dir"] / "pending_orders.csv", index=False)


def summary(cfgs, etf_names):
    lines = ["# Paper trading", "",
             "Simulated fills at the Monday close after each signal, with the backtest's cost model.", ""]
    rows = []
    for name, cfg in cfgs.items():
        nav_path = cfg["paper_dir"] / "nav.csv"
        if not nav_path.exists():
            continue
        nav = pd.read_csv(nav_path)
        start, now = nav.iloc[0], nav.iloc[-1]
        ledger = cfg["paper_dir"] / "ledger.csv"
        fills = pd.read_csv(ledger) if ledger.exists() else pd.DataFrame()
        cost_col = [c for c in fills.columns if c.startswith("cost_")]
        row = {"strategy": name, "since": start["date"], "latest": now["date"],
               "value": f"{now['equity']:,.2f}", "return": f"{now['equity'] / cfg['account']['capital'] - 1:+.2%}",
               "trades": len(fills), "costs": f"{fills[cost_col[0]].sum():,.2f}" if cost_col else "0.00",
               "dividend tax": f"{nav['dividend_tax'].fillna(0).sum():,.2f}" if "dividend_tax" in nav else "0.00"}
        for t, label in etf_names.items():
            if f"{t}_price" in nav:
                row[f"{label} buy & hold"] = f"{now[f'{t}_price'] / start[f'{t}_price'] - 1:+.2%}"
        rows.append(row)
    lines.append(pd.DataFrame(rows).to_markdown(index=False) if rows else "_No paper runs yet._")
    return "\n".join(lines) + "\n"


def run(cfg, close_local, volume, fx_usd, universe, spec_path):
    cfgs = strategy_configs(cfg, spec_path)
    etf_px = load_benchmarks(cfg, fx_usd)
    div_yield = load_dividends(cfg)
    prepared, div_tax, failed = {}, {}, {}
    for name, c in cfgs.items():
        print(f"\n=== {name} ===")
        try:
            _run_strategy(c, close_local, volume, fx_usd, universe, etf_px, div_yield, prepared, div_tax)
        except Exception as e:                      # one strategy failing must not block the others
            failed[name] = f"{type(e).__name__}: {e}"
            print(f"  FAILED: {failed[name]}")
    etf_names = {t: v["name"] for t, v in cfg["benchmarks"]["etfs"].items()}
    text = summary(cfgs, etf_names)
    if failed:
        text += "\n**Failed this run:** " + "; ".join(f"{k} ({v})" for k, v in failed.items()) + "\n"
    (spec_path.parent / "summary.md").write_text(text)
    print("\n" + text)
    if failed:
        raise RuntimeError(f"paper run failed for: {', '.join(failed)} (the other strategies completed)")
    return cfgs


def _run_strategy(c, close_local, volume, fx_usd, universe, etf_px, div_yield, prepared, div_tax):
    """Advance one strategy: fill last run's orders, deduct dividend tax, value it, plan this week."""
    key = (str(c["universe"]), c["model"]["label_horizon_weeks"])
    if key not in prepared:
        prepared[key] = prepare(c, close_local, volume, fx_usd, universe)
        div_tax[key] = (dividend_tax_per_share(prepared[key][2], div_yield, universe, c)
                        if div_yield is not None else None)
    _, _, px = prepared[key]
    c["paper_dir"].mkdir(parents=True, exist_ok=True)
    if not c["paths"]["holdings"].exists():
        write_holdings(c["paths"]["holdings"], {}, c["account"]["capital"])
    # Dividend tax on what was held since the last run: the old holdings up to the fill, the new after.
    since, e, last = last_nav_date(c), exec_date(c, px), px.index[-1]
    withheld = charge_dividend_tax(c, div_tax[key], since, e if e is not None else last)
    fill_pending(c, px, universe, fx_usd)
    if e is not None:
        withheld += charge_dividend_tax(c, div_tax[key], max(e, since) if since is not None else e, last)
    equity = record_nav(c, px, etf_px, withheld)
    print(f"  account value {equity:,.2f} {c['account']['base_currency']}")
    shares, cash = read_holdings(c["paths"]["holdings"], c["account"]["capital"])
    save_pending(c, plan(c, close_local, volume, fx_usd, universe, shares, cash, prepared[key]))
