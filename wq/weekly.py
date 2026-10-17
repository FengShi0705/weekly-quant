"""Live weekly run: score the latest week and write an order sheet for manual execution."""
import hashlib
import json
from datetime import date

import pandas as pd

from .backtest import prepare
from .costs import trade_cost
from .data import usd_per_base
from .features import market_index
from .model import feature_importance, smooth_scores, walk_forward
from .portfolio import generate_orders, regime_exposure, select_targets


def read_holdings(path, capital):
    """CSV with columns ticker,shares. A row 'CASH,<amount>' holds cash in base currency."""
    if not path.exists():
        print(f"No holdings file at {path}; assuming an all-cash account of {capital:,.0f}.")
        return {}, float(capital)
    df = pd.read_csv(path)
    df["ticker"] = df["ticker"].astype(str).str.strip()
    cash_rows = df["ticker"].str.upper() == "CASH"
    cash = float(df.loc[cash_rows, "shares"].sum())
    shares = {t: float(q) for t, q in zip(df.loc[~cash_rows, "ticker"], df.loc[~cash_rows, "shares"]) if q}
    return shares, cash


def model_fingerprint(cfg):
    """Short hash of the model settings; saved scores are only reused under the same settings."""
    return hashlib.sha1(json.dumps(cfg["model"], sort_keys=True, default=str).encode()).hexdigest()[:12]


def recent_raw_scores(panel, cfg, dates):
    """Unsmoothed scores for `dates` (oldest first, newest last).

    Earlier weeks come from the score history, so the 4-week average uses the scores you actually
    traded on. Missing weeks, and always the newest week, are scored by walk_forward exactly as the
    backtest scores them. Returns (scores, model fitted for the newest week, weeks reused).
    """
    path, fp = cfg["paths"]["score_history"], model_fingerprint(cfg)
    history = pd.read_csv(path, parse_dates=["date"]) if path.exists() else pd.DataFrame(
        columns=["date", "ticker", "ml", "baseline", "score", "model"])
    reuse = history[(history["model"] == fp) & history["date"].isin(dates[:-1])]
    reused = sorted(reuse["date"].unique())
    todo = [d for d in dates if d not in set(reused)]
    new, model = walk_forward(panel, cfg, todo, verbose=True, return_model=True)

    keep = history[~history["date"].isin(new.index.get_level_values("date").unique())]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([keep, new.reset_index().assign(model=fp)]).sort_values(["date", "ticker"]).to_csv(path, index=False)

    if not reused:
        return new, model, reused
    saved = reuse.set_index(["date", "ticker"])[["ml", "baseline", "score"]].astype(float)
    return pd.concat([saved, new]).sort_index(), model, reused


