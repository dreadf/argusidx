# Experiment Log

Living log of every hypothesis tested for ArgusIDX. One entry per
hypothesis: what we pre-registered, how we tested it, what we found,
what it means in plain language, why it came out that way, and what it
opens up. Nulls get logged with the same honesty as positives (see
RULES.md verification approach, item 6: "ship the null if it's null").

This is also the trial counter for selection-bias purposes: every entry
here, tested or explicitly abandoned, counts. See the hypothesis register
in the plan file for what's still queued.

---

## H1: Does free float predict volatility on IDX?

**Date:** 2026-09-06. **Re-run 2026-09-10 on corrected price data** (Yahoo
endpoint fix, `pipeline/dev/fetch_yahoo_prices.py` switched from
`/v7/finance/spark` to `/v8/finance/chart`: see `docs/DATA.md`). This
was **not** a small-delta refresh like the earlier `stats.py` tie-fix:
n grew from 853 to 913, and **two of the four "explanations" checked
below changed in substance, not just magnitude**: the liquidity-fade
boundary condition turns out to have been a coverage-gap artifact, and
the "holds in every year" claim does not survive on the corrected data.
Both are written up in full below, old numbers struck through per this
file's own convention, not silently replaced.
**Status:** Tested. Falsified, in the opposite direction, and more
specific than first thought. **Exploratory, not confirmatory**: see
Limits below.

### The hypothesis, written down before looking

IDX stocks with **lower free float** (a smaller share of stock actually
available for the public to trade) show **higher volatility** and
**deeper drawdowns** than high-float stocks. Basis: the documented
"saham gorengan" (pump-and-dump) mechanism, where a thinly-traded stock
can be moved a long way by a small amount of money.

**This hypothesis would be falsified if:** there's no consistent
(monotonic) relationship across free-float groups, or if the
relationship runs the other way.

### How we tested it

1. Pulled free float for all 961 IDX-listed companies from Sectors
   (`/v2/free-float/`, 10 credits: `data/raw/free_float_2026-09-06.json`).
2. Pulled a year of daily closing prices for those tickers from Yahoo
   Finance (free, development-time only: see `pipeline/dev/`). ~~853~~
   **913** of 961 had enough history to use (re-run 2026-09-10 on the
   corrected `/v8/finance/chart`-based cache: see `docs/DATA.md`).
3. For each stock, computed how much its price swings day to day
   (annualized volatility) and its worst fall from a peak (max
   drawdown) over that year.
4. Sorted all ~~853~~ **913** stocks by free float into five equal groups
   (quintiles) and compared the groups.
