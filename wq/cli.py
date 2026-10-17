import argparse
import json

import pandas as pd

from . import backtest, weekly
from .config import load_config
from .data import download, load_cached, load_universe

# Reference palette (light): categorical slots 1-3, benchmark recedes in neutral gray.
SERIES = {"score": ("ML + momentum blend", "#2a78d6"), "ml": ("ML only", "#eb6834"),
          "baseline": ("Momentum baseline", "#1baf7a")}
BENCH = ("Equal-weight universe", "#8a8984")
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"


def _plot(out, results, bench):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax, ax_dd) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1.3]}, facecolor=SURFACE)
    curves = {k: (1 + r[0]["ret"].fillna(0)).cumprod() for k, r in results.items()}
    curves["bench"] = (1 + bench.fillna(0)).cumprod()
    for k, eq in curves.items():
        label, color = SERIES.get(k, BENCH)
        style = "--" if k == "bench" else "-"
        ax.plot(eq.index, eq.values, style, color=color, lw=2, label=label)
        ax.annotate(f"{label}  {eq.iloc[-1]:.2f}x", (eq.index[-1], eq.iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK_2)
    lo, hi = min(c.min() for c in curves.values()), max(c.max() for c in curves.values())
    if hi / lo > 3:  # log scale only when compounding makes linear unreadable
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 3, 5)))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda y, _: f"{y:g}x"))
    ax.set_title("Growth of 1 (after costs, base currency)", loc="left", color=INK, fontsize=12)
    dd = curves["score"] / curves["score"].cummax() - 1
    ax_dd.fill_between(dd.index, dd.values, 0, color=SERIES["score"][1], alpha=0.25, lw=0)
    ax_dd.plot(dd.index, dd.values, color=SERIES["score"][1], lw=1.5)
    ax_dd.set_title("Drawdown — blend", loc="left", color=INK, fontsize=10)
    ax_dd.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    for a in (ax, ax_dd):
        a.set_facecolor(SURFACE)
        a.grid(True, color=GRID, lw=0.8)
        a.tick_params(colors=INK_2, labelsize=9)
        for s in a.spines.values():
            s.set_visible(False)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_2, loc="upper left")
    fig.subplots_adjust(right=0.80, hspace=0.25)
    fig.savefig(out / "equity.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)


def _fmt(summary):
    keys = ["cagr", "ann_vol", "sharpe", "max_drawdown", "avg_weekly_turnover", "costs_pct_of_capital_per_year"]
    rows = {k: {m: v.get(m) for m in keys} for k, v in summary.items() if k != "ic"}
    return pd.DataFrame(rows).T


def cmd_backtest(cfg):
    close, volume, fx = load_cached(cfg)
    universe = load_universe(cfg)
    res = backtest.run(cfg, close, volume, fx, universe)
    out = cfg["paths"]["reports"] / "backtest"
    out.mkdir(parents=True, exist_ok=True)
    for k, (r, trades) in res["results"].items():
        r.to_csv(out / f"weekly_{k}.csv")
        trades.to_csv(out / f"trades_{k}.csv", index=False)
    res["ic"].to_csv(out / "ic_weekly.csv")
    (out / "summary.json").write_text(json.dumps(res["summary"], indent=2, default=float))
    _plot(out, res["results"], res["benchmark"])
    table = _fmt(res["summary"])
    print("\n" + table.to_string(float_format=lambda x: f"{x:.3f}"))
    print("\nInformation coefficient (weekly Spearman, score vs next-week return):")
    print(pd.DataFrame(res["summary"]["ic"]).T.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nWritten to {out}/")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="wq", description="Weekly global equity strategy")
    ap.add_argument("--config", default="config.yaml")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", help="download prices, volumes and FX into the cache")
    sub.add_parser("backtest", help="run the walk-forward backtest on cached data")
    w = sub.add_parser("weekly", help="score the latest week and write this week's order sheet")
    w.add_argument("--no-download", action="store_true", help="use cached data instead of refreshing")
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
