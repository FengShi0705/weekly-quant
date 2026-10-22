import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from wq import deep  # noqa: E402
from wq.backtest import prepare  # noqa: E402


def small_cfg(**kw):
    base = dict(d_model=16, heads=2, blocks=1, max_epochs=8, patience=3, refit_every_weeks=26, seeds=(0,), workers=1)
    return deep.Stage1Config(**(base | kw))


def weekly_ic(scores, panel):
    df = scores.join(panel[["fwd_ret_1w"]]).dropna()
    ic = df.groupby(level="date").apply(lambda g: g["tx"].rank().corr(g["fwd_ret_1w"].rank()))
    return ic.mean(), ic.mean() / ic.std() * np.sqrt(ic.count())


def run(cfg, market, scfg, shuffle=False):
    close, volume, fx, universe = market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    weeks, vocab = deep.build_weeks(panel, universe)
    if shuffle:
        rng = np.random.default_rng(0)
        weeks = [deep.Week(w.date, w.week, w.tickers, w.x, w.cat, rng.permutation(w.y)) for w in weeks]
    dates = [d for d in cal.index if d >= pd.Timestamp(cfg["backtest"]["start"])][:-1]
    scores, log = deep.walk_forward_tx(weeks, vocab, dates, scfg, verbose=False)
    return scores, log, panel, weeks


def test_finds_planted_momentum(cfg, signal_market):
    scores, log, panel, _ = run(cfg, signal_market, small_cfg())
    ic, t = weekly_ic(scores, panel)
    assert ic > 0.05 and t > 3, (ic, t)
    assert (log["epochs"] >= 1).all()


def test_no_skill_on_pure_noise(cfg, noise_market):
    scores, _, panel, _ = run(cfg, noise_market, small_cfg())
    ic, t = weekly_ic(scores, panel)
    assert abs(ic) < 0.03 and abs(t) < 3, (ic, t)


def test_scores_do_not_depend_on_future_labels(cfg, signal_market):
    """Scramble every label after a cutoff week: scores from refits trained before it must not change."""
    close, volume, fx, universe = signal_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    weeks, vocab = deep.build_weeks(panel, universe)
    dates = [d for d in cal.index if pd.Timestamp("2017-01-01") <= d < pd.Timestamp("2018-07-01")]
    scfg = small_cfg(max_epochs=3)
    plan = deep.refit_plan(weeks, dates, scfg)
    assert len(plan) >= 3
    cutoff = plan[1][3][0].week - 2                     # the second refit's training window ends here
    rng = np.random.default_rng(1)
    scrambled = [w if w.week <= cutoff else deep.Week(w.date, w.week, w.tickers, w.x, w.cat,
                                                      rng.permutation(w.y) + 1.0) for w in weeks]
    a, _ = deep.walk_forward_tx(weeks, vocab, dates, scfg, verbose=False)
    b, _ = deep.walk_forward_tx(scrambled, vocab, dates, scfg, verbose=False)
    known = [w.date for p in plan[:2] for w in p[3]]
    later = [w.date for p in plan[2:] for w in p[3]]
    pd.testing.assert_frame_equal(a.loc[known], b.loc[known])
    assert not np.allclose(a.loc[later, "tx"], b.loc[later, "tx"])   # the test can see a difference


def test_refit_plan_never_looks_ahead(cfg, signal_market):
    close, volume, fx, universe = signal_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    weeks, _ = deep.build_weeks(panel, universe)
    dates = [d for d in cal.index if d >= pd.Timestamp("2016-01-01")][:-1]
    plan = deep.refit_plan(weeks, dates, deep.Stage1Config())
    assert len(plan) > 5
    for window, fit_w, val_w, chunk in plan:
        first = chunk[0].week
        assert max(w.week for w in window) <= first - 2          # labels known by the signal date
        assert 156 <= len(window) <= 260 and len(val_w) == 52
        assert max(w.week for w in fit_w) < min(w.week for w in val_w) - 1    # purge between them
        assert set(w.week for w in fit_w) | set(w.week for w in val_w) < set(w.week for w in window)
        assert max(w.week for w in chunk) < first + 13
    predicted = [w.date for p in plan for w in p[3]]
    assert len(predicted) == len(set(predicted))                  # each week scored by one refit


