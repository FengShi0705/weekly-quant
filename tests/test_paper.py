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


def test_transformer_strategy_and_failure_isolation(cfg, signal_market, tmp_path):
    pytest.importorskip("torch")
    close, volume, fx, universe = signal_market
    cfg["data"]["cache_dir"] = tmp_path / "no_cache"
    cfg["paths"]["tx_models"] = tmp_path / "tx_models"
    spec = tmp_path / "paper" / "strategies.yaml"
    spec.parent.mkdir()
    spec.write_text("start_capital: 10000\nstrategies:\n  main: {}\n"
                    "  tx:\n    model:\n      type: transformer\n      transformer: {d_model: 16, heads: 2, blocks: 1,"
                    " max_epochs: 2, patience: 1, refit_every_weeks: 26, seeds: 1, workers: 1,"
                    " refit_anchor: '2019-06-07'}\n"
                    "  broken:\n    model: {type: transformer, transformer: {refit_anchor: '1999-01-01'}}\n")
    week1 = close.loc[:"2019-12-13"]
    with pytest.raises(RuntimeError, match="broken"):
        paper.run(cfg, week1, volume.loc[week1.index], fx.loc[week1.index], universe, spec)
    for name in ("main", "tx"):                                  # the others still completed
        pending = pd.read_csv(spec.parent / name / "pending_orders.csv")
        assert len(pending) == 15 and set(pending["side"]) == {"buy"}
    assert "Failed this run" in (spec.parent / "summary.md").read_text()
    assert list((tmp_path / "tx_models").glob("*/refit*_seed0.pt"))
