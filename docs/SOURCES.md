# Sources

External research backing the hypotheses and product decisions in this
project. Not a bibliography for its own sake — every entry here is tied to
a specific claim used somewhere in `EXPERIMENT.md`, `docs/PLAN.md`, or
`BACKLOG.md`, and that claim links back here.

**Tagging convention, used on every entry:**
- **[fetched]** — the actual page was retrieved and read (via `WebFetch` or
  a direct request) in this project's own research, not recalled from
  training data. Author/date/claims below come from that fetch.
- **[snippet]** — only a search-engine result summary was available (the
  source itself 403'd, is paywalled, or wasn't re-fetched); treat the
  specific numbers as approximate until someone reads the primary source.

**Where a fetch corrected something already written elsewhere in this
repo, that correction is called out explicitly** rather than silently
folded in — same discipline `EXPERIMENT.md` already uses for its own
struck-through numbers.

---

## 1. H1 — free float, ownership concentration, and volatility

- **Glass Lewis, "Free Float, Ownership Transparency and Governance
  Quality: What Indonesia's Market Stress Revealed"** — Decky Windarto,
  Director of Research, South & Southeast Asia and Hong Kong. Published
  **11 Feb 2026**. **[fetched]**
  <https://www.glasslewis.com/article/free-float-ownership-transparency-governance-quality-what-indonesia-market-stress-revealed>
  - Indonesia's minimum free-float requirement has stood at **~7.5%** for
    years — low by international standards, and a contributor to the
    market's vulnerability during liquidity stress.
  - Regulators are moving to raise the minimum to **15%**, with increased
    scrutiny of shareholder affiliations (including holdings below
    traditional reporting thresholds), following MSCI's investability
    review.
  - Explicitly hedged: effectiveness "will hinge on clear definitions of
    public ownership and meaningful enforcement," not the headline number
    alone.
  - Does **not** mention monthly free-float reporting or a separate
    minimum for smaller IPOs — those specifics were not found in this
    article and should not be cited from it. (An earlier internal note
    claimed both; struck here rather than carried forward unverified.)
  - **How it's used:** `EXPERIMENT.md`'s H1 Limits — states the regulatory
    tension plainly (regulators treat *low* free float as the risk to fix;
    H1 found small-cap *volatility* rising with *higher* float) without
    resolving it either way.

- **Jakarta Globe, "Indonesia to Raise Minimum Free Float Requirement to
  15% After MSCI Review."** **[snippet]**
  <https://jakartaglobe.id/business/indonesia-to-raise-minimum-free-float-requirement-to-15-after-msci-review>
  Corroborates the Glass Lewis 7.5%→15% figures independently.

- **"Volatility Drivers in Islamic Stock Markets: IDX30"** (title as
  found; full citation not resolved). **[snippet]** — free float was
  **not** individually significant as a volatility driver among the
  large-cap IDX30 constituents. Consistent with H1's own finding that the
  effect is concentrated in small caps and nearly vanishes among large
  ones — cited as external corroboration of that boundary condition, not
  of the headline direction.

- **Turkey ISE free-float study** (title/authors not resolved).
  **[snippet]** — reported the same *direction* H1 found (higher free
  float associated with higher volatility), in a different emerging
  market. Weak corroboration only — not the same market, not re-fetched.

- **China A-shares free-float risk premium study** (title/authors not
  resolved). **[snippet]** — a free-float-related risk premium documented
  in Chinese equities. Noted as a parallel literature, not a direct
  comparison.

## 2. H1 — saham gorengan / manipulation literature

- **Pump-and-dump mechanics on IDX** — accumulation / mark-up /
  distribution phase framing, standard in the pump-and-dump literature.
  **[snippet]**

- **"Pump-Dump Manipulation Analysis: The Influence of Market
  Capitalization and Its Impact on Stock Price Volatility at Indonesia
  Stock Exchange."** **[snippet]**
  <https://www.researchgate.net/publication/344164378_Pump-Dump_Manipulation_Analysis_The_Influence_of_Market_Capitalization_and_Its_Impact_on_Stock_Price_Volatility_at_Indonesia_Stock_Exchange>
  - **Correction from an earlier internal note:** this is not "a 2015
    study" — the *observation window* it analyzes is 30 Nov–30 Dec 2015
    (149 IDX companies, manipulation identified across 14 distinct
    periods within that month); ResearchGate's own metadata dates
    *publication* to **2018**. Both dates matter and shouldn't be
    conflated.
  - Trading-volume/CAR correlation tested positive up to 4 trading days
    after the manipulated period — i.e. detectable abnormal volume
    precedes/accompanies the price move, the mechanism the "gorengan"
    framing describes informally.

