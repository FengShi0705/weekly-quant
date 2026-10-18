"""Time one training step of each proposed stage (docs/GRPO transformer portfolio design.md) with random
data of the real shapes. Needs PyTorch (CPU build is enough). Usage: python research/bench_stages.py [threads]

Measured on the 4-CPU cloud machine, 18 Oct 2026 (MLP history encoder, 113k parameters):
  245 stocks:   stage1 0.12s  stage2 0.36s  stage3 0.90s  stage3 8-week group forward 11.9s
  1,000 stocks: stage1 1.33s  stage2 6.52s  stage3 10.8s  stage3 8-week group forward 184s
"""
import sys
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)
F_RANK, HIST, D, K = 15, 26, 64, 15


class Block(nn.Module):
    def __init__(self, d, h, ff, p):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.att = nn.MultiheadAttention(d, h, dropout=p, batch_first=True)
        self.ff = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Dropout(p), nn.Linear(ff, d))
        self.drop = nn.Dropout(p)

    def forward(self, x, mask):
        y = self.ln1(x)
        x = x + self.drop(self.att(y, y, y, key_padding_mask=mask, need_weights=False)[0])
        return x + self.drop(self.ff(self.ln2(x)))


class Net(nn.Module):
    def __init__(self, temporal):
        super().__init__()
        self.temporal = temporal
        self.enc = (nn.GRU(2, 32, batch_first=True) if temporal == "gru"
                    else nn.Sequential(nn.Linear(2 * HIST, 64), nn.GELU(), nn.Linear(64, 32)))
        self.emb_c, self.emb_s, self.emb_k = nn.Embedding(30, 8), nn.Embedding(15, 8), nn.Embedding(10, 4)
        self.inp = nn.Linear(2 * F_RANK + 32 + 8 + 8 + 4 + 6, D)
        self.film = nn.Linear(8, 2 * D)
        self.blocks = nn.ModuleList([Block(D, 4, 4 * D, 0.2) for _ in range(2)])
        self.ln, self.head = nn.LayerNorm(D), nn.Linear(D, 2)

    def forward(self, b, acct):
        B, N, _ = b["x"].shape
        if self.temporal == "gru":
            _, h = self.enc(b["hist"].reshape(B * N, HIST, 2))
            h = h[-1].reshape(B, N, 32)
        else:
            h = self.enc(b["hist"].reshape(B, N, 2 * HIST))
        z = torch.cat([b["x"], h, self.emb_c(b["c"]), self.emb_s(b["s"]), self.emb_k(b["k"]), acct], -1)
        z = self.inp(z)
        g, beta = self.film(b["m"]).chunk(2, -1)
        z = z * (1 + g[:, None]) + beta[:, None]
        for blk in self.blocks:
            z = blk(z, b["mask"])
        return self.head(self.ln(z))[..., 0]


def batch(B, N):
    return {"x": torch.randn(B, N, 2 * F_RANK), "hist": torch.randn(B, N, HIST, 2),
            "c": torch.randint(0, 14, (B, N)), "s": torch.randint(0, 11, (B, N)), "k": torch.randint(0, 5, (B, N)),
            "m": torch.randn(B, 8), "mask": torch.zeros(B, N, dtype=torch.bool),
            "R": 0.03 * torch.randn(B, N), "kb": torch.full((B, N), 0.004), "ks": torch.full((B, N), 0.0025)}


def stage1(net, opt, N, B=8):
    b = batch(B, N)
    s = net(b, torch.zeros(B, N, 6))
    y = (b["R"] - b["R"].mean(1, keepdim=True)) / b["R"].std(1, keepdim=True)
    sc = (s - s.mean(1, keepdim=True)) / (s.std(1, keepdim=True) + 1e-8)
    loss = -(sc * y).mean(1).mean() - 0.5 * (F.softmax(y / 0.5, 1) * F.log_softmax(s, 1)).sum(1).mean()
    opt.zero_grad(); loss.backward(); opt.step()


def soft_topk(s, tau=0.5):
    top = s.topk(K + 1, dim=1).values.detach()
    theta = 0.5 * (top[:, K - 1] + top[:, K])
    w = torch.sigmoid((s - theta[:, None]) / tau)
    return 0.98 * w / w.sum(1, keepdim=True)