5. Measured the relationship with a rank correlation (Spearman's rho)
   and checked whether it could be coincidence (the t-statistic).

Full runnable code: `pipeline/hypotheses/h1_free_float.py`. Run with
`python -m pipeline.hypotheses.h1_free_float`: every number below comes
from that command, byte-for-byte.

### What we found

The opposite of what we expected, and not by a small margin.

~~The fifth of stocks with the **least** public ownership (about 9% of
shares) swung about **60%** a year. The fifth with the **most** public
ownership (about 49% of shares) swung about **90%** a year.~~

**Corrected 2026-09-10** (n=913, up from 853): the thinnest-float fifth
(median 9.0% public) swung about **54%** a year; the widest-float fifth
(median 49.0%) swung about **73%**. Same direction, a smaller gap than
first published.

So wide-float stocks were the wild ones, not the thin-float ones. The
odds this is a coincidence are still very low: ~~rho = +0.224, t =
+6.72~~ **rho = +0.177, t = +5.42**: still a t-statistic that essentially
never happens by chance, just not as extreme as first published.

There was **no relationship at all** between free float and how much
money a stock actually made or lost over the year (~~rho = +0.007, t =
+0.22~~ **rho = +0.009, t = +0.28**, statistically indistinguishable from
zero, unchanged in substance). This finding is about how bumpy the ride
was, not where it ended up.

### Two ways this could have been a false alarm: one genuinely ruled out, one we got wrong the first time

⚠️ **Correction (2026-09-07):** the "checked and ruled out" verdict below
for Explanation 1 was wrong. It's kept struck through rather than
deleted, because the mistake and the fix are both worth showing.

**Could it be that thin-float stocks just don't trade much, so their
prices only look calm because nobody's actually buying or selling?**

~~We checked by counting, for every stock, how many days its price
didn't move at all. Thin-float stocks sat still on 14.2% of days;
wide-float stocks sat still on 13.1% of days: almost identical. We also
reran the whole test using only stocks that genuinely trade often, and
the result held up just as strongly.~~

**What was actually wrong with that check:** "how many days its price
didn't move" only counts days a price *exists*. A stock that didn't
trade at all on a given day has no price to check, so those days were
invisible to the check: not counted as "calm," simply not counted. A
stock could be silent for months and this measure would never notice.
That is exactly the mechanism Explanation 1 describes, and the check
could not see it.

**Redone properly**, using the actual number of days each stock traded
(`pipeline/hypotheses/h1_stress.py`, test 1) instead of that measure:

~~| Require ≥ N trading days (of ~242 in the window) | n | ρ | t |
|---|---|---|---|
| none (full sample) | 853 | +0.224 | +6.72 |
| ≥190 | 784 | +0.196 | +5.60 |
| ≥210 | 663 | +0.148 | +3.85 |
| ≥220 | 502 | +0.109 | +2.45 |
| ≥230 | 161 | −0.026 | −0.33 (not significant) |

**The effect fades toward zero as required trading activity rises.**
That is a real, previously undisclosed boundary condition...~~

⚠️ **Correction (2026-09-10): the "fades with liquidity" boundary
condition above does not survive the Yahoo endpoint fix, and it was the
coverage gap itself that produced it, not a real property of the
market.** The old `spark`-endpoint cache had so little history for many
stocks that "require ≥230 trading days" left only 161 of 853 stocks: 
a small, and apparently unrepresentative, surviving slice. Re-run on the
corrected `/v8/finance/chart` cache (n=913, `pipeline/hypotheses/h1_stress.py`
test 1):

| Require ≥ N trading days (of ~242 in the window) | n | ρ | t |
|---|---|---|---|
| none (full sample) | 913 | +0.177 | +5.42 |
| ≥190 | 911 | +0.180 | +5.50 |
| ≥210 | 910 | +0.179 | +5.49 |
| ≥220 | 910 | +0.179 | +5.49 |
| ≥230 | 910 | +0.179 | +5.49 |
| ≥235 | 909 | +0.179 | +5.49 |

**The effect no longer fades at all.** Because coverage is now good
enough that 910 of 913 stocks clear even the strictest threshold, this
sweep barely changes the sample and the correlation is essentially flat
across it (+0.177 to +0.180, all clearly significant). **Read plainly:
the "undisclosed boundary condition" published on 2026-09-07 was itself
a Yahoo coverage-gap artifact**: the old cache's missing history was
disproportionately concentrated among certain stocks, and restricting to
"high trading-day count" was inadvertently restricting to whichever
stocks the old `spark` endpoint happened to cover well, not to
whichever stocks were actually thinly traded. The corrected result is
simpler than either prior version: **no fading, no reversal, no
liquidity boundary condition found.**

**The GOTO wrinkle, substantially resolved.** `GOTO.JK`: one of the
most actively traded stocks on IDX: showed only 128 of ~242 days in the
old cache, almost certainly a coverage gap rather than illiquidity. On
the corrected cache it shows **244 of ~249 days**: the gap for this
specific, heavily-traded symbol is gone. This doesn't prove every
residual short history is genuine illiquidity rather than a remaining
Yahoo gap, but it removes the clearest previously-known counterexample,
and the liquidity-sweep table above no longer shows any threshold effect
for the "poorly covered" explanation to be hiding behind. `docs/PLAN.md`
§8.3's Sectors-price cross-check is still owed before this is fully
closed (see Limits): "substantially resolved," not "resolved."

**Could this just be describing the 2026 market crash**, where foreign
investors pulled money out of Indonesia and hit the big, widely-owned
stocks hardest for reasons that have nothing to do with free float?
~~We checked by running the same test separately for every year from
2022 to 2026. The same pattern showed up **every single year**: this
part holds up~~:

⚠️ **Correction (2026-09-10): "holds in every year" is retracted; it
does not survive the Yahoo endpoint fix.** Re-run on the corrected cache
(n per year below, `pipeline/hypotheses/h1_free_float.py`):

| Year | ρ | t | thin-float vol | wide-float vol |
|---|---|---|---|---|
| 2022 | −0.033 | −0.91 (not significant) | 43.2% | 42.4% |
| 2023 | +0.001 | +0.02 (not significant) | 40.7% | 39.5% |
| 2024 | +0.179 | +5.39 | 43.8% | 57.3% |
| 2025 | +0.179 | +5.41 | 51.9% | 66.9% |
| 2026 | +0.164 | +4.95 | 54.6% | 71.0% |

**2022 and 2023 now show no relationship at all**: not weaker, *zero*,
in the case of 2023 (ρ = +0.001). This is not the growing-sample
confound already flagged and corrected once (below): checking on the
**balanced panel of 751 stocks present in all five years**
(`pipeline/hypotheses/h1_stress.py`, test 1) gives the same split: 
2022 ρ −0.033/t −0.91, 2023 ρ −0.024/t −0.66, both still not
significant, against 2024 t +4.63, 2025 t +4.16, 2026 t +4.26 on the
identical fixed panel. **Read plainly: this is a real, newly-disclosed
boundary condition, not an artifact of unbalanced samples or of the old
coverage gap**: the relationship is present in 2024–2026 and absent in
2022–2023, on the same 751 stocks either way. One plausible (unverified)
reading: free float is a single 2026 measurement, so it may describe
*current* ownership structure correlating with *recent* trading
behaviour better than it describes ownership years before it was
measured: but this is speculation, not something this data can confirm,
since (as already established below) there is no historical free-float
series to test against directly.

~~| Year | all stocks | fixed panel (564 stocks) |
|---|---|---|
| 2022 | ρ +0.081, t +2.02 | ρ +0.046, t +1.08 |
| 2023 | ρ +0.076, t +1.97 | ρ +0.043, t +1.02 |
| 2024 | ρ +0.179, t +5.01 | ρ +0.060, t +1.43 |
| 2025 | ρ +0.194, t +5.58 | ρ +0.050, t +1.18 |
| 2026 | ρ +0.199, t +5.71 | ρ +0.111, t +2.65 |

On a fixed panel the effect is +0.04 to +0.11 and clears significance in
**one** of five years. **What survives:** the effect appears in every
year, so it isn't a one-off 2026 artifact. **What doesn't:** any claim
that it's intensifying over time.~~ **Superseded by the balanced-panel
numbers above** (751 stocks, not 564: coverage improved enough that the
fixed panel itself grew). The corrected, current statement: **the
effect is not present in every year: it clearly holds 2024–2026 and is
absent in 2022–2023**, on the same fixed set of stocks throughout.

### A confound we did find, and it sharpened the finding

We wondered whether "free float" was secretly just a stand-in for
"company size" (big companies vs small ones). It isn't: the two are
barely related. But splitting stocks into four groups by size and
re-running the test inside each group revealed something more precise: 
**revised 2026-09-10, and the revision is substantive, not cosmetic:**

~~**The whole effect lives in small companies.** Among the smallest IDX
companies, high-float stocks swing about **102%** a year against **75%**
for closely-held ones: a huge gap. Among the largest companies, free
float barely matters at all (53% vs 47%).~~

⚠️ **Correction (2026-09-10): "the whole effect lives in small
companies" does not survive the Yahoo endpoint fix.** Re-run on the
corrected cache (n=913, `pipeline/hypotheses/h1_free_float.py`):

| Size bucket | ρ(float, vol) | t | low-float vol | high-float vol |
|---|---|---|---|---|
| Smallest | +0.215 | +3.32 | 68.5% | 83.9% |
| Small-mid | +0.139 | +2.11 | 57.9% | 72.1% |
| Mid-large | +0.086 | +1.29 (not significant) | 51.1% | 58.0% |
| Largest | +0.170 | +2.60 | 43.1% | 50.6% |

**This is a different shape, not just smaller numbers.** The original
result showed one bucket (smallest) carrying almost the entire effect
(t=+7.64) with the other three weak-to-borderline. The corrected result
shows the effect **significant in three of four buckets: including the
largest**: and weakest in the second-largest ("mid-large") bucket, not
monotonically fading with size. **The "small-cap-specific" framing this
project has used since 2026-09-06: including in `docs/PLAN.md`'s
product design for a per-stock applicability rule ("H1 does not apply to
BBCA, the largest IDX company"): no longer holds up as a clean
description of the corrected data**, and needs to be revisited before
any product decision continues to rely on it. Recorded here rather than
silently propagated; see Limits and `BACKLOG.md` for the follow-up this
requires.

### A third explanation, tested after the fact: is this just cheap stocks?

IDX prices move in fixed steps (a "tick"), and the tick is a bigger
percentage of a cheap stock's price than an expensive one's: a Rp 1
tick is a 2%+ move on a Rp 40 stock but under 0.4% on a Rp 6,000 one.
Cheap stocks can look mechanically more volatile for a reason that has
nothing to do with turbulence.

~~`pipeline/hypotheses/h1_stress.py`, test 2: 18.1% of the 853 stocks
trade under Rp 100 (tick ≥1% of price), 5.3% under Rp 50 (tick ≥2%).
Restricting to stocks trading at Rp 500 or more (tick under 1%): n=334,
ρ = −0.023, t = −0.43: **not significant**.~~ **Corrected 2026-09-10**
(n=913): 20.6% of stocks trade under Rp 100, 7.1% under Rp 50.
Restricting to Rp 500 or more: n=348, ρ = +0.042, t = +0.78: still
**not significant**, same conclusion as before. ρ(price, free_float) =
−0.270 (was −0.237). This plausibly overlaps the liquidity finding above
rather than being independent evidence: though "the liquidity finding"
above has itself now been resolved as a coverage-gap artifact (see the
2026-09-10 correction), so this overlap claim is weaker than when first
written: cheap stocks and thinly-traded stocks may still tend to be the
same obscure small companies, but "thinly-traded" is no longer shown to
matter for the *main* effect the way it appeared to.

### What this means, in one sentence

~~**Among small Indonesian companies, the ones where a lot of stock is
publicly available are far more turbulent than the ones a founder or
family still tightly controls: which is the opposite of the common
warning that thinly-held stocks are the dangerous ones.**~~

⚠️ **Corrected 2026-09-10: the "among small companies" qualifier
overstates what the data now shows.** The size-control table above
found the effect significant in three of four size buckets, not
concentrated in the smallest one. Revised statement: **IDX stocks where
a lot of stock is publicly available tend to be more turbulent than
closely-held ones: the opposite of the common warning that thinly-held
stocks are the dangerous ones: and this holds across most company
sizes, not just small caps.** Still true and unchanged: this describes
2024–2026 specifically, not 2022–2023 (see the year-by-year correction
above).

### Why it might be true

A guess, not yet tested, and weakened by the size-control correction
above: the original mechanism guessed that a tightly-held company barely
trades because whoever owns most of it isn't selling, so its price barely
moves: while a widely-held company is one the public actually trades,
and that trading is what makes it choppy. That story was built to
explain a *small-cap-specific* pattern; now that the effect also shows
up among large caps (where "a founder holding most of the stock and
never selling" is a less obvious story: large IDX companies vary widely
in ownership structure), **this mechanism is no longer well-supported
and should be treated as withdrawn, not just unverified**, pending a
better explanation.

### Limits: read this before using the finding anywhere

- **This describes volatility, not money made or lost.** A stock can be
  wildly turbulent and still go up. Don't read "turbulent" as "bad."
- **Correlation, not cause.** We haven't shown *why*: the mechanism
  guess originally offered here has since been withdrawn (see "Why it
  might be true" above) and not replaced.
- **This is a contemporaneous association, not a prediction.** Free
  float is a single 2026 measurement with no history, so it cannot be
  used to predict a historical outcome (see the predictor-before-outcome
  rule in `docs/DATA.md`): it only describes stocks measured *at the
  same time* as their volatility. Never describe this finding as
  predictive.
- ~~**Undisclosed boundary condition, found late:** the effect fades as
  actual trading activity rises...~~ **Resolved 2026-09-10:** re-run on
  the corrected Yahoo cache, the effect does **not** fade with trading
  activity at any threshold tested (see the correction above): the
  original "fades" finding was itself a coverage-gap artifact of the old
  `spark` endpoint, not a real boundary condition. Superseded by the next
  bullet, which **is** a real, still-open boundary condition.
- **New boundary condition, found on the 2026-09-10 re-run and not yet
  explained: the effect holds 2024–2026 and is absent in 2022–2023**, on
  a fixed panel of the same 751 stocks throughout: not a sample-size or
  coverage artifact. **Any product use of this finding should account
  for this being a recent-period pattern, not a five-year constant**,
  until a mechanism is found or ruled out.
- **The "small-cap-specific" framing is retracted, not merely
  qualified.** The 2026-09-10 size-control re-run found the effect
  significant in 3 of 4 size buckets (smallest, small-mid, largest),
  weakest in mid-large. **Any product feature that gates this finding on
  company size (e.g. "does not apply to large-caps like BBCA") is now
  built on a claim this data no longer supports** and needs updating
  before it ships: tracked in `BACKLOG.md`.
- **Exploratory, not confirmatory.** Tested on all the data at once, no
  formal train/test split. Its previously-claimed strength ("holds up
  across five separate years") no longer holds: see the year-by-year
  boundary condition above. H2 onward (and H5, which already does) uses
  a proper holdout, per `RULES.md`.
- **Gorengan tension, partially reframed rather than resolved.** The
  literature treats *low* free float as the danger signal; our result
  says the opposite. ~~The corrected liquidity check suggests the two may
  not be in as much tension as first thought...~~ That specific liquidity
  argument no longer applies now that the liquidity boundary condition
  itself was found to be an artifact (see above): the tension is
  unresolved and, if anything, less explained than before.
- **The regulatory story runs on the opposite theory, and this is a
  genuinely separate tension from the one above.** Indonesian regulators
  have kept the *minimum* free-float requirement low (~7.5%) for years and
  are now raising it to 15% specifically because *low* float is treated as
  a market-health risk (Glass Lewis, 11 Feb 2026: see `docs/SOURCES.md`
  §1). H1 found small-cap volatility rising with *higher*, not lower,
  float. Both can be true at once: regulators may be responding to a
  different failure mode (concentrated ownership enabling manipulation)
  than the one H1 measured (public trading activity itself producing
  turbulence): but nothing in this project's data adjudicates that.
  Stated as an open tension, not resolved either way.
- **Two known bugs in the shared statistics library were fixed after
  this was first run** (`pipeline/stats.py`, tied-rank averaging and a
  quintile-bucket sizing bug). The headline ρ moved from +0.225 to
  +0.224 (2026-09-07) then, on the corrected Yahoo cache, to +0.177
  (2026-09-10): this second move is the endpoint fix, not a further
  statistics-library bug.
- **Trial count: 1.** This is the first hypothesis tested. Any claim
  made from this finding should say so, the same way Argus (the
  previous project) always quoted its Deflated Sharpe Ratio together
  with how many things had been tried. Re-running on corrected data is
  not a new trial (same hypothesis, same method: only the underlying
  price series changed), matching how the `stats.py` tie-fix was handled.

### What this opens up

- A real finding, but its two live boundary conditions (2024–2026 only;
  no longer cleanly small-cap-specific) need to be attached before it
  goes anywhere near the product: the unqualified "small caps are more
  volatile when widely held" version is no longer defensible on this
  data.
- The Yahoo endpoint fix (2026-09-10) resolved what the "trading
  activity" boundary condition actually was: a coverage-gap artifact,
  not thin trading or recent listing. `docs/PLAN.md` §8.3's Sectors
  price cross-check is still owed before this is fully closed, but the
  most urgent open question it was meant to answer has already been
  answered by the endpoint fix itself.
- H1b (below): does the *drawdown* relationship survive the same
  size-control test that volatility did? (Also re-run 2026-09-10; see
  its own corrections.)
- `pipeline/hypotheses/h1_stress.py` also ran a placebo test and a
  random split-half, both re-run 2026-09-10 on the corrected cache:
  ~~shuffled free float, ρ = +0.02: passed~~ → **shuffled free float,
  ρ = +0.019: still passes**, gate held; ~~split-half ρ +0.180/t +3.76
  and ρ +0.267/t +5.72~~ → **split-half ρ +0.170/t +3.68 and ρ
  +0.179/t +3.87**: both halves still positive and significant, so the
  direction still isn't an artifact of one arbitrary half of the sample.

### Robustness stress tests (2026-09-20): sector, bootstrap, bucketing

`pipeline/hypotheses/h1_robustness.py` (0 credits, owned data, seeded,
~10 s). Stress tests of an existing finding, so **no new trials** (trial
counter unchanged); interpretations were fixed in the module docstring
before running. Reproduces the baseline exactly (n=913, ρ +0.177, t +5.42).

**1. Leave-one-sector-out: not sector-driven.** Excluding each of the 11
sectors in turn leaves ρ between +0.161 (Financials excluded) and +0.213
(Consumer Cyclicals excluded), t between +4.56 and +6.00. Excluding
property, mining (Basic Materials, Energy) and Financials together
(n=527): ρ +0.165, t +3.82. Pre-registered verdict: robust to sector.
Descriptive, not a claim: alone, the effect is never negative; ten
sectors are positive and Consumer Cyclicals is ≈0 (n=149, ρ +0.001),
which is why dropping it raises the pooled ρ. Eight of 11 single sectors
are not individually significant (only Consumer Non-Cyclicals,
Financials and Industrials clear |t|>2), which at n=37–149 is a power limit, not
evidence against the effect. 11 looks, no multiple-comparison correction.
Do not read the sector ordering as "strongest in X".

**2. Bootstrap 95% intervals (2,000 resamples).** Smallest-cap bucket
(n=229): ρ +0.215, stock-level [+0.077, +0.349], sector-cluster
[+0.077, +0.403]. Pooled: [+0.109, +0.241] / [+0.100, +0.249]. Largest:
[+0.037, +0.297] / [+0.025, +0.272]. **Small-mid: [+0.008, +0.269]
stock-level but [−0.004, +0.280] cluster: borderline.** Mid-large
includes zero on both. So "significant in 3 of 4 size buckets" holds
only at the stock level; allowing for sector clustering it is 2 of 4
clearly plus one borderline. Do not repeat the 3-of-4 wording in
product copy.

**3. Bucketing and threshold sensitivity: direction consistent, shape is
a step.** Terciles 52/69/69%, quartiles 53/55/73/70%, quintiles
54/53/69/69/73%, deciles 49/60/51/54/63/75/73/57/66/78% median volatility
(thinnest float first). High float has the higher median in every scheme,
but the relationship is not smooth: deciles rise in only 6 of 9 steps.
Thin-float cut: stocks below 5/10/15/20/25/30% free float have median
volatility 14–22 points lower than the rest at the 5–25% cuts and 10.6
at 30%, every 95% interval excludes zero (the <5% cut has n=13: [+4.4, +65.8],
too few to lean on).

**What this changes for the app.** Nothing in the direction of the H1
statement: it is not a property/mining/financials artifact and its
direction survives every cut. Wording constraints: keep "bersamaan
dengan", never "menyebabkan" or "memprediksi"; do not claim it holds
inside every size bucket or sector (Consumer Cyclicals shows nothing);
describe it as lower vs higher float groups, not a smooth gradient.
Still true from before: contemporaneous association, 2024–2026 only,
snapshot free float.

Not run here: the optional H5-excluding-Financials side-by-side.

---

## H1b: Does the float-drawdown relationship survive size control?

**Date:** 2026-09-06. **Re-run 2026-09-10** on the corrected Yahoo cache
alongside H1: see H1's entry above for what changed and why. Old
numbers struck through below, not silently replaced.
**Status:** Tested. ~~Confirmed: the drawdown relationship behaves like
the volatility one.~~ **Still not falsified, but the "small-cap-specific"
framing is retracted: see below**, matching H1's own 2026-09-10
correction. **Exploratory, not confirmatory**, and not an independent
trial: see Limits below.

### The hypothesis, written down before looking

H1's uncontrolled result already showed free float negatively correlated
with max drawdown (rho = ~~−0.185, t = −5.50~~ **−0.169, t = −5.17**):
wider-float stocks fell further from their peaks. H1's *volatility*
version of this pattern was originally reported as concentrated in small
companies and nearly vanishing among large ones: **that framing has
since been retracted (see H1's 2026-09-10 correction)**. H1b asks
whether the *drawdown* version follows the same (now-corrected) shape.

**This hypothesis would be falsified if:** the drawdown relationship
held roughly evenly across all four size buckets: i.e. if, unlike
volatility, it were *not* a small-cap-specific effect.

### How we tested it

Reused H1's exact dataset and per-stock measures (free float, market
cap, max drawdown over the same year): no new data, no new cost. Split
the ~~853~~ **913** stocks into four size buckets by market cap, then
re-ran the free-float-vs-drawdown correlation inside each bucket, the
same double-sort used for H1's volatility size-control check.

Full runnable code: `pipeline/hypotheses/h1b_float_drawdown_size.py`.
Run with `.venv/bin/python -m pipeline.hypotheses.h1b_float_drawdown_size`.

### What we found

~~The same pattern as volatility, and just as lopsided:

| Size bucket | rho(float, drawdown) | t | low-float mdd | high-float mdd |
|---|---|---|---|---|
| Smallest | **−0.356** | **−5.55** | −52.9% | −66.3% |
| Small-mid | −0.067 | −0.97 | −48.1% | −51.9% |
| Mid-large | −0.087 | −1.26 | −44.8% | −48.9% |
| Largest | −0.132 | −1.93 | −40.9% | −46.3% |

The uncontrolled figure (t = −5.50 across all 853 stocks) turns out to be
a diluted average: it's driven almost entirely by the smallest bucket...~~

⚠️ **Corrected 2026-09-10** (n=913, `pipeline/hypotheses/h1b_float_drawdown_size.py`):

| Size bucket | rho(float, drawdown) | t | low-float mdd | high-float mdd |
|---|---|---|---|---|
| Smallest | −0.188 | −2.89 | −51.8% | −59.8% |
| Small-mid | −0.163 | −2.48 | −47.9% | −55.7% |
| Mid-large | −0.084 | −1.26 (not significant) | −43.9% | −48.3% |
| Largest | **−0.196** | **−3.01** | −39.1% | −46.2% |

**Not falsified: but not small-cap-specific either.** The largest bucket
is now the single *strongest* result by t-statistic (−3.01), not the
weakest. Three of four buckets are significant; only mid-large isn't: 
the same "significant everywhere except the middle" shape H1's own
2026-09-10 correction found for volatility. The original "driven almost
entirely by the smallest bucket" reading does not survive correction.

### What this means, in one sentence

~~**Among small IDX companies, the ones with wide public ownership don't
just swing more, they also fall further from their peaks, while for
larger companies free float has little bearing on either.**~~

**Corrected 2026-09-10:** IDX stocks with wide public ownership tend to
fall further from their peaks than closely-held ones: across most
company sizes, not specifically small ones, matching H1's own corrected
volatility finding.

### Limits: read this before using the finding anywhere

- **Not an independent confirmation of H1: and closer to a restatement
  than a second data point.** `corr(volatility, max drawdown) =`
  ~~−0.792~~ **−0.822** (Spearman; ~~−0.775~~ **−0.82** Pearson) across
  the same ~~853~~ **913** stocks. A stock that swings more mechanically
  tends to fall further from its peak, so H1b finding "the same pattern"
  in drawdown is largely expected once H1's volatility result is known,
  not independent evidence for it.
- **Same exploratory status as H1**: no held-out period, all data looked
  at at once.
- ~~**Same undisclosed boundary condition as H1** (fades with actual
  trading activity...)~~ **Resolved 2026-09-10, same as H1**: does not
  fade with trading activity on the corrected cache (not separately
  re-run for drawdown specifically, but there's no reason to expect a
  different result given how closely volatility and drawdown move
  together: see the correlation above).
- **Same year-boundary condition as H1, not yet separately re-verified
  for drawdown**: H1's volatility effect holds 2024–2026 and is absent
  2022–2023. Not re-tested specifically for drawdown here, but given
  `corr(volatility, max drawdown) = −0.822`, there is no reason to expect
  it behaves differently: treat as inherited, not independently confirmed.
- **Same open, partially-reframed gorengan tension** as H1.
- **Trial count: 2** (H1, H1b). Both trials came from the same purchased
  dataset; this should be stated alongside either finding. The 2026-09-10
  re-run is a data correction, not a new trial: same reasoning as H1's.

### What this opens up

- ~~Strengthens the case that "free float" and "small-cap" need to
  combine...~~ **Superseded 2026-09-10**: the corrected data no longer
  supports gating this finding (or H1's) on company size at all: see
  both entries' 2026-09-10 corrections. What both findings now need
  before product use is an explanation for the 2024–2026-only pattern,
  not a size qualifier.
- The next genuinely new hypothesis (Phase 0, then whichever the
  register in `docs/PLAN.md` §6 prioritizes) uses fresh data rather than
  re-cutting what's already owned.

---

## H5: Do value and size factors predict returns on IDX?

**Date:** 2026-09-08. **Re-run 2026-09-10** on the corrected Yahoo price
cache (Chunk B) with one methodology addition: the return calculation now
uses `adjclose` (dividend-and-split-adjusted) instead of raw `close`: the
size proxy still uses raw `close` (see "How we tested it" below for why
that split matters). **This is a data/measurement correction, not a new
trial**: same hypothesis, same proxies, same formation lag, same year
split as the original 2026-09-08 run; only the underlying price series
(completeness + dividend-adjustment) changed. Same reasoning as `stats.py`'s
tied-rank fix and H1's 2026-09-10 re-run. Old numbers struck through below,
not deleted.
**Status:** Tested, with a real explore/holdout split. ~~Value: not
confirmed. Size: an unpredicted, significant result appeared in holdout~~ →
**Value: now confirmed in both phases (same direction, both significant).
Size: the unpredicted holdout lead persists, largely unchanged, and is now
*more* concentrated in a single year, not less.** See the corrected
inversion section below before reading either number as a headline.

### The hypothesis, written down before looking

Cheaper IDX stocks (higher earnings yield, i.e. lower P/E) and/or smaller
IDX stocks (smaller market cap) earn **higher** subsequent returns than
expensive/large stocks over the same window: the value and size premia,
well documented in developed markets, untested here.

**This hypothesis would be falsified if:** no monotonic relationship shows
up across quintiles in the holdout window, or it reverses.

### Holdout discipline (decided 2026-09-07/08, before any holdout number was looked at)

`pe[2021]` is **entirely absent** from the purchased universe: 0 of 962
companies, including BBCA: verified by reading
`data/raw/universe_2026-09-07.json` directly, not assumed from the field
list. That leaves 4 usable formation years: 2022–2025. Because the newest
pair (formed on 2025 data) can only be checked against a partial 2026: 
2026 isn't complete yet: **every** window, explore and holdout alike, uses
the identical **May 1 → Sep 4 of the following year** range, so exploration
tests exactly the method that runs in holdout, not a longer or cleaner
version of it.

Formation date is May 1, not Jan 1, to avoid looking ahead of when annual
figures were actually public: fiscal-year data isn't known the instant the
year ends. **This is an assumed ~4-month reporting lag, not verified against
IDX's actual disclosure deadline**: conservative in the safe direction
(later, not earlier), so it doesn't manufacture a false positive if wrong.

**Explore** (methodology allowed to change): formation 2022, 2023 → return
May–Sep 2023, 2024. **Holdout** (frozen, run once): formation 2024, 2025 →
return May–Sep 2025, 2026.

### How we tested it

1. **Value proxy:** `1 / pe[year]` (earnings yield), restricted to `pe > 0`: 
   negative P/E (loss-making companies) isn't a meaningful "cheapness"
   signal, so those rows are excluded from the value ranking entirely
   (shrinks n; not a neutral filter).
2. **Size proxy:** `outstanding_shares[year] × nearest Yahoo close at
   formation`. Sectors has no yearly `market_cap` field, so this is computed
   from data already purchased. Yahoo prices are dev-only, free, never ship
   (`RULES.md`): same status as H1's price data. **Uses raw `close`, not
   `adjclose`, deliberately**: `adjclose` retroactively lowers historical
   prices for dividends/splits that happen *after* the date being priced
   [verified 2026-09-10 against the cache: BBCA.JK's close/adjclose gap is
   14.65% on the oldest cached date, shrinking to 0% on the most recent].
   Using it for size would shrink the market-cap proxy specifically for
   stocks that later pay more dividends: correlated with the value leg
   this hypothesis tests: so it would bias the size proxy in a
   direction-specific way, not just add noise.
3. **Outcome:** return from that formation price to the nearest close on or
   near Sep 4 of the same year: **using `adjclose` (added 2026-09-10)**,
   because a return measure is supposed to capture total investment return,
   which dividends are part of by definition. This directly fixes the
   dividend-exclusion limitation named in the original write-up.
4. Spearman rank correlation, quintiles, and a value-vs-size confound check
: same `pipeline/stats.py` functions H1 uses, no new statistics code
   (the corrected run adds `stats.nearest_value`, a straightforward
   generalization of the date-matching logic already used, to read the new
   cache schema: see `docs/DATA.md`).

Full runnable code: `pipeline/hypotheses/h5_value_size.py`. Explore only:
`.venv/bin/python -m pipeline.hypotheses.h5_value_size`. With holdout
(touched once per the original 2026-09-08 run, reproduced byte-identical on
a second run then; **re-run once more 2026-09-10 as the data correction
described above, also reproduced byte-identical on a second run**):
`.venv/bin/python -m pipeline.hypotheses.h5_value_size --confirm-holdout`.

### What we found: explore phase

~~| Formation → outcome | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| 2022 → May-Sep 2023 | 512 | +0.137 | +3.13 | +0.051 | +1.14 |
| 2023 → May-Sep 2024 | 545 | +0.079 | +1.85 | −0.117 | −2.75 |
| **Pooled** | **1057** | **+0.105** | **+3.42** | **−0.037** | **−1.20** |~~

⚠️ **Corrected 2026-09-10:**

| Formation → outcome | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| 2022 → May-Sep 2023 | 570 | +0.203 | +4.94 | +0.089 | +2.14 |
| 2023 → May-Sep 2024 | 601 | +0.134 | +3.32 | −0.078 | −1.90 |
| **Pooled** | **1171** | **+0.166** | **+5.77** | **+0.002** | **+0.05** |

Value looks even more clearly real and in the predicted direction than
before (pooled t rose from +3.42 to +5.77). Size is, if anything, *more*
null than before: the pooled figure is now essentially zero (t=+0.05,
was −1.20), and the two years still disagree on sign. Value-vs-size
confound check: ρ≈+0.07–0.10 across both years: still weak, not a
meaningful overlap.

### What we found: holdout, re-touched once as a data correction

~~| Formation → outcome | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| 2024 → May-Sep 2025 | 568 | −0.027 | −0.65 | **−0.282** | **−7.00** |
| 2025 → May-Sep 2026 | 530 | +0.057 | +1.31 | −0.061 | −1.40 |
| **Pooled** | **1098** | **+0.037** | **+1.24** | **−0.193** | **−6.52** |~~

⚠️ **Corrected 2026-09-10: this is the headline change:**

| Formation → outcome | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| 2024 → May-Sep 2025 | 601 | +0.033 | +0.80 | **−0.292** | **−7.48** |
| 2025 → May-Sep 2026 | 547 | **+0.111** | **+2.61** | −0.022 | −0.51 |
| **Pooled** | **1148** | **+0.088** | **+2.99** | **−0.183** | **−6.31** |

### The inversion: corrected, and it now only applies to one leg

~~**Holdout produced the opposite pattern from what exploration predicted.**
The leg that looked promising in exploration (value)... The leg that looked
null in exploration (size)... came back strongly significant in holdout~~

**Corrected 2026-09-10: the inversion no longer describes the value leg.**
On the corrected data, **value is positive and significant in both
explore (t=+5.77) and holdout (t=+2.99)**: the same direction throughout,
which is what a real effect is supposed to look like. Including dividends
(via `adjclose`) directly fixed the null result: the original write-up's
own speculation: *"the null on value may be partly a measurement artifact
rather than proof the effect doesn't exist"*: turned out to be correct.
Within the corrected holdout, one year clears significance on its own
(2025→2026, t=+2.61); the other (2024→2025, t=+0.80) doesn't individually,
but is still positive, not a sign disagreement.

**The size leg's inversion is unchanged, and its "one-year" problem is
now worse, not better.** Size is still null-to-mixed in explore (t=+2.14
and −1.90, opposite signs) and still strongly negative in holdout
(pooled t=−6.31, barely different from before). But the split between
holdout years moved in the wrong direction for confidence: 2024→2025 got
*more* extreme (t=−7.00 → −7.48) while 2025→2026 got *weaker*
(t=−1.40 → −0.51, now barely different from zero). **A single year
(2024→2025) is doing even more of the work than in the original write-up**
: the opposite of what more/better data would ideally show for a robust
effect.

This is exactly the pattern a real holdout exists to catch, but the two
legs now tell different stories: reporting "IDX has a value effect" using
the corrected numbers is now defensible (same sign, significant, in both
phases). Reporting "IDX has a size effect" is not: it remains a
**single-year-driven, unpredicted lead**, not a confirmed finding, and the
correction made that concern sharper rather than resolving it.

### What this means, in one sentence

~~**No confirmed value effect on IDX in this test; an unpredicted size
effect showed up in the untouched holdout data and needs its own
independent confirmation before it means anything for the product.**~~

**Corrected 2026-09-10: cheaper IDX stocks (by earnings yield) earned
higher subsequent returns in both the explore and holdout windows, once
dividends are counted: a real, if modest, value effect. The size
result is unchanged: still an unpredicted, single-year-driven holdout
lead that needs independent confirmation before it means anything for
the product.**

### Limits: read this before using either result anywhere

- **`pe[2021]` gap limits this to 4 formation years total**, split 2-and-2: 
  a thin base for any holdout, and the reason a single year (2024) can drive
  most of a pooled result (see below).
- **The 4-month reporting-lag formation date is assumed, not verified**
  against IDX's actual annual-report deadline.
- **The `pe > 0` filter removes loss-making companies from the value test
  entirely**: the value result describes profitable companies only.
- ~~**Size-correlated data dropout...** companies missing from the Yahoo
  dev cache, or too far from the target dates, are dropped from the test: 
  and the dropped companies skew smaller in three of four years (median
  market cap of kept vs. dropped rows: 2022 2.24T vs 0.52T; 2023 2.09T vs
  0.71T; 2025 2.21T vs 1.29T)...~~ **Substantially resolved 2026-09-10** by
  the Yahoo endpoint fix (Chunk B): dropout counts collapsed from the
  dozens/hundreds implied above to single digits in three of four years.
  Re-measured directly (eligible pool = `pe>0, shares>0`; kept = also has
  usable price data within 10 days of both formation and outcome dates):

  | Year | eligible | kept | dropped | kept median mcap | dropped median mcap |
  |---|---|---|---|---|---|
  | 2022 | 574 | 570 | 4 | 2.02T | 2.16T |
  | 2023 | 604 | 601 | 3 | 1.95T | 0.18T (n=3, noisy) |
  | 2024 | 603 | 601 | 2 | 1.98T | 2.16T |
  | 2025 | 571 | 547 | 24 | 2.15T | 1.23T |

  No year shows the dropout skew the original write-up flagged as tainting
  the pooled figure: dropout is now small enough in absolute count (2-24
  companies) that it can no longer meaningfully bias any of the four years.
  **"Substantially resolved," not "resolved outright"**: 2025 still drops
  24 companies skewed somewhat smaller, and this fixes the *dev-cache* data
  only; `docs/PLAN.md` §8.3's Sectors-price cross-check obligation is
  unchanged by this fix.
- ~~**The return measure excludes dividends...**~~ **Resolved 2026-09-10**
: the return calculation now uses `adjclose`, which includes dividends
  and splits. This was the original write-up's own top candidate
  explanation for the value null, and fixing it changed the result exactly
  as speculated: value is now significant in both explore and holdout.
- **New limitation, found while fixing the schema, not previously
  disclosed: the effective outcome-window length varies by stock, by up
  to ~20 days (~15% of the ~127-day window), and this isn't new to the
  2026-09-10 correction: it was already true of the original code, just
  not previously named.** Both the formation-date and outcome-date price
  lookups independently tolerate up to 10 days' gap, so a stock with
  perfect data gets the full May 1 → Sep 4 window while a more illiquid
  one could get anywhere from ~107 to ~147 days, depending on which side
  of each 10-day tolerance its nearest trades fall on. Since illiquidity
  correlates with company size, this is a real confound specifically for
  the size leg: not fixed here, because changing it would be a
  methodology change to an already-frozen, once-run holdout, which this
  project's own anti-p-hacking discipline forbids mid-flight. Flagged for
  whoever next revises H5's methodology from scratch (e.g. the H5
  follow-up in `BACKLOG.md`), not fixed as part of this data correction.
- **Single-regime risk on the holdout itself: worse after correction, not
  better:** only two years (2024, 2025) make up the entire holdout, and one
  of them (2024) drives nearly the whole size result. ~~2024 t=−7.00~~ →
  **corrected 2024 t=−7.48, while 2025 weakened from t=−1.40 to t=−0.51**: 
  the split between years is now more lopsided than in the original
  write-up, not less. The same "is this just one period" concern already
  flagged for H1's year-by-year check, here with even less data to average
  over.
- **New, verified 2026-09-10: H5's sample includes all 107 IDX "Financials"
  sector companies (98 of which actually appear in the test at some point,
  12.7% of the 770 unique symbols tested).** Fama & French (1992) explicitly
  exclude financial firms from cross-sectional return studies, on the stated
  grounds that "the high leverage that is normal for these firms probably
  does not have the same meaning as for nonfinancial firms, where high
  leverage more likely indicates distress" (`docs/SOURCES.md`). P/E and
  leverage may not carry the same meaning for banks and insurers as for the
  rest of the sample, so both the value and size results here are diluted
  by ~13% of the sample the foundational factor-investing literature would
  have excluded. Not re-run without financials: that would be a
  methodology change to a frozen holdout, tracked instead as a candidate
  follow-up in `BACKLOG.md`.
- **External literature runs opposite to what we found, and a specific,
  checked explanation, not just a general tension, accounts for it.**
  The general pattern in emerging-market factor research is that *value*
  survives real trading costs while the *size* premium is fragile to them
: in one 11-market study, size returns were "obliterated" by liquidity
  constraints while value was "the only premium left standing" (Zaremba &
  Konieczka 2015, via The Evidence-Based Investor, Feb 2025: see
  `docs/SOURCES.md` §3). H5 found the reverse: value did not confirm,
  size did. Two checks done against our own data, not just literature
  comparison:
  - **Checked and ruled out:** the specific small-cap names in a
    widely-reported December 2025 single-day rally (IPOL, NATO, TRUE,
    TRON: Jakarta Globe, 4 Dec 2025) do not explain the holdout result.
    IPOL and TRON sat in the second size quintile, not the smallest; NATO
    in the third; TRUE wasn't in the eligible sample at all; and TRON's
    actual measured return in H5's own May–Sep 2025 window was **−28%**
    (a reversal, not the reported surge, which in any case happened three
    months after that window closed).
  - **Best-supported explanation found (not proven):** Bank Indonesia cut
    its benchmark rate three times in 2025: 15 Jan, **21 May**, and
    15–16 Jul, −25bp each: with the May cut landing right at the start
    of the 2024-formation holdout's outcome window (May–Sep 2025). This
    matches a documented general mechanism (small/thin names
    disproportionately rallying on falling rates, as seen internationally
    in the 2025 Russell 2000 rally) and fits the shape of the actual
    result: a broad, roughly monotonic staircase across all five size
    quintiles, not a few outliers. The explore years (2022–2023) had no
    comparable rate-cutting cycle, consistent with exploration never
    predicting this. No direct causal test was possible with only 4 years
    of data: this is a well-supported explanation, not a proven one.
  - **Read together: corrected 2026-09-10:** the size result still looks
    like a real but regime-specific rate-cut rotation, not a persistent IDX
    size premium. ~~which is also consistent with the general literature
    above, even though H5's specific pattern (size significant, value not)
    inverts which leg looked fragile~~: **that inversion is now gone**:
    with dividends included, H5's pattern (value significant and durable,
    size significant but fragile across years) now matches the general
    literature's shape directly, not just its themes. Read plainly: this
    correction made H5's results *more* consistent with the outside
    literature, not less.
- **Size's significance cannot yet be told apart from a one-period fluke: 
  if anything more true after correction**, given the widened gap between
  the two holdout years' individual t-statistics above. Ruling that out
  needs a genuinely new, independent year of data, which doesn't exist
  yet: re-testing on the same four years would violate the exact
  explore/holdout discipline that surfaced this lead in the first place.
- **Dev-only price data, same status as H1:** every number here comes from
  Yahoo, never shipped, and owes the same Sectors price cross-check already
  tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3) before any of this reaches
  the product.
- **The outcome-window-length limitation above (up to ~20 days'
  variability between stocks) applies to both legs but is a specific
  concern for size**, since illiquidity (which drives which stocks get a
  shorter or longer effective window) correlates with company size.
- **Trial count: 3** (H1, H1b, H5): unchanged. The 2026-09-10 re-run is a
  data correction, not a new trial (same hypothesis, proxies, lag, and year
  split: only the price series changed), per this file's own convention
  for exactly this situation.

### Stress tests (2026-09-11): the checks H1 got that H5 never had

H1 has a dedicated stress-test module (`pipeline/hypotheses/h1_stress.py`:
a placebo test and a random split-half). H5 only ever had its
explore/holdout split and a value-vs-size confound check: a real gap,
now closed by `pipeline/hypotheses/h5_stress.py`.

**Design note, important for reading the results correctly:** pooling all
4 formation years gives a stock up to 4 rows (one per year): repeated
observations of the same company, not independent draws. Two
independent review passes caught that testing on that raw pooled sample
(n=2319) would make a split-half test's two "halves" not actually
independent (a company's own persistent traits can land in both halves
via different years) and would inflate the placebo test's significance.
**Fixed by collapsing to one row per symbol** (averaging
earnings_yield/size/return across whichever years a symbol has) before
either test: 2319 pooled rows collapse to **770 distinct symbols**.

**Test 1: placebo** (shuffle earnings_yield, separately shuffle size;
each against real returns; hard gate at |ρ| < 0.1):

| Shuffled | ρ | t | Gate |
|---|---|---|---|
| earnings_yield | −0.0008 | −0.02 | **PASS** |
| size | +0.0170 | +0.47 | **PASS** |

Both collapse to ~0 as required. The statistical pipeline is not
manufacturing correlation from noise.

**Test 2: random split-half** (770 symbols → 385/385, independent by
construction since each symbol appears in only one half):

| | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| Half A | 385 | +0.159 | +3.15 | −0.104 | −2.04 |
| Half B | 385 | +0.110 | +2.17 | −0.080 | −1.56 |

**Value:** both halves positive and significant: corroborates the
already-confirmed explore/holdout result on a genuinely independent
split of companies, not just of years.
**Size:** both halves negative, one significant (t=−2.04) and one
borderline (t=−1.56, just under the usual 1.96 threshold): more
consistent under a random split than the year-by-year breakdown alone
might suggest. **This does not resolve the size leg's core concern.** A
random split mixes years together, so it cannot detect (or rule out) a
result that depends on *which year* a row comes from: that's a
different question, already answered separately by the year-by-year
table further up (2024→2025 t=−7.48 vs. 2025→2026 t=−0.51). Read
together: size is reasonably stable across *which companies* you sample,
but still concentrated in *which year* you sample: two distinct and not
mutually resolving robustness questions.

### What this opens up

- **The explore/holdout split worked as intended, in both directions.**
  On the original (uncorrected) data it flagged a size pattern as needing
  confirmation rather than letting one untouched-data run count as proof: 
  and on the corrected data, it let a real value effect (present in *both*
  phases) be told apart from a one-phase fluke, which single-phase testing
  never could have done either way.
- ~~The size lead is not actionable until it's tested against data this
  project hasn't seen yet... or once the Sectors price cross-check (owed
  anyway) replaces the Yahoo dev cache and removes the coverage-gap and
  dividend-exclusion caveats above.~~ **Partially superseded 2026-09-10:**
  the coverage-gap and dividend-exclusion caveats are now resolved (Chunk
  B/D). The size lead is still not actionable, for the same reason as
  before: it needs a genuinely new, independent formation year, which
  doesn't exist yet regardless of data quality.
- ~~A dividend-inclusive return measure would directly address the value
  leg's biggest named limitation and might change its outcome...~~ **Done,
  2026-09-10: and it did change the outcome, in exactly the direction
  speculated.** The next open question for the value leg is the
  Financials-exclusion limitation above, not dividends.
- **New from this correction:** the outcome-window-length variability
  limitation (up to ~20 days between stocks) was not previously named and
  is now the most-recently-found open methodological question for H5,
  parallel to how H1's boundary conditions kept surfacing on re-verification
  rather than all being found in the first pass.

### Timing-precision diagnostic (2026-09-12): is the confirmed year's effect concentrated around the rate cut?

**Not a new trial, not a fix for the "confirmed in only one year" weakness
: a diagnostic on an already-observed result**, run once
(`pipeline/hypotheses/h5_timing_diagnostic.py`). Verified first, before
running anything: there is **no way to add a genuinely new, independent
formation year before the 2026-09-30 freeze**: `pe[2021]` is confirmed
absent from every field capable of reconstructing it (checked every
equity/book-value/earnings-related field in the owned schema; none
exist), and the next new year (formation 2026) needs `pe[2026]`, not
public until well after the freeze. This diagnostic cannot change that;
it can only test whether the one confirmed year's effect is internally
consistent with the rate-cut explanation already on record.

**What was tested:** the 2024-formation holdout window (return 1 May – 4
Sep 2025, size ρ=−0.292/t=−7.48) was split at **21 May 2025**: the
middle of the three 2025 BI rate cuts, and the first one to fall inside
this window (15 Jan is before the window opens): into a pre-cut and
post-cut sub-period, using the same `adjclose`/`nearest_value` machinery
`h5_value_size.py` already uses on the same cache.

| Sub-period | n | size ρ | size t |
|---|---|---|---|
| Full window (reference, matches the table above) | 601 | −0.292 | −7.48 |
| Pre-cut (1 May → 21 May 2025) | 601 | −0.059 | −1.45 |
| Post-cut (21 May → 4 Sep 2025) | 601 | −0.294 | −7.52 |

**Reading this plainly:** the pre-cut sub-period shows essentially no
size effect (t=−1.45, not significant at the usual threshold); the
post-cut sub-period alone reproduces almost the entire full-window
effect (t=−7.52, actually marginally stronger than the full window). The
size quintile medians tell the same story: the smallest-quintile median
return is +5.0% pre-cut vs. +27.6% post-cut, while the largest quintile
barely moves either half (+3.9% vs. +1.1%).

**What this does and does not mean:**
- **Consistent with, not proof of, the rate-cut explanation already on
  record.** The effect concentrating in the sub-period that starts at the
  rate cut is exactly what that explanation would predict, and this is a
  closer, more specific check than the whole-window correlation could
  offer on its own.
- **Does NOT resolve the size leg's core weakness.** This is a split of
  the *same single window* that already drives nearly the entire size
  result: it cannot substitute for an independent year, and doesn't
  attempt to. A single window split two ways, along a dimension (calendar
  time within one year) that was never itself pre-registered as a
  predictor, is a low-power, after-the-fact check: informative about
  internal consistency, not new evidence of the effect's existence or
  durability.
- **Product decision unchanged:** size stays scoreboard-only, not shipped
  as a feature, regardless of this result.

---

## H14: Do retail's own technical indicators (RSI, 200-day MA, momentum) predict returns on IDX?

**Date:** 2026-09-12. **Status:** Tested, explore + holdout, with a real
holdout confirmation run. **All three indicators come back null**: no
sign-consistent, significant relationship survives from explore into
holdout for any of them. Reported in full per this file's own rule (item
6: ship the null if it's null), not filed away quietly.

### The hypothesis, written down before looking

1. RSI(14) < 30 ("oversold") predicts a bounce (positive forward return);
   RSI(14) > 70 ("overbought") predicts a pullback (negative forward
   return).
2. Price above its 200-day moving average (an uptrend) predicts
   continuation; below predicts further weakness (trend-following).
3. 60-trading-day trailing momentum predicts the next window's return: 
   the sign of the correlation answers both competing beliefs at once
   (positive = continuation, negative = mean-reversion).

**Falsified (per indicator) if:** the correlation is not significant, or
does not survive from explore into holdout in the same direction.

### Holdout discipline

Cost: **$0**: uses only the owned Yahoo 5-year dev cache, no Sectors
call, and (unlike H1/H5) no snapshot field either, so the usual
predictor-before-outcome risk doesn't apply: every indicator is computed
strictly from `close` values up to the signal date, forward return
measured strictly after it, by construction. Explore/holdout split by
calendar year of the signal date, same boundary H5 uses for consistency:
explore = 2021–2023 signal dates, holdout = 2024–2026.

**Sampling design: avoiding the pseudo-replication bug found and fixed
in H5's stress test this session, before it could recur:** one signal
date per stock roughly every 20 trading days (~1 month), with a
20-trading-day forward-return horizon, so consecutive sample windows for
the same stock are back-to-back rather than overlapping. Uses `close`
(raw price), not `adjclose`: same reasoning as H1: a technical signal is
about the chart a trader actually watches, not a dividend-adjusted series.

Full runnable code: `pipeline/hypotheses/h14_technical_indicators.py`.
Explore only: `.venv/bin/python -m pipeline.hypotheses.h14_technical_indicators`.
With holdout (touched once, this run): `... --confirm-holdout`.

### What we found

| Indicator | Explore ρ | Explore t | Holdout ρ | Holdout t | Sign-consistent? |
|---|---|---|---|---|---|
| RSI(14) vs next-20-day return | −0.056 | −6.56 | +0.021 | +3.41 | **No: flips** |
| price-vs-200d-MA vs next-20-day return | +0.006 | +0.75 | −0.042 | −6.94 | **No: explore null, holdout flips negative** |
| 60-day momentum vs next-20-day return | +0.006 | +0.68 | −0.012 | −2.00 | **No: explore null, holdout weakly negative** |

n=13,937 explore sample points (887 symbols pooled), n=26,701 holdout
sample points.

**Base rates** (the form retail actually uses these in):

| Signal | Explore: up next 20d | Holdout: up next 20d | Baseline (same phase) |
|---|---|---|---|
| RSI < 30 ("oversold") | 38.7% (n=1,195) | 36.7% (n=1,907) | 36.7% / 41.7% |
| RSI > 70 ("overbought") | 38.1% (n=614) | 43.6% (n=1,807) | 36.7% / 41.7% |
| Price above 200d MA | 41.1% (n=4,478) | 42.7% (n=11,442) | 36.7% / 41.7% |
| Price below 200d MA | 34.7% (n=9,459) | 40.9% (n=15,259) | 36.7% / 41.7% |

Reading this plainly: in explore, "oversold" and "overbought" both beat
their own baseline by a similar amount: no differentiation between the
two supposedly opposite signals, which is itself evidence against the
belief. In holdout, "overbought" (43.6%) actually beat "oversold"
(36.7%): the *opposite* of what the bounce/pullback belief predicts.
None of this is a stable pattern; it moves around between phases in ways
that look like noise, not signal.

### What it means in plain language

**None of the three most common retail technical indicators predicted
IDX returns in a way that held up.** RSI showed a real, significant
relationship in explore: but it flipped sign in holdout, which is
exactly the outcome an honest holdout test exists to catch (a purely
in-sample pattern that doesn't generalize). The 200-day moving average
and momentum signals were statistically indistinguishable from zero in
explore and only picked up a weak, opposite-of-expected signal in
holdout. **A user following any of these three signals on IDX would not
have had a real edge over the base rate.**

### Why it came out this way (inferred, not verified)

Not independently investigated this session: noted as a plausible,
unverified explanation rather than left blank: retail technical
indicators are backward-looking, price-only heuristics with no
theoretical link to a specific market's fundamentals; their most common
empirical support comes from developed, highly liquid markets with
different microstructure (tick size, participation mix) than IDX, where
H1 already found free float and liquidity effects on volatility that
don't hold universally. A genuinely thin/illiquid market could plausibly
break the assumptions (continuous, efficiently-arbitraged price
discovery) these indicators are built on: but this is speculation, not
a tested explanation, and is not claimed as one.

### Limits

- **This module cannot rule out a shorter or longer horizon working
  where the 20-trading-day one tested here didn't**: a genuinely
  different pre-registered horizon would be a new trial, not a re-run of
  this one.
- **Sample points from the same stock across nearby months are not
  fully independent draws**, even with the ~20-day spacing designed to
  remove the dominant mechanical overlap (see the module docstring): no
  claim of full independence is made; this is a real, acknowledged
  limitation shared with every panel-style test in this project.
- **Dev-only price data, same status as H1/H5:** every number here comes
  from Yahoo, never shipped, and owes the same Sectors price cross-check
  already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 6** (H1, H1b, H5, plus 3 new: RSI, MA, momentum): each
  of the three indicators is one pre-registered trial (explore phase
  doesn't count separately, matching how H5's explore phase is treated).

### What it opens up

- **This is exactly the content the honesty scoreboard exists for**: 
  "RSI/moving-average/momentum: no link found on IDX" is a plain,
  directly usable sentence for a user about to trust a chart signal, and
  no competitor product publishes anything like it.
- **Chunk P's remaining method upgrades** (future-shifted-timestamp
  placebo, Monte Carlo permutation) could be applied here as a further
  robustness check, but given all three indicators already failed the
  much simpler explore→holdout sign-consistency bar, that additional
  work is low-priority against other queued items.

---

## H15: Do technical × fundamental factor combinations predict returns on IDX better than either factor alone?

**Date:** 2026-09-12. **Status:** Tested, explore + holdout, with a real
holdout confirmation run. **All three pre-registered interactions come
back null**: no combination clears both the usual and the stricter
multiple-comparisons bar with sign agreement between explore and
holdout. Reported in full per this file's own rule (item 6: ship the
null if it's null).

### Why this hypothesis exists, and what it deliberately is NOT

H14 tested RSI, 200-day-MA position, and momentum standalone and found
all three null: and literature search confirmed IDX-specific research
on these three already exists and disagrees with itself, so re-testing
them one at a time adds little. The more original question: does
**combining** a technical signal with a fundamental one predict anything
neither predicts alone: something no retail screener tests, since they
only ever show factors in isolation.

**Not a composite score.** `CLAUDE.md`'s hard constraint: *"No score or
combined verdict across findings"*: governs anything this project
ships; a weighted/blended signal is exactly what it forbids. This is
also the statistically sounder choice independent of that rule: a fitted
multi-factor model has many tunable parameters against a holdout of only
~600-1,200 rows: the same setup that produced H5's size leg, a result
that looked real until it needed to survive out-of-sample. Chosen
instead: **3 pre-registered, theory-justified interaction tests**, the
same low-free-parameter design that already worked for H1 and H5. If any
interaction had survived, it would have become its own finding card with
its own limits: never a "buy/sell algorithm."

### Pre-registered interactions (written before looking at results)

1. **Cheap (top-tercile earnings_yield, `pe>0` only) × oversold
   (RSI(14) < 30).** Why expect one: a temporarily oversold cheap stock
   is a different situation from an oversold expensive one: value
   provides a floor an overbought/expensive stock lacks.
2. **Quality (top-tercile ROE) × uptrend (price above its 200-day MA at
   formation).** Why expect one: trend-confirmation: good fundamentals
   the market hasn't priced in should show sustained price strength.
3. **High leverage (top-tercile debt-to-equity) × downtrend (price at or
   below its 200-day MA).** Why expect one: risk-confirmation: leverage
   is dangerous specifically when a company is also losing price support.

**Falsified (per interaction) if:** the combination's mean return
doesn't differ from EITHER single-factor-alone group (Welch's t-test,
|t| < ~1.96) in holdout, or if it does but disagrees in sign with the
theory above or with explore.

