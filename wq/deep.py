"""Stage 1 of docs/GRPO transformer portfolio design.md: a stocks-as-tokens transformer ranker.

Each signal week is one sample. Every eligible stock that week is a token carrying the same 15
ranked price/volume features LightGBM uses (plus missing-value flags) and learned country, sector and
currency embeddings. Attention runs across the stocks of the week, with no ordering, so the model
handles a universe whose members change. Per-stock account inputs (held, weight, weeks held, buy and
sell cost) have slots from the start but are zero in Stage 1; Stages 2 and 3 switch them on.

Training per refit (walk-forward, like model.walk_forward but refitting every few weeks):
  1. weeks whose labels were known by the prediction date, the same 260-week window as LightGBM;
  2. the last 52 of them are an inner validation block (after a 1-week purge) used only to pick the
     number of epochs by validation IC;
  3. the model is then retrained on all 260 weeks for that many epochs and scores the next weeks.
Several seeds are trained independently and their scores averaged. Needs PyTorch (CPU is enough).
"""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .features import FEATURES

N_ACCOUNT = 6           # held flag, weight, weeks held, buy cost, sell cost, spare


@dataclass
class Stage1Config:
    d_model: int = 64
    heads: int = 4
    blocks: int = 2
    dropout: float = 0.2
    lr: float = 3e-4
    weight_decay: float = 1e-3
    batch_weeks: int = 8
    max_epochs: int = 40
    patience: int = 5
    listnet_weight: float = 0.5
    listnet_temperature: float = 0.5
    val_weeks: int = 52
    refit_every_weeks: int = 13
    train_window_weeks: int = 260
    min_train_weeks: int = 156
    seeds: tuple = (0, 1, 2)
    workers: int = 4
    use_categories: bool = True     # False: country, sector and currency ids are blanked (ablation)
    save_dir: str = ""              # if set, each refit's model is saved there (for Stage 2)
    features: list = field(default_factory=lambda: list(FEATURES))


@dataclass
class Week:
    date: pd.Timestamp
    week: int
    tickers: np.ndarray
    x: np.ndarray          # (N, 2F): ranked features with NaN -> 0, then missing flags
    cat: np.ndarray        # (N, 3): country, sector, currency ids
    y: np.ndarray          # (N,): next-week return rank in [-0.5, 0.5]; NaN if not yet known


def build_weeks(panel, universe, features=FEATURES):
    """One Week per signal date, from the panel that features.build_panel returns."""
    vocab = {c: {v: i + 1 for i, v in enumerate(sorted(universe[c].astype(str).unique()))}
             for c in ("country", "sector", "currency")}
    ids = pd.DataFrame({c: universe[c].astype(str).map(vocab[c]) for c in vocab}, index=universe.index)
    weeks = []
    for d, g in panel.groupby(level="date", sort=True):
        tick = g.index.get_level_values("ticker").to_numpy()
        f = g[features].to_numpy(dtype=np.float32)
        miss = np.isnan(f)
        x = np.concatenate([np.nan_to_num(f), miss.astype(np.float32)], axis=1)
        cat = ids.reindex(tick).fillna(0).to_numpy(dtype=np.int64)
        weeks.append(Week(d, int(g["week"].iloc[0]), tick, x, cat, g["label"].to_numpy(dtype=np.float32)))
    return weeks, {c: len(v) + 1 for c, v in vocab.items()}


def _torch():
    import torch
    return torch


