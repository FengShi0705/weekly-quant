# GRPO (Group Relative Policy Optimization) for a weekly long-only stock-portfolio policy: the algorithm, finance applications to Oct 2026, and how well it fits

Scope note: the literature search covered arXiv (full-text reads of the main papers through the arXiv API/PDFs) plus web search, up to 18 Oct 2026. "Preprint" means arXiv only, with no peer-reviewed venue found. arXiv abstract search will miss papers that mention GRPO only in the body, and SSRN was not searched.

---

## Q1. What exactly is GRPO, and what problems do the later variants (Dr. GRPO, DAPO, GSPO, no-std GRPO) fix?

### Takeaway
GRPO is PPO without a critic. For each prompt/state q it samples G outputs from the old policy and scores each one. The baseline is the group's mean reward, and DeepSeekMath also divides by the group's standard deviation. It then keeps PPO's clipped importance-ratio surrogate and adds a KL penalty (k3 estimator) to a frozen reference policy. Later work found that the per-sample length normalisation and the std normalisation bias the gradient. Dr. GRPO, RLOO and "no-std GRPO" fix this and become (near-)unbiased REINFORCE with a leave-one-out-style baseline. DAPO targets entropy collapse and zero-signal groups, and GSPO targets the variance of token-level importance ratios. The std-normalisation bias matters most for finance: in stochastic-outcome settings it has been shown to cause overconfident, collapsed policies.