- **Law No. 8/1995** (Indonesian Capital Market Law) — the legal
  framework under which OJK's anti-manipulation and disclosure rules
  operate. **[snippet]**, not re-fetched this session.

## 3. H5 — value/size factor studies, and the root cause of its own inversion

- **The Evidence-Based Investor, "The case for factor investing in
  emerging markets."** Robin Powell. Published **7 Feb 2025** (updated 9
  Feb 2025). **[fetched]**
  <https://www.evidenceinvestor.com/post/factor-investing-in-emerging-markets>
  - Citing **Zaremba & Konieczka (2015)**, tested across 11 Central and
    Eastern European markets: after accounting for realistic trading
    costs (spreads, liquidity constraints, market frictions), **value was
    the only premium left standing**.
  - The **size premium's** impact from trading costs was "almost lethal"
    — Poland's size advantage "vanished entirely" once frictions were
    included; described as gross size returns being "obliterated" by the
    cost of actually capturing them in thin emerging markets.
  - **How it's used:** `EXPERIMENT.md`'s H5 Limits — general literature
    runs *opposite* to what H5 found (H5's value leg failed to confirm in
    holdout; its size leg produced an unpredicted, significant holdout
    result). Cited as context for that mismatch, not as proof of anything
    about IDX specifically — no IDX data appears in this source.

- **IDX-specific Fama-French factor studies** (2003–2006 sample,
  confirming both value and size factors; a separate LQ45 2014–2018 study
  finding size significant and *negative*). **[snippet]**, titles/authors
  not resolved this session — flagged as worth a proper fetch before any
  of these numbers are quoted directly.

- **Drew (2002), KLSE size/value study.** **[snippet]** — Malaysian
  market parallel to the CEE finding above (size fragile, value more
  durable).

### The root-cause investigation for H5's own explore→holdout inversion

Not a literature comparison — checks against this project's own data,
done to explain *why* H5 found an unpredicted, significant size effect in
its 2024-formation holdout (May–Sep 2025 return window) that exploration
gave no reason to expect.

- **Jakarta Globe, "Indonesia Stock Market Hits New Record; Five Stocks
  Surge Up to 34%."** **[fetched, date corrected this session]**
  <https://jakartaglobe.id/business/indonesia-stock-market-hits-new-record-five-stocks-surge-up-to-34>
  - **Published 4 December 2025** — JCI at 8,640.20. Named gainers:
    Indopoly Swakarsa Industry (IPOL), Surya Permata Andalan (NATO),
    Triniti Dinamik (TRUE), Teknologi Karya Digital Nusa (TRON), Wulandari
    Bangun Laksana (BSBK) — each up ~34%+ in a single day.
  - **Correction:** an earlier internal note described this as a
    "mid-May-2025" surge and used that framing when checking these
    tickers against H5's holdout data. The article is dated **December
    2025**, not May 2025. This actually makes the ruling-out *more*
    decisive, not less: December 2025 falls entirely outside H5's
    2024-formation outcome window (returns measured to Sep 4, 2025 at the
    latest), so a single-day rally reported three months after that
    window closed cannot mechanically explain a return already measured
    inside it.
  - **Checked directly against H5's own data regardless of the date
    mix-up:** IPOL and TRON landed in Q2 of the free-float/size sort (not
    the smallest quintile that drives the holdout result); NATO landed in
    Q3; TRUE was not even in the eligible sample; TRON's actual measured
    return over H5's real May–Sep 2025 window was **−28%** (a reversal,
    not a surge caught in that window). **Ruled out** as the explanation
    for the size result, on the data itself — independent of whether the
    news article's date was originally misstated.