def make_model(n_feat, vocab_sizes, cfg):
    torch = _torch()
    nn = torch.nn

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            d = cfg.d_model
            self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
            self.att = nn.MultiheadAttention(d, cfg.heads, dropout=cfg.dropout, batch_first=True)
            self.ff = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Dropout(cfg.dropout), nn.Linear(4 * d, d))
            self.drop = nn.Dropout(cfg.dropout)

        def forward(self, z, pad):
            y = self.ln1(z)
            z = z + self.drop(self.att(y, y, y, key_padding_mask=pad, need_weights=False)[0])
            return z + self.drop(self.ff(self.ln2(z)))

    class Ranker(nn.Module):
        """Scores every stock of a week, looking at the whole week's cross-section."""

        def __init__(self):
            super().__init__()
            self.emb = nn.ModuleList([nn.Embedding(vocab_sizes[c], k) for c, k in
                                      (("country", 4), ("sector", 4), ("currency", 3))])
            self.inp = nn.Linear(n_feat + 4 + 4 + 3, cfg.d_model)
            self.acct = nn.Linear(N_ACCOUNT, cfg.d_model, bias=False)
            nn.init.zeros_(self.acct.weight)        # Stage 1 behaves as if account inputs didn't exist
            self.blocks = nn.ModuleList([Block() for _ in range(cfg.blocks)])
            self.ln = nn.LayerNorm(cfg.d_model)
            self.head = nn.Linear(cfg.d_model, 1)

        def forward(self, x, cat, pad, acct=None):
            e = [emb(cat[..., i]) for i, emb in enumerate(self.emb)]
            z = self.inp(torch.cat([x, *e], -1))
            if acct is not None:
                z = z + self.acct(acct)
            for blk in self.blocks:
                z = blk(z, pad)
            return self.head(self.ln(z))[..., 0]

    return Ranker()


def collate(weeks):
    """Pad a list of Weeks to tensors: x (B,N,2F), cat (B,N,3), y (B,N), pad (B,N) True = padding."""
    torch = _torch()
    n = max(len(w.tickers) for w in weeks)
    B, F = len(weeks), weeks[0].x.shape[1]
    x = np.zeros((B, n, F), np.float32)
    cat = np.zeros((B, n, 3), np.int64)
    y = np.full((B, n), np.nan, np.float32)
    pad = np.ones((B, n), bool)
    for i, w in enumerate(weeks):
        k = len(w.tickers)
        x[i, :k], cat[i, :k], y[i, :k], pad[i, :k] = w.x, w.cat, w.y, False
    return torch.from_numpy(x), torch.from_numpy(cat), torch.from_numpy(y), torch.from_numpy(pad)


def ranking_loss(s, y, pad, cfg):
    """Minus the weekly correlation between scores and labels, plus a ListNet term (mean over weeks)."""
    torch = _torch()
    valid = ~pad & ~torch.isnan(y)
    yv = torch.where(valid, y, torch.zeros_like(y))
    n = valid.sum(1).clamp(min=2)

    def z(v):
        m = (v * valid).sum(1, keepdim=True) / n[:, None]
        c = torch.where(valid, v - m, torch.zeros_like(v))
        return c / (c.pow(2).sum(1, keepdim=True) / n[:, None]).sqrt().clamp(min=1e-6)

    zs, zy = z(s), z(yv)
    ic = (zs * zy).sum(1) / n
    neg = torch.finfo(s.dtype).min
    p = torch.softmax(torch.where(valid, zy / cfg.listnet_temperature, torch.full_like(zy, neg)), 1)
    logq = torch.log_softmax(torch.where(valid, s, torch.full_like(s, neg)), 1)
    listnet = -(torch.where(valid, p * logq, torch.zeros_like(s))).sum(1)
    return (-ic + cfg.listnet_weight * listnet).mean()


def _score(model, weeks, batch=16):
    torch = _torch()
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(weeks), batch):
            chunk = weeks[i:i + batch]
            x, cat, _, pad = collate(chunk)
            s = model(x, cat, pad).numpy()
            out += [s[j, :len(w.tickers)] for j, w in enumerate(chunk)]
    return out


def mean_ic(model, weeks):
    ics = []
    for w, s in zip(weeks, _score(model, weeks)):
        ok = ~np.isnan(w.y)
        if ok.sum() >= 10:
            ics.append(pd.Series(s[ok]).rank().corr(pd.Series(w.y[ok]).rank()))
    return float(np.mean(ics)) if ics else float("nan")


