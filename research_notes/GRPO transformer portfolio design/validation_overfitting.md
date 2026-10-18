# Validating ML / RL weekly cross-sectional equity strategies without overfitting (solo-researcher protocol)

Context assumed throughout: weekly rebalance, ~1,000 weeks of history (2010+ data, 2016–2026 backtest = 561 weeks in the repo), long-only, 15 equal-weight holdings from ~245–290 global large caps, £10k account, Trading 212 / IBKR costs. The incumbent is a LightGBM ranking model (5-seed ensemble, weekly retrain on a rolling 260-week window, 1-week rank label, 4-week score smoothing, top-150 hold band) blended 70/30 with momentum. The challenger is a deep-learning / RL (e.g. GRPO-trained transformer) portfolio policy.

Research-method note: web fetches to arxiv.org, ssrn, nber, uzh.ch, wikipedia, neurips.cc, escholarship and readthedocs all failed with DNS errors in this session, so most cited findings come from search-engine summaries of those pages (primary-source URLs are still given). Formulas below are standard and are cross-checked against the cited implementation docs; where I could not verify a formula or number against the primary paper, that is flagged. All worked numbers were computed by me (Python, standard library) and are labelled as inferences.

---

## 1. Backtest-overfitting statistics: PBO/CSCV, PSR, DSR, MinTRL, Harvey–Liu–Zhu hurdles

### Takeaway
Treat every backtest Sharpe as the maximum of N noisy trials: deflate it (DSR) using the logged number of trials and the cross-trial Sharpe variance, require the deflated probability ≥ 0.95 on **active** (benchmark-relative) returns, estimate PBO with CSCV over the configuration grid (PBO < 0.5 is the bare minimum; aim < 0.2), and recognise that a t-stat > 3 on 10 years of data needs an annualised Sharpe/IR ≈ 0.95. On the repo's own numbers the absolute Sharpe passes every deflation test trivially, but that is because it is mostly market beta — the relevant active-return t-stat is ~1.6 (annual data) and the weekly IC t-stat is 2.86, i.e. *below* the HLZ 3.0 hurdle.

