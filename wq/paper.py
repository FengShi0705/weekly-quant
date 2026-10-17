"""Paper trading: one simulated account per strategy, run weekly.

Each run, for every strategy in paper/strategies.yaml:
  1. fill last run's orders at the close of the execution day (the Monday after the signal), with the
     same cost model and cash rules as the backtest;
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
from .data import load_benchmarks, usd_per_base
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


def fill_pending(cfg, px, universe, fx_usd):
    """Fill last run's orders at the close of the first trading day after their signal date."""
    d = cfg["paper_dir"]
    path = d / "pending_orders.csv"
    if not path.exists():
        return []
    pending = pd.read_csv(path, parse_dates=["signal_date"])
    signal = pending["signal_date"].iloc[0]
    later = px.index[px.index > signal]
    if len(later) == 0:
        print(f"  orders from {signal.date()} can't be filled yet (no later prices)")
        return []
    e = later[0]
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


def record_nav(cfg, px, etf_px):
    d = cfg["paper_dir"]
    shares, cash = read_holdings(cfg["paths"]["holdings"], cfg["account"]["capital"])
    last = px.index[-1]
    price = px.ffill().loc[last]
    equity = cash + sum(q * price[t] for t, q in shares.items())
    row = {"date": last.date(), "equity": round(equity, 2), "cash": round(cash, 2), "positions": len(shares)}
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
               "trades": len(fills), "costs": f"{fills[cost_col[0]].sum():,.2f}" if cost_col else "0.00"}
        for t, label in etf_names.items():
            if f"{t}_price" in nav:
                row[f"{label} buy & hold"] = f"{now[f'{t}_price'] / start[f'{t}_price'] - 1:+.2%}"
        rows.append(row)
    lines.append(pd.DataFrame(rows).to_markdown(index=False) if rows else "_No paper runs yet._")
    return "\n".join(lines) + "\n"


def run(cfg, close_local, volume, fx_usd, universe, spec_path):
    cfgs = strategy_configs(cfg, spec_path)
    etf_px = load_benchmarks(cfg, fx_usd)
    prepared = {}
    for name, c in cfgs.items():
        print(f"\n=== {name} ===")
        key = (str(c["universe"]), c["model"]["label_horizon_weeks"])
        if key not in prepared:
            prepared[key] = prepare(c, close_local, volume, fx_usd, universe)
        _, _, px = prepared[key]
        c["paper_dir"].mkdir(parents=True, exist_ok=True)
        if not c["paths"]["holdings"].exists():
            write_holdings(c["paths"]["holdings"], {}, c["account"]["capital"])
        fill_pending(c, px, universe, fx_usd)
        equity = record_nav(c, px, etf_px)
        print(f"  account value {equity:,.2f} {c['account']['base_currency']}")
        shares, cash = read_holdings(c["paths"]["holdings"], c["account"]["capital"])
        save_pending(c, plan(c, close_local, volume, fx_usd, universe, shares, cash, prepared[key]))
    etf_names = {t: v["name"] for t, v in cfg["benchmarks"]["etfs"].items()}
    text = summary(cfgs, etf_names)
    (spec_path.parent / "summary.md").write_text(text)
    print("\n" + text)
    return cfgs
