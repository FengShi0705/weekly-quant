import numpy as np
import pytest
import pandas as pd

from wq import backtest
from wq.backtest import prepare
from wq.features import EXTRA_FEATURES, FEATURES
from wq.model import information_coefficients, train_slice, walk_forward


def test_features_ignore_the_future(cfg, noise_market):
    close, volume, fx, universe = noise_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    cut = cal.index[300]

    shocked = close.copy()
    after = shocked.index > cut
    shocked.loc[after] *= np.random.default_rng(9).uniform(0.5, 2.0, size=(after.sum(), close.shape[1]))
    panel2, _, _ = prepare(cfg, shocked, volume, fx, universe)

    cols = FEATURES + EXTRA_FEATURES + ["raw_vol_60"]
    a = panel.loc[:cut, cols]
    b = panel2.loc[:cut, cols]
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


def test_ridge_and_extra_features_run(cfg, signal_market):
    from wq.model import fit, predict

    close, volume, fx, universe = signal_market
    panel, _, _ = prepare(cfg, close, volume, fx, universe)
    cfg["model"].update(type="ridge", extra_features=EXTRA_FEATURES)
    train = panel[panel["label"].notna()]
    (model,) = fit(train, cfg)
    assert model.feature_name() == FEATURES + EXTRA_FEATURES
    pred = predict([model], panel.iloc[:50])
    assert np.isfinite(pred).all()


def test_live_scores_match_backtest(cfg, signal_market):
    """The live run's averaged score for the newest week equals the backtest's for that week."""
    from wq.model import smooth_scores
    from wq.weekly import recent_raw_scores

    close, volume, fx, universe = signal_market
    cfg["model"]["retrain_every_weeks"] = 1
    panel, _, _ = prepare(cfg, close, volume, fx, universe)
    dates = list(panel.index.get_level_values("date").unique().sort_values())
    k = cfg["model"]["score_smoothing_weeks"]
    backtest_view = smooth_scores(walk_forward(panel, cfg, dates[-10:], verbose=False), k)
    raw, _, reused = recent_raw_scores(panel, cfg, dates[-k:])
    live_view = smooth_scores(raw, k)
    assert reused == []
    pd.testing.assert_series_equal(live_view.xs(dates[-1], level="date")["score"],
                                   backtest_view.xs(dates[-1], level="date")["score"])


def test_score_history_is_reused_only_for_same_model_settings(cfg, signal_market):
    from wq.weekly import recent_raw_scores

    close, volume, fx, universe = signal_market
    cfg["model"]["retrain_every_weeks"] = 1
    panel, _, _ = prepare(cfg, close, volume, fx, universe)
    dates = list(panel.index.get_level_values("date").unique().sort_values())
    first, _, _ = recent_raw_scores(panel, cfg, dates[-5:-1])          # last weekend's run
    second, _, reused = recent_raw_scores(panel, cfg, dates[-4:])      # this weekend's run
    assert reused == dates[-4:-1]                                       # three earlier weeks came from history
    pd.testing.assert_frame_equal(second.loc[dates[-4]:dates[-2]], first.loc[dates[-4]:dates[-2]])
    cfg["model"]["ml_weight"] = 0.5
    _, _, reused = recent_raw_scores(panel, cfg, dates[-4:])
    assert reused == []                                                  # settings changed: rescore everything


def test_newest_week_is_reused_only_within_the_same_day(cfg, signal_market, monkeypatch):
    import datetime as dt
    from wq import weekly

    close, volume, fx, universe = signal_market
    cfg["model"]["retrain_every_weeks"] = 1
    panel, _, _ = prepare(cfg, close, volume, fx, universe)
    dates = list(panel.index.get_level_values("date").unique().sort_values())[-4:]
    first, _, _ = weekly.recent_raw_scores(panel, cfg, dates)
    again, model, reused = weekly.recent_raw_scores(panel, cfg, dates)       # same day: nothing retrained
    assert reused == dates and model is None
    pd.testing.assert_frame_equal(again, first, check_like=True)

    class Tomorrow(dt.date):
        @classmethod
        def today(cls):
            return dt.date(2099, 1, 1)
    monkeypatch.setattr(weekly, "date", Tomorrow)
    _, model, reused = weekly.recent_raw_scores(panel, cfg, dates)             # another day: newest rescored
    assert reused == dates[:-1] and model is not None


def test_lightgbm_with_country_and_sector(cfg, signal_market):
    close, volume, fx, universe = signal_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    assert set(panel["country_id"].unique()) == {0, 1, 2} and panel["sector_id"].max() == 5
    cfg["model"]["categorical"] = True
    dates = [d for d in cal.index if d >= pd.Timestamp("2018-01-01")][:30]
    scores, model = walk_forward(panel, cfg, dates, verbose=False, return_model=True)
    assert {"country_id", "sector_id"} <= set(model[0].feature_name())
    ic = information_coefficients(scores, panel)
    assert ic["ml"].mean() > 0.03                                  # still finds the planted momentum


def test_history_and_market_inputs_ignore_the_future(cfg, signal_market):
    from wq.backtest import prepare
    from wq.features import market_context, weekly_history
    close, volume, fx, universe = signal_market
    _, cal, px = prepare(cfg, close, volume, fx, universe)
    sig = cal.index[cal.index <= "2018-06-30"]                      # the full calendar of signal dates
    T = sig[-15]
    full_h, full_m = weekly_history(px, sig), market_context(px, sig)
    cut = px.loc[:T]
    part_h, part_m = weekly_history(cut, sig[sig <= T]), market_context(cut, sig[sig <= T])
    pd.testing.assert_frame_equal(full_h.loc[:T], part_h)
    pd.testing.assert_frame_equal(full_m.loc[:T], part_m)
    recent = full_h.loc["2018-01-01":]
    assert recent.notna().mean().min() > 0.9 and full_m.abs().max().max() <= 1


def test_daily_calendar_matches_the_weekly_panel_on_fridays(cfg, noise_market):
    """The daily panel (research/daily_trial.py) gives each Friday the same features as the weekly one."""
    from wq.data import to_base
    from wq.features import build_panel, daily_calendar
    close, volume, fx, universe = noise_market
    weekly, cal_w, _ = prepare(cfg, close, volume, fx, universe)
    px = to_base(close, universe["currency"], fx, cfg["account"]["base_currency"])
    daily, cal_d, _ = build_panel(px, volume, universe, cfg, calendar=daily_calendar)
    assert (cal_d["exec_date"].iloc[:-1].to_numpy() == cal_d.index[1:].to_numpy()).all()
    cols = FEATURES + ["raw_vol_60"]
    fridays = weekly.index.get_level_values("date").unique()[-50:]
    a = weekly[weekly.index.get_level_values("date").isin(fridays)][cols]
    b = daily.reindex(a.index)[cols]
    pd.testing.assert_frame_equal(a, b)