def _train(train_weeks, n_feat, vocab, cfg, seed, epochs=None, val_weeks=None):
    """Train from scratch. With val_weeks, stop when validation IC stops improving; returns
    (model, best epoch count). Without, train exactly `epochs` epochs."""
    torch = _torch()
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = make_model(n_feat, vocab, cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    best, best_ep, best_state, bad = -np.inf, 0, None, 0
    for ep in range(1, (epochs or cfg.max_epochs) + 1):
        model.train()
        order = rng.permutation(len(train_weeks))
        for i in range(0, len(order), cfg.batch_weeks):
            x, cat, y, pad = collate([train_weeks[j] for j in order[i:i + cfg.batch_weeks]])
            loss = ranking_loss(model(x, cat, pad), y, pad, cfg)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        if val_weeks is None:
            continue
        ic = mean_ic(model, val_weeks)
        if ic > best:
            best, best_ep, bad = ic, ep, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= cfg.patience:
                break
    if val_weeks is not None and best_state is not None:
        model.load_state_dict(best_state)
    return model, best_ep


def refit_plan(weeks, pred_dates, cfg, horizon=1):
    """[(train weeks, val weeks, prediction weeks)] for each refit, with no look-ahead."""
    by_date = {w.date: w for w in weeks}
    pred = [by_date[d] for d in pred_dates if d in by_date]
    plan, i = [], 0
    while i < len(pred):
        iT = pred[i].week
        hi = iT - horizon - 1                       # labels known at signal(T): t + h <= T - 1
        window = [w for w in weeks if hi - cfg.train_window_weeks < w.week <= hi]
        chunk = [w for w in pred[i:] if w.week < iT + cfg.refit_every_weeks]
        if len(window) >= cfg.min_train_weeks:
            cut = hi - cfg.val_weeks
            fit_w = [w for w in window if w.week < cut]          # one-week purge before validation
            val_w = [w for w in window if w.week > cut]
            plan.append((window, fit_w, val_w, chunk))
        i += len(chunk)
    return plan


def _job(args):
    """One (refit, seed): pick epochs on the inner validation block, retrain on the full window, score."""
    plan_i, seed, n_feat, vocab, cfg = args
    torch = _torch()
    torch.set_num_threads(1)
    window, fit_w, val_w, chunk = _PLAN[plan_i]
    _, best_ep = _train(fit_w, n_feat, vocab, cfg, seed * 1000 + plan_i, val_weeks=val_w)
    model, _ = _train(window, n_feat, vocab, cfg, seed * 1000 + plan_i, epochs=max(best_ep, 1))
    if cfg.save_dir:
        torch.save(model.state_dict(), f"{cfg.save_dir}/refit{plan_i:03d}_seed{seed}.pt")
    scores = _score(model, chunk)
    rows = [pd.DataFrame({"date": w.date, "ticker": w.tickers, "tx": s, "seed": seed})
            for w, s in zip(chunk, scores)]
    return plan_i, seed, best_ep, pd.concat(rows)


_PLAN = []


def walk_forward_tx(weeks, vocab, pred_dates, cfg, verbose=True):
    """Stage 1 scores for pred_dates: DataFrame indexed by (date, ticker) with column tx (the
    seed-averaged, per-week z-scored score). Also returns a log of epochs chosen per refit and seed."""
    global _PLAN
    if not cfg.use_categories:
        weeks = [Week(w.date, w.week, w.tickers, w.x, np.zeros_like(w.cat), w.y) for w in weeks]
    _PLAN = refit_plan(weeks, pred_dates, cfg)
    n_feat = weeks[0].x.shape[1]
    jobs = [(i, s, n_feat, vocab, cfg) for i in range(len(_PLAN)) for s in cfg.seeds]
    results, log = [], []
    if cfg.workers > 1:
        import multiprocessing as mp
        with ProcessPoolExecutor(cfg.workers, mp_context=mp.get_context("fork")) as ex:
            for k, (i, seed, ep, df) in enumerate(ex.map(_job, jobs)):
                results.append(df)
                log.append({"refit": i, "first_date": _PLAN[i][3][0].date, "seed": seed, "epochs": ep})
                if verbose:
                    print(f"  {k + 1}/{len(jobs)} refit {_PLAN[i][3][0].date.date()} seed {seed}: {ep} epochs",
                          flush=True)
    else:
        for i, seed, ep, df in map(_job, jobs):
            results.append(df)
            log.append({"refit": i, "first_date": _PLAN[i][3][0].date, "seed": seed, "epochs": ep})
    raw = pd.concat(results)
    raw["tx"] = raw.groupby(["date", "seed"])["tx"].transform(lambda v: (v - v.mean()) / (v.std() or 1.0))
    scores = raw.groupby(["date", "ticker"])["tx"].mean().to_frame()
    return scores, pd.DataFrame(log)
