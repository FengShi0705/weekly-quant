"""Stage 3 of docs/GRPO transformer portfolio design.md: GRPO through the exact live order rules.

For each training week the policy samples G portfolios of 15 stocks (a masked Plackett-Luce draw over
its scores: one stock at a time with probability softmax(z(score) / tau), skipping stocks already picked
and countries or sectors that are full). Every sampled set goes through the same order rules as live
trading: equal weights, the 30% drift band for names already held, the £75 minimum trade, the idle-cash
top-up and buys scaled to the cash available, with Trading 212's per-stock costs. Its reward is next
week's net log return (dividend tax included) minus a risk penalty.

All G samples share the week's holdings and market, so a sample's advantage (its reward minus the mean
of the other G-1) says only whether its choice of names, and of swaps, beat the alternatives after
costs. A KL penalty to the frozen Stage 1 policy stops it from memorising which stocks happened to win.
Updates are on-policy (one gradient step per sampled batch), so this is GRPO without the parts that do
nothing here: no clipping, no per-week standard-deviation scaling.
"""
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np

from .deep import Stage1Config, make_model, ranking_loss
from .stage2 import account_inputs, initial_holdings, zscore

NEG = -1e9


@dataclass
class Stage3Config:
    group: int = 64               # sampled portfolios per week
    weeks_per_step: int = 32
    steps: int = 100              # fixed budget per refit, no early stopping
    lr: float = 3e-5
    weight_decay: float = 1e-3
    tau: float = 0.15             # sampling temperature on z-scored scores: samples differ from the
                                  # deployed top 15 by about 4 names (0.5 gave about 10)
    beta: float = 0.05            # weight of KL(policy || Stage 1 policy), exact, summed over the 15 picks
    gamma: float = 2.0            # annual risk aversion; penalty gamma/2 * weekly variance
    rho: float = 0.3
    aux: float = 0.5              # Stage 1 ranking loss on the return head
    n_positions: int = 15
    cash_buffer: float = 0.02
    max_per_country: int = 6
    max_per_sector: int = 5
    drift: float = 0.30
    min_trade: float = 75.0
    max_idle_cash: float = 0.05
    account: float = 10_000.0     # account size the £75 minimum is applied against
    max_swaps_init: int = 3


def _torch():
    import torch
    return torch


def _caps_full(ccount, scount, country, sector, cfg):
    return (ccount.gather(-1, country) >= cfg.max_per_country) | (scount.gather(-1, sector) >= cfg.max_per_sector)


def sample_sets(logits, valid, country, sector, cfg, generator=None):
    """Draw cfg.group sets of n_positions stocks per week. logits (B,N); returns picks (B,G,K) long."""
    torch = _torch()
    B, N = logits.shape
    G, K = cfg.group, cfg.n_positions
    with torch.no_grad():
        lg = logits[:, None, :].expand(B, G, N)
        cty, sec = country.expand(B, G, N), sector.expand(B, G, N)
        taken = torch.zeros(B, G, N, dtype=torch.bool)
        cc = torch.zeros(B, G, int(country.max()) + 1)
        sc = torch.zeros(B, G, int(sector.max()) + 1)
        picks = []
        for _ in range(K):
            mask = ~valid[:, None, :] | taken | _caps_full(cc, sc, cty, sec, cfg)
            p = torch.softmax(lg.masked_fill(mask, NEG), -1)
            i = torch.multinomial(p.reshape(B * G, N), 1, generator=generator).reshape(B, G)
            taken.scatter_(-1, i[..., None], True)
            cc.scatter_add_(-1, cty.gather(-1, i[..., None]), torch.ones(B, G, 1))
            sc.scatter_add_(-1, sec.gather(-1, i[..., None]), torch.ones(B, G, 1))
            picks.append(i)
    return torch.stack(picks, -1)


