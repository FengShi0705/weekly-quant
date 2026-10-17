import numpy as np
import pytest
import pandas as pd

from wq import backtest
from wq.backtest import prepare
from wq.features import FEATURES
from wq.model import information_coefficients, train_slice, walk_forward


def test_features_ignore_the_future(cfg, noise_market):
    close, volume, fx, universe = noise_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    cut = cal.index[300]

    shocked = close.copy()
    after = shocked.index > cut
    shocked.loc[after] *= np.random.default_rng(9).uniform(0.5, 2.0, size=(after.sum(), close.shape[1]))
    panel2, _, _ = prepare(cfg, shocked, volume, fx, universe)

    a = panel.loc[:cut, FEATURES]
    b = panel2.loc[:cut, FEATURES]
    pd.testing.assert_frame_equal(a, b)


def test_training_labels_are_realised_before_signal(cfg, noise_market):
    close, volume, fx, universe = noise_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    h = cfg["model"]["label_horizon_weeks"]
    signal_dates = cal.index
    for i_T in [200, 260, 400]:
        train = train_slice(panel, i_T, cfg)
        last_label_week = train["week"].max() + h
        label_known_on = cal["exec_date"].iloc[last_label_week]
        assert label_known_on <= signal_dates[i_T]


def test_no_skill_on_pure_noise(cfg, noise_market):
    """If anything leaked future returns into the model, it would 'predict' noise."""
    close, volume, fx, universe = noise_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    dates = [d for d in cal.index if d >= pd.Timestamp(cfg["backtest"]["start"])][:-1]
    ic = information_coefficients(walk_forward(panel, cfg, dates, verbose=False), panel)
    for col in ["ml", "baseline", "score"]:
        t = ic[col].mean() / ic[col].std() * np.sqrt(ic[col].count())
        assert abs(ic[col].mean()) < 0.03 and abs(t) < 3, (col, ic[col].mean(), t)


def test_finds_planted_momentum(cfg, signal_market):
    close, volume, fx, universe = signal_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    dates = [d for d in cal.index if d >= pd.Timestamp(cfg["backtest"]["start"])][:-1]
    ic = information_coefficients(walk_forward(panel, cfg, dates, verbose=False), panel)
    assert ic["baseline"].mean() > 0.05
    assert ic["ml"].mean() > 0.05


def test_backtest_runs_end_to_end(cfg, signal_market):
    close, volume, fx, universe = signal_market
    res = backtest.run(cfg, close, volume, fx, universe, verbose=False)
    n = cfg["portfolio"]["n_positions"]
    for v, (weekly, trades) in res["results"].items():
        assert (weekly["equity"] > 0).all()
        assert (weekly["cash_after"] >= -1e-6).all()
        assert (weekly["positions"] <= n).all()
        assert len(trades) > 0
    assert res["summary"]["baseline"]["cagr"] > res["summary"]["benchmark_equal_weight"]["cagr"]


def test_weekly_run_writes_order_sheet(cfg, signal_market, tmp_path):
    from wq import weekly

    close, volume, fx, universe = signal_market
    held = universe.index[0]
    (tmp_path / "holdings.csv").write_text(f"ticker,shares\n{held},10\nNOT_IN_UNIVERSE,3\nCASH,8000\n")
    cfg["paths"].update(reports=tmp_path / "reports", holdings=tmp_path / "holdings.csv")
    out = weekly.run(cfg, close, volume, fx, universe)
    orders = pd.read_csv(out / "orders.csv")
    targets = pd.read_csv(out / "target_portfolio.csv")
    assert len(targets) == cfg["portfolio"]["n_positions"]
    assert set(orders["side"]) <= {"BUY", "SELL"}
    assert "NOT_IN_UNIVERSE" in (out / "report.md").read_text()


def test_score_smoothing_uses_only_past_weeks():
    from wq.model import smooth_scores

    idx = pd.MultiIndex.from_product([pd.date_range("2020-01-03", periods=6, freq="W-FRI"), ["A", "B"]],
                                     names=["date", "ticker"])
    s = pd.DataFrame({"score": np.arange(12, dtype=float)}, index=idx)
    out = smooth_scores(s, 3)
    a = s.xs("A", level="ticker")["score"].to_numpy()
    assert out.xs("A", level="ticker")["score"].iloc[0] == a[0]
    assert out.xs("A", level="ticker")["score"].iloc[4] == pytest.approx(a[2:5].mean())
    future_changed = s.copy()
    future_changed.iloc[-2:] = 999
    pd.testing.assert_frame_equal(smooth_scores(future_changed, 3).iloc[:-2], out.iloc[:-2])


def test_seed_ensemble_averages_member_predictions(cfg, signal_market):
    from wq.model import fit, predict

    close, volume, fx, universe = signal_market
    panel, _, _ = prepare(cfg, close, volume, fx, universe)
    train = panel[panel["label"].notna()].iloc[:5000]
    cfg["model"]["n_seeds"] = 3
    models = fit(train, cfg)
    assert len(models) == 3
    X = panel.iloc[5000:5100]
    members = np.array([m.predict(X[FEATURES]) for m in models])
    assert not np.allclose(members[0], members[1])
    np.testing.assert_allclose(predict(models, X), members.mean(axis=0))
