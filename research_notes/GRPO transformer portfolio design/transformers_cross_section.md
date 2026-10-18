# Transformer Architectures for Cross-Sectional Stock Return Prediction and Portfolio Construction

Scope note: this covers (a) transformer designs used to predict or rank stocks, (b) how they compare with GBDT/MLP baselines out-of-sample, (c) practical design for weekly data on 1,000–3,000 global stocks over ~20 years (~1,000 weekly cross-sections), (d) permutation equivariance and changing universes, (e) using transformer outputs as a portfolio policy for policy-gradient or GRPO-style training. Status labels: **[PR]** = peer-reviewed; **[WP]** = working paper or preprint. Market labels: **CN** = China A-shares, **US**, **GLB** = multi-country. **Costs**: whether reported results are net of trading costs.

## 1. Architectures: what each attends over, inputs, target, reported results

### Takeaway
There are three families. (1) Temporal transformers over one stock's history (vanilla Transformer, TFT, PatchTST, Autoformer/FEDformer, Kronos). These are consistently weak or middling for cross-sectional ranking when used alone. (2) Cross-sectional attention, where stocks at a date are the tokens (Kelly–Kuznetsov–Malamud–Xu AIPM, AlphaPortfolio's CAAN, Poh et al.'s self-attention re-ranker). (3) Two-axis or spatio-temporal models (MASTER, DTML, Stockformer, Crossformer, HIST-style concept models). Families (2) and (3) have the strongest reported evidence. The best US evidence is AIPM: out-of-sample (OOS) SDF Sharpe 4.6 vs 3.9 for the strongest non-attention model, monthly, gross of costs, working paper. The best-documented peer-reviewed two-axis result is MASTER: CSI300 IC 0.064 vs 0.051 for XGBoost, China only, costs not stated.

### Cited Findings

