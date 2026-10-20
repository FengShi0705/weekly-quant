"""Stage 2 of docs/GRPO transformer portfolio design.md: cost-aware fine-tuning through soft rollouts.

Starting from a Stage 1 ranker, the network is fine-tuned on the money it would make. Each training
sample is a closed-loop rollout of H consecutive weeks:

  week k:  scores s_k = f(features_k, holdings h_k)          (holdings enter as per-stock inputs)
           weights w_k = soft top-15 of s_k                  (smooth, so gradients flow)
           reward  r_k = log(1 - cost(h_k -> w_k)) + log(1 + w_k . R_k) - gamma/2 * var(w_k)
           h_{k+1} = w_k drifted by the week's returns

The gradient of every week's reward flows back through the holdings chain to earlier weeks, so the
model learns that keeping a stock saves next week's swap cost. Costs are Trading 212's per-stock
rates (FX fee, stamp duty / FTT, slippage), returns are net of dividend tax.

Deployed (and evaluated), the scores go through the hard live rules without the top-150 hold band or
score smoothing: hold the top 15 scores within the country cap, with the 30% drift band, the £75
minimum and real costs (`simulate_policy`).
"""
import copy
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .costs import trade_cost
from .data import usd_per_base
from .deep import N_ACCOUNT, make_model, ranking_loss
from .features import FEATURES, market_index
from .portfolio import execute, generate_orders, regime_exposure, select_targets


@dataclass
class Stage2Config:
    horizon: int = 8              # weeks per rollout
    rollouts_per_step: int = 4
    steps: int = 300              # fixed training budget per refit (no early stopping)
    lr: float = 1e-4
    weight_decay: float = 1e-3
    tau_start: float = 1.0        # soft top-K temperature on z-scored scores, annealed geometrically
    tau_end: float = 0.1
    gamma: float = 2.0            # annual risk aversion: penalty gamma/2 * variance
    rho: float = 0.3              # assumed average correlation between stocks in the risk model
    anchor: float = 0.1           # weight of ||z(s) - z(s_stage1)||^2
    aux: float = 0.5              # weight of the Stage 1 ranking loss on the return head
    n_positions: int = 15
    cash_buffer: float = 0.02
    max_swaps_init: int = 3       # random swaps applied to each rollout's starting portfolio
    seed_offset: int = 0


@dataclass
class Dense:
    """Every week over the same ticker axis, so holdings carry from week to week."""
    dates: list
    weeks: np.ndarray       # global week numbers
    tickers: np.ndarray
    x: np.ndarray           # (W, N, 2F)
    cat: np.ndarray         # (N, 3)
    present: np.ndarray     # (W, N) bool: eligible that week
    y: np.ndarray           # (W, N) label rank (Stage 1 target), NaN if unknown
    ret: np.ndarray         # (W, N) next-week return net of dividend tax, 0 where unknown
    known: np.ndarray       # (W,) bool: next-week return known
    sigma: np.ndarray       # (W, N) weekly volatility
    k_buy: np.ndarray       # (N,) cost of buying, fraction of value
    k_sell: np.ndarray      # (N,)


def cost_rates(universe, cfg, tickers):
    """Per-stock buy and sell cost as a fraction of value (Trading 212 has no fixed fees)."""
    v = 10_000.0
    buy = [trade_cost(v, 1, universe.loc[t, "country"], universe.loc[t, "currency"], "buy", cfg, ticker=t) / v
           for t in tickers]
    sell = [trade_cost(v, 1, universe.loc[t, "country"], universe.loc[t, "currency"], "sell", cfg, ticker=t) / v
            for t in tickers]
    return np.array(buy, np.float32), np.array(sell, np.float32)


