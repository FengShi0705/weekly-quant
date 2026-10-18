"""Approximate per-trade costs for Trading 212 and IBKR, and the dividend tax lost while holding."""
from .data import quote_currency


def buy_tax_bps(ticker, country, cfg):
    c = cfg["costs"]
    overrides = c.get("buy_tax_overrides") or {}
    return overrides[ticker] if ticker in overrides else c["buy_tax_bps"].get(country, 0)


def trade_cost(value, shares, country, currency, side, cfg, usd_per_base=1.0, ticker=None):
    """value and the result are in base currency; value > 0. side is 'buy' or 'sell'."""
    c = cfg["costs"]
    base = cfg["account"]["base_currency"]
    broker = cfg["account"]["broker"]
    b = c[broker]
    ccy, _ = quote_currency(currency)

    cost = value * c["slippage_bps"] / 1e4
    if side == "buy":
        cost += value * buy_tax_bps(ticker, country, cfg) / 1e4
    else:
        cost += value * (c.get("sell_tax_bps") or {}).get(country, 0) / 1e4
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


def dividend_tax_per_share(px_base, div_yield, universe, cfg):
    """Cumulative dividend tax withheld per share held, in base currency, by day.

    div_yield[d] is the dividend going ex on day d as a fraction of the previous close (see
    data.total_return). Prices are dividend-adjusted, so returns already include the gross dividend;
    this is the part withheld at source. The tax on a holding of q shares between days a and b is
    q * (result[b] - result[a]).
    """
    rates = universe["country"].map(cfg["costs"].get("dividend_withholding") or {}).fillna(0.0)
    d = div_yield.reindex(index=px_base.index, columns=px_base.columns).fillna(0.0)
    per_share = px_base.ffill().shift(1) * d * rates.reindex(px_base.columns).fillna(0.0)
    return per_share.fillna(0.0).cumsum()


def dividend_tax(shares, cum_tax, start, end):
    """Tax withheld on `shares` (ticker -> quantity) for dividends going ex after `start`, up to `end`."""
    if cum_tax is None or start is None or not shares or end <= start:
        return 0.0
    a, b = cum_tax.loc[:start].iloc[-1], cum_tax.loc[:end].iloc[-1]
    return float(sum(q * (b[t] - a[t]) for t, q in shares.items() if t in cum_tax.columns))