**(2) Cross-sectional attention (stocks as tokens)**
- **AIPM / "Artificial Intelligence Asset Pricing Models"** (Kelly, Kuznetsov, Malamud, Xu; NBER WP 33351, Jan 2025, revised June 2026) **[WP, US, gross]**. The paper "implants a transformer in the stochastic discount factor". The input at each date is the N_t × D matrix of characteristics for all stocks. Attention lets "the optimal portfolio weight for asset i" depend on the characteristics of other assets, and a final linear layer λ maps the transformed characteristics to SDF portfolio weights. Training minimizes a "maximum Sharpe ratio regression" (MSRR) objective, so the network outputs portfolio weights directly, not return forecasts — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf); [NBER abstract](https://www.nber.org/papers/w33351)
  - Data: US monthly 1963–2022 from the JKP (Jensen–Kelly–Pedersen) dataset, NYSE/AMEX/NASDAQ, CRSP share codes 10–12. Uses 132 of 153 characteristics (those with <30% missing). Nano caps (<1st NYSE percentile) are dropped, as are stock-months missing more than one third of characteristics. Each characteristic is cross-sectionally rank-standardized to [−0.5, 0.5], and missing values are set to 0 (the median) — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - Training: 60-month rolling windows, retrained every month. OOS runs Feb 1968–Dec 2022. Adam optimizer. Results are averaged over 10 random seeds because "model estimates are sensitive to the random seed" — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - Results (OOS SDF Sharpe):
    - Linear SDF without attention: 3.6. Linear portfolio transformer: 3.9 (alpha t-stat 6.8 vs the attention-free model).
    - DKKM nonlinear SDF without attention: 3.9. Nonlinear transformer: 4.6.
    - An "apples-to-apples" feed-forward network with the same architecture but no attention gives the same qualitative gap.
    - Scaling: 1 block (~100k params) gives 3.8; 10 blocks (~1M params) give 4.6, and the curve "has not yet flattened".
    - The MLP benchmark has over 300k params (2 hidden layers of width 512) — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - Size: the transformer "dominates all other models in every size group". The "relative increase in performance from the transformer is largest among mega and large-cap stocks". Sharpe rises monotonically from mega to micro for all models. The authors say "much of the performance ... is generated from the relatively illiquid subset" — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - Observable firm links (customer–supplier, analyst co-coverage, and others) and learned attention are "complementary and mutually beneficial" — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - Compute: work supported by a Swiss National Supercomputing Centre (CSCS) grant. The authors leave larger models to future work "due to the computational costs for model training" — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - A search of the full text for "transaction" found no cost-adjusted results. These Sharpe ratios are gross, long-short SDF portfolios — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- **AlphaPortfolio** (Cong, Tang, Wang, Zhang; draft Aug 2021) **[WP, US]**.
  - Architecture: a sequence representation module (SREM) encodes each asset's 12-month history of characteristics. A Cross-Asset Attention Network (CAAN) "takes the representations of all assets as inputs" and outputs a scalar "winner score" per asset.
  - Portfolio generator: assets are sorted by score. The top G go long with weight exp(s_i)/Σ_top exp(s_j), and the bottom G go short with weights ∝ exp(−s_i).
  - Training: gradient ascent on an OOS-style Sharpe objective, with episodes of 12 monthly periods. Data: CRSP/Compustat, July 1965–June 2016, 1.76M firm-months.
  - Results: OOS Sharpe "consistently above two" over 1990–2016, including when the bottom 10% or 20% by market cap are excluded. Alpha above 13.5% under multiple factor models — [NBER conference PDF](https://conference.nber.org/conf_papers/f160875/f160875.pdf)
  - The authors say the framework "allows ... transaction costs", but the headline numbers are monthly long-short — [NBER conference PDF](https://conference.nber.org/conf_papers/f160875/f160875.pdf). A later follow-up with a modified objective reported OOS Sharpe "over 1.2", well below the original claim (per search-result summary; not verified against the primary source) — [Stanford PURL](https://purl.stanford.edu/fy908xd8332)
- **Context-aware learning to rank with self-attention** (Poh, Lim, Zohren, Roberts, Oxford-Man; arXiv 2105.10019) **[WP, FX]**. A transformer re-ranks the instruments in a cross-section at each rebalance, so a score depends on the other instruments in the list. On 31 currencies it "increases the Sharpe ratio by around 30%" vs learning-to-rank baselines, including during risk-off states. Results are rescaled to 15% volatility — [arXiv](https://arxiv.org/abs/2105.10019)
  - The earlier paper by the same group (arXiv 2012.07149) applied pairwise/listwise learning to rank to cross-sectional momentum and reports "approximately threefold boosting of Sharpe Ratios compared to traditional approaches" — [arXiv](https://arxiv.org/abs/2012.07149)
- **Portfolio Transformer (PT)** (Kisiel & Gorse, UCL; arXiv 2206.03246) **[WP, US + multi-asset, costs in loss]**. An encoder–decoder transformer with time-encoding layers and gating that "directly optimizes the Sharpe ratio" and includes transaction-cost penalties in the loss.
  - Datasets (daily): 4 ETFs (from 2006), 24 commodity futures (from 2002), and 500 NASDAQ stocks (from 1996).
  - Stock panel Sharpe: PT 2.00, LSTM 1.46, XGBoost 0.92, MLP 0.77, mean-variance 0.69. Trained on one P100 GPU — [arXiv PDF](https://arxiv.org/abs/2206.03246)

**(3) Spatio-temporal / two-axis models**
- **MASTER** (Li et al., SJTU/Alibaba; AAAI 2024) **[PR, CN, costs not stated]**. Three stages: (i) market-guided gating, where a 63-feature market-state vector from CSI300/500/800 index data rescales feature dimensions through a temperature-β softmax; (ii) intra-stock attention over the time steps of each stock, with sinusoidal positional encoding; (iii) inter-stock attention across stocks at each time step. These alternate instead of using full τ×|S| attention. The predictor is a linear head trained with MSE on a **daily cross-sectionally z-scored 5-day return label**. Each batch is all stocks on one date — [arXiv 2312.15235](https://arxiv.org/abs/2312.15235); [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/27767)
  - Setup: CSI300 and CSI800, daily 2008–2022. Train Q1 2008–Q1 2020, validation Q2 2020, test Q3 2020–Q4 2022. Alpha158 features, lookback τ = 8, horizon d = 5. D = 256, lr = 1e-5, 4 intra-stock heads, 2 inter-stock heads. At most 40 epochs with early stopping. One V100 GPU, 5 seeds — [arXiv](https://arxiv.org/abs/2312.15235)
  - Design rationale: the authors warn that stock forecasting is "in intense data hunger … only around 250 trading days per year" and that a full spatio-temporal attention field "often struggles to optimize" — [arXiv](https://arxiv.org/abs/2312.15235)
  - CSI300 test results (IC / RankIC / excess AR / IR, top-30 daily strategy):
    - MASTER 0.064 / 0.076 / 0.27 / 2.4
    - XGBoost 0.051 / 0.050 / 0.23 / 1.9
    - Vanilla Transformer 0.047 / 0.051 / 0.22 / 2.0
    - DTML 0.049 / 0.052 / 0.21 / 1.7
    - LSTM 0.049 / 0.051 / 0.20 / 2.0
    — [arXiv](https://arxiv.org/abs/2312.15235)
  - CSI800: MASTER 0.052 / 0.066 / 0.28 / 2.3; XGBoost 0.040 / 0.047 / 0.08 / 0.6; Transformer 0.040 / 0.048 / 0.13 / 1.1 — [arXiv](https://arxiv.org/abs/2312.15235)
  - Code: [GitHub SJTU-DMTai/MASTER](https://github.com/SJTU-DMTai/MASTER)
- **DTML** (Yoo, Soun, Park, Kang; KDD 2021) **[PR, US/CN/JP/UK]**. A temporal attention-LSTM per stock, multi-level contexts with a global market context, and a transformer encoder across stocks. The target is movement classification. Reports state-of-the-art accuracy on 6 datasets and "up to 13.8 percentage points higher profit", with a 44.4% annualized return in simulation — [KAIST repository](https://dspace.kaist.ac.kr/handle/10203/311555)
  - In MASTER's re-run on CSI300, DTML's IC (0.049) was below XGBoost's (0.051) — [arXiv](https://arxiv.org/abs/2312.15235)
- **HIST** (Xu et al., arXiv 2110.13716) **[WP, CN]**. Graph and attention modules that mine "concept-oriented shared information" from predefined concepts (industry, etc.) and learned hidden concepts — [arXiv](https://arxiv.org/abs/2110.13716)
  - In Qlib's CSI300 Alpha360 benchmark, HIST is the best model: IC 0.0522, RankIC 0.0667, AR 9.87%, IR 1.37 — [Qlib benchmarks](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
- **FactorVAE** (Duan et al., AAAI 2022) **[PR, CN]**. A dynamic factor model combined with a VAE, trained with a prior–posterior scheme in which the posterior sees future returns. It also outputs return variances.
  - Setup: all A-shares, Alpha158 (20 features), T = 20. Train 2010–2017 (3,432 stocks), validation 2018, test 2019–2020 (3,923 stocks).
  - Results: Rank IC 0.055 (Rank ICIR 0.568) vs Transformer 0.033, GRU 0.032, and the GKX conditional autoencoder 0.039. The paper also reports robustness to stocks "that have never been learned before" — [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/20369)
- **Stockformer** (arXiv 2401.06139, "under consideration" at Expert Systems with Applications) **[WP, CN]**. A discrete wavelet transform splits returns into high and low frequencies, followed by a dual-frequency spatiotemporal encoder with graph embedding and multitask learning (return + direction). Inputs are 360 Alpha360-style price-volume factors on CSI300 constituents, 2018-03-01 to 2024-01-30. Evaluation uses 14 rolling sub-datasets (2-year train / 3-month validation / 3-month test) and a TopK-Dropout backtest — [arXiv](https://arxiv.org/abs/2401.06139)
- **Crossformer** (cross-dimension attention) and other adaptive-graph models in **QuantBench** (US, volume-price + fundamentals, IC loss): Crossformer IC 4.50%, SR 3.13. The best model is the adaptive GNN THGNN (IC 4.93%, SR 3.32). DTML: IC 3.87%, SR 3.20 — [QuantBench arXiv 2504.18600](https://arxiv.org/html/2504.18600v1)

**(1) Temporal transformers over each stock's history**
- **Qlib CSI300** (20 seeds) **[benchmark, CN, net of costs]**:
  - Alpha158: vanilla Transformer IC 0.0264, AR 2.73%, IR 0.40. Localformer IC 0.0356, AR 4.38%. TFT IC 0.0358 but RankIC only 0.0116, AR 8.47%, max DD −18.2%.
  - Alpha360 (raw price/volume sequences): vanilla Transformer IC 0.0114, AR −2.70%, IR −0.34.
  — [Qlib benchmarks](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
- **QuantBench (US)** **[WP]**: time-series transformers "underperformed in stock prediction tasks, a finding consistent with other studies". Autoformer IC 0.08%, FEDformer 0.13%, PatchTST 1.07% (SR 0.61), Pyraformer 1.14%. For comparison, LSTM 3.89% (SR 3.02), GRU 4.12% (SR 3.44), TFT 3.99% (SR 3.23) — [QuantBench](https://arxiv.org/html/2504.18600v1)
- **Kronos** (Shi, Fu et al., Tsinghua; arXiv 2508.02739, Aug 2025) **[WP, multi-market pretraining, CN backtest net of 0.15% costs]**. A decoder-only transformer over OHLCV "K-lines" that are tokenized into discrete tokens with Binary Spherical Quantization. Uses RoPE. Pretrained on more than 12B K-line records from 45 exchanges — [arXiv HTML](https://arxiv.org/html/2508.02739v1); [HF papers](https://huggingface.co/papers/2508.02739)
  - Sizes: small 24.7M params (8 layers, d_model 512), base 102.3M, large 499.2M — [arXiv HTML](https://arxiv.org/html/2508.02739v1)
  - Claims: zero-shot RankIC +93% over the leading time-series foundation model (TSFM) and +87% over the best non-pretrained baseline — [HF papers](https://huggingface.co/papers/2508.02739)
  - Ablation: Kronos-small return-forecasting IC 0.0665 / RankIC 0.0622, vs a same-size continuous MSE autoregressive model at 0.0416 / 0.0399 — [arXiv HTML](https://arxiv.org/html/2508.02739v1)
  - Backtest: the signal is the 10-day average forecast price over a 90-day daily lookback. CSI300 top-k = 50 (n = 5 dropped), CSI800 top-k = 200, cost 0.15% per trade. Kronos reports the highest AER and IR, but the numbers appear only in figures. The 25 baselines are TS models (PatchTST, iTransformer, TimesNet, DLinear, …), TSFMs, GARCH and generative models. No GBDT on engineered factors appears in the baseline list — [arXiv HTML](https://arxiv.org/html/2508.02739v1)
  - A secondary blog says it was accepted at AAAI 2026, and an AAAI OJS link appeared in search results. Not verified — [blog](https://themenonlab.blog/blog/kronos-foundation-model-financial-markets-candlestick)
- **Generic TS architectures** referenced above:
  - PatchTST: patches of a univariate series as tokens, channel-independent — [arXiv 2211.14730](https://arxiv.org/abs/2211.14730)
  - iTransformer: each variate's whole series is one token; attention runs across variates — [arXiv 2310.06625](https://arxiv.org/abs/2310.06625)
  - TFT: variable selection, LSTM encoder, interpretable attention — [arXiv 1912.09363](https://arxiv.org/abs/1912.09363)
- **SERT / pre-trained transformers for US large-cap pricing** (arXiv 2505.01575) **[WP, US]**. Reports OOS R² of 11.94% and 11.47% around COVID, and a Sortino ratio 47% above buy-and-hold under static transaction costs — [arXiv](https://arxiv.org/abs/2505.01575). These R² values are about 30× GKX-scale stock-level R² (~0.4%/month). The target or setup is probably not comparable; treat with caution.
- **Wang (2025), Finance Research Letters** **[PR, US]**. An Autoformer on the GKX-style US panel (1957–2021, 920 features) "significantly outperform[s]" simple neural networks, with the largest gap at longer horizons (per abstract/summary) — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612325020379)

### Inferences
- Cross-asset context is where attention adds value; temporal self-attention over short noisy price histories does not. This holds in the US (AIPM: attention vs identical attention-free network), in China (MASTER/HIST > temporal Transformer), and in FX (Poh). Vanilla temporal transformers sit at the bottom of both Qlib and QuantBench.
- **iTransformer is structurally a cross-sectional attention model**: tokens are variates, i.e. stocks. With weekly stock histories embedded by an MLP, it is close to "stocks-as-tokens" attention. In standard long-horizon forecasting use it is trained on a fixed variate set to regress raw values, which does not match ranking.
- MASTER's 5-day horizon and per-date batching are the closest published analogue to a weekly cross-sectional ranker. Its gain over XGBoost (+0.013 IC on CSI300) is real but modest, China-only, and over a 2.5-year test window.
- AIPM is the closest analogue to "transformer outputs portfolio weights". Its results are long-short, gross, include small and micro caps, and are monthly. A long-only, 10–20-name, developed-market large/mid-cap implementation should expect much lower Sharpe. Even so, the relative gain of attention was largest in mega/large caps, which is encouraging for the target universe.

### Gaps
- MASTER's backtest section does not state transaction costs. The "excess AR" for a daily top-30 strategy with no costs is probably optimistic.
- AIPM's per-size-group Sharpe values are only in a figure (Fig. 6). Exact mega/large-cap Sharpe ratios were not extracted.
- Kronos's AER/IR numbers are in figures only. It is unclear whether its "IC" for return forecasting is cross-sectional or per-series.
- Stockformer, DTML and HIST full results tables were not extracted (only abstracts or third-party benchmark rows).
- I found no peer-reviewed transformer study on **global developed-market weekly** cross-sections. The evidence is US monthly (AIPM, AlphaPortfolio, GKX-style), China daily (most of the CS/AI literature), or FX.
- "Portfolio Transformer" publication venue not verified (arXiv only here).

## 2. Evidence versus strong baselines (GBDT, MLP, linear) and foundation models

### Takeaway
On hand-engineered tabular factors, GBDTs (LightGBM/XGBoost/CatBoost, and especially ensembles such as DoubleEnsemble) match or beat vanilla temporal transformers and often beat MLPs. Transformers beat trees only when they exploit **cross-sectional context** (MASTER, HIST, AIPM) or are pretrained at scale on financial data (Kronos, Rahimikia et al.'s finance-pretrained TSFMs). Off-the-shelf TSFMs (Chronos, TimesFM) are weak zero-shot on returns. Most head-to-head transformer-vs-tree evidence is China daily data. US monthly evidence (GKX, AIPM) favours shallow or medium neural nets over trees for mid/large caps.

### Cited Findings
- **Gu, Kelly & Xiu (2020), RFS 33:2223–2273** **[PR, US, gross]**. About 30,000 US stocks, 1957–2016, 94 characteristics × 8 macro interactions + 74 industry dummies = 920 covariates. Train 1957–1974, validation 1975–1986, test 1987–2016 — [NBER w25398](https://www.nber.org/papers/w25398)
  - Monthly OOS R² (all stocks): NN3 0.40%, NN2 0.39%, NN4 0.39%, GBRT 0.34%, RF 0.33%, NN1 0.33%, ENet 0.11%, OLS −3.46%.
  - Top-1000 stocks: NN3 0.70%, NN4 0.67%, RF 0.63%, GBRT 0.52%.
  — [NBER w25398](https://www.nber.org/papers/w25398)
  - "Shallow learning outperforms deeper learning": NN3 (32-16-8) is best, and 4–5 layers do not help. Long-short decile Sharpe: NN 1.35 (value-weighted) and 2.45 (equal-weighted), vs OLS 0.61 and 0.83. The strongest predictors are momentum, liquidity and volatility variants — [NBER w25398](https://www.nber.org/papers/w25398); [RFS DOI](https://doi.org/10.1093/rfs/hhaa009)
- **Qlib benchmark, CSI300** (mean ± std over 20 seeds) **[CN, net of costs]**.
  - Setup (from the LightGBM Alpha158 config): train 2008–2014, validation 2015–2016, test 2017-01-01 to 2020-08-01. TopkDropoutStrategy with topk = 50, n_drop = 5. Open cost 0.05%, close cost 0.15%, min cost 5. Benchmark SH000300 — [Qlib LightGBM config](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml)
  - Alpha158 (engineered tabular), annualized return / IR:
    - DoubleEnsemble (LightGBM-based) 11.58% / 1.34 (IC 0.0521)
    - LightGBM 9.01% / 1.02 (IC 0.0448)
    - MLP 8.95% / 1.14
    - XGBoost 7.80% / 0.91
    - TRA 7.18% / 1.08
    - Linear 6.92% / 0.92
    - Localformer 4.38% / 0.66
    - Transformer 2.73% / 0.40
    — [Qlib benchmarks](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
  - Alpha360 (raw sequences):
    - HIST 9.87% / 1.37; IGMTF 9.46% / 1.35; TRA 9.20% / 1.28; TCTS 8.93% / 1.23; GATs 8.24% / 1.11
    - GRU 7.20% / 0.97; LightGBM 5.58% / 0.76; Localformer 2.46%
    - MLP 0.29%; Transformer −2.70%
    — [Qlib benchmarks](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
  - CSI500 Alpha158: LightGBM 12.84% / IR 1.57 vs MLP 0.43% / 0.06 (the table is noted as incomplete). Qlib warns it had "very limited resources to implement and finetune the models" — [Qlib benchmarks](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
  - QuantBench notes that Qlib's benchmark "mostly focus[es] on temporal models and has an earlier cutoff (early 2022)" — [QuantBench](https://arxiv.org/html/2504.18600v1)
- **QuantBench** (HKUST et al., arXiv Apr 2025) **[WP]**. In China, LSTM beats XGBoost on IC with both Alpha101 (4.76% vs 2.31%) and Alpha158 (5.95% vs 2.53%). Yet XGBoost has the better Sharpe on Alpha101 (0.81 vs 0.77) and LSTM wins on Alpha158 (0.76 vs 0.64). The authors conclude that DNNs' "proficiency [in fitting objectives] does not necessarily translate to superior returns over tree models" — [QuantBench](https://arxiv.org/html/2504.18600v1)
- **Grinsztajn, Oyallon & Varoquaux (2022)**, NeurIPS 2022 Datasets & Benchmarks **[PR]**. On 45 tabular datasets, "tree-based models remain state-of-the-art on medium-sized data (~10K samples)". NNs struggle to be "robust to uninformative features", to "preserve the orientation of the data", and to "learn irregular functions". The study used 20,000 compute hours of hyperparameter search per learner — [arXiv 2207.08815](https://arxiv.org/abs/2207.08815)
- **International ML evidence (non-transformer)**:
  - Cakici, Fieberg, Metko & Zaremba (2023, J. Econ. Dynamics & Control) **[PR, GLB]**: 46 markets, 148 characteristics, 11 models including GBRT, RF and FFNNs. All give substantial gains, but **forecast combination** is "particularly effective". Predictability comes mainly from momentum, reversal, value and size, and is stronger in markets with more listed firms and higher idiosyncratic risk — [open.icm](https://open.icm.edu.pl/items/f88ffcae-dc39-44e1-b48a-602d7612de55); [DOI](https://doi.org/10.1016/j.jedc.2023.104725)
  - Choi, Jiang & Zhang, "Alpha Go Everywhere" **[WP, GLB]**: NNs trained market-by-market beat a US-trained global model, and trees underperform linear models when observations are few — [ABFER PDF](https://www.abfer.org/media/abfer-events-2023/annual-conference/papers-investment/AC23P3084-Alpha-Go-Everywhere-Machine-Learning-and-International-Stock-Returns.pdf)
- **Time-series foundation models on returns**:
  - Rahimikia, Ni & Wang, "Re(Visiting) Time Series Foundation Models in Finance" (arXiv 2511.18578, Nov 2025) **[WP, GLB daily, gross]**. Off-the-shelf Chronos and TimesFM "perform poorly" zero-shot and fine-tuned, "underperforming strong ensemble models such as CatBoost and LightGBM". Models **pretrained from scratch on financial data** "deliver substantial forecasting and economic gains", and larger data, synthetic augmentation and tuning help further — [arXiv HTML](https://arxiv.org/html/2511.18578v1)
    - Benchmarks: across 5/21/252/512-day windows (2001–2023), ensembles (CatBoost, XGBoost, LightGBM) beat linear models and NNs. US OOS R²: CatBoost −0.10% vs linear −0.47%. Best CatBoost daily long-short: AR 46.5%, Sharpe 6.79, **without transaction costs** — [arXiv HTML](https://arxiv.org/html/2511.18578v1)
    - 613 finance-pretrained models released (FinText) — [Hugging Face FinText](https://huggingface.co/FinText)
  - Noguer i Alonso & Franklin (arXiv 2606.27100, June 2026) **[WP, 5 US large caps]**. TimeGPT, TimesFM-2.5, Moirai-2.0, Chronos and Chronos-2 vs NBEATS, NHITS, PatchTST, iTransformer and KAN, with context L = 512, a rolling origin, and random-walk benchmarks with Diebold–Mariano tests. The authors stress that "strong rankings need not imply economically" meaningful gains (abstract) — [arXiv HTML](https://arxiv.org/html/2606.27100)
  - Kronos (above): finance-specific pretraining beats generic TSFMs and full-shot TS models on CN backtests net of 0.15% costs, but the comparison does not include GBDT on engineered factors — [arXiv HTML](https://arxiv.org/html/2508.02739v1)
- **AIPM vs ML baselines (US monthly)**: nonlinear transformer Sharpe 4.6 vs DKKM 3.9, a 300k-param MLP (lower; exact number not extracted), and linear (Brandt–Santa-Clara–Valkanov style) ridge SDF. No GBDT baseline appears — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- **MASTER vs XGBoost (CN)**: MASTER wins IC by +0.013 on CSI300 and +0.012 on CSI800, and IR 2.4 vs 1.9 and 2.3 vs 0.6. The vanilla temporal Transformer is roughly level with XGBoost — [arXiv](https://arxiv.org/abs/2312.15235)

### Inferences
- **Where transformers help**: (a) attention across stocks at a date (AIPM, MASTER inter-stock, HIST, CAAN); (b) raw-sequence inputs where trees lack inductive bias (Alpha360: recurrent and graph models beat LightGBM, though the vanilla Transformer does not); (c) large-scale finance-specific pretraining (Kronos; Rahimikia's from-scratch TSFMs).
- **Where they don't help**: generic TS transformers (PatchTST, Autoformer, FEDformer) on per-stock histories, and vanilla temporal transformers on engineered factor sets. In those settings LightGBM/DoubleEnsemble and even MLP/linear are as good or better (Qlib, QuantBench, Rahimikia).
- **Baseline to beat**: for weekly global data, a LightGBM (or LightGBM ensemble) on rank-normalised factors is the bar. GKX's top-1000 result (NN3 0.70% vs GBRT 0.52%) suggests well-regularised small NNs can beat trees for larger, more liquid names in monthly US data.
- Combining forecasts (Cakici: forecast combination; Qlib: DoubleEnsemble best; QuantBench: seed ensembles) is consistently one of the largest, cheapest gains. A transformer + LightGBM blend is a sensible default.

### Gaps
- I found no clean, peer-reviewed head-to-head between a cross-sectional transformer and tuned LightGBM on US or global **weekly** data with costs.
- The AIPM paper does not include a GBDT baseline (none found in text).
- The Wang (2025, FRL) Autoformer result was seen only via abstract or summary. Effect sizes not extracted.
- Many Chinese results (MASTER, FactorVAE, Stockformer) use 1–3-year test windows. Statistical significance across regimes is limited.

## 3. Practical design for limited data (~1,000 weekly cross-sections × 1,000–3,000 stocks)

### Takeaway
Published working configurations are small: MASTER uses D = 256, a few heads, lr 1e-5, ≤40 epochs, 1 GPU. AIPM shows 100k–1M parameter cross-sectional transformers generalising when trained on just 60 monthly cross-sections per window, with many stocks per date and rank-standardised inputs. The recurring recipe is:
- rank- or z-normalise inputs and labels per date
- one date = one batch
- train on cross-sectional (IC/listwise) objectives
- early-stop on validation IC
- ensemble many seeds
- retrain on a rolling schedule

### Cited Findings
- **Sample size reference points**:
  - AIPM trains a ~1M-param, 10-block transformer on **60-month rolling windows** (60 cross-sections of US stocks) and still improves OOS Sharpe as depth grows (1 block ~100k params: 3.8; 10 blocks: 4.6) — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - MASTER trains on ~12 years of daily CSI300/CSI800 data (Q1 2008–Q1 2020) and calls the task "intense data hunger" — [arXiv](https://arxiv.org/abs/2312.15235)
  - GKX found depth beyond 3 hidden layers does not help (NN3 best) — [NBER w25398](https://www.nber.org/papers/w25398)
  - AIPM's MLP benchmark performance "saturates around a width of 512" and is "U-shaped in the network depth and saturates at a depth of 2" — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- **Inputs and normalisation**:
  - AIPM/JKP: cross-sectional rank to [−0.5, 0.5], missing set to 0 (median) — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - GKX: 94 characteristics + interactions with 8 macro predictors + industry dummies — [NBER w25398](https://www.nber.org/papers/w25398)
  - Qlib Alpha158 (engineered tabular) vs Alpha360 (raw 60-day price/volume ratios). Alpha158 favours trees; Alpha360 favours sequence and graph models — [Qlib benchmarks](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
  - MASTER adds a market-state vector (63 index-based features) used as a gate — [arXiv](https://arxiv.org/abs/2312.15235)
  - QuantBench: feature engineering matters more for trees. Adding Wikidata relations gave "minimal improvements" — [QuantBench](https://arxiv.org/html/2504.18600v1)
  - AIPM: observable firm links (supplier, analyst co-coverage) are complementary to learned attention — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- **Labels**: MASTER uses "daily Z-score normalization of return ratio to encode the label with the rankings" — [arXiv](https://arxiv.org/abs/2312.15235)
- **Loss functions**:
  - QuantBench (LSTM, US, return / SR / IC):
    - **IC loss** 36.0% / 1.86 / 3.62%
    - Classification 19.3% / 1.98 / 2.77%
    - MSE 8.97% / 0.45 / 1.78%
    - Pairwise ranking −1.11% / −0.10 / −0.07%
    - The pattern repeats for RGCN and DTML (IC loss best on return) — [QuantBench](https://arxiv.org/html/2504.18600v1)
  - Kwiatkowski & Chudziak (arXiv 2510.14156, Oct 2025) **[WP, US]**. A MASTER-style transformer on 110 S&P 500 stocks (top 10 per GICS sector), 2015–2024 daily, inputs = return and turnover, 20-day lookback, 70/15/15 split, daily long-only top-5. Sharpe: Margin 0.75, ListNet 0.74, BPR 0.72 (lowest MDD −15.8%), RankNet 0.68, MSE 0.66. IC was nearly identical across losses (0.073–0.077), and RankNet had the highest IC but only moderate Sharpe — [arXiv HTML](https://arxiv.org/html/2510.14156)
  - Zhang & Wu (arXiv 2104.12484) **[WP, CN]**: a long-short-aware generalisation of ListMLE (generalised Plackett–Luce) emphasising the top and bottom of the list. On 68 factors, China 2006–2019: OOS annual return 38%, Sharpe 2 — [arXiv](https://arxiv.org/abs/2104.12484)
  - Poh et al.: listwise/pairwise learning to rank about triples Sharpe vs heuristics for cross-sectional momentum — [arXiv](https://arxiv.org/abs/2012.07149)
- **Regularisation, seeds, ensembling**:
  - Qlib reports ±std over 20 seeds; TabNet and Transformer show large IR std (e.g. TabNet IR 0.37 ± 0.54) — [Qlib benchmarks](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
  - AIPM averages 10 seeds — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - QuantBench: 40-seed MLP-Mixer runs show "significant variance", and ensembling "helped reduce this variance, improving robustness" — [QuantBench](https://arxiv.org/html/2504.18600v1)
  - MASTER: early stopping, ≤40 epochs, very low lr (1e-5) — [arXiv](https://arxiv.org/abs/2312.15235)
  - Loss study: AdamW with weight decay, early stopping on validation, grid search over dropout and d_model — [arXiv](https://arxiv.org/html/2510.14156)
- **Retraining cadence**: QuantBench (US 2021–2023) compared 3/6/12-month rolling retrains with no retraining. **3-month** retraining was best and no rolling was worst — [QuantBench](https://arxiv.org/html/2504.18600v1). AIPM retrains monthly on a 60-month window — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- **Positional encodings**: MASTER uses fixed sinusoidal PE over the lookback window only, with no PE across stocks — [arXiv](https://arxiv.org/abs/2312.15235). Kronos uses RoPE in causal attention — [arXiv HTML](https://arxiv.org/html/2508.02739v1). PT uses "specialized time encoding layers" — [arXiv](https://arxiv.org/abs/2206.03246)
- **Compute**:
  - MASTER: one Tesla V100 16GB — [arXiv](https://arxiv.org/abs/2312.15235)
  - PT: one P100 16GB — [arXiv](https://arxiv.org/abs/2206.03246)
  - AIPM (monthly re-fit over 55 years × 10 seeds, up to 1M params): national supercomputer allocation — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
  - Kronos pretraining (25M–499M params on 12B records) is far beyond a single-GPU budget. The smallest released model is 24.7M params — [arXiv HTML](https://arxiv.org/html/2508.02739v1)

### Inferences (design recommendations for the stated setting)
- **Model size**: start at d_model 64–128, 2–4 heads, 1–3 cross-sectional attention blocks, FFN 2–4× d_model, roughly 50k–500k params. That is the AIPM 1–3-block range, and below MASTER's D = 256 because a weekly panel has fewer, noisier dates. Scale only if a validation rank-IC curve keeps improving, as AIPM's did.
- **Effective sample**: ~1,000 dates × ~2,000 stocks ≈ 2M stock-weeks, but only ~1,000 independent cross-sections and ~20 years of regimes. Choose validation splits by time, use purged and embargoed walk-forward folds with a gap of at least the label horizon, and retrain every quarter or half-year.
- **Inputs per stock-week**: (i) about 20–150 rank-normalised ([−0.5, 0.5]) characteristics (value, momentum 1/3/6/12m, short-term reversal, volatility, liquidity/turnover, size, quality/profitability, investment, accruals, analyst revisions if available), with missing values set to 0 plus a missing-indicator; (ii) an optional short weekly price/volume history (e.g. 12–26 weeks) embedded per stock by a small MLP or 1-layer temporal encoder (MASTER-style intra-stock step); (iii) country and sector embeddings (learned, few dims) so attention can learn region and industry linkages; (iv) a date-level market or regime vector (index returns, volatility, rates) used as a gate or FiLM (MASTER).
- **Rank-normalise within region** (or globally plus within country) to remove currency and market-level scale differences. Use local-currency or USD-hedged excess returns relative to the cross-sectional mean or median as the label.
- **Loss**: IC/correlation loss or listwise softmax cross-entropy (ListNet) on cross-sectionally z-scored or ranked 1-week (or 4-week smoothed) forward returns. Optionally add MSE for stability. QuantBench and the loss study both favour IC or listwise over plain MSE and over naive pairwise.
- **Regularisation**: dropout 0.1–0.3 on attention and FFN, AdamW weight decay ~1e-4–1e-2, early stopping on validation rank-IC, gradient clipping, low lr (1e-4–1e-5). Use a seed ensemble of 5–20 models, then blend with LightGBM.
- **Compute**: one weekly cross-section of 3,000 tokens with d = 64 and 4 heads needs 3,000² × 4 ≈ 36M attention scores per layer, ~144MB in fp32. A full epoch over ~800 training dates is seconds to minutes on one consumer GPU and feasible but slower on CPU. A single GPU is sufficient; multi-seed ensembles and walk-forward re-fits dominate cost.

### Gaps
- No published ablation for weekly frequency on global developed markets specifies the best d_model, depth or dropout. The recommendations above are extrapolations from monthly US (AIPM, GKX) and daily China (MASTER, Qlib).
- The loss study (2510.14156) uses one split of about 1.5 years and does not report costs or significance. Loss rankings may not be robust.
- QuantBench's Sharpe values (often >3) are not clearly stated net or gross of costs in the extracted text.

## 4. Permutation equivariance and a changing universe

### Takeaway
Self-attention without positional encodings over the stock axis is permutation-equivariant: reordering stocks reorders outputs identically. A model with stocks as tokens therefore needs no fixed ordering, and with key-padding masks it handles any number of stocks per date. This is the main structural advantage of cross-sectional attention (AIPM, MASTER inter-stock, CAAN) over "assets as fixed input channels" designs (PT, many RL portfolio nets), which need a fixed asset list.

### Cited Findings
- AIPM's input is the N_t × D characteristics matrix with N_t varying by month. The attention matrix A_t (N_t × N_t) has entries built from characteristic similarities across asset pairs (X_t W X_t′ in the linear version). Portfolio weights come from a shared final λ applied row-wise, so the same parameters price any number of assets — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- AIPM's feed-forward sublayer "operates row-wise", transforming each asset's characteristics with shared weights — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- MASTER: data-driven attention over stocks "is more flexible and applicable to the time-varying stock sets", whereas predefined graphs "may not be generalizable to new stocks in an evolving market where events such as company listing, delisting ... happen" — [arXiv](https://arxiv.org/abs/2312.15235)
- FactorVAE reports better robustness than baselines when stocks in the test set "have never been learned before" (its Table 2 varies the number of missing stocks), and its stock counts grow from 3,432 to 3,923 between train and test — [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/20369)
- Theory background: functions on sets are characterised as permutation-invariant or equivariant (Deep Sets) — [arXiv 1703.06114](https://arxiv.org/abs/1703.06114). Attention-based set models without positional encodings (Set Transformer) are permutation-equivariant and handle variable set sizes, with inducing points reducing O(N²) cost — [arXiv 1810.00825](https://arxiv.org/abs/1810.00825)
- Contrast: Portfolio Transformer experiments use fixed asset sets (4 ETFs, 24 futures, 500 NASDAQ stocks) — [arXiv](https://arxiv.org/abs/2206.03246). iTransformer makes each variate a token — [arXiv 2310.06625](https://arxiv.org/abs/2310.06625)

### Inferences
- **Implementation for a changing universe**: build each date's batch from that date's eligible members (point-in-time index or liquidity screen), pad to N_max, and pass a key-padding mask so padded tokens neither attend nor are attended to. Mask them in the loss and in portfolio weights too. Do **not** add stock-ID or positional embeddings on the stock axis. Stock-ID embeddings in particular break generalisation to new listings and encourage memorisation.
- Use country, sector or size-bucket embeddings as "type" features instead of identity. They keep equivariance (identical inputs give identical outputs) while letting attention specialise.
- Cross-sectional normalisation (ranks per date) together with equivariant attention makes the model invariant to universe size and composition drift. It is the natural pairing.
- Attention cost is O(N²) per date. For 3,000 stocks this is fine on a GPU. For larger universes, use inducing points (Set Transformer), attention within region or sector blocks, or a MASTER-style factorisation.
- Survivorship bias: the AlphaPortfolio and GKX universes rely on CRSP point-in-time membership. A global build must use point-in-time constituents and delisting returns, or the cross-sectional attention will learn survivorship artifacts.

### Gaps
- I found no paper that specifically ablates stock-ID embeddings vs none, or padding-mask strategies, for cross-sectional stock transformers. The recommendations above are standard ML practice rather than finance-specific evidence.

## 5. Can transformer outputs directly parameterise a portfolio policy (softmax weights / Plackett–Luce) for policy-gradient or GRPO training?

### Takeaway
Yes. There is direct precedent for transformer or attention scores → portfolio weights trained end-to-end on a portfolio objective:
- AIPM: linear weight head, Sharpe objective
- AlphaPortfolio: CAAN winner scores → softmax over top-G/bottom-G, Sharpe objective
- Portfolio Transformer: Sharpe minus costs

For a ranking-based long-only top-K book, a Plackett–Luce policy over the per-stock scores gives a tractable log-probability (a product of successive softmaxes) usable with REINFORCE, PL-Rank or GRPO-style group-relative advantages. When the reward is differentiable in the weights, the published finance papers optimise it directly by backpropagation, which has lower variance than score-function RL.

### Cited Findings
- **AIPM**: the network output is the SDF portfolio weight vector w(X_t; Θ) for all N_t assets, trained by MSRR, a penalised least-squares form of maximum Sharpe — [NBER PDF](https://www.nber.org/system/files/working_papers/w33351/w33351.pdf)
- **AlphaPortfolio**: the portfolio generator sorts winner scores. Top-G weights are b⁺(i) = exp(s_i)/Σ_{top G} exp(s_j), and bottom-G short weights are exp(−s_i)/Σ_{bottom G} exp(−s_j). Parameters follow θ_τ = θ_{τ−1} + η∇J(θ), where J is the episode Sharpe (episode = 12 monthly periods) and "∇J(θ) is automatically calculated using the deep learning framework". In effect this is a differentiable direct-policy optimisation framed as RL — [NBER conference PDF](https://conference.nber.org/conf_papers/f160875/f160875.pdf)
- **Portfolio Transformer**: directly optimises Sharpe "under the specified transaction cost penalties", so costs enter the training loss — [arXiv](https://arxiv.org/abs/2206.03246)
- **Plackett–Luce policies**: a PL policy is a product of softmax distributions over item scores from a neural scorer and can be optimised with the log-derivative (REINFORCE) trick using sampled rankings. Naive estimators have high variance and become expensive for large candidate sets. PL-Rank gives more sample-efficient and cheaper gradient estimates — [arXiv 2105.00855](https://arxiv.org/abs/2105.00855)
- **ListMLE as a PL likelihood** (supervised analogue): ListMLE "defines the probability distribution based on the Plackett-Luce Model in a top-down style". Zhang & Wu generalise it to a long-short-aware PL model for portfolios — [arXiv 2104.12484](https://arxiv.org/abs/2104.12484)
- **GRPO** (Group Relative Policy Optimization, DeepSeekMath) estimates advantages relative to a group of sampled outputs for the same prompt, with no separate value model — [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- I found no published paper combining GRPO with a cross-sectional stock transformer portfolio policy. The nearest are RL-trained transformer portfolio policies (e.g. 2D relative-attentional gated transformer, arXiv 2101.03138) and GRPO for financial sentiment (FinSMART, arXiv 2607.28127) — [arXiv 2101.03138](https://arxiv.org/abs/2101.03138); [arXiv 2607.28127](https://arxiv.org/pdf/2607.28127)

### Inferences (design options for long-only, 10–20 holdings, weekly)
- **Policy head**: the transformer emits a scalar score s_i per stock token (masked for non-members). Options:
  - **(A) Deterministic softmax weights**: w = softmax(s/τ) restricted to the top-K by score (AlphaPortfolio-style), or sparsemax/entmax for exact sparsity. Train by backpropagating a differentiable reward such as w·r_{t+1} − cost·|w − w_prev|₁ − λ·risk. This is lower variance than RL and is what AIPM, AlphaPortfolio and PT effectively do.
  - **(B) Stochastic PL policy**: sample an ordered top-K list without replacement via Gumbel-top-k on s/τ. log π(list) = Σ_{k=1..K} [s_{(k)} − logsumexp over remaining stocks]. Weights are equal or score-softmax among the K selected. Reward is the realised next-week portfolio return, optionally net of turnover cost vs current holdings.
  - **(C) GRPO-style**: for each date, sample G portfolios (e.g. G = 16–64) from the PL policy. Advantage = (R_g − mean_G R)/std_G R. This removes date-level market moves automatically, a natural cross-sectional baseline. Add a KL penalty to a reference (e.g. supervised IC-pretrained) policy, and clip ratios as in PPO.
- **When RL (B/C) is worth it over (A)**: discrete constraints (exact K names, minimum position sizes, sector or country caps implemented by rejection), non-differentiable or path-dependent rewards (turnover with buffers, drawdown, multi-week holding), or a deliberate need for exploration or entropy. Otherwise a differentiable objective on the same scores is lower variance and simpler.
- **Practical recipe**: (1) pretrain the cross-sectional transformer with an IC or ListNet loss (supervised, stable); (2) fine-tune the score head as a PL policy with group-relative advantages and a KL anchor to the pretrained scorer; (3) evaluate net of costs against the supervised top-K-by-score baseline and a LightGBM top-K baseline. Reward variance is extreme with ~1,000 weekly dates, so the KL anchor and seed ensembling are important.
- **Temperature τ** controls concentration. With 10–20 holdings from 1,000–3,000 names, a PL policy with too high a τ will be near-uniform and the gradient signal tiny. Anneal τ or learn it.

### Gaps
- No empirical study found comparing direct differentiable Sharpe training vs REINFORCE/PL vs GRPO for stock portfolios on the same data.
- No published evidence on the variance of PL-policy gradients for K = 10–20 out of N = 1,000–3,000 with weekly rewards. PL-Rank's efficiency results are from information-retrieval benchmarks, not finance.
- AlphaPortfolio's later lower-Sharpe follow-up (>1.2) was seen only via a search summary. Its objective and design differences could not be verified.