def run(cfg, close_local, volume, fx_usd, universe):
    base = cfg["account"]["base_currency"]
    panel, cal, px = prepare(cfg, close_local, volume, fx_usd, universe)
    dates = panel.index.get_level_values("date").unique().sort_values()
    T = dates[-1]
    k = cfg["model"]["score_smoothing_weeks"]
    print(f"Scoring signal date {T.date()} (averaged over the last {k} weeks) ...")
    raw, model, reused = recent_raw_scores(panel, cfg, list(dates[-k:]))
    if reused:
        print(f"  reused saved scores for {', '.join(str(d.date()) for d in reused)}")
    scores = smooth_scores(raw, k).xs(T, level="date")

    shares, cash = read_holdings(cfg["paths"]["holdings"], cfg["account"]["capital"])
    unmanaged = {t: q for t, q in shares.items() if t not in universe.index}
    shares = {t: q for t, q in shares.items() if t in universe.index}
    price = px.ffill().loc[T]
    equity = cash + sum(q * price[t] for t, q in shares.items())

    mkt_w = market_index(px).reindex(cal.index, method="ffill")
    expo = regime_exposure(mkt_w, T, cfg)
    vol = panel.xs(T, level="date")["raw_vol_60"]
    targets = select_targets(scores["score"], set(shares), universe, price, equity, cfg, expo, vol)
    orders = generate_orders(shares, targets, price, equity, universe, cfg, cash)

    local = close_local.ffill().loc[:T].iloc[-1]
    upb = usd_per_base(fx_usd, base, T)
    rows = []
    for o in orders:
        t = o["ticker"]
        ccy = universe.loc[t, "currency"]
        rows.append({
            "side": o["side"].upper(), "ticker": t, "name": universe.loc[t, "name"],
            "country": universe.loc[t, "country"], "shares": round(o["shares"], 4),
            "ref_price_local": round(float(local[t]), 4), "quote_ccy": ccy,
            "est_value_" + base: round(o["value"], 2),
            "est_cost_" + base: round(trade_cost(o["value"], o["shares"], universe.loc[t, "country"], ccy,
                                                 o["side"], cfg, upb), 2),
            "reason": o["reason"],
        })
    order_df = pd.DataFrame(rows)

    rank = scores["score"].rank(ascending=False).astype(int)
    target_df = pd.DataFrame([{
        "rank": int(rank[t]), "ticker": t, "name": universe.loc[t, "name"], "country": universe.loc[t, "country"],
        "sector": universe.loc[t, "sector"], "score": round(float(scores.loc[t, "score"]), 3), "target_weight": round(w, 4),
        "target_value_" + base: round(w * equity, 2), "held": t in shares,
    } for t, w in targets.items()]).sort_values("rank")

    out = cfg["paths"]["reports"] / str(date.today())
    out.mkdir(parents=True, exist_ok=True)
    order_df.to_csv(out / "orders.csv", index=False)
    target_df.to_csv(out / "target_portfolio.csv", index=False)
    scores.sort_values("score", ascending=False).to_csv(out / "all_scores.csv")
    importance = feature_importance(model) if model is not None else pd.Series(dtype=float)
    (out / "report.md").write_text(_report(T, base, equity, cash, expo, target_df, order_df, unmanaged,
                                            importance, cfg))
    print(f"\nEquity {equity:,.2f} {base} | exposure {expo:.0%} | {len(order_df)} orders")
    print(order_df.to_string(index=False) if len(order_df) else "No trades needed this week.")
    print(f"\nWritten to {out}/")
    return out


def _report(T, base, equity, cash, expo, targets, orders, unmanaged, importance, cfg):
    lines = [
        f"# Weekly rebalance — signal date {T.date()}",
        "",
        f"- Broker: **{cfg['account']['broker']}**, base currency **{base}**",
        f"- Account equity (managed): **{equity:,.2f} {base}**, cash before trades {cash:,.2f}",
        f"- Market regime exposure: **{expo:.0%}**"
        + (" (universe below its 40-week average, so exposure is reduced)" if expo < 1 else ""),
        "",
        "## Orders to place",
        "",
        "Place sells first, then buys. Prices are the last close and only a guide: use limit orders "
        "a little through the current quote. London prices are in pence (GBp).",
        "",
        orders.to_markdown(index=False) if len(orders) else "_No trades needed this week._",
        "",
        "## Target portfolio",
        "",
        "Sector mix: " + ", ".join(f"{k} {v}" for k, v in targets["sector"].value_counts().items())
        + f" (cap {cfg['portfolio']['max_per_sector']} per sector).",
        "",
        targets.to_markdown(index=False),
        "",
        "## What the model is leaning on (feature importance, gain)",
        "",
        importance.round(1).to_frame("gain").to_markdown(),
        "",
        "## After you trade",
        "",
        f"Update `{cfg['paths']['holdings'].name}` with your actual filled share quantities and the cash "
        "balance from your broker, so next week's run starts from what you really hold.",
    ]
    if unmanaged:
        lines += ["", "## Holdings ignored (not in the strategy universe)", "",
                  ", ".join(f"{t} ({q})" for t, q in unmanaged.items())]
    return "\n".join(lines) + "\n"