def build_dense(panel, cal, px, universe, cfg, div_tax=None, features=FEATURES):
    from .deep import build_weeks
    weeks, vocab = build_weeks(panel, universe, features)
    tickers = np.array(sorted(panel.index.get_level_values("ticker").unique()))
    col = {t: i for i, t in enumerate(tickers)}
    W, N, F = len(weeks), len(tickers), weeks[0].x.shape[1]
    x = np.zeros((W, N, F), np.float32)
    present = np.zeros((W, N), bool)
    y = np.full((W, N), np.nan, np.float32)
    cat = np.zeros((N, 3), np.int64)
    for i, w in enumerate(weeks):
        j = np.array([col[t] for t in w.tickers])
        x[i, j], present[i, j], y[i, j], cat[j] = w.x, True, w.y, w.cat
    dates = [w.date for w in weeks]
    fwd = panel["fwd_ret_1w"].unstack().reindex(index=dates, columns=tickers)
    known = fwd.notna().any(axis=1).to_numpy()
    ret = np.array(fwd.fillna(0.0).to_numpy(np.float32))            # writable copy
    if div_tax is not None:
        ex = pd.to_datetime(cal.loc[dates, "exec_date"])
        nxt = ex.shift(-1)
        pxv = px.ffill()
        for i, (a, b) in enumerate(zip(ex, nxt)):
            if pd.isna(a) or pd.isna(b):
                continue
            per_share = div_tax.loc[:b].iloc[-1] - div_tax.loc[:a].iloc[-1]
            ret[i] -= np.nan_to_num((per_share / pxv.loc[:a].iloc[-1]).reindex(tickers).to_numpy(np.float32))
    sig = panel["raw_vol_60"].unstack().reindex(index=dates, columns=tickers)
    sigma = np.array((sig.fillna(sig.median(axis=1).median()) * np.sqrt(5)).to_numpy(np.float32))
    kb, ks = cost_rates(universe, cfg, tickers)
    return Dense(dates, np.array([w.week for w in weeks]), tickers, x, cat, present, y, ret, known, sigma,
                 kb, ks), vocab


def account_inputs(h, kb, ks, n_positions, cash_buffer):
    """Per-stock account features: held flag, weight relative to target, buy and sell cost (in %)."""
    torch = _torch()
    target = (1 - cash_buffer) / n_positions
    held = (h > 1e-9).float()
    z = torch.zeros_like(h)
    return torch.stack([held, h / target, z, kb.expand_as(h) * 100, ks.expand_as(h) * 100, z], -1)


def _torch():
    import torch
    return torch


def zscore(s, valid):
    torch = _torch()
    n = valid.sum(-1, keepdim=True).clamp(min=2)
    m = (s * valid).sum(-1, keepdim=True) / n
    c = torch.where(valid, s - m, torch.zeros_like(s))
    return c / (c.pow(2).sum(-1, keepdim=True) / n).sqrt().clamp(min=1e-6)


def soft_topk(z, valid, k, tau, invest):
    """Smooth top-k weights from z-scored scores: about invest/k for clear winners, about 0 otherwise."""
    torch = _torch()
    neg = torch.full_like(z, -1e4)
    zz = torch.where(valid, z, neg)
    top = zz.topk(k + 1, dim=-1).values.detach()
    theta = 0.5 * (top[..., k - 1] + top[..., k])
    g = torch.sigmoid((zz - theta[..., None]) / tau) * valid
    return invest * g / g.sum(-1, keepdim=True).clamp(min=1e-9)


def rollout_reward(model, d, start, h0, cfg, tau, ref=None):
    """Sum over H weeks of the net log reward, plus anchor terms. Returns (total reward, extras)."""
    torch = _torch()
    kb, ks = torch.from_numpy(d.k_buy), torch.from_numpy(d.k_sell)
    cat = torch.from_numpy(d.cat)[None]
    invest = 1 - cfg.cash_buffer
    h, total, anchor, aux = h0, 0.0, 0.0, 0.0
    for t in range(start, start + cfg.horizon):
        x = torch.from_numpy(d.x[t])[None]
        valid = torch.from_numpy(d.present[t])[None]
        h = h * valid                                                # anything no longer eligible is sold
        acct = account_inputs(h, kb, ks, cfg.n_positions, cfg.cash_buffer)
        s, r_head = model(x, cat, ~valid, acct, both_heads=True)
        z = zscore(s, valid)
        w = soft_topk(z, valid, cfg.n_positions, tau, invest)
        cost = ((w - h).clamp(min=0) * kb + (h - w).clamp(min=0) * ks).sum(-1)
        R = torch.from_numpy(d.ret[t])[None]
        g = (w * R).sum(-1)
        sig = torch.from_numpy(d.sigma[t])[None]
        var = cfg.rho * (w * sig).sum(-1).pow(2) + (1 - cfg.rho) * (w.pow(2) * sig.pow(2)).sum(-1)
        total = total + torch.log1p(-cost) + torch.log1p(g) - cfg.gamma / 2 * var   # weekly variance
        if ref is not None:
            with torch.no_grad():
                s_ref = ref(x, cat, ~valid)
            anchor = anchor + ((z - zscore(s_ref, valid)).pow(2) * valid).sum(-1) / valid.sum(-1)
        y = torch.from_numpy(d.y[t])[None]
        aux = aux + ranking_loss(r_head, y, ~valid, _rank_cfg())
        h = w * (1 + R) / (1 + g)[..., None]
    return total, anchor, aux