def replay(logits, ref_logits, picks, valid, country, sector, cfg):
    """Log-probability of each sampled sequence under the policy, and the exact KL to the reference
    policy summed over the picks (each step's KL over the stocks still allowed). Differentiable."""
    torch = _torch()
    B, G, K = picks.shape
    N = logits.shape[-1]
    cty, sec = country.expand(B, G, N), sector.expand(B, G, N)
    taken = torch.zeros(B, G, N, dtype=torch.bool)
    cc = torch.zeros(B, G, int(country.max()) + 1)
    sc = torch.zeros(B, G, int(sector.max()) + 1)
    lg, lr = logits[:, None, :].expand(B, G, N), ref_logits[:, None, :].expand(B, G, N)
    logp = torch.zeros(B, G)
    kl = torch.zeros(B, G)
    for k in range(K):
        mask = ~valid[:, None, :] | taken | _caps_full(cc, sc, cty, sec, cfg)
        lp = torch.log_softmax(lg.masked_fill(mask, NEG), -1)
        lq = torch.log_softmax(lr.masked_fill(mask, NEG), -1)
        i = picks[..., k:k + 1]
        logp = logp + lp.gather(-1, i)[..., 0]
        kl = kl + (lp.exp() * (lp - lq)).masked_fill(mask, 0.0).sum(-1)
        taken = taken.scatter(-1, i, True)
        cc = cc.scatter_add(-1, cty.gather(-1, i), torch.ones(B, G, 1))
        sc = sc.scatter_add(-1, sec.gather(-1, i), torch.ones(B, G, 1))
    return logp, kl


def construct(v, cash, chosen, kb, ks, cfg):
    """The live order rules (portfolio.generate_orders + execute) in value terms, vectorised.

    v (..., N) position values before trading, cash (...), chosen (..., N) bool: the target set.
    Returns (values after trading, cash after, total cost)."""
    E = cash + v.sum(-1)
    t = (1 - cfg.cash_buffer) * E / cfg.n_positions
    tt = t[..., None]
    idle = (cash / E > cfg.max_idle_cash)[..., None]
    held = v > 0
    exit_ = held & ~chosen
    in_band = np.abs(v - tt) <= cfg.drift * tt
    keep = chosen & held & in_band & ~(idle & (tt > v))
    trade = np.where(chosen & ~keep, tt - v, 0.0)
    trade = np.where(np.abs(trade) < cfg.min_trade, 0.0, trade)
    trade = np.where(exit_, -v, trade)
    sells, buys = np.clip(-trade, 0, None), np.clip(trade, 0, None)
    cash1 = cash + (sells * (1 - ks)).sum(-1)
    need = (buys * (1 + kb)).sum(-1)
    scale = np.where(need > 0, np.minimum(1.0, cash1 / np.where(need > 0, need, 1.0)), 1.0)
    buys = buys * scale[..., None]
    cash2 = cash1 - (buys * (1 + kb)).sum(-1)
    cost = (sells * ks).sum(-1) + (buys * kb).sum(-1)
    return v - sells + buys, cash2, cost


def week_rewards(v0, cash0, picks, R, sigma, kb, ks, cfg):
    """Net log return of each sampled portfolio over the next week, minus the risk penalty (numpy)."""
    B, G, K = picks.shape
    N = v0.shape[-1]
    chosen = np.zeros((B, G, N), bool)
    np.put_along_axis(chosen, picks, True, axis=-1)
    v = np.broadcast_to(v0[:, None, :], (B, G, N))
    cash = np.broadcast_to(cash0[:, None], (B, G))
    E0 = cash + v.sum(-1)
    v1, cash1, _ = construct(v, cash, chosen, kb, ks, cfg)
    w = v1 / E0[..., None]
    E1 = cash1 + (v1 * (1 + R[:, None, :])).sum(-1)
    s = sigma[:, None, :]
    var = cfg.rho * (w * s).sum(-1) ** 2 + (1 - cfg.rho) * (w ** 2 * s ** 2).sum(-1)
    return np.log(E1 / E0) - cfg.gamma / 2 * var


