import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from wq import stage2, stage3  # noqa: E402
from wq.portfolio import execute, generate_orders  # noqa: E402
from tests.conftest import make_market  # noqa: E402


@pytest.fixture
def meta():
    _, _, _, universe = make_market(n=30)
    return universe


def _live(shares, cash, chosen, price, meta, cfg):
    equity = cash + sum(q * price[t] for t, q in shares.items())
    targets = {t: (1 - cfg["portfolio"]["cash_buffer"]) / 15 for t in chosen}
    orders = generate_orders(shares, targets, price, equity, meta, cfg, cash)
    shares, cash, cost, _ = execute(orders, shares, cash, price, meta, cfg)
    return {t: q * price[t] for t, q in shares.items()}, cash, cost


@pytest.mark.parametrize("case", ["fresh", "drifted", "idle_cash", "short_of_cash"])
def test_vectorised_rules_match_the_live_order_rules(cfg, meta, case):
    rng = np.random.default_rng({"fresh": 0, "drifted": 1, "idle_cash": 2, "short_of_cash": 3}[case])
    tickers = list(meta.index)
    price = pd.Series(rng.uniform(5, 500, len(tickers)), index=tickers)
    shares, cash = {}, 10_000.0
    if case != "fresh":
        held = rng.choice(tickers, 15, replace=False)
        drift = {"drifted": (0.5, 1.6), "idle_cash": (0.8, 1.2), "short_of_cash": (1.0, 1.0)}[case]
        for t in held:
            shares[t] = 653.0 * rng.uniform(*drift) / price[t]
        cash = {"drifted": 200.0, "idle_cash": 900.0, "short_of_cash": 5.0}[case]
    chosen = list(rng.choice(tickers, 15, replace=False)) if case != "idle_cash" else list(shares)
    vals, cash_live, cost_live = _live(dict(shares), cash, chosen, price, meta, cfg)

    scfg = stage3.Stage3Config()
    kb, ks = stage2.cost_rates(meta, cfg, tickers)
    v = np.array([shares.get(t, 0.0) * price[t] for t in tickers])
    mask = np.array([t in chosen for t in tickers])
    v1, cash1, cost1 = stage3.construct(v, np.array(cash), mask, kb.astype(float), ks.astype(float), scfg)
    live = np.array([vals.get(t, 0.0) for t in tickers])
    assert np.abs(v1 - live).max() < 0.5                           # pennies: live rounds shares to 4 decimals
    assert cash1 == pytest.approx(cash_live, abs=1.0) and cost1 == pytest.approx(cost_live, abs=0.05)


def test_sampling_respects_caps_and_greedy_limit():
    rng = np.random.default_rng(0)
    N = 60
    country = torch.from_numpy(rng.integers(0, 3, N))
    sector = torch.from_numpy(rng.integers(0, 6, N))
    valid = torch.ones(1, N, dtype=torch.bool)
    valid[0, :5] = False
    logits = torch.from_numpy(rng.normal(0, 1, (1, N)).astype(np.float32))
    cfg = stage3.Stage3Config(group=32)
    picks = stage3.sample_sets(logits, valid, country, sector, cfg, torch.Generator().manual_seed(0))
    for g in range(cfg.group):
        p = picks[0, g].numpy()
        assert len(set(p)) == 15 and (p >= 5).all()
        assert np.bincount(country.numpy()[p]).max() <= 6 and np.bincount(sector.numpy()[p]).max() <= 5
    sharp = stage3.sample_sets(logits * 1000, valid, country, sector, stage3.Stage3Config(group=2))
    order = np.argsort(-logits[0].numpy())
    greedy, cc, sc = [], np.zeros(3), np.zeros(6)                   # the deployed rule: top scores within caps
    for i in order:
        if valid[0, i] and cc[country[i]] < 6 and sc[sector[i]] < 5 and len(greedy) < 15:
            greedy.append(i)
            cc[country[i]] += 1
            sc[sector[i]] += 1
    assert set(sharp[0, 0].numpy()) == set(greedy)


def test_replay_logprob_and_kl():
    rng = np.random.default_rng(1)
    N = 40
    country, sector = torch.from_numpy(rng.integers(0, 3, N)), torch.from_numpy(rng.integers(0, 6, N))
    valid = torch.ones(2, N, dtype=torch.bool)
    logits = torch.from_numpy(rng.normal(0, 1, (2, N)).astype(np.float32))
    cfg = stage3.Stage3Config(group=8)
    picks = stage3.sample_sets(logits, valid, country, sector, cfg)
    logp, kl = stage3.replay(logits, logits, picks, valid, country, sector, cfg)
    assert torch.allclose(kl, torch.zeros_like(kl), atol=1e-5)
    # brute-force the first sequence's log-probability
    seq, lp, taken = picks[0, 0].tolist(), 0.0, []
    cc, sc = np.zeros(3), np.zeros(6)
    for i in seq:
        allowed = [j for j in range(N) if j not in taken and cc[country[j]] < 6 and sc[sector[j]] < 5]
        z = logits[0, allowed]
        lp += float(logits[0, i] - torch.logsumexp(z, 0))
        taken.append(i)
        cc[country[i]] += 1
        sc[sector[i]] += 1
    assert logp[0, 0].item() == pytest.approx(lp, abs=1e-4)
    _, kl2 = stage3.replay(logits, logits + torch.randn_like(logits), picks, valid, country, sector, cfg)
    assert (kl2 > 0).all()


def test_grpo_trades_less_when_costs_are_high(cfg, signal_market):
    from tests.test_stage2 import _one_head, _setup
    d, vocab, s1cfg, model, rows, panel, cal, px, universe, fx = _setup(cfg, signal_market, kb=0.02)
    scfg = stage3.Stage3Config(group=16, weeks_per_step=8, steps=40, lr=3e-4, max_per_sector=15)
    tuned, log = stage3.train_stage3(model.state_dict(), d, vocab, rows[:200], scfg, s1cfg, seed=0)
    assert np.isfinite([r["reward"] for r in log]).all()
    row_of = {dt: i for i, dt in enumerate(d.dates)}
    dates = [d.dates[i] for i in rows[205:245]]
    c = stage2.deployed_cfg(cfg)
    c["costs"]["slippage_bps"] = 200
    s2 = stage2.Stage2Config()
    base, _ = stage2.simulate_policy(lambda T, sh, eq, pr: stage2.policy_scores(
        [_one_head(model, d, vocab, s1cfg)], d, row_of[T], sh, eq, pr, s2), panel, cal, px, universe, fx, c, dates)
    new, _ = stage2.simulate_policy(lambda T, sh, eq, pr: stage2.policy_scores(
        [tuned], d, row_of[T], sh, eq, pr, s2), panel, cal, px, universe, fx, c, dates)
    assert new["turnover"].iloc[1:].mean() < 0.7 * base["turnover"].iloc[1:].mean()
