# Global Mid/Large-Cap Equity Universe and Survivorship-Bias-Free Data on a Retail Budget

Research date: 2026-10-18. Context: UK retail investor, Trading 212 Stocks & Shares ISA (GBP), weekly rebalancing, global mid/large caps. Prices are as shown on vendor pages on the fetch date unless flagged. "Researcher test" means a direct HTTP check run on 2026-10-18 from this research session.

## 1. Definitions and sizes of a global mid/large-cap universe (MSCI, FTSE, S&P, Solactive; mid-cap cut-offs; names by country; exchanges)

### Takeaway
"Global large + mid cap" is a standard definition: about 85% of free-float market cap in each country. MSCI ACWI had 2,414 names (Sep 30, 2026): 1,249 developed (MSCI World) and about 1,165 emerging. FTSE All-World is wider, at about 4,265 names covering 90–95%. Under MSCI rules (May 2026), the developed-market large+mid floor is about USD 7.9bn full market cap, allowed to range from about USD 3.9bn to 9.1bn. The emerging-market floor is half that. In practice the smallest developed-market constituents have about USD 2.3bn of free float.

### Cited Findings
**MSCI ACWI (USD factsheet, Sep 30, 2026)**
- Large and mid cap across 23 developed (DM) and 24 emerging (EM) countries. "With 2,414 constituents, the index covers approximately 85% of the global investable equity opportunity set." — [MSCI ACWI factsheet](https://www.msci.com/documents/10199/255599/msci-acwi-net.pdf)
- Index market cap USD 102.70tn. Largest constituent USD 5,250bn (NVIDIA), smallest USD 192.7m, average USD 42.5bn, median USD 10.36bn. Turnover over the last 12 months was 3.40% (MSCI World 3.18%, EM 5.52%). — [MSCI ACWI factsheet](https://www.msci.com/documents/10199/255599/msci-acwi-net.pdf)
- DM countries: Australia, Austria, Belgium, Canada, Denmark, Finland, France, Germany, Hong Kong, Ireland, Israel, Italy, Japan, Netherlands, New Zealand, Norway, Portugal, Singapore, Spain, Sweden, Switzerland, UK, US. EM countries: Brazil, Chile, China, Colombia, Czech Republic, Egypt, Greece, Hungary, India, Indonesia, Korea, Kuwait, Malaysia, Mexico, Peru, Philippines, Poland, Qatar, Saudi Arabia, South Africa, Taiwan, Thailand, Turkey, UAE. — [MSCI ACWI factsheet](https://www.msci.com/documents/10199/255599/msci-acwi-net.pdf)
- The constituent count moves every quarter. Earlier 2026 factsheets showed 2,458 (Aug 31, 2026) and 2,460 (July 2026, KRW gross version). Neither was opened directly; both figures are from search snippets. — [MSCI factsheet search results (AUD version)](https://www.msci.com/documents/10199/255599/msci-acwi-index-aud-net.pdf)
- Share-class duplicates are inside the index itself: the ACWI top 10 lists both "ALPHABET A" and "ALPHABET C". — [MSCI ACWI factsheet](https://www.msci.com/documents/10199/255599/msci-acwi-net.pdf)

**MSCI World (GBP and CAD factsheets, Sep 30, 2026)**
- 23 DM countries, 1,249 constituents. In GBP: smallest constituent GBP 1,754.85m float market cap, median GBP 18,118m, average GBP 54,492m, largest GBP 3,952bn. — [MSCI World GBP factsheet](https://www.msci.com/documents/10199/255599/msci-world-index-gbp-net.pdf); same count in the [CAD factsheet](https://www.msci.com/documents/10199/255599/msci-world-index-cad-net.pdf)
- Earlier 2026 counts: 1,280 (AUD factsheet, Aug 2026) and 1,282 (GBP factsheet, Jul 2026). These are from search snippets. justETF reports US weight 72.94%, Japan 5.91%, UK 3.41%. — [justETF MSCI World](https://www.justetf.com/en-it/how-to/msci-world-etfs.html)

**MSCI size rules (Global Investable Market Indexes methodology summary, July 2026)**
- Market coverage targets in each market: Standard (large+mid) 85%, allowed range 80–90%. Large cap 70% (range 65–75%). IMI 99% (range 98.5–100%). Mid cap is Standard minus Large. — [MSCI GIMI Methodology Summary Jul 2026](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Jul26_GIMIMethod_Summary.pdf)
- The Global Minimum Size Reference (GMSR) is set on the DM investable universe, at the full market cap of the company that brings cumulative free-float coverage to 85–87% for Standard. The EM GMSR is half the DM GMSR. Each market's size-segment cutoff must sit within the Global Minimum Size Range of 0.5x to 1.15x GMSR. — [MSCI GIMI Methodology Summary Jul 2026](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Jul26_GIMIMethod_Summary.pdf)
- Thresholds in use at the May 2026 index review, based on the minimum investability requirements for the Standard indexes:
  - Company full market cap: DM USD 7,874m, EM USD 3,937m, Frontier USD 232m.
  - Security float market cap: DM USD 3,937m, EM USD 1,969m.
  - Liquidity (annualised traded value ratio, ATVR): DM 20%, EM 15%.
  - Equity Universe Minimum Size: USD 537m (as of Apr 20, 2026).
  - 3-month frequency of trading: DM ≥ 90%, EM ≥ 80% for new entrants.
  - Buffer zones: 1.5x the next larger cutoff above, 0.67x the cutoff below.
  - Reviews are quarterly (Feb, May, Aug, Nov).
  — [MSCI GIMI Methodology Summary Jul 2026](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Jul26_GIMIMethod_Summary.pdf)

**Names by country and exchange: iShares MSCI ACWI ETF holdings file (as of Oct 15, 2026; researcher-parsed)**
- The fund held 2,197 equity lines against 2,414 index constituents (Sep 30). ETF holdings are therefore not the index list.
- Lines by country (weight):

  | Country | Lines | Weight |
  |---|---|---|
  | US | 515 | 64.73% |
  | China | 360 | 1.80% |
  | Japan | 167 | 5.02% |
  | India | 165 | 1.18% |
  | Canada | 81 | 3.00% |
  | Korea | 76 | 2.00% |
  | Taiwan | 75 | 3.32% |
  | UK | 66 | 3.04% |
  | France | 54 | 1.96% |
  | Germany | 50 | 1.82% |
  | Australia | 43 | 1.34% |
  | Brazil | 43 | 0.55% |
  | Switzerland | 40 | 1.96% |
  | Sweden | 39 | 0.75% |
  | Saudi Arabia | 27 | |
  | South Africa | 27 | |
  | Italy | 26 | |
  | Netherlands | 25 | |
  | Hong Kong | 25 | |
  | Spain | 21 | |
  | Mexico | 20 | |
  | Malaysia | 20 | |
  | UAE | 17 | |
  | Poland | 16 | |
  | Singapore | 15 | |
  | Israel | 15 | |
  | Denmark | 14 | |
  | Finland | 13 | |
  | Belgium, Norway, Thailand, Turkey | 12 each | |
  | Greece | 10 | |
  | Russia | 10 (0% weight) | |
  | Others | ≤ 9 each | |

- Lines by exchange: NYSE 354, NASDAQ 184, HKEX 174, Tokyo 167, NSE India 163, Shanghai 124, TSX 81, Shenzhen 76, KRX 73, TWSE 68, LSE 67, Euronext Paris 53, Xetra 49, ASX 43, SIX 40, B3 39, Nasdaq Nordic and the Nordic venues about 76, Tadawul 27, JSE 27, Borsa Italiana 26, Euronext Amsterdam 23, Madrid 21.
- 37 trading currencies: USD 546, EUR 225, CNY 199, HKD 174, JPY 167, INR 165, CAD 81, KRW 76, TWD 75, GBP 64, and others. The file's FX column gave 0.75 GBP per USD.
— [iShares ACWI latest-holdings.csv](https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/latest-holdings.csv)

**FTSE**
- FTSE All-World: 4,265 index constituents (31 Jul 2026), free-float weighted, reviewed semi-annually. — [DWS/Xtrackers factsheet](https://etf.dws.com/download/asset/7949babd-2ceb-429c-a5fa-e7a5a111dfc2). justETF gives 4,265 (30 Jun 2026) and 90–95% coverage of investable market cap. — [justETF FTSE All-World](https://www.justetf.com/en-be/how-to/ftse-all-world-etfs.html). Vanguard lists 4,264 benchmark stocks against 3,782 holdings in its fund (VWRL/VWRP), as of 31 Jul 2026. — [Vanguard FTSE All-World UCITS ETF](https://www.vanguard.co.uk/professional/product/etf/equity/9679/ftse-all-world-ucits)
- FTSE Developed: 1,975 constituents (30 Jun 2026) and 1,983 (27 Feb 2026), per justETF (secondary source). — [justETF FTSE Developed](https://www.justetf.com/en-be/how-to/ftse-developed-etfs.html)

**S&P and Solactive**
- S&P Global LargeMidCap combines S&P Global LargeCap and MidCap: the stocks making up the top 85% of float-adjusted market cap in each developed and emerging country. It is a subset of the S&P Global BMI. — [S&P DJI index page](https://www.spglobal.com/spdji/en/indices/equity/sp-global-largemidcap/)
- Solactive GBS Global Markets Large & Mid Cap covers roughly the largest 85% of free-float market cap in global markets, weighted by free float. It belongs to the Solactive Global Benchmark Series. — [Solactive GBS GM L&M GBP PR](https://solactive.com/index/DE000SL0BAH7)

### Inferences
- Size thresholds in USD, mid-2026:
  - DM large+mid lower bound: about USD 3.9–9.1bn full market cap (0.5–1.15x of the USD 7.874bn GMSR).
  - Smallest DM constituent float: about USD 2.3bn (GBP 1.75bn at 0.75 GBP/USD).
  - EM: half of the DM figures, about USD 2–4.5bn full market cap.
  - Median ACWI stock: about USD 10bn float.
  - "Mid cap" therefore covers roughly USD 2–4bn up to the large-cap cutoff (about the 70% coverage point). These are derived numbers, not MSCI-published per-region cutoffs.
- To mimic ACWI by rule: about 1,250 DM names plus about 1,150 EM names. To mimic FTSE All-World: about 4,250 names. A DM-only ("World") universe has 1,250–2,000 names, depending on whether MSCI (85%) or FTSE (about 90%) coverage is used.
- ACWI/World counts fell by about 30–45 names per quarter during 2026 (2,460 → 2,414; 1,282 → 1,249). Quarterly churn is small (3.4% one-way turnover), which supports refreshing a replicated universe monthly or quarterly rather than weekly.

### Gaps
- No official FTSE Russell or S&P DJI constituent counts for FTSE Developed, S&P Global LargeMidCap or Solactive GBS GM L&M were retrieved. The S&P page returned HTTP 403, and the Solactive count was not found.
- The actual per-market MSCI Standard cutoffs (for example the US, Japan and UK USD cutoffs at the Aug/Nov 2026 reviews) were not found. Only GMSR-based thresholds are available.
- FTSE GEIS size bands (the large/mid percentages) were not verified from FTSE ground rules in this session.

## 2. Point-in-time index membership: how to get historical constituents without survivorship bias

### Takeaway
Free official point-in-time constituent history for global indices is effectively unavailable. MSCI, FTSE and S&P sell it. The legacy iShares historical-holdings endpoint did not return CSV in testing on 2026-10-18. The SEC's N-PORT datasets give free quarterly holdings for US-registered ETFs such as ACWI, URTH and VT, but only from Oct 2019. The robust retail approach is a rule-based universe: rank all listed securities, including delisted ones, by market cap or traded value each month. Use ETF holdings only to validate the rule.

### Cited Findings
- **iShares current holdings.** The current file is free and machine-readable: ticker, name, sector, market value, weight, quantity, price, location, exchange, currency, FX rate, market currency. The researcher test returned holdings as of Oct 15, 2026. — [iShares ACWI latest-holdings.csv](https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/latest-holdings.csv)
- **iShares historical holdings (researcher test, 2026-10-18).** Adding `?asOfDate=20200131` to latest-holdings.csv still returned Oct 15, 2026 holdings. The legacy endpoint `.../1467271812596.ajax?fileType=csv&fileName=..._holdings&dataType=fund&asOfDate=YYYYMMDD` returned an HTML page (labelled text/csv) instead of holdings, for both ACWI and IVV and for dates from 2008 to 2026. — [iShares legacy ajax endpoint (tested)](https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/1467271812596.ajax?fileType=csv&fileName=ACWI_holdings&dataType=fund&asOfDate=20180131). A search found no documented `asOfDate` parameter. — [search result listing](https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/latest-holdings.csv)
- **ETF holdings differ from index constituents.** The ACWI ETF held 2,197 equity lines against 2,414 index names. Vanguard's FTSE All-World fund held 3,782 stocks against 4,264 in its benchmark. — [iShares ACWI holdings](https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/latest-holdings.csv); [Vanguard FTSE All-World](https://www.vanguard.co.uk/professional/product/etf/equity/9679/ftse-all-world-ucits)
- **SEC N-PORT.** The SEC publishes quarterly Form N-PORT data sets built from XML filings submitted since October 2019. — [SEC Form N-PORT Data Sets](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets); [SEC N-PORT readme](https://sec.gov/files/nport_readme.pdf). Only the third month of each fiscal quarter is made public; the first two months stay confidential. This comes from a third-party vendor and is unverified against the SEC. — [sec-api.io N-PORT dataset](https://sec-api.io/datasets/form-nport)
- **Compustat Global (academic, via WRDS).** It covers more than 42,000 non-North-American companies, active and inactive, including delisted or removed ones. About 16,000 of them have market price data and about 26,000 have fundamentals. — [Nova SBE library: Compustat Global](https://library.novasbe.unl.pt/databases/compustat-global/). The Security Daily file runs from Dec 31, 1985. — [ZJU library WRDS listing](https://lib.intl.zju.edu.cn/node/2623). A Feb 2026 WRDS/S&P webinar lists "Coverage & Survivorship" as a topic. — [WRDS S&P webinar](https://wrds-www.wharton.upenn.edu/documents/2180/WRDS_SP_Webinar_Feb_002.pdf)
- **Index history from vendors (US/AU/CA only).**
  - Norgate Platinum/Diamond (US) include "Historical index constituents" and delisted securities; the AU and CA Platinum packages include them too. — [Norgate packages](https://norgatedata.com/stockmarketpackages.php)
  - Sharadar's bundle includes S&P 500 constituents back to 1957. — [QuantRocket Sharadar](https://www.quantrocket.com/pricing/data/sharadar)
  - EODHD sells an "Indices Historical Constituents" add-on: "up to 12 years" of history for S&P and Dow Jones indices such as the S&P 500, 600, 100 and 400. The pricing page shows prices of $29.99/mo (listed against $50.00). — [EODHD pricing](https://eodhd.com/pricing)
- **Delisted symbols on EODHD.** Delisted tickers are listed per exchange with `delisted=1`; the US list alone has "tens of thousands" of symbols. Delisted tickers keep their full history up to the delisting date. — [EODHD delisted data docs](https://eodhd.com/financial-apis/delisted-stock-companies-data-2)

### Inferences
- The recommended point-in-time approach is to rebuild membership by rule: at each monthly or quarterly review date, take all common stocks on target exchanges, active and delisted, and rank by size and liquidity using only data known at that date. Then apply MSCI-style per-country coverage (top about 85% of float market cap) or per-region top-N, with buffer bands (enter at rank N, exit at 1.5N-equivalent). This captures most of the survivorship benefit without index licences.
- Use free ETF holdings as a validation set, not a backtest universe:
  - From Oct 2019: quarterly N-PORT for ACWI, URTH and VT.
  - Now: the daily iShares/Vanguard files.
  - Measure overlap with the rule-based universe; for example, a target of more than 85–90% by weight.
- Pre-2019 index membership would need paid data (MSCI/FTSE constituent history, or Compustat Global and Datastream through a university). Otherwise accept a rule-based proxy.
- Wayback Machine snapshots of the holdings URLs could fill some gaps, but coverage is sporadic. They should be treated as spot checks, not a complete history; this was not verified, see Gaps.

### Gaps
- The Wayback Machine CDX query for archived iShares holdings files could not be completed (connection reset through the session proxy), so archive depth is unknown.
- Vanguard (VWRL/VWRP) and SPDR (for example SSAC/ACWI IMI) historical-holdings availability was not checked.
- MSCI/FTSE/S&P retail or academic prices for constituent history were not found; all are quote-only.
- It was not confirmed whether the iShares historical endpoint moved to a new URL or was withdrawn. The test only shows the old URL no longer returns CSV.

## 3. Data vendors with global coverage including delisted securities, at retail prices

### Takeaway
EODHD is the only retail vendor found that combines global end-of-day prices, explicit delisted coverage across about 70 exchanges, fundamentals with historical shares outstanding, and a bulk API, at $19.99–$99.99 a month. Two caveats: delisted names before 2018 have prices only (no fundamentals), and coverage of some large markets (Japan, Hong Kong, India) could not be confirmed. FMP Ultimate ($139/mo) is the main alternative. Norgate, Sharadar, Massive/Polygon and Databento are excellent but North-America- or US-only. Bloomberg, LSEG and FactSet cost about USD 12–32k a year.

### Cited Findings
**EODHD (eodhd.com): prices from the pricing page on 2026-10-18; a Wealth-Lab forum user saw the same plan shown in EUR, possibly depending on location**
- Plans:
  - Free: 20 calls/day, 1 year of history.
  - EOD Historical All-World: $19.99/mo or $199.00/yr.
  - All-World Extended (EOD + intraday): $29.99/mo or $299.90/yr.
  - Fundamentals Data Feed: $59.99/mo or $599.90/yr. Its comparison table marks end-of-day prices "Not included".
  - ALL-IN-ONE: $99.99/mo or $999.90/yr.
  — [EODHD pricing](https://eodhd.com/pricing); [Wealth-Lab EODHD price thread](https://wealth-lab.com/Discussion/EODHD-extension-subscription-price-9689)
- Paid plans allow 100,000 API calls/day and 1,000 requests/minute. Call costs: EOD 1, intraday 5, fundamentals 10, bulk 100 or more. The allowance resets at midnight GMT. History depth is "30+ yrs" for EOD. End-of-day covers "150,000+ tickers worldwide". — [EODHD pricing](https://eodhd.com/pricing)
- **Delisted data by delisting date:**
  - Delisted after 2018: EOD, fundamentals, dividends and splits.
  - Delisted after 2021: all of the above plus intraday.
  - Delisted before 2018: EOD only.
  - `General.IsDelisted=true` in fundamentals flags delisted names.
  - Symbol Change History (old ticker to new ticker) covers US exchanges only.
  — [EODHD delisted docs](https://eodhd.com/financial-apis/delisted-stock-companies-data-2)
- Delisted symbol counts (search snippet of an EODHD page, Sep 2026; not opened directly): US 60,191, Frankfurt 9,587, LSE 4,077. — [EODHD delisted review page](https://eodhd.com/financial-apis/review-delisted-stock-companies-data)
- The exchanges endpoint lists 70 supported exchanges (Aug 2026). `delisted=1` replaces the active list rather than adding to it, so both lists must be requested; Warsaw, for example, has 417 delisted and 612 active. ISIN is returned when available; it can be null, as for the delisted AAAB. — [EODHD exchanges API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours); [EODHD delisted docs](https://eodhd.com/financial-apis/delisted-stock-companies-data-2)
- **Bulk end-of-day.** A whole exchange for one day costs a flat 100 calls; adding `symbols=` costs extra. `filter=extended` adds market cap, beta, EMAs and 14/50/200-day average volume at no extra cost. A single-ticker full history costs 1 call. — [EODHD bulk API](https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends)
- **Historical market cap API: US only** (NYSE/NASDAQ). Weekly series, starting 2021-07-09, in USD. — [EODHD historical market cap API](https://eodhd.com/financial-apis/historical-market-capitalization-api)
- **Fundamentals.** They include `outstandingShares` history (annual and quarterly, with shares and sharesMln) and `SharesStats.SharesOutstanding`. Non-US symbols are covered from 2000, major US firms from 1985. "Minor companies have the last 6 years and 20 quarters." — [EODHD fundamentals docs](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds)
- **Exchange list as captured on the public page.** EODHD's "List of Stock Markets" page, fetched 2026-10-18, lists:
  - US; NEO, TSXV, TSX.
  - German venues (Frankfurt, Stuttgart, Munich, Hanover, Düsseldorf, Hamburg) and Xetra; Vienna.
  - Euronext Paris, Brussels, Lisbon and Amsterdam; SIX; Madrid; Irish.
  - Copenhagen, Stockholm, Oslo, Helsinki.
  - Prague, Budapest, Warsaw, Athens, Bucharest, Zagreb.
  - KRX and KOSDAQ; Shanghai and Shenzhen; TWSE and TPEx; Jakarta, Bangkok, Kuala Lumpur, Philippines, Karachi, Colombo, Vietnam.
  - ASX.
  - B3, Mexico, Santiago, Buenos Aires, Lima.
  - Egypt and several African exchanges.

  The page did not list London, Tokyo, Hong Kong, NSE/BSE India, JSE, Tadawul, Tel Aviv, Istanbul, SGX or Borsa Italiana. The API docs do show "London Exchange" (code LSE), so the page is incomplete or partly rendered by JavaScript. — [EODHD list of stock markets](https://eodhd.com/list-of-stock-markets); [EODHD exchanges API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours)
- In a researcher test, EODHD public summary pages loaded for 005930.KO, 2330.TW, 600519.SHG and VALE3.SA. They returned 404 for 7203.TSE, 0700.HK, RELIANCE.NSE, 2222.SR, NPN.JSE, ENI.MI, D05.SG, TEVA.TA, THYAO.IS and also HSBA.LSE. LSE is supported, so a 404 is not proof that coverage is missing. — [EODHD summary page example](https://eodhd.com/financial-summary/2330.TW)
- An older EODHD forum thread had a user reporting Japan missing; EODHD replied that it lacked that data and was looking for a third-party provider. The thread is undated in the snippet. — [EODHD forum: important exchanges missing](https://forum.eodhd.com/t/important-exchanges-and-bonds-missing/128)
- EODHD's disclaimer says it does not use exchange data feeds for pricing and that prices may not be accurate or appropriate for trading. — [EODHD pricing page footer](https://eodhd.com/pricing)

**Financial Modeling Prep (FMP)**
- Plans:
  - Basic: free, 250 calls/day.
  - Starter: $29/mo, or $19/mo billed annually. 300 calls/min, up to 5 years of history, US coverage.
  - Premium: $69/mo, or $49/mo annually. 750 calls/min, 30+ years, "UK and Canada Coverage".
  - Ultimate: $139/mo, or $99/mo annually. 3,000 calls/min, "Global Coverage", "Full Historical Access", bulk and batch delivery, ETF and mutual fund holdings.
  - Bandwidth caps over a trailing 30 days: 500MB (Free), 20GB (Starter), 50GB (Premium), 150GB (Ultimate).
  — [FMP pricing](https://site.financialmodelingprep.com/pricing-plans)
- The endpoint catalogue includes "Delisted Companies", "Historical Market Cap", "Batch Market Cap", "All Shares Float" and "Symbol Changes List". Which tier includes each could not be parsed from the page. — [FMP pricing](https://site.financialmodelingprep.com/pricing-plans). A competitor says FMP has a "delisted + survivorship endpoint" (unverified). — [MarketParquet vs FMP](https://marketparquet.com/vs/fmp)

**Norgate Data (US, Canada, Australia only; Windows updater required, plus Python package)**
- US packages:
  - Silver: $270/yr, last 10 years.
  - Gold: $360/yr, 20 years, plus fundamentals.
  - Platinum: $630/yr. History back to 1990, delisted securities back to 1990, historical index constituents.
  - Diamond: $787.50/yr. Back to 1950, delisted back to 1950.
  - 6-month prices are $148.50, $198, $346.50 and $433.13.
- Canada Platinum: CAD 630/yr (delisted back to 1990). ASX Platinum: AUD 630/yr (delisted back to 1992). Both include historical index constituents.
- "World Indices" are included with all packages.
— [Norgate packages](https://norgatedata.com/stockmarketpackages.php)

**Sharadar (Nasdaq Data Link; US only)**
- "No survivorship bias: includes active and delisted tickers." US fundamentals from 1990, US end-of-day prices from 1998, S&P 500 constituents from 1957, insider holdings from 2005. Price is shown only after login, and professional users must buy through Nasdaq Data Link. — [QuantRocket Sharadar pricing](https://www.quantrocket.com/pricing/data/sharadar)

**Massive (formerly Polygon.io; US stocks)**
- Stocks Basic: $0, 5 calls/min, 2 years of history.
- Starter: $29/mo, unlimited calls, 5 years, flat files.
- Developer: $79/mo, 10 years, flat files.
- Advanced: $199/mo, 20+ years, flat files.
- Financials & Ratios: $29/mo. Annual billing saves 20%.
— [Massive pricing](https://massive.com/pricing)

**Databento (US equities, plus futures and other venues)**
- US Equities combines 15 US exchanges and 30 alternative trading systems (ATSs). — [Databento US Equities](https://databento.com/blog/introducing-databento-us-equities)
- Pricing is usage-based ($/GB) or by subscription, with $125 of free credits. — [Databento pricing](https://databento.com/pricing). Databento says it has price data from 60+ venues and corporate actions for 215 exchanges. — [Databento IEX migration post](https://databento.com/blog/migrating-from-iex-cloud)

**Alpha Vantage**
- Free: 25 requests/day.
- Premium: $49.99/mo (75 req/min), $99.99 (150), $149.99 (300), $199.99 (600), $249.99 (1,200). Annual plans have 2 months free.
— [Alpha Vantage premium](https://www.alphavantage.co/premium/)

**Intrinio**
- The pricing page shows tiers of "$150/mo", "$333/mo to start (6 mo at $333, 6 mo at $666, $999 thereafter)" and "$1,250/mo+". Global ETF holdings are Enterprise-only. Which dataset each price applies to could not be parsed. — [Intrinio pricing](https://intrinio.com/pricing)

**Tiingo (official page is JavaScript-rendered; third-party figures only, unverified)**
- Free: 500 unique symbols/month, 50 requests/hour. Power plan: about USD 300/yr (~$30/mo) per a comparison site, but a dated QuantStart article says $10/mo; official pages show no public price. Business plan: about $50/mo. End-of-day covers US stocks, ETFs, mutual funds, ADRs and "supported international" data. No source on delisted coverage. — [FindMyMoat Databento vs Tiingo](https://www.findmymoat.com/vs/databento-vs-tiingo); [QuantStart Tiingo](https://www.quantstart.com/articles/evaluating-data-coverage-with-tiingo/); [Fitgap Tiingo](https://us.fitgap.com/products/tiingo)

**Institutional terminals (third-party estimates, not vendor price lists)**
- Bloomberg Terminal: about USD 24–32k per user per year.
- LSEG Workspace: about USD 12–24k per year; with Datastream or SDC about USD 26k.
— [Costbench terminals 2026](https://costbench.com/best/best-financial-data-terminals/); [CT Acquisitions comparison](https://ctacquisitions.com/refinitiv-vs-bloomberg-vs-factset-vs-capital-iq/)

### Inferences
- **Vendor summary.** Prices are monthly, as listed, Oct 2026.

  | Vendor | Geography | Delisted | Shares/market-cap history | Price |
  |---|---|---|---|---|
  | EODHD | ~70 exchanges (Japan, HK, India unconfirmed) | Yes, all exchanges | Shares-outstanding history; market-cap API US only | $19.99 (EOD) / $99.99 (EOD + fundamentals) |
  | FMP | Global on Ultimate | Endpoint exists; non-US depth unverified | Historical market cap endpoint | $139 ($99 annual) |
  | Norgate | US, CA, AU | Yes, plus index constituents | Current fundamentals | US $52.50 ($630/yr) |
  | Sharadar | US | Yes | Point-in-time fundamentals | Login-gated |
  | Massive/Polygon | US | Not stated | — | $29–199 |
  | Databento | US equities | — | — | Usage-based |
  | Alpha Vantage | Mostly US/global quotes | Not stated | — | $49.99+ |
  | Tiingo | US + some international | Not stated | — | Unverified, ~$10–30 |

- **Which EODHD plan.** For a rule-based universe ranked by market cap outside the US, EODHD ALL-IN-ONE ($99.99/mo, or $83.33/mo annually) is needed. It is the only plan with both end-of-day prices and fundamentals; the Fundamentals plan excludes end-of-day prices. EOD All-World at $19.99 is enough if the universe is ranked by traded value instead of market cap.
- **Pre-2018 size proxy.** EODHD has no fundamentals for names delisted before 2018, so a market-cap ranking for 2006–2017 cannot include dead companies. Ranking by trailing median USD traded value (price × volume from end-of-day data) gives a survivorship-consistent size and liquidity proxy for the whole history.
- **Check coverage before relying on it.** Before paying, call `/api/exchanges-list/` and `/api/exchange-symbol-list/{CODE}?delisted=1` on a trial key for TSE, HK, NSE, LSE, MI (Milan), SR, JSE and TA. Japan, Hong Kong and India together hold about 13% of ACWI weight and 506 of its holdings lines.
- **Data quality.** EODHD aggregates prices rather than using exchange feeds, so cross-check samples, especially splits, adjusted closes and delisting terminal prices, against a second source (FMP or Yahoo) for a few hundred names.

### Gaps
- EODHD coverage of Tokyo, Hong Kong, India, Saudi Arabia, South Africa, Israel, Turkey, Singapore and Italy is unconfirmed (public page incomplete; forum host blocked from this session).
- How far back delisted coverage goes on non-US EODHD exchanges, and whether delisting returns or terminal prices are included, is unknown.
- FMP's tier mapping for its delisted and historical market cap endpoints, and its non-US delisted depth, are unknown.
- FactSet and Morningstar retail or API pricing was not found.
- Tiingo's official pricing and delisted coverage were not verified.
- No independent quant-community benchmark of EODHD international delisted data quality was found. Searches of r/algotrading and the EODHD forum turned up only anecdotes. — [EODHD forum anecdote thread](https://forum.eodhd.com/t/who-uses-eodhd-data-for-automated-trading/565)

## 4. Yahoo Finance limitations for a 2,000+ stock global universe

### Takeaway
Yahoo, through yfinance, is unofficial, rate-limited at IP level with undocumented limits, and loses all history for delisted symbols. That makes it structurally survivorship-biased, so it is unsuitable as the primary backtest source for a 2,000+ name global universe. At most it is a free secondary check on current names.

### Cited Findings
- `YFRateLimitError` and HTTP 429 were widespread in 2025, on single-ticker as well as bulk calls. They persisted across IP addresses and yfinance versions (reports cite 0.2.54 and 0.2.57–0.2.59). One user downloading about 7,000 tickers got about 950 before 429s began. Yahoo does not publish limits, and commenters describe temporary IP blocks. — [yfinance discussion #2431](https://github.com/ranaroussi/yfinance/discussions/2431); [yfinance issue #2422](https://github.com/ranaroussi/yfinance/issues/2422); [yfinance issue #2480](https://github.com/ranaroussi/yfinance/issues/2480)
- According to the node-yahoo-finance2 library docs, when a stock is delisted its old symbol stops working, "including periods for when the stock WAS listed. ALL DATA will no longer be available." This is a maintainer statement, not Yahoo's. — [node-yahoo-finance2 historical docs](https://github.com/gadicc/node-yahoo-finance2/blob/devel/docs/modules/historical.md)
- Yahoo's help page: tickers go missing after symbol changes, acquisitions, bankruptcies or exchange moves, and changes may not be reflected immediately. — [Yahoo help: missing ticker symbol](https://sg.help.yahoo.com/kb/SLN2257.html)
- Users report missing historical quotes from Yahoo (Portfolio Performance forum). — [Portfolio Performance forum](https://forum.portfolio-performance.info/t/missing-historical-cotizations-in-yahoo-finance/30741)

### Inferences
- At around 1 request per ticker plus throttling, refreshing 2,000–3,000 global names daily is feasible only with caching and pacing, and can break without warning. A weekly rebalancing live system should not depend on it.
- Any Yahoo-built history of "current ACWI members" is survivorship-biased by construction, because dead names vanish. Ticker changes also break continuity unless a separate symbol-mapping table is maintained.

### Gaps
- No systematic source on Yahoo bad prints or adjustment errors for non-US listings was found. Evidence is anecdotal.

## 5. Practical constraints: Trading 212 tradability, liquidity filters, share-class duplicates, ADRs vs local lines, currency

### Takeaway
Trading 212 Invest/ISA covers about 13,000 stocks and ETFs on about 16 venues, centred on the US, UK and continental Europe. Japanese, Hong Kong, Indian and mainland Chinese local lines appear not to be offered, and Canada is disputed. A global ACWI-style universe therefore has to be cut down to what T212 can trade, using US-listed ADRs as stand-ins for many Asian names. Costs differ by market: UK stamp duty is 0.5%, French FTT 0.4%, and FX conversion 0.15%. These costs matter at weekly rebalancing.

### Cited Findings
**Trading 212 coverage and API**
- About 13,000 stocks and ETFs. The "16 exchanges" include NYSE, NASDAQ, LSE, Deutsche Börse (Xetra/Gettex), Euronext Paris, Amsterdam and Lisbon, Bolsa de Madrid, Wiener Börse and the Toronto Stock Exchange. No ASX shares. — [Trading 212 review roundup (FindMyMoat)](https://www.findmymoat.com/tools/trading-212); [investingintheweb T212 review](https://investingintheweb.com/reviews/trading-212-review/); [BrokerChooser T212 review](https://www.brokerchooser.com/broker-reviews/trading-212-review)
- A community thread listed Canada, Australia, Hong Kong, Japan and India as not available. It may be dated, and it conflicts with the TSX claim above. A forum post says many Swedish stocks are reachable only through Gettex, with lower liquidity than Nasdaq Stockholm. — [T212 community: New Stock Exchanges](https://community.trading212.com/t/new-stock-exchanges/91702)
- 0.15% FX conversion fee on trades in foreign currencies. — [BrokerChooser T212 review](https://www.brokerchooser.com/broker-reviews/trading-212-review)
- **Market fees (T212 help centre):**
  - LSE: 0.5% Stamp Duty Reserve Tax on share purchases. Most AIM stocks and ETFs are exempt. PTM levy £1.50 per trade over £10,000.
  - US: FINRA fee $0.000195 × quantity sold; SEC fee 0.00206% of sell value.
  - France: 0.4% FTT on purchases of French companies with market cap over €1bn.
  — [T212 help: stock exchange fees](https://helpcentre.trading212.com/hc/en-us/articles/360007081637)
- **Public API (beta).** Enabled only for Invest and Stocks ISA accounts. Rate limits are per account and reported in `x-ratelimit-*` headers. `GET /api/v0/equity/metadata/instruments` allows 1 request per 50s; `/metadata/exchanges` allows 1 per 30s. Data refreshes every 10 minutes. — [Trading 212 API docs](https://docs.trading212.com/api); [T212 instruments metadata docs](https://docs.trading212.com/api/instruments-metadata.md)

**ETF-holdings evidence relevant to deduplication and currency**
- ACWI includes multiple share classes of one company: GOOGL (Alphabet Class A) and GOOG (Class C). Its holdings span 37 trading currencies. China exposure is split across 199 CNY A-share lines (Shanghai/Shenzhen) and 174 HKD lines. — [iShares ACWI holdings](https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/latest-holdings.csv)
- MSCI requires DM securities to trade on at least 90% of days and to meet an ATVR of at least 20% (EM 15%). These are workable templates for a liquidity screen. — [MSCI GIMI Methodology Summary Jul 2026](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Jul26_GIMIMethod_Summary.pdf)

### Inferences
- **Tradable subset estimate (from ACWI line counts, assuming T212 covers US, UK, Germany, Euronext, Spain and Austria):** about 515 US + 66 UK + 54 France + 50 Germany + 25 Netherlands + 21 Spain + 12 Belgium + 6 Portugal + 5 Austria, which is about 750 local lines. Possible additions:
  - Switzerland (40), Italy (26) and the Nordics (about 78), via Xetra/Gettex cross-listings or ADRs.
  - Canada (81), if TSX access is real.
  - Large Japanese, Chinese, Taiwanese, Indian and Korean names that have NYSE/NASDAQ ADRs.

  A realistic tradable "global mid/large" universe on T212 is therefore about 800–1,200 names, not 2,400. The live instrument list should be pulled from the T212 metadata endpoint and joined to the research universe by ISIN.
- **Liquidity filter.** Use trailing 63-day median daily value traded in USD or GBP. For a small ISA, a floor of about USD 5–20m per day for DM and a higher bar for Gettex/OTC lines is reasonable. This is a judgement call, not a sourced threshold. Also require trading on at least 90% of days, mirroring MSCI.
- **Share-class duplicates.** Collapse to one line per issuer: keep the most liquid class, or the one T212 offers. Identify issuers by ISIN prefix or company name, plus the vendor's company ID. In the backtest, do the same so one issuer is never held twice (GOOG/GOOGL, BRK, dual-listed Shell/Unilever-style cases, A/H shares).
- **ADRs vs local lines.** ADR prices trade during US hours while local lines close earlier. Mixing them in a weekly cross-sectional signal creates timing mismatch. For the backtest, compute signals on the line actually traded (ADR or local) and convert everything to GBP at a consistent daily FX fixing.
- **Currency.** Store prices in local currency and convert to GBP (the ISA base) and USD (for ranking) with daily FX from the same vendor (EODHD offers FOREX). Model 0.15% FX cost per non-GBP trade, 0.5% stamp duty on UK buys and 0.4% FTT on French buys. With weekly rebalancing, these costs favour low-turnover signal designs and favour US and German lines over UK and French ones for a given exposure.

### Gaps
- No official, current T212 exchange list or per-exchange instrument count was obtained. The T212 instruments page returned 403 to the researcher. Whether TSX, SIX, Borsa Italiana or the Nordic venues are available on Invest/ISA is unconfirmed.
- No source was found on whether T212 instruments are flagged as ISA-eligible in API metadata.

## 6. Recommended affordable design and data volume (about 3,000 stocks × 20 years daily)

### Takeaway
Build the universe by rule on EODHD. Use ALL-IN-ONE ($99.99/mo, or $999.90/yr, about £750/yr at 0.75 GBP/USD) for market-cap ranking from shares outstanding from 2018 onwards, or EOD All-World ($199/yr) for ranking by traded value. Pull every active and delisted common stock on the target exchanges. Each month, rank by trailing size and liquidity with buffers. Validate against current and N-PORT ETF holdings, then intersect with T212's live instrument list. Data volume is small: about 15M rows for 3,000 names over 20 years, and about 76M rows if the full candidate pool of about 15,000 names is stored.

### Cited Findings
- EODHD paid plans allow 100,000 calls/day. A full end-of-day history costs 1 call per ticker, fundamentals 10 calls per ticker, and a whole-exchange daily bulk file 100 calls. The bulk `filter=extended` field includes current market cap and average volumes. — [EODHD pricing](https://eodhd.com/pricing); [EODHD bulk API](https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends)
- Delisted symbols require a separate `delisted=1` list per exchange. Pre-2018 delisted names have end-of-day data only. — [EODHD exchanges API](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours); [EODHD delisted docs](https://eodhd.com/financial-apis/delisted-stock-companies-data-2)
- Shares-outstanding history is available via `outstandingShares` (annual/quarterly). Non-US fundamentals start in 2000; minor companies have only 6 years. — [EODHD fundamentals docs](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds)
- MSCI-style rule components: 85% coverage per market, buffers at 1.5x/0.67x, quarterly reviews, and a 90% frequency-of-trading test. — [MSCI GIMI Methodology Summary Jul 2026](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Jul26_GIMIMethod_Summary.pdf)
- Validation sources: iShares daily holdings and SEC N-PORT quarterly data (from Oct 2019). — [iShares ACWI holdings](https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/latest-holdings.csv); [SEC N-PORT data sets](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets)

### Inferences
- **Recommended pipeline (researcher's design):**
  1. **Security master.** For each target exchange code (US, LSE, XETRA, PA, AS, BR, LS, MC, VI, SW, MI if available, CO, ST, OL, HE, TO, plus Asian and EM codes if T212 or ADR access justifies them), pull `exchange-symbol-list` twice, active and `delisted=1`. Filter `type=common_stock`. Keep Code, ISIN, currency, exchange and name. Expect about 10–20k candidate securities for DM-focused coverage (estimate).
  2. **Prices.** Pull a 1-call full end-of-day history per ticker (about 15k calls, under one day's quota), with splits and dividends (adjusted close is provided). Then keep it updated with daily bulk files: about 20–30 exchanges × 100 calls = 2–3k calls/day.
  3. **Size.** For 2018 onwards, and for live names back to 2000: market cap = `outstandingShares` (forward-filled from report date plus a reporting lag of about 60–90 days to stay point-in-time) × close × FX. Fundamentals cost about 10 calls per ticker, so about 150k calls for 15k tickers, spread over 2 days. For anything the shares data cannot cover, especially pre-2018 delisted names: use 126- or 252-day median USD traded value as the ranking variable. Simplest consistent choice: use traded value throughout, and market cap only as a secondary filter after 2018.
  4. **Membership rule.** At each month-end, per region (US, Europe ex-UK, UK, Canada, Japan/APAC via ADRs, EM via ADRs), rank by size and keep the top names until cumulative regional size reaches about 85%, or simply the top N (for example US 500, Europe 450, UK 70, other 200). Add buffers: incumbents stay until they fall below 1.5× the entry rank. Also require trading on at least 90% of days and a liquidity floor. Then collapse share classes to one line per issuer.
  5. **Tradability overlay (live and recent backtest).** Inner-join on ISIN with T212 `/equity/metadata/instruments`, which can be called at most once per 50s, so cache it daily. Backtest on the same exchange lines T212 trades.
  6. **Validation.** For 2019Q4 onwards, compare the rule universe with N-PORT ACWI/URTH/VT holdings each quarter, and with today's iShares/Vanguard files. Report weight overlap and name overlap.
  7. **Costs.** Apply 0.15% FX, 0.5% UK stamp duty on buys, 0.4% French FTT on buys, and spread and slippage assumptions by liquidity bucket.
- **Data volume (researcher calculation).** Assume 252 trading days × 20 years = 5,040 rows per security, and per row OHLC + adjusted close as float64, volume as int64, plus int32 date and ID = 56 bytes.

  | Securities | Rows | Raw size | Parquet (est.) |
  |---|---|---|---|
  | 3,000 | 15.1M | about 0.85 GB | about 0.2–0.35 GB |
  | 15,000 (full candidate pool incl. delisted) | 75.6M | about 4.2 GB | about 1.1–1.7 GB |
  | 40,000 | 201.6M | about 11.3 GB | about 2.8–4.5 GB |

  The 2.5–4× compression ratio is an assumption. Fundamentals JSON is larger per ticker but small in total, a few GB at most (not measured). Everything fits on a laptop and in DuckDB or Polars.
- **Budget options:**
  - **Minimum: about $199/yr.** EODHD EOD All-World, with the universe ranked by traded value. Free iShares/N-PORT data for validation.
  - **Recommended: about $999.90/yr.** EODHD ALL-IN-ONE, for shares-outstanding market cap and fundamentals.
  - **Optional US gold standard: +$630/yr.** Norgate US Platinum, for US delisted names and historical index constituents back to 1990, to cross-check EODHD's US side, which is about 65% of global weight.
  - **Alternative: FMP Ultimate at $99–139/mo.** Use it if EODHD's coverage of Japan, Hong Kong or India proves missing and those markets are wanted. Its non-US delisted depth needs a trial check first.
- **Point-in-time cautions.**
  - Use as-of dates for shares outstanding: the filing date, not the period end.
  - Include delisted names up to their last trading date. Assume a delisting return: the last price, or −30% to −100% for bankruptcies if no terminal price is available (a modelling choice).
  - Freeze universe membership at each rebalance using only prior data.

### Gaps
- Actual EODHD candidate-pool sizes per exchange (active plus delisted common stocks) were not measured; that needs an API key.
- Real parquet compression for this schema was not measured.
- EODHD's handling of delisting terminal prices and returns is undocumented in the pages reviewed.
- No published benchmark was found on how closely a traded-value-ranked universe matches MSCI ACWI membership.