### Cited Findings
**Original GRPO (DeepSeekMath, Feb 2024, arXiv technical report)**
- GRPO is presented as a PPO variant that "obviates the need for additional value function approximation as in PPO, and instead uses the average reward of multiple sampled outputs, produced in response to the same question, as the baseline." For each question q it samples outputs {o_1..o_G} from π_θold. — [DeepSeekMath, arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- Objective (eq. 3): J(θ) = E[q, {o_i}~π_old] (1/G) Σ_i (1/|o_i|) Σ_t { min( ρ_{i,t} Â_{i,t}, clip(ρ_{i,t}, 1−ε, 1+ε) Â_{i,t} ) − β·D_KL[π_θ‖π_ref] }, with ρ_{i,t} = π_θ(o_{i,t}|q,o_{i,<t}) / π_old(o_{i,t}|q,o_{i,<t}). The KL is added to the loss directly, not folded into the reward as in PPO-RLHF, "avoiding complicating the calculation of Â". — [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- KL estimator (eq. 4, citing Schulman 2020): D_KL = π_ref/π_θ − log(π_ref/π_θ) − 1, described as "guaranteed to be positive" (this is the "k3" estimator). — [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- Outcome-supervision advantage: every token of output i gets Â_{i,t} = (r_i − mean(r)) / std(r). The process-supervision variant normalises step rewards and sums the normalised rewards of later steps. — [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- "Iterative GRPO" (Algorithm 1) resets the reference model to the current policy at each outer iteration and retrains the reward model with 10% replay. — [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- DeepSeekMath-RL hyperparameters: policy learning rate 1e-6, KL coefficient 0.04, 64 samples per question, max length 1024, batch size 1024. "The policy model only has a single update following each exploration stage." — [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- On-policy (π_θ = π_old), the clipped estimator reduces to the vanilla policy gradient. Clipping only does anything when several gradient steps reuse one batch of samples. — [Bereket & Leskovec, arXiv 2508.11800](https://arxiv.org/abs/2508.11800)

**DeepSeek-R1 (Jan 2025; peer-reviewed, Nature 645:633–638, 2025)**
- R1-Zero and R1 stage-1 RL used GRPO with learning rate 3e-6, KL coefficient 0.001, temperature 1, 16 outputs per question (max 32,768 tokens, later 65,536), 32 questions per step (batch 512), and the reference model replaced by the latest policy every 400 steps. Each rollout of 8,192 outputs is split into 16 minibatches trained for a single inner epoch. Stage-1 used a GRPO clip ratio ε = 10, and the authors note that "a lower value can lead to the truncation of gradients for a significant number of tokens… while a higher value may cause instability." — [DeepSeek-R1, arXiv 2501.12948 / Nature](https://arxiv.org/abs/2501.12948)

**Dr. GRPO ("Understanding R1-Zero-Like Training", Mar 2025, preprint)**
- The authors find two biases. (1) A *response-level length bias* from dividing by |o_i|: for positive advantages, short correct answers get larger per-token updates, and for negative advantages, long wrong answers are penalised less, so length grows. (2) A *question-level difficulty bias* from dividing by std(R): questions with low reward std (very easy or very hard) get more weight. GRPO's objective "is equivalent to a reweighted version of the unbiased advantage Ã_{i,t} = R(q,o_i) − mean(R)." — [Liu et al., arXiv 2503.20783](https://arxiv.org/abs/2503.20783)
- Dr. GRPO removes both the 1/|o_i| and std normalisations, replacing the per-sample masked mean with a constant such as the generation budget (MAX_TOKENS). The authors also found the length bias in several open-source PPO implementations. — [arXiv 2503.20783](https://arxiv.org/abs/2503.20783)

**DAPO (Mar 2025, preprint; open-source system on verl)**
- The authors report that naive GRPO suffers "entropy collapse, reward noise" and instability. They propose four fixes. **Clip-Higher** decouples ε_low = 0.2 from ε_high = 0.28 so low-probability tokens can grow. **Dynamic Sampling** over-samples and filters out prompts whose group accuracy is all-1 or all-0, since those have zero advantage. **Token-level PG loss** averages over all tokens in the batch rather than per sample. **Overlong reward shaping** is the fourth. — [Yu et al., arXiv 2503.14476](https://arxiv.org/abs/2503.14476)
- DAPO removes the KL term entirely: during long-CoT training "the model distribution can diverge significantly from the initial model, thus this restriction is not necessary." Hyperparameters were AdamW at a constant learning rate of 1e-6, 16 responses per prompt, and a mini-batch of 512 giving 16 gradient updates per rollout step. — [arXiv 2503.14476](https://arxiv.org/abs/2503.14476)

**GSPO (Qwen, Jul 2025, preprint)**
- GSPO argues that GRPO's token-level importance weights are "ill-posed" and inject "high-variance noise", leading to "catastrophic and irreversible model collapse", especially in MoE models. It instead uses a sequence-level, length-normalised ratio s_i(θ) = (π_θ(y_i|x)/π_old(y_i|x))^{1/|y_i|} with sequence-level clipping. The group-normalised advantage (r − mean)/std is unchanged. Clipping ranges were 3e-4 (left) and 4e-4 (right). — [Zheng et al., arXiv 2507.18071](https://arxiv.org/abs/2507.18071)

**Std normalisation under stochastic outcomes (most relevant to finance)**
- In verifiable domains with *stochastic* outcomes (synthetic Bernoulli tasks and CRISPR-screen outcomes), GRPO "induces overconfident probability predictions", while PPO, RLOO and GRPO without std normalisation are well calibrated. ECE was 0.239 for GRPO vs 0.002 for GRPO-no-std on synthetic data, and 0.292 vs 0.036 on CRISPR. — [Bereket & Leskovec, arXiv 2508.11800](https://arxiv.org/abs/2508.11800)
- In that setup every member of the group is scored against *the same observed stochastic outcome* a, which mirrors one realised market week. The authors derive E[Â_no-std] = ((G−1)/G)·A(q, p̂), which is unbiased up to a constant. With std normalisation the expected advantage carries 1/(σ_1+ϵ) and 1/(σ_0+ϵ) weights: a "policy-dependent bias that pushes policies towards overconfident predictions", and the bias grows as the policy concentrates. — [arXiv 2508.11800](https://arxiv.org/abs/2508.11800)
- RLOO's advantage is r_i − mean(r_{j≠i}) (leave-one-out baseline). REINFORCE-style RLOO variants outperformed PPO, DPO and RAFT in RLHF, and "many components of PPO are unnecessary in an RLHF context." — [Bereket & Leskovec table, arXiv 2508.11800](https://arxiv.org/abs/2508.11800); [Ahmadian et al., "Back to Basics", arXiv 2402.14740](https://arxiv.org/abs/2402.14740)

**Theory and KL implementation**
- With binary verifiable rewards, GRPO's mean+variance calibration "induces a weighted contrastive loss in which the contrastive samples are synthetic data drawn from the previous policy." The paper analyses mean-only vs mean+variance normalisation and KL to the previous model vs a fixed reference, and proves that the probability of success converges to a fixed point above the reference ("success amplification"). It is listed by IBM Research as an ICML 2026 paper. — [Mroueh, arXiv 2503.06639](https://arxiv.org/abs/2503.06639); [IBM Research listing](https://research.ibm.com/publications/reinforcement-learning-with-verifiable-rewards-grpos-loss-dynamics-and-success-amplification)
- "'k3 as loss' (like in GRPO) is merely a first-order, biased approximation of the principled loss" for reverse-KL regularisation. "k1 in reward" (PPO-style) and, on-policy, "k2 as loss" are the gradient-correct implementations, and off-policy "k_n as loss" needs an importance-sampling correction. — [arXiv 2510.01555](https://arxiv.org/abs/2510.01555) (preprint)
- GR2PO, a continuous-control robotics variant, notes that critic-free group methods "fail to learn long-term action outcomes when directly applying immediate rewards" in dense-reward settings. It instead estimates discounted returns from parallel trajectories and "performs group normalization at each rollout time index." — [Wang et al., arXiv 2609.19850](https://arxiv.org/abs/2609.19850) (preprint, Sep 2026)

### Inferences
- **What carries over to portfolios.** Under on-policy updates (μ = 1, as in DeepSeekMath), GRPO is REINFORCE with a per-state group-mean baseline, optional per-state std scaling, and an explicit KL-to-reference term. Clipping and the importance ratio only matter if each sampled batch gets several gradient steps.
- **Length bias is irrelevant for fixed-dimension actions.** Dr. GRPO's length fix matters only if the policy emits variable-length text (an LLM).
- **The std-normalisation bias is directly relevant.** Its weekly analogue is a "week-dispersion bias" (Q5), and Bereket's same-outcome setup is structurally the market case. The safe default is no-std (Dr. GRPO/RLOO). An alternative is a *global* scale: a running or batch-level std across all weeks rather than a per-week std.
- **DAPO's fixes transfer partly.** Dynamic sampling, i.e. dropping states where all group rewards are equal, is cheap and sensible. Clip-higher addresses premature entropy collapse; in a portfolio bandit, collapse is also the in-sample optimum (Q4/Q5), so explicit entropy or KL control matters more than clip asymmetry.
- **GSPO's insight has a direct analogue.** A policy over 1,000–3,000 assets has a joint log-probability that sums thousands of per-dimension terms, just as long sequences do. Per-dimension (geometric-mean) normalised ratios or strictly on-policy updates avoid exploding importance ratios.

### Gaps
- Peer-review status of Dr. GRPO, DAPO, GSPO and RLOO was not verified; arXiv metadata lists no journal ref for them.
- No paper tested std-vs-no-std GRPO *on financial returns*. The calibration result comes from Bernoulli and biology outcomes, and its transfer to continuous-return rewards is inferred, not shown.

---

## Q2. Which papers apply GRPO or similar critic-free group-relative policy gradients to trading, portfolio management, stock selection or quant finance? Results, data, horizon, costs, credibility

### Takeaway
By Oct 2026 there are about ten trading or portfolio GRPO papers, all preprints except one 3-page IEEE conference paper. Most fine-tune a 1–8B LLM (Qwen3/Llama) whose "action" is text: a rating, a factor subset, a ranking of 15 ETFs, or 5 ETF weights. Rewards come from realised forward returns. Evaluations are mostly weak: 3–12-month test windows, frequent absence of costs, tiny universes, and possible look-ahead through LLM pretraining. The best-designed one (FinRankGRPO: 314 test weeks, 5 bps costs, post-cutoff check) shows only a modest gain over equal-weight. I found **no** GRPO paper on a weekly long-only top-K portfolio over a 1,000–3,000-stock universe. The non-LLM GRPO trading papers (FinRL NASDAQ-100, BTC 1-minute, LOB HFT) are exploratory. The older critic-free portfolio literature (REINFORCE with Dirichlet policies; deterministic gradients through returns) is the more relevant precedent. Its strongest negative result: REINFORCE portfolios ended up statistically indistinguishable from 1/N.

### Cited Findings
**A. GRPO applied to trading/portfolio decisions (chronological)**

| Paper (status) | Policy / action | Reward | Data, split | Costs | Headline result | Credibility flags |
|---|---|---|---|---|---|---|
| A New DAPO Algorithm for Stock Trading (May 2025; IEEE IDS 2025, 3-page short paper; 2nd in FinRL Contest 2025 Task 1) — [arXiv 2505.06408](https://arxiv.org/abs/2505.06408) | Non-LLM FinRL agent. The state holds cash, prices, holdings, technical indicators and pre-extracted LLM sentiment/risk; actions are buy/sell/hold per stock. "For each state s_t, the policy samples a group of n potential actions", with advantage (r−μ)/(σ+ϵ). | One-period portfolio return, multiplied by sentiment^α / risk^β factors (0.99–1.01 per score) | NASDAQ-100, FNSPID news 1999–2023; trained on 6 years; test 2020–2023 | Not specified in paper | 230.49% cumulative, IR 0.37, MDD −49.11%, CVaR5% −5.64%, vs CPPO-DeepSeek ~215% / ~−35% MDD. Training 2.5 h vs ~7–8 h. | Single path, no CIs, deeper drawdown than baseline, reward mixes LLM sentiment into returns |
| Trading-R1 (Sep 2025, preprint) — [arXiv 2509.11420](https://arxiv.org/abs/2509.11420) | Qwen3-4B. SFT + GRPO in a 3-stage curriculum; writes a thesis, then a 5-class rating (Strong Sell…Strong Buy) per asset-day | Structure + evidence + decision. The decision label comes from 3/7/15-day EMA forward returns ÷ 20-period volatility, weighted 0.3/0.5/0.2, cut at asymmetric quantiles (85/53/15/3%) | Tauric-TR1-DB: 100k samples, 14 tickers, Jan 2024–May 2025. Backtest Jun 1–Aug 31 2024 on AAPL, GOOGL, AMZN, SPY etc., described as "excluded from the training data" | None mentioned | NVDA Sharpe 1.88, return 8.08%. AAPL Sharpe 1.80 vs GPT-4.1 1.24. | ~3-month test (~13 weekly obs). Test window lies inside the corpus date span. Authors admit "a structural long bias" from bullish 2024–25 large-cap AI names. |
| News-Aware Direct Reinforcement Trading (Oct 2025, preprint) — [arXiv 2510.19173](https://arxiv.org/abs/2510.19173) | **Non-LLM** MLP/RNN/LSTM/Transformer policies. DDQN vs GRPO with *mean-only* advantage r_i − mean(r); 3 actions (short / long one BTC / …) | Trading return | BTC/USDT 1-minute bars plus Yahoo news, Dec 2019–Jan 2024. Train/val then last ~15% as test. Evaluated on 256 sampled 3,000-minute windows plus a full backtest. | None found in text | Beats BTC buy-and-hold on the test set | High frequency, no costs, single asset |
| Alpha-R1 (Dec 2025, v2, preprint) — [arXiv 2512.23515](https://arxiv.org/abs/2512.23515) | Qwen3-8B "semantic gating": picks ≤10 factors from a 40-factor pre-screened Alpha101 pool given an LLM market-state description. Factors feed a linear model → top-10 equal-weight long-only, holding period H = 5 days. | Realised execution-adjusted portfolio return, penalised by an LLM judge (Claude 3.5 Haiku) score and a structural validity penalty | Factor coefficients estimated 2020–23, RL training 2024, test 2025. S&P 500 and CSI 300, with transfer to Russell 2000 and CSI 1000. Point-in-time constituents. | Double-sided 10 bps, first-30-min VWAP | S&P 500 AR 47.87%, excess SR 1.62 (buy-and-hold 19.34% / 0.80). CSI 300 40.57% / 2.23. Without RL: 12.85% / 0.47 and 15.44% / 0.79. Transfer: R2000 80.54% / 2.46, CSI 1000 73.52% / 2.80. GRPO settings: G = 8, ε = 0.2, β = 0.001, lr 1e-6, 2 epochs, 64 H800 GPUs × ~120 h. | One test year (~50 weekly obs). Returns are extraordinary, and the authors' own TopN heatmap reaches 176% AR at TopN = 2–3 (high variance). Authors note the comparison vs zero-shot LLMs "does not by itself isolate how much of the gain comes from the RL algorithm." |
| Trade-R1 (Jan 2026, v2, preprint) — [arXiv 2601.03948](https://arxiv.org/abs/2601.03948) | Qwen3-8B; asset selection from daily news (15 "investment style beliefs" per day). GRPO G = 8, lr 1e-6, batch 32. | 10-day forward excess return vs CSI 300, gated by a RAG "triangular consistency" score s: FSR = r + 2s; DSR = α(s,r)·r with α = 0.5+s if r>0, else 2−s | A-shares: train Jul 2024–Jun 2025, test Jul–Oct 2025. US used as test-only. | None mentioned | A-share: DSR 37.76% cum, SR 3.04; Market-only 37.62%; untrained Qwen3-8B 32.60%; index 17.91%. **US: untrained base 16.90% beat DSR 15.34%, Market-only 12.63% and FSR 11.40%.** "Market-only" reward caused reward hacking (hallucination rate 0.225 vs 0.019 for the base model). | 4-month test, no costs, overlapping 10-day labels. RL variants failed to transfer to the US market. |
| DeepSeekMath Meets Order Book (May 2026, preprint) — [arXiv 2605.25527](https://arxiv.org/abs/2605.25527) | **Non-LLM** PPO / GRPO / GSPO policies on an order-flow-imbalance state from a frozen forecaster | Spread-scaled directional PnL with downside-aware shaping | LOBSTER Level-10 data: AAPL 400k, AMZN 270k, GOOG 148k points, from selected ticker-dates | Explicit costs/slippage listed as future work | GRPO/GSPO beat tabular Q-learning on net average PnL and drawdown | Authors: no repeated seeds or bootstrap CIs; results "indicative rather than conclusive" |
| FinSMART (Jul 2026, preprint) — [arXiv 2607.28127](https://arxiv.org/abs/2607.28127) | Llama-3-8B-Instruct sentiment model trained by GRPO with KL to a frozen reference | "Discrete asymmetric trading reward" from realised (idiosyncratic and market) returns | Daily long–short (35%) S&P 500 portfolios, point-in-time universe; out-of-sample Jan 2019–Jun 2021 | No transaction costs found in text | Claims +220% cumulative return over the strongest baseline | Daily long-short with no costs; 2.5-year test |
| FinATOM (Aug 2026, preprint) — [arXiv 2608.09880](https://arxiv.org/abs/2608.09880) | Llama-3.2-1B + LoRA emits **5 long-only ETF weights as grid tokens**. SFT imitates a causal mean–variance "anchor", then "DAPO-augmented GRPO" (asymmetric clip, token-level update, G = 8, **no reference-KL**, "behavior-KL stop") | Realised 21-day Sharpe plus an anchor-consistency term | ETF tests 2023–2025 | 5 bps | Pooled gross Sharpe 1.428 → 1.529; net 1.394 → 1.494. Advantage "clearest" in 2025. | 5 assets, 3 test years, modest gain |
| FinRankGRPO (Sep 2026, v2 13 Oct 2026, preprint) — [arXiv 2609.24175](https://arxiv.org/abs/2609.24175) | Qwen3-4B(-Instruct) generates a **full permutation of 15 ETFs weekly** from news. Rankings → Entropy Pooling → long-only max-Sharpe. GRPO with std-normalised advantage, **4 responses per prompt**, lr 3e-6, 1 epoch. | σ(Spearman ρ) when ρ > 0 (piecewise), −1 for structural errors | Train 2010–2019 (2,516 rolling-week instances); test 2020–2025 (**314 non-overlapping weeks**); mean of 5 trials. Extra post-cutoff test Jun–Dec 2025. | 5 bps per unit turnover | Sharpe 0.689, ann. return 13.1%, mean Spearman 0.018 vs equal-weight 0.502 / 11.9%, SFT-only 0.532, DeepSeek-Chat 0.560. A GRPO baseline with exact-match reward got 0.436, because the exact-match reward "assigns zero reward to every sampled completion." Post-cutoff: SR 1.159 vs GPT-4o-mini 0.953. On a 24-stock universe: SR 0.586 vs 0.540. | Abstract (0.636 Sharpe / 0.023 Spearman) disagrees with the main table (0.689 / 0.018). Tiny universe and IC. 2020–24 test news overlaps Qwen3 pretraining, partly addressed by the post-cutoff test. Best-designed evaluation in this set. |

**B. GRPO in finance but not producing trades (context only)**
- Fin-R1: Qwen2.5-7B, SFT then GRPO on 60,091 distilled CoT samples; financial QA (ConvFinQA 85.0, FinQA 76.0), not trading. — [arXiv 2503.16252](https://arxiv.org/abs/2503.16252); [HF model card](https://huggingface.co/SUFE-AIFLM-Lab/Fin-R1/blob/refs%2Fpr%2F1/README_en.md)
- DianJin-R1: GRPO with format and correctness rewards on CFLUE/FinQA/compliance QA. — [arXiv 2504.15716](https://arxiv.org/abs/2504.15716)
- FinZero: multimodal financial time-series forecasting with "Uncertainty-adjusted GRPO" (UARPO). — [arXiv 2509.08742](https://arxiv.org/abs/2509.08742)
- DualCast: an LLM forecast-reviser trained with a "return-space group relative policy optimization objective that rewards improvements over the fast forecast"; equities and energy, at 5-minute, daily and weekly horizons. — [arXiv 2609.38197](https://arxiv.org/abs/2609.38197)
- "Time-R1" names two unrelated papers: a general temporal-reasoning LLM, and a time-series forecasting LLM using "GRIP (group-based relative importance for policy optimization)". Neither is a trading paper. — [arXiv 2505.13508](https://arxiv.org/abs/2505.13508); [arXiv 2506.10630](https://arxiv.org/abs/2506.10630)
- AlphaDiverse: joint GRPO for local Planner/Realizer agents doing alpha-factor mining on four Chinese stock universes, with research feedback kept to an inner period and evaluation on a later outer period. — [arXiv 2609.29014](https://arxiv.org/abs/2609.29014)
- Mint-Agent: finance agent models trained with SFT, on-policy distillation and RLVR; benchmark (not trading) results. — [arXiv 2608.16386](https://arxiv.org/abs/2608.16386)

**C. Critic-free / direct policy-gradient portfolio precedents (non-GRPO)**
- **Dirichlet REINFORCE (André & Coqueret, preprint, q-fin.PM).** Dirichlet policies give "closed forms for the policy gradients", implemented with REINFORCE on US equities (monthly, Jan 2000–Jun 2020, 12 firm characteristics, linear policy). "RL-based portfolios are very close to the equally-weighted (1/N) allocation". t-tests of RL vs 1/N returns gave p-values between 0.82 and 0.998. "The only robust conclusion is that bootstrap sequences perform better than sequential ones." — [arXiv 2011.05381](https://arxiv.org/abs/2011.05381)
- **EIIE (Jiang, Xu & Liang 2017, preprint).** Deterministic policy gradient on crypto portfolios (30-minute periods, 0.25% commission). It assumes "zero slippage" and "zero market impact", under which the immediate reward "can be regarded as the action-value function of action w_t with a discounted factor of 0." This justifies "full-exploitation" with no exploration; the reward is the average log return. — [arXiv 1706.10059](https://arxiv.org/abs/1706.10059)
- **Zhang, Zohren & Roberts 2020.** An LSTM (64 units) with a softmax long-only output directly maximises the Sharpe ratio by gradient ascent through realised returns, on 4 ETFs (VTI, AGG, DBC, VIX). Test 2011–Apr 2020 with 2-yearly retraining, transaction costs and volatility scaling in the test. They note their model accumulates larger transaction costs than reallocation strategies. Published in J. Financial Data Science (DOI 10.3905/jfds.2020.1.042 per the arXiv listing). — [arXiv 2005.13665](https://arxiv.org/abs/2005.13665); [search result on DOI](https://www.arxiv.org/abs/2005.13665v2)
- **Moody & Saffell (2001), "direct reinforcement".** Actor-only RL with recurrent networks, optimising trading performance functions directly. — [IEEE TNN 12(4), DOI 10.1109/72.935097](https://doi.org/10.1109/72.935097); described in [arXiv 2510.19173 related work](https://arxiv.org/abs/2510.19173)

### Inferences
- **No direct precedent exists for this problem** (GRPO on a weekly long-only top-10–20 portfolio from 1,000–3,000 global stocks, with retail costs). LLM-based GRPO papers sidestep the large universe by acting on tiny universes (5–15 ETFs, 6–14 tickers) or by selecting *factors*, not stocks (Alpha-R1).
- **Statistical power is low.** Under the standard iid approximation, SE(annualised Sharpe) ≈ √((1 + SR²/2)/years). For true SR near 0–1 that gives roughly ±2 for a 3-month test (Trading-R1), ±1.7 for 4 months (Trade-R1), ±1 for one year (Alpha-R1) and ±0.4 for six years (FinRankGRPO). The errors are larger when the reported SR is high (e.g. ≈±4 for SR ≈ 3 over 4 months). Only FinRankGRPO's window is long enough to say anything, and its Sharpe gain over equal-weight (~0.19) is within about 1 SE on an unpaired basis.
- **Two ablations show how fragile market-return rewards are.** Trade-R1's US result (RL below the untrained base) and Alpha-R1's TopN sensitivity both point to overfitting of a single realised path (Q5).
- **The highest-quality evidence on critic-free portfolio policy gradients is negative** (Dirichlet REINFORCE ≈ 1/N). The successful end-to-end precedents (EIIE, Zhang et al.) use *deterministic* gradients through returns, not sampling.

### Gaps
- Trading-R1's exact GRPO hyperparameters (group size, β) were not extracted. It is unclear whether its per-asset label quantiles were computed on data including the test window.
- FinSMART and DAPO-stock cost assumptions could not be confirmed. Neither text states transaction costs explicitly.
- No GRPO portfolio paper from SSRN, journals or industry blogs was found. Coverage of non-arXiv venues is incomplete.

---

## Q3. How does a weekly portfolio problem map onto GRPO's ingredients, and which stochastic policy parameterisations (with log-probabilities) can be used?

### Takeaway
Mapping: prompt q ↔ week-t state (features of the N_t stocks plus current holdings). Output o ↔ a sampled portfolio. Group ↔ G portfolios sampled for that same week. Reward ↔ next-week net return of each sampled portfolio. Every portfolio's reward can be computed counterfactually from the realised return vector, so sampling the group needs no simulator. For "hold 10–20 of 1,000–3,000 names", the natural policy is a Plackett–Luce (PL) / Gumbel-top-K sampler over learned scores, with a closed-form ordered log-probability. Dirichlet and logistic-normal (Gaussian-softmax) policies suit continuous simplex weights but fit sparsity poorly. All of these have reparameterised alternatives that make the score-function estimator unnecessary.

### Cited Findings
- Dirichlet portfolio policies have closed-form policy gradients and were implemented with REINFORCE for factor portfolios. — [André & Coqueret, arXiv 2011.05381](https://arxiv.org/abs/2011.05381)
- Dirichlet (and Gamma, Beta, von Mises) samples admit low-variance *implicit reparameterisation gradients*, avoiding the score-function estimator. — [Figurnov, Mohamed & Mnih, NeurIPS 2018, arXiv 1805.08498](https://arxiv.org/abs/1805.08498)
- Zhang et al. use a deterministic softmax output layer for long-only weights and differentiate the Sharpe ratio through realised returns. — [arXiv 2005.13665](https://arxiv.org/abs/2005.13665)
- Sampling without replacement for discrete variables. Kool et al. derive an unbiased "unordered set" estimator: a Rao-Blackwellisation of three estimators whose built-in control variate costs no extra model evaluations. "By sampling without replacement, the unordered set estimator forces the estimator to compare different alternatives, and reinforces the best among them." The Gumbel-top-k trick draws k items without replacement. — [Kool, van Hoof & Welling, ICLR 2020, arXiv 2002.06043](https://arxiv.org/abs/2002.06043); [workshop precursor "Buy 4 REINFORCE samples, get a baseline for free"](https://mlanthology.org/iclrw/2019/kool2019iclrw-buy)
- PL ranking models are "fully differentiable", but exact gradients of ranking metrics need all permutations. PL-Rank exploits PL structure to get better sample efficiency than generic policy gradients, and PL-Rank-3 reaches complexity comparable to sorting. — [Oosterhuis, SIGIR 2021, arXiv 2105.00855](https://arxiv.org/abs/2105.00855); [PL-Rank-3, arXiv 2204.10872](https://ar5iv.labs.arxiv.org/html/2204.10872)
- LLM GRPO papers map the output to text or tokens. FinRankGRPO's action is a full permutation of 15 ETFs, rewarded by Spearman ρ against the realised ordering. FinATOM emits 5 weights as constrained grid tokens. Alpha-R1 emits a factor subset that is then turned into a top-10 equal-weight portfolio. — [arXiv 2609.24175](https://arxiv.org/abs/2609.24175); [arXiv 2608.09880](https://arxiv.org/abs/2608.09880); [arXiv 2512.23515](https://arxiv.org/abs/2512.23515)
- In the non-LLM DAPO-stock agent, GRPO samples n candidate actions per state and scores each by its one-period portfolio return, i.e. counterfactual evaluation in a price-taker environment. — [arXiv 2505.06408](https://arxiv.org/abs/2505.06408)

### Inferences
**Ingredient mapping (a non-LLM transformer policy over the cross-section)**
- **State.** s_t = (X_t, h_t). X_t holds per-stock features for the N_t eligible names (a set, so a transformer without positional order fits) plus market features. h_t is current holdings after drift: h_t = w_{t−1} ⊙ (1+R_t) / (1 + w_{t−1}·R_t).
- **Action.** Either (a) simplex weights w_t ∈ Δ^{N−1} (long-only), or (b) a set S_t of K names with equal weights (K = 10–20).
- **Group.** For each training week, draw a_1..a_G ~ π_θold(·|s_t).
- **Reward.** r_i = w(a_i)·R_{t+1} − c·‖w(a_i) − h_t‖₁ (proportional cost c ≈ 0–0.65% of traded value), optionally a log or risk-adjusted version.
- **No prompt diversity issue.** Every historical week is a "prompt". There are ~1,000 such prompts in 20 years, with one realised outcome each.

**Parameterisations and their log-probabilities**
1. **Dirichlet.** w ~ Dir(α(s)), α_i = softplus(f_θ(x_i)) + ε, α₀ = Σα_i.
   `log p(w) = log Γ(α₀) − Σ_i log Γ(α_i) + Σ_i (α_i − 1) log w_i`;  `∂ log p/∂α_i = ψ(α₀) − ψ(α_i) + log w_i`.
   Mean α_i/α₀; Var = α_i(α₀−α_i)/(α₀²(α₀+1)), so the concentration α₀ couples mean and exploration noise. Problems at N ≈ 3,000: samples are dense (no exact zeros, hence no 10–20-name portfolios). Sparse-looking samples need α_i ≪ 1, which makes log w_i hugely negative or underflow, so the log-prob and its gradient become numerically unstable. The joint log-ratio sums N terms, so importance ratios blow up off-policy. A workable variant is a two-stage policy (choose the K-set, then a K-dimensional Dirichlet over weights). Implicit reparameterisation allows a pathwise gradient instead.
2. **Logistic-normal ("Gaussian-softmax").** z = μ_θ(s) + σ⊙ε, w = softmax(z) or a masked softmax over the top-K of z. Treat **z** as the action: `log p(z) = −Σ_i (z_i − μ_i)²/(2σ_i²) − Σ_i log σ_i − (N/2) log 2π`. This needs no softmax Jacobian, because the reward is a deterministic function of z and the score-function estimator is valid for the latent. With fixed σ, the ratio is exp(Σ_i[(z_i−μ_old,i)² − (z_i−μ_θ,i)²]/(2σ²)), again a sum over N dimensions. It is fully reparameterisable, so the pathwise gradient ∂r/∂μ = J_softmax(z)ᵀ R is available (Q4).
3. **Plackett–Luce / Gumbel-top-K over names (recommended if sampling).** Scores s_i = f_θ(x_i, h_t). Sample by adding iid Gumbel(0,1) noise to s_i/τ and taking the top K: an ordered PL draw without replacement. Ordered log-prob:
   `log p(i_1..i_K) = Σ_{k=1}^{K} [ s_{i_k}/τ − log Σ_{j ∉ {i_1..i_{k−1}}} exp(s_j/τ) ]`.
   This costs O(NK), or O(N + K) with a running log-sum-exp minus removed terms; use log-space subtraction to avoid cancellation when top scores dominate. Equal weights make the order irrelevant, so the reward depends only on the set. Using the *ordered* log-prob is still an unbiased score-function estimator on an augmented action. The unordered set probability p(S) sums over K! orderings (20! ≈ 2.4×10¹⁸), which is why Kool et al.'s unordered-set estimator is the lower-variance (but more complex) option. Temperature τ (or a learned scale) is the exploration knob. A PL policy can be **pretrained supervised** with a ListMLE-style likelihood of the realised ranking, which then gives a natural π_ref.
4. **Independent Bernoulli inclusion** (y_i ~ Bern(σ(s_i))): `log p(y) = Σ_i [y_i log σ(s_i) + (1−y_i) log(1−σ(s_i))]`. Simple, but K is random and the log-ratio sums N terms. A conditional-Poisson (fixed-K) version restores the constraint but loses the simple form.
5. **Hybrid for weighted top-K.** Use PL to choose S, then a Gaussian-softmax or Dirichlet over the K chosen names for weights. log p = log p_PL(S-order) + log p(weights | S).
- **KL to reference without the k3 estimator.** For PL, the KL between policy and reference can be computed exactly *per selection step* given the sampled prefix (categorical KL over the remaining names). For Gaussians with shared σ it is ‖μ − μ_ref‖²/(2σ²). Both avoid k3's bias (Q1).

### Gaps
- No paper compared Dirichlet vs PL vs logistic-normal policies for large-universe equity portfolios under GRPO. The numerical issues above are reasoned from the densities, not reported results.
- Kool et al.'s unordered-set estimator has not been tested on portfolio top-K selection in any source found.

---

## Q4. Price-taker structure: is this a contextual bandit plus a cost/holdings state, and when does GRPO beat simply differentiating portfolio return directly?

### Takeaway
A £10k account cannot move prices, so the action does not affect future market features. The only endogenous state is the holdings vector, and its transition is deterministic, known and differentiable almost everywhere. Without costs the problem is a **full-information contextual bandit**: the reward of *every* possible portfolio is known after the fact. With costs it is a contextual bandit coupled to a known, differentiable inventory state. GRPO then mostly becomes a Monte Carlo, higher-variance estimate of a gradient that can be computed exactly through the return (EIIE, Zhang et al., Moody & Saffell). The score-function noise grows roughly linearly with the number of assets. Sampling helps only where the objective or action is genuinely non-differentiable (hard top-K with equal weights, lot sizes, black-box execution, text outputs), or as deliberate smoothing or exploration of a non-convex objective.

### Cited Findings
- EIIE says it outright. Under "zero market impact" ("the capital invested … is so insignificant that is has no influence on the market"), the immediate reward "can be regarded as the action-value function of action w_t with a discounted factor of 0, taking no consideration of future influence of the action". Having a definite action-value "further justifies the full-exploitation approach, since exploration in other RL problems is mainly for trying out different classes of action-value functions." The framework can evaluate "different sequences of actions" on the "same segment of market history." — [Jiang et al., arXiv 1706.10059](https://arxiv.org/abs/1706.10059)
- EIIE still models transaction costs through the previous weights (Portfolio-Vector Memory) at a 0.25% commission. This is the "turnover state" that makes the problem not purely one-step. — [arXiv 1706.10059](https://arxiv.org/abs/1706.10059)
- Direct (deterministic) optimisation through realised returns: Zhang et al. "directly optimise the portfolio Sharpe ratio" and "circumvent the requirements for forecasting expected returns" by gradient ascent through softmax weights. — [arXiv 2005.13665](https://arxiv.org/abs/2005.13665); [Moody & Saffell 2001](https://doi.org/10.1109/72.935097)
- Monte Carlo gradient estimation falls into three families: pathwise, score-function and measure-valued, each with different assumptions and variance properties. — [Mohamed et al., JMLR 21(132) 2020, arXiv 1906.10652](https://arxiv.org/abs/1906.10652)
- Critic-free methods using immediate rewards "fail to learn long-term action outcomes" in dense-reward sequential settings. GR2PO fixes this with discounted returns from parallel trajectories, normalised per time index. — [arXiv 2609.19850](https://arxiv.org/abs/2609.19850)
- DAPO-stock in practice: the agent samples several candidate actions for the same state and scores them all with one-period returns. This is only possible because the environment's market path does not depend on the action. — [arXiv 2505.06408](https://arxiv.org/abs/2505.06408)

### Inferences
**Formal structure**
- Market features evolve as X_{t+1} ~ P(·|X_t), independent of w_t. Holdings evolve as h_{t+1} = drift(w_t, R_{t+1}), which is deterministic and known.
- Objective: J = Σ_t [ w_t·R_{t+1} − c‖w_t − h_t‖₁ ] (or a utility of it).
- With c = 0 the sum separates into independent weekly problems: a contextual bandit with **full counterfactual feedback**, since R_{t+1} reveals the payoff of every portfolio. There is no exploration–exploitation trade-off in the bandit sense. Stochasticity in the policy is purely an *optimisation device*, as the EIIE quote says.
- With c > 0, today's choice affects next week's cost through h. But h's dynamics are known and differentiable, so one can backpropagate through multi-week unrolled rollouts (backprop through time over H weeks) with no learned critic.

**GRPO vs exact gradient, linear (risk-neutral) reward, no costs**
- E_{w~π}[w·R] = μ_π(s)·R, where μ_π is the policy's mean portfolio. The exact gradient is ∇_θ μ_π(s)·R: a single backward pass with zero policy-sampling noise.
- GRPO estimates the same quantity as (1/G) Σ_i (r_i − r̄) ∇ log π(a_i|s). Example: logistic-normal policy with σ, reward locally linear r ≈ r(μ) + gᵀ(z−μ). The score term ((gᵀσε)(ε/σ)) = (gᵀε)ε has mean g and covariance ‖g‖² I + g gᵀ. Total variance ≈ (N+1)‖g‖², against ≈0 for the pathwise estimator.
- So with N = 3,000 names, a GRPO group of G samples has a relative noise² of ~N/G: ~190 for G = 16 and ~12 for G = 256 (signal ≈ noise only around G ≈ N) — just to approximate one exact gradient for that week. This noise adds to the market noise already in R_{t+1}.
- The PL/top-K policy has a comparable effective dimension. With equal weights and no costs, its expected reward is (1/K) Σ_i P_θ(i ∈ S) R_i, linear in the inclusion probabilities. So the "RL" problem is learning inclusion probabilities that correlate with realised returns. PL-Rank-style estimators or differentiable soft-top-K relaxations target this much more efficiently than generic GRPO sampling.

**When sampling-based policy gradient adds value**
1. The reward is non-differentiable in the action and no good relaxation exists: hard cardinality with equal weights *and* path-dependent fixed fees, integer lot sizes (with £500–1,000 positions, rounding is minor for most mid/large caps), or a black-box execution simulator with partial fills. Even here, relaxations (soft top-K, sparsemax, Gumbel-softmax straight-through) are worth trying first.
2. The policy is an LLM emitting text, the reason GRPO exists. Here the output is not differentiable, and the group baseline replaces a token-level critic.
3. Smoothing a rugged objective. E_π[u] is a Gaussian/PL-smoothed version of the realised P&L, akin to evolution strategies, and may escape poor local optima of piecewise objectives such as turnover-thresholded rules. A deterministic objective plus noise injection or ensembling can reproduce this.
4. Risk-averse or non-decomposable objectives (drawdown, Sharpe over a year) can be targeted with multi-week group trajectories. But these are also differentiable through an unrolled backtest (Zhang et al. differentiate Sharpe directly).

**When it is just a noisier estimator.** Smooth weight policies (softmax / sparsemax / Dirichlet means) with proportional costs and a return or utility reward: the direct pathwise gradient optimises the *same in-sample objective* with orders of magnitude less variance.

**Deployment mismatch.** GRPO optimises the expected reward of a *stochastic* policy, but one would deploy the mode (top-K by score) or the mean weights. With concave utilities or costs these differ, so validation must score the deterministic deployed policy.

**Turnover handling options**
- (i) Put h_t in the state and the cost in the one-step reward. This is myopic: the policy is charged today's cost but not credited for lower future costs. In practice it still learns "stay near current holdings".
- (ii) Group = G multi-week trajectories (H = 4–13 weeks) from the same start holdings, with H-week net return as reward and GR2PO-style per-time-index normalisation.
- (iii) A differentiable unroll with an L1 cost term. This is the cleanest option.

**Cost scale.** Replacing 2 of 20 equal-weight names per week trades ~20% of the portfolio weekly (~10.4× per year). At 0.65% per trade that is ≈6.8% per year of drag; at 0.1% it is ≈1%. For this account the cost/turnover term is first-order, and the holdings state cannot be ignored.

### Gaps
- No published head-to-head between GRPO and direct differentiable portfolio optimisation on the same equity data was found. The variance comparison above is analytical, not empirical.
- The literature on "exogenous/input-driven MDPs" (formalising action-independent market dynamics) was not retrieved, so it is not cited here.

---

## Q5. All samples in a group share the same realised market outcome: what does the group-relative advantage then measure, and how big is the single-path overfitting risk?

### Takeaway
Under a shared outcome R_{t+1}, the mean-centred advantage is exactly the return of a long–short portfolio: sample minus group-mean portfolio. For fully invested long-only portfolios, any return component common to all stocks cancels exactly, so the market move is removed. Differences in factor exposure (beta, size, sector) between samples still leak factor returns into the advantage. Without std normalisation, GRPO is an unbiased (×(G−1)/G) estimate of the gradient of the *realised-path* expected reward, the same in-sample objective a direct method optimises. Larger G therefore reduces policy-sampling noise but gives no protection against overfitting the one historical path of ~1,000 weeks; a stronger in-sample optimiser actually memorises realised winners more easily. Per-week std normalisation reweights weeks by inverse cross-sectional dispersion, and as the policy concentrates it amplifies updates toward collapse.

### Cited Findings
- Trade-R1 states the effect explicitly: "Group-wise normalization is crucial for financial time-series, as it effectively removes the non-stationary market trend (β), ensuring the model learns relative asset selection (α)". The authors model observed returns as r = r* + ξ (signal plus noise), argue that Var(ĝ_mkt) ∝ σ²_noise "prevents the optimizer from distinguishing between causal reasoning and random reward, leading to reward hacking", and observe reward hacking with a market-only reward. — [arXiv 2601.03948](https://arxiv.org/abs/2601.03948)
- Trade-R1's market-only-reward model scored well on the training market's test window (A-share 37.62%) but underperformed the untrained base model on US stocks (12.63% vs 16.90%). — [arXiv 2601.03948](https://arxiv.org/abs/2601.03948)
- With a shared stochastic outcome, mean-centred (no-std) group advantages give E[Â] = ((G−1)/G)·A (unbiased up to a constant). The std-normalised version has a policy-dependent bias toward overconfidence, which grows as the policy concentrates. — [arXiv 2508.11800](https://arxiv.org/abs/2508.11800)
- Dr. GRPO identifies std normalisation as a "difficulty bias" that upweights prompts with low reward spread. — [arXiv 2503.20783](https://arxiv.org/abs/2503.20783)
- FinRankGRPO: the realised weekly Spearman correlation between predicted and realised ETF rankings averaged only ~0.018 even for the best model, illustrating how faint the weekly cross-sectional signal is relative to noise. An exact-match reward gave zero advantage for every sampled completion. — [arXiv 2609.24175](https://arxiv.org/abs/2609.24175)
- Bootstrapped training sequences beat sequential ones for Dirichlet REINFORCE portfolios, and the learned policies stayed near 1/N. — [arXiv 2011.05381](https://arxiv.org/abs/2011.05381)
- Alpha-R1's own sensitivity analysis shows test-period annualised return moving from the reported 47.87% to 176.03% just by changing TopN (to 2–3) on S&P 500, a sign of how path-specific realised P&L is. — [arXiv 2512.23515](https://arxiv.org/abs/2512.23515)

### Inferences
**Exact form of the advantage**
- A_i = r_i − r̄ = (w_i − w̄)·R_{t+1} − (c_i − c̄), where w̄ is the group-average portfolio.
- Since 1ᵀw_i = 1ᵀw̄ = 1, we get (w_i − w̄)·(R + m·1) = (w_i − w̄)·R for any common shock m. The equal-weighted cross-sectional mean return cancels exactly, so the advantage is a **cross-sectional relative return** of a zero-net long–short portfolio. With a cash sleeve this fails: cash-weight differences × market return remain.
- With a factor model R = a + Bf + ε: A_i = (w_i − w̄)ᵀa + (b_i − b̄)ᵀf + (w_i − w̄)ᵀε, with b_i = Bᵀw_i. Sampled top-K portfolios from 3,000 names differ in beta, size, sector and country, so **factor realisations leak in**. The policy is rewarded for tilting toward factors that happened to pay off in the training sample (e.g., a persistent US-tech or growth tilt over 2010–2024). This is learning *in-sample factor premia*, a classic overfit.
- Mitigations: compute the reward on risk-model residual returns (R − B f̂), and/or add exposure penalties.

**Concave or risk-adjusted rewards re-introduce the market.** u(r_i) − ū ≈ u′(r̄)(r_i − r̄) + ½u″(r̄)[(r_i − r̄)² − Var]. Advantages are scaled by marginal utility at the group-mean return: larger in down weeks for concave u, smaller in up weeks. The weighting is market-dependent but not crazy.
- A per-week realised-variance penalty mostly penalises this week's common market move (shared noise). Ex-ante risk penalties (−λ wᵀΣ̂_t w from a covariance estimate known at t) are much less noisy than realised-variance rewards.

**Std normalisation in this setting**
- s_t = std_i(r_i) ≈ realised dispersion of the sampled portfolios' returns, which tracks the cross-sectional dispersion of week t times the policy's spread.
- (a) The per-week gradient is scaled by 1/s_t. This down-weights high-dispersion weeks (crises, earnings seasons), where much of the real P&L variation lives, and up-weights quiet weeks. The objective becomes roughly Σ_t E_π[r_t]/s_t (a dispersion-normalised, IC-like target), not expected P&L.
- (b) s_t shrinks as the policy concentrates, so the effective step size grows and drives collapse, matching the overconfidence mechanism above.
- Default: mean-only centring (RLOO or Dr. GRPO) with a global or running scale for the learning-rate budget.

**Single-path overfitting**
- E[GRPO gradient | R_{1..T}] ∝ ∇_θ Σ_t E_π[r_t(a; R_{t+1})]: the realised-history objective. G Monte Carlo samples per week only make the optimiser better at finding, *for each historical week*, the portfolios that did best in that specific week.
- If features identify the week (distinctive macro or price patterns), a high-capacity transformer can memorise the "realised winners per week". The KL-regularised optimum is the exponential tilt π*(a|s_t) ∝ π_ref(a|s_t)·exp(r(a; R_{t+1})/β). With small β this is literally "buy what went up". With large G this tilt is estimated very accurately.
- The effective sample size for *time-varying* decisions (factor timing, regime calls) is ~1,000 weeks, minus overlap if H > 1. Cross-sectional breadth (thousands of names per week) helps pure selection skill, but within-week errors are correlated.
- So the number of independent "outcome draws" bounds what RL can learn, regardless of G.

**Practical anti-overfitting levers**
- Keep β meaningful relative to the reward scale.
- Run few RL epochs: Alpha-R1 used 2 and FinRankGRPO 1.
- Use purged walk-forward validation on deterministic deployed performance.
- Bootstrap or block-bootstrap weeks, and sub-sample random universes per episode (both inspired by the André & Coqueret result).
- Use residualised rewards.
- Compare against the reference ranking model alone. If GRPO cannot beat π_ref out of sample, the RL stage is fitting noise.

### Gaps
- No empirical study measured how much factor-exposure leakage enters GRPO advantages in equity portfolios, or compared residual-return vs raw-return rewards under GRPO.
- No source quantified the dispersion-reweighting effect of std normalisation on financial returns. The effect is derived, not observed.

---

## Q6. Practical training details: group size, learning rate, KL coefficient, reference policy, entropy, sample efficiency/variance, and ~1,000 weekly states

### Takeaway
Published finance GRPO runs use small groups (G = 4–8), LLM-scale learning rates (1e-6 to 3e-6), weak or no KL (β = 0–0.001; DeepSeekMath used 0.04), and 1–2 epochs. For a non-LLM cross-sectional transformer with ~1,000 weekly states, sampling is nearly free, so G can be much larger (64–512). The core design question is not GRPO's hyperparameters but:
- whether to use the exact or pathwise gradient instead;
- how to regularise toward a supervised ranking prior;
- how to stop the in-sample collapse onto realised winners.

A defensible recipe uses a PL top-K policy pretrained supervised, GRPO without std normalisation (leave-one-out baseline), exact per-step KL to the pretrained policy, on-policy updates, cost-aware rewards with holdings in the state, and walk-forward early stopping on deterministic net performance.

### Cited Findings
- Hyperparameters reported in the literature:
  - DeepSeekMath: G = 64, lr 1e-6, β = 0.04, single update per exploration stage. — [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
  - DeepSeek-R1: G = 16, lr 3e-6, β = 0.001, ε = 10, reference reset every 400 steps, 16 minibatches per rollout. — [arXiv 2501.12948](https://arxiv.org/abs/2501.12948)
  - DAPO: G = 16, lr 1e-6, ε_low/high = 0.2/0.28, no KL. — [arXiv 2503.14476](https://arxiv.org/abs/2503.14476)
  - Alpha-R1: G = 8, ε = 0.2, β = 0.001, lr 1e-6, 2 epochs, temperature 1.0, reference = frozen Qwen3-8B. — [arXiv 2512.23515](https://arxiv.org/abs/2512.23515)
  - Trade-R1: G = 8, lr 1e-6, batch 32, temperature 1.0. — [arXiv 2601.03948](https://arxiv.org/abs/2601.03948)
  - FinRankGRPO: 4 responses per prompt, lr 3e-6, 1 epoch. — [arXiv 2609.24175](https://arxiv.org/abs/2609.24175)
  - FinATOM: G = 8, no reference-model KL, behaviour-KL stop. — [arXiv 2608.09880](https://arxiv.org/abs/2608.09880)
- Reference policies in finance GRPO are usually the SFT checkpoint or the frozen base LLM. Trading-R1 penalises KL to "the reference SFT model π_ref". FinRankGRPO uses a fixed reference after SFT on teacher rankings chosen for the highest Spearman correlation. — [arXiv 2509.11420](https://arxiv.org/abs/2509.11420); [arXiv 2609.24175](https://arxiv.org/abs/2609.24175)
- Zero-variance groups give no gradient. DAPO filters prompts whose group rewards are all equal, and DAPO-stock filters "states with all the same rewards". — [arXiv 2503.14476](https://arxiv.org/abs/2503.14476); [arXiv 2505.06408](https://arxiv.org/abs/2505.06408)
- A dense reward is necessary. FinRankGRPO's exact-match reward produced zero advantage everywhere, while the Spearman reward gave a "substantially denser optimization signal." — [arXiv 2609.24175](https://arxiv.org/abs/2609.24175)
- Entropy collapse is the main failure mode of naive GRPO in LLMs, addressed by Clip-Higher. — [arXiv 2503.14476](https://arxiv.org/abs/2503.14476)
- Std normalisation causes overconfidence under stochastic outcomes; no-std and RLOO stay calibrated. — [arXiv 2508.11800](https://arxiv.org/abs/2508.11800)
- The k3-as-loss KL is a biased approximation; prefer k1-in-reward or (on-policy) k2-as-loss, or exact KL. — [arXiv 2510.01555](https://arxiv.org/abs/2510.01555)
- Multi-step returns with per-time-index group normalisation (GR2PO) handle delayed consequences without a critic; group size and clip ratio were ablated. — [arXiv 2609.19850](https://arxiv.org/abs/2609.19850)
- Validated anti-leakage practices in this literature:
  - Strict chronological splits with point-in-time constituents and frozen LLM-generated memory before the test year (Alpha-R1).
  - Non-overlapping test weeks plus a post-LLM-cutoff test window (FinRankGRPO).
  - Research feedback confined to an inner period, with evaluation on a later outer period (AlphaDiverse).
  — [arXiv 2512.23515](https://arxiv.org/abs/2512.23515); [arXiv 2609.24175](https://arxiv.org/abs/2609.24175); [arXiv 2609.29014](https://arxiv.org/abs/2609.29014)

### Inferences (design recommendations for ~1,000 weekly states, N = 1,000–3,000, K = 10–20, £10k, c = 0–0.65%)
**1. Baseline first.** Train the same cross-sectional transformer with a *direct* objective:
- (a) supervised listwise ranking of next-week (residual) returns (the PL likelihood gives a natural π_ref), then
- (b) end-to-end deterministic fine-tuning through a differentiable top-K/softmax portfolio with an L1 cost against h_t, and a risk term from an ex-ante covariance.

GRPO must beat (b) out of sample on *deterministic* deployed net returns to justify itself.

**2. If using GRPO**
- **Policy.** PL / Gumbel-top-K over scores, with a temperature floor. Use the ordered log-prob (Q3); optionally Kool's unordered-set estimator.
- **Group size.** Policy sampling costs one dot product per sample, so use G = 64–256 per week. Per Q4 the score-function noise scales like N/G, so even G = 256 leaves noise comparable to signal at N ≈ 3,000. Alternatively, restrict the candidate set to the reference policy's top ~200 names, which shrinks the effective dimension.
- **Batch.** 16–64 weeks per step, sampled at random (block-bootstrapped) rather than sequentially.
- **Advantage.** RLOO / no-std: A_i = r_i − mean_{j≠i} r_j. Divide by a global running std of rewards (not per week). Drop weeks where all G rewards are identical.
- **Updates.** Strictly on-policy (μ = 1, so ratio = 1 and clipping is moot). If reusing samples, use a per-name length-normalised (GSPO-style) log-ratio with a tight clip.
- **KL.** Exact per-step categorical KL to the frozen supervised PL model. β is the main hyperparameter: choose it on walk-forward validation, initially so that KL ≈ a few nats per decision. β → 0 reproduces "buy last week's realised winners" (Q5).
- **Entropy diagnostics.** Track the mean pairwise Jaccard overlap of the G sampled sets and the PL entropy. Rising overlap toward 1 signals collapse.
- **Reward.**
  - r_i = h-week net return: w_i·R − c‖w_i − h_t‖₁, on residual returns if factor-neutral selection is the goal.
  - Optionally use log(1+r) or −λ·wᵀΣ̂_t w as ex-ante risk.
  - For turnover, use G multi-week (H = 4–8) trajectories from the same h_t with per-step group normalisation, or accept the myopic one-step cost.
- **Learning rate.** LLM rates (1e-6) don't transfer. For a small transformer, ordinary Adam rates with few RL epochs and early stopping are the analogue; the published runs used 1–2 epochs over the data (inference).

**3. Data budget.**
- Chronological split with purging, e.g. ~12 years train / 3 val / 5 test, then walk-forward refits.
- With ~600 train weeks, one RL epoch at 32 weeks per step is only ~20 updates. Many epochs over the same 600 realised outcomes will overfit.
- Prefer data augmentation (random sub-universes, bootstrapped week orders, per-region subsets) to more epochs.

**4. Evaluation hygiene.**
- Report ≥5 seeds and block-bootstrap CIs on paired differences vs (i) π_ref top-K, (ii) the direct-gradient model, (iii) 1/N and cap-weight.
- Sweep costs at 0, 0.1%, 0.65%, and report turnover.
- Test at least 5 years, since ±0.4 Sharpe SE at 6 years is already the best in this literature.
- If any LLM component is used, test only after its knowledge cutoff.

**5. Expected value of GRPO here.** In a full-information, price-taker, weekly setting, GRPO's distinctive features have little to do:
- no critic is needed, because the one-step value is known exactly;
- the group gives free counterfactual sampling, but the exact expectation is often computable anyway;
- the clipping and ratio machinery is moot on-policy.

Its plausible benefits are (a) optimising a hard, non-differentiable top-K equal-weight net-of-cost objective as specified, and (b) smoothing and KL-anchoring a pretrained ranker toward that objective. Expect the gains, if any, to resemble FinRankGRPO's: small IC improvements, with Sharpe differences inside sampling error unless the test is long.

### Gaps
- No finance paper reports GRPO hyperparameter sweeps (G, β, std vs no-std) on portfolio outcomes. All recommended values above are inferences from LLM practice and from the variance and structure analysis.
- No source tests multi-week-trajectory GRPO for turnover-aware equity portfolios. GR2PO's per-time-index normalisation was validated only on robot control.
- Broker-specific retail cost structures (fixed fees, FX spreads, UK stamp duty) were not researched. The 0–0.65% range is taken from the brief.