### How we tested it

Same yearly-field-with-formation-lag pattern as `h5_value_size.py`
(`pe[year]`/`roe[year]`/`debt_to_equity_ratio[year]`, read no earlier
than May 1 of `year+1`), same `adjclose` return field, same May 1 → Sep 4
window, same `EXPLORE_YEARS`/`HOLDOUT_YEARS` boundary (imported directly
from `h5_value_size.py`, so it can't silently drift). Technical side uses
`pipeline/stats.py`'s `rsi()`/`moving_average()` on raw `close`
(technical signals are about the chart a trader watches, same reasoning
as H1/H14), evaluated at the exact formation date via `nearest_index`
(new in `stats.py` this session). **One row per (symbol, formation
year)**, not H14's dense monthly sampling: the fundamental side only
changes once a year, so resampling technical signals monthly around a
fixed yearly fundamental value would add rows without adding independent
information. Terciles for the "top tercile" factors are computed
**separately within each phase's own pooled sample**: explore terciles
never see holdout rows, or vice versa.

Full runnable code:
`pipeline/hypotheses/h15_technical_fundamental_interactions.py`. Explore
only: `.venv/bin/python -m pipeline.hypotheses.h15_technical_fundamental_interactions`.
With holdout (touched once, this run): `... --confirm-holdout`.

### What we found

| Interaction | Phase | n (combo / A-only / B-only) | combo vs A-only | combo vs B-only |
|---|---|---|---|---|
| Cheap × oversold | Explore | 37 / 338 / 81 | diff −10.5%, t **−1.58** | diff −8.0%, t **−1.22** |
| Cheap × oversold | Holdout | 13 / 397 / 27 | diff +8.3%, t **+0.48** | diff +18.6%, t **+0.94** |
| Quality × uptrend | Explore | 184 / 323 / 203 | diff +1.5%, t **+0.49** | diff −13.7%, t **−1.20** |
| Quality × uptrend | Holdout | 233 / 325 / 470 | diff +9.7%, t **+2.50** | diff −14.7%, t **−2.33** |
| High leverage × downtrend | Explore | 377 / 132 / 761 | diff +2.9%, t **+0.83** | diff −0.6%, t **−0.23** |
| High leverage × downtrend | Holdout | 331 / 227 / 640 | diff −11.8%, t **−1.49** | diff −4.4%, t **−1.08** |

**Reading this plainly:**
- **Interaction 1 (cheap × oversold):** null in both phases, and the sign
  even flips between them (explore: combo underperforms cheap-alone;
  holdout: combo outperforms). No signal, no direction.
- **Interaction 2 (quality × uptrend): the one case that looks
  interesting, and why it still doesn't survive:** holdout shows the
  combo beating quality-alone (t=+2.50, clears the usual 1.96 bar) but
  *losing* to uptrend-alone (t=−2.33): the standout performer in
  holdout was **uptrend by itself** (+34.8% mean), not the combination.
  Neither comparison clears the stricter Bonferroni-style bar this
  module's own output states (~2.6 for 6 simultaneous tests), and explore
  showed neither comparison anywhere near significant (t=+0.49, −1.20)
: no sign-agreement between phases. Falsified by this hypothesis's own
  pre-registered criteria.
- **Interaction 3 (high leverage × downtrend):** null in both phases.

**None of the three pre-registered combinations added anything beyond
what a single factor already captured.** This is a comprehensive null,
not a partial one: every one of the 6 holdout comparisons either misses
the loose bar, misses the stricter bar, or (interaction 2) actually shows
a single factor alone outperforming the combination.

### Comparison against H1 and H5 (the question this hypothesis exists to answer): plain numbers, side by side, never combined

| Finding | Type | Explore/main ρ (t) | Holdout ρ (t) |
|---|---|---|---|
| **H1**: free float vs volatility | Single factor | (exploratory only, no holdout split) | ρ=+0.177, t=+5.42 (n=913) |
| **H5 value**: earnings yield vs return | Single factor | ρ=+0.166, t=+5.77 (n=1171) | ρ=+0.088, t=+2.99 (n=1148) |
| **H5 size**: market cap vs return | Single factor | ρ=+0.002, t=+0.05 (n=1171) | ρ=−0.183, t=−6.31 (n=1148): single-year-driven, unconfirmed |
| **H15**: best-surviving interaction | Combination | none clear the pre-registered bar | none clear the pre-registered bar |

**Answering the user's question directly:** combining technical and
fundamental factors, at least for these 3 theory-motivated pairs, does
**not** produce a stronger or more reliable signal than the single-factor
findings this project already has. H1's free-float result and H5's value
result, both single factors, remain the strongest evidence-backed
results in the project. This is a real answer, not a non-answer: it
means the "combination adds value" intuition, plausible on its face,
doesn't hold for these three specific combinations on this data.

### Limits

- **Only 3 combinations were tested: this is not a claim that NO
  technical×fundamental combination works on IDX**, only that these
  three theory-motivated ones don't. A different pairing (not
  pre-registered here) remains untested, and testing it now would be a
  new trial, not a re-run of this one.
- **Interaction 1's sample is restricted to profitable companies
  (`pe>0`)**: same limitation H5's value leg already carries, inherited
  here, not introduced by this module.
- **Small holdout cells for interaction 1** (`cheap AND oversold`,
  n=13): a t-test on 13 observations is very low-powered; the null
  result there is weak evidence of absence, not strong evidence.
- **No p-value/FDR correction machinery exists in this project** (no
  scipy dependency): t-statistics are reported against the same ~1.96
  asymptotic-normal threshold every other hypothesis module here uses,
  with an explicit stricter Bonferroni-style note (~2.6 for 6
  simultaneous holdout tests) rather than a computed p-value.
- **Dev-only price data, same status as H1/H5/H14:** every number here
  comes from Yahoo, never shipped, and owes the same Sectors
  price cross-check already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 9** (H1, H1b, H5, H14's 3 indicators, plus H15's 3
  interactions): each interaction is one pre-registered trial (explore
  doesn't count separately, matching H5's own convention).

### What it opens up

- **Directly answers the question that motivated this hypothesis:**
  combining factors is not automatically better, at least not for
  arbitrary theory-plausible pairs: a genuinely useful, non-obvious
  finding for the honesty scoreboard, distinct from H14's "indicators
  don't work alone" finding.
