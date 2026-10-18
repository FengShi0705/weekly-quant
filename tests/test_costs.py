import numpy as np
import pandas as pd
import pytest

from wq import paper
from wq.backtest import prepare, simulate
from wq.costs import dividend_tax, dividend_tax_per_share, trade_cost
from wq.data import total_return
from wq.model import smooth_scores, walk_forward


def test_buy_taxes_follow_the_issuer(cfg):
    bps = lambda t, country, ccy, side="buy": trade_cost(10_000, 10, country, ccy, side, cfg, ticker=t)
    assert bps("BNP.PA", "FR", "EUR") == pytest.approx(10 + 40 + 15)        # slippage + French FTT + FX fee
    assert bps("AIR.PA", "FR", "EUR") == pytest.approx(10 + 15)             # Airbus SE is Dutch: no FTT
    assert bps("ENEL.MI", "IT", "EUR") == pytest.approx(10 + 20 + 15)
    assert bps("BARC.L", "UK", "GBp") == pytest.approx(10 + 50)             # GBP account: no FX fee
    assert bps("EXPN.L", "UK", "GBp") == pytest.approx(10)                  # Jersey company: no SDRT
    assert bps("BARC.L", "UK", "GBp", "sell") == pytest.approx(10)          # stamp duty is on buys only
    assert bps("AAPL", "US", "USD", "sell") == pytest.approx(10 + 15 + 0.21)  # SEC fee on US sells
    assert trade_cost(10_000, 10, "FR", "EUR", "buy", cfg) == pytest.approx(10 + 40 + 15)  # no ticker


def test_total_return_fixes_london_dividends_applied_100x_too_small():
    idx = pd.bdate_range("2024-01-01", periods=6)
    raw = pd.DataFrame({"BARC.L": [300.0, 303, 297, 300, 306, 303], "AAPL": [100.0, 101, 99, 100, 102, 101]},
                       index=idx)
    # Yahoo-style adjusted closes: earlier closes are scaled by (1 - dividend / previous close). A 6p
    # dividend on BARC.L going ex on day 4 is applied as 0.06p; a $1 AAPL dividend on day 5 correctly.
    adj = raw.copy()
    adj.iloc[:3, 0] *= 1 - 0.06 / 297
    adj.iloc[:4, 1] *= 1 - 1.0 / 100
    tr, y = total_return(raw, adj, pence=["BARC.L"])
    assert y.loc[idx[3], "BARC.L"] == pytest.approx(6 / 297, rel=1e-6)
    assert y.loc[idx[4], "AAPL"] == pytest.approx(0.01, rel=1e-6)
    assert (y.drop([idx[3]])["BARC.L"] == 0).all() and (y.drop([idx[4]])["AAPL"] == 0).all()
    assert tr.iloc[-1].tolist() == raw.iloc[-1].tolist()                    # equal to the raw close today
    r = tr["BARC.L"].pct_change()
    assert r.iloc[3] == pytest.approx(300 / (297 - 6) - 1)                   # dividend included, as Yahoo does
    assert tr["AAPL"].pct_change().iloc[1:].tolist() == pytest.approx(adj["AAPL"].pct_change().iloc[1:].tolist())


def test_dividend_tax_charged_on_holdings(cfg):
    idx = pd.bdate_range("2024-01-01", periods=5)
    px = pd.DataFrame({"AAPL": 100.0, "BARC.L": 3.0, "SAP.DE": 200.0}, index=idx)
    div = pd.DataFrame(0.0, index=idx, columns=px.columns)
    div.loc[idx[2]] = 0.01                                                 # 1% dividends, ex on day 3
    universe = pd.DataFrame({"country": ["US", "UK", "DE"]}, index=px.columns)
    cum = dividend_tax_per_share(px, div, universe, cfg)
    shares = {"AAPL": 10, "BARC.L": 100, "SAP.DE": 2}
    assert dividend_tax(shares, cum, idx[0], idx[4]) == pytest.approx(10 * 1 * 0.15 + 0 + 2 * 2 * 0.26375)
    assert dividend_tax(shares, cum, idx[2], idx[4]) == 0                   # bought on the ex-date: no dividend
    assert dividend_tax(shares, None, idx[0], idx[4]) == 0


def test_backtest_charges_dividend_tax(cfg, signal_market):
    close, volume, fx, universe = signal_market
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    dates = [d for d in cal.index if d >= pd.Timestamp("2019-06-01") and pd.notna(cal.loc[d, "exec_date"])]
    scores = smooth_scores(walk_forward(panel, cfg, dates, verbose=False), cfg["model"]["score_smoothing_weeks"])
    div = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    div.iloc[::63] = 0.01                                                  # a 1% dividend every quarter
    cum = dividend_tax_per_share(px, div, universe, cfg)
    plain, _ = simulate(scores, panel, cal, px, universe, fx, cfg)
    taxed, _ = simulate(scores, panel, cal, px, universe, fx, cfg, div_tax=cum)
    assert plain["dividend_tax"].sum() == 0 and taxed["dividend_tax"].sum() > 0
    assert taxed["equity"].iloc[-1] < plain["equity"].iloc[-1]


def test_paper_ledger_deducts_dividend_tax(cfg, signal_market, tmp_path):
    close, volume, fx, universe = signal_market
    cache = tmp_path / "cache"
    cache.mkdir()
    cfg["data"]["cache_dir"] = cache
    div = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    div.loc["2019-12-18"] = 0.01                                           # ex-date in week 2, after the fill
    div.to_parquet(cache / "div_yield.parquet")
    spec = tmp_path / "paper" / "strategies.yaml"
    spec.parent.mkdir()
    spec.write_text("start_capital: 10000\nstrategies:\n  main: {}\n")

    week1 = close.loc[:"2019-12-13"]
    paper.run(cfg, week1, volume.loc[week1.index], fx.loc[week1.index], universe, spec)
    week2 = close.loc[:"2019-12-20"]
    cfgs = paper.run(cfg, week2, volume.loc[week2.index], fx.loc[week2.index], universe, spec)
    main = cfgs["main"]["paper_dir"]
    nav = pd.read_csv(main / "nav.csv")
    assert nav["dividend_tax"].tolist()[0] == 0

    _, _, px = prepare(cfg, week2, volume.loc[week2.index], fx.loc[week2.index], universe)
    held = pd.read_csv(main / "holdings.csv").set_index("ticker")["shares"]
    rates = {"US": 0.15, "DE": 0.26375, "UK": 0.0}
    expected = sum(q * px.ffill().loc["2019-12-17", t] * 0.01 * rates[universe.loc[t, "country"]]
                   for t, q in held.drop("CASH").items())
    assert expected > 0 and nav["dividend_tax"].iloc[-1] == pytest.approx(expected, abs=0.02)
    ledger = pd.read_csv(main / "ledger.csv")
    base = cfg["account"]["base_currency"]
    spent = ledger[f"value_{base}"].sum() + ledger[f"cost_{base}"].sum()
    assert held["CASH"] == pytest.approx(10000 - spent - expected, abs=0.05)
    assert np.isfinite(nav["equity"]).all()
