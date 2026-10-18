import argparse
import json

import numpy as np
import pandas as pd

from . import backtest, paper, weekly
from .config import load_config
from .data import download, load_benchmarks, load_cached, load_universe

# Reference palette (light): categorical slots in fixed order; the stock-universe benchmark recedes in gray.
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
GRAY = "#8a8984"
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
SYMBOL = {"GBP": "£", "USD": "$", "EUR": "€"}
VARIANT_NAMES = {"score": "Strategy (ML + momentum)", "ml": "ML only", "baseline": "Momentum baseline"}


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, lw=0.8)
    ax.tick_params(colors=INK_2, labelsize=9)
    for s in ax.spines.values():
        s.set_visible(False)


def _lines(ax, series, money, log=False):
    """series: list of (label, Series, color, linestyle). Draws lines with collision-free end labels."""
    import matplotlib

    for label, s, color, ls in series:
        ax.plot(s.index, s.values, ls, color=color, lw=2, label=label)
    if log:
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 3, 5)))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda y, _: money(y)))
    fwd, inv = (np.log10, lambda v: 10 ** v) if log else ((lambda v: v), (lambda v: v))
    y0, y1 = ax.get_ylim()
    gap, prev = 0.045 * (fwd(y1) - fwd(y0)), -np.inf
    for label, s, _, _ in sorted(series, key=lambda x: x[1].iloc[-1]):
        prev = max(fwd(max(s.iloc[-1], y0)), prev + gap)
        ax.text(s.index[-1] + pd.Timedelta(days=30), inv(prev), f"{label}  {money(s.iloc[-1])}",
                va="center", fontsize=9, color=INK_2)
    _style(ax)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_2, loc="upper left")


