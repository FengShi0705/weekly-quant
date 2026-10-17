import pandas as pd
import pytest

from wq import paper
from wq.backtest import prepare


def test_two_paper_weeks(cfg, signal_market, tmp_path):
    close, volume, fx, universe = signal_market
    cfg["data"]["cache_dir"] = tmp_path / "no_cache"           # no benchmark ETFs in this test
    spec = tmp_path / "paper" / "strategies.yaml"
    spec.parent.mkdir()
    spec.write_text("start_capital: 10000\nstrategies:\n  main: {}\n"
                    "  small:\n    portfolio: {n_positions: 5}\n")

    week1 = close.loc[:"2019-12-13"]                            # Friday signal
    cfgs = paper.run(cfg, week1, volume.loc[week1.index], fx.loc[week1.index], universe, spec)
    main = cfgs["main"]["paper_dir"]
    pending = pd.read_csv(main / "pending_orders.csv")
    assert len(pending) == 15 and set(pending["side"]) == {"buy"}
    assert not (main / "ledger.csv").exists()

    week2 = close.loc[:"2019-12-20"]
    paper.run(cfg, week2, volume.loc[week2.index], fx.loc[week2.index], universe, spec)
    ledger = pd.read_csv(main / "ledger.csv")
    assert set(ledger["exec_date"]) == {"2019-12-16"}           # filled at the Monday close
    _, _, px = prepare(cfg, week2, volume.loc[week2.index], fx.loc[week2.index], universe)
    base = cfg["account"]["base_currency"]
    for _, r in ledger.iterrows():
        assert r[f"price_{base}"] == pytest.approx(px.loc["2019-12-16", r["ticker"]], rel=1e-6)

    holdings = pd.read_csv(main / "holdings.csv").set_index("ticker")["shares"]
    assert holdings["CASH"] >= 0 and len(holdings) == 16
    nav = pd.read_csv(main / "nav.csv")
    assert len(nav) == 2 and nav["equity"].iloc[0] == 10000
    spent = ledger[f"value_{base}"].sum() + ledger[f"cost_{base}"].sum()
    assert holdings["CASH"] == pytest.approx(10000 - spent, abs=0.05)
    assert len(pd.read_csv(cfgs["small"]["paper_dir"] / "ledger.csv")) == 5
    assert "main" in (spec.parent / "summary.md").read_text()