- **Databoks/Katadata, Bank Indonesia rate-decision reports.**
  **[snippet, dates corrected/expanded this session]**
  <https://databoks.katadata.co.id/en/monetary/statistics/6787f034af5af/bank-indonesia-cuts-interest-rate-to-575-at-the-beginning-of-2025>,
  <https://databoks.katadata.co.id/en/monetary/statistics/687859a3b8957/indonesias-central-bank-cuts-interest-rate-to-525-in-july-2025>
  - BI cut its benchmark rate **three** times in 2025, not two as an
    earlier internal note said: **15 Jan** (6.00%→5.75%), **21 May**
    (→5.50%), **15–16 Jul** (→5.25%) — each −25bp. The **21 May** cut in
    particular lands right at the start of H5's 2024-formation outcome
    window (May–Sep 2025), which an earlier "two cuts" framing missed.
  - **How it's used:** `EXPERIMENT.md`'s H5 Limits — the best-supported
    (not proven) explanation for the size result is a regime-specific,
    rate-cut-driven small-cap rotation coinciding with the holdout window,
    not a persistent IDX size premium. Explore years (2022–2023) had no
    comparable rate-cutting cycle, consistent with exploration never
    predicting this.

- **J.P. Morgan Private Bank, piece on the 2025 small-cap rally (Russell
  2000 context).** **[snippet]** — international precedent for the same
  general mechanism (falling rates disproportionately lifting small/thin
  names), used only as a mechanism analogy, not as evidence about IDX.

## 4. H2 / news and sentiment

- **Joseph Tanuri, "Post-Earnings-Announcement Drift in Indonesia."**
  Claremont McKenna College senior thesis, **2023**. **[fetched:
  abstract/summary only — full text is restricted to Claremont Colleges
  affiliates]**
  <https://scholarship.claremont.edu/cmc_theses/3400/>
  - Using Bloomberg data: **8.3%** PEAD for the top quintile of IDX stocks
    over the one-month window starting the day after earnings
    announcements; **15.48%** pre-announcement leakage starting two weeks
    before; portfolios built on this beat benchmark index portfolios with
    returns up to **5.83%** in 30 days (~20% annualized).
  - **Flagged explicitly: an unreviewed undergraduate thesis, not
    peer-reviewed literature.** Cited as groundwork if H2 is ever revived
    (currently dropped — see `docs/PLAN.md` §6), not as settled evidence.

- **General news/social-media sentiment vs. returns studies.**
  **[snippet]**, titles/authors not resolved this session. Distinct from
  PEAD — recorded as the basis for candidate **H9** in `BACKLOG.md`, not
  to be conflated with H2.

## 5. Competitive / product landscape

Extends `docs/PLAN.md` §4.5.

- **IndoFinancial** — Indonesian stock screener/portfolio platform.
  **[fetched]** <https://www.indofinancial.com/>,
  <https://indofinancial.com/screener/>
  - Ships a valuation screener with three buckets: **Murah** (cheap),
    **Wajar** (fair), **Mahal** (expensive) — filterable alongside
    technical trend, P/E, P/B, ROE, and sector, across 965+ IDX
    companies. Also offers a macro dashboard, an "AI Stock Picker," and
    an MPT portfolio builder.
  - Conceptually this is the same claim as H5's value factor (cheap
    stocks are "Murah"), but the site publishes **no backtest or evidence
    the classification predicts anything** — an absence-of-evidence
    observation (nothing found in the pages fetched), not a proof that no
    backtest exists anywhere on the site. Directly supports this
    project's own positioning: nobody in this market publishes whether
    their signals work.

- **StockView.id, StockPilot.id** — existing IDX screeners, noted as part
  of the competitive landscape. **[snippet]**, not fetched this session.

---

*Every claim from this file that reaches `EXPERIMENT.md`, `docs/PLAN.md`,
or `BACKLOG.md` links back here rather than restating the source inline —
if a citation here turns out to be wrong, there is one place to fix it.*


---

## Problem statement and market facts (checked 2026-09-27)

Each figure below was read on the page named, in this session. "Secondary"
means the primary document (a regulator PDF) was blocked or unreadable, so a
news report quoting it was used instead, and the primary is still to be read.
The WebFetch tool returns page text through a summariser, so quotes marked
(summariser) were not seen verbatim.

- **KSEI: 20.32 million investors (SID) at end-2025, up 37% from 14.87 million.**
  Secondary: IPOT report of the KSEI director's statement, 29 Dec 2025.
  <https://www.indopremier.com/ipotnews/newsDetail.php?jdl=KSEI__Jumlah_Investor_Pasar_Modal_di_2025_Melonjak_37__Jadi_20_32_Juta_SID&news_id=210837&group_news=IPOTNEWS&news_date=&taging_subtype=REGULATIONS&name=&search=y_general&q=KSEI&halaman=1>
  The "5.45 million added" is our subtraction, not a stated figure. The KSEI
  statistics PDF was unreadable. **This corrects the earlier README figure of
  "4.28 million new investors in 2025".**
