import dataclasses

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from wq import deep, stage2  # noqa: E402
from wq.backtest import prepare, simulate  # noqa: E402
from wq.model import smooth_scores, walk_forward  # noqa: E402


def test_closed_loop_simulator_matches_the_backtest(cfg, signal_market):
    close, volume, fx, universe = signal_market
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    dates = [d for d in cal.index if d >= pd.Timestamp("2018-01-01") and pd.notna(cal.loc[d, "exec_date"])]
    scores = smooth_scores(walk_forward(panel, cfg, dates, verbose=False), 4)
    ref, _ = simulate(scores, panel, cal, px, universe, fx, cfg)
    got, _ = stage2.simulate_policy(lambda T, sh, eq, pr: scores.xs(T, level="date")["score"],
                                    panel, cal, px, universe, fx, cfg, scores.index.get_level_values("date").unique())
    pd.testing.assert_series_equal(got["equity"], ref["equity"])
    assert stage2.deployed_cfg(cfg)["portfolio"]["hold_rank"] == cfg["portfolio"]["n_positions"]


def test_soft_topk():
    z = torch.tensor([[3.0, 2.5, 2.0, -1.0, -2.0, 9.0]])
    valid = torch.tensor([[True, True, True, True, True, False]])           # the 9.0 is padding
    w = stage2.soft_topk(z, valid, 3, 0.01, 0.98)
    assert w.sum().item() == pytest.approx(0.98)
    assert w[0, :3].tolist() == pytest.approx([0.98 / 3] * 3, abs=1e-3) and w[0, 3:].abs().max() < 1e-3
    soft = stage2.soft_topk(z, valid, 3, 1.0, 0.98)
    assert 0 < soft[0, 3] < soft[0, 2] < soft[0, 0] and soft[0, 5] == 0


def _setup(cfg, market, kb=None):
    close, volume, fx, universe = market
    panel, cal, px = prepare(cfg, close, volume, fx, universe)
    d, vocab = stage2.build_dense(panel, cal, px, universe, cfg)
    if kb is not None:
        d = dataclasses.replace(d, k_buy=np.full_like(d.k_buy, kb), k_sell=np.full_like(d.k_sell, kb))
    s1cfg = deep.Stage1Config(d_model=16, heads=2, blocks=1, max_epochs=6, patience=2)
    weeks, _ = deep.build_weeks(panel, universe)
    rows = [i for i, w in enumerate(d.weeks) if d.known[i]]
    fit = rows[:200]
    model, _ = deep._train([weeks[i] for i in fit], weeks[0].x.shape[1], vocab, s1cfg, 0, epochs=4)
    return d, vocab, s1cfg, model, rows, panel, cal, px, universe, fx


def test_rollout_reward_is_finite_and_differentiable(cfg, signal_market):
    d, vocab, s1cfg, model, rows, *_ = _setup(cfg, signal_market)
    m2 = deep.make_model(d.x.shape[2], vocab, s1cfg, two_heads=True)
    m2.load_stage1(model.state_dict())
    scfg = stage2.Stage2Config(horizon=4)
    rng = np.random.default_rng(0)
    h0 = torch.from_numpy(stage2.initial_holdings(d, rows[10], np.zeros(len(d.tickers)), scfg, rng))[None]
    total, anchor, aux = stage2.rollout_reward(m2, d, rows[10], h0, scfg, 0.5, model)
    assert torch.isfinite(total).all() and torch.isfinite(anchor).all() and torch.isfinite(aux)
    (-total.mean()).backward()
    assert m2.head.weight.grad.abs().sum() > 0 and m2.acct.weight.grad.abs().sum() > 0


def test_fine_tuning_trades_less_when_costs_are_high(cfg, signal_market):
    """With 2% per trade, the cost-aware policy should turn over far less than the Stage 1 ranker."""
    d, vocab, s1cfg, model, rows, panel, cal, px, universe, fx = _setup(cfg, signal_market, kb=0.02)
    scfg = stage2.Stage2Config(steps=60, rollouts_per_step=2, horizon=6, lr=3e-4)
    tuned = stage2.train_stage2(model.state_dict(), d, vocab, rows[:200], scfg, s1cfg, seed=0)
    test_rows = rows[205:245]
    dates = [d.dates[i] for i in test_rows]
    row_of = {dt: i for i, dt in enumerate(d.dates)}
    c = stage2.deployed_cfg(cfg)
    c["costs"]["slippage_bps"] = 200

    def stage1_fn(T, shares, equity, price):
        return stage2.policy_scores([_one_head(model, d, vocab, s1cfg)], d, row_of[T], shares, equity, price, scfg)

    def tuned_fn(T, shares, equity, price):
        return stage2.policy_scores([tuned], d, row_of[T], shares, equity, price, scfg)

    base, _ = stage2.simulate_policy(stage1_fn, panel, cal, px, universe, fx, c, dates)
    new, _ = stage2.simulate_policy(tuned_fn, panel, cal, px, universe, fx, c, dates)
    assert new["turnover"].iloc[1:].mean() < 0.7 * base["turnover"].iloc[1:].mean()


def _one_head(model, d, vocab, s1cfg):
    m = deep.make_model(d.x.shape[2], vocab, s1cfg, two_heads=True)
    m.load_stage1(model.state_dict())
    m.eval()
    return m
