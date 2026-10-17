"""Turn scores into a target portfolio and the trades needed to reach it.

The backtest and the live weekly run call exactly these functions, so the backtest
simulates the same rules you will trade.
"""
import math

import pandas as pd

from .costs import trade_cost


def regime_exposure(mkt_weekly, date, cfg):
    p = cfg["portfolio"]
    if not p["regime_filter"]:
        return 1.0
    hist = mkt_weekly.loc[:date]
    if len(hist) < 40:
        return 1.0
    return p["regime_exposure"] if hist.iloc[-1] < hist.iloc[-40:].mean() else 1.0


def _whole_units(meta, ticker, cfg):
    return not cfg["account"]["fractional_shares"] or int(meta.loc[ticker, "lot_size"]) > 1


def quantize(shares, lot, whole):
    """Round toward zero to a tradable quantity."""
    if whole:
        return math.trunc(shares / lot) * lot
    return math.trunc(shares * 1e4) / 1e4


def select_targets(scores, held, meta, price, equity, cfg, exposure=1.0):
    """scores: Series ticker -> score (higher is better). Returns dict ticker -> target weight."""
    p = cfg["portfolio"]
    n = p["n_positions"]
    weight = (1 - p["cash_buffer"]) * exposure / n
    pos_value = weight * equity
    ranked = scores.dropna().sort_values(ascending=False)
    rank = pd.Series(range(1, len(ranked) + 1), index=ranked.index)

    def buyable(t):
        if t not in price.index or not price[t] > 0:
            return False
        if not _whole_units(meta, t, cfg):
            return True
        return price[t] * int(meta.loc[t, "lot_size"]) <= pos_value

    selected, per_country = [], {}

    def add(t):
        c = meta.loc[t, "country"]
        if per_country.get(c, 0) >= p["max_per_country"]:
            return
        selected.append(t)
        per_country[c] = per_country.get(c, 0) + 1

    # Incumbents get a wider band (hold_rank) than newcomers (n_positions) to cut turnover.
    for t in sorted((t for t in held if t in rank.index and rank[t] <= p["hold_rank"]), key=rank.get):
        if len(selected) < n:
            add(t)
    for t in ranked.index:
        if len(selected) >= n:
            break
        if t not in selected and buyable(t):
            add(t)
    return {t: weight for t in selected}


def generate_orders(shares, targets, price, equity, meta, cfg):
    """shares: dict ticker -> current quantity. Returns a list of order dicts (sells first)."""
    p = cfg["portfolio"]
    orders = []
    for t in sorted(set(shares) | set(targets)):
        cur = shares.get(t, 0.0)
        px = price.get(t)
        if px is None or not px > 0:
            continue
        cur_val = cur * px
        if t not in targets:
            if cur > 0:
                orders.append({"ticker": t, "side": "sell", "shares": cur, "value": cur_val, "reason": "exit"})
            continue
        tgt_val = targets[t] * equity
        if cur > 0 and abs(cur_val - tgt_val) <= p["rebalance_drift"] * tgt_val:
            continue
        whole = _whole_units(meta, t, cfg)
        qty = quantize((tgt_val - cur_val) / px, int(meta.loc[t, "lot_size"]), whole)
        if abs(qty * px) < p["min_trade_value"] or qty == 0:
            continue
        side = "buy" if qty > 0 else "sell"
        reason = "enter" if cur == 0 else "resize"
        orders.append({"ticker": t, "side": side, "shares": abs(qty), "value": abs(qty * px), "reason": reason})
    return sorted(orders, key=lambda o: o["side"] != "sell")


def execute(orders, shares, cash, price, meta, cfg, usd_per_base=1.0):
    """Apply orders at `price`, charging costs. Buys are scaled down if cash runs short.

    Returns (shares, cash, total_cost, filled_orders).
    """
    shares = dict(shares)
    total_cost, filled = 0.0, []

    def cost_of(o):
        return trade_cost(o["value"], o["shares"], meta.loc[o["ticker"], "country"],
                          meta.loc[o["ticker"], "currency"], o["side"], cfg, usd_per_base)

    for o in (o for o in orders if o["side"] == "sell"):
        c = cost_of(o)
        cash += o["value"] - c
        total_cost += c
        left = shares.get(o["ticker"], 0.0) - o["shares"]
        if left <= 1e-9:
            shares.pop(o["ticker"], None)
        else:
            shares[o["ticker"]] = left
        filled.append({**o, "cost": c})

    buys = [o for o in orders if o["side"] == "buy"]
    need = sum(o["value"] + cost_of(o) for o in buys)
    scale = min(1.0, cash / need) if need > 0 else 1.0
    for o in buys:
        t = o["ticker"]
        if scale < 1.0:
            qty = quantize(o["shares"] * scale, int(meta.loc[t, "lot_size"]), _whole_units(meta, t, cfg))
            if qty <= 0:
                continue
            o = {**o, "shares": qty, "value": qty * price[t]}
        c = cost_of(o)
        if o["value"] + c > cash + 1e-9:
            continue
        cash -= o["value"] + c
        total_cost += c
        shares[t] = shares.get(t, 0.0) + o["shares"]
        filled.append({**o, "cost": c})
    return shares, cash, total_cost, filled