@pytest.mark.parametrize("h", [4, 13])
def test_refit_plan_purges_multi_week_labels(cfg, signal_market, h):
    """With h-week labels (research/horizon_trial.py), a training week's label must have ended by the
    prediction date, and every fit label before the validation block starts."""
    close, volume, fx, universe = signal_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    weeks, _ = deep.build_weeks(panel, universe)
    dates = [d for d in cal.index if d >= pd.Timestamp("2016-01-01")][:-1]
    plan = deep.refit_plan(weeks, dates, deep.Stage1Config(label_horizon=h))
    assert len(plan) > 5
    for window, fit_w, val_w, chunk in plan:
        first = chunk[0].week
        assert max(w.week for w in window) + h <= first - 1      # label ends at exec(t + h) <= signal(T)
        assert max(w.week for w in fit_w) + h < min(w.week for w in val_w)


def test_cached_walk_forward_resumes_with_identical_scores(cfg, signal_market, tmp_path):
    """With cache_dir, an interrupted walk-forward reuses finished (refit, seed) scores exactly."""
    scfg = small_cfg(cache_dir=str(tmp_path))
    first, log1, _, _ = run(cfg, signal_market, scfg)
    files = sorted(tmp_path.glob("*.parquet"))
    assert len(files) == len(log1)
    files[-1].unlink()                                        # as if the last job was interrupted
    again, log2, _, _ = run(cfg, signal_market, scfg)
    pd.testing.assert_frame_equal(first, again)
    assert log1["epochs"].tolist() == log2["epochs"].tolist()


def test_padding_and_account_slots_do_not_change_scores(cfg, signal_market):
    close, volume, fx, universe = signal_market
    panel, _, _ = prepare(cfg, close, volume, fx, universe)
    weeks, vocab = deep.build_weeks(panel, universe)
    model = deep.make_model(weeks[0].x.shape[1], vocab, deep.Stage1Config())
    model.eval()
    small = deep.Week(weeks[-1].date, weeks[-1].week, weeks[-1].tickers[:20], weeks[-1].x[:20],
                      weeks[-1].cat[:20], weeks[-1].y[:20])
    alone = deep._score(model, [small])[0]
    padded = deep._score(model, [small, weeks[-2]])[0]             # batched with a bigger week
    assert np.allclose(alone, padded, atol=1e-5)
    x, cat, _, pad = deep.collate([small])
    with torch.no_grad():
        acct = torch.randn(1, 20, deep.N_ACCOUNT)
        assert torch.allclose(model(x, cat, pad), model(x, cat, pad, acct))   # zero-initialised


def test_ranking_loss_prefers_correct_order():
    cfg = deep.Stage1Config()
    y = torch.tensor([[0.4, 0.1, -0.1, -0.4, float("nan")]])
    pad = torch.tensor([[False, False, False, False, True]])
    good = deep.ranking_loss(torch.tensor([[2.0, 1.0, -1.0, -2.0, 9.0]]), y, pad, cfg)
    bad = deep.ranking_loss(torch.tensor([[-2.0, -1.0, 1.0, 2.0, 9.0]]), y, pad, cfg)
    assert good < bad and torch.isfinite(good)


def test_live_scores_retrain_and_match_the_walk_forward(cfg, signal_market, tmp_path):
    close, volume, fx, universe = signal_market
    panel, cal, _ = prepare(cfg, close, volume, fx, universe)
    weeks, vocab = deep.build_weeks(panel, universe)
    dates = [d for d in cal.index if d >= pd.Timestamp("2017-01-01")][:40]
    scfg = small_cfg(max_epochs=2, seeds=(0, 1), refit_anchor=str(dates[0].date()))
    backtest, _ = deep.walk_forward_tx(weeks, vocab, dates, scfg, verbose=False)
    live_dates = dates[22:30]                                    # spans the boundary between two blocks
    live = deep.live_scores(panel, universe, live_dates, tmp_path, scfg, verbose=False)
    pd.testing.assert_frame_equal(live, backtest.loc[live_dates], atol=1e-6)
    assert len(list(tmp_path.glob("*/refit*_seed*.pt"))) == 4    # two blocks x two seeds, saved
    with pytest.raises(FileNotFoundError):
        deep.live_scores(panel, universe, live_dates, tmp_path / "empty", scfg, retrain=False)