### Cited Findings
**Probability of Backtest Overfitting (PBO) and CSCV**
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting", *Journal of Computational Finance* (2017; SSRN 2326253). They argue hold-out and other standard regression anti-overfitting tools are "unreliable and inaccurate in the context of investment backtests" and propose estimating PBO via combinatorially symmetric cross-validation (CSCV), a model-free non-parametric procedure; they report CSCV gives reasonable PBO estimates with small errors — [SSRN](https://papers.ssrn.com/abstract=2326253); [Risk.net / J. Comp. Finance](https://www.risk.net/journal-of-computational-finance/2471206/the-probability-of-backtest-overfitting)
- CSCV mechanics (as implemented): split the T×N matrix of per-period returns (T periods × N strategy configurations) into S equal time blocks; for each of the C(S, S/2) ways of choosing half the blocks as in-sample (IS) and the complement as out-of-sample (OOS), pick the IS-best configuration, compute its relative OOS rank r ∈ (0,1), take the logit λ = ln(r/(1−r)); PBO = share of splits with λ ≤ 0, i.e. the IS-best configuration lands at or below the OOS median — [fynance PBO docs](https://fynance.readthedocs.io/en/latest/generated/fynance.research.pbo.html); [LuxAlgo PBO concept page](https://www.luxalgo.com/library/concept/probability-of-backtest-overfitting/)
- With S = 16 blocks there are C(16,8) = 12,870 IS/OOS splits; an open-source engine runs all 12,870 in ~0.2 s for 1,300 configurations × 3,610 bars. The R `pbo` package README states "12,780" combinations for S = 16, which appears to be a typo — [MQL5 forge PBO/CSCV engine](https://forge.mql5.io/Lerooy/pbo-cscv-engine/raw/branch/main/README.md); [CRAN pbo README](https://cran.hafro.is/web/packages/pbo/readme/README.html)
- The R `pbo` package (CRAN) implements the paper; its docs note the authors used the Sharpe ratio as the performance measure — [CRAN pbo README](https://cran.hafro.is/web/packages/pbo/readme/README.html)
- Caveat: CSCV's block reshuffling weakens strict time ordering, so PBO complements walk-forward rather than replacing it — [LuxAlgo PBO concept page](https://www.luxalgo.com/library/concept/probability-of-backtest-overfitting/)
- Practitioner thresholds (convention, not a standard): PBO > 0.50 = "more likely than not overfit"; DSR < 0.95 = "performance may be overfit" — [walk-forward-validation skill guide (secondary)](https://skillselion.com/skills/agiprolabs/claude-trading-skills/walk-forward-validation); [tradingstrategy.ai backtesting docs](https://tradingstrategy.ai/docs/learn/backtesting.html)
- Bailey et al.'s FAQ: "The most important piece of information missing from virtually all backtest reports is the number of trials attempted. Without this information, it is impossible to determine the probability of backtest overfitting." Also: a hold-out applied ~20 times at 95% confidence is expected to yield a false pass — [mathinvestor.org FAQ](https://mathinvestor.org/2014/04/faqs-on-backtest-overfitting/)

**Probabilistic and Deflated Sharpe Ratio**
- The DSR is the Probabilistic Sharpe Ratio (PSR) evaluated against a raised benchmark SR₀ = the expected maximum Sharpe of N trials (False Strategy Theorem) rather than 0 — [Wikipedia: Deflated Sharpe ratio (search summary)](https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio); [fynance DSR docs](https://fynance.readthedocs.io/en/latest/generated/fynance.research.deflated_sharpe_ratio.html)
- Expected-maximum benchmark: SR₀ = √V[{SRₙ}] · [(1−γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))], γ ≈ 0.5772 (Euler–Mascheroni), V = cross-trial variance of the trial Sharpe estimates; SR₀ = 0 if N = 1. This is the Bailey & López de Prado (2014) approximation — [endgame sharpe.py source](https://endgame-ml.readthedocs.io/en/latest/_modules/endgame/utils/sharpe.html); [fynance guards source](https://fynance.readthedocs.io/en/v2.10.0/_modules/fynance/research/guards.html)
- Sharpe ratios must be **per-period** (weekly here), not annualised, or the DSR "saturates to ~1"; the fynance default V = 1.0 is a conservative placeholder that overstates SR₀ — pass the empirical cross-trial variance — [fynance DSR docs](https://fynance.readthedocs.io/en/v2.10.1/generated/fynance.research.deflated_sharpe_ratio.html)
- Original paper: Bailey & López de Prado, "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality", *Journal of Portfolio Management* 40(5), 94–107 (2014) — [fynance DSR docs (citation)](https://fynance.readthedocs.io/en/latest/generated/fynance.research.deflated_sharpe_ratio.html)
- Asymptotic distribution of the estimated Sharpe ratio is normal with variance ≈ (1 − γ₃·SR + (γ₄ − 1)/4 · SR²)/T, γ₃ = skewness, γ₄ = (raw) kurtosis; skew and fat tails widen the error band — [Portfolio Optimizer blog on PSR/MinTRL](https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/)
- **Kurtosis-convention conflict across implementations**: the endgame code is described as plugging *excess* kurtosis into (kurtosis − 1)/4, while R `quantstrat::deflatedSharpe` uses non-excess (raw) kurtosis — [endgame sharpe.py](https://endgame-ml.readthedocs.io/en/latest/_modules/endgame/utils/sharpe.html); [quantstrat deflatedSharpe](https://www.rdocumentation.org/packages/quantstrat/versions/0.16.7/topics/deflatedSharpe)
- The expected maximum Sharpe of pure-noise trials grows roughly like √(2 ln N), so each extra order of magnitude of data-mining raises the bar by less (secondary commentary) — [WebSearch summary of quantt.co.uk "Sharpe ratio of pure noise"](https://www.quantt.co.uk/resources/sharpe-ratio-of-pure-noise)

**Minimum Track Record Length (MinTRL)**
- Bailey & López de Prado, "The Sharpe Ratio Efficient Frontier", *Journal of Risk* (2012): derives the track-record length needed to reject "true SR ≤ threshold" at a given confidence, and shows negative skew + positive excess kurtosis require longer records — [Risk.net](https://www.risk.net/journal-risk/2223785/sharpe-ratio-efficient-frontier); [IDEAS/RePEc](https://ideas.repec.org/a/rsk/journ4/2223785.html)
- PerformanceAnalytics `MinTrackRecord` implements it; its docs warn higher moments are data-intensive and its default ignores kurtosis for short series — [PerformanceAnalytics MinTrackRecord](https://www.quantargo.com/help/r/latest/packages/PerformanceAnalytics/NEWS/MinTrackRecord)

**Multiple-testing hurdles (Harvey, Liu & Zhu 2016; Harvey & Liu 2015)**
- Harvey, Liu & Zhu, "…and the Cross-Section of Expected Returns", *Review of Financial Studies* 29(1):5–68 (NBER w20592, 2014): a newly discovered factor should clear t > 3.0, not 2.0; their framework allows correlated tests and missing data, and they conclude most claimed findings in financial economics are likely false — [NBER w20592](https://nber.org/papers/w20592); [SSRN 2513152](https://papers.ssrn.com/abstract=2513152)
- Harvey & Liu, "Backtesting", *Journal of Portfolio Management* (Fall 2015): convert Sharpe → t-ratio → p-value, adjust p for the number of tests (Bonferroni / Holm / BHY), convert back; the haircut is "non-linear": high Sharpes are moderately penalised, marginal Sharpes heavily; using a flat 50% haircut is "a serious mistake"; they cite at least 316 factors tested; they also define a minimum-average-return profit hurdle — [Harvey & Liu P120 Backtesting PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF); [CME copy](https://www.cmegroup.com/content/dam/cmegroup/education/files/backtesting.pdf); [rdocumentation profit.hurdle](https://www.rdocumentation.org/link/profit.hurdle)
- R code for the Harvey–Liu haircut exists in quantstrat's sandbox (`Haircut_SR`) — [rdrr.io quantstrat sandbox](https://rdrr.io/github/braverock/quantstrat/src/sandbox/Harvey_Liu_Backtesting/50a170e4e37da951ea1192888418c82a/Haircut_SR%20with%20sample_random_multests.R)

### Inferences
**Formulas to implement (all in weekly units; T = number of weekly returns; γ₃ = skew; γ₄ = raw kurtosis, = 3 for a normal):**
- PSR(SR*) = Φ( (ŜR − SR*)·√(T − 1) / √(1 − γ₃·ŜR + (γ₄ − 1)/4·ŜR²) ).
- DSR = PSR(SR₀), with SR₀ from the expected-maximum formula above, N = number of *effectively independent* trials, V = variance of the N trial Sharpes (weekly units).
- MinTRL(SR*, α) = 1 + (1 − γ₃·ŜR + (γ₄ − 1)/4·ŜR²)·(Z₁₋α / (ŜR − SR*))² weeks. (This is PSR = 1 − α solved for T; I could not open the primary paper to confirm its typography, but it follows algebraically from the PSR above.)
- Kurtosis sanity check: with γ₄ = 3 (normal) the variance term becomes 1 + ŜR²/2, which is Lo's (2002) iid-normal result. If an implementation feeds *excess* kurtosis (0 for normal) into (γ₄ − 1)/4 it gets −¼·SR² — wrong sign. So use raw kurtosis in (γ₄ − 1)/4, or excess kurtosis in (γ₄ₑ + 2)/4.
- Harvey–Liu–Zhu in Sharpe units: t ≈ SR_annual·√years (iid approximation). t > 3 needs SR ≥ 0.95 over 10 years and ≥ 0.67 over 20 years; t > 2 needs 0.63 (10 y) / 0.45 (20 y). One-sided Bonferroni z-hurdles at 5% family-wise: N = 10 → 2.58; 50 → 3.09; 100 → 3.29; 1,000 → 3.89.

**Worked numbers (generic; skew −0.5, raw kurtosis 5, T = 520 weeks = 10 years):**
- PSR(0) for annual SR 0.5 / 0.8 / 1.0 = 0.939 / 0.993 / 0.999 — i.e. absolute PSR is nearly uninformative for a long-only equity book with market-like Sharpe.
- DSR for an observed annual SR of 1.0 when the cross-trial SD of annual Sharpes is 0.4: N = 10 → SR₀ = 0.63 annual, DSR 0.87; N = 20 → 0.76, DSR 0.77; N = 50 → 0.91, DSR 0.61; N = 100 → 1.01, DSR 0.49. With cross-trial SD 0.2, N = 100 gives SR₀ = 0.51 and DSR 0.93. **The cross-trial dispersion matters as much as N.**
- MinTRL (95% one-sided, same moments): to show SR > 0 — annual SR 0.5 needs 586 weeks (11.3 y), 0.8 → 236 w (4.5 y), 1.0 → 154 w (3.0 y), 1.5 → 73 w (1.4 y). To show SR > 0.5 (i.e. beat a passive-like Sharpe) — SR 1.0 needs 614 w (11.8 y); SR 0.8 needs 1,670 w (32 y).

**Applied to this repo (computed from `reports/backtest/weekly_*.csv`, `summary.json`, `by_year.csv`, `docs/phase1b_variants*.csv`):**
- Blended strategy: T = 561 weeks, weekly SR 0.164 (annual 1.18), skew −0.53, raw kurtosis 4.85. ML-only: annual 1.27; momentum-only: 0.91. PSR(0) = 0.9999.
- Logged trials: 88 rows in the two phase-1b variant grids (plus the 12-combination tuning grid and seed variants), mean dev Sharpe 1.16, cross-trial SD 0.126. DSR (absolute returns) stays ≥ 0.99 for N up to 200 with SD 0.126, and 0.87–0.94 if one assumes SD 0.3. **So absolute-return DSR passes — but it is the wrong test.** The equal-weight same-universe benchmark has Sharpe 1.19, *equal* to the strategy's 1.18. Skill must be judged on active returns.
- Active return vs equal-weight universe, annual (11 calendar-year observations, 2026 partial): mean +7.8 pts/yr, SD 15.9 pts, IR ≈ 0.49, t ≈ 1.6. 2020 alone contributes +43.7 pts; 2022 was −17.6 pts. Weekly IC: mean 0.0225, t = 2.86 (ML), 2.59 (blend) — **below the t > 3 HLZ hurdle** once ~100 trials are acknowledged (Bonferroni z at N = 100 is 3.29).
- Implication for the new model: the burden of proof is on active returns / IC, not on raw Sharpe; and the LightGBM baseline itself is not yet "significant" under a multiple-testing hurdle, which lowers the bar for "is the challenger different?" but not for "is the challenger real?".

**Practical rules:**
- Log every configuration run (architecture, hyper-params, reward shapes, checkpoints chosen, seeds) to a trial ledger *before* looking at OOS numbers; N for the DSR is the ledger length, discounted for correlated trials (e.g. cluster trials by return correlation and count clusters — López de Prado proposed this, but I did not verify the specific paper in this session).
- Run CSCV on the weekly *active* returns of the whole grid, S = 16 (≈ 35 weeks per block for 561 weeks; 62 weeks per block for 1,000 weeks); report PBO, the λ histogram, and the IS-vs-OOS Sharpe regression slope (performance degradation).

### Gaps
- Could not open the DSR or PBO primary papers; the DSR paper's own worked example (inputs/outputs) is unverified. The search engine could not confirm a worked example matching "100 trials, 1,250 days, skew −3, kurtosis 10".
- The exact "effective number of trials" method (clustering) is not verified from a primary source here.
- No primary-source confirmation of a recommended S for CSCV beyond implementations that use S = 16.

---

## 2. Cross-validation with overlapping labels: purging, embargo, CPCV, walk-forward, nested validation; how many independent test periods

### Takeaway
For a weekly model with a 1-week label, label overlap is tiny but *feature* overlap is large (12-month momentum, 4-week score smoothing, rolling volatility), so purge ≥ the label horizon and embargo ≥ the longest smoothing/serial-dependence window (≈ 4–13 weeks). Use walk-forward (rolling 260-week window, to match the live system) as the primary "what you would have traded" record, CPCV (e.g. N = 10 groups, k = 2 → 45 splits, 9 full paths) for a distribution of OOS Sharpes, and nested walk-forward for hyper-parameters. 20 years of weekly data give ~1,000 weekly observations but only ~15–20 annual blocks and a handful of regimes — the binding constraint is regime count, not week count.

### Cited Findings
- **Purging**: remove from the training set any observation whose label interval overlaps in time with any test-label interval. **Embargo**: additionally drop training observations immediately *after* a test block, to stop leakage via serially-correlated features — [Purged cross-validation (Wikipedia, search summary)](https://en.wikipedia.org/wiki/Purged_cross-validation); [mizarlabs CPCV docs](https://mizarlabs.readthedocs.io/en/latest/mizarlabs.model.html); [Towards AI CPCV explainer](https://towardsai.com/p/l/the-combinatorial-purged-cross-validation-method)
- Embargo sizing: one practitioner rule of thumb is an embargo of ~1% of bars (described relative to the test set); other sources give no fixed size — [Return on Effort newsletter](https://returnoneffort.beehiiv.com/p/mitigating-overfitting-advanced-crossvalidation); [Towards AI](https://pub.towardsai.net/the-combinatorial-purged-cross-validation-method-363eb378a9c5) (sources disagree; López de Prado's book is the primary reference and was not accessible here)
- **CPCV** (López de Prado 2018, *Advances in Financial Machine Learning*): partition the timeline into N groups, use every combination of k test groups, purge/embargo at each boundary; number of splits = C(N, k) (e.g. N = 6, k = 2 → 15 splits); because each group appears in k·C(N,k)/N splits, the number of complete backtest paths is φ = (k/N)·C(N, k) = C(N−1, k−1) (N = 6, k = 2 → 5 paths) — [skfolio CombinatorialPurgedCV source](https://skfolio.org/_modules/skfolio/model_selection/_combinatorial.html); [fynance combinatorial_purged_cv](https://fynance.readthedocs.io/en/latest/generated/fynance.data.combinatorial_purged_cv.html); [Towards AI](https://towardsai.com/p/l/the-combinatorial-purged-cross-validation-method)
- Comparative evidence: Arian et al. (2024) compared out-of-sample testing methods for ML in finance and (as reported by a later paper) found CPCV better at reducing overfitting risk, while walk-forward remains the industry standard for realistic trading simulation — [arXiv 2512.12924 (secondary citation of Arian et al. 2024)](https://arxiv.org/pdf/2512.12924)
- Hold-out alone does not control for the number of variants tried — [mathinvestor.org FAQ](https://mathinvestor.org/2014/04/faqs-on-backtest-overfitting/)

### Inferences
**Recommended split design for ~1,000 weeks (2007/2010–2026):**
- *Outer layer — walk-forward, rolling window = 260 weeks (to match the live retrain), expanding as a robustness variant.* Rolling suits non-stationary cross-sectional relations and keeps the model comparable to the LightGBM incumbent; expanding gives more data to a data-hungry transformer. Run both; pre-register rolling as primary for like-for-like comparison.
- *Purge* = label horizon h (1 week for next-week rank; 4 weeks if a 4-week label is used). *Embargo* ≥ max(h, score-smoothing window = 4 weeks); 13 weeks is a conservative choice given 12-1 momentum features. The repo already enforces "train only on labels fully known before T" (`PLAN.md` §6) — that is purging; there is no explicit post-test embargo because walk-forward never trains on data after the test week, so embargo matters only for CPCV/k-fold splits, where training data can lie after the test block.
- *Middle layer — CPCV for the distribution of OOS performance.* With 1,000 weeks: N = 10 groups (100 weeks ≈ 2 years each), k = 2 → 45 train/test splits, 9 complete paths; N = 10, k = 3 → 120 splits, 36 paths (but each training set is only 70% of data); N = 12, k = 2 → 66 splits, 11 paths. Report the distribution (median, IQM, 10th percentile) of path Sharpes/IRs, not just the mean. Caveat: CPCV trains on future data relative to some test groups — acceptable for estimating model *quality* but not for the "tradable record" (use walk-forward for that).
- *Inner layer — nested validation for hyper-parameters.* Inside each outer training window, carve the last 52–104 weeks (after a purge + embargo gap) as validation; tune on it; refit on the full outer window; evaluate once on the outer test block. Early stopping (epochs / RL updates) is a hyper-parameter and must also use only the inner validation block.
- *Final untouched hold-out.* The repo's "untouched" holdout (Jul 2024 – Oct 2026) has a `hold_sharpe` column for all 88 phase-1b variants, so it has been looked at many times and is no longer clean for the *challenger*. The only clean holdout left is forward paper trading from 17 Oct 2026 (repo §15) — or a held-out region (see §5).

**How many independent test periods exist:**
- Weekly returns with a 1-week label: ~1,000 non-overlapping weekly observations (≈ 520–560 in a 2016–2026 backtest). With a 4-week label, only ~250 non-overlapping.
- Standard error of an annualised Sharpe (iid normal, SR ≈ 1): √((1 + SR_w²/2)/T)·√52 ≈ 1.00 for 1 year, 0.58 for 3 years, 0.32 for 10 years, 0.23 for 1,000 weeks.
- Regime-level independence is far lower: ~20 calendar years, ~15 annual OOS folds after a 5-year burn-in, and perhaps 4–6 distinct regimes (GFC tail, 2010s QE, 2020 Covid, 2022 rate shock, 2023–26 AI/mega-cap). Momentum and growth tilts are regime-dependent, so the effective sample for "does this work across regimes" is single digits. This argues for sub-period and cross-region tests rather than more folds.

### Gaps
- López de Prado's exact embargo recommendation (often quoted as h ≈ 0.01·T) could not be verified from the book here; sources conflict on whether the 1% refers to the whole sample or the test set.
- The Arian et al. (2024) paper itself (venue, exact metrics) was not retrieved — only a secondary citation.

---

## 3. RL-specific evaluation: seed variance, IQM and stratified bootstrap, one-path overfitting, early stopping, seed ensembles

### Takeaway
Deep-RL results swing wildly with the random seed, so a GRPO/transformer policy must be trained with ≥ 10 seeds per configuration (the repo already saw a 5-point CAGR swing across LightGBM seeds), reported as a distribution (IQM + stratified-bootstrap 95% CI + probability of improvement over the LightGBM seeds), selected with early stopping on an inner validation block only, and deployed as a seed ensemble. Count every seed × checkpoint × hyper-parameter trial in the DSR ledger.

### Cited Findings
- Henderson et al., "Deep Reinforcement Learning that Matters" (AAAI 2018): averaging results across different random seeds can produce misleading reports; experiments used 5 trials per evaluation with OpenAI Baselines on Hopper-v1 and HalfCheetah-v1 — [arXiv 1709.06560](https://arxiv.org/abs/1709.06560); [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/11694/11553)
- Colas et al. ("How Many Random Seeds?", 2018) describe the Henderson result: running the same algorithm with 10 seeds and averaging two splits of 5 seeds gives learning curves that seem to come from different distributions, which can lead to claims that two algorithms differ when they do not; Colas et al. propose statistical power analysis to choose the number of seeds — [arXiv 1806.08295](https://arxiv.org/pdf/1806.08295)
- Agarwal, Schwarzer, Castro, Courville & Bellemare, "Deep RL at the Edge of the Statistical Precipice" (NeurIPS 2021 Outstanding Paper): most results report point estimates of mean/median over few runs and ignore uncertainty; on Atari 100k, point estimates and proper interval estimates gave substantially different conclusions; few-run median scores were overestimated for CURL, SPR and DrQ and underestimated for DER; discrepancies also on ALE, Procgen and DM Control — [arXiv 2108.13264](https://arxiv.org/abs/2108.13264v4); [NeurIPS oral](https://neurips.cc/virtual/2021/oral/26713); [AIhub summary](https://aihub.org/2022/01/19/rliable-towards-reliable-evaluation-and-reporting-in-reinforcement-learning)
- Recommendations: interval estimates via **stratified bootstrap CIs** (resample runs within each task), **performance profiles** (score distributions) instead of tables of means, and **IQM** (mean of the middle 50% of pooled runs) instead of mean or median; also report **probability of improvement** and **optimality gap**. IQM is robust to outliers and more statistically efficient than the median; the median "requires a large number of runs to claim improvements" — [rliable GitHub](https://github.com/google-research/rliable); [rliable PyPI](https://pypi.org/project/rliable)
- rliable code examples use 50,000 bootstrap reps for aggregate-metric CIs and 2,000 for probability of improvement; the repository was archived (read-only) in Oct 2025 — [rliable GitHub](https://github.com/google-research/rliable)
- IQM implementation detail (third-party): trim the top and bottom 25% of pooled normalised scores, average the rest; resample seeds independently within each stratum — [evaluma IQM docs](https://evaluma.readthedocs.io/en/stable/autoapi/evaluma/methods/iqm/index.html)
- Repo evidence (`config.yaml`, `PLAN.md` §13): single LightGBM seeds ranged 23–28% CAGR; "a single seed's luck moved backtest CAGR by up to 5 points"; with 15 positions "one different borderline pick changes every later trade", so the plan treats any single backtest as ±3 pts (full period) and ±6 pts (holdout). (Local file evidence, `/home/user/weekly-quant/PLAN.md`.)

### Inferences
**Mapping rliable to a trading backtest.** "Tasks" = strata that should not be pooled naively: e.g. CPCV paths, or sub-periods (2016–18, 2019–21, 2022–24, 2024–26), or regions (US, UK, EU, …). "Runs" = seeds. Score = annualised net active return or IR per (seed, stratum).
- *IQM across seeds:* with 10 seeds × 4 sub-periods = 40 scores, drop the 10 lowest and 10 highest, average 20.
- *Stratified bootstrap CI:* resample seeds with replacement *within* each stratum, recompute IQM, 10,000+ reps, take 2.5/97.5 percentiles.
- *Probability of improvement* P(X > Y): share of (challenger seed, LightGBM seed) pairs, per stratum, where the challenger's score is higher, averaged over strata; bootstrap its CI. Decision: CI lower bound > 0.5.
- Also report the challenger *seed-ensemble* score separately: the ensemble is what gets traded; the per-seed distribution measures how much luck is in it.

**Seed count.** Five seeds (Henderson's setup) were shown to be insufficient to separate algorithms. Use ≥ 10 seeds for the challenger, and re-run the LightGBM incumbent with the same 10 seeds so P(improvement) compares like with like. If seed SD of IR is σ_s and you want the seed-mean IR within ±0.1, you need n ≈ (1.96·σ_s/0.1)² seeds — with σ_s ≈ 0.15 that is ≈ 9 seeds. (Inference; Colas et al. give the general power-analysis approach.)

**Training-on-one-path overfitting (specific to RL on historical markets).** An RL agent trained on the single realised 2010–2024 path can memorise date-specific patterns (e.g. "hold NVDA in 2023"), especially a transformer with stock-identity embeddings. Mitigations:
- No stock-ID or calendar-date features; use only cross-sectionally normalised, point-in-time features, so the policy must generalise across names.
- Train on resampled episodes: random start dates, random sub-universes (e.g. random 60% of names per episode), block-bootstrapped week sequences, and cross-sectional permutation of stock order (transformers without positional encoding over stocks are permutation-equivariant by design).
- Make the reward net of the exact cost model (FX 15 bps, UK stamp 50 bps, 10 bps slippage) and turnover; otherwise RL learns to churn.
- Check a simple degenerate policy: does the agent beat "rank by the LightGBM score and take top-15" when given the LightGBM score as an input? If not, the RL layer adds nothing.

**Early stopping without test leakage.** Pick the checkpoint by inner-validation IR (purged + embargoed block at the end of each training window), not by the OOS fold; freeze the stopping rule (e.g. patience = 5 evaluations, metric = validation IR net of costs) before running any outer fold. Count "which checkpoint" choices as trials. A cheap guard: report OOS results for the *last* checkpoint and the *validation-best* checkpoint; a large gap between them flags instability.

**Ensembling across seeds.** Average the policies' target weights (or scores, then rank) across seeds; this reduced seed sensitivity for the incumbent. Ensembling cannot fix a model with no edge, so the per-seed distribution must pass first.

**GRPO-specific note.** GRPO normalises rewards within a group of sampled actions/portfolios; on one historical path the group baseline only removes common market moves per week, so the policy gradient is effectively a cross-sectional ranking signal — compare it directly to the LightGBM IC, not to absolute returns.

### Gaps
- Could not open Agarwal et al. to confirm the exact numbers of runs used in surveyed papers (often quoted as 3–5 or 3–10) or which Atari 100k conclusions flipped.
- No finance-specific peer-reviewed study of seed variance for RL portfolio agents was found in this session.
- Colas et al.'s recommended seed counts for given effect sizes were not retrieved.

---

## 4. Comparing two strategies' Sharpe ratios; block/stationary bootstrap; weeks of paper trading needed

### Takeaway
Use the Ledoit–Wolf (2008) studentized block-bootstrap test (or its HAC version) on paired weekly returns; Jobson–Korkie/Memmel is invalid under fat tails and serial correlation. Power is brutal: with SRs of 1.0 vs 0.7 and return correlation 0.8, detecting ΔSR = 0.3 with 80% power takes ~35 years of weekly data (~9 years even at correlation 0.95). Paper trading therefore cannot *prove* superiority in any reasonable time; use it to check implementation and to apply a pre-set kill rule, and make the adoption decision on the backtest protocol plus IC-based tests, which are more powerful.

### Cited Findings
- Ledoit & Wolf, "Robust Performance Hypothesis Testing with the Sharpe Ratio", *Journal of Empirical Finance* 15(5):850–859 (2008): the Jobson–Korkie test (corrected by Memmel) is not valid when returns have tails heavier than normal or are time-series dependent; they build a studentized time-series bootstrap CI for the Sharpe difference and reject equality if 0 is outside it; resampling observed (not null-restricted) data; simulation shows better finite-sample performance — [LW 2008 PDF (uzh.ch)](https://uzh.ch/cmsssl/econ/dam/jcr:ffffffff-935a-b0d6-0000-00007214c2bc/jef_2008pdf.pdf); [CORE record](https://core.ac.uk/works/4359613)
- A HAC standard error (Andrews 1991; Andrews & Monahan 1992) is valid asymptotically but can be unsatisfactory in finite samples, motivating the bootstrap — [Ledoit et al. 2011 Wilmott](https://uzh.ch/cmsssl/econ/dam/jcr:520edf26-2322-4708-8dde-51d61141914a/Ledoit_et_al-2011-Wilmott_Robust_Performance.pdf)
- R `PeerPerformance::msharpeTesting` implements the test: `type = 1` asymptotic (HAC), `type = 2` studentized circular bootstrap — [PeerPerformance docs](https://www.rdocumentation.org/packages/PeerPerformance/versions/2.3.2/topics/msharpeTesting)
- Critique: the test has limited power in practice; Sharpe *differences* behave differently from Sharpe ratios — [Econ Journal Watch, O'Connor 2024](https://econjwatch.org/file_download/1300/OConnorMar2024.pdf)
- Block-length choice: Politis & White (2004, *Econometric Reviews* 23) give data-driven optimal block sizes for block/stationary bootstraps, based on flat-top lag-window spectral estimation; corrected by Patton, Politis & White (2009) after an error in Lahiri's stationary-bootstrap variance; implementations: R `blocklength::pwsd()`, `np::b.star()` (feeds `tsboot`) — [IDEAS/RePEc](https://ideas.repec.org/a/taf/emetrv/v23y2004i1p53-70.html); [Patton–Politis–White 2009 correction](https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf); [blocklength README](https://cran.r-project.org/web/packages/blocklength/readme/README.html); [np b.star](https://www.rdocumentation.org/packages/np/versions/0.70-5/topics/b.star)
- Applied example: a 2026 ETF-portfolio paper uses a paired stationary block bootstrap across strategies, citing Ledoit–Wolf (2008) and Politis–White block length — [arXiv 2606.08283](https://arxiv.org/pdf/2606.08283)

### Inferences
**Formulas (weekly per-period Sharpes SR₁, SR₂; return correlation ρ; T weeks):**
- Jobson–Korkie/Memmel asymptotic variance of the difference (iid normal): Var(ŜR₁ − ŜR₂) ≈ (1/T)·[2(1 − ρ) + ½(SR₁² + SR₂² − 2·SR₁·SR₂·ρ²)]; z = (ŜR₁ − ŜR₂)/√Var. (From memory of Memmel 2003; not verified against a primary text in this session — but it is the baseline that LW 2008 explicitly replaces.)
- Required sample for power 1 − β, two-sided α: T ≈ (z₁₋α/₂ + z₁₋β)²·[2(1 − ρ) + ½(SR₁² + SR₂² − 2SR₁SR₂ρ²)] / (SR₁ − SR₂)².
- Ledoit–Wolf procedure (practical): (1) paired weekly returns (r₁ₜ, r₂ₜ); (2) choose block length b by Politis–White on the series of the influence function or simply b ≈ T^{1/3} (≈ 8–10 weeks for 561–1,000 weeks); (3) circular block bootstrap of *pairs* (keeps cross-correlation), M ≥ 5,000 reps; (4) studentize each bootstrap difference by its HAC SE; (5) CI for ΔSR from the bootstrap distribution of the studentized statistic; reject if 0 ∉ CI. For a quick version, use `PeerPerformance` (R) or a percentile block bootstrap (less accurate).

**Worked numbers for ΔSR = 0.3 (annual SR 1.0 vs 0.7):**
| ρ (weekly return correlation) | weeks for 80% power | years | SE of annual ΔSR after 1 y / 10 y |
|---|---|---|---|
| 0.0 | 9,135 | 176 | 1.42 / 0.45 |
| 0.5 | 4,585 | 88 | 1.01 / 0.32 |
| 0.8 | 1,840 | 35 | 0.64 / 0.20 |
| 0.9 | 923 | 18 | 0.45 / 0.14 |
| 0.95 | 463 | 9 | 0.32 / 0.10 |
Even for 50% power at ρ = 0.9 you need ~450 weeks (8.7 y). Two long-only books drawn from the same 245 large caps will typically have ρ ≈ 0.8–0.95 because both are dominated by the market factor — which helps, but not enough for a 6–12 month paper trial.

**Applied to repo (computed from `reports/backtest/weekly_ml.csv` vs `weekly_baseline.csv`, 561 weeks):** ML-only annual SR 1.27 vs momentum-only 0.91, ρ = 0.75; ΔSR = 0.37, Memmel SE 0.22, z = 1.70, two-sided p = 0.09; circular block bootstrap (b = 8, 5,000 reps, percentile) 95% CI for annual ΔSR = [−0.06, +0.78]. So even the incumbent's apparent 0.37 Sharpe advantage over its own momentum baseline is not significant after 10.8 years.

**More powerful alternatives for the adoption decision:**
- *IC-difference test:* weekly cross-sectional IC uses ~245 stocks per week, so it is less noisy than portfolio returns. Incumbent weekly IC: mean 0.0225, t = 2.86 over 561 weeks ⇒ weekly IC SD ≈ 0.186. Paired weekly ΔIC with IC correlation 0.7 has SD ≈ 0.144; detecting ΔIC = 0.01 at 80% power needs ≈ 1,600 weeks, ΔIC = 0.02 needs ≈ 400 weeks. Use Newey–West SEs (lag ≈ 4–8) because ICs are autocorrelated.
- *Active-return regression:* regress challenger weekly returns on incumbent weekly returns; test the intercept (alpha of challenger beyond incumbent) with HAC SEs. A significant intercept and β < 1 also argue for a blend rather than a swap.

**What paper/live trading is for (from 17 Oct 2026):**
- Implementation shortfall: compare fills vs Monday-close model (`paper/t212_practice/comparison.md` already does this); expect to learn the cost model's error within ~3–6 months.
- Kill rule (one-sided, pre-registered): stop the challenger if its cumulative active return vs the incumbent falls below −2 × σ_active × √(weeks/52) (e.g. with tracking error 8%/yr vs incumbent: −16 pts after 1 year, −22.6 pts after 2 years — a deliberately loose 2σ rule that only catches clear failure), or if live IC is < 0 with t < −2 after 52 weeks.
- Promotion rule: do *not* require live significance (impossible); require that live results are *consistent* with the backtest (live IR inside the backtest's bootstrap 90% band) for ≥ 26–52 weeks.

### Gaps
- Could not open LW 2008 to confirm their recommended block sizes and bootstrap reps (I recall they used b ∈ {1, 2, 4, 6, 8, 10} with a calibration step, M = 4,999 — unverified).
- No source located for a finance-specific power table for Sharpe differences; the table above is my calculation from the iid-normal Memmel variance, which *understates* required sample size under fat tails/autocorrelation.

---

## 5. Synthetic-data and placebo tests

### Takeaway
Before trusting any OOS number, the challenger must (a) show no skill on noise and shuffled labels, (b) recover a planted signal, (c) beat a distribution of random 15-stock portfolios drawn under the same constraints from the same (survivorship-biased) universe, and (d) work in ≥ 2 of 3 sub-periods and in at least one region it was not tuned on. These tests are cheap, pre-registerable, and catch leakage and selection effects that statistics on returns cannot.

### Cited Findings
- Bailey et al.'s online tool calibrates a strategy on pseudorandom returns; "after a few hundred iterations, it is trivial to find highly profitable strategies in-sample, despite the small number of parameters involved. Performance out-of-sample is, of course, utterly disappointing" — [mathinvestor.org FAQ](https://mathinvestor.org/2014/04/faqs-on-backtest-overfitting/)
- Sharpe-ratio haircuts are non-linear and depend strongly on the number of trials and adjustment method — [Harvey & Liu 2015](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF); [arXiv 1905.05023 (covariance-penalty approach)](https://arxiv.org/pdf/1905.05023)
- Repo evidence: `tests/` already enforce that on synthetic pure-noise prices the model shows no skill, that a planted signal is found, and that changing future prices does not change past features; phase-1b variant files record Sharpe by sub-period (2016–18, 2019–21, 2022–24H1) (local: `/home/user/weekly-quant/PLAN.md` §6, `/home/user/weekly-quant/docs/phase1b_variants.csv`).

### Inferences
**Placebo battery to pre-register (each with a pass rule):**
1. *Cross-sectional label shuffle:* within each week, permute next-week returns across stocks (preserves market return and volatility, destroys cross-sectional signal). Train the full pipeline (same seeds, same epochs). Pass: OOS IC within ±2 SE of 0, IR vs equal-weight within ±2 SE of 0. Repeat ≥ 20 permutations to get a null distribution for IC and IR; the real model's OOS IC should exceed the 95th percentile.
2. *Time-shift placebo:* shift labels by +k weeks (k = 4, 13): any "skill" that survives implies the model is picking persistent characteristics (or leaking), not predicting next-week returns.
3. *Random-signal portfolios:* replace scores with random ranks but keep every portfolio rule (15 names, top-150 hold band, 4-week smoothing, country cap, costs). Run 1,000 draws. This gives the distribution of CAGR/Sharpe purely from the universe + rules; for this universe the equal-weight benchmark already has Sharpe 1.19, so expect random portfolios around there. The challenger's percentile in this distribution is a direct, survivorship-matched p-value.
4. *Synthetic market with planted signal:* simulate returns = factor model + small planted cross-sectional signal (IC ≈ 0.02, the incumbent's level). Pass: the challenger recovers IC within 50% of the planted value and does not exceed it materially (exceeding = leakage).
5. *Held-out regions:* tune on US only; test frozen model on UK/EU/CH/Nordic/CA (or vice versa). Pass: positive IC with t > 2 in the held-out block. With ~290 names split by region, the per-region cross-section is small (tens of names), so use IC rather than 15-name portfolio returns.
6. *Sub-period stability:* report IR and IC for 2016–18, 2019–21, 2022–24, 2024–26 (and 2010–15 if data allow). Pass: positive in ≥ 3 of 4, and no single period > 50% of total active return. (The incumbent's annual active returns fail the concentration check: 2020 alone is +43.7 of the cumulative ~86 pts of annual excess, ≈ 50%.)
7. *Feature ablation / "is it just momentum?":* regress challenger active returns on the momentum baseline's active returns; report alpha t-stat.

### Gaps
- No published practitioner guide (Man AHL, AQR, Two Sigma, Quantopian) was retrievable in this session to cite specific placebo protocols; the battery above is my synthesis.

---

## 6. Survivorship bias, benchmark choice, realistic costs

### Takeaway
The repo's universe is *today's* large caps, so every backtest is optimistic; published estimates of survivorship/delisting bias range from ~1.6 to ~5 percentage points a year for broad equity samples, and more for concentrated or equal-weighted books. Always judge the challenger on net active return over the **equal-weight same-universe** benchmark (which shares the bias), report gross and net of the exact cost model, and run a 2× cost stress test.

### Cited Findings
- Price, Beaver & McNichols (via Alpha Architect): adding CRSP delisting returns to a book-to-market strategy cut the deep-value mean annual return from ~30.1% to ~24.6% — [Alpha Architect](https://alphaarchitect.com/2016/08/dealing-with-delistings-a-critical-aspect-for-stock-selection-research/)
- Indian small caps 2016–2025 (1,437 stocks, 2026 preprint, peer-review status unknown): survivor-only backtests overstate annual returns by ~4.9 pts (~21% → ~26%) — [arXiv 2603.19380](https://arxiv.org/pdf/2603.19380)
- US equities 1926–2001 (blog citing CRSP): ~1.6 pts/yr gap between survivorship-free and survivorship-biased data (7.4% vs 9.0%) — secondary, unverified — [LuxAlgo blog](https://luxalgo.com/blog/survivorship-bias-in-backtesting-explained)
- Crypto 2014–2021: ~0.93%/yr bias for value-weighted vs ~62%/yr for equal-weighted portfolios — weighting scheme dominates the size of the bias — [University of St. Gallen](https://alexandria.unisg.ch/handle/20.500.14171/108037)
- Repo evidence (local `/home/user/weekly-quant/PLAN.md` §4, §13; `/home/user/weekly-quant/config.yaml`): universe = today's large caps; plan already treats excess over the equal-weight universe (~7 pts/yr) as an upper bound; recommended survivorship-free sources: Norgate Data or Sharadar (~$30–60/month, US), EODHD/FMP (~$20–80/month, global); cost model = 10 bps slippage, buy taxes UK 50 / FR 30 / IT 10 / ES 20 bps, T212 FX fee 15 bps; first run with ~50%/week turnover paid 7.7%/yr in costs; current settings 0.8%/yr cost drag at 5.2%/week turnover.

### Inferences
- **Primary benchmark:** equal-weight portfolio of the same point-in-time universe, rebalanced weekly with the same cost model (shares survivorship and size/equal-weight tilt). **Secondary:** real investable funds (VWRL, VUSA) for "was it worth it?". **Tertiary:** the incumbent LightGBM blend (the decision benchmark for the challenger).
- **Survivorship-bias stress:** (i) re-run on a survivorship-free US dataset (Norgate/Sharadar) for the US sub-universe — the challenger must keep a positive active return; (ii) apply a haircut of 2–5 pts/yr to absolute returns when quoting expected performance; (iii) check whether the challenger's excess concentrates in names that *entered* the universe because they won (e.g. 2020–2024 semiconductor winners). Deep models with more capacity are more likely than LightGBM to exploit "future large cap" structure in a survivorship-biased universe, so the bias likely flatters the challenger more than the incumbent.
- **Costs:** report gross, net (model costs), and 2× costs. RL policies trained on gross rewards will learn high turnover; at £10k with 15 names (~£650 each), T212 has no commission but FX (15 bps) and UK stamp (50 bps) dominate; IBKR minimums (£1/€1.25 per international trade) matter for small tickets. Reconcile against `paper/t212_practice/comparison.md` fills after 3 months.

### Gaps
- No global-large-cap-specific estimate of survivorship bias was found; the cited magnitudes are from US, India, crypto and value-strategy samples.

---

## 7. Pre-registration checklist: new deep-learning / RL model vs the LightGBM baseline

### Takeaway
Write and commit (git timestamp) a one-page protocol *before* any challenger OOS number is seen: primary metric (net weekly active return vs equal-weight universe, IR), splits (rolling 260-week walk-forward + CPCV N = 10/k = 2 with purge 1 w and embargo 13 w + nested inner validation), trial ledger for the DSR, ≥ 10 seeds with IQM/stratified-bootstrap reporting, the placebo battery, and explicit adopt / blend / reject rules. Default to the incumbent when evidence is ambiguous.

### Cited Findings
- Report the number of trials; without it PBO cannot be assessed — [mathinvestor.org FAQ](https://mathinvestor.org/2014/04/faqs-on-backtest-overfitting/)
- Use DSR (trial-adjusted, non-normality-adjusted) and PBO together, with walk-forward and forward confirmation — [tradingstrategy.ai backtesting docs](https://tradingstrategy.ai/docs/learn/backtesting.html); [LuxAlgo PBO](https://www.luxalgo.com/library/concept/probability-of-backtest-overfitting/)
- Report interval estimates (stratified bootstrap), IQM and probability of improvement for multi-seed RL — [rliable GitHub](https://github.com/google-research/rliable)
- Use robust (LW 2008) rather than Jobson–Korkie tests for Sharpe differences — [LW 2008](https://uzh.ch/cmsssl/econ/dam/jcr:ffffffff-935a-b0d6-0000-00007214c2bc/jef_2008pdf.pdf)
- t > 3 hurdle for new "factors" given multiple testing — [NBER w20592](https://nber.org/papers/w20592)
- Repo rule already in place: "If ML can't beat the simple baseline after costs, we trade the baseline" (local `/home/user/weekly-quant/PLAN.md` §6).

### Inferences
**Pre-registration checklist (commit as `research/preregistration_<model>.md` before running outer folds):**

A. *Question & metrics*
1. Hypothesis: "Challenger's net weekly active return vs equal-weight universe exceeds the LightGBM blend's" (one-sided).
2. Primary metric: annualised IR of net weekly active returns (vs EW universe). Secondary: weekly rank IC (mean, Newey–West t), net CAGR, max drawdown, turnover, cost drag. Same cost model (`config.yaml` `costs:`), same portfolio rules (15 names, hold band, smoothing, country cap) for both models — so differences come from the score, not the rules.
3. Unit of observation: weekly; T, start/end dates fixed.

B. *Data & leakage*
4. Point-in-time universe definition; list of known biases (survivorship); planned survivorship-free US re-test.
5. Feature list with look-back lengths; no stock-ID/calendar features for the transformer.
6. Leak tests pass (noise → no skill; planted signal recovered; future-price perturbation leaves past features unchanged).

C. *Splits*
7. Outer: rolling 260-week walk-forward, weekly (or 4-weekly for compute) retrain, min 156 weeks history — identical to incumbent. Robustness: expanding window.
8. CPCV: N = 10 groups, k = 2 (45 splits, 9 paths); purge = label horizon (1 w); embargo = 13 w.
9. Inner (hyper-params, early stopping): last 52–104 weeks of each training window after a purge+embargo gap. Max hyper-parameter budget declared up front (e.g. ≤ 30 configurations).
10. Hold-outs: forward paper trading from 17 Oct 2026 (clean); held-out region(s) named in advance. Declare that Jul 2024–Oct 2026 is *not* clean (it was viewed for 88 incumbent variants).

D. *Trials & seeds*
11. Trial ledger file (append-only): every configuration × seed × checkpoint rule evaluated on any OOS data. N_DSR = ledger rows (or clusters).
12. Seeds: 10 per configuration for the challenger; incumbent re-run with the same 10 seeds.
13. Deployed object: 10-seed ensemble (average target weights/scores).

E. *Statistics*
14. DSR of challenger's weekly active returns with N from the ledger, V from the ledger's cross-trial Sharpe variance, raw kurtosis.
15. PBO via CSCV, S = 16, across the challenger's configuration grid (on active returns).
16. IQM across seeds × strata (CPCV paths or sub-periods) with stratified-bootstrap 95% CI (≥ 10,000 reps); probability of improvement vs incumbent seeds with CI.
17. Ledoit–Wolf studentized circular-block-bootstrap test of IR difference (b ≈ 8–10 weeks, ≥ 5,000 reps); HAC IC-difference test; intercept test from regressing challenger on incumbent returns.
18. Placebo battery (§5, items 1–7) with null distributions.

F. *Decision rules (fixed in advance)*
- **Adopt (replace incumbent)** only if all hold: (i) DSR(active) ≥ 0.95; (ii) PBO ≤ 0.2; (iii) P(improvement) lower 95% bound > 0.5 and IQM IR CI excludes the incumbent's IQM; (iv) LW test one-sided p < 0.05 *or* HAC ΔIC t > 2; (v) positive active return in ≥ 3 of 4 sub-periods and in the held-out region; (vi) all placebos pass; (vii) still beats incumbent at 2× costs; (viii) ≥ 26 weeks of paper trading with live IR inside the backtest's 90% bootstrap band and no kill-rule trigger.
- **Blend** (e.g. 50/50 score average) if (iii) and (vi) pass and active-return correlation with incumbent < 0.6, but (iv) fails — diversification gain without proof of superiority. Check the blend's own DSR (add it to the ledger).
- **Reject** otherwise; keep LightGBM. Record the result either way (negative results lower N for the next attempt only if the ledger is honest).
- **Kill switch (live):** cumulative active return vs incumbent < −2·TE·√(weeks/52), or live IC t < −2 after 52 weeks.

G. *Reporting*
19. Report all seeds, all CPCV paths, gross and net, with and without the 2020 year, and the number of trials. Plot λ (CSCV logits) histogram and IS-vs-OOS Sharpe scatter.

**Realistic expectation (inference from §4 numbers):** with ~560–1,000 weeks and two highly correlated long-only books, the challenger can almost never be *proven* better on Sharpe; the most likely defensible outcomes are "reject" or "blend". The protocol's job is mainly to stop a lucky seed or checkpoint from replacing a working incumbent.

### Gaps
- No published pre-registration template specific to quantitative trading strategies was found in this session; the checklist is a synthesis of the cited methods.
- Thresholds such as PBO ≤ 0.2 and DSR ≥ 0.95 are conventions/judgement calls, not derived optimal values.
