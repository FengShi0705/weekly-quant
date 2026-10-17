"""Approximate per-trade costs for Trading 212 and IBKR, in base currency."""
from .data import quote_currency


def trade_cost(value, shares, country, currency, side, cfg, usd_per_base=1.0):
    """value and the result are in base currency; value > 0. side is 'buy' or 'sell'."""
    c = cfg["costs"]
    base = cfg["account"]["base_currency"]
    broker = cfg["account"]["broker"]
    b = c[broker]
    ccy, _ = quote_currency(currency)

    cost = value * c["slippage_bps"] / 1e4
    if side == "buy":
        cost += value * c["buy_tax_bps"].get(country, 0) / 1e4
    if ccy != base:
        cost += value * b["fx_fee_bps"] / 1e4

    if broker == "ibkr":
        if country == "US":
            value_usd = value * usd_per_base
            comm_usd = min(max(abs(shares) * b["us_per_share"], b["us_min"]), value_usd * b["us_max_pct"])
            cost += comm_usd / usd_per_base
        else:
            cost += max(value * b["intl_commission_pct"], b["intl_min"])
    else:
        cost += max(value * b["commission_pct"], b["min_commission"])
    return cost