def _rank_cfg():
    from .deep import Stage1Config
    return Stage1Config()


def initial_holdings(d, t, scores_ref, cfg, rng):
    """A plausible starting portfolio: the reference model's top 15 at week t, a few names swapped at
    random, weights jittered to look drifted."""
    valid = np.where(d.present[t])[0]
    order = valid[np.argsort(-scores_ref[valid])]
    held = list(order[:cfg.n_positions])
    for _ in range(rng.integers(0, cfg.max_swaps_init + 1)):
        held[rng.integers(len(held))] = rng.choice(order[cfg.n_positions:])
    h = np.zeros(len(d.tickers), np.float32)
    h[held] = (1 - cfg.cash_buffer) / cfg.n_positions * np.exp(rng.normal(0, 0.15, len(held)))
    return h * (1 - cfg.cash_buffer) / h.sum()


def train_stage2(stage1_state, d, vocab, train_idx, cfg, s1cfg, seed):
    """Fine-tune a copy of the Stage 1 model on rollouts that start inside train_idx (week rows whose
    whole rollout has known returns). Returns the fine-tuned model."""
    torch = _torch()
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = make_model(d.x.shape[2], vocab, s1cfg, two_heads=True)
    model.load_stage1(stage1_state)
    ref = make_model(d.x.shape[2], vocab, s1cfg)
    ref.load_state_dict(stage1_state)
    ref.eval()
    starts = [i for i in train_idx if i + cfg.horizon - 1 <= max(train_idx)]
    with torch.no_grad():
        ref_scores = {}
        for i in sorted(set(starts)):
            valid = torch.from_numpy(d.present[i])[None]
            ref_scores[i] = ref(torch.from_numpy(d.x[i])[None], torch.from_numpy(d.cat)[None], ~valid)[0].numpy()
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    model.train()
    for step in range(cfg.steps):
        tau = cfg.tau_start * (cfg.tau_end / cfg.tau_start) ** (step / max(cfg.steps - 1, 1))
        loss = 0.0
        for _ in range(cfg.rollouts_per_step):
            t0 = int(rng.choice(starts))
            h0 = torch.from_numpy(initial_holdings(d, t0, ref_scores[t0], cfg, rng))[None]
            total, anchor, aux = rollout_reward(model, d, t0, h0, cfg, tau, ref)
            loss = loss + (-total + cfg.anchor * anchor + cfg.aux * aux / cfg.horizon).mean() / cfg.rollouts_per_step
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
    model.eval()
    return model


def policy_scores(models, d, t, shares, equity, price, cfg):
    """Seed-averaged policy scores for week row t given current holdings (dict ticker -> shares)."""
    torch = _torch()
    h = np.zeros(len(d.tickers), np.float32)
    col = {tk: i for i, tk in enumerate(d.tickers)}
    for tk, q in shares.items():
        if tk in col and equity > 0:
            h[col[tk]] = q * price[tk] / equity
    valid = torch.from_numpy(d.present[t])[None]
    ht = torch.from_numpy(h)[None]
    acct = account_inputs(ht, torch.from_numpy(d.k_buy), torch.from_numpy(d.k_sell), cfg.n_positions,
                          cfg.cash_buffer)
    out = 0
    with torch.no_grad():
        for m in models:
            s, _ = m(torch.from_numpy(d.x[t])[None], torch.from_numpy(d.cat)[None], ~valid, acct, both_heads=True)
            out = out + zscore(s, valid)[0].numpy()
    s = pd.Series(out / len(models), index=d.tickers)
    return s[d.present[t]]


