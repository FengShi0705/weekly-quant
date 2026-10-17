import numpy as np
import pandas as pd
import pytest

from wq.backtest import etf_value, monthly_deposits, xirr
from wq.portfolio import generate_orders


def test_xirr_matches_simple_cases():
    d0, d1 = pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01")
    assert xirr([d0, d1], [-100, 110]) == pytest.approx(0.10, abs=1e-3)
    d2 = pd.Timestamp("2022-01-01")
    # 100 in, then 100 more after a year, worth 231 after two years -> 10%/yr on both deposits
    assert xirr([d0, d1, d2], [-100, -100, 231]) == pytest.approx(0.10, abs=2e-3)


def test_monthly_deposits_first_week_of_each_month():
    dates = pd.date_range("2024-01-05", periods=10, freq="W-FRI")
    dep = monthly_deposits(dates, 500)
    assert dep.sum() == 500 * 3
    assert list(dep[dep > 0].index.month) == [1, 2, 3]


def test_etf_value_uses_last_close_on_etf_holidays(cfg):
    cfg["account"]["base_currency"] = "GBP"
    days = pd.bdate_range("2024-01-01", periods=30)
    etf = pd.Series(np.linspace(100, 129, 30), index=days).drop(days[[5, 6, 12]])  # ETF closed those days
    dates = days[::5]
    cal = pd.DataFrame({"exec_date": dates}, index=dates)
    deposits = pd.Series(100.0, index=dates)
    v = etf_value(etf, cal, dates, cfg, "GBP", deposits=deposits)
    assert v.notna().all()
    # every deposit was invested: units only ever increase
    units = v / etf.reindex(etf.index.union(dates)).ffill().reindex(dates)
    assert (units.diff().dropna() > 0).all()


def test_idle_cash_tops_up_underweight_holdings(cfg):
    meta = pd.DataFrame({"country": ["US", "US"], "sector": ["Tech", "Health"], "currency": ["USD", "USD"],
                         "lot_size": [1, 1], "name": ["A", "B"]}, index=["AAA", "BBB"])
    cfg["portfolio"].update(rebalance_drift=0.30, max_idle_cash=0.05, min_trade_value=10)
    price = pd.Series({"AAA": 100.0, "BBB": 100.0})
    shares = {"AAA": 4.5, "BBB": 4.5}  # 900 invested
    targets = {"AAA": 0.49, "BBB": 0.49}
    # 100 cash on 1000 equity: each position is ~8% under target (inside the drift band)
    assert generate_orders(shares, targets, price, 1000, meta, cfg, cash=0) == []
    orders = generate_orders(shares, targets, price, 1000, meta, cfg, cash=100)
    assert {o["ticker"] for o in orders} == {"AAA", "BBB"} and all(o["side"] == "buy" for o in orders)