def train_stage3(stage1_state, d, vocab, train_idx, cfg, s1cfg, seed):
    """GRPO fine-tuning of a Stage 1 model on the weeks in train_idx (rows with known next-week returns)."""
    torch = _torch()
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = make_model(d.x.shape[2], vocab, s1cfg, two_heads=True)
    model.load_stage1(stage1_state)
    ref = make_model(d.x.shape[2], vocab, s1cfg)
    ref.load_state_dict(stage1_state)
    ref.eval()
    country, sector = torch.from_numpy(d.cat[:, 0]), torch.from_numpy(d.cat[:, 1])
    kb_t, ks_t = torch.from_numpy(d.k_buy), torch.from_numpy(d.k_sell)
    cat = torch.from_numpy(d.cat)
    rows = np.array(sorted(train_idx))
    with torch.no_grad():
        ref_all = {}
        for i in rows:
            valid = torch.from_numpy(d.present[i])[None]
            ref_all[i] = ref(torch.from_numpy(d.x[i])[None], cat[None], ~valid)[0]
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    model.eval()        # no dropout: sample from, and train, the same policy that will be deployed
    log = []
    for step in range(cfg.steps):
        wk = rng.choice(rows, size=min(cfg.weeks_per_step, len(rows)), replace=False)
        h = np.stack([initial_holdings(d, i, ref_all[i].numpy(), cfg, rng) for i in wk])
        h *= rng.uniform(0.9, 1.0, (len(wk), 1)).astype(np.float32)          # some weeks start with idle cash
        v0 = h * cfg.account
        cash0 = cfg.account - v0.sum(-1)
        valid = torch.from_numpy(d.present[wk])
        x = torch.from_numpy(d.x[wk])
        acct = account_inputs(torch.from_numpy(h), kb_t, ks_t, cfg.n_positions, cfg.cash_buffer)
        s, r_head = model(x, cat.expand(len(wk), -1, -1), ~valid, acct, both_heads=True)
        logits = zscore(s, valid) / cfg.tau
        ref_logits = torch.stack([zscore(ref_all[i][None], valid[j:j + 1])[0] for j, i in enumerate(wk)]) / cfg.tau
        picks = sample_sets(logits.detach(), valid, country, sector, cfg, gen)
        r = week_rewards(v0, cash0, picks.numpy(), d.ret[wk], d.sigma[wk], d.k_buy, d.k_sell, cfg)
        G = cfg.group
        adv = r - (r.sum(1, keepdims=True) - r) / (G - 1)                    # leave-one-out baseline
        adv = adv / (adv.std() + 1e-8)                                        # one global scale per batch
        logp, kl = replay(logits, ref_logits, picks, valid, country, sector, cfg)
        y = torch.from_numpy(d.y[wk])
        loss = (-(torch.from_numpy(adv.astype(np.float32)) * logp).mean() + cfg.beta * kl.mean()
                + cfg.aux * ranking_loss(r_head, y, ~valid, Stage1Config()))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        log.append({"step": step, "reward": float(r.mean()), "kl": float(kl.detach().mean()),
                    "jaccard": float(_mean_overlap(picks.numpy()))})
    model.eval()
    return model, log


def _mean_overlap(picks):
    """Average share of names two sampled portfolios of the same week have in common (collapse check)."""
    B, G, K = picks.shape
    a, b = picks[:, 0, :], picks[:, 1, :]
    return np.mean([len(set(a[i]) & set(b[i])) / K for i in range(B)])


_JOBS = {}


def _job(key):
    torch = _torch()
    torch.set_num_threads(1)
    state_path, train_idx, cfg, s1cfg, seed, out_path = _JOBS[key]
    d, vocab = _JOBS["data"]
    model, log = train_stage3(torch.load(state_path), d, vocab, train_idx, cfg, s1cfg, seed)
    torch.save(model.state_dict(), out_path)
    return key, log


def train_all(d, vocab, jobs, cfg, s1cfg, workers=4, verbose=True):
    """jobs: list of (key, stage1 state path, train row indices, seed, output path). Returns training logs."""
    _JOBS.clear()
    _JOBS["data"] = (d, vocab)
    for key, state_path, train_idx, seed, out_path in jobs:
        _JOBS[key] = (state_path, train_idx, cfg, s1cfg, seed, out_path)
    logs = {}
    with ProcessPoolExecutor(workers, mp_context=mp.get_context("fork")) as ex:
        for n, (key, log) in enumerate(ex.map(_job, [j[0] for j in jobs])):
            logs[key] = log
            if verbose:
                print(f"  {n + 1}/{len(jobs)} trained {key}: reward {log[0]['reward']:+.4f} -> {log[-1]['reward']:+.4f}, "
                      f"KL {log[-1]['kl']:.2f}, overlap {log[-1]['jaccard']:.2f}", flush=True)
    return logs
