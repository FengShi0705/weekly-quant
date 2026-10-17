import pandas as pd
import pytest

from wq.costs import trade_cost
from wq.portfolio import execute, generate_orders, quantize, select_targets


@pytest.fixture
def meta():
    return pd.DataFrame({
        "country": ["US", "US", "UK", "JP", "DE"],
        "currency": ["USD", "USD", "GBp", "JPY", "EUR"],
        "lot_size": [1, 1, 1, 100, 1],
        "name": list("ABCDE"),
    }, index=["AAA", "BBB", "CCC.L", "7203.T", "DDD.DE"])


def test_t212_cost_on_uk_buy(cfg):
    cfg["account"].update(broker="t212", base_currency="USD")
    # 10 bps slippage + 50 bps UK stamp duty + 15 bps FX fee
    assert trade_cost(1000, 5, "UK", "GBp", "buy", cfg) == pytest.approx(7.5)
    assert trade_cost(1000, 5, "UK", "GBp", "sell", cfg) == pytest.approx(2.5)
    assert trade_cost(1000, 5, "US", "USD", "buy", cfg) == pytest.approx(1.0)


def test_ibkr_minimums(cfg):
    cfg["account"].update(broker="ibkr", base_currency="USD")
    assert trade_cost(1000, 10, "US", "USD", "buy", cfg) == pytest.approx(1.0 + 0.35)
    assert trade_cost(500, 3, "DE", "EUR", "sell", cfg) == pytest.approx(0.5 + 1.5 + 0.1)


def test_quantize():
    assert quantize(7.9, 1, True) == 7
    assert quantize(-7.9, 1, True) == -7
    assert quantize(250, 100, True) == 200
    assert quantize(1.23456, 1, False) == pytest.approx(1.2345)


def test_select_respects_lots_country_cap_and_hold_band(cfg, meta):
    cfg["account"]["fractional_shares"] = True
    cfg["portfolio"].update(n_positions=3, hold_rank=4, max_per_country=1)
    price = pd.Series({"AAA": 100, "BBB": 50, "CCC.L": 10, "7203.T": 3000 / 150, "DDD.DE": 80})
    scores = pd.Series({"7203.T": 0.9, "AAA": 0.8, "BBB": 0.7, "CCC.L": 0.6, "DDD.DE": 0.1})
    # 7203.T needs 100 shares x 20 = 2000 > 1000 * 0.98 / 3, so it is skipped; BBB loses to AAA on the US cap.
    t = select_targets(scores, set(), meta, price, 1000, cfg)
    assert set(t) == {"AAA", "CCC.L", "DDD.DE"}
    # A held stock ranked 4th (inside hold_rank) is kept ahead of a better-ranked newcomer.
    t = select_targets(scores, {"BBB"}, meta, price, 1000, cfg)
    assert "BBB" in t and "AAA" not in t


def test_orders_and_execution_never_overdraw(cfg, meta):
    cfg["account"].update(broker="ibkr", fractional_shares=False)
    cfg["portfolio"].update(min_trade_value=20, rebalance_drift=0.3)
    price = pd.Series({"AAA": 100.0, "BBB": 50.0, "CCC.L": 10.0, "7203.T": 20.0, "DDD.DE": 80.0})
    shares = {"AAA": 5, "DDD.DE": 2}
    cash = 100.0
    equity = cash + 5 * 100 + 2 * 80
    targets = {"BBB": 0.49, "CCC.L": 0.49}
    orders = generate_orders(shares, targets, price, equity, meta, cfg)
    assert [o["side"] for o in orders][:2] == ["sell", "sell"]
    new_shares, new_cash, cost, filled = execute(orders, shares, cash, price, meta, cfg)
    assert new_cash >= 0
    assert "AAA" not in new_shares and "DDD.DE" not in new_shares
    assert all(float(q).is_integer() for q in new_shares.values())
    total = new_cash + sum(q * price[t] for t, q in new_shares.items())
    assert total == pytest.approx(equity - cost)