def simulate_policy(score_fn, panel, cal, px, universe, fx_usd, cfg, dates, div_tax=None, capital=None,
                    exposure_fn=None):
    """The backtest loop of backtest.simulate, with scores computed each week from the current holdings.

    score_fn(T, shares, equity, price) -> Series ticker -> score. With a score_fn that ignores the
    holdings this reproduces backtest.simulate exactly (tested). exposure_fn(T, rows so far) -> fraction
    invested replaces the regime filter (for risk-overlay research)."""
    from .costs import dividend_tax
    base = cfg["account"]["base_currency"]
    px_val = px.ffill()
    mkt_w = market_index(px).reindex(cal.index, method="ffill")
    cash = float(cfg["account"]["capital"] if capital is None else capital)
    shares, rows, trades, prev_e = {}, [], [], None
    for T in dates:
        e = cal.loc[T, "exec_date"]
        if pd.isna(e):
            break
        price = px_val.loc[e]
        withheld = dividend_tax(shares, div_tax, prev_e, e)
        cash -= withheld
        prev_e = e
        equity = cash + sum(q * price[t] for t, q in shares.items())
        s = score_fn(T, shares, equity, price)
        expo = exposure_fn(T, rows) if exposure_fn else regime_exposure(mkt_w, T, cfg)
        vol = panel.xs(T, level="date")["raw_vol_60"]
        targets = select_targets(s, set(shares), universe, price, equity, cfg, expo, vol)
        orders = generate_orders(shares, targets, price, equity, universe, cfg, cash)
        shares, cash, cost, filled = execute(orders, shares, cash, price, universe, cfg,
                                             usd_per_base(fx_usd, base, e))
        rows.append({"signal_date": T, "exec_date": e, "deposit": 0.0, "equity": equity, "cash_after": cash,
                     "positions": len(shares), "exposure": expo, "cost": cost, "dividend_tax": withheld,
                     "turnover": sum(o["value"] for o in filled) / equity if equity > 0 else 0.0})
        trades += [{"signal_date": T, "exec_date": e, **o} for o in filled]
    res = pd.DataFrame(rows).set_index("signal_date")
    res["ret"] = res["equity"].shift(-1) / res["equity"] - 1
    return res, pd.DataFrame(trades)


def deployed_cfg(cfg):
    """Live rules for a Stage 2/3 policy: no top-150 hold band (the model decides what to keep)."""
    c = copy.deepcopy(cfg)
    c["portfolio"]["hold_rank"] = c["portfolio"]["n_positions"]
    return c


_JOBS = {}


def _job(key):
    torch = _torch()
    torch.set_num_threads(1)
    state_path, train_idx, cfg, s1cfg, seed, out_path = _JOBS[key]
    d, vocab = _JOBS["data"]
    model = train_stage2(torch.load(state_path), d, vocab, train_idx, cfg, s1cfg, seed)
    torch.save(model.state_dict(), out_path)
    return key


def train_all(d, vocab, refits, cfg, s1cfg, workers=4, verbose=True):
    """refits: list of (key, stage1 state path, train row indices, seed, output path). Trains in parallel."""
    import multiprocessing as mp
    _JOBS.clear()
    _JOBS["data"] = (d, vocab)
    for key, state_path, train_idx, seed, out_path in refits:
        _JOBS[key] = (state_path, train_idx, cfg, s1cfg, seed, out_path)
    keys = [r[0] for r in refits]
    with ProcessPoolExecutor(workers, mp_context=mp.get_context("fork")) as ex:
        for n, key in enumerate(ex.map(_job, keys)):
            if verbose:
                print(f"  {n + 1}/{len(keys)} trained {key}", flush=True)