def _plot(out, res, cfg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sym = SYMBOL.get(cfg["account"]["base_currency"], "")
    money = lambda v: f"{sym}{v / 1000:,.0f}k" if abs(v) >= 1000 else f"{sym}{v:,.0f}"
    etfs = cfg["benchmarks"]["etfs"]
    c = res["curves"]
    lump = [(VARIANT_NAMES["score"], c["score"], SLOTS[0], "-")]
    lump += [(f"{etfs[t]['name']} (buy & hold)", c[t], SLOTS[i + 1], "-") for i, t in enumerate(etfs) if t in c]
    lump += [("Equal-weight stock universe", c["equal_weight"], GRAY, "--")]

    fig, (ax, ax_dd) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1.3]}, facecolor=SURFACE)
    _lines(ax, lump, money, log=True)
    ax.set_title(f"{money(cfg['account']['capital'])} invested once, Jan 2016 (after costs)", loc="left",
                 color=INK, fontsize=12)
    for label, s, color, ls in lump[:-1]:
        dd = s / s.cummax() - 1
        ax_dd.plot(dd.index, dd.values, ls, color=color, lw=1.5)
    ax_dd.set_title("Drawdown from previous peak", loc="left", color=INK, fontsize=10)
    ax_dd.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    _style(ax_dd)
    fig.subplots_adjust(right=0.74, hspace=0.25)
    fig.savefig(out / "equity.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)

    if not res["dca"]:
        return
    d = res["dca"]
    monthly = cfg["benchmarks"]["dca_monthly"]
    dca = [(VARIANT_NAMES["score"], d["strategy"], SLOTS[0], "-")]
    dca += [(etfs[t]["name"], d[t], SLOTS[i + 1], "-") for i, t in enumerate(etfs) if t in d]
    dca += [("Total deposited", d["deposited"], GRAY, "--")]
    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=SURFACE)
    _lines(ax, dca, money)
    ax.set_title(f"{money(monthly)} invested every month from Jan 2016 (after costs)", loc="left",
                 color=INK, fontsize=12)
    fig.subplots_adjust(right=0.78)
    fig.savefig(out / "dca.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)


def _tables(res, cfg):
    s, etfs = res["summary"], cfg["benchmarks"]["etfs"]
    rows = {VARIANT_NAMES[v]: s[v] for v in ["score", "ml", "baseline"]}
    rows |= {f"Buy & hold {etfs[t]['name']}": s[f"buy_hold_{t}"] for t in etfs if f"buy_hold_{t}" in s}
    rows["Equal-weight stock universe"] = s["benchmark_equal_weight"]
    lump = pd.DataFrame(rows).T[["final_value", "cagr", "ann_vol", "sharpe", "max_drawdown"]]
    dca_rows = {VARIANT_NAMES["score"]: s.get("dca_strategy")}
    dca_rows |= {etfs[t]["name"]: s.get(f"dca_{t}") for t in etfs}
    dca = pd.DataFrame({k: v for k, v in dca_rows.items() if v}).T
    return lump, dca


def cmd_backtest(cfg):
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    etf_px = load_benchmarks(cfg, fx)
    res = backtest.run(cfg, close, volume, fx, universe, etf_px=etf_px)
    out = cfg["paths"]["reports"] / "backtest"
    out.mkdir(parents=True, exist_ok=True)
    for k, (r, trades) in res["results"].items():
        r.to_csv(out / f"weekly_{k}.csv")
        trades.to_csv(out / f"trades_{k}.csv", index=False)
    res["ic"].to_csv(out / "ic_weekly.csv")
    res["by_year"].to_csv(out / "by_year.csv")
    (out / "summary.json").write_text(json.dumps(res["summary"], indent=2, default=float))
    _plot(out, res, cfg)

    pct = lambda x: f"{x:.1%}"
    money = lambda x: f"{x:,.0f}"
    lump, dca = _tables(res, cfg)
    base = cfg["account"]["base_currency"]
    print(f"\nLump sum: {cfg['account']['capital']:,} {base} invested once at the start")
    print(lump.to_string(formatters={"final_value": money, "cagr": pct, "ann_vol": pct, "max_drawdown": pct,
                                     "sharpe": "{:.2f}".format}))
    if len(dca):
        print(f"\nMonthly investing: {cfg['benchmarks']['dca_monthly']:,} {base} every month "
              "(xirr = money-weighted annual return)")
        print(dca.to_string(formatters={"invested": money, "final_value": money, "gain": money, "xirr": pct}))
    print("\nInformation coefficient (weekly Spearman, score vs next-week return):")
    print(pd.DataFrame(res["summary"]["ic"]).T.to_string(float_format=lambda x: f"{x:.3f}"))
    print("\nCalendar-year returns (after costs):")
    print(res["by_year"].to_string(float_format=pct))
    print(f"\nWritten to {out}/")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="wq", description="Weekly global equity strategy")
    ap.add_argument("--config", default="config.yaml")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="download prices, volumes and FX into the cache")
    sub.add_parser("backtest", help="run the walk-forward backtest on cached data")
    w = sub.add_parser("weekly", help="score the latest week and write this week's order sheet")
    w.add_argument("--no-download", action="store_true", help="use cached data instead of refreshing")
    pp = sub.add_parser("paper", help="advance every paper-trading strategy by one week")
    pp.add_argument("--no-download", action="store_true", help="use cached data instead of refreshing")
    pp.add_argument("--spec", default="paper/strategies.yaml")
    tp = sub.add_parser("t212", help="mirror the paper strategy's orders in a Trading 212 Practice account")
    tp.add_argument("--execute", action="store_true", help="send the orders (default: dry run)")
    tp.add_argument("--retry-rejected", action="store_true",
                    help="resend only this week's orders that Trading 212 rejected (HTTP 400)")
    tp.add_argument("--spec", default="paper/strategies.yaml")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)

    if args.cmd == "download":
        download(cfg)
    elif args.cmd == "backtest":
        cmd_backtest(cfg)
    elif args.cmd == "weekly":
        if not args.no_download:
            download(cfg)
        close, volume, fx = load_cached(cfg)
        weekly.run(cfg, close, volume, fx, load_universe(cfg))
    elif args.cmd == "paper":
        if not args.no_download:
            download(cfg)
        close, volume, fx = load_cached(cfg)
        paper.run(cfg, close, volume, fx, load_universe(cfg), cfg["_root"] / args.spec)
    elif args.cmd == "t212":
        from . import t212
        client = t212.Client()
        spec = cfg["_root"] / args.spec
        universe = load_universe(cfg)
        close, volume, fx = load_cached(cfg)
        t212.sync(client, spec)
        if not args.retry_rejected:
            print(f"  prices up to {close.index.max().date()}")
            t212.plan_from_account(client, cfg, spec, close, volume, fx, universe)
        t212.place(client, spec, universe, execute=args.execute, retry_rejected=args.retry_rejected)
        t212.compare(spec, cfg, close, fx, universe)