def stage2(net, opt, N, B=4, H=8):
    bs = [batch(B, N) for _ in range(H)]
    h = torch.zeros(B, N)
    total = 0
    for b in bs:
        acct = torch.stack([h, (h > 0).float(), b["kb"], b["ks"], torch.zeros_like(h), torch.zeros_like(h)], -1)
        w = soft_topk(net(b, acct))
        cost = ((w - h).clamp(min=0) * b["kb"] + (h - w).clamp(min=0) * b["ks"]).sum(1)
        g = (w * b["R"]).sum(1)
        total = total + torch.log1p(-cost) + torch.log1p(g) - 2.0 * (w ** 2 * 0.0009).sum(1)
        h = w * (1 + b["R"]) / (1 + g[:, None])
    loss = -total.mean()
    opt.zero_grad(); loss.backward(); opt.step()


def sample_pl(logits, country, G, cap=6):
    """Masked Plackett-Luce: G samples of K names each, at most `cap` per country. Returns (picks, logp)."""
    B, N = logits.shape
    lg = logits[:, None].expand(B, G, N)
    taken = torch.zeros(B, G, N, dtype=torch.bool)
    counts = torch.zeros(B, G, 30)
    cty = country[:, None].expand(B, G, N)
    logp, picks = 0, []
    for _ in range(K):
        full = counts.gather(2, cty) >= cap
        l = lg.masked_fill(taken | full, -1e9)
        lp = F.log_softmax(l, -1)
        i = torch.multinomial(lp.exp().reshape(B * G, N), 1).reshape(B, G)
        logp = logp + lp.gather(2, i[..., None])[..., 0]
        taken = taken.scatter(2, i[..., None], True)
        counts = counts.scatter_add(2, country.gather(1, i)[..., None], torch.ones(B, G, 1))
        picks.append(i)
    return torch.stack(picks, -1), taken, logp


def stage3(net, opt, N, B=32, G=128):
    b = batch(B, N)
    h = torch.zeros(B, N)
    h[:, :K] = 0.98 / K
    acct = torch.stack([h, (h > 0).float(), b["kb"], b["ks"], torch.zeros_like(h), torch.zeros_like(h)], -1)
    s = net(b, acct)
    _, chosen, logp = sample_pl(s, b["c"], G)
    w = chosen.float() * (0.98 / K)
    keep = chosen & (h[:, None] > 0) & ((h[:, None] - 0.98 / K).abs() <= 0.3 * 0.98 / K)
    w = torch.where(keep, h[:, None].expand_as(w), w)                       # drift band for kept names
    hh = h[:, None]
    cost = ((w - hh).clamp(min=0) * b["kb"][:, None] + (hh - w).clamp(min=0) * b["ks"][:, None]).sum(-1)
    r = torch.log1p(-cost) + torch.log1p((w * b["R"][:, None]).sum(-1))
    adv = r - (r.sum(1, keepdim=True) - r) / (G - 1)
    adv = adv / (adv.std() + 1e-8)
    loss = -(adv.detach() * logp).mean()
    opt.zero_grad(); loss.backward(); opt.step()


def stage3_multiweek(net, N, G=128, H=8):
    """Forward cost only: each of G members rolls its own holdings for H weeks (one group)."""
    with torch.no_grad():
        for _ in range(H):
            b = batch(G, N)
            net(b, torch.zeros(G, N, 6))


def timeit(fn, reps):
    fn()
    t = time.perf_counter()
    for _ in range(reps):
        fn()
    return (time.perf_counter() - t) / reps


if __name__ == "__main__":
    torch.set_num_threads(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
    for temporal in ("mlp", "gru"):
        net = Net(temporal)
        opt = torch.optim.AdamW(net.parameters(), lr=1e-4)
        print(f"\n[{temporal} temporal encoder] {sum(p.numel() for p in net.parameters()):,} parameters, "
              f"{torch.get_num_threads()} threads")
        for N in (245, 1000):
            t1 = timeit(lambda: stage1(net, opt, N), 5)
            t2 = timeit(lambda: stage2(net, opt, N), 3)
            t3 = timeit(lambda: stage3(net, opt, N), 2)
            t4 = timeit(lambda: stage3_multiweek(net, N), 1)
            print(f"  N={N:5d}  stage1 step (8 weeks) {t1:6.3f}s | stage2 step (4 rollouts x 8 wks) {t2:6.3f}s | "
                  f"stage3 step (32 weeks x 128 samples) {t3:6.2f}s | stage3 8-week group fwd (128 members) {t4:6.2f}s")
