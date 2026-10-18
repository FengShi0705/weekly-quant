# Trading 212 Stocks & Shares ISA (GBP): exact trading costs, taxes, constraints and API access for an automated weekly global-equity strategy

Research date: 18 Oct 2026. Method: Trading 212 help-centre articles were read directly via the Zendesk article API (each article's "edited" date is cited). Trading 212 legal PDFs (Invest Terms, ISA Terms, Order Execution Policy, Costs & Charges Disclosure, API Terms) and the official OpenAPI spec were downloaded and read in full. HMRC/gov.uk pages were read directly. trading212.com/terms/fees returned "Access Denied" (geo/IP block) and could not be read; the help-centre "fees" articles were used in its place.

> **Most important finding for automation:** Trading 212's Invest Terms (cl. 5.1, updated 7 Aug 2026) and API Terms (cl. 4.2(a), updated 17 Oct 2025) **expressly prohibit "Algorithmic Trading"**. They define it as trading where "a computer algorithm automatically determines individual parameters of Orders, such as whether to initiate the Order, the timing of execution, price or quantity ... with limited to no human intervention". A fully unattended weekly rebalancer fits that definition. See the API section.

---

## 1. Trading 212 fees for ISA accounts (2025–2026)

### Takeaway
Trading 212 charges no commission, custody, platform, inactivity, withdrawal or fractional-share fee. Its only fee on Invest, ISA and SIPP accounts is a **0.15% FX fee**, taken on every conversion. The Stocks ISA is **not multi-currency**, so every non-GBP trade pays 0.15% on the buy and again on the sell (about 0.30% round trip). Dividends are exempt from the FX fee. Card and e-wallet deposits are free up to £2,000 in total, then cost 0.7%; bank transfers are free.

### Cited Findings
- "The only fee Trading 212 can charge your Invest, ISAs, and SIPP is the FX Fee. FX fee: 0.15%. Trading commission: Free. Custody Fee: Free." Other trade costs are levied by exchanges and tax authorities and appear on the Review Order screen (edited 17 Aug 2026; updated 13 Oct 2026). — [T212: What are the fees in the Invest, ISAs, and SIPP?](https://helpcentre.trading212.com/hc/en-us/articles/11471996799517-What-are-the-fees-in-the-Invest-ISAs-and-SIPP)
- **FX fee mechanics.** An order in an instrument quoted in another currency is converted at "spot exchange rate + 0.15% FX fee". The worked example applies the fee multiplicatively to the side of the spot quote you trade on:
  - Buy: rate = 1.40 − (0.15/100 × 1.40) = 1.3979, using the spot bid of 1.4000.
  - Sell: rate = 1.41 + (0.15/100 × 1.41) = 1.412115, using the spot ask of 1.4100.
  - The fee is shown on the Review Order page. It also applies inside Pies. Dividends and other corporate-event payments are exempt.
  - (edited 6 Aug 2026) — [T212: What is the FX fee? (Invest & Stocks ISA)](https://helpcentre.trading212.com/hc/en-us/articles/360018909758-What-is-the-FX-fee-Invest-Stocks-ISA)
- **No multi-currency in the ISA.** "At this stage, only the Invest and SIPP accounts support multi-currency." Supported Invest currencies are GBP, USD, EUR, CHF, DKK, NOK, PLN, SEK, CZK, RON, HUF, CAD and AUD (edited 2 Sep 2026). — [T212: What is a multi-currency account?](https://helpcentre.trading212.com/hc/en-us/articles/11669719976093-What-is-a-multi-currency-account)
- "ISA and CFD accounts use the primary account currency for all transactions." Choosing the order currency is possible only in Invest accounts (edited 1 Sep 2026). — [T212: Can I choose the currency...](https://helpcentre.trading212.com/hc/en-us/articles/34159237080861-Can-I-choose-the-currency-in-which-to-buy-sell-assets-for-Invest-accounts)
- Dividends are received in the instrument's currency and converted to the primary currency "This will not be subject to an FX fee" (edited 25 Sep 2025). — [T212: How can I receive dividends?](https://helpcentre.trading212.com/hc/en-us/articles/360007327218-How-can-I-receive-dividends-Invest-Stocks-ISA)
- The Costs & Charges Disclosure says the 0.15% FX fee applies "whenever you convert funds", at "the live interbank rate", with "No weekend fees or surcharges", and "The FX fee does not apply when receiving dividend payments". Its worked US example charges FX on both buy and sell: £1.50 + ~£1.50 on £1,000, about 0.30% round trip (PDF; server last-modified 9 Oct 2026). — [T212 Costs & Charges Disclosure](https://www.trading212.com/legal-documentation/uk/common/Costs-and-Charges-Disclosure_EN.pdf)
- **Deposits.** Card, Google Pay, Apple Pay, OpenBankingPL and Klarna deposits are free "until you have deposited 2,000 GBP/EUR in total. Once the limit is reached, a fee of 0,7% will apply." The limit is lifetime-cumulative across Invest/ISA. "Deposits via Bank Transfers and Instant Bank Transfers remain free." "All withdrawals remain free." (edited 24 Jun 2026) — [T212: What are the fees for funding my account?](https://helpcentre.trading212.com/hc/en-us/articles/360007139838-What-are-the-fees-for-funding-my-account)
- Withdrawals: "We do not charge any fees for processing payments" but the receiving bank may (edited 12 Feb 2025). — [T212: Withdrawal fees](https://helpcentre.trading212.com/hc/en-us/articles/11472022690973-What-are-the-withdrawal-fees)
- "There are no inactivity fees" (edited 16 Jun 2024). — [T212: Is there an inactivity fee?](https://helpcentre.trading212.com/hc/en-us/articles/360007303418-Is-there-an-inactivity-fee)
- **Fractional shares.**
  - "There are no extra fees for trading fractional shares. The only cost involved is a 0.15% foreign exchange fee, where applicable."
  - "Any government or regulatory fees that apply to whole shares, like Stamp Duty, also apply to fractional shares in the same way."
  - (edited 8 Jan 2025) — [T212: Can I trade with fractional shares?](https://helpcentre.trading212.com/hc/en-us/articles/9511997937437-Can-I-trade-with-fractional-shares)
- Trading 212's main Invest/ISA revenue streams are "the 0.15% FX fee ... and share lending proceeds" (edited 26 Jul 2024). — [T212: How does Trading 212 make money?](https://helpcentre.trading212.com/hc/en-us/articles/360008682638-How-does-Trading-212-make-money)
- A pre-trade "Cost information" screen breaks out entry, ongoing and exit costs (FX, stamp duty, SEC/FINRA) for Invest, Stocks ISA and SIPP. Custody/platform lines "always show as zero"; third-party inducements show zero (edited 16 Jul 2026). — [T212: How can I see the cost of a trade before I place it?](https://helpcentre.trading212.com/hc/en-us/articles/37664081239709-How-can-I-see-the-cost-of-a-trade-before-I-place-it)
- Interest is paid on uninvested cash in the Stocks & Shares ISA. Cash is held in banks or qualifying money market funds (edited 2 Oct 2026). — [T212: What is interest on cash?](https://helpcentre.trading212.com/hc/en-us/articles/15475153380637-What-is-interest-on-cash)
- Third-party reviews dated 2026 agree that the FX fee is 0.15% and is the only platform fee (affiliate sites, lower reliability). — [Investors Centre: T212 fees](https://www.theinvestorscentre.co.uk/reviews/trading-212-review/fees); [StockBrokers.com](https://www.stockbrokers.com/uk/review/trading-212)

### Inferences
- **Changes announced in 2025–2026:**
  - I found no change to Trading 212's own fee (still 0.15% FX, zero commission).
  - The changes in this period are pass-through levies (PTM £1.50, French FTT 0.4%, Italian FTT doubled, FINRA TAF and SEC fee updates — see section 2) and the ISA rule changes (section 4).
  - Two operational changes: the pre-trade cost screen (July 2026) and the API moving to key + secret authentication (API Terms of 17 Oct 2025).
- **Exact FX model for code:**
  - Buy: GBP → CCY at `spot_bid × (1 − 0.0015)`.
  - Sell: CCY → GBP at `1 / (spot_ask × (1 + 0.0015))`.
  - The round-trip FX cost is about 0.30% plus the interbank bid/ask (tiny for GBP/USD and GBP/EUR).
  - Because the ISA cannot hold foreign cash, no trade can avoid the FX fee.
- Bank-transfer funding keeps deposit cost at zero. Card funding is only free for the first £2,000 lifetime.

### Gaps
- The trading212.com "Terms & Fees" page could not be fetched (Access Denied to this IP), so the current interest rate on ISA cash and any fee-page-only items are unverified.
- The Costs & Charges Disclosure PDF contains **stale figures** that conflict with the help centre (edited Aug 2026) and with primary sources: PTM £1, French FTT 0.3%, FINRA $0.000166 and SEC 0.0008%. Treat the help centre and primary sources as current.

---

## 2. Taxes and levies passed through, per market

### Takeaway
Trading 212 documents and passes through these levies:
- **UK:** SDRT 0.5% on buys, plus PTM levy £1.50 on each side for orders over £10,000.
- **US:** SEC fee 0.00206% of sell value, plus FINRA TAF $0.000195 per share sold.
- **France:** FTT 0.4% on buys of French-HQ companies with market cap over €1bn.

Trading 212 does not document whether it passes through the Spanish (0.2%) or Italian (0.2% from 1 Jan 2026, doubled from 0.1%) FTT, or Irish stamp duty (1%). The law imposes them on buyers regardless of residence, so a conservative model should include them. Trading 212 does not offer Hong Kong.

### Cited Findings
**UK**
- "Stamp Duty Reserve Tax is charged at 0.5% on share purchases made for stocks listed on the London Stock Exchange. There is no Stamp Duty charge applied to gilts, bonds or ETFs." (edited 17 Aug 2026) — [T212: Applicable stock exchange fees](https://helpcentre.trading212.com/hc/en-us/articles/360007081637-What-are-the-applicable-stock-exchange-fees)
- "PTM LEVY is charged both on purchase and sale, and it is £1.5 per trade for orders over £10,000." (edited 17 Aug 2026) — same source.
- "Most stocks traded on the LSE AIM are exempt from Stamp Duty Reserve Tax." (edited 17 Aug 2026) — same source.
- **HMRC scope of SDRT.** You pay 0.5% when buying "existing shares in a company incorporated in the UK" and "shares in a foreign company that has a share register in the UK". You "do not normally have to pay Stamp Duty or SDRT if you buy foreign shares outside the UK". A 1.5% rate applies to transfers into depositary receipt schemes and clearance services. — [gov.uk: Tax when you buy shares](https://www.gov.uk/tax-buy-shares)
- The Takeover Panel raised the PTM levy from £1 to £1.50 per contract where total consideration exceeds £10,000, effective for trades from 2 December 2024. It was the first change since 2002 (Panel Statement 2024/19, Aug 2024; seen via search summary). — [Takeover Panel Statement 2024/19](https://thetakeoverpanel.org.uk/wp-content/uploads/2024/08/Panel-Statement-2024_19.pdf); corroborated by [IBKR PTM disclosure](https://www.interactivebrokers.co.uk/en/includes/disclosures/eu-stk-ptm-levy.php?nhf=T)
- **New-listing relief.** Autumn Budget 2025 (26 Nov 2025) introduced a three-year SDRT exemption for securities of companies first listed on a UK regulated market on or after 27 Nov 2025. Mergers of existing listed companies and new holdcos over existing listed companies are excluded. The government also plans to replace stamp duty and SDRT with a single securities transfer charge. — [CMS: Autumn Budget 2025 SDRT three-year holiday](https://cms.law/en/gbr/legal-updates/autumn-budget-2025-stamp-duty-reserve-tax-three-year-holiday-for-new-listings); [QuotedData](https://quoteddata.com/2025/11/budget-2025-no-stamp-duty-on-new-listings-for-three-years/)

**US**
- "FINRA Fee is charged on all covered stock and ETF sales at $0.000195 x quantity sold. Transaction Fee (Securities and Exchange Commission) is $0.00206% of the value of the sell order." (edited 17 Aug 2026) — [T212: Applicable stock exchange fees](https://helpcentre.trading212.com/hc/en-us/articles/360007081637-What-are-the-applicable-stock-exchange-fees)
- **SEC Section 31 fee.** It rose from $0.00 to **$20.60 per million** (= 0.00206%) for charge dates on or after **4 April 2026**. It "will remain in effect until 60 calendar days after legislation is enacted that sets the amount of the Commission's fiscal year 2027 appropriation" (SEC order 34-104909, 27 Feb 2026). — [FINRA Information Notice 17 Mar 2026](https://www.finra.org/sites/default/files/2026-03/Information-Notice-20260317.pdf); [Federal Register 4 Mar 2026](https://www.govinfo.gov/content/pkg/FR-2026-03-04/pdf/2026-04233.pdf); [SEC Fee Rate Advisory 2026-2](https://www.sec.gov/rules-regulations/fee-rate-advisories/2026-2)
- **FINRA TAF.** From 1 Jan 2026 it is $0.000195 per share sold (was $0.000166), with a $0.01 minimum and a **$9.79 maximum** per trade (was $8.30). — [Revolut: trading regulatory fees](https://help.revolut.com/help/wealth/order-execution-fees-and-limits/trading-regulatory-fees/); [Investrade](https://www.investrade.com/commissions/). A FINRA primary page was fetched but the rate was not machine-readable (see Gaps).

**France**
- "The French Financial Transaction Tax (FFT) is 0.4%, and it is applied on the purchase of shares of companies located in France with a market cap of over 1 billion." (edited 17 Aug 2026) — [T212: Applicable stock exchange fees](https://helpcentre.trading212.com/hc/en-us/articles/360007081637-What-are-the-applicable-stock-exchange-fees)
- **Legal basis and scope.** Article 98 of the 2025 Finance Law raised the TTF from 0.3% to **0.4% for acquisitions from 1 April 2025**. It applies when three conditions are all met:
  - the shares are admitted to a regulated market;
  - the issuer's registered office is in France;
  - market cap exceeds €1bn on 1 December of the preceding year.
  - The operator withholds it at source. The 2026 list was published in BOFiP on 17 Dec 2025, with caps measured at 1 Dec 2025 (Legifiscal, 18 Dec 2025).
  - — [Legifiscal: TTF list at 1 Dec 2025](https://www.legifiscal.fr/actualites-fiscales/4362-taxe-transactions-financieres-liste-societes-concernees-1er-decembre-2025.html)
- The 2026 list covers **121** French companies (BOFiP BOI-ANNX-000467). — [Tout sur mes finances](https://www.toutsurmesfinances.com/bourse/a/taxe-sur-les-transactions-financieres); [Deloitte Avocats](https://blog.avocats.deloitte.fr/taxe-sur-les-transactions-financieres-mise-a-jour-de-la-liste-des-societes-francaises-dans-le-scope/)
- PLF 2026 amendment I-1478 proposed a rate scaled by company size from 1 Jan 2026. I found no evidence it was adopted, and 0.4% remains the reference rate. — [Assemblée nationale amendment 1478](https://www.assemblee-nationale.fr/dyn/17/amendements/1906A/AN/1478.pdf)

**Spain**
- The AEAT list for 2026 names Spanish companies with market cap over €1bn at 1 Dec 2025. 61 companies are listed, from Inditex, Santander, Iberdrola, BBVA and CaixaBank down to roughly €1.0bn caps. — [AEAT: Relación sociedades ejercicio 2026 (PDF)](https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/Declaraciones_informativas/I_Transacciones_Financieras/RELACION_SOCIEDADES_EJERCICIO_2026.pdf)
- The ITF rate is 0.2% on onerous acquisitions of shares in listed Spanish companies whose market cap exceeded €1bn on 1 Dec of the prior year. — [finreg360 on AEAT FAQ](https://finreg360.com/alerta/la-aeat-emite-una-primera-recopilacion-de-preguntas-frecuentes-del-impuesto-sobre-transacciones-financieras)

**Italy**
- The 2026 Budget Law (Art. 1, paras 30–31) doubled Tobin-tax rates from **1 Jan 2026**:
  - shares traded on regulated markets/MTFs: 0.1% → **0.2%**;
  - shares not traded on regulated markets: 0.2% → 0.4%;
  - high-frequency trading: 0.02% → 0.04%.
  - (DWF, Jan 2026) — [DWF: 2026 budget law key tax changes](https://dwfgroup.com/en/news-and-insights/insights/2026/1/2026-budget-law-key-tax-changes)
- The law was published in Gazzetta Ufficiale n. 301 (30 Dec 2025) and took effect on 1 Jan 2026. Transfers of shares in companies with market cap below €500m remain excluded. The tax is applied to the net daily balance per instrument. — [ecnews: raddoppio Tobin Tax](https://www.ecnews.it/legge-di-bilancio-2026-raddoppio-delle-aliquote-di-applicazione-della-tobin-tax/); [Money.it](https://www.money.it/tobin-tax-novita-2026-raddoppia-l-imposta-sulle-transazioni-finanziarie)

**Ireland**
- Stamp duty applies to transfers of shares in an Irish company unless an exemption applies. The standard rate is 1%, paid by the purchaser. Consideration of €1,000 or less is exempt. — [Revenue.ie: shares and share options](https://www.revenue.ie/en/property/stamp-duty/shares-stocks-marketable-securities/shares-and-share-options.aspx); [Ogier](https://ogier.com/news-and-insights/insights/stamp-duty-and-share-transfers-five-key-considerations)

**Hong Kong**
- Stamp duty on HK stock transfers is 0.1% per side (buyer and seller), down from 0.13%, effective 17 Nov 2023. — [HK IRD stamp duty guide (PDF)](https://www.gov.hk/en/residents/taxes/docs/IRSD123(E).pdf); [KPMG tax alert](https://kpmg.com/cn/en/home/insights/2023/11/tax-alert-21-hk-the-reduced-stamp-duty-rate-on-hk-stock-transfer-will-take-effect-from-17-nov-23.html)

**How Trading 212 records and collects taxes**
- In the official API spec, the `Tax.name` enum on each fill's `walletImpact.taxes` is: COMMISSION_TURNOVER, CURRENCY_CONVERSION_FEE, FINRA_FEE, FRENCH_TRANSACTION_TAX, PTM_LEVY, STAMP_DUTY, STAMP_DUTY_RESERVE_TAX and TRANSACTION_FEE. — [T212 OpenAPI spec](https://docs.trading212.com/_bundle/api.json?download)
- Invest Terms cl. 12.9 says buy funds cover the price plus "any applicable transaction tax and/or stamp duty, governmental or administrative levy", and these are deducted from sale proceeds on sells. Trading 212 "will on a best efforts basis withhold those transaction taxes" (Invest Terms, updated 7 Aug 2026). — [T212 Invest Terms (PDF)](https://www.trading212.com/legal-documentation/uk/invest/Invest-Terms_EN.pdf)

### Inferences
- **Per-trade levy model** (`notional` is in trade currency; T212 converts to GBP):
  - **UK (UK-incorporated, or foreign with a UK register; main market):** buy SDRT = 0.005 × consideration. PTM = £1.50 on buy and on sell if consideration > £10,000.
  - **UK exemptions:** AIM (most), ETFs/ITs-as-ETFs, gilts/bonds, and new UK listings from 27 Nov 2025 for three years: SDRT 0.
  - **US sells:** SEC = 0.0000206 × sell value (USD). FINRA = min(max(0.000195 × shares, $0.01), $9.79). Whether T212 applies the $0.01 minimum and $9.79 cap exactly is unverified. US buys carry no levy.
  - **France buys** (French HQ, on the 2026 BOFiP list): 0.004 × consideration. Others: 0.
  - **Spain buys** (on the AEAT 2026 list): 0.002 × consideration, if T212 collects it (see Gaps).
  - **Italy buys** (Italian issuer, cap ≥ €500m): 0.002 × net daily acquired value (2026 rate), if collected.
  - **Germany, Netherlands, Belgium, Portugal, Austria, Switzerland, Canada, Japan:** I found no levy that T212 passes to a non-resident retail buyer. T212's fee pages list none. This is inferred from absence and not confirmed; Belgian TOB and Swiss stamp duty generally attach to resident or Swiss-dealer involvement.
- **French scope trap.** Euronext Paris names with a non-French registered office are out of scope (e.g., companies domiciled in the Netherlands). Use the BOFiP list keyed by ISIN (FR-prefixed issuers on the list), not the exchange.
- The levy list should be re-pulled annually: France (BOFiP, December), Spain (AEAT, December), Italy (the €500m list). The SEC fee changes at least once per fiscal year.

### Gaps
- **Spanish and Italian FTT pass-through by Trading 212 is undocumented.** T212's fee pages mention only UK, US and French levies, and the API Tax enum has no Spanish or Italian entries (only a generic TRANSACTION_FEE). Verify empirically: place a small Spanish or Italian buy and inspect `walletImpact.taxes`.
- **Irish stamp duty treatment is undocumented by T212.** Trading 212's market list has no Euronext Dublin. Treatment of Irish-incorporated companies traded on LSE or US venues was not established.
- The FINRA TAF primary source (FINRA By-Laws Schedule A) was not read directly; the rate comes from Trading 212's page plus secondary broker pages.
- The SEC fiscal-2027 rate was not found. Per the SEC order, the $20.60/m rate persists until 60 days after the FY2027 appropriation is enacted.
- The full French 2026 list (121 names) was not extracted; fetch BOFiP BOI-ANNX-000467.

---

## 3. Execution: exchanges, fractional shares, order types, queued orders, cash reservation, spreads

### Takeaway
Trading 212 lists these markets:
- LSE and AIM;
- NYSE, NASDAQ and OTC, with 24/5 trading for the most liquid US names;
- Xetra, Euronext Paris, Amsterdam, Brussels and Lisbon;
- Madrid, Borsa Italiana, SIX and Vienna;
- TSX, Tokyo and Gettex. Availability varies by account and entity.

No Nordic, Hong Kong or Dublin venue is listed. Most ISA instruments can be traded fractionally with market, limit, stop and stop-limit orders.

Orders placed while a market is closed are queued for the open. Buys block cash at the market price plus a buffer, and an order may not exceed 95% of available cash. Trading 212 mostly fills as principal through its Systematic Internaliser, at prices no worse than the reference exchange's best bid/offer. No published spread statistics were found.

### Cited Findings
- **Market hours** (GMT; edited 4 Aug 2026), where "Exchange availability can vary by account type, country and Trading 212 entity":
  - LSE & AIM: 07:00–15:30 GMT.
  - NYSE/NASDAQ: pre-market 08:00–13:30, regular 13:30–20:00, after-hours 20:00–00:00, overnight 00:00–08:00 GMT.
  - OTC: 13:30–20:00.
  - TSX: 13:30–20:00.
  - Tokyo: 00:00–06:00, with a 02:30–03:30 break.
  - Gettex: 06:30–22:00.
  - Xetra, Euronext Amsterdam/Brussels/Lisbon/Paris, Bolsa de Madrid, Borsa Italiana, SIX Swiss and Wiener Börse: 07:00–15:30 GMT.
  - — [T212: Market opening and closing times](https://helpcentre.trading212.com/hc/en-us/articles/360008818178-What-are-the-markets-opening-and-closing-times)
- **Instrument types available in Invest and Stocks ISA:** ordinary shares, preferred shares, ETFs, ETPs, ETCs, REITs and investment trusts (edited 13 Mar 2026). — [T212: What trading instruments does Trading 212 offer?](https://helpcentre.trading212.com/hc/en-us/articles/11717160183197-What-trading-instruments-does-Trading-212-offer)
- **24/5 trading** covers pre-market 04:00–09:30 ET, regular, after-hours 16:00–20:00 ET and overnight 20:00–04:00 ET. The overnight session is "exclusively available only to the most liquid securities on NYSE and NASDAQ". "all US stocks are available as fractional shares". Overnight prices come from Blue Ocean. Regular and extended-session prices use NBBO across 18 US exchanges (edited 5 Nov 2025). — [T212: 24/5 Trading – Invest & Stocks ISA](https://helpcentre.trading212.com/hc/en-us/articles/13574400364445-24-5-Trading-Invest-Stocks-ISA)
- **Fractional trading.**
  - "Most instruments available on the Invest accounts and ISAs can be traded fractionally. Fractional Market, Limit, Stop and Stop Limit orders are all supported."
  - Pending fractional orders can only be set by number of shares.
  - Fractional orders are executed "internally and matching the price for whole shares on the reference exchange. No spread is applied."
  - Fractions cannot be transferred out to another broker.
  - (edited 8 Jan 2025) — [T212: Can I trade with fractional shares?](https://helpcentre.trading212.com/hc/en-us/articles/9511997937437-Can-I-trade-with-fractional-shares)
- **Market orders** fill "on the best available asking price" (buy) or "bid price" (sell). The displayed price is the last trade and is indicative (edited 25 Sep 2025). — [T212: Market Orders](https://helpcentre.trading212.com/hc/en-us/articles/360007081257-Market-Orders)
- An order placed outside market hours "will only be executed once the market opens again". OTC and LSE AIM are "more prone to low liquidity conditions", so delays are expected (edited 10 Jul 2024). — [T212: Why is my market order still not executed?](https://helpcentre.trading212.com/hc/en-us/articles/5781955715613-Why-is-my-market-order-still-not-executed)
- **Limit orders** remain pending with the needed funds "blocked" until filled. They "cannot be modified unless cancelled or replaced" (edited 10 Jul 2026). — [T212: Limit Orders](https://helpcentre.trading212.com/hc/en-us/articles/360007139778-Limit-Orders)
- **Cash reservation (Invest Terms, updated 7 Aug 2026):**
  - cl. 12.4: T212 calculates the maximum spend and adds "a reasonable percentage above the current market price to cover market price changes ('Total Order Blocked Funds')". Residual is released after execution.
  - cl. 12.7: "You can place an Order as long as the value of the Order does not exceed 95% of the Available Cash". Slippage can still cause a negative balance, which T212 may cure by selling.
  - — [T212 Invest Terms (PDF)](https://www.trading212.com/legal-documentation/uk/invest/Invest-Terms_EN.pdf)
- **Order queuing and other order rules (same Invest Terms):**
  - cl. 12.5: "an Order received when the relevant exchange is closed ... will not be executed until after it next re-opens", or as soon as reasonably practicable if many orders are queued.
  - cl. 12.6: no fixed execution price except for limit orders.
  - cl. 12.8: "You are not permitted to Short Sell".
  - cl. 6.4(a): T212 "shall not accept an Instruction to Deal when the relevant market is closed". This is internally inconsistent with cl. 12.5 and with the API docs (see section 5).
- **App value orders.** In "Number of shares" mode, a buy close to free funds is converted to a Value order; above 95% of free funds the slider rounds to 100% "to protect you from a negative balance". Sells above 95% of the position are converted to whole-position share-quantity orders (edited 13 Mar 2026). — [T212: Value orders vs. Number of shares](https://helpcentre.trading212.com/hc/en-us/articles/7897588388125-Value-orders-vs-Number-of-shares)
- **Execution venues (Order Execution Policy, updated 8 Oct 2026):**
  - Venues relied on: Trading 212 UK Ltd (SI), Trading 212 Markets (Ireland) Ltd (SI), Interactive Brokers LLC and J.P. Morgan Securities PLC.
  - When filling through its own SI, T212 matches "upon the best available bid and ask prices on the reference exchange", e.g. if best bid/ask is €100.50/€100.55, a client fill is "no worse than these levels".
  - Minimum and maximum order sizes "vary based on market conditions and remain at T212's sole discretion".
  - — [T212 Order Execution Policy (PDF)](https://www.trading212.com/legal-documentation/uk/common/Order-Execution-Policy_EN.pdf)
- The API Terms warn that "placing Orders through our API may carry risks of lower liquidity, higher volatility and wider spreads", and that all API orders "will be processed by Trading 212's Systematic Internaliser" (17 Oct 2025). — [T212 API Terms (PDF)](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf)
- A list of small-cap stocks is in "Close-only" mode, so no BUY orders can be placed in them. It includes many LSE/AIM and French micro-caps (edited 24 Jan 2025). — [T212: Small-cap stocks in close-only mode](https://helpcentre.trading212.com/hc/en-us/articles/6021761386653-Small-cap-stocks-in-close-only-mode)
- The Disclosure Notice and Invest Terms state that Trading 212 does not accept third-party inducements or payment for order flow. — [T212: Cost information](https://helpcentre.trading212.com/hc/en-us/articles/37664081239709-How-can-I-see-the-cost-of-a-trade-before-I-place-it)

### Inferences
- **Execution cost is just the reference-exchange half-spread** (plus FX and levies). There is no extra T212 markup on Invest/ISA equities: SI fills are no worse than the reference BBO, and "no spread is applied" on fractions.
  - Planning assumptions, not sourced Trading 212 data:
    - S&P 500 or FTSE 100 mega-caps: half-spread ≈ 1–5 bps.
    - European large caps: ≈ 3–8 bps.
    - FTSE 250, small caps or AIM: tens to hundreds of bps.
  - Calibrate from realised fills: the API `Fill.price` against the contemporaneous exchange quote.
- **Queued market orders** fill at the next open price, which can gap. They also lock cash at the price plus an undisclosed buffer, so a weekly batch of buys should leave about 5% or more cash headroom (the 95% cap).
  - Rebalance sells first, wait for fills, then buy.
  - Or use limit orders at the open (DAY validity) to cap gap risk.
- Trading during each market's regular session, not pre-market or overnight, avoids the wider spreads T212 warns about. For US names, set `extendedHours=false`.
- **Effective universe:** US (NYSE/NASDAQ, plus most OTC), UK (LSE/AIM), Germany, France, Netherlands, Belgium, Portugal, Spain, Italy, Switzerland, Austria, and possibly Canada and Japan. **Nordics and Hong Kong are not offered** per the market list.

### Gaps
- The exact exchange list for a UK ISA (especially TSX, Tokyo and Gettex) is not stated per account type. Confirm by calling `GET /api/v0/equity/metadata/exchanges` and `/instruments` on the ISA key.
- The size of the "reasonable percentage" buffer on blocked funds is not disclosed.
- Minimum order size (value or quantity) is not published in any help article read. The API exposes `maxOpenQuantity` but no minimum field.
- No independent spread or execution-quality statistics for Trading 212 were found (RTS 28 reports no longer exist; no Which?/Monevator execution study found).
- The conflict between Invest Terms cl. 6.4(a) (no instructions accepted while a market is closed) and cl. 12.5 and the API docs (orders queued) is unresolved. Behaviour should be tested in demo.

---

## 4. ISA rules relevant to the strategy

### Takeaway
- **Allowance:** £20,000 for 2025/26 and 2026/27, frozen until April 2031.
- **From 6 April 2027:** under-65s can put at most £12,000 into Cash ISAs. Interest on cash held inside a Stocks & Shares ISA will face a flat-rate charge at the savings basic rate (22%), and S&S-to-Cash ISA transfers are barred.
- **Tax:** gains and dividends are free of UK tax, but foreign withholding tax (e.g. 15% US with W-8BEN) is a final, unrecoverable cost inside an ISA.
- **Instruments:** shares, ETFs, ETPs, ETCs, REITs and ITs on recognised exchanges. No shorting, leverage or CFDs. No new crypto-ETN purchases from 6 April 2026.

### Cited Findings
- "In the 2026 to 2027 tax year, the maximum you can save in ISAs is £20,000." You must be 18+ and UK resident. — [gov.uk: Individual Savings Accounts](https://www.gov.uk/individual-savings-accounts)
- "You do not pay tax on: interest on cash in an ISA; income or capital gains from investments in an ISA". The allowance can be split across ISA types; the tax year runs 6 April to 5 April. — [gov.uk: How ISAs work](https://www.gov.uk/individual-savings-accounts/how-isas-work)
- **Autumn Budget 2025** (26 Nov 2025):
  - ISA subscription limit "will remain at £20,000 until April 2031".
  - From 6 April 2027 the Cash ISA limit is £12,000 for under-65s and stays £20,000 for 65+.
  - Anti-circumvention rules: no transfers from S&S/IFISA to Cash ISA; tests for "cash-like" investments; and "a charge on any interest paid on cash held in a stocks and shares or Innovative Finance ISA". These rules apply to under-65s.
  - From 2027/28 the savings basic, higher and additional rates rise to 22%, 42% and 47%.
  - — [HMRC Tax-free savings newsletter 19 (Nov 2025, updated 22 Dec 2025)](https://www.gov.uk/government/publications/tax-free-savings-newsletter-19/tax-free-savings-newsletter-19-november-2025)
- The ISA (Amendment) (No. 2) Regulations 2026 were laid on **14 Sep 2026** and come into force **6 April 2027**:
  - overall limit stays £20,000; under-65s may put £12,000 into Cash ISAs;
  - "a flat-rate charge, set at the savings basic rate, on interest ... that providers pay on cash held in Stocks and Shares and Innovative Finance ISAs";
  - a bar on under-65 transfers from non-Cash to Cash ISA;
  - S&S ISA investments may not consist entirely of money market funds;
  - purpose rules for cash held in non-Cash ISAs were removed after consultation.
  - — [HMRC Tax-free savings newsletter 23 (29 Sep 2026)](https://www.gov.uk/government/publications/tax-free-savings-newsletter-23/tax-free-savings-newsletter-23-september-2026)
- Trading 212 restates: from 6 April 2027 the overall limit stays £20,000 and under-65 Cash ISA contributions are capped at £12,000. There is no change before then (edited 16 Oct 2026). — [T212: Upcoming ISA Allowance Changes](https://helpcentre.trading212.com/hc/en-us/articles/32116234003997-Upcoming-ISA-Allowance-Changes-Effective-6-April-2027)
- The T212 Stocks ISA minimum deposit is £1. It is **flexible**: withdrawn current-year funds can be replaced without using allowance (edited 9 Dec 2025). — [T212: Stocks and Shares ISA](https://helpcentre.trading212.com/hc/en-us/articles/32380375609117-Stocks-and-Shares-ISA)
- The ISA Terms confirm both T212 ISAs are flexible "effective from April 6, 2024". Non-qualifying investments, including those received via corporate actions, must be dealt with under cl. 4.5. Fractional shares must be sold on a full ISA transfer-out. — [T212 ISA Terms (PDF)](https://www.trading212.com/legal-documentation/uk/isa/ISA-Terms_EN.pdf)
- **Crypto ETNs:** "From 6 April 2026: You can hold or sell existing positions, but new purchases will not be allowed" in the ISA, following the HMRC rule change (edited 27 Feb 2026). — [T212: Crypto ETNs in ISA accounts](https://helpcentre.trading212.com/hc/en-us/articles/31007919710365-Crypto-ETNs-in-ISA-accounts)
- **OTC stocks:** "Most OTC stocks we offer meet HMRC's eligibility criteria and are allowed in an ISA." — [T212: What is an OTC-traded stock?](https://helpcentre.trading212.com/hc/en-us/articles/360009775317-What-is-an-OTC-traded-stock)
- **Recognised stock exchanges:** HMRC publishes lists of designated recognised stock exchanges (updated 21 Apr 2026) and designated countries (updated 31 Jul 2026). Shares officially listed on these, or admitted to trading on a recognised EEA exchange market, qualify for S&S ISAs. — [gov.uk: Recognised stock exchanges](https://www.gov.uk/guidance/recognised-stock-exchanges); [James Hay ISA permitted investments](https://www.jameshay.co.uk/media/5867/modular-isa-permitted-investments-list.pdf); [HMRC 2013 ISA note](https://assets.publishing.service.gov.uk/media/5a75ba6ce5274a436829983e/isa-aug2013.pdf)
- **No short selling:** "You are not permitted to Short Sell" (Invest Terms cl. 12.8, which also govern the Stocks ISA). CFDs are a separate account type and are not in the ISA instrument list. — [T212 Invest Terms (PDF)](https://www.trading212.com/legal-documentation/uk/invest/Invest-Terms_EN.pdf); [T212: Instruments](https://helpcentre.trading212.com/hc/en-us/articles/11717160183197-What-trading-instruments-does-Trading-212-offer)
- **W-8BEN:** non-US investors "must complete the W-8BEN form" to buy US stocks. It lowers the 30% US rate on dividends. It "is valid for the year when it's signed and the three following calendar years" (edited 3 Sep 2026). — [T212: What is a W-8BEN?](https://helpcentre.trading212.com/hc/en-us/articles/360007080877-What-is-a-W-8BEN)
- A valid W-8BEN reduces US dividend withholding from 30% to 15% under the US–UK treaty. — [Fidelity UK: W-8BEN](https://fidelity.co.uk/international-shares/w-8ben-form)
- Withholding tax is applied before dividends are credited. Where T212 cannot adjust it to the treaty rate, the investor must reclaim via the source-country authority. T212's example: German WHT of 26.375% on an Allianz dividend (edited 20 Feb 2026 and 25 Sep 2025). — [T212: Do you charge any taxes on profits?](https://helpcentre.trading212.com/hc/en-us/articles/360007080857-Do-you-charge-any-taxes-on-profits); [T212: How can I receive dividends?](https://helpcentre.trading212.com/hc/en-us/articles/360007327218-How-can-I-receive-dividends-Invest-Stocks-ISA)
- **Reclaiming inside an ISA:** there is no UK tax liability inside an ISA against which to credit foreign tax. Only withholding above the treaty rate is reclaimable, so the US 15% is not reclaimable. These are forum and broker-guide sources, not HMRC. — [Freetrade community](https://community.freetrade.io/t/withholding-tax-15/41240?page=2); [Financial Interest: W-8BEN explained](https://financialinterest.com/w-8ben-explained/)

### Inferences
- **Dividend model:** net dividend = gross × (1 − WHT_country), with no FX fee and no UK tax. US is 15% with W-8BEN.
  - Other markets withhold at their domestic rate unless T212 applies treaty relief. Examples: Germany 26.375% per T212's own example; France, Switzerland (35% statutory) and others likely at statutory rates. Excess over treaty is reclaimable only via the foreign tax authority, and is impractical at £500–£1,000 sizes.
  - UK dividends carry 0% WHT. This favours UK and US holdings for a dividend-sensitive strategy.
- **The April 2027 cash-interest charge** matters for a weekly strategy that leaves cash idle in the ISA between rebalances. Interest earned on that cash (T212 pays interest on S&S ISA cash) would be taxed at 22% from 6 April 2027, for under-65s per HMRC's Nov 2025 summary. Model the interest at 78% of gross from that date.
- ISA rules do not cap trading frequency. Weekly turnover is allowed; costs, not ISA rules, are the constraint.

### Gaps
- Official HMRC guidance on the mechanics of the flat-rate charge (whether the provider deducts it at source, and the age test detail) is not yet published. HMRC says ISA manager guidance will come before 6 April 2027.
- No HMRC primary text was found stating that the 15% US WHT is unrecoverable inside an ISA; this rests on forum and broker sources plus reasoning.
- The country-by-country WHT rates T212 actually applies to UK ISA holders (treaty vs statutory) are not published by T212.

---

## 5. Trading 212 public API: availability, endpoints, limits, terms

### Takeaway
The public API (v0, **beta**) is live for **Invest and Stocks ISA** accounts, not SIPP. It supports market, limit, stop and stop-limit orders by fractional **quantity** only (no value orders), executed only in the account's primary currency. Per-account rate limits apply (e.g. market orders 50 requests/minute, limit orders 1 per 2 seconds), and order endpoints are not idempotent.

The binding constraint is contractual: the API Terms and Invest Terms **prohibit Algorithmic Trading**, defined as orders whose parameters a computer determines "with limited to no human intervention". "High-speed or automated mass data entry" and "customised interfaces" need T212's prior written consent.

### Cited Findings
- "Only for Invest and Stocks ISA. The API described here is enabled and usable only for Invest and Stocks ISA account types." — [T212 Public API docs (v0, beta)](https://docs.trading212.com/api)
- **Environments:** Paper `https://demo.trading212.com/api/v0` and Live `https://live.trading212.com/api/v0`. — same source.
- **Other API rules (same docs):**
  - "Orders can be executed only in the primary account currency".
  - "Multi-currency accounts are not currently supported through the API".
  - Sells use a negative `quantity` (e.g. −10.5).
  - Authentication is HTTP Basic with API_KEY:API_SECRET. Keys can be IP-restricted.
  - Rate limits apply "on a per-account basis, regardless of which API key is used or which IP". Headers: x-ratelimit-limit, -period, -remaining, -reset and -used.
  - "maximum of 50 pending orders allowed per ticker, per account".
  - List pagination: max 50 items per page, cursor via `nextPagePath`.
- **Endpoints and rate limits (official OpenAPI spec, version v0):**
  - Orders:
    - `POST /equity/orders/market` — 50 req/1m.
    - `POST /equity/orders/limit` — 1 req/2s.
    - `POST /equity/orders/stop` — 1 req/2s.
    - `POST /equity/orders/stop_limit` — 1 req/2s.
    - `DELETE /equity/orders/{id}` — 50 req/1m.
    - `GET /equity/orders` (pending) — 1 req/5s.
    - `GET /equity/orders/{id}` — 1 req/1s.
  - Account and portfolio:
    - `GET /equity/positions` — 1 req/1s.
    - `GET /equity/account/summary` — 1 req/5s.
  - Metadata:
    - `GET /equity/metadata/instruments` — 1 req/50s (data refreshed every 10 min).
    - `GET /equity/metadata/exchanges` — 1 req/30s.
  - History:
    - `GET /equity/history/orders`, `/dividends`, `/transactions` — 20 req/1m each.
    - CSV exports: POST 1 req/30s, GET 1 req/1m.
  - Pies are deprecated.
  - — [T212 OpenAPI spec](https://docs.trading212.com/_bundle/api.json?download)
- **Request schemas:**
  - `MarketRequest` = {ticker, quantity (number, example 0.1), extendedHours (bool, default false)}. "If placed when the market is closed, the order will be queued to execute when the market next opens."
  - `LimitRequest` = {ticker, quantity, limitPrice, timeValidity ∈ {DAY, GOOD_TILL_CANCEL}}. DAY expires at midnight in the exchange's time zone.
  - All order POSTs: "In this beta version, this endpoint is not idempotent. Sending the same request multiple times may result in duplicate orders."
  - "Placing orders by value is not currently supported via the API"; `strategy` is QUANTITY only.
  - — [T212 OpenAPI spec](https://docs.trading212.com/_bundle/api.json?download)
- **Response schemas:**
  - `TradableInstrument` has ticker (e.g. AAPL_US_EQ), isin, currencyCode, type, maxOpenQuantity, extendedHours and workingScheduleId.
  - `Fill` has price, quantity, tradingMethod ∈ {TOTV, OTC} and `walletImpact` {fxRate, netValue, realisedProfitLoss, taxes[]}. The tax names are listed in section 2.
  - — same source.
- **Help-centre API facts** (edited 31 Aug 2026):
  - "Currently, the Public API section is visible only for the General Invest Account and the Stock & Shares ISA Account"; not available for SIPP.
  - "You can place Market Orders via the Trading 212 API for live accounts" and "Limit, Stop and Stop Limit orders ... for live accounts".
  - Keys are scoped by permission (account data, history, orders, portfolio) and can be IP-restricted. The secret is shown once.
  - — [T212: Trading 212 API key](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-Trading-212-API-key)
- **API Terms (last updated 17 Oct 2025):**
  - cl. 1.3–1.5: the API "is currently in beta testing", use is "entirely at your own risk".
  - cl. 3.4: API orders go through T212's Systematic Internaliser.
  - cl. 4.2(a): "**You are expressly prohibited from using our API for Algorithmic Trading purposes**". Scalping, API abuse and exploiting price errors are also banned (4.2(b)).
  - cl. 6.1–6.2: licence is "solely for your personal use ... and only for testing purposes".
  - cl. 6.6: "The use of any high-speed or automated mass data entry system with our API will only be permitted with our prior written consent".
  - cl. 6.7: "Use of any customised interface shall be subject to our prior written consent".
  - cl. 7.1(b): "You will not receive real-time information on Market Data".
  - cl. 9.1: T212 may suspend API access or "vary the limits" at any time without notice.
  - cl. 11: "Algorithmic Trading means any kind of trading in Instruments where a computer algorithm automatically determines individual parameters of Orders, such as whether to initiate the Order, the timing of execution, price or quantity of the Order, or how to manage the Order after its submission, with limited to no human intervention".
  - — [T212 API Terms (PDF)](https://www.trading212.com/legal-documentation/API-Terms_EN.pdf)
- The Invest Terms cl. 5.1 (updated 7 Aug 2026) repeat the ban for the Share Dealing Services generally: "expressly prohibited from making use of our Share Dealing Services for Algorithmic Trading purposes". T212 reserves the right to close such accounts. The definition is identical. — [T212 Invest Terms (PDF)](https://www.trading212.com/legal-documentation/uk/invest/Invest-Terms_EN.pdf)

### Inferences
- **Compliance risk.** A strategy where code decides what, when and how much to trade and submits orders unattended appears to fall squarely within the prohibited definition. The consequence could be API revocation or account closure (Invest Terms 5.1; API Terms 9.1).
  - Lower-risk designs: (a) the model generates a proposed weekly order list, and a human reviews and explicitly approves each batch before the script submits it. Log the approvals.
  - Or (b) seek T212's prior written consent under API Terms cl. 6.6–6.7.
  - Whether (a) is sufficient "human intervention" is not defined by T212.
- **Practical API design for a weekly rebalance of ~20–50 names:**
  - Market orders (50/min) are not a bottleneck.
  - Limit orders (1 per 2 s) take about 1–2 minutes for 50 names.
  - Poll `GET /equity/orders/{id}` (1/s) or positions (1/s) for fills.
  - Because posts are not idempotent, never blind-retry an order POST on a timeout. First reconcile against `GET /equity/orders` and history.
- **Orders must be sized by quantity**, not value: quantity = target_GBP / (price_in_ccy / FX). Leave the 95%-of-cash headroom, and round to the instrument's allowed fractional precision. The precision is not documented; check rejections in demo.
- **Use `walletImpact.taxes` from history** to get exact realised FX fees, SDRT, FTT, PTM and SEC/FINRA per fill. This is the ground truth for calibrating the cost model, and for discovering whether Spanish or Italian FTT is charged.
- **No real-time market data via the API** (API Terms 7.1(b)), so pricing and signals need an external data source.

### Gaps
- There is no public statement of what level of human involvement takes a workflow outside the "Algorithmic Trading" definition. I found no T212 community or official clarification. Recommend asking T212 support in writing.
- The quantity precision (decimal places) per instrument and the minimum order quantity are not in the API spec.
- No changelog was found listing API changes in 2026 (the community forum search returned nothing via the API).

---

## 6. Total round-trip cost estimates (£500–£1,000 per position)

### Takeaway
For a GBP ISA at £500–£1,000 per position, explicit round-trip costs are about:
- **US:** 0.30%, essentially all FX.
- **UK main-market shares:** 0.50% (SDRT).
- **UK ETFs and AIM:** 0%.
- **France in-scope large caps:** 0.70%.
- **Spain and Italy in-scope:** about 0.50% if their FTT is passed through.
- **Other EU, Swiss, Canadian, Japanese:** 0.30%.

Add the exchange bid/ask spread: a few bps for mega-caps, much more for small caps and AIM. Below £10,000 the PTM levy never applies, and SEC/FINRA fees are negligible at these sizes. Every explicit cost is proportional, so percentages are identical at £500 and £1,000.

### Cited Findings
- T212's own worked example for a USD stock (GBP account, £1,000, 36-month hold, GBP/USD 1.1): FX buy £1.50 + FX sell £1.35–£1.65, plus US sell levies about £0.04. Total ≈ £2.89–£3.19, i.e. **0.29–0.32%**. The levies in that example use stale SEC/FINRA rates. — [T212 Costs & Charges Disclosure](https://www.trading212.com/legal-documentation/uk/common/Costs-and-Charges-Disclosure_EN.pdf)
- T212's example for a GBP stock: SDRT £5.00 on £1,000 (0.5%). PTM appears only on the £10,000 scenario's sell (~£10,945 gross). The PDF shows £1; the current rate is £1.50. — same source; [T212: Applicable stock exchange fees](https://helpcentre.trading212.com/hc/en-us/articles/360007081637-What-are-the-applicable-stock-exchange-fees)
- T212's example for a GBP-denominated ETF: no FX, no government taxes or levies; only the fund's OCF. — [T212 Costs & Charges Disclosure](https://www.trading212.com/legal-documentation/uk/common/Costs-and-Charges-Disclosure_EN.pdf)
- Rates used below:
  - FX 0.15% per conversion — [T212 FX fee](https://helpcentre.trading212.com/hc/en-us/articles/360018909758-What-is-the-FX-fee-Invest-Stocks-ISA)
  - SDRT 0.5% and PTM £1.50 over £10k — [T212 fees](https://helpcentre.trading212.com/hc/en-us/articles/11471996799517-What-are-the-fees-in-the-Invest-ISAs-and-SIPP)
  - SEC 0.00206% — [FINRA notice](https://www.finra.org/sites/default/files/2026-03/Information-Notice-20260317.pdf)
  - FINRA TAF $0.000195/share — [T212](https://helpcentre.trading212.com/hc/en-us/articles/360007081637-What-are-the-applicable-stock-exchange-fees)
  - French FTT 0.4% — [Legifiscal](https://www.legifiscal.fr/actualites-fiscales/4362-taxe-transactions-financieres-liste-societes-concernees-1er-decembre-2025.html)
  - Spanish ITF 0.2% — [AEAT list](https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/Declaraciones_informativas/I_Transacciones_Financieras/RELACION_SOCIEDADES_EJERCICIO_2026.pdf)
  - Italian FTT 0.2% — [DWF](https://dwfgroup.com/en/news-and-insights/insights/2026/1/2026-budget-law-key-tax-changes)

### Inferences
**Explicit round-trip cost per £1,000 position** (buy then sell at an unchanged price). Spread is an assumption and must be calibrated from real fills.

| Market (GBP ISA) | Buy-side explicit | Sell-side explicit | Explicit round trip | Assumed spread, round trip (large cap) | All-in estimate |
|---|---|---|---|---|---|
| US NYSE/NASDAQ large cap (e.g., $150 share) | FX £1.50 | FX ~£1.50 + SEC ~£0.02 + FINRA ~$0.01 | ≈ £3.02 (0.302%) | 2–6 bps | ≈ 0.32–0.36% |
| US small/mid cap or OTC | FX £1.50 | FX + SEC + FINRA | ≈ 0.30% | 10–100+ bps | 0.4–1.3% |
| UK main market, UK-incorporated (FTSE 100) | SDRT £5.00 | £0 (PTM only if >£10k) | £5.00 (0.50%) | 4–10 bps | ≈ 0.54–0.60% |
| UK FTSE 250 / smaller | SDRT 0.5% | 0 | 0.50% | 10–40 bps | 0.6–0.9% |
| UK AIM (most) | 0 | 0 | 0% | 50–300 bps | 0.5–3% |
| UK-listed ETF (GBP line) | 0 | 0 | 0% | 2–15 bps | 0.02–0.15% (plus OCF) |
| France, French HQ & cap >€1bn (2026 list) | FTT 0.4% + FX 0.15% | FX 0.15% | 0.70% | 4–10 bps | ≈ 0.74–0.80% |
| France, out-of-scope issuer | FX 0.15% | FX 0.15% | 0.30% | 4–10 bps | ≈ 0.34–0.40% |
| Spain, cap >€1bn (2026 list) | ITF 0.2%* + FX 0.15% | FX 0.15% | 0.50%* | 4–12 bps | ≈ 0.54–0.62%* |
| Italy, cap ≥€500m | FTT 0.2%* + FX 0.15% | FX 0.15% | 0.50%* | 4–12 bps | ≈ 0.54–0.62%* |
| Germany / NL / BE / PT / AT / CH | FX 0.15% | FX 0.15% | 0.30% | 4–10 bps | ≈ 0.34–0.40% |
| Canada (TSX) / Japan (TSE), if ISA-available | FX 0.15% | FX 0.15% | 0.30% | 5–15 bps | ≈ 0.35–0.45% |
| Irish-incorporated (e.g., Dublin line) | possibly 1% stamp duty* + FX | FX | up to 1.30%* | — | unverified |

\* Pass-through by Trading 212 not confirmed (see section 2 Gaps).

- **Size effects:**
  - £500 vs £1,000 changes nothing in percentage terms; all explicit costs are proportional.
  - FINRA TAF is per share with a $0.01 floor, so it is negligible.
  - PTM (£1.50 per side) only bites above £10,000 consideration.
  - Card-deposit fees (0.7% after £2,000 lifetime) should be avoided by funding through bank transfer.
- **Turnover drag** ≈ (round trips per year) × (round-trip cost). Examples:
  - Replacing 20% of an all-US book weekly = 0.2 × 52 = 10.4 round trips/yr × ~0.33% ≈ **3.4% per year**.
  - The same turnover in UK main-market names ≈ 10.4 × ~0.56% ≈ **5.8% per year**.
  - In French in-scope names ≈ 10.4 × ~0.77% ≈ **8% per year**.
  - This argues for turnover penalties, no-trade bands and preferring US, non-FTT EU, UK AIM/ETF lines for high-churn sleeves.
- Since the buy/sell asymmetry is large (UK, France, Spain and Italy tax only buys; the US taxes only sells, and minimally), code buy-side and sell-side costs separately rather than as a symmetric half-cost.
- **Dividend leakage** (WHT, section 4) is an additional holding cost for non-UK names: 15% of the yield for the US, potentially 26–35% of the yield for Germany and Switzerland.

### Gaps
- Spread assumptions are not sourced from Trading 212 execution data; none is published. Calibrate with live or demo fills.
- Whether Trading 212 collects the Spanish and Italian FTT and Irish stamp duty materially changes the Spanish, Italian and Irish rows; this is unverified.
- ISA availability of TSX and Tokyo instruments is unconfirmed.