- **OJK and BPS, SNLIK 2025: capital-market literacy 17.78%, inclusion 1.34%.**
  Primary, released 2 May 2025. Overall literacy 66.46% and inclusion 80.51%
  (sustainability method) or 66.64% and 92.74% (DNKI coverage method); 10,800
  respondents, 34 provinces.
  <https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/OJK-dan-BPS-Umumkan-Hasil-Survei-Nasional-Literasi-Dan-Inklusi-Keuangan-SNLIK-Tahun-2025.aspx>
  **This corrects the earlier README figure of "1.55%".**
- **Retail share of trading 38% (2024) to 50% (end-2025).** Secondary: detik,
  2 Jan 2026, attributing it to OJK.
  <https://finance.detik.com/bursa-dan-valas/d-8288678/porsi-transaksi-investor-ritel-naik-ojk-bidik-aksi-goreng-saham>
  OJK's own release (SP 01/GKPB/OJK/I/2026) was an unreadable PDF and is not yet confirmed.
- **OJK "2L" (legal and logical).** Secondary: detik, 2 May 2025, quoting the
  head of the Satgas PASTI secretariat; Kontak OJK 157 is named for checking
  legality. The definition (legal = licensed or on the whitelist, logical = the
  promised return is plausible) comes from a search snippet and is not yet read
  on an ojk.go.id page.
  <https://news.detik.com/berita/d-7897116/ramai-scam-trading-kripto-ojk-ingatkan-2l-sebelum-investasi>
- **Minimum free float to 15%.** Glass Lewis (see section 1) says the regulator
  "indicated it would raise" it and states no effective dates. IPOT, 29 Jan
  2026: OJK's chair said the exchange would issue rules for a 15% minimum, with
  an adjustment period. No effective date was found; none is stated in this project.
  <https://www.indopremier.com/ipotnews/newsDetail.php?jdl=OJK_Tanggapi_Evaluasi_MSCI__BEI_akan_Revisi_Aturan_Free_Float_Saham_Jadi_15_&news_id=483970&group_news=RESEARCHNEWS&news_date=&taging_subtype=INDONESIA&name=&search=y_general&q=INDONESIA,+&halaman=1>
- **IDX price rules change on 28 Sep 2026.** Secondary: Katadata reporting exchange
  decision Kep-00136/BEI/09-2026 (21 Sep 2026): the minimum share price falls
  from Rp50 to Rp1 and auto-rejection bands change (the 15% lower limit widens from
  1 Jan 2027). The project's data is dated 13 Sep 2026 and predates it. Tick-size
  bands are not confirmed.
  <https://katadata.co.id/finansial/bursa/6ab0fe985f085/harga-minimum-saham-jadi-rp-1-mulai-pekan-depan-auto-rejection-disesuaikan>
- **Trading costs.** Secondary and old (CNBC Indonesia, 26 Jun 2019): broker
  commission 0.15% to 0.35% including VAT, levy about 0.04%, final income tax
  0.1% on sales only. A round trip of about 0.4% is therefore a low-end figure,
  not a typical one (inferred: roughly 0.4% to 0.75%).
  <https://www.cnbcindonesia.com/mymoney/20190626164219-72-80860/sebelum-jual-beli-saham-kenali-dulu-biaya-biaya-transaksinya>
- **Foreign net purchases and returns on the IDX.** Rudiawarni, Sulistiawan and
  Sergi, "The role of the net purchase of stocks by foreign investors in boosting
  stock returns: Evidence from the Indonesian stock market", *Economic Modelling*
  vol. 135, June 2024. Abstract read via RePEc (ScienceDirect blocked): net
  purchases "lead to higher excess returns" (summariser). The sample period and the
  horizon were not visible, so they are **not cited**.
  <https://ideas.repec.org/a/eee/ecmode/v135y2024ics0264999324000865.html>
- **Listed companies.** OJK's Hasan Fawzi, as reported by detik on 29 Jul 2026:
  "Saat ini perusahaan tercatat ada 963." Our universe of 962 (data of 13 Sep 2026)
  is consistent. <https://finance.detik.com/bursa-dan-valas/d-8595961/bursa-butuh-30-perusahaan-ipo-tiap-tahun-buat-capai-target-1-100-emiten/amp>
- **Listing boards (Utama, Akselerasi).** Only a 2023 secondary description was
  found; the IDX rule text was not opened, so no numeric listing criteria are
  stated in this project.