- **The quality×uptrend near-miss is worth a plain-language callout on
  its own, separate from any combined claim:** in the holdout window,
  simply being above the 200-day MA (with no fundamental filter at all)
  outperformed everything else tested here, including the combination.
  That is itself closer to H14's already-published MA finding than to a
  new result: H14 found the *continuous* MA-distance correlation was
  null; this finds a *binary* above/below split had one strong holdout
  window. Worth flagging as a possible follow-up diagnostic (in the same
  spirit as H5's timing-precision check) rather than a standalone claim,
  since one strong holdout window from a binary split is exactly the
  single-period-fragile pattern H5's size leg already taught this
  project to distrust.

---

## H10: Broad pre-registered feature screen: which single features predict IDX returns?

**Date:** 2026-09-12. Adopted 2026-09-09 (`docs/PLAN.md`'s H10 section),
built once the comprehensive screener sweep (`data/raw/universe_2026-09-12.json`,
`industry`/`sub_industry`/`earnings[YYYY]`/price bands) landed.

### Why this exists

H1 and H5 each answer "does this one specific thing predict returns": 
one feature, tested carefully. This asks the broader question a retail
screener never answers honestly: **of the popular signals people watch,
which actually hold up, tested all at once with the multiple-comparisons
correction that honesty requires?** Testing 20 unrelated things yields
~1 "significant" result by chance alone at the usual 5% threshold: 
reporting only the winner is p-hacking. The discipline that prevents it:
every feature below is pre-registered (frozen before any result is
seen), tested identically in explore and holdout, and reported in full
, including nulls, with Benjamini-Hochberg FDR correction across the
whole batch.

### Pre-registered features (committed before running anything)

All seven are yearly `field[year]` values: snapshot fields are excluded
by rule (`CLAUDE.md`'s predictor-before-outcome constraint):

1. **earnings_yield** = 1/pe[year], pe>0 only. **Overlaps H5's already-
   confirmed value leg**: not independent evidence, kept for
   completeness under this module's different (sector-neutral-rank)
   methodology, disclosed rather than presented as fresh.
2. **roe[year]**: quality. H15 tested this only inside an interaction
   (quality × uptrend, null); first standalone test.
3. **debt_to_equity_ratio[year]**: leverage. Same story: H15 tested it
   only inside an interaction (high-leverage × downtrend, null); first
   standalone test. Predicted direction: negative.
4. **total_yield[year]**: realized dividend yield. Belief under test:
   "high dividend yield means better returns." Not tested standalone
   anywhere else in this project.
5. **size** = outstanding_shares[year] × raw close at formation.
   **Overlaps H5's size leg** (an unconfirmed lead there, not a
   validated finding): disclosed, not independent evidence.
6. **revenue_growth** = revenue[year]/revenue[year−1] − 1, prior-year
   revenue > 0 only. Belief under test: growth persists (or is already
   priced in).
7. **payout_ratio** = `stats.payout_ratio_from_totals` (dividend-per-
   share ÷ EPS, where EPS = earnings[year]/outstanding_shares[year]).
   ⚠️ Originally written here as `total_dividend[year]/earnings[year]`
   directly: corrected 2026-09-13 (see the correction note further
   below in this section): that naive division is off by a factor of
   shares outstanding, not a real payout ratio. Belief under test: a
   high payout predicts *worse* forward returns (the "unsustainable
   yield" story). Distinct outcome from H4 (payout ratio → dividend
   CUT, now tested and confirmed) despite the same ratio construction: 
   no overlap in what's being predicted.

No interaction terms: H15 already covers pre-registered interactions
under its own trial count; repeating them here would double-count.

### Method

**Sector-neutral ranks, not raw pooled values**: decided before
building: a bank's P/E isn't comparable to a miner's, so each feature is
converted to a percentile rank *within the company's own sub_sector*
(`pipeline.stats.sector_neutral_rank`, new this module) before pooling
across all 33 sub-sectors. Strips systematic sector differences while
keeping the full sample.

**Explore/holdout: the same boundary H1/H5/H14/H15 already use**: 
2022–2023 explore, 2024–2025 holdout, May-1-to-Sep-4 formation-lag
window, imported directly from `h5_value_size.py` so this can't
silently drift from that boundary.

**Multiple-comparisons correction, pre-declared:** Benjamini-Hochberg
FDR at q=0.10 across all 7 holdout tests (`pipeline.stats.
benjamini_hochberg`, new this session: p-values via the standard-normal
approximation this project already implicitly uses for its ~1.96
threshold, `math.erfc`, no scipy). Explore doesn't count as a separate
trial (matching H5/H15's own convention).

**A feature is called CONFIRMED only if it clears FDR *and* explore and
holdout agree in sign**: FDR survival alone is not enough, matching
every earlier hypothesis here (a result that only shows up in one phase
is exactly H5's own already-documented size-leg weakness).

Full runnable code: `pipeline/hypotheses/h10_broad_feature_screen.py`.

### What we found

**Holdout, n=1,774 pooled (symbol, formation-year) rows** (per-feature n
varies: see table; not every feature is defined for every row, e.g.
`earnings_yield` requires `pe>0`):

| Feature | Explore rho/t | Holdout rho/t (p) | FDR (q=0.10) | Sign agreement | Verdict |
|---|---|---|---|---|---|
| earnings_yield | +0.162 / +5.66 | +0.120 / +4.26 (p<0.0001) | survives | same | **CONFIRMED** (overlaps H5) |
| total_yield (dividend yield) | +0.079 / +1.95 | +0.078 / +2.06 (p=0.040) | survives | same | **CONFIRMED: new** |
| size (small→higher return) | −0.027 / −1.11 | −0.199 / −8.00 (p<0.0001) | survives | same | **CONFIRMED** (overlaps H5's size lead) |
| revenue_growth | −0.002 / −0.06 | +0.051 / +2.07 (p=0.038) | survives | **flipped** | NOT confirmed |
| roe (quality) | +0.019 / +0.76 | −0.025 / −1.04 (p=0.301) | does not survive | flipped | NOT confirmed |
| debt_to_equity_ratio (leverage) | −0.011 / −0.45 | −0.024 / −1.00 (p=0.318) | does not survive | same | NOT confirmed |
| payout_ratio | +0.011 / +0.25 | −0.032 / −0.79 (p=0.428) | does not survive | flipped | NOT confirmed |

**Three of seven confirmed, four null**: reported in full regardless.

⚠️ **Correction, 2026-09-13 (found building H4):** `payout_ratio`'s
original construction (`total_dividend[year]/earnings[year]`) divided a
PER-SHARE figure by a company-TOTAL figure: off by a factor of shares
outstanding, not a real payout ratio at all (caught by sanity-checking
against the snapshot `payout_ratio` field: BBCA's naive value came out
5e-12 against a real ~0.8). Fixed to `total_dividend[year] /
(earnings[year]/outstanding_shares[year])`. **The verdict is unchanged
, still NOT confirmed, but the table above reflects the corrected
numbers**, not the originally-published ones (both explore and holdout
rho/t changed slightly; explore's sign flipped from the original write-up,
still not significant either way). The other 6 features were never
affected by this bug and are unchanged.

### What's new here, not just a re-run

**Dividend yield → better returns is a genuinely new confirmed finding**
: `docs/PRODUCT.md`'s honesty-scoreboard row for this belief was marked
"untested" until this run; it is now the second real, positive finding
alongside H1 and H5's value leg. Modest (rho ≈ +0.08), same order of
magnitude as H5's value effect, but consistent in sign and significant
in both phases.

**The size result here is on firmer footing than H5's own size leg**,
and this needs stating plainly because it looks at the same underlying
relationship two different ways: H5's own timing-precision diagnostic
(`h5_timing_diagnostic.py`, see above) found its size effect
concentrated almost entirely in the 2024→2025 (post-rate-cut) holdout
window: "confirmed in one year" was H5's stated, unresolved weakness.
Here, the same size proxy, tested by pooling formation years within
each phase (2022+2023 explore vs. 2024+2025 holdout) and ranking
sector-neutrally rather than per-year, shows the *same negative sign* in
both phases, with holdout far stronger than explore (t=−1.11 → t=−8.00).
**This does not resolve H5's weakness**: the holdout is still dominated
by the same 2024→2025 window driving H5's own result, and the two
modules share the same underlying price data, so this is not
independent replication in the strict sense. But the sign holding in
explore too (even if weakly) is evidence H10's own pre-registration
didn't have when H5 was first written up. Treat this as "somewhat
firmer than before," not "resolved."

### Limits

- **earnings_yield and size are not independent evidence**: both
  overlap H5's already-published legs; their appearance in this table is
  disclosure of the overlap, not a second confirmation from a different
  dataset.
- **revenue_growth's holdout significance is not trustworthy**: it
  survives FDR but its sign flipped from explore (−0.002, essentially
  zero) to holdout (+0.051, barely significant). A near-zero explore
  estimate flipping sign under a different sample is weak evidence of
  nothing, not evidence of a real relationship the correction merely
  detected. Reported for completeness, not treated as confirmed.
- **total_yield's n is much smaller than the other features** (603
  explore, 701 holdout): many stocks pay no dividend in a given year,
  so this factor is only defined for a dividend-paying subset. The
  effect may not generalize to non-payers by definition.
- **Sector-neutral ranking assumes sub_sector is the right comparison
  group**: the same 13-of-33-sub-sectors-under-15-companies problem
  `docs/PLAN.md` already documents for the product's peer groups applies
  here too; a handful of tiny sub-sectors contribute noisy within-group
  ranks.
- **No p-value/FDR machinery existed in this project before this
  module**: the p-values here use a standard-normal approximation
  (`math.erfc`), the same asymptotic assumption every earlier
  hypothesis's ~1.96 threshold already implicitly relied on, now made
  numeric rather than a new, unverified method.
- **Dev-only price data, same status as H1/H5/H14/H15:** every number
  here comes from Yahoo, never shipped, and owes the same Sectors
  price cross-check already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 16** (H1, H1b, H5, H14's 3 indicators, H15's 3
  interactions, plus H10's 7 features): each feature is one
  pre-registered trial (explore doesn't count separately, matching
  H5/H14/H15's own convention).

### What it opens up

- **A second real, positive, user-facing finding** (dividend yield): 
  directly powers a finding card and updates the honesty scoreboard from
  "untested" to "yes, modestly," alongside H1 and H5.
- **The scoreboard itself gets three more null rows** (quality, leverage,
  growth, payout, 4 of 7 null), exactly the content `docs/PLAN.md`
  argues is itself a differentiator: "we tested 7 more things; 3 held up."
- **H4** (payout ratio → dividend cut, a different outcome) remains
  unaffected by payout_ratio's null result here: that tested payout
  ratio against *return*, not against *whether the dividend gets cut*;
  still a live, distinct candidate.

---

## H11: Do stocks suspended for "unusual price increase" subsequently underperform the index?

**Date:** 2026-09-13. Candidate since the plan's original design (ties
to the gorengan problem statement); adopted for real once
`/v2/suspensions/` was purchased (20 credits, full 588-record history: 
see `docs/credit_ledger.md`).

### Why this exists

74% of all 588 IDX suspensions purchased this session (437) are for a
"significant cumulative price INCREASE": IDX's own regulatory language
for a pump-like move, explicitly issued "as investor protection." This
is the closest thing to a direct, official, checkable gorengan marker
this project has data for, and unlike H8 (blocked at ~100+ credits) the
data was a single flat-rate purchase.

### Method

Pre-registered: suspended stocks (reason contains "peningkatan harga",
verified directly against the purchased data, not assumed) earn a
LOWER subsequent return than the index (^JKSE) over +30 and +90 calendar
days from the suspension date: a mean-reversion "pump fades" claim.
Explore = 2025 suspensions (312 usable events), holdout = 2026
suspensions so far (91/83 usable events at +30d/+90d: some 2026 events
are too recent for their horizon to have elapsed yet and are excluded,
not estimated). Baseline price is the last close before the halt
(`adjclose`); benchmark is the index over the identical window. Full
code: `pipeline/hypotheses/h11_suspension_underperformance.py`.

### What we found: and why the mean and the win-rate tell different stories

| Phase | Horizon | n | Beat index | Stock mean / median | Index mean / median | Welch t |
|---|---|---|---|---|---|---|
| Explore | +30d | 312 | 55.1% | +25.5% / +7.3% | +1.9% / +2.4% | +5.99 |
| Explore | +90d | 312 | 43.3% | +66.4% / −4.4% | +3.0% / +7.3% | +5.56 |
| Holdout | +30d | 91 | **37.4%** | +0.9% / **−11.7%** | −7.7% / −8.5% | +1.29 |
| Holdout | +90d | 83 | **33.7%** | −11.8% / **−30.5%** | −16.8% / −17.2% | +0.75 |

**By the pre-registered Welch-t criterion, H11 is FALSIFIED as stated: 
the mean-based test never comes out negative, let alone significantly
so, in either phase.** Taken at face value that looks like the opposite
of what was predicted.

**But the win-rate and median numbers tell a real, different, and more
useful story that the mean-based test is hiding.** In 3 of 4 cells
(both holdout horizons, and explore's +90d), the suspended stock beats
the index LESS than half the time, and its MEDIAN return is
substantially worse than the index's median over the same window: 
holdout's +90d median is −30.5% against the index's own −16.2% over the
same dates. **The mean is dragged strongly positive by a small number
of extreme continuing run-ups** (explore's own median flips from +7.3%
at +30d to −4.4% at +90d while the mean does the opposite, +25.5% →
+66.4%: a small number of stocks kept pumping hard enough to swing the
average even as the typical case reversed). This is the same
right-skewed shape H16 already documented for the whole IDX market
(Bessembinder's pattern): just sharper here, since a suspension for a
rapid price spike is exactly the population most likely to contain a
few genuine mania continuations alongside a majority that reverts.

### Honest verdict

**Neither a clean confirmation nor a clean null: reported as both,
deliberately, rather than picking whichever framing looks better.**
The formally pre-registered test (mean/Welch-t) does not confirm
underperformance and is not falsified in the "outperforms" direction
either: it is simply not significant, and mildly positive-signed in
both phases (a genuine, if weak, sign AGREEMENT between explore and
holdout, just in the opposite direction from what was predicted).
**The win-rate/median framing, not pre-registered as the primary test
but visible in the same output, shows real, holdout-consistent
underperformance** (33.7%–37.4% win rate, both well below 50%) that
would need its own honestly-labeled follow-up test (e.g. a sign test on
win-rate, or a test on medians) to be formally confirmed rather than
just observed.

### Limits

- **The primary Welch-t test treats paired same-window observations as
  independent**: the stock and index return at a given horizon share
  the exact same calendar dates, so they are not independent samples in
  the textbook sense this test assumes. No paired-test machinery exists
  in this project yet. This likely makes the reported t-statistics
  somewhat too confident either way, not just too weak.
- **Repeat suspensions of the same symbol are pooled as separate
  events, not collapsed**: a stock suspended 3 times during one rally
  contributes 3 non-independent rows. Not fixed here, consistent with
  this project's practice of disclosing rather than silently patching
  every clustering concern (see H5's dropout-bias precedent).
- **2026 holdout events requiring a horizon past "today" are excluded,
  not estimated**: the holdout n (91/83) is smaller than explore's
  (312) partly for this reason, not just because 2026 has fewer months
  of data so far.
- **The win-rate/median result described above was NOT the
  pre-registered primary test**: noticing it in the same run's output
  and reporting it honestly is different from having pre-registered it
  as the falsification criterion. Treat it as a real, disclosed
  observation worth a proper follow-up test, not as confirmed evidence.
- **Legal/naming note, unchanged from the rest of this project:** this
  reports a regulatory CATEGORY and a resulting base rate, never a
  claim that any named company manipulated its price. No symbol is
  singled out here as an accusation.
- **Dev-only price data, same status as every other Yahoo-derived
  number in this project:** owes the same Sectors price cross-check
  already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 18** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, plus
  H11's 2 pre-registered horizons).

### What it opens up

- **A genuinely usable, checkable base-rate sentence for the product,
  once the win-rate framing gets its own proper follow-up test:**
  "of stocks suspended for a sudden price spike, roughly 2 in 3 were
  down more than the index three months later": directly serves the
  gorengan problem statement without accusing any specific company.
- **A cautionary companion note the mean-based result itself supplies:**
  a minority of these stocks kept running hard enough to flip a naive
  average: "usually fades, but not always, and the exceptions are
  large" is itself a more honest, more useful message than either
  "always fades" or "doesn't fade."

---

## H4: Does a high payout ratio predict a dividend cut the following year?

**Date:** 2026-09-13. Adopted 2026-09-09 as "near-free" once
`earnings[YYYY]` was unlocked by the 2026-09-12 sweep; built once H10 and
H11 were done.

### Why this exists

"This dividend may not be sustainable" is a concrete, checkable,
non-advisory flag `docs/PLAN.md` designed the product around: but only
if the underlying claim (high payout → more likely cut) actually holds
on IDX. Distinct outcome from H10's `payout_ratio` feature (which tested
the same ratio against subsequent RETURN, and found nothing): this
tests it against a DIVIDEND CUT, a different question entirely, despite
sharing the ratio construction.

### A units bug, found and fixed before trusting any number

The obvious construction, `total_dividend[year] / earnings[year]`, is
wrong: `total_dividend` is a PER-SHARE rupiah figure, `earnings` is the
company's TOTAL profit. Dividing one by the other is off by a factor of
shares outstanding, not a payout ratio. Caught by sanity-checking a real
company (BBCA 2024) against the already-purchased snapshot
`payout_ratio` field: the naive construction gave 5e-12; the corrected
one (`total_dividend[year] / (earnings[year]/outstanding_shares[year])`,
i.e. dividend-per-share over EPS) gave 0.62, the right order of
magnitude against the snapshot's ~0.8 ttm figure. **This same bug
existed in H10's `payout_ratio` feature and has been fixed there too**
(H10's verdict for that feature is unchanged, still not confirmed, 
but its exact numbers in this document were corrected; see H10's own
entry).

### Method

Pre-registered: payout_ratio (dividend-per-share ÷ EPS) in year Y, top/
middle/bottom terciles, predicts whether `total_dividend[Y+1] <
total_dividend[Y]` (a cut). Only dividend-payers with positive earnings
in year Y are included (payout ratio is undefined otherwise). Usable
formation years: 2021–2024 (2025 is the latest year with a fully
realized Y+1 outcome, since 2026 isn't complete yet). Explore = formation
2021–2022 (outcome 2022–2023); holdout = formation 2023–2024 (outcome
2024–2025). Full code:
`pipeline/hypotheses/h4_payout_dividend_cuts.py`.

### What we found

| Phase | n | rho | t | T1 (lowest payout) cut rate | T2 cut rate | T3 (highest payout) cut rate |
|---|---|---|---|---|---|---|
| Explore | 450 | +0.403 | +9.33 | 8.0% (12/150) | 28.0% (42/150) | 51.3% (77/150) |
| Holdout | 540 | +0.441 | +11.41 | 13.9% (25/180) | 39.4% (71/180) | **65.6% (118/180)** |

**CONFIRMED, cleanly, in both phases**: a large, highly significant,
monotonic effect that gets clearly stronger with each tercile, in the
predicted direction, replicating from explore to holdout almost exactly
(rho +0.40 → +0.44). One of the strongest and least ambiguous confirmed
results in this project, alongside H1 and H5's value leg.

### What it means in plain language

Of IDX companies whose payout ratio was in the bottom third, roughly 1
in 10 cut their dividend the next year. Of those in the top third
(paying out about all, or more than all, of what they earned), roughly
2 in 3 did. **A high payout ratio is a real, checkable warning sign for
IDX dividend sustainability**: directly powers the flag `docs/PLAN.md`
designed this hypothesis for.

### Limits

- **Mechanical, not purely behavioral:** a company paying out 100%+ of
  earnings has very little room before a profit dip forces a lower
  absolute dividend even with an unchanged payout POLICY: some of this
  effect is closer to accounting arithmetic than a discovered market
  inefficiency. Still a real, useful base rate for the flag either way.
- **"Cut" is defined as ANY decrease**, including a token 1-rupiah
  reduction: does not distinguish a small trim from a dividend
  elimination. Not refined here.
- **No FDR correction needed at n=1 trial**, but this is exactly the
  kind of large, clean effect that should make anyone pause and
  double-check the construction before trusting it: which is exactly
  what happened (see the units-bug section above) and is the reason this
  result is trusted, not despite the correction but because of it.
- **Trial count: 19** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  plus H4).

### What it opens up

- **A clean, strong, directly product-usable finding**: powers the
  "this dividend may not be sustainable" flag exactly as designed,
  without needing any hedging beyond the mechanical-effect caveat above.

---

## H13: Do Acceleration-board IPOs underperform Main-board IPOs?

**Date:** 2026-09-13. Candidate since 2026-09-09 ("free to test": 266
owned 2021+ listings, prices already in the Yahoo dev cache); built as
the next free hypothesis after H4 confirmed and H12 hit a blocking data
problem.

### Why this exists

`docs/SOURCES.md` already cites published findings that ~2/3 of
Acceleration-board IDX IPOs from 2020-2024 posted negative returns at
360/720 days: this project holds `listing_date`/`listing_board` for 266
2021+ listings, already purchased, and prices already in the free Yahoo
cache. Zero additional cost to check whether the same pattern shows up
in this project's own data (a different sample/window, not a strict
replication of the cited study).

### Method

Pre-registered: Acceleration-board IPOs earn a lower return, and are
more often negative, than Main-board IPOs, at 180/365/720 calendar days
from first trade. "Listing price" proxy = nearest close within 10 days
of `listing_date` (not the actual IPO offer price: a disclosed
simplification). Explore = listed 2021-2022 (83 usable listings);
holdout = listed 2023-2024 (120 usable). A horizon is excluded per-event
if it hasn't elapsed yet, not padded. Full code:
`pipeline/hypotheses/h13_ipo_board_performance.py`.

### What we found

| Phase | Horizon | Acceleration n / neg. rate / median | Main n / neg. rate / median | Welch t (Accel vs Main) |
|---|---|---|---|---|
| Explore | +180d | 13 / 69.2% / −54.5% | 18 / 50.0% / +2.8% | −1.23 |
| Explore | +365d | 13 / 69.2% / −48.9% | 18 / 61.1% / −5.5% | −1.27 |
| Explore | +720d | 13 / 76.9% / −77.8% | 18 / 55.6% / −6.1% | −1.01 |
| Holdout | +180d | 20 / 60.0% / −35.8% | 21 / 47.6% / +2.8% | −1.23 |
| Holdout | +365d | 20 / **80.0%** / −73.0% | 21 / **33.3%** / +18.6% | −1.26 |
| Holdout | +720d | 20 / 65.0% / −33.7% | 18 / 27.8% / +6.7% | −0.41 |

**Same two-story pattern H11 already taught this project to check for,
found again.** The negative-rate/median framing shows a real, large,
consistent gap: Acceleration's negative rate is 60-80% in every one of
the 6 cells, Main's is much lower (28-62%), closely matching the cited
literature's own ~⅔ figure for Acceleration. **Every single one of the 6
Welch-t values is negative-signed** (Acceleration's mean return below
Main's), in both phases, at all three horizons: real sign agreement,
not a coin flip. **But none clears even the plain ~1.96 threshold**, let
alone the stricter ~2.4 Bonferroni bar: group sizes of 13-21 give this
test very little power, and mean returns are wildly noisy (a few extreme
winners, e.g. Main's holdout +365d mean of +186.5%, swamp the signal the
same way H11's suspension data did).

### Honest verdict

**Falsified on the pre-registered Welch-t test: not significant at any
horizon, in either phase.** But the negative-rate/median pattern is
large, consistent across both phases and all three horizons, and matches
independently-published literature closely enough that this reads as
real underpowered evidence, not noise: the sample is just too small
(13-21 per group) for the mean-based test to detect what the frequency
numbers already show plainly. Reported as both, exactly like H11,
rather than picking whichever framing looks cleaner.

### Limits

- **"Listing price" is a same-day-close proxy, not the actual IPO offer
  price**: a real difference from the cited literature's own basis;
  Sectors' `/v2/listing-performance/` would give the real figure but
  costs credits per symbol (docs/PLAN.md's ~60-120 credit estimate to
  ship this with real Sectors prices, a separate decision).
- **Small group sizes (13-21) are the likely reason the mean-based test
  never reaches significance** despite a large, consistent gap on the
  frequency measure: this is a power problem, not necessarily a sign
  the effect isn't real.
- **Extreme individual outliers dominate the mean** in several cells
  (e.g. Main's own IPOs occasionally posted 100%+ returns): the same
  right-skew this project has now found in H11 and H16, evidently a
  general property of IDX small/speculative stocks, not unique to any
  one hypothesis.
- **Development and Watchlist boards are reported descriptively only**
: no specific literature-backed directional claim was pre-registered
  for them, so their numbers (also often showing a real negative-rate
  gap, e.g. Watchlist's 100% negative rate at +720d holdout, n=3) are not
  part of the falsification test and the n is often very small.
- **Dev-only price data, same status as every other Yahoo-derived
  number in this project:** owes the same Sectors price cross-check
  already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 22** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  H4, plus H13's 3 horizons).

### What it opens up

- **A real, checkable base rate for the exact decision `docs/PLAN.md`
  §4.4 flags as served by nothing today:** "of the last N Acceleration-
  board IPOs, roughly 2 in 3 were below their first-trade price a year
  later": usable even while formally unconfirmed, with the caveat
  stated plainly (large gap, small sample).
- **A candidate for the ~60-120 credit real-Sectors-price version**,
  if the product build reaches a point where shipping this with real
  IPO offer prices (rather than the free proxy) is worth the spend.

---

## H11b: Among stocks suspended for an unusual price INCREASE, do larger companies hold their gains better?

**Date:** 2026-09-13. Promoted from an exploratory finding (found while
digging into H11's mean/median split at the user's request) to a
pre-registered, held-out test.

### The road here: including a false lead, kept for the record

Digging into why H11's suspended-stock returns sometimes fade and
sometimes keep running, three candidates were checked exploratorily
against H11's full pool (395 usable events):
1. **Size of the pre-suspension run-up**: no relationship (rho=+0.025,
   t=+0.50).
2. **Free float**, no relationship (rho=+0.028, t=+0.55), notably,
   H1's own float→volatility signal does NOT carry over to this specific
   question.
3. **Prior suspension count for the same symbol**: looked huge at first
   (Welch t=−6.37, "repeat offenders" doing far better) but this was a
   **look-ahead leak**: counting suspensions across *all* time (including
   ones AFTER the event being measured) smuggles outcome information
   into the predictor: a stock getting suspended again next month IS
   direct evidence its price kept rising during the very window being
   measured. Corrected to count only suspensions strictly BEFORE each
   event, the effect nearly vanished (t=+0.85, wrong direction even).
   **Kept here as documentation of exactly the mistake this project's
   own predictor-before-outcome discipline exists to catch**: not
   swept away as a footnote.
4. **Company size (market_cap)**: the one that held up: smallest
   tercile median +90d return −23%, largest tercile +15%, same sign in
   2025 and 2026 checked separately.

Candidate #4 is what this module tests properly.

### Method

Pre-registered: among stocks suspended for a significant cumulative
price INCREASE, larger companies (market_cap terciles, computed within
each phase's own pool) earn a higher subsequent return than smaller
ones, at +30d and +90d. Explore = suspended in 2025 (matching H11's own
boundary); holdout = suspended in 2026. Reuses H11's own
`_parse_events`/`_baseline_at_or_before` rather than reimplementing them.
Full code: `pipeline/hypotheses/h11b_suspension_size.py`.

**Predictor caveat, same shape as H1's `free_float`:** `market_cap` is a
SNAPSHOT field (current, as of the 2026-09-13 sweep), not a historical
value at the time of each past suspension event: not strictly
predictor-before-outcome the way H4/H5/H10's yearly fields are.
Disclosed plainly rather than papered over, matching H1's own long-
standing treatment of this exact limitation.

### What we found

| Phase | Horizon | n | rho | t | T1 (smallest) | T3 (largest) |
|---|---|---|---|---|---|---|
| Explore | +30d | 312 | +0.116 | +2.06 | mean +9.8% / median +0.0% | mean +37.8% / median +8.2% |
| Explore | +90d | 312 | +0.240 | +4.36 | mean +8.9% / median −17.6% | mean +99.7% / median +18.6% |
| Holdout | +30d | 91 | +0.127 | +1.21 | mean −10.1% / median −23.6% | mean −2.5% / median −13.0% |
| Holdout | +90d | 83 | +0.144 | +1.31 | mean −18.1% / median −34.2% | mean +7.8% / median −25.6% |

### Honest verdict

**Direction holds: all four rho values are positive, larger companies
consistently do relatively better: but holdout does not clear
significance at either horizon** (t=1.21, 1.31, well short of the usual
~1.96, let alone the stricter ~2.4 bar), and holdout's tercile table is
no longer cleanly monotonic (T2 dips below T1 at both horizons).
**NOT confirmed by this module's own pre-registered bar.** The much
smaller holdout sample (83-91 events vs. explore's 312) and a generally
rougher 2026 for suspended stocks overall (every tercile median is
negative in holdout, unlike explore) both plausibly explain the weaker
signal without requiring the underlying pattern to be false: but that
is exactly the kind of after-the-fact explanation this project doesn't
let itself lean on as proof. Reported honestly as underpowered, not
confirmed.

### Limits

- **market_cap is a snapshot field**: see the caveat above; same
  category of limitation H1 has carried since this project's first
  hypothesis, not a new problem invented here.
- **Holdout sample is small** (83-91 events): the most likely reason
  this fails to reach significance despite a same-signed correlation;
  a genuine power problem, not necessarily evidence of no effect.
- **The candidate-search process that led here was exploratory**: this
  module is the first REAL test of it, but the explore-phase numbers
  above were already known before this module existed (they're the same
  numbers from the original diagnostic pass): so "explore agrees with
  itself" here carries less weight than it would if explore had been run
  blind. Only the holdout numbers are genuinely fresh evidence.
- **Trial count: 24** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  H4, H13's 3, plus H11b's 2).

### What it opens up

- **A partial, honest answer to "why does it fade sometimes and not
  others"**: company size looks like a real part of the story, but the
  evidence isn't strong enough yet to ship as a confirmed finding: 
  worth re-testing once more 2026/2027 suspension data accumulates,
  rather than assumed settled either way.

---

## H8 (cheap version): Does insider selling before a price-spike suspension predict a deeper crash?

**Date:** 2026-09-13. The original H8 ("gorengan fingerprint" via
broker-concentration tracking) is blocked at ~100+ credits
(`/v2/broker-summary/`'s 14-day window cap makes full-market coverage
unaffordable). This is a different, cheaper mechanism, promoted from an
anecdote to a real pre-registered test at the user's direct request.

### Why this exists

H11's own companion probe (4 case studies, 2026-09-13) found insiders
selling meaningful stakes in the weeks before real price-spike
suspensions: MGLV's controlling holder sold from 74% to 67% ownership
across three filings in three weeks before its suspension. That was 4
anecdotes, not evidence. This module tests the same idea across **all**
437 qualifying suspension events, using a bulk `/v2/filings/` pull (79
credits: see the cost-overrun disclosure below) instead of one query
per event.

### Method

Pre-registered: stocks with an insider SELL filing in the 30 days
before a "peningkatan harga" (unusual price increase) suspension earn a
LOWER subsequent return than stocks with no such filing, at +30d/+90d.
Only filings strictly before the suspension date count (predictor-
before-outcome). Explore = suspended in 2025, holdout = suspended in
2026, matching H11/H11b's own boundary. Reuses H11's own
`_parse_events`/`_baseline_at_or_before` rather than reimplementing
them. Full code: `pipeline/hypotheses/h8_insider_selling_gorengan.py`.

**Data-quality guard, verified:** 1 of 1,388 pulled insider-sell filings
had an impossible `share_percentage_transaction` of 930.2% (a garbled
record for PPRI.JK, sharing the same holder/date as an adjacent sane
record showing 0.93%): excluded via a `<=100%` sanity filter before any
aggregation, not silently summed in.

### Small-sample limitation, stated up front

Only 29 of 437 events (6.6%) have a matching insider-sell filing in
their 30-day pre-window: **22 in explore, only 7 in holdout**: well
below this project's usual n≥10 convention for a formal test.

### What we found: and it does NOT confirm the anecdote

| Phase | Horizon | Insider sold: n / mean / median | No insider selling: n / mean / median |
|---|---|---|---|
| Explore | +30d | 20 / +16.6% / +10.0% | 292 / +26.1% / +6.8% |
| Explore | +90d | 20 / +35.8% / +2.7% | 292 / +68.5% / −4.9% |
| Holdout | +30d | 4 / +35.1% / −6.5% | 87 / −0.7% / −11.7% |
| Holdout | +90d | 4 / +100.1% / +67.6% | 79 / −17.4% / −32.8% |

**Falsified, and not just weakly: reversed in holdout.** Explore's
mean-based direction is weakly consistent with the hypothesis (t=−0.83
at +30d, t=−1.42 at +90d, neither significant), but holdout **flips
completely**: the "insider sold" group did dramatically *better* than
the "no selling" group at both horizons (median +67.6% vs −32.8% at
+90d): the opposite of what was predicted. With only 4 holdout events,
this reversal itself isn't reliable evidence of anything either: the
honest reading is that the sample is too thin to draw any conclusion,
and what data exists points away from the hypothesis, not toward it.

### Honest verdict

**The exciting 4-case anecdote did not replicate at scale.** This is
exactly what pre-registration and holdout discipline exist to catch: 
an anecdote that looked like a real pattern (MGLV's dramatic stake sale)
turned out not to generalize across the full population of qualifying
events. Not shipped as a finding, not carried forward as a "likely true
but underpowered" lead the way H11b's size result was: this one
actively reversed, not just fell short of significance.

### Limits

- **n=4 in holdout is far too small to distinguish signal from noise**
: this result could look completely different with a few more months
  of data either direction.
- **Only ~6.6% of suspension events have ANY matching insider-sell
  filing in the pre-window**: for the vast majority of pump-and-dump-
  flagged stocks, there's simply no insider filing to check, so even a
  real effect (if one exists) would only ever apply to a small minority
  of cases.
- **A 30-day pre-window is a specific, somewhat arbitrary choice**: not
  varied or tested against other windows here; a different window could
  in principle produce a different sample and different result. Not
  explored further given how thin the data already is.
- **Trial count: 26** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  H4, H13's 3, H11b's 2, plus this H8's 2).

### What it opens up

- **A clean, honest example for the honesty scoreboard**: "insiders
  selling before a price spike predicts a crash" is a plausible-sounding
  story that this project actually tested and found does not hold up: 
  itself valuable, checkable content distinct from a confirmed finding.
- **Confirms the value of pre-registration as a discipline, concretely**
: without this test, the 4-case anecdote could easily have been
  oversold as a real pattern in the product.

---

## H9: Does news sentiment (Bullish vs. Bearish, as tagged by Sectors) predict short-term returns?

**Date:** 2026-09-13. Previously "candidate, uncosted, not pre-
registered": researched and built for real at the user's request, who
specifically wanted a genuinely different axis from technical/
fundamental analysis.

### Why this exists

Literature review (see Sources below) found real, if short-lived,
sentiment effects on IDX specifically: one LSTM study on manufacturing
stocks found news sentiment the second-most-influential predictor,
ahead of several traditional financial variables. The classic reference
(Tetlock 2007) finds media pessimism predicts short-term downward
pressure, THEN a reversion toward fundamentals: a horizon-dependent
effect, not a simple "bullish news → stock keeps rising" story.
Sectors' own `/v2/news/` endpoint already tags articles Bullish/
Bearish/Neutral and links most to a specific symbol: no NLP pipeline
needed, a large scope reduction from the original "uncosted" framing.

### A major limitation, found only after pulling the data

The corpus (8,801 Bullish/Bearish-tagged articles, 294 credits: see
`docs/credit_ledger.md`) covers **only 2026-05-16 to 2026-09-12, ~4
months**: not the multi-year span every other hypothesis here uses.
This wasn't knowable from the schema; it only became clear after the
pull. Consequence: the usual calendar-YEAR explore/holdout split (2025
vs. 2026) used by H1/H5/H10/H11/H13 is impossible here: there's less
than one year of data at all. This module instead splits the pulled
window itself in half (first half = explore, second half = holdout), a
meaningfully weaker form of holdout than this project's other
hypotheses, since the two "phases" aren't genuinely independent time
periods and can share market-wide conditions.

### Method

Pre-registered: a stock named in a Bullish-tagged article earns a
higher return than one named in a Bearish-tagged article, over the
following 10 and 20 calendar days (short horizons, since the ~4-month
window can't support anything longer). One row per (article, symbol)
pair: 2,428 of 8,801 articles name more than one company (broad
market-wide news), each getting an identical sentiment reading, a real,
disclosed limitation, not deduplicated. Full code:
`pipeline/hypotheses/h9_news_sentiment.py`.

### What we found

| Phase | Horizon | Bullish n / mean / median | Bearish n / mean / median | Welch t |
|---|---|---|---|---|
| Explore | +10d | 5,165 / +0.4% / +0.4% | 2,558 / +1.1% / +0.0% | **−1.93** |
| Explore | +20d | 5,165 / +1.2% / +0.9% | 2,558 / +0.8% / +0.0% | +1.18 |
| Holdout | +10d | 4,555 / +1.7% / +0.6% | 1,863 / −0.1% / +0.0% | **+7.20** |
| Holdout | +20d | 3,663 / +3.8% / +2.0% | 1,503 / +1.6% / +0.0% | **+5.54** |

### Honest verdict: NOT confirmed, despite huge holdout t-statistics

Holdout's t-statistics (7.20, 5.54) are enormous: but **the +10d
horizon actually REVERSES sign between phases**: explore has bearish
outperforming bullish (t=−1.93, wrong direction), holdout has bullish
winning decisively (t=+7.20). Per this project's own standing rule
(explore and holdout must agree in sign before anything is called
confirmed: see H1/H5/H10's identical convention), **this fails at the
10-day horizon specifically**, despite huge significance in one phase.
The 20-day horizon is directionally consistent (both positive) but
explore is nowhere near significant there (t=+1.18). Given the sample
sizes are enormous (thousands of rows) yet the sign still disagrees at
one horizon, this reads less like noise and more like the corpus's two
halves genuinely reflecting different market conditions: exactly the
risk the module's own limitation section warned about before running
anything.

### Limits

- **The within-window "holdout" is not a real held-out time period**
  the way H1/H4/H5/H10/H11/H13's year-based splits are: both halves
  come from the same ~4-month window and likely share overlapping
  market regime effects. Treat any result here as considerably less
  trustworthy than this project's other confirmed findings until a
  longer news history is available to re-test against.
- **Multi-symbol articles (2,428 of 8,801) give identical sentiment
  readings to every named company**: not weighted down or
  deduplicated; a busy market-news day could correlate returns across
  many "unrelated" rows.
- **10-day sign reversal between phases is the headline limitation**: 
  this alone is enough to call the pre-registered hypothesis not
  confirmed, regardless of holdout's raw significance.
- **Article timestamp, not publication-to-market-open lag, is used as
  t0**: an article published after market close same-day is measured
  against a baseline price from before it existed; not adjusted for
  here.
- **Trial count: 28** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  H4, H13's 3, H11b's 2, H8's 2, plus H9's 2).

### What it opens up

- **A genuinely promising lead for a proper future test** once Sectors'
  news corpus accumulates a longer history: the 20-day direction
  agreement and the sheer sample size available (unlike H8's thin 29
  events) suggest this axis is worth re-testing, not abandoning.
- **A concrete illustration, alongside H8, of why holdout discipline
  matters**: a naive read of holdout's t=7.20 alone would have looked
  like the strongest finding in the whole project; only checking
  sign-agreement against explore caught that it doesn't actually
  confirm the pre-registered claim.

### Sources

- Alamsyah et al. (2019) and related IDX-specific sentiment studies: 
  found via literature search, 2026-09-13; see the search summary
  provided to the user in-conversation for full citations (Journal
  Sagepub LSTM study, PMC emerging-markets sentiment study, Atlantis
  Press IDX investor-sentiment study).
- Tetlock, P. (2007). "Giving Content to Investor Sentiment: The Role
  of Media in the Stock Market." *The Journal of Finance*, 62(3),
  1139-1168.

---

## H8b: Does insider BUYING before a price-spike suspension predict a better outcome? (mirror of H8)

**Date:** 2026-09-13. Requested directly by the user after H8 (insider
selling) came back falsified: insider buying is a distinct claim, not
just "the absence of selling." Lakonishok & Lee (2001, *Review of
Financial Studies*) find insider purchases predict returns more
reliably across markets than insider sales, reasoning that a sale can
be liquidity-driven noise while a purchase is a costlier, more
deliberate signal. Same 437 "unusual price increase" suspension events
as H8/H11; new data pull, `/v2/filings/` (`transaction_type=buy`), 60
credits, 1,767 records: see `docs/credit_ledger.md`.

**Pre-registered:** stocks with insider BUY filings in the 30 days
before a price-spike suspension earn a HIGHER subsequent return than
stocks with no such filings, over the following 30 and 90 calendar
days. Full code: `pipeline/hypotheses/h8b_insider_buying_suspension.py`.

**Data-quality note, a real fix over H8's own filter:** H8's
`0 < pct <= 100` filter silently drops any transaction whose
`share_percentage_transaction` rounds to 0.0: verified real, not
garbled data (e.g. BBCA buys of 0.001%-0.03% of its enormous share
count, confirmed via `share_percentage_before`/`_after`). 69 of 1,388
H8 sell records and 281 of 1,767 H8b buy records fall into this
category. H8b uses `pct <= 100` instead (excludes only the one
impossible >100% record, the buy-side mirror of H8's own excluded
PPRI.JK record): not backported to H8 to avoid re-touching an
already-closed hypothesis's methodology after the fact.

**Small-sample limitation, same shape as H8:** only 29 of 437 events
(6.6%) have a matching insider-buy filing: 18 in 2025 (explore, after
usable-row filtering), 7 in 2026 (holdout): below MIN_GROUP_SIZE=10 in
holdout for a formal test at either horizon.

### What we found

| Phase | Horizon | Bought n / mean / median | No buy n / mean / median | Welch t |
|---|---|---|---|---|
| Explore | +30d | 18 / +20.2% / +18.2% | 294 / +25.8% / +6.5% | −0.54 |
| Explore | +90d | 18 / +87.3% / +22.9% | 294 / +65.2% / −5.3% | +0.67 |
| Holdout | +30d | 7 / −10.2% / −17.2% | 84 / +1.8% / −11.4% | n/a (n<10) |
| Holdout | +90d | 7 / +22.8% / −27.0% | 76 / −14.9% / −32.9% | n/a (n<10) |

### Honest verdict: underpowered, and the two horizons disagree with each other

Neither horizon reaches a formal test in holdout (bought group n=7).
Descriptively: **the 30-day horizon is directionally consistent across
phases but in the OPPOSITE direction from the pre-registered
hypothesis**: insider buying predicts a *worse* subsequent return at
30 days in both explore (diff −5.6%) and holdout (diff −12.0%). **The
90-day horizon is directionally consistent WITH the hypothesis** in
both phases (diff +22.1% explore, +37.7% holdout). Two horizons of the
same underlying data giving opposite reads of the same claim is itself
informative: this is not a clean confirmation, and not a clean
falsification either. A plausible read, not verified further: insiders
buying right before a suspicious price spike may include participants
in the run-up itself (worse near-term outcome, consistent with a
"buying into the pump" story) whose position only looks vindicated over
a longer horizon if the stock happens to hold its gains: but this is
speculation, not something the data here can distinguish from noise
given n=7.

### Limits

- Holdout group (n=7) is below MIN_GROUP_SIZE=10 at both horizons: no
  formal significance test possible; only means/medians reported.
- Same event population as H8/H11: not independent evidence of a
  different underlying pattern, just a different predictor tested on
  the same 437 events.
- **Trial count: 30** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  H4, H13's 3, H11b's 2, H8's 2, H9's 2, plus H8b's 2: counted for
  disclosure purposes matching H8's own convention for underpowered
  subgroups, even though nothing here reached a formal significance
  test).

---

## H9b: Does sentiment DISAGREEMENT (bullish and bearish news at once) predict higher volatility?

**Date:** 2026-09-13. A different axis from H9's own DIRECTION test,
requested by the user as a way to get more use out of the already-paid
294-credit news corpus (no new Sectors cost). Tests whether a stock
getting bullish and bearish coverage at the same time: the market
visibly disagreeing about it: predicts a choppier ride next, not which
way sentiment leans.

**Pre-registered:** a symbol-window with both a bullish- and a
bearish-tagged article earns higher realized volatility over the
following 10 trading days than a one-sided-coverage window. To avoid
scoring near-duplicate overlapping windows (the H14/H15 pseudo-
replication lesson, applied up front this time), articles are grouped
into non-overlapping 20-day bins per symbol
(`pipeline/hypotheses/_news_bins.py`), not scored article-by-article.
Same within-window explore/holdout split as H9 (before/after
2026-07-15): same ~4-month-corpus caveat applies identically. Full
code: `pipeline/hypotheses/h9b_sentiment_dispersion_volatility.py`.

### What we found

| Phase | Mixed n / mean vol / median vol | One-sided n / mean vol / median vol | Welch t |
|---|---|---|---|
| Explore | 323 / 52.5% / 45.6% | 461 / 45.7% / 37.4% | **+2.65** |
| Holdout | 417 / 38.7% / 31.8% | 580 / 38.9% / 30.5% | −0.10 |

### Honest verdict: NOT confirmed

Explore looked like a real, significant effect (t=+2.65, mixed-coverage
stocks ~7 points more volatile). It **completely vanished in holdout**
(t=−0.10, effectively zero difference). This is the clean pattern H5's
own stress-testing work exists to catch: a result that looks real in
one slice and disappears in the next is exactly what a placebo/holdout
discipline is supposed to filter out before anything ships.

### Limits

- Same weak within-window holdout caveat as H9/H9c/H9d: inherited from
  the corpus's ~4-month span.
- Overall market-wide volatility may simply have been higher in the
  explore half of the window than the holdout half (a level-shift
  unrelated to sentiment dispersion specifically): not separately
  checked here.
- **Trial count: 31** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  H4, H13's 3, H11b's 2, H8's 2, H9's 2, H8b's 2, plus H9b's 1: single
  horizon, unlike H9's two).

---

## H9c: Does news COVERAGE VOLUME (regardless of tone) predict returns?

**Date:** 2026-09-13. Third of the three follow-up angles on H9's data.
Motivated by attention-driven-trading literature (Barber & Odean, "All
That Glitters," 2008): unusual investor attention on a stock can
predict distinctive subsequent price behavior independent of whether
the attention is positive or negative.

**Real limitation, stated up front:** the pulled corpus was filtered to
`tags=bullish,bearish` only: there is no neutral-tagged news in this
dataset, so "attention" here means "count of bullish/bearish-tagged
articles," a proxy, not true total coverage volume (which would need a
separate, uncosted pull of neutral-tagged news too).

**Pre-registered:** an above-median-article-count symbol-window earns a
different subsequent 10-trading-day return than a below-median-count
window; no direction pre-specified (exploratory: does volume matter at
all, not which way). Same 20-day non-overlapping bins as H9b. Full
code: `pipeline/hypotheses/h9c_news_attention_volume.py`.

### What we found

| Phase | High-attention n / mean / median | Low-attention n / mean / median | Welch t |
|---|---|---|---|
| Explore | 380 / +5.1% / +3.0% | 404 / +4.0% / +1.3% | +1.28 |
| Holdout | 459 / +1.9% / 0.0% | 543 / +2.2% / 0.0% | −0.45 |

### Honest verdict: the cleanest null of the three follow-ups

Not significant in explore (t=+1.28), and the sign flips in holdout
(t=−0.45) on top of that. No evidence news-volume alone (independent of
tone) predicts IDX returns in this corpus.

### Limits

- The "attention" proxy is incomplete (bullish/bearish only, no
  neutral-tagged baseline): a genuine attention test would need the
  full news feed, not this subset.
- Same weak within-window holdout caveat as H9/H9b/H9d.
- **Trial count: 32** (H1, H1b, H5, H14's 3, H15's 3, H10's 7, H11's 2,
  H4, H13's 3, H11b's 2, H8's 2, H9's 2, H8b's 2, H9b's 1, plus H9c's
  1).

---

## H9d: Is news more bearish than usual right before a price-spike suspension?

**Date:** 2026-09-13. The most direct tie to the gorengan theme of the
three follow-ups, but the weakest in design: **descriptive only, not
a pre-registered statistical test, and not counted in the trial
counter**, stated up front rather than dressed up with a p-value on a
sample this small.

**The constraint, checked before building anything:** the news corpus
spans only 2026-05-16 to 2026-09-12 (~4 months); the 437 "unusual price
increase" suspension events span all of 2025-2026. Only events falling
inside the news window can be checked: verified: 30 of 437 (6.9%), and
only 22 of those actually have at least one tagged article in their
30-day pre-window. Full code:
`pipeline/hypotheses/h9d_sentiment_before_suspension.py`.

### What we found

Population baseline across the whole corpus: 10,926 bullish / 4,894
bearish articles (30.9% bearish overall). Of the 22 covered
suspension events: 3 bearish-only, 10 bullish-only, 9 mixed. Pre-window
bearish share across all 22 events: **25.0%**: slightly BELOW the
30.9% population baseline, not above it.

### Honest verdict: no support for the idea, on a sample too small to trust either way

If anything, the pre-suspension coverage in this tiny sample runs
*more* bullish than the market-wide baseline, not more bearish: the
opposite of what a "the market senses something is wrong" story would
predict. With n=22 and no matched control group (the 30.9% baseline is
a rough population average, not stocks matched on size/sector/period),
this is not strong enough evidence to conclude anything either way: it
just doesn't support the hypothesis on the data available.

### Limits

- n=22 is far below any threshold this project treats as informative;
  not a matched control (population baseline vs. a specific 30-day
  pre-event window for a handful of small, illiquid stocks are not
  directly comparable).
- 407 of 437 events (93%) predate the news corpus entirely and simply
  cannot be checked with this data.
- **Not counted in the trial counter**: descriptive only, per the
  module's own stated design.

---

## H16: Of IDX stocks, how many actually beat the alternatives to picking them?

**Date:** 2026-09-12. **NOT a falsifiable predictive hypothesis**: no
"X predicts Y" claim, no explore/holdout split, does not add to the
trial counter. Descriptive/comparative, same category as the sector
lenses ("correct arithmetic," not a testable claim). Kept the "H16"
label for continuity with how it was discussed while planning; it
belongs with the base-rate family (Chunk M).

### Why this exists

Every hypothesis tested so far (H1, H5, H14, H15) asks "does signal X
help pick a *better* stock." This asks the prior question a retail
investor should ask first: **is picking an individual stock, in
general, even a good idea compared to the alternatives?** This is the
question Bessembinder ("Do Stocks Outperform Treasury Bills?", SSRN
2018) asked of the entire US market since 1926: nobody has published
an IDX version. His finding: 4 of 7 US stocks underperformed T-bills
over their lifetime, and the best-performing 4% of firms explain the
*entire* market's net wealth creation above cash; the other 96%
collectively just matched it. That comes from positive skew (a handful
of huge winners), not from typical stocks being good bets.

**Honest scope limitation, stated up front:** Bessembinder used ~90
years of data; this uses the ~5 years of Yahoo price history this
project already owns. This measures "how IDX stocks did over roughly
2021–2026," not "over their lifetimes": a narrower, different claim
from his, not a like-for-like replication.

### The five benchmarks, and why each was chosen (decided with the user, 2026-09-12)

1. **IDX Composite index (^JKSE)**: the standard "just buy the market."
2. **Gold, in rupiah.** Verified via search: **67% of Indonesians hold
   gold** as an investment; it returned **32% (2024) and 44% (2025
   YTD)** in rupiah terms `[snippet]`. For much of this product's
   target audience this may be the *actual* alternative to buying a
   stock, not a theoretical one.
3. **Bank deposit / BI policy rate.** No API exposes this as a queryable
   series: built from a small manually-compiled table, sourced
   directly from `bi.go.id` for 2025–2026 (`[fetched]`, day-precise) and
   a secondary aggregator for 2021–2024 (`[snippet]`, month-precise).
   One disclosed gap: the exact date of the drop from 5.25% (Jul 2025)
   to 4.75% (by Dec 2025) wasn't pinned down: approximated as a single
   step at the later, verified date. Proxies a floating-rate deposit,
   not any specific bank's actual (typically lower) offered rate.
4. **The typical stock, not just the index: Bessembinder's actual
   point.** The cap-weighted index is itself dragged up by the same
   handful of giant winners a given stock was never realistically going
   to weight like. Computed as the cross-sectional median of every
   stock's own annualized return.
5. **Sector/sub-sector peer median**: reuses the peer-group split
   already planned for the product's 4 lenses.

### How we tested it

Each stock's OWN available window in the Yahoo cache (first to last
timestamp), not a forced common window: a forced window would bias
toward old, stable, already-listed-in-2021 companies and exclude newer
IPOs, exactly the population most relevant to "someone about to buy a
hot listing." Required ≥1 year of history. Total return on `adjclose`
(dividend-inclusive, same convention as H5), annualized so stocks with
different-length histories are comparable. Index and gold are
date-matched to each stock's own two calendar dates; the deposit proxy
is compounded from the rate table over those same dates; the typical-
stock and sector benchmarks are population-level medians.

Full runnable code: `pipeline/hypotheses/h16_stock_vs_benchmarks.py`,
building on a new dev-only fetch (`pipeline/dev/fetch_benchmark_prices.py`,
`^JKSE`/`GC=F`/`USDIDR=X`, never ships, same status as the existing
Yahoo price cache).

### What we found

**n = 887 stocks with ≥1 year of history.**

| Benchmark | Stocks that beat it | Rate |
|---|---|---|
| IDX Composite index | 441 of 887 | 49.7% |
| **Gold, in rupiah** | **141 of 887** | **15.9%** |
| BI-rate deposit proxy | 376 of 887 | 42.4% |
| Typical (median) stock | 443 of 887 | 50.0% (by construction) |
| Own sub_sector peer median | 435 of 887 | 49.0% |

**Distribution shape:**
- Median annualized return: **+1.6%**. Mean: **+4.7%**. Mean well above
  median: the right-skewed shape Bessembinder describes: a few big
  winners pull the average up while the typical stock trails it.
- Bottom decile (88 stocks): mean **−36.1%** annualized.
- Top decile (88 stocks): mean **+68.0%** annualized.
- **418 of 887 stocks (47.1%) had a negative annualized return** over
  their own available window.

### What it means in plain language

**Roughly a coin flip against the index, but a landslide loss against
gold.** Half of IDX stocks didn't even beat simply holding the index: 
consistent with the "most individual stocks are mediocre, a few huge
winners carry the market" pattern documented for the US. But the
sharper finding is against gold: **only 16 stocks in 100 did better than
just holding gold** over this window. For an audience where two in
three households already hold gold, this is a directly actionable
comparison no competitor product makes: buying a random IDX stock over
this period was, more often than not, a worse decision than doing
nothing and holding what a majority of the target audience may already
own.

### Why it came out this way (inferred, not verified)

Gold's 2024–2025 rally (32–44% annual returns, cited above) landed
inside this project's own 5-year measurement window: a period-specific
tailwind for gold, not a claim that gold structurally beats IDX stocks
over all horizons. Stated as plausible, not tested: a different 5-year
window (e.g. one without a gold rally) could show a very different
gold-comparison number. This is exactly the kind of period-dependency
this project's own H1/H5 write-ups already flag for their findings: not
unique to H16.

### Limits

- **Not a lifetime measure**: see the scope limitation above. A stock
  that IPO'd in 2025 is measured over ~1 year, not 5; its annualized
  number carries much more noise than a stock measured over the full
  window. Not adjusted for here beyond the 1-year minimum.
- **Survivorship, in the direction this project's other findings don't
  usually have:** a stock that was suspended or effectively delisted
  mid-window and never resumed trading would show a truncated window
  ending at its last traded price, not a "zero" outcome: if any such
  cases exist in the 887, this could modestly overstate average
  performance. Not checked this session.
- **The BI-rate table's 2021–2024 entries are month-precision,
  `[snippet]`-sourced, not independently re-verified against `bi.go.id`
  day-by-day**: adequate for an annualized comparison over a 1-5 year
  window, not precise enough for a monetary-policy analysis.
- **Gold priced via GC=F (a US futures contract) × USDIDR=X, not a
  domestic Indonesian gold price (e.g. Pegadaian or Antam rates)**: 
  these track closely but aren't identical; a domestic price series
  would be more locally accurate if one becomes available.
- **Dev-only price data, same status as every other Yahoo-derived
  number in this project:** never ships; owes the same Sectors
  price cross-check already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- Reviewed manually plus a background `/code-review` pass (see the
  working plan for its findings) rather than a single synchronous pass,
  since the review tool hit its weekly rate limit mid-session and later
  reset.

### What it opens up

- **The strongest candidate yet for the home-page ranking + honesty-
  scoreboard treatment**: "beat gold: 16%" is a single, visceral,
  directly usable sentence, more so than any correlation this project
  has produced.
- **Reframes the H14/H15 nulls as expected, not disappointing:** if
  most individual stocks are mediocre by the shape found here, it's
  unsurprising that short-horizon technical signals struggle to
  reliably separate the few winners from the many: the nulls and this
  finding tell one coherent story, not several unconnected ones.
- **Both product renderings planned, not yet built:** (1) home-page
  ranking of stocks by how they did against each benchmark; (2) a
  per-stock detail chart plotting that stock's own cumulative-return
  line against the index, gold, and typical-stock lines: free, reuses
  owned Yahoo data, no new Sectors call. Both deferred to the app-build
  phase (Chunk N), per the product's own "detailed product planning is
  its own pass" rule.

---

## Chunk M base rates: loss-maker turnaround, typical drawdown, recovery after a fall

**Date:** 2026-09-13. Same category as H16: **not falsifiable
hypotheses**, no explore/holdout split, no significance test, not
counted in the trial counter. All three are free (owned Sectors
sweep + owned Yahoo price cache, no new API calls), from
`docs/PLAN.md`'s Chunk M "base-rate family," which the plan itself
flags as the highest-value remaining free work: each answers a
concrete decision the problem statement names as currently served by
nothing (`docs/PLAN.md` §4.4).

### Loss-maker turnaround rate: "it's cheap because it's temporarily loss-making"

Of IDX companies that lost money in a given year, what fraction were
profitable again the following year? Uses the owned `earnings[YYYY]`
field (`data/raw/universe_2026-09-12.json`, 2021-2025), no price data
needed. Full code: `pipeline/hypotheses/m_loss_maker_turnaround.py`.

| Transition | n loss-years | turned around | rate |
|---|---|---|---|
| 2021→2022 | 230 | 81 | 35.2% |
| 2022→2023 | 207 | 55 | 26.6% |
| 2023→2024 | 211 | 39 | 18.5% |
| 2024→2025 | 205 | 50 | 24.4% |
| **Pooled** | **853** | **225** | **26.4%** |

**Reasonably stable across years** (18.5%-35.2%, no single year driving
the pooled figure): roughly **1 in 4** loss-making IDX companies
return to profit the very next year. Tempers "it's cheap because it's
temporarily loss-making" without needing a prediction: most don't turn
around within a year.

### Typical drawdown for a stock's profile: "is this fall normal?"

How far does a stock like this usually fall in a bad year? Uses the
1-year Yahoo cache (raw `close`, H1's convention) + the owned
`market_cap` snapshot for descriptive size buckets. ⚠️ **A first attempt
using the 5-year cache's full-period drawdown produced implausibly
extreme numbers (median −74.7%): caught by comparing against H1b's
own published 1-year drawdown figures (−40% to −66% range) before
writing anything up; switched to the 1-year window to match.** Full
code: `pipeline/hypotheses/m_typical_drawdown.py`.

| Group | n | 25th pctile | median | 75th pctile |
|---|---|---|---|---|
| All IDX stocks | 913 | −66.3% | −49.5% | −35.2% |
| Smallest tercile | 304 | −68.7% | −54.7% | −40.8% |
| Mid tercile | 304 | −65.0% | −49.5% | −35.3% |
| Largest tercile | 305 | −63.3% | −44.3% | −30.6% |

**The median IDX stock's worst 1-year decline is around −50%**: a
sobering number worth surfacing on its own, not just as a size-bucket
comparison, since it resets expectations for what "normal" looks like
on this market regardless of which stock a user holds. Size still
matters at the margins (smallest tercile ~10 points worse than
largest), consistent in direction with H1/H1b's own float/size-volatility
findings, though this isn't the same claim (current size vs. current
drawdown, not a predictive test).

### Recovery after a fall: "should I average down?"

Of stocks that fell 30%+ from a peak, what fraction were back to that
peak a year later, vs. still down? Uses the 5-year Yahoo cache only.
Event detection built to avoid double-counting the same decline
multiple times (a running-peak/re-arm design: see module docstring):
1,348 distinct fall events found across 887 stocks. Full code:
`pipeline/hypotheses/m_recovery_after_fall.py`.

| Outcome (measured ~1 year after the 30%+ trigger) | n | share |
|---|---|---|
| Still below the pre-fall peak | 1,191 | **88.4%** |
| Back at or above the pre-fall peak | 157 | 11.6% |

Of the 1,191 still down, the median gap to the old peak was still
**−49.2%**: not a near-miss, a real continued shortfall. **This is a
demanding bar (fully round-tripping back to the OLD HIGH, not merely a
positive return)**, so the low recovery rate should not be read as "88%
of IDX stocks lose money": it specifically answers "did this stock's
big fall round-trip within a year," which is what "should I average
down expecting a snap-back" actually asks. Consistent in spirit with
H16's own finding that only 49.7% of stocks beat the index and 47.1%
had a negative annualized return: this market does not reliably
reward buying dips on a 1-year horizon.

### Limits, all three

- **Descriptive base rates, not predictions for any individual stock.**
  None of these claim "this specific stock will behave this way": they
  report what happened across the population, same epistemic status as
  H16.
- **Loss-maker turnaround:** only checks a 1-year turnaround; a company
  that recovers in year 2 counts as "did not turn around" here: a
  real, disclosed undercount of the true eventual-turnaround rate.
- **Typical drawdown:** current `market_cap` used for a descriptive
  grouping only (not a predictive claim): see module docstring for why
  that's fine here despite the project's usual predictor-before-outcome
  rule (which governs "X predicts Y" claims, not descriptive groupings).
- **Recovery after a fall:** "recovered" requires the close price back
  at/above the OLD peak specifically: a stock that's up 25% from its
  trough but still below its old high counts as "still down" here. A
  gentler bar (e.g. "recovered X% of the drawdown") was considered but
  not built, to keep the headline number answering exactly the
  "should I average down" question rather than a softer one.
- **Not counted in the trial counter**: none of the three is a
  falsifiable "X predicts Y" claim.

## Pre-registration, 2026-09-22: H17 and three descriptive situations (S1, A, D)

**Written before any outcome for these definitions was computed.**
Everything below is frozen here first; the modules come after.

**Disclosure.** Earlier in the build a rough, exploratory look at
outcomes was taken for candidate situations A and D (and two others,
B and C, that are dropped: B looked like a data artifact, C needs its
own pre-registration). A and D below are therefore descriptive base
rates only, never findings, and their definitions may have been
influenced by that look. S1 and H17 had counts only (S1: number of
events and stocks); no outcome was looked at.

### H17: "Laba naik → harga naik" (a falsifiable hypothesis, +1 trial)

Belief under test: companies whose annual net income grew go on to
have higher returns.

- **Predictor:** `earnings[Y] / earnings[Y−1] − 1`, only where
  `earnings[Y−1] > 0`. Yearly field, measured strictly before the
  outcome window (predictor-before-outcome holds: Y's full-year figure
  is published by about April Y+1, the window opens 1 May Y+1).
- **Outcome:** `adjclose` return from 1 May to 4 Sep of Y+1, the same
  window and price rule as H5/H10 (constants imported from
  `h5_value_size.py`, so the boundary cannot drift).
- **Method:** percentile rank within each `sub_sector`
  (`stats.sector_neutral_rank`), pooled, Spearman against the return.
  Explore 2022–2023, holdout 2024–2025.
- **Direction, fixed in advance:** positive.
- **Decision rule:** CONFIRMED only if holdout p < 0.05 (two-sided) and
  explore and holdout agree in sign. One test, so no FDR correction;
  it adds **one trial (32 → 33)**.
- **Overlap, disclosed:** it sits next to H10's `revenue_growth` and
  `earnings_yield`, which used different inputs. Earnings growth was
  not one of H10's seven features.

### S1: "Harga baru melonjak" (descriptive situation, not counted)

- **Event:** the first close with `close[t] / close[t−20] − 1 ≥ +0.40`
  (20 trading days), raw `close` from the 5-year dev cache. After an
  event, the next one for the same stock needs at least 40 more trading
  days. Bars with a missing or non-positive close are dropped.
- **In the situation now:** the stock's latest event is at most 20
  trading days old.
- **Base rate, three numbers, fixed in advance**, measured on the
  event day's close over the next 60 trading days: (a) share of events
  whose close 60 trading days later is below the event-day close;
  (b) median and 25th/75th percentile of that 60-day change; (c) share
  that closed at least 30% below the event-day close at some point
  within the 60 days. Events with fewer than 60 later bars are left
  out.
- **Limits stated up front:** events of the same stock can overlap, so
  the events are not independent; a stock-level view (first event per
  stock) is reported beside the pooled one. Five years, one market
  regime. No comparison against any other group.

### A: "Laba turun dua tahun berturut-turut" (descriptive)

- **Trigger:** `earnings[Y] < earnings[Y−1] < earnings[Y−2]`, all
  reported, and `earnings[Y−2] > 0`. Shown now for Y = 2025.
- **Base rate:** among stock-years with that trigger where
  `earnings[Y+1]` exists (Y = 2023, 2024), the share with
  `earnings[Y+1] > earnings[Y]` (earnings rose the next year).

### D: "Laba lebih dari dua kali lipat" (descriptive)

- **Trigger:** `earnings[Y] > 2 × earnings[Y−1]` and `earnings[Y−1] > 0`.
  Shown now for Y = 2025.
- **Base rate:** among stock-years with that trigger where
  `earnings[Y+1]` exists (Y = 2022–2024), (a) the share with
  `earnings[Y+1] < earnings[Y]` (gave part of it back) and (b) the
  share with `earnings[Y+1] < earnings[Y−1]` (gave all of it back).

**Not counted in the trial counter:** S1, A, D. **Counted:** H17.

### Results, run 2026-09-22 (each module run once, as pre-registered)

**H17: NOT confirmed.** Explore (Y = 2022–2023): n=1,196, rho +0.050,
t +1.73, p=0.084. Holdout (Y = 2024–2025): n=1,256, rho +0.002, t +0.07,
p=0.945. Same sign, but the holdout effect is zero. **Trial count: 33**
(was 32). Reproduce: `.venv/bin/python -m pipeline.hypotheses.h17_earnings_growth`.

**S1, descriptive** (`m_recent_spike`): 773 stocks had at least one jump of
40% or more in 20 trading days. Of 3,081 events with 60 later bars:
57.2% closed lower 60 trading days later, median change −7.0%
(25th/75th percentile −26.9% / +24.9%), and 32.4% closed at least 30%
below the event-day close at some point in the 60 days. First event per
stock (n=766): 57.8% lower, median −8.0%, 27.7% deep drop. Roughly 4 in 10
did not fall, and a quarter gained about 25% or more, so this describes a
wide spread, not a direction. Events of one stock can overlap.
*Implementation fix, disclosed:* the first run compared
`close[t]/close[t-20] - 1 >= 0.40`, which misses an exact +40% because of
floating-point (140/100 - 1 is 0.3999…). It now compares
`close[t] >= close[t-20] * 1.40`. The first run gave 3,044 events / 771
stocks and the same shape (57.2% lower, median −7.1%, 32.7% deep drop);
the definition is unchanged.

**A, descriptive** (`m_earnings_streaks`): 136 stocks are in it now
(Y = 2025). Of 262 earlier stock-years (Y = 2023: 108, 2024: 154), 151
(57.6%) had higher earnings the next year (61.1% and 55.2%).

**D, descriptive** (`m_earnings_streaks`): 79 stocks are in it now. Of 256
earlier stock-years (Y = 2022–2024), 136 (53.1%) had lower earnings the
next year than the jump year, and 53 (20.7%) fell below the pre-jump
level (by year: 23.5% / 20.3% / 16.4%).

Earlier notes said 77 stocks for A; the pre-registered definition
(`earnings[Y-2] > 0`, all three years reported) gives 136. The
pre-registered number is the one used.

## Pre-registration, 2026-09-26: H6 "Asing borong → harga naik" (a falsifiable hypothesis, +1 trial)

Written **before any list data was pulled**. Only availability probes were
run (5 + 4 credits, ledger 2026-09-26): they show the full-market
foreign-flow list is empty until between 2024-12-13 and 2025-01-31, and
they looked at no prices or outcomes.

**Belief.** The stocks on a day's "top foreign net buy" list (what retail
apps show as *asing borong*) do better afterwards than the stocks on the
"top foreign net sell" list.

**Why it is not obvious.** Foreign flow follows past returns (feedback
trading) and moves the price the same day (price impact), so a rise on
the day is not evidence. Studies of Indonesia disagree on whether it
predicts later returns (Ekaputra 2014 same-day only; Arroisi &
Koesrindartoto 2019 no effect on returns; Froot et al. 2001 country-level
predictive). No study found tests the retail "daily list".

**Data.** Sectors REST `/v2/foreign-flow/?date=D` (no MCP tool exists),
page 1 of the two orderings: top 30 by `net_foreign_inflow` (buy list) and
top 30 by ascending `net_foreign_inflow` (sell list). Investor-origin
attribution. Outcomes from the Yahoo dev cache `adjclose` (research only,
never shipped) and `^JKSE`.

**Dates.** ^JKSE trading days from 2025-01-31 (first verified list date)
to 2026-09-11; every 6th trading day from a seeded random offset (seed
20260926, offset 0), so outcome windows never overlap. 63 dates. Explore =
dates up to 2025-09-30 (26); holdout = from 2025-10-01 (37).

**Outcome.** From the close of D+1 to the close of D+6 (5 trading days,
starting the first day a user who saw the list that evening could act),
minus the same-window ^JKSE return. Stocks with a missing price are counted
and reported, not silently dropped.

**Primary statistic.** Per date: mean excess return of the buy list minus
mean excess return of the sell list (stock returns winsorised at the pooled
1st/99th percentile). A one-sample t-test of that spread across dates,
per phase.

**Decision.** CONFIRMED only if the holdout spread is > 0 with p < 0.05
(two-sided) and the explore spread has the same sign. A significant
negative holdout spread is reported as the opposite of the belief. Anything
else: NOT confirmed, stated with the minimum detectable effect. +1 trial
(33 → 34).

**Robustness (pre-registered, not extra trials).** (1) Regress the spread's
stock-level returns on list membership plus past 20-day return and log size
(price × prior-year shares), date fixed effects, errors clustered by date;
(2) medians and the share beating ^JKSE; (3) large half vs small half by
market cap; (4) same-day return and past-20-day return of each list,
descriptive only, to show price pressure and feedback.

**Power, stated up front.** Simulated on the price cache (500 random dates,
two random groups of 30 among the 200 largest, 2025–26 volatility): the
per-date spread has SD about 2.5% at 5 days. With 37 holdout dates the
minimum detectable effect (80% power) is about **1.2%** per 5 days; pooled
over 63 dates about 0.85%. A smaller true effect would come out as NOT
confirmed. **Known limits, disclosed now:** only about 20 months of list
history exist, all in one market regime (including the 2026 sell-off), so a
holdout that agrees with explore is weaker evidence than for H5 or H10.

### Amendment to the H6 pre-registration, 2026-09-26 (before any outcome was computed)

Two clarifications made after the pull and **before the analysis was run**:
1. The p-value is the exact Student-t value (n is 26 and 35, too few for
   the normal approximation this project uses elsewhere). Same test.
2. Two of the 63 dates, 2026-03-27 and 2026-04-15, returned an empty list
   (probably exchange holidays that the price cache still lists as bars).
   With no list there is nothing to test, so they are excluded and
   reported: **61 dates, 26 explore and 35 holdout.** The minimum
   detectable effect on the holdout rises slightly (about 1.25%).

### Results, H6, run once on 2026-09-26

**H6: NOT confirmed. No detectable effect in either phase.** Trial
count: **34**.

| | Explore (26 dates, to 2025-09-30) | Holdout (35 dates, from 2025-10-01) |
|---|---|---|
| Mean spread, buy list minus sell list (5-day excess return) | +0.05% (t +0.17, p 0.87) | −0.03% (t −0.05, p 0.96) |
| Share beating ^JKSE, buy list / sell list | 44.7% / 45.9% | 48.9% / 50.3% |
| Median excess return, buy / sell | −0.64% / −0.41% | −0.14% / +0.03% |
| Regression: list membership, controlling past 20-day return, size, date effects | −0.18% (p 0.59) | −0.19% (p 0.72) |
| Large half / small half spread | −0.47% (p 0.42) / +0.37% (p 0.47) | −0.51% (p 0.41) / +0.02% (p 0.98) |

**In plain numbers:** of 100 stocks on the top foreign-buy list, about 45
(explore) and 49 (holdout) beat the index over the next 5 trading days;
of 100 on the sell list, about 46 and 50. No difference.

**What the lists do show (descriptive, not tested).** The buy list had
already risen: +2.4% on the list day itself versus −0.7% for the sell
list, and +9.0% versus +5.3% over the previous 20 days (holdout: +2.6%
vs −0.8% and +6.7% vs +2.6%). So "asing borong" describes a move that
already happened; after the list appears, the two lists behave alike.

**Limits.** About 20 months of list history, one market regime (including
the 2026 sell-off); the minimum detectable effect was about 1.2–1.25%
per 5 days, so an effect smaller than that would not show. 149 of the
3,660 list appearances had no price in the research cache (39 in explore,
110 in holdout, mostly delisted or newly listed names), counted here, not
dropped silently. 2 of 63 dates had an empty list and were excluded (see
the amendment above). Daily lists only: this says nothing about foreign
ownership over months or years.

## Pre-registration, 2026-09-26 (batch 1): situations C, I2, I3, S2, I6, I9 and hypothesis H18

Written **before any of these was computed**. Descriptive items (C, I2,
I3, S2, I6, I9) are base rates: no explore/holdout split, no significance
test, not counted in the trial counter, each run once. H18 is a
falsifiable test (+1 trial, 34 → 35). Definitions are frozen; a bug fixed
after seeing numbers is disclosed as a correction. Outcomes for any
"still below / recovered" item are read only after the definition is fixed
here.

**C: "Masih di bawah puncak lama".** Uses `m_recovery_after_fall`'s fall
event (first close ≤70% of the running peak, re-armed only by a new peak).
A stock is *in the situation now* if a fall event triggered at least 252
trading days ago and its latest close is still below that event's
pre-fall peak. Base rate, from earlier events: of events still below the
peak 252 trading days after the trigger, how many were back at or above
the peak 252 trading days later (trigger + 504)? Events with fewer than
200 bars after trigger + 252 are left out; report n. Research prices
(`close`, 5-year cache). Target: none of the 15 famous tickers left with
no situation.

**I2: "Dividen besar dibanding laba".** (a) Verify that the flag
`payout_above_earnings` (payout ratio > 100%) uses the same construct as
H4 (`payout_ratio_from_totals`, prior-year dividend ÷ earnings): recompute
it for every flagged stock and report any that disagree. (b) If they
agree, the situation triggers for the flagged stocks and shows H4's
already-published cut rates for payout ratio above 100% (both phases),
recomputed from the H4 module without changing it. No new outcome test.

**I3: "Dekat puncak, laba menurun".** Trigger as in the flag: close within
10% of the running maximum close in the 5-year cache and earnings[Y] <
earnings[Y-1] (both reported). Evaluated on 1 May of Y+1 for Y = 2022,
2023, 2024 (earnings known by then, as in H5/H10). Outcome over the H5/H10
window (1 May to 4 Sep): share with a negative return and share beating
the median stock. Report n per year and pooled. (The flag uses all-time
high from Sectors; the base rate can only use the 5-year cache high, so it
is a proxy, and disclosed as one.)

**S2: "Langganan suspensi".** From the owned Sectors suspensions file: an
event is a suspension whose reason mentions a price increase
("peningkatan harga" or "kenaikan harga"), 437 events over 229 stocks.
Base rate: of events with at least 365 days of follow-up (event date on or
before 2025-09-11), the share followed by another price-increase
suspension of the same stock within 365 days. Also stock-level: of stocks
with at least one such event, how many have two or more (134 of 229 now).
Sectors-only data, no prices.

**I6: "Dividen rutin".** From `total_dividend[2021..2025]`: a stock has a
streak of N years if it paid a dividend (> 0) in each of the N years
ending Y. Base rate: for N = 1 to 4 and Y = 2022 to 2024, the share that
paid again in Y+1 (> 0), and the share that paid at least as much as in Y.
Report n per cell.

**I9: "Dividen jauh di atas rata-rata sendiri".** Historical version of the
flag with the same multiplier (1.5, from `build_flags.py`, not changed):
`total_yield[Y]` at least 1.5 times the mean of `total_yield[Y-3..Y-1]`
(needs all three). Outcome: `total_dividend[Y+1] < total_dividend[Y]` (a
cut, missing counted as a cut, and reported both ways). Y = 2024 and 2025
where Y+1 is known; report n. Descriptive.

**H18: "Orang dalam beli → harga naik" (falsifiable, +1 trial).** Events:
insider-buy filings in the owned file (`insider_buys_2025_2026`), one
event per stock per 60 days (the first filing, then none for the next 60
calendar days), the filing date counting only if it is a trading day (else
the next). Outcome: adjclose return from the close of the day after the
filing to 20 trading days later, minus the same-window ^JKSE return.
**Power rule, checked before any outcome is read:** count events per phase
(explore = filings in 2025, holdout = 2026). If either phase has fewer
than 100 events, H18 is reported as descriptive only ("belum cukup
data"), with no verdict. If both have at least 100: per phase, average the
excess returns by calendar month, then a one-sample t-test across months
(exact Student-t); CONFIRMED only if holdout mean > 0 with p < 0.05 and
explore has the same sign. Filings that are ownership changes above 10%,
takeovers or tender offers are reported separately by tag (`takeover`),
not dropped. Limits stated up front: 20 months of filings, clustered in
time, and a filing is not proof the person is an "insider" in the popular
sense.

### Results, batch 1 descriptive items, run once 2026-09-26

None is a trial. Each was run once by `m_*.py`; the numbers below are the
printed ones.

**C: still below the old peak.** 703 of 887 cached stocks are in it now
(a fall event at least 252 trading days ago and still below the pre-fall
peak). Of 999 earlier events still below the peak one year after the
trigger, **121 (12.1%) were back at or above it a year later**; 119 of 974
(12.2%) using only exact-date outcomes. Because 79% of the cached stocks
qualify, this is a broad situation, not a rare one; the cache starts in
Sep 2021, so many stocks are still below a 2021–2022 peak.

**I2: payout above 100% (flag vs H4).** The flag `payout_above_earnings`
covers 29 stocks, but only **12 agree** with H4's own construct
(prior-year dividend ÷ earnings, Y = 2025); 10 have an undefined ratio and
7 have a recomputed ratio at or below 100% (for example EAST 1.42 in the
snapshot vs 0.32 recomputed). Recomputed with the H4 module unchanged,
stock-years with payout strictly above 100% saw a dividend cut the next
year in **50 of 82 (61.0%, explore) and 70 of 88 (79.5%, holdout)**.
**Decision:** the situation and the flag are rebased to H4's construct
(2025 dividend x shares / 2025 earnings above 100%). Run on the whole
universe this marks **37 of 306** evaluable stocks now (the 12 above are
only the overlap with the old 29), a definition change disclosed here, made
because the snapshot ratio is trailing and does not match the tested
quantity, not to move a count. The old snapshot version is kept in the code
for the comparison.

**I3: near the high, earnings down.** Stock-years (evaluated 1 May): 2022:
41, 2023: 13, 2024: 14 (68 pooled). Negative return over 1 May to 4 Sep:
41.5%, 30.8%, 28.6% (pooled 36.8%); beat the median stock: 29.3%, 53.8%,
50.0% (pooled 38.2%). Small n, and the 5-year cache high covers only about
7 months in 2022, so it is a proxy for the all-time high the flag uses.

**S2: repeat price-increase suspension.** 437 events, 229 stocks (134 with
two or more). Of 174 events with at least a year of follow-up, **100
(57.5%) were followed by another one within 365 days**; 46 of those 100
within 7 days (consecutive notices can be one episode).

**I6: dividend streaks.** The share that paid again the next year rises
with the streak: 1 year: 87–89%; 2: 91%; 3: 93–94%; 4: 96% (Y = 2024). The
share paying at least as much: 50–62%. Non-payers are missing in the data,
so "missing" counts as "did not pay"; a variant on reported values only
differs by under 1 point.

**I9: yield far above own average (≥ 1.5×).** Y = 2024: 47 stocks; **26
(55.3%) cut the dividend the next year**. Y = 2025: 62 stocks now; no
outcome yet (owned fields end 2025).

### Results, H18 "Orang dalam beli → harga naik", run once 2026-09-26

**H18: NOT confirmed.** Trial count: **35**. The power rule was met (314
events in 2025, 346 in 2026), so the test ran.

| | Explore (2025) | Holdout (2026) |
|---|---|---|
| Events used (of all) | 300 (of 314) | 292 (of 346) |
| Months averaged | 10 | 8 |
| Mean of monthly mean 20-day excess return | +7.2% (t +2.41, p 0.039) | +3.0% (t +1.26, p 0.25) |
| Median event excess return | −2.1% | +0.07% |
| Events beating ^JKSE | 43.3% | 50.7% |
| Without takeover-tagged events | +7.9% (p 0.023) | +3.0% (p 0.23) |

**How to read it.** The explore mean is positive and would pass alone, but
the **median event and the share beating the index are at or below zero**:
a few large winners lift the monthly means, not a broad edge. The
holdout, which decides, is not significant. **In plain numbers:** of 100
stocks after an insider-buy filing, about 43 (2025) and 51 (2026) beat the
index over the next 20 trading days.

**Limits.** 20 months of filings; only 8 holdout months (the latest events
have no full 20-day window); filings are ownership changes, not proof of an
"insider" in the popular sense; the calendar month is that of the filing
date (the pre-registration did not specify it, disclosed here). 14 (explore)
and 54 (holdout) events were dropped for missing prices or an incomplete
window (35 of the 54 lack the window). No winsorising was pre-registered.

**S2 diagnostic added after seeing the counts.** Follow-ups more than 7
days after the event, within 365 days: 72 of 174 (41.4%); the frozen figure
stays 100 of 174 (57.5%).

## Pre-registration, 2026-09-26 (batch 2): E, F1, P3, I7, I8, I10 and H19

Written before any of these was computed. All are descriptive or
disclosure items, not counted in the trial counter, run once each,
**except H19**, which is a falsifiable test (+1 trial) **only if** its
power rule passes; the first step for H19 is a count, with no outcome
computed.

**E: H4 robustness (disclosure, not a new trial).** H4's tercile design is
unchanged. (a) Recompute the payout-tercile cut rates three ways for the
holdout and explore phases: missing next-year dividend counted as a cut
(as now, if that is what H4 does; state it), excluded, and as a separate
bucket. (b) Mechanical-effect check: restrict to stock-years whose earnings
did not fall (`earnings[Y+1] >= earnings[Y]`) and report the cut rate by
payout tercile. (c) Placebo: shuffle payout ratios within sub-sector 1,000
times (seed 20260926) and report where the real holdout rho falls in that
distribution. (d) A note that H10 reused the H5 holdout years for its
second screen (a disclosure item, no computation).

**F1: flag thresholds (disclosure, outcome-free).** For each flag in
`build_flags.py` (payout ratio 1.0; near-high 0.10; yield multiplier 1.5;
LQ45 float 0.25) report the number of stocks flagged at the threshold and
at ±20% of it. No outcomes are read and no threshold is changed. The
rationale text per threshold is written by the lead.

**P3: survivorship, counted from owned data.** From the suspensions file:
count events whose reason mentions delisting (`delisting`, `penghapusan
pencatatan`, `go private`), the distinct symbols, and how many of those
symbols are absent from the 962-company universe (i.e. really gone).
Also the count of universe companies missing from the 887-stock price
cache. Descriptive, to state how many companies the base rates cannot see.

**I7: typical drawdown by sector.** Same method as `m_typical_drawdown`
(1-year cache `close`, one `max_drawdown` per stock) grouped by `sector`
(the 11 IDX sectors) instead of size tercile; median, 25th/75th
percentile, share with a drawdown of at least 30%; groups with fewer than
15 stocks are marked "too few". Descriptive.

**I8: "LQ45 lebih aman?" (contemporaneous association only, like H1).**
LQ45 members (from `indices`) versus the 45 largest non-members by
`market_cap` (a size-matched comparison), over the 1-year cache: median
max drawdown, median annualised volatility, share with a drawdown of at
least 30%. `indices` and `market_cap` are current snapshots, so this is
an association, never a prediction.

**I10: derived rankings (a documented method, not a score), a new builder
`pipeline/appdata/build_derived_rankings.py` writing
`data/app/rankings_derived.json`.** (a) ROE percentile within the stock's
peer group, using `peer_groups.py`'s cascade and minimum group size,
`roe[2025]`, top 20 with group name and size. (b) Dividend consistency:
years of positive `total_dividend` out of 2021–2025, ties broken by the
smaller variation of the dividend, top 20. (c) Earnings streaks: longest
current run of rising annual earnings ending 2025 (all years positive),
top 20. (d) Net insider buying: (sum of buy shares − sum of sell shares
over 2025-01 to 2026-09, from the filings' `holding_before`/`holding_after`)
as a share of `outstanding_shares[2025]`, top 20 net buyers and top 20 net
sellers, filings tagged `takeover` shown separately. Each list carries a
short "Cara menghitung" text and no combined score.

**H19: coal price → coal miners (step 1: count only).** Series: monthly
`Coal` and `Coal (HBA 1)` prices (owned). Count the usable monthly changes
per series. **Power rule:** if fewer than 24, H19 becomes a descriptive chart
(commodity price index beside the equal-weight coal-miner price index, no
verdict). If 24 or more, a test is pre-registered separately before any
outcome is computed: predictor = the month-t change, outcome = the
equal-weight excess return of the 55 listed coal miners in month t+1,
Spearman, with a stated assumption on when each monthly price becomes
public.

### Results, batch 2 (descriptive and disclosure items), run once 2026-09-26

None is a counted trial.

**E: H4 robustness.** H4 excludes stock-years with a missing next-year
dividend (so its published rates are the "excluded" variant; the row counts
match: 450 explore, 540 holdout). Cut rate by payout tercile, low to high:
*excluded (as published)* explore 8.0% / 28.0% / 51.3%, holdout 13.9% /
39.4% / 65.6%; *missing counted as a cut* explore 18.8% / 32.3% / 54.9%,
holdout 21.5% / 43.5% / 71.9%. The rise with payout holds in every variant.
Missing next-year dividend: 43 (explore) and 59 (holdout) rows, with a
lower typical payout (0.31, 0.45). **Mechanical-effect check** (only
stock-years whose earnings did not fall): explore 4.7% / 23.5% / 44.7%,
holdout 11.1% / 34.3% / 66.3%, so the pattern is not just "earnings fell".
**Placebo** (payout shuffled within sub-sector, 1,000 draws, holdout): real
rho +0.441 against a placebo mean +0.025 (sd 0.042, max +0.156); 0 of 1,000
draws reached it. Disclosure: H10's second screen reused the H5 holdout
years. H4's verdict stands.

**F1: flag sensitivity (counts only, no outcomes).** Flags at −20% / as
shipped / +20% of the threshold: payout above earnings (H4 construct,
shipped from 2026-09-26) 56 / 37 / 26 (of 306; the earlier snapshot version
was 56 / 29 / 22 of 326); near the high with lower earnings 12 / 14 / 15 (of 852); yield far
above average (multiplier 1.2 / 1.5 / 1.8) 122 / 89 / 75 (of 462); LQ45
with low float 10 / 12 / 17 (of 45). Counts move a lot for the payout and
yield flags, which is why the app states the rule with each flag.

**P3: survivorship.** The owned suspensions file has only 3 delisting
events over 2 symbols, and 1 of them (HDTX) is absent from the 962-company
universe. **So our data cannot count how many companies disappeared;** the
universe holds only listed companies. 75 universe companies are missing
from the 5-year price cache (49 from the 1-year cache), so their outcomes
are not in the price-based base rates either. Every base rate is therefore
"of companies that are still listed", which is likely optimistic.

**I7: typical drawdown by sector** (1-year, 913 stocks; median max
drawdown, share with 30%+): Financials −41.5% (72%), Healthcare −41.6%
(81%), Basic Materials −45.8% (73%), Consumer Non-Cyclicals −45.6% (81%),
Industrials −49.7% (77%), Infrastructures −50.9% (84%), Technology −51.3%
(88%), Energy −51.8% (83%), Consumer Cyclicals −52.6% (88%), Properties
−54.0% (86%), Transportation −57.6% (95%). Every group has 37+ stocks.

**I8: LQ45 vs the 45 largest non-members** (association only): median
max drawdown −44.7% vs −46.0%; median annualised volatility 0.49 vs 0.55;
share with a 30%+ drawdown 82.2% vs 80.0%. LQ45 membership is not
associated with a smaller fall, only slightly lower volatility. `indices`
is a current snapshot, and a null `indices` was treated as non-member.

**I10: derived rankings** written to `data/app/rankings_derived.json`
(ROE percentile within peer group: 837 evaluable; dividend consistency: 474,
the top 20 all 5 of 5 years with zero variation; earnings streaks: 345,
longest run 4 years shared by 54 stocks, so the top 20 is an alphabetical
cut inside a 54-way tie; net insider: 382 stocks, 378 after the exclusion below). **Decisions:** net
changes above 100% of outstanding shares (PACK +4.22×, MAPI +1.23×, BIKE
−1.37×, LOPI −1.08×, and takeover-tagged PACK) are likely artefacts or
takeover-scale events, so they are kept out of the ranked lists and
reported separately as `excluded_over_100_percent`. The large ties will be
stated on the page instead of ranking within them.

**H19: coal price and coal miners: descriptive only, no test, no trial.**
The owned Coal and HBA series have 26 first-of-month points, so 25 monthly
changes (37 if the two-per-month points from March 2025 are counted, which
would mix spacings). That passes the pre-registered count of 24 by one
change, but a rank correlation on 25 points can only detect a very strong
relationship (roughly |rho| above 0.5), and the outcome month depends on an
unverified publication lag. **Decision (before any outcome was computed):**
H19 stays a descriptive chart, the trial count stays 35.

---

*(Next entries land here as later hypotheses are tested: see the
hypothesis register in `docs/PLAN.md` §6 for what's queued.)*

## Pre-registration, 2026-09-27: stress tests of the newest hypotheses and situations

Written before any of the checks below was computed. Purpose: find where the
recently added results (H6, H18 and the situations C, S2, I2, I3, I6, I9) are
fragile, and fill the gaps. **None of this is a new trial and none changes a
verdict by itself.** A verdict changes only if the decision rule stated here
is met, and every variant examined is reported, including those that favour
the belief. No thresholds of the app flags change. Owned data only, no Sectors
calls. Each module is run once. Bootstrap replicates B = 2,000, permutation
shuffles 10,000, seed 20260927, Wilson 95% intervals for proportions.

**ST0: uncertainty for every base rate the app quotes.** For each proportion
shown as "N dari 100" (recent spike, price-spike suspension, S2, C, I2 by
phase, I3, I6 by streak, I9, loss turnaround, earnings two-year decline,
earnings more than doubled, IPO by board): count, n, Wilson 95% interval. For
event-based rates where one stock contributes several events (C, S2, recent
spike): a cluster bootstrap that resamples stocks, and the number of distinct
stocks. Output a file the app can read (`data/app/base_rate_uncertainty.json`).
Rule: an interval wider than 20 points is marked "lebar" and the page says so.

**ST1: situation C (still below the old peak).** Report the recovery rate
(a) by trigger year, (b) with one event per stock (the first), (c) by size
tercile (market cap, a snapshot, description only), (d) with the trigger drop
at -20% and -40% instead of -30%, and the wait at 126 and 378 trading days
instead of 252. Fragile if the rate varies by more than 10 points across
trigger years, or the one-per-stock rate differs from the pooled rate by more
than 5 points, or any sensitivity variant moves it by more than 5 points.

**ST2: situation S2 (repeat suspension).** (a) One event per stock; (b)
leaving out the three stocks with the most events; (c) by year of the first
event; (d) the follow-up window at 180 and 730 days; (e) **a baseline**: among
stocks with any price-increase suspension, the share that had one in an
arbitrary 365-day window, computed over the same calendar span, so that
"57 of 100" can be compared with a stock's ordinary chance. Fragile under the
same 5/10-point rules; the baseline is reported as a comparison, with no
threshold.

**ST3: baselines for I2, I3, I6, I9.** A statement like "55 of 100 cut the
dividend" means little without the ordinary rate. Report (a) the cut rate among
all dividend payers of the same year Y (Y = 2024; and pooled 2022 to 2024 where
the fields allow) next to I9 and I2; (b) for I3, the share of all evaluable
stock-years with a negative 1 May to 4 Sep return and the share beating the
median stock, per year, next to the 68 flagged; (c) for I6, the overall share of
payers that paid again next year, per year. Each with a Wilson interval and the
difference in points with its interval. Rule: if the interval of the difference
includes 0, the app copy must not imply the situation raises or lowers the
ordinary rate (it currently says only the rate).

**ST4: H18 (insiders buy).** Variants, each in explore and holdout: (a)
winsorised event returns at the pooled 1st and 99th percentiles; (b) dedupe
window 30 and 90 days instead of 60; (c) horizons 5, 10 and 60 trading days;
(d) benchmark = the equal-weight median return of the cached universe over the
same window instead of ^JKSE; (e) excluding the lowest market-cap tercile; (f)
event-level cluster bootstrap by stock for the mean and the median; (g) the
minimum detectable effect for each phase. 17 variants in total (a to f, each
per phase, are counted). **Decision rule:** H18 stays NOT confirmed unless the
holdout mean is above 0 with p < 0.05 and the median is above 0 in the
holdout under the primary definition; variants are reported as sensitivity,
never as a second chance. If a variant is significant, it is reported as
"significant only under a variant not pre-registered".

**ST5: H6 (foreign buying).** (a) A permutation test: shuffle the buy/sell list
labels within each date 10,000 times and report where the real holdout and
explore spreads fall; (b) horizons of 1, 10 and 20 trading days after D+1
(descriptive); (c) top 10 buys versus top 10 sells; (d) equal-weight universe
benchmark instead of ^JKSE; (e) excluding dates within the last 3 trading days
of Feb, May, Aug and Nov (index-review windows, dates inferred and labelled
so); (f) the same comparison using only the net foreign-flow amount above its
list median (a large-net-inflow subset). Same decision rule as ST4: H6 stays NOT
confirmed unless the pre-registered primary result is significant.

**Gap fills that follow (decided now, not from the results).** (1) The app shows
the ST0 interval next to each "N dari 100" in the page's basis line. (2) Where ST3
finds an ordinary rate, the page states it beside the situation's rate. (3) Any
"fragile" outcome from ST1 or ST2 is written on that situation's page in the
Batasan list. (4) Every result is added to this file under a Results heading, with
the count of variants examined.

### Results, stress tests, run once 2026-09-27 (`stress_*.py`, `build_base_rate_uncertainty.py`)

Every frozen figure was reproduced exactly before any variant (C 121/999, S2
100/174, I9 26/47, I2 50/82 and 70/88, H18 explore +7.2% p 0.039 and holdout
+3.0% p 0.25, H6 explore +0.05% and holdout -0.03%). No verdict changed. The
modules were executed a few times while being written; no definition changed
after numbers were seen. Counts: ST0 80 rates; ST1 7 variants; ST2 6; ST3 22
comparisons; ST4 18 phase-cells (the pre-registration said 17, an arithmetic
slip in the text, all cells were run); ST5 16 phase-cells.

**ST0.** 80 rates with Wilson 95% intervals (file `data/app/base_rate_uncertainty.json`),
39 marked wide (more than 20 points). Stock-resampled intervals: C 121/999,
Wilson 10.2 to 14.3, stock-resampled 9.9 to 14.4 (799 stocks); S2 100/174,
50.0 to 64.6, 50.6 to 63.3 (97 stocks); recent spike 1,762/3,081, 55.4 to 58.9.
I9 26/47: 41.2 to 68.6 (wide). I3 pooled 25/68: 26.3 to 48.6 (wide); every I3
cell and every IPO-by-board cell is wide.

**ST1 (C), FRAGILE by the pre-registered rule.** Recovery by trigger year: 2021
9/129 (7.0%), 2022 41/454 (9.0%), 2023 49/272 (18.0%), 2024 22/144 (15.3%), a
range of 11.0 points (rule: more than 10 points). One event per stock 96/799
(12.0%, -0.1 point). By size tercile (description only): smallest 7.7%, middle
10.7%, largest 19.5%. Trigger -20%: 157/1,283 (12.2%); -40%: 78/778 (10.0%);
wait 126 days: 112/1,131 (9.9%); wait 378 days: 90/885 (10.2%). The one-per-stock
and sensitivity rules were not triggered. The outcome horizon stays 252 bars after the wait.

**ST2 (S2), FRAGILE by the 5-point rule.** First event per stock 66/97 (68.0%,
+10.6 points). Without the three stocks with the most events (MGLV, UDNG, INET;
a four-way tie, broken alphabetically) 89/162 (54.9%, -2.5). Follow-up window
180 days: 175/394 (44.4%, -13.1). A 730-day window has no eligible event, and a
by-year split is measurable only for 2025. **A finding not in the plan:** all 437
price-increase suspensions in the data fall between 2025-01-08 and 2026-09-11 (323
in 2025, 114 in 2026), so S2 describes one 20-month regime, and the app's earlier
"since 2018" wording was wrong (fixed). The pre-registered baseline (share of the
229 stocks with an event in an arbitrary 365-day window: mean 83.5%) is
**not informative**: the stocks are selected for having events in that same span,
so it cannot be compared with 57.5%. It is not shown in the app.

**ST3 (22 comparisons; the interval of the difference includes 0 in 13).** I9
55.3% versus all 2024 dividend payers 46.0% (157/341): +9.3 points [-5.8, +23.5],
includes 0 with missing-as-cut, and vs 37.8% (112/296) with missing left out
[+2.3, +31.8] excludes 0; the answer depends on the convention. I2: explore 61.0%
versus payers of 2021-22 29.0%, +31.9 [+20.3, +42.5]; holdout 79.5% versus 39.6%,
+40.0 [+29.6, +48.1]; both exclude 0. I3: negative-return share 36.8% versus
35.5% (911/2,563) of all stock-years, +1.2 [-9.4, +13.2]; beat-the-median 38.2%
versus 48.7%, -10.4 [-21.2, +1.6]; 7 of 8 per-year cells include 0. I6: streak 2
includes 0 in all three years; streak 3 in 2024 (+7.0 [+1.9, +11.7]) and streak 4
in 2024 (+9.2 [+4.1, +13.7]) exclude 0. **Rule triggered** (the app copy must not
imply the situation raises or lowers the ordinary rate) for I9 under its main
convention, 7 of 8 I3 cells and I6 streak 2. The app now shows the ordinary rate
beside I3 and I9.

**ST4 (H18), stays NOT confirmed.** Mean of monthly means (p), explore /
holdout: primary +7.24% (0.039) / +2.97% (0.247), holdout median +0.07%;
winsorised +5.13% (0.010) / +3.16% (0.209); refractory 30 days +7.07% (0.017) /
+2.37% (0.296), 90 days +7.54% (0.043) / +1.75% (0.469); horizon 5 days +0.01%
(0.996) / +1.52% (0.136), 10 days +3.18% (0.124) / +3.08% (0.116), 60 days
+22.42% (0.027) / +10.41% (0.025; 213 events, 6 months, median +5.04%);
equal-weight benchmark +8.71% (0.040) / +2.03% (0.363); without the lowest size
tercile +8.62% (0.091) / +3.49% (0.174). Stock-resampled: explore event mean
+8.12% [+3.03, +15.04] but median -2.08% [-3.12, -0.33]; holdout mean +1.95%
[-0.54, +4.34], median +0.07% [-1.49, +1.66]. Minimum detectable effect (5%
level, 80% power, an assumption made here): 9.46% (explore, 10 months), 7.66%
(holdout, 8 months); the observed holdout was +2.97%, so the holdout was
underpowered for anything but a large effect. Rule: holdout p 0.247, so not
confirmed. Six cells reach p < 0.05 and are labelled "significant only under a
variant not pre-registered": winsorised explore, refractory 30 and 90 explore,
horizon 60 explore and holdout, equal-weight benchmark explore. The 60-day
horizon is the one to watch: it is significant in both phases, on 6 holdout
months. It is outside what was registered, and it stays a lead for later, not a
finding.

**ST5 (H6), stays NOT confirmed.** Explore / holdout spread (p): primary +0.048%
(0.869) / -0.027% (0.961). Permutation test (10,000 shuffles of the list labels
within each date): the real spread sits at percentile 54.5 (p 0.90) and 47.3 (p
0.95). Horizon 1 day -0.197% (0.298) / +0.021% (0.927); 10 days -0.064% (0.908) /
+0.341% (0.687); 20 days -0.103% (0.914) / +0.424% (0.690). Top 10 versus top 10
-0.426% (0.549) / -0.312% (0.707). Without index-review windows (dates inferred)
+0.062% (0.850) / -0.024% (0.965). Largest-net-inflow subset -0.509% (0.323) /
+0.088% (0.895). No variant has p < 0.05. The equal-weight benchmark cancels out
of a same-date buy-minus-sell spread by construction, so it is a near no-op.

**Gap fills made in the app.** Intervals ("kisaran wajar") on the old-peak,
repeat-suspension and price-spike pages; the ordinary rate beside I3 and I9;
"fragile" lines in the Batasan of C and S2; the suspension span corrected to
January 2025 to September 2026; the H6 permutation and the H18 non-registered
variants disclosed on their pages.

## Pre-registration, 2026-09-27: H18b "Orang dalam beli → harga naik dalam 60 hari" on an independent sample (a falsifiable hypothesis, +1 trial if it runs)

Written before any new filings were pulled and before any outcome is computed.
**Why it exists.** In the H18 stress tests (ST4) the 60-trading-day horizon was
significant in both phases (explore +22.4%, p 0.027; holdout +10.4%, p 0.025;
holdout median +5.0%), but it was not pre-registered and rests on 6 holdout
months. That result was found by looking at the 2025-2026 data, so those months
cannot confirm it. H18b tests the same idea on data that has not been seen.

**Sample.** Insider buy filings dated 2021-01-01 to 2024-12-31 (the earlier
pull covers 2025-01-01 onward only). It runs only if the Sectors filings endpoint
returns filings for that period (a one-credit size probe decides). If it returns
none, H18b is dropped, is not counted as a trial, and this is stated.

**Everything else is copied from H18 unchanged:** the buy-filing definition,
one event per stock per 60 days, entry at the close after the filing date's next
trading day, excess return over ^JKSE, `adjclose`, events without prices dropped
and counted. **Only the horizon differs: 60 trading days.**

**Primary statistic.** Mean over calendar months of the month's mean 60-day
excess return; t-test across months with Newey-West standard errors, lag 2
(60-day windows of adjacent months overlap). Months are those of the filing date.

**Split.** None: the whole 2021-2024 sample is a single independent holdout,
because the exploration was done on 2025-2026.

**Power rule (checked with a count before any outcome is computed).** At least 24
calendar months with 10 or more events each. Otherwise H18b is not run and not counted.

**Decision.** CONFIRMED only if the mean is above 0 with p < 0.05 (two-sided) and
the median event excess return is above 0. A significant negative result is
reported as the opposite. Anything else is NOT confirmed, with the minimum
detectable effect stated. Trial counter 36 if it runs.

**Robustness (reported, not extra trials).** Winsorised at the pooled 1st and 99th
percentiles; equal-weight universe benchmark; events without takeover-tagged
filings; stock-resampled bootstrap interval for the mean and median; the same test
by calendar year. Survivorship: the price cache holds only stocks still listed, so
delisted names are missing (disclosed; a bias toward better outcomes).

### H18b outcome, 2026-09-27: not run, not counted

The one-credit size probe (`docs/credit_ledger.md`, 2026-09-27) found 76 insider buy
filings for 2021-01-01 to 2024-12-31, against the 24 months with 10 or more events
each that the pre-registration requires. The power rule fails, so H18b was **not run
and is not a trial** (the counter stays at 35). No outcome was computed. The 60-day
result from ST4 therefore stays an unconfirmed lead: it can only be tested on
filings that do not exist yet, so the earliest independent check is after the
2026-2027 filings accumulate, which is after this project's freeze.

## Pre-registration, 2026-09-27: V: the three "proven" price-outcome results re-checked on Sectors' own closing prices

Written before any Sectors closing price was pulled. **Purpose.** The three
findings that held up on price outcomes (cheap earnings multiple, small size,
high dividend yield: H5 and H10) were measured on a free public price history,
which is a weakness for a Sectors-track project even though the sample check
(20 symbols) matched. V repeats their **holdout** with Sectors' prices. This is a
replication of tests already counted, not a new trial: the trial counter stays
at 35 whatever it shows.

**Data.** MCP tool `fetch-daily-close` (1 credit per page of 30 tickers; about
32 pages, about 128 credits for four dates) for the four dates the research
module's nearest-price rule selects: 2025-04-30 and 2025-09-04 (formation year
2024), 2026-04-30 and 2026-09-04 (formation year 2025). The explore windows
(2023 and 2024) are not re-pulled (another 128 credits); this is stated as a limit.
Cap: 140 credits. If any date returns more than 34 pages or covers fewer than 95%
of the tickers in the universe, the pull stops and is reported.

**Method.** The H10 holdout is run again with its own code, unchanged (same
formation fields, same filters, same sector-neutral rank statistic, same p-value),
on a price table built from the Sectors closes, for the three features
`earnings_yield`, `size` and `total_yield`. Sectors closes are not adjusted for
dividends, so two references are also printed: (a) the research history on its
dividend-adjusted `adjclose` (the frozen H10 figure, reproduced first) and (b) the
research history on its unadjusted `close`, the like-for-like comparison. The
difference between (b) and the Sectors run isolates the price source; the
difference between (a) and (b) isolates dividend adjustment.

**Decision (per feature, fixed now).** "Replicated on Sectors prices" if the
holdout statistic has the same sign as the frozen H10 holdout and p < 0.0167 (0.05
divided by the three checks). Otherwise "not replicated on Sectors prices", with
the numbers. If (b) and the Sectors run disagree by more than 0.02 in the
statistic, the price source itself is reported as inconsistent. Every result is
published whichever way it falls; the app's "Terbukti" label for a feature
changes only through a stated rule (it is annotated, not removed, unless the
Sectors run shows the opposite sign with p < 0.0167).

### Results, V (Sectors closes), run once 2026-09-27 (`v_sectors_recheck.py`)

Data: 129 pages of `fetch-daily-close` (955, 954, 957 and 962 tickers on the four dates; 129
credits, running total 864 of 1,000). H10's holdout was run again with its own code on three price
tables. **Not a trial; the counter stays at 35.** Universe rows with a Sectors close: see the JSON.

| Feature | (a) research adjclose | (b) research close, like-for-like | (c) Sectors closes | Rule |
|---|---|---|---|---|
| earnings yield (cheap P/E) | rho +0.120 | rho +0.070 (n 1,246) | **rho +0.080, t +2.85, p 0.0043 (n 1,274)** | replicated |
| size (small companies) | rho -0.199 | rho -0.225 (n 1,549) | **rho -0.226, t -9.25, p below 0.0001 (n 1,598)** | replicated |
| dividend yield | rho +0.078 | rho +0.004 (n 701) | **rho +0.010, t +0.27, p 0.79 (n 709)** | **not replicated** |

The price source is consistent: |rho(b) - rho(c)| is at most 0.01 for all three (limit 0.02), so
Sectors' closes and the research closes agree. **The dividend-yield result does not survive when
dividends are left out of the return.** It is present on the dividend-adjusted series (a) and absent
on the same history without adjustment (b) and on Sectors' prices (c). The likely reading
(inferred): a stock that pays a high yield has that income counted in a dividend-adjusted return, so
part of the "proven" association is the dividend itself, not the price. By the pre-registered rule the
label is annotated, not removed (the Sectors sign is the same and not opposite). The value result is
weaker on prices alone (+0.12 to +0.08) but stays significant; the size result is, if anything,
stronger. Only the holdout was repeated; the explore windows were not re-pulled.

## Rule amendment, 2026-09-27: the "no combined score" constraint, narrowed

Before this date, `CLAUDE.md`'s hard constraint read: "No score or combined
verdict across findings. Each finding stands on its own evidence and its own
limits." That wording is now:

> No rating, no buy/sell/hold or "good stock" score, and never a blend of
> findings' verdicts. A count or combination of risk signs may be shown only
> if a pre-registered test confirmed it on the holdout. Each sign always
> stays visible on its own, and labels describe states, never actions.

**Why.** The market page (Pasar) and a stock page's Kesimpulan summary need
to answer "so what" for a user today, which single, independent findings
cannot do on their own: they are each honest and correct, but they don't
combine into a reading of the current situation. The original rule's purpose,
preventing an invented, untested "3 of 4 signals look bad" measure from
reaching the product, is unchanged. What changes is that a count or
combination is now allowed **once it has itself been pre-registered and
tested against held-out data**, exactly like any other finding in this log.
It is never a rating, never a buy/sell/hold call, and it never replaces the
individual signs, which stay visible on their own regardless of the count's
result.

**What this does not change:** H15's null result (`pipeline/hypotheses/
h15_technical_fundamental_interactions.py`, cited at line 1167 above) tested
whether combining a technical and a fundamental signal predicts *returns*
better than either alone; all three pre-registered interactions were null.
That result stands as written. The amendment governs a different kind of
claim: a count of risk signs predicting a risk event (a large fall, a
suspension, a dividend cut), not a return-prediction score.

**What it enables, each its own pre-registered trial:** R2a (does the number
of active risk signs on a stock predict a subsequent large fall, tested
against the strongest single sign), R2b (three specific sign pairs, each
tested against its own two signs), and T1 (a market-condition label,
"tertekan" or not, tested against subsequent market moves). Each ships only
if its own test passes on holdout data; each that fails is published as a
null, same as every other result in this log.

## Pre-registration, 2026-09-27: T1 (market condition, +1 trial), R1 (warning overlap, descriptive) and R2a (does the count of active warnings matter, +1 trial if common support qualifies)

Written before any of these three is run: this section locks the definitions,
splits and pass rules. Per the amendment above, T1 and R2a are the first two
tests of the count/combination rule it created. Plan reference:
`kind-juggling-hoare.md` §5. Data already pulled for these: M1 (full IHSG
daily history, `data/raw/ihsg_2026-09-27.json`, `docs/credit_ledger.md`
2026-09-27, 1,861 trading days, 2019-01-02 to 2026-09-27); the universe sweep
(`data/raw/universe_2026-09-12.json`, 83 fields, 962 companies); and the
existing dev-time research price history (`pipeline/dev/`, never shipped, per
`CLAUDE.md`'s standing rule) already used by H5/H10/H17/etc. No new Sectors
pull is required to run any of the three; none is being requested here.

**Common protocol, all three (plan §4), restated as this project's binding
rules, not just as this pre-registration's):**
1. Predictor before outcome: every predictor here is computable using only
   data available strictly before the day it is measured on.
2. Lag guard: yearly `field[YYYY]` columns become usable on 1 May of the
   following year, enforced by the existing pytest lag-guard tests; R1/R2a's
   "loss year" and "earnings down two years" warnings use this rule.
3. IDX calendar: "previous trading day" comes from the Sectors-sourced IHSG
   calendar (`ihsg_2026-09-27.json`'s date list, from 2019; for dates before
   that, `idx_total.json`'s calendar, from 2021), never from the previous row
   of the research-price file, which can have gaps that don't correspond to
   real non-trading days.
4. Embargo: a formation counts only if its whole outcome window ends before
   the explore/holdout boundary. 20 trading days for T1, 126 trading days for
   R2a. A formation whose outcome window crosses the boundary is dropped and
   the drop is counted and reported.
5. Run once: each of the three below is computed exactly one time on real
   data, after this text is committed. Results are reported by explore vs.
   holdout, by year, and (T1 only) by ARB-7% regime; nulls get equal weight
   and equal visibility with confirmations.
6. Standard errors: moving-block bootstrap (20-day blocks) for the T1 market
   series; stock- and date-clustered bootstrap for the R1/R2a panel. Reuses
   `pipeline/hypotheses/_stress_common.py` and `pipeline/stats.py` rather than
   a new implementation.
7. Missing outcomes (R2a; a stock suspended or delisted inside its 126-day
   window) are categorised as suspended, delisted or unknown, not silently
   dropped. The primary result carries the last close forward through the
   window; an exclusion-of-missing run and a worst-case -50%-at-gap run are
   also reported.
8. Asymmetry: where realised volatility alone could produce a result, the
   statistic compares down minus up (T1's A-B, R2a's D-U), not either alone.

### T1: "Kondisi pasar: tertekan" (+1 trial)

**State at close t**, using IHSG data up to and including t only (no
look-ahead). The market is `tertekan` if **either**:
- IHSG's close is >=10% below its running peak-to-date **and** below its
  own 200-trading-day moving average; **or**
- its 20-trading-day realised volatility (std. dev. of daily log returns) is
  above the 90th percentile of that same volatility measure's own history up
  to t (an expanding percentile, not a fixed-window one).

**Burn-in, verified today on M1 before writing this rule down (plan required
this check to pass before pre-registering, and it did):** the state is
computed only from trading day 250 onward. Day 250 of `ihsg_2026-09-27.json`
is **2020-01-08**. The COVID crash (verified low: 2020-03-24, IHSG 3,937.632,
trading-day index 303) falls 53 trading days after burn-in ends, not at its
edge, so it sits fully inside the post-burn-in period and is available for
both explore and (via later years) generalization checks, exactly as the plan
required ("If it fails, stop and re-plan" -- it did not fail).

**Split.** Explore: burn-in end (2020-01-08) through 2022-12-31. Holdout:
2023-01-01 onward, after the 20-day embargo at the boundary.

**Outcomes, over t+1 to t+20 trading days:**
- A = P(IHSG falls a further >=5% from its close at t, at any point in the
  window)
- B = P(IHSG rises >=5% from its close at t, at any point in the window)

**Primary statistic.** (A-B) computed separately on `tertekan` days and on
normal days, within the holdout; the test statistic is the difference between
those two (A-B) values.

**Pass.** CONFIRMED only if, on the holdout: the (A-B tertekan) minus (A-B
normal) difference is > 0, its bootstrap CI (moving-block, 20-day) is
entirely above 0, **and** the same-signed difference also holds in explore.
Anything else is NOT confirmed and is published as such, with the numbers.

**The fail state is designed now, before any result exists:** if NOT
confirmed, the product still shows the percentile tiles (peak distance,
200-day average distance, realised volatility percentile) as a plain
description of where IHSG sits today, with no state label implying
predictive meaning.

**Robustness (reported, not additional trials).** The same test excluding
the ARB-7% auto-reject-band period (dates to be verified against IDX before
reporting, not assumed); with 8% and 12% peak-distance thresholds in place of
10%.

### R1: overlap between the eight warnings (descriptive, not a trial)

**Panel.** Stock x month-start, from 2022-05-01 (the earliest month
`outstanding_shares[YYYY]` supports under the 1 May lag rule, per the plan's
R2 size-control note). Each cell is a binary vector over the eight warnings
below, computed as of that month-start using only data available before it.

**The eight warnings, each already precisely defined by an existing module or
finding in this log (reused, not redefined):**
1. fell 30%+ from peak (existing drawdown definition, `m_typical_drawdown.py`)
2. long below peak (existing definition, `m_long_below_peak.py`)
3. up 40%+ in 20 trading days (existing definition, `m_recent_spike.py`)
4. loss year (most recent lagged `earnings[YYYY]` < 0)
5. earnings down two years running (two most recent lagged `earnings[YYYY]`
   both below the prior year)
6. payout in H4's top tercile (`h4_payout_dividend_cuts.py`'s existing
   tercile cut)
7. near peak with falling earnings (existing definition,
   `m_near_peak_earnings_decline.py`)
8. yield spike (existing definition, `m_yield_spike_cut.py`)

**Merging rule, fixed now.** For every pair of warnings, compute the Jaccard
index of their active-month sets across the whole panel. Any pair with
Jaccard > 0.5 merges into whichever of the two is more specific (the smaller
active-month count), and the merged pair is reported as one warning with both
original names noted. This is descriptive only: R1 produces the overlap
table and the (possibly-merged) warning list that R2a and R2b consume; it
does not itself carry a pass/fail rule and is not counted as a trial.

### R2a: does the number of active warnings matter? (+1 trial, conditional)

**Cells.** Size tercile (by `outstanding_shares[YYYY]`, lagged to 1 May, with
the plan's flag rule: a stock-year whose share count changes >=50% is flagged,
takes its size from the following year, and the flag is counted and reported)
x 60-trading-day realised-volatility tercile, both measured strictly before
formation.

**Common support, checked before any outcome.** A cell counts only if each of
the 0, 1, 2 and 3+ active-warning groups (using R1's merged warning list) has
>=30 observations in **both** the explore and holdout periods. **If fewer
than 2 cells qualify, R2a is not run as a trial; it becomes descriptive
(each warning shown alone, no count claim), and the trial counter does not
move.** This check is done first and reported before the rest of R2a
proceeds, so the conditional outcome is known before the pass/fail statistic
is computed.

**Outcomes, within 126 trading days of formation:**
- D = P(a fall of >=30% from the formation price, at any point in the window)
- U = P(a rise of >=30% from the formation price, at any point in the window)
- L = suspended or delisted inside the window (reported, not folded into D)

**Split.** Explore: formations from 2022-05-01, ending 126 trading days
before 2024-01-01. Holdout: formations from 2024-01-01 onward, after the
126-day embargo at the boundary.

**Pass.** CONFIRMED only if, on the holdout, cell-weighted (weighted by each
qualifying cell's observation count):
1. D-U rises monotonically with the active-warning count (0 < 1 < 2 < 3+); **and**
2. D-U for the 2+ group beats D-U for the single strongest warning, where
   "strongest" is chosen using **explore data only**, before looking at the
   holdout, so the choice cannot be reverse-engineered from the holdout result.

Both conditions must hold; either failing makes R2a NOT confirmed, published
with the numbers. If confirmed, this is the test that licenses the
Kesimpulan's "N tanda risiko aktif" line under the amended combination rule
above; if not, the Kesimpulan falls back to listing warnings individually, in
explore-strength order.

**Trial counter if both run as trials:** T1 makes it **36**; R2a, if common
support qualifies, makes it **37** (matching the plan's stated total). If
R2a's common-support check fails and it turns descriptive, the counter stops
at 36 for this batch. R1 is never counted, in either outcome.

### Results, T1, R1 and R2a, run once 2026-09-27 (`t1_market_state.py`, `r1_warning_overlap.py`, `r2a_warning_count.py`)

The plan's own schedule (`kind-juggling-hoare.md` §8) put this run on 2026-09-28,
one day after pre-registration; run same-day instead on the user's explicit
instruction ("Yes moveon and start right now"), after the text above was
already committed to git history, so the rule still came before the result.

**T1: NOT confirmed.** IHSG series: 1,861 trading days, 2019-01-02 to
2026-09-25 (`data/raw/ihsg_2026-09-27.json`). Burn-in ends 2020-01-08, as
verified before pre-registering. 1,592 formations with a complete 20-day
window; 20 dropped for insufficient trailing data, 20 dropped at the
2023-01-01 embargo. Explore: 711 formations (187 tertekan). Holdout: 861
formations (256 tertekan).

| | (A-B \| tertekan) - (A-B \| normal) |
|---|---|
| Explore | -0.097 |
| Holdout | +0.017, 20-day moving-block bootstrap CI [-0.345, 0.380] (2,000 replicates) |

Explore and holdout disagree in sign, and the holdout CI straddles zero by a
wide margin: the decision rule's three conditions (holdout > 0, CI entirely
above 0, explore same sign) all fail. **This is a clean null**, not a near
miss: even taking holdout's statistic alone as noisy-but-positive, explore
pointed the opposite way. Robustness (not a second trial): the holdout
statistic stays small and sign-unstable at 8% (+0.010) and 12% (-0.022) peak
thresholds too, so this isn't an artifact of the 10% cutoff specifically. The
ARB-7%-period exclusion was NOT run, as disclosed in the pre-registration:
that regime's dates were never verified against IDX. **Trial counter: 36.**
Shipped: the percentile tiles (peak distance, 200-day-average distance,
volatility percentile) as a plain description of where IHSG sits, with no
predictive state label -- exactly the fail-state design written before this
result existed.

**R1 (descriptive).** Panel: 43,881 stock-months, 887 stocks, 53 months
(2022-05-01 to 2026-08-01 formation, using `data/dev_cache/prices_5y.json`
+ `data/raw/universe_2026-09-12.json`, both already owned, zero new Sectors
calls). Active-month shares: fell_30 68.9%, long_below_peak 57.3%, loss_year
25.2%, earnings_down_2y 10.6%, payout_top_tercile 11.1%, spike_40_20 3.7%,
near_peak_earnings_decline 2.0%, yield_spike 2.0%. The very high fell_30/
long_below_peak shares are consistent with, not contradicted by, this
project's own earlier base rate (`m_typical_drawdown.py`'s median full-year
drawdown already sat in the -40% to -66% range) and with the real ~40%
IHSG fall from its January 2026 peak (M1, above) reaching even blue-chip
names by mid-2026 (spot-checked: BBCA reads fell_30=False for the whole
panel except 2026-07-01, where it flips True). **One merge** (Jaccard >
0.5): `fell_30` (30,220 active months) merges into `long_below_peak`
(25,153 active months, the more specific of the pair, Jaccard 0.681); no
other pair exceeds 0.5. **Final list for R2a/R2b, 7 warnings:**
long_below_peak, spike_40_20, loss_year, earnings_down_2y,
payout_top_tercile, near_peak_earnings_decline, yield_spike.

**R2a: fewer than 2 qualifying cells -- DESCRIPTIVE, not a trial. Trial
counter unchanged at 36.** Outcomes computed for 38,559 of 43,881 rows
(5,322 dropped: window runs past the price cache's own end, 2026-09-09).
Explore: 10,285 formations; holdout: 23,496; 4,778 dropped at the
2024-01-01 embargo. Common support (size tercile x 60-day-volatility
tercile, >=30 observations per active-warning bucket in both periods):
**zero of nine cells qualified.** The binding constraint is the 3+ bucket:
in explore, no cell ever reaches 30 stock-months with 3 or more of the 7
final warnings simultaneously active (the largest is 8, in the largest-size
/ highest-volatility cell) -- inspected directly, not assumed, before
concluding this. This is close to the failure mode the plan's own
methodology discussion anticipated before any data was pulled ("R2's
size/volatility controls... common-support empty cells"): the warnings are
disjoint enough (a recent 40% spike and a 250+-day drawdown rarely coincide
on the same stock-month) that 3+ simultaneous warnings is simply a rare
event, not a common-support artifact of a badly chosen cell design.

Because R2a turned descriptive, no count/combination claim ships (per the
amended combination rule, above): each warning is shown on its own. Pooled
(not cell-weighted) single-warning D-U, for reference:

| Warning | Explore D-U (n) | Holdout D-U (n) |
|---|---|---|
| long_below_peak | -0.085 (1,614) | -0.236 (16,733) |
| spike_40_20 | +0.188 (191) | -0.153 (1,183) |
| loss_year | -0.004 (2,819) | -0.225 (5,699) |
| earnings_down_2y | n/a (0) | -0.261 (3,629) |
| payout_top_tercile | -0.128 (1,070) | -0.117 (2,662) |
| near_peak_earnings_decline | +0.153 (72) | -0.101 (535) |
| yield_spike | n/a (0) | -0.215 (517) |

These are descriptive, not tested against a decision rule, and every
holdout D-U here is negative (a large fall was, on the whole, more common
than a large rise following every one of the 7 warnings in the 2024+
window) -- unsurprising given the same IHSG fall context as R1, and not
itself evidence that any one warning "works," since there is no benchmark
rate for a stock with no active warnings shown alongside it here (that
comparison is exactly what R2a's cell design was for, and it didn't
qualify). L (suspension announced inside the 126-day window,
`data/raw/suspensions_2026-09-13.json`): 0 in explore, 2,103 of 23,496 in
holdout (9.0%) -- consistent with the 2025-2026 concentration already
visible in that file's own date distribution, and with "delisted" being
unobservable in this dataset by construction (survivorship: every stock
in the panel is, by definition, still in the current universe -- the same
disclosed limit already on Cara-Menguji).

**New code, all covered by pytest before running on real data:**
`pipeline/hypotheses/t1_market_state.py`, `_warnings_panel.py`,
`r1_warning_overlap.py`, `r2a_warning_count.py`,
`_stress_common.moving_block_bootstrap` (new shared primitive).

## R2b and R5, run 2026-09-27 (`r2b_warning_pairs.py`, `r5_warning_market_state.py`)

**Deviation from this project's own discipline, disclosed rather than hidden:**
unlike every other entry in this log, these two modules were run BEFORE a
dated pre-registration paragraph for them existed in this file -- done at
the user's explicit instruction ("yeah go moveone right now") to keep
working through R2b/R5/A1 in one sitting, on the same day as T1/R1/R2a.
Their exact definitions were fixed in advance in the *approved plan*
(`kind-juggling-hoare.md` section 5, approved before any of this code
existed), so the substance was locked before the result was seen, but the
usual "written and committed to git, then run" ordering was not followed
for these two specifically. Recorded here as both the definition and the
result together, git-history-adjacent rather than git-history-preceding.

### R2b: three pre-registered warning pairs (using R1's merged names)

Pairs, cells (size tercile x 60-day-vol tercile, per formation month),
outcomes and the Holm correction are exactly as specified in the plan; the
"pair"/"X alone"/"Y alone" group definitions, the HOLDOUT-ONLY support
check (the plan's R2b text never asks for an explore-side check, unlike
R2a), and the one-sided stock-clustered-bootstrap significance test are
this module's own operationalization of that spec (stated as such in the
module's own docstring, not claimed as pre-existing).

| Pair | Qualifying cells | Result |
|---|---|---|
| spike_40_20 x loss_year | 0 | Not run as a trial (descriptive). Pooled: pair n=69 D-U -0.116; spike_40_20 alone n=227 D-U -0.040; loss_year alone n=712 D-U -0.090. |
| payout_top_tercile x earnings_down_2y | 0 | Not run as a trial (descriptive). Pooled: pair n=72 D-U -0.042; payout_top_tercile alone n=677 D-U -0.037; earnings_down_2y alone n=223 D-U -0.022. |
| long_below_peak x loss_year | 8 of 9 | **Ran as a trial. NOT confirmed.** |

The one pair with support: cell-weighted holdout D-U was pair -0.224,
long_below_peak alone -0.240, loss_year alone -0.101. The pair beats
long_below_peak alone (-0.224 > -0.240) but **does not** beat loss_year
alone (-0.224 < -0.101) -- min(pair-x, pair-y) = -0.123, so the "beats
both" condition fails outright regardless of significance. One-sided
bootstrap p (H1: pair beats both) = 0.989, 2,000 valid replicates: no
evidence for the direction being tested. Holm-Bonferroni was applied
across the 1 pair that actually ran (trivial at m=1, same as
uncorrected): not significant. **Trial counter: 37** (one trial ran, the
other two stayed descriptive and are not counted, same fallback rule as
R2a).

### R5: warnings x market state (holdout only)

**Correction to the plan's stated premise**, found while building this and
disclosed rather than silently absorbed: the plan says the explore period
"has no stressed months." Checked directly against T1's real fitted
states: explore has exactly one stressed month, 2022-06-01 (708 of
10,285 explore formations), a single isolated episode. Not literally zero,
but this doesn't disturb the holdout-only design, since the real 2025-2026
stress episode this test is actually about lives entirely in holdout
(8,832 of 23,496 holdout formations, spanning 16 of holdout's 33 months).

Episode minimum (this module's own operationalization, the plan states the
idea without a number): each of the 4 groups (0/2+ warnings x
tertekan/normal) needs >=30 holdout observations, pooled rather than
cell-weighted (cell-weighting on top of this many splits would very likely
starve every cell, the same way R2a's did). All 4 groups qualified:
tertekan/0 n=1,300; tertekan/2+ n=3,398; normal/0 n=2,725; normal/2+
n=5,184. **Ran as a trial.**

DiD statistic -- (DU[2+,tertekan] - DU[0,tertekan]) - (DU[2+,normal] -
DU[0,normal]) -- estimate **+0.029**, stock-clustered bootstrap CI
**[-0.040, 0.092]** (2,000 replicates), straddling zero. **R5: NOT
confirmed.** Warnings appear directionally to matter slightly more during
a stressed market than a normal one, but the effect is small and not
distinguishable from zero at this sample size. **Trial counter: 38.**

**New code, all covered by pytest before running on real data:**
`pipeline/hypotheses/r2b_warning_pairs.py`, `r5_warning_market_state.py`,
`pipeline.stats.holm_bonferroni` (new shared primitive).

## A1, run 2026-09-27 (`a1_extreme_gainers.py`)

**"Saham yang naik paling tinggi hari ini akan terus naik" (extreme
one-day gainers keep winning).** Same disclosed deviation as R2b/R5: spec
fixed in the approved plan before this code existed, but the dated
EXPERIMENT.md entry follows the run rather than preceding it, at the
user's explicit instruction.

**A verification detour, disclosed rather than worked around silently**:
the plan's stated exclusion mechanism, the ARA (auto-rejection) price
band, could not be verified from a primary source. A subagent tried
idx.co.id directly (every URL 403/404), the AEI post-pandemic-adjustments
article (dead, default host page), and idnfinancials (403). It also
surfaced signs of network interception (injected fake instructions on
unrelated pages, degraded search results) unrelated to this specific
question but worth flagging generally. Only the *upcoming* Sept
2026/Jan 2027 band change had any coverage, and even that from three
disagreeing secondary sources; 2022-2025, essentially this whole study
window, had no accessible source at all. Rather than guess a percentage
and label it verified, **M4 (the corporate-actions pull) was run instead**
-- the plan's own alternative, which sidesteps the ARA question by
flagging actual split/rights/bonus days directly. User approved the spend
after seeing this tradeoff (2026-09-27, "Spend ~61 credits on M4").

**M4 cost more than stated, disclosed rather than only the intended
figure**: a 3-credit probe (confirming the endpoint's type names and date
fields) was accidentally run twice -- 6 credits, not 3, because a second
ad hoc Python process re-issued an identical call instead of reusing the
first response. The full 20-window pull then cost 60 credits (window 1
re-fetched rather than reconstructed from the incomplete probe output, to
avoid writing fabricated data). Total: 66 credits against the ~61 stated,
logged in `docs/credit_ledger.md`. Running total after this batch: **963
of 1,000, 37 left of the credits expiring 2026-09-30.**

**Method, as specified in the plan**: top-10 one-day gainers by raw
`close` return (t-1 from the IHSG calendar, no gap-bridging; price >= Rp
50; corporate-action days excluded via M4's `ex_date`/`date` fields) vs.
same-day ranks 11-100, per-date spread of the t+1..t+21 return in excess
of IHSG, 20-day moving-block bootstrap, explore/holdout boundary
2023-01-01 (T1's boundary, reused per the common protocol's "20 days for
T1 and A1" grouping).

**`/code-review` (run before presenting this as finished, per CLAUDE.md)
found and this fixed before the run below**: the first version used raw
`close`, not `adjclose`, for the t+1..t+21 OUTCOME return, contradicting
docs/DATA.md's own rule that a multi-day return ratio must include
dividends; and M4's exclusion only checked day t, not the outcome window
itself, so a split/rights/bonus action landing between t+1 and t+21 could
still have distorted a `close`-based outcome undetected. Both fixed:
outcome returns now use `adjclose`, and an event is dropped outright if
any corporate action for that symbol falls anywhere in `[t, t+21]`, not
only on t. (Two more review findings were fixed too, without changing any
number: the corporate-actions fetcher's resumability was keyed to
`date.today()`, which would have silently lost resumability and re-billed
a resume across a day boundary; and the missing-exit-bar carry-forward
scan was bounded to the calendar window instead of scanning a whole
symbol's history.)

**Data**: 864,729 (symbol, day) event-eligible rows from `prices_5y.json`
(2022-01-01 onward) and the IHSG calendar; 66,277 excluded below the Rp 50
floor, 200 excluded as a corporate action on day t itself, 12 trading days
skipped for having fewer than 100 eligible stocks. 1,115 days had a full
top-10/11-100 split; 1,106 had a computable spread (both groups had at
least one usable outcome after also excluding any event whose 21-day
window contained a corporate action, per the fix above). Explore: 225
days. Holdout: 860 days. 21 days dropped at the embargo.

| | Mean per-date spread (top 10 minus ranks 11-100, 21-day `adjclose` excess return) |
|---|---|
| Explore | -0.0072 |
| Holdout | +0.0034, 20-day moving-block bootstrap CI [-0.0100, 0.0223] (2,000 replicates) |

Explore and holdout disagree in sign, and the holdout CI straddles zero
by a wide margin relative to the point estimate itself. **A1: NOT
confirmed.** (The pre-fix run had produced the same conclusion with
similar magnitudes, -0.0047/+0.0030; the fix changed the numbers modestly
but not the result -- reported here as the trustworthy version, not as a
correction of a wrong headline finding.) A third null in this batch that
disagrees in sign between explore and holdout, same pattern as T1 -- read
together, this project is not finding evidence that recent extreme price
behavior (a market-wide stress state, or a single day's biggest movers)
reliably predicts what IHSG or those specific stocks do next, on the data
and methods tested so far. **Trial counter: 39.**

**New code, all covered by pytest before running on real data:**
`pipeline/hypotheses/a1_extreme_gainers.py`,
`pipeline/appdata/fetch_corporate_actions_history.py`.

## Pre-registration, 2026-09-28: R3 (sector/size snapshot) and R4 (H5/H10/H4 split by market state)

Written before either is computed. Plan reference: `kind-juggling-hoare.md`
§5, "R3 and R4 (not trials)". **Neither counts toward the trial counter,
by the plan's own label**: both are explicitly descriptive, with no
decision rule, no explore/holdout split of their own, and no significance
test. Because there is no pass/fail boundary either could be gamed
against, this entry does not follow blind pre-registration discipline the
way T1/R2a/R2b/R5/A1 did -- the market-state labels used below (found via
`t1_market_state.compute_states`, already run and logged) were checked
before writing this definition, and that's disclosed here rather than
presented as if it weren't.

**Data:** M2 (`data/raw/lq45_2026-09-28.json`, `idxhidiv20_2026-09-28.json`),
M3 (`data/raw/subsectors_2026-09-28.json`,
`subsector_market_cap_2026-09-28.json`) and M6
(`data/raw/sectors_daily_close_m6_2026-09-28.json`), all pulled 2026-09-28,
stated cost and approved by the user before the pull, logged in
`docs/credit_ledger.md`. R3 uses M6; R4 uses none of the three new pulls
(it re-slices H5/H10/H4's own already-owned data by an existing state
series) -- M2 and M3 feed Pasar's other sections directly, not R3/R4.

### R3: sector-neutral, size-controlled snapshot, 2025-12-30 -> 2026-06-30

Labelled "satu kejadian, bukan uji" on Sektor, per the plan. One realized
outcome per stock, not a repeated-sampling statistic -- no CI, no
bootstrap, no significance claim.

- **Universe:** every symbol present in both M6 dates
  (`sectors_daily_close_m6_2026-09-28.json`, 956/957 companies).
- **Return:** `close[2026-06-30] / close[2025-12-30] - 1`.
- **Sector-neutral rank:** `stats.sector_neutral_rank(rows, "ret",
  "sub_sector")`, `sub_sector` from `data/raw/universe_2026-09-12.json`
  (already owned, no new pull) -- the same primitive H10 already uses, per
  `pipeline/stats.py`'s "fix it once" rule.
- **Size control:** market-cap proxy `outstanding_shares[2025] *
  close[2025-12-30]` (same raw-price-at-formation convention H5/H10 use
  for size), bucketed into terciles via `quintiles(rows, "size",
  n_buckets=3)`.
- **Report:** sector-neutral return-rank distribution by size tercile
  (median, not mean, matching this project's own convention for skewed
  return data), plus the 10 highest and 10 lowest sector-adjusted movers
  by name, with their sector and raw return shown alongside the rank so
  the number isn't presented without its own context.

### R4: H5, H10 and H4 re-tabulated by market state at their already-fixed formation dates

No new formation logic: every entry date below is already fixed by each
hypothesis's own pre-registered methodology (H5/H10's EXPLORE_YEARS
`[2022,2023]`/HOLDOUT_YEARS `[2024,2025]`, H4's EXPLORE_YEARS
`[2021,2022]`/HOLDOUT_YEARS `[2023,2024]`, all unchanged). State comes
from `t1_market_state.compute_states` on the M1 IHSG series, read on the
nearest trading day on/after each target date (same nearest-value
convention used throughout this project).

**States found (2026-09-28, on the real M1 series):**

| Formation year | Entry date (nearest trading day) | State |
|---|---|---|
| 2021 (H4 only) | 2022-05-09 | normal |
| 2022 (H5/H10/H4) | 2023-05-02 | normal |
| 2023 (H5/H10/H4) | 2024-05-02 | normal |
| 2024 (H5/H10/H4) | 2025-05-05 | tertekan |
| 2025 (H5/H10 only) | 2026-05-04 | tertekan |

**Disclosed confound, found before writing this table:** for H5 and H10,
state is perfectly collinear with phase -- every explore-formation year is
"normal" and every holdout-formation year is "tertekan." A state split for
H5/H10 therefore cannot separate a genuine state effect from whatever else
changed between explore and holdout (methodology freeze, calendar time, or
regime): it is reported as a description of what those already-published
holdout numbers were measured against, not as new evidence of a state
effect. **H4 alone has within-phase variation** -- its two holdout years
split 2023-formation (normal) vs. 2024-formation (tertekan) -- so that
comparison is the one place in this batch where state isn't confounded
with phase, and is called out as such in the results rather than pooled
silently with the rest.

- **H5/H10:** re-run `build_rows_for_year`/`run_phase` per individual
  formation year (not pooled across years, so each year keeps its own
  state label), report the same Spearman/quintile statistics already
  computed for T1/H5/H10, annotated with state.
- **H4:** re-run `build_rows_for_year` per individual formation year,
  report payout-ratio-tercile cut rates annotated with state, with the
  2023-vs-2024 holdout-year comparison called out separately.
- No decision rule, no new significance test: this is a re-tabulation of
  each hypothesis's already-computed relationship by one additional cut,
  not a new claim.

**New code, to be covered by pytest before running on real data:**
`pipeline/hypotheses/r3_sector_size_snapshot.py`,
`pipeline/hypotheses/r4_market_state_split.py`.

### Results, R3 and R4, run once 2026-09-28 (`r3_sector_size_snapshot.py`, `r4_market_state_split.py`)

**R3.** 775 of 956/957 M6-covered stocks had both a `sub_sector` and
`outstanding_shares[2025]` (181 dropped, mostly newer/thinly-covered
listings). Raw median return over the window was deeply negative in every
size tercile alike (T1 -22.8%, T2 -22.6%, T3 -23.7%) -- consistent with
the broad IHSG decline this project has already established (M1: IHSG
peak 2026-01-20, this window starts after that peak and ends mid-2026).
Sector-neutral return rank showed **no meaningful size gradient**: T1
0.519, T2 0.520, T3 0.465 -- the largest tercile ranked slightly worse
within its own sectors, but the gap is small and this is one snapshot, not
a tested effect. The 10 best/worst sector-adjusted movers span ordinary
small/mid-caps across many sectors (MKAP +242%, TIRT +365%, DSSA -80%,
SSTM -85%), not an obvious single-sector story. Shipped as-is to Sektor:
a descriptive ranking, explicitly labelled "satu kejadian, bukan uji," no
predictive claim attached.

**R4.** H5's earnings-yield-vs-return relationship stayed positive across
all 4 formation years (rho +0.203, +0.134, +0.033, +0.111) but weakened
sharply in the first holdout year; its size-vs-return relationship
flipped sign between explore (+0.089, -0.078) and holdout (-0.292, -0.022)
-- **this is exactly the confound disclosed before running**: state
(normal in explore, tertekan in holdout) and phase are perfectly
collinear here, so this split cannot say whether the flip is a state
effect, a phase/regime effect, or coincidence. H10 was not re-run
separately: it shares the identical years and therefore the identical
confound, so a feature-by-feature re-tabulation would add no information
beyond what H5's numbers already show. **H4 is the one place state and
phase aren't confounded**: the payout-ratio-vs-cut relationship stayed
positive and similar in strength across all 4 years regardless of state
(rho +0.410, +0.396, +0.469, +0.404), and the direct within-holdout
comparison -- 2023 formation (normal): 41.0% cut rate, 2024 formation
(tertekan): 38.3% -- shows **no material difference**, though the lowest
payout tercile's cut rate did rise from 11.0% (normal) to 18.9%
(tertekan). Read together: on the one comparison in this batch not
confounded by phase, the state a company entered a "high payout ratio"
period in doesn't appear to change whether that ratio predicted a
dividend cut. Neither result changes any earlier finding's status;
both are descriptive re-tabulations, not new trials, and neither is
published as a predictive claim.
