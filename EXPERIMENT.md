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

## H1 — Does free float predict volatility on IDX?

**Date:** 2026-09-06. **Re-run 2026-09-10 on corrected price data** (Yahoo
endpoint fix, `pipeline/dev/fetch_yahoo_prices.py` switched from
`/v7/finance/spark` to `/v8/finance/chart` — see `docs/DATA.md`). This
was **not** a small-delta refresh like the earlier `stats.py` tie-fix:
n grew from 853 to 913, and **two of the four "explanations" checked
below changed in substance, not just magnitude** — the liquidity-fade
boundary condition turns out to have been a coverage-gap artifact, and
the "holds in every year" claim does not survive on the corrected data.
Both are written up in full below, old numbers struck through per this
file's own convention, not silently replaced.
**Status:** Tested. Falsified, in the opposite direction, and more
specific than first thought. **Exploratory, not confirmatory** — see
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
   (`/v2/free-float/`, 10 credits — `data/raw/free_float_2026-09-06.json`).
2. Pulled a year of daily closing prices for those tickers from Yahoo
   Finance (free, development-time only — see `pipeline/dev/`). ~~853~~
   **913** of 961 had enough history to use (re-run 2026-09-10 on the
   corrected `/v8/finance/chart`-based cache — see `docs/DATA.md`).
3. For each stock, computed how much its price swings day to day
   (annualized volatility) and its worst fall from a peak (max
   drawdown) over that year.
4. Sorted all ~~853~~ **913** stocks by free float into five equal groups
   (quintiles) and compared the groups.
5. Measured the relationship with a rank correlation (Spearman's rho)
   and checked whether it could be coincidence (the t-statistic).

Full runnable code: `pipeline/hypotheses/h1_free_float.py`. Run with
`python -m pipeline.hypotheses.h1_free_float` — every number below comes
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
+6.72~~ **rho = +0.177, t = +5.42** — still a t-statistic that essentially
never happens by chance, just not as extreme as first published.

There was **no relationship at all** between free float and how much
money a stock actually made or lost over the year (~~rho = +0.007, t =
+0.22~~ **rho = +0.009, t = +0.28**, statistically indistinguishable from
zero, unchanged in substance). This finding is about how bumpy the ride
was, not where it ended up.

### Two ways this could have been a false alarm — one genuinely ruled out, one we got wrong the first time

⚠️ **Correction (2026-09-07):** the "checked and ruled out" verdict below
for Explanation 1 was wrong. It's kept struck through rather than
deleted, because the mistake and the fix are both worth showing.

**Could it be that thin-float stocks just don't trade much, so their
prices only look calm because nobody's actually buying or selling?**

~~We checked by counting, for every stock, how many days its price
didn't move at all. Thin-float stocks sat still on 14.2% of days;
wide-float stocks sat still on 13.1% of days — almost identical. We also
reran the whole test using only stocks that genuinely trade often, and
the result held up just as strongly.~~

**What was actually wrong with that check:** "how many days its price
didn't move" only counts days a price *exists*. A stock that didn't
trade at all on a given day has no price to check, so those days were
invisible to the check — not counted as "calm," simply not counted. A
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

⚠️ **Correction (2026-09-10) — the "fades with liquidity" boundary
condition above does not survive the Yahoo endpoint fix, and it was the
coverage gap itself that produced it, not a real property of the
market.** The old `spark`-endpoint cache had so little history for many
stocks that "require ≥230 trading days" left only 161 of 853 stocks —
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
a Yahoo coverage-gap artifact** — the old cache's missing history was
disproportionately concentrated among certain stocks, and restricting to
"high trading-day count" was inadvertently restricting to whichever
stocks the old `spark` endpoint happened to cover well, not to
whichever stocks were actually thinly traded. The corrected result is
simpler than either prior version: **no fading, no reversal, no
liquidity boundary condition found.**

**The GOTO wrinkle, substantially resolved.** `GOTO.JK` — one of the
most actively traded stocks on IDX — showed only 128 of ~242 days in the
old cache, almost certainly a coverage gap rather than illiquidity. On
the corrected cache it shows **244 of ~249 days** — the gap for this
specific, heavily-traded symbol is gone. This doesn't prove every
residual short history is genuine illiquidity rather than a remaining
Yahoo gap, but it removes the clearest previously-known counterexample,
and the liquidity-sweep table above no longer shows any threshold effect
for the "poorly covered" explanation to be hiding behind. `docs/PLAN.md`
§8.3's Sectors-price cross-check is still owed before this is fully
closed (see Limits) — "substantially resolved," not "resolved."

**Could this just be describing the 2026 market crash**, where foreign
investors pulled money out of Indonesia and hit the big, widely-owned
stocks hardest for reasons that have nothing to do with free float?
~~We checked by running the same test separately for every year from
2022 to 2026. The same pattern showed up **every single year** — this
part holds up~~:

⚠️ **Correction (2026-09-10) — "holds in every year" is retracted; it
does not survive the Yahoo endpoint fix.** Re-run on the corrected cache
(n per year below, `pipeline/hypotheses/h1_free_float.py`):

| Year | ρ | t | thin-float vol | wide-float vol |
|---|---|---|---|---|
| 2022 | −0.033 | −0.91 (not significant) | 43.2% | 42.4% |
| 2023 | +0.001 | +0.02 (not significant) | 40.7% | 39.5% |
| 2024 | +0.179 | +5.39 | 43.8% | 57.3% |
| 2025 | +0.179 | +5.41 | 51.9% | 66.9% |
| 2026 | +0.164 | +4.95 | 54.6% | 71.0% |

**2022 and 2023 now show no relationship at all** — not weaker, *zero*,
in the case of 2023 (ρ = +0.001). This is not the growing-sample
confound already flagged and corrected once (below): checking on the
**balanced panel of 751 stocks present in all five years**
(`pipeline/hypotheses/h1_stress.py`, test 1) gives the same split —
2022 ρ −0.033/t −0.91, 2023 ρ −0.024/t −0.66, both still not
significant, against 2024 t +4.63, 2025 t +4.16, 2026 t +4.26 on the
identical fixed panel. **Read plainly: this is a real, newly-disclosed
boundary condition, not an artifact of unbalanced samples or of the old
coverage gap** — the relationship is present in 2024–2026 and absent in
2022–2023, on the same 751 stocks either way. One plausible (unverified)
reading: free float is a single 2026 measurement, so it may describe
*current* ownership structure correlating with *recent* trading
behaviour better than it describes ownership years before it was
measured — but this is speculation, not something this data can confirm,
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
numbers above** (751 stocks, not 564 — coverage improved enough that the
fixed panel itself grew). The corrected, current statement: **the
effect is not present in every year — it clearly holds 2024–2026 and is
absent in 2022–2023**, on the same fixed set of stocks throughout.

### A confound we did find, and it sharpened the finding

We wondered whether "free float" was secretly just a stand-in for
"company size" (big companies vs small ones). It isn't — the two are
barely related. But splitting stocks into four groups by size and
re-running the test inside each group revealed something more precise —
**revised 2026-09-10, and the revision is substantive, not cosmetic:**

~~**The whole effect lives in small companies.** Among the smallest IDX
companies, high-float stocks swing about **102%** a year against **75%**
for closely-held ones — a huge gap. Among the largest companies, free
float barely matters at all (53% vs 47%).~~

⚠️ **Correction (2026-09-10) — "the whole effect lives in small
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
shows the effect **significant in three of four buckets — including the
largest** — and weakest in the second-largest ("mid-large") bucket, not
monotonically fading with size. **The "small-cap-specific" framing this
project has used since 2026-09-06 — including in `docs/PLAN.md`'s
product design for a per-stock applicability rule ("H1 does not apply to
BBCA, the largest IDX company") — no longer holds up as a clean
description of the corrected data**, and needs to be revisited before
any product decision continues to rely on it. Recorded here rather than
silently propagated; see Limits and `BACKLOG.md` for the follow-up this
requires.

### A third explanation, tested after the fact: is this just cheap stocks?

IDX prices move in fixed steps (a "tick"), and the tick is a bigger
percentage of a cheap stock's price than an expensive one's — a Rp 1
tick is a 2%+ move on a Rp 40 stock but under 0.4% on a Rp 6,000 one.
Cheap stocks can look mechanically more volatile for a reason that has
nothing to do with turbulence.

~~`pipeline/hypotheses/h1_stress.py`, test 2: 18.1% of the 853 stocks
trade under Rp 100 (tick ≥1% of price), 5.3% under Rp 50 (tick ≥2%).
Restricting to stocks trading at Rp 500 or more (tick under 1%): n=334,
ρ = −0.023, t = −0.43 — **not significant**.~~ **Corrected 2026-09-10**
(n=913): 20.6% of stocks trade under Rp 100, 7.1% under Rp 50.
Restricting to Rp 500 or more: n=348, ρ = +0.042, t = +0.78 — still
**not significant**, same conclusion as before. ρ(price, free_float) =
−0.270 (was −0.237). This plausibly overlaps the liquidity finding above
rather than being independent evidence — though "the liquidity finding"
above has itself now been resolved as a coverage-gap artifact (see the
2026-09-10 correction), so this overlap claim is weaker than when first
written: cheap stocks and thinly-traded stocks may still tend to be the
same obscure small companies, but "thinly-traded" is no longer shown to
matter for the *main* effect the way it appeared to.

### What this means, in one sentence

~~**Among small Indonesian companies, the ones where a lot of stock is
publicly available are far more turbulent than the ones a founder or
family still tightly controls — which is the opposite of the common
warning that thinly-held stocks are the dangerous ones.**~~

⚠️ **Corrected 2026-09-10 — the "among small companies" qualifier
overstates what the data now shows.** The size-control table above
found the effect significant in three of four size buckets, not
concentrated in the smallest one. Revised statement: **IDX stocks where
a lot of stock is publicly available tend to be more turbulent than
closely-held ones — the opposite of the common warning that thinly-held
stocks are the dangerous ones — and this holds across most company
sizes, not just small caps.** Still true and unchanged: this describes
2024–2026 specifically, not 2022–2023 (see the year-by-year correction
above).

### Why it might be true

A guess, not yet tested, and weakened by the size-control correction
above: the original mechanism guessed that a tightly-held company barely
trades because whoever owns most of it isn't selling, so its price barely
moves — while a widely-held company is one the public actually trades,
and that trading is what makes it choppy. That story was built to
explain a *small-cap-specific* pattern; now that the effect also shows
up among large caps (where "a founder holding most of the stock and
never selling" is a less obvious story — large IDX companies vary widely
in ownership structure), **this mechanism is no longer well-supported
and should be treated as withdrawn, not just unverified**, pending a
better explanation.

### Limits — read this before using the finding anywhere

- **This describes volatility, not money made or lost.** A stock can be
  wildly turbulent and still go up. Don't read "turbulent" as "bad."
- **Correlation, not cause.** We haven't shown *why* — the mechanism
  guess originally offered here has since been withdrawn (see "Why it
  might be true" above) and not replaced.
- **This is a contemporaneous association, not a prediction.** Free
  float is a single 2026 measurement with no history, so it cannot be
  used to predict a historical outcome (see the predictor-before-outcome
  rule in `docs/DATA.md`) — it only describes stocks measured *at the
  same time* as their volatility. Never describe this finding as
  predictive.
- ~~**Undisclosed boundary condition, found late:** the effect fades as
  actual trading activity rises...~~ **Resolved 2026-09-10:** re-run on
  the corrected Yahoo cache, the effect does **not** fade with trading
  activity at any threshold tested (see the correction above) — the
  original "fades" finding was itself a coverage-gap artifact of the old
  `spark` endpoint, not a real boundary condition. Superseded by the next
  bullet, which **is** a real, still-open boundary condition.
- **New boundary condition, found on the 2026-09-10 re-run and not yet
  explained: the effect holds 2024–2026 and is absent in 2022–2023**, on
  a fixed panel of the same 751 stocks throughout — not a sample-size or
  coverage artifact. **Any product use of this finding should account
  for this being a recent-period pattern, not a five-year constant**,
  until a mechanism is found or ruled out.
- **The "small-cap-specific" framing is retracted, not merely
  qualified.** The 2026-09-10 size-control re-run found the effect
  significant in 3 of 4 size buckets (smallest, small-mid, largest),
  weakest in mid-large. **Any product feature that gates this finding on
  company size (e.g. "does not apply to large-caps like BBCA") is now
  built on a claim this data no longer supports** and needs updating
  before it ships — tracked in `BACKLOG.md`.
- **Exploratory, not confirmatory.** Tested on all the data at once, no
  formal train/test split. Its previously-claimed strength ("holds up
  across five separate years") no longer holds — see the year-by-year
  boundary condition above. H2 onward (and H5, which already does) uses
  a proper holdout, per `RULES.md`.
- **Gorengan tension, partially reframed rather than resolved.** The
  literature treats *low* free float as the danger signal; our result
  says the opposite. ~~The corrected liquidity check suggests the two may
  not be in as much tension as first thought...~~ That specific liquidity
  argument no longer applies now that the liquidity boundary condition
  itself was found to be an artifact (see above) — the tension is
  unresolved and, if anything, less explained than before.
- **The regulatory story runs on the opposite theory, and this is a
  genuinely separate tension from the one above.** Indonesian regulators
  have kept the *minimum* free-float requirement low (~7.5%) for years and
  are now raising it to 15% specifically because *low* float is treated as
  a market-health risk (Glass Lewis, 11 Feb 2026 — see `docs/SOURCES.md`
  §1). H1 found small-cap volatility rising with *higher*, not lower,
  float. Both can be true at once — regulators may be responding to a
  different failure mode (concentrated ownership enabling manipulation)
  than the one H1 measured (public trading activity itself producing
  turbulence) — but nothing in this project's data adjudicates that.
  Stated as an open tension, not resolved either way.
- **Two known bugs in the shared statistics library were fixed after
  this was first run** (`pipeline/stats.py`, tied-rank averaging and a
  quintile-bucket sizing bug). The headline ρ moved from +0.225 to
  +0.224 (2026-09-07) then, on the corrected Yahoo cache, to +0.177
  (2026-09-10) — this second move is the endpoint fix, not a further
  statistics-library bug.
- **Trial count: 1.** This is the first hypothesis tested. Any claim
  made from this finding should say so, the same way Argus (the
  previous project) always quoted its Deflated Sharpe Ratio together
  with how many things had been tried. Re-running on corrected data is
  not a new trial (same hypothesis, same method — only the underlying
  price series changed), matching how the `stats.py` tie-fix was handled.

### What this opens up

- A real finding, but its two live boundary conditions (2024–2026 only;
  no longer cleanly small-cap-specific) need to be attached before it
  goes anywhere near the product — the unqualified "small caps are more
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
  ~~shuffled free float, ρ = +0.02 — passed~~ → **shuffled free float,
  ρ = +0.019 — still passes**, gate held; ~~split-half ρ +0.180/t +3.76
  and ρ +0.267/t +5.72~~ → **split-half ρ +0.170/t +3.68 and ρ
  +0.179/t +3.87** — both halves still positive and significant, so the
  direction still isn't an artifact of one arbitrary half of the sample.

---

## H1b — Does the float-drawdown relationship survive size control?

**Date:** 2026-09-06. **Re-run 2026-09-10** on the corrected Yahoo cache
alongside H1 — see H1's entry above for what changed and why. Old
numbers struck through below, not silently replaced.
**Status:** Tested. ~~Confirmed — the drawdown relationship behaves like
the volatility one.~~ **Still not falsified, but the "small-cap-specific"
framing is retracted — see below**, matching H1's own 2026-09-10
correction. **Exploratory, not confirmatory**, and not an independent
trial — see Limits below.

### The hypothesis, written down before looking

H1's uncontrolled result already showed free float negatively correlated
with max drawdown (rho = ~~−0.185, t = −5.50~~ **−0.169, t = −5.17**):
wider-float stocks fell further from their peaks. H1's *volatility*
version of this pattern was originally reported as concentrated in small
companies and nearly vanishing among large ones — **that framing has
since been retracted (see H1's 2026-09-10 correction)**. H1b asks
whether the *drawdown* version follows the same (now-corrected) shape.

**This hypothesis would be falsified if:** the drawdown relationship
held roughly evenly across all four size buckets — i.e. if, unlike
volatility, it were *not* a small-cap-specific effect.

### How we tested it

Reused H1's exact dataset and per-stock measures (free float, market
cap, max drawdown over the same year) — no new data, no new cost. Split
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

**Not falsified — but not small-cap-specific either.** The largest bucket
is now the single *strongest* result by t-statistic (−3.01), not the
weakest. Three of four buckets are significant; only mid-large isn't —
the same "significant everywhere except the middle" shape H1's own
2026-09-10 correction found for volatility. The original "driven almost
entirely by the smallest bucket" reading does not survive correction.

### What this means, in one sentence

~~**Among small IDX companies, the ones with wide public ownership don't
just swing more — they also fall further from their peaks — while for
larger companies free float has little bearing on either.**~~

**Corrected 2026-09-10:** IDX stocks with wide public ownership tend to
fall further from their peaks than closely-held ones — across most
company sizes, not specifically small ones, matching H1's own corrected
volatility finding.

### Limits — read this before using the finding anywhere

- **Not an independent confirmation of H1 — and closer to a restatement
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
  together — see the correlation above).
- **Same year-boundary condition as H1, not yet separately re-verified
  for drawdown**: H1's volatility effect holds 2024–2026 and is absent
  2022–2023. Not re-tested specifically for drawdown here, but given
  `corr(volatility, max drawdown) = −0.822`, there is no reason to expect
  it behaves differently — treat as inherited, not independently confirmed.
- **Same open, partially-reframed gorengan tension** as H1.
- **Trial count: 2** (H1, H1b). Both trials came from the same purchased
  dataset; this should be stated alongside either finding. The 2026-09-10
  re-run is a data correction, not a new trial — same reasoning as H1's.

### What this opens up

- ~~Strengthens the case that "free float" and "small-cap" need to
  combine...~~ **Superseded 2026-09-10**: the corrected data no longer
  supports gating this finding (or H1's) on company size at all — see
  both entries' 2026-09-10 corrections. What both findings now need
  before product use is an explanation for the 2024–2026-only pattern,
  not a size qualifier.
- The next genuinely new hypothesis (Phase 0, then whichever the
  register in `docs/PLAN.md` §6 prioritizes) uses fresh data rather than
  re-cutting what's already owned.

---

## H5 — Do value and size factors predict returns on IDX?

**Date:** 2026-09-08. **Re-run 2026-09-10** on the corrected Yahoo price
cache (Chunk B) with one methodology addition: the return calculation now
uses `adjclose` (dividend-and-split-adjusted) instead of raw `close` — the
size proxy still uses raw `close` (see "How we tested it" below for why
that split matters). **This is a data/measurement correction, not a new
trial** — same hypothesis, same proxies, same formation lag, same year
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
expensive/large stocks over the same window — the value and size premia,
well documented in developed markets, untested here.

**This hypothesis would be falsified if:** no monotonic relationship shows
up across quintiles in the holdout window, or it reverses.

### Holdout discipline (decided 2026-09-07/08, before any holdout number was looked at)

`pe[2021]` is **entirely absent** from the purchased universe — 0 of 962
companies, including BBCA — verified by reading
`data/raw/universe_2026-09-07.json` directly, not assumed from the field
list. That leaves 4 usable formation years: 2022–2025. Because the newest
pair (formed on 2025 data) can only be checked against a partial 2026 —
2026 isn't complete yet — **every** window, explore and holdout alike, uses
the identical **May 1 → Sep 4 of the following year** range, so exploration
tests exactly the method that runs in holdout, not a longer or cleaner
version of it.

Formation date is May 1, not Jan 1, to avoid looking ahead of when annual
figures were actually public — fiscal-year data isn't known the instant the
year ends. **This is an assumed ~4-month reporting lag, not verified against
IDX's actual disclosure deadline** — conservative in the safe direction
(later, not earlier), so it doesn't manufacture a false positive if wrong.

**Explore** (methodology allowed to change): formation 2022, 2023 → return
May–Sep 2023, 2024. **Holdout** (frozen, run once): formation 2024, 2025 →
return May–Sep 2025, 2026.

### How we tested it

1. **Value proxy:** `1 / pe[year]` (earnings yield), restricted to `pe > 0` —
   negative P/E (loss-making companies) isn't a meaningful "cheapness"
   signal, so those rows are excluded from the value ranking entirely
   (shrinks n; not a neutral filter).
2. **Size proxy:** `outstanding_shares[year] × nearest Yahoo close at
   formation`. Sectors has no yearly `market_cap` field, so this is computed
   from data already purchased. Yahoo prices are dev-only, free, never ship
   (`RULES.md`) — same status as H1's price data. **Uses raw `close`, not
   `adjclose`, deliberately** — `adjclose` retroactively lowers historical
   prices for dividends/splits that happen *after* the date being priced
   [verified 2026-09-10 against the cache: BBCA.JK's close/adjclose gap is
   14.65% on the oldest cached date, shrinking to 0% on the most recent].
   Using it for size would shrink the market-cap proxy specifically for
   stocks that later pay more dividends — correlated with the value leg
   this hypothesis tests — so it would bias the size proxy in a
   direction-specific way, not just add noise.
3. **Outcome:** return from that formation price to the nearest close on or
   near Sep 4 of the same year — **using `adjclose` (added 2026-09-10)**,
   because a return measure is supposed to capture total investment return,
   which dividends are part of by definition. This directly fixes the
   dividend-exclusion limitation named in the original write-up.
4. Spearman rank correlation, quintiles, and a value-vs-size confound check
   — same `pipeline/stats.py` functions H1 uses, no new statistics code
   (the corrected run adds `stats.nearest_value`, a straightforward
   generalization of the date-matching logic already used, to read the new
   cache schema — see `docs/DATA.md`).

Full runnable code: `pipeline/hypotheses/h5_value_size.py`. Explore only:
`.venv/bin/python -m pipeline.hypotheses.h5_value_size`. With holdout
(touched once per the original 2026-09-08 run, reproduced byte-identical on
a second run then; **re-run once more 2026-09-10 as the data correction
described above, also reproduced byte-identical on a second run**):
`.venv/bin/python -m pipeline.hypotheses.h5_value_size --confirm-holdout`.

### What we found — explore phase

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
null than before — the pooled figure is now essentially zero (t=+0.05,
was −1.20), and the two years still disagree on sign. Value-vs-size
confound check: ρ≈+0.07–0.10 across both years — still weak, not a
meaningful overlap.

### What we found — holdout, re-touched once as a data correction

~~| Formation → outcome | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| 2024 → May-Sep 2025 | 568 | −0.027 | −0.65 | **−0.282** | **−7.00** |
| 2025 → May-Sep 2026 | 530 | +0.057 | +1.31 | −0.061 | −1.40 |
| **Pooled** | **1098** | **+0.037** | **+1.24** | **−0.193** | **−6.52** |~~

⚠️ **Corrected 2026-09-10 — this is the headline change:**

| Formation → outcome | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| 2024 → May-Sep 2025 | 601 | +0.033 | +0.80 | **−0.292** | **−7.48** |
| 2025 → May-Sep 2026 | 547 | **+0.111** | **+2.61** | −0.022 | −0.51 |
| **Pooled** | **1148** | **+0.088** | **+2.99** | **−0.183** | **−6.31** |

### The inversion — corrected, and it now only applies to one leg

~~**Holdout produced the opposite pattern from what exploration predicted.**
The leg that looked promising in exploration (value)... The leg that looked
null in exploration (size)... came back strongly significant in holdout~~

**Corrected 2026-09-10: the inversion no longer describes the value leg.**
On the corrected data, **value is positive and significant in both
explore (t=+5.77) and holdout (t=+2.99)** — the same direction throughout,
which is what a real effect is supposed to look like. Including dividends
(via `adjclose`) directly fixed the null result: the original write-up's
own speculation — *"the null on value may be partly a measurement artifact
rather than proof the effect doesn't exist"* — turned out to be correct.
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
— the opposite of what more/better data would ideally show for a robust
effect.

This is exactly the pattern a real holdout exists to catch, but the two
legs now tell different stories: reporting "IDX has a value effect" using
the corrected numbers is now defensible (same sign, significant, in both
phases). Reporting "IDX has a size effect" is not — it remains a
**single-year-driven, unpredicted lead**, not a confirmed finding, and the
correction made that concern sharper rather than resolving it.

### What this means, in one sentence

~~**No confirmed value effect on IDX in this test; an unpredicted size
effect showed up in the untouched holdout data and needs its own
independent confirmation before it means anything for the product.**~~

**Corrected 2026-09-10: cheaper IDX stocks (by earnings yield) earned
higher subsequent returns in both the explore and holdout windows, once
dividends are counted — a real, if modest, value effect. The size
result is unchanged: still an unpredicted, single-year-driven holdout
lead that needs independent confirmation before it means anything for
the product.**

### Limits — read this before using either result anywhere

- **`pe[2021]` gap limits this to 4 formation years total**, split 2-and-2 —
  a thin base for any holdout, and the reason a single year (2024) can drive
  most of a pooled result (see below).
- **The 4-month reporting-lag formation date is assumed, not verified**
  against IDX's actual annual-report deadline.
- **The `pe > 0` filter removes loss-making companies from the value test
  entirely** — the value result describes profitable companies only.
- ~~**Size-correlated data dropout...** companies missing from the Yahoo
  dev cache, or too far from the target dates, are dropped from the test —
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
  the pooled figure — dropout is now small enough in absolute count (2-24
  companies) that it can no longer meaningfully bias any of the four years.
  **"Substantially resolved," not "resolved outright"** — 2025 still drops
  24 companies skewed somewhat smaller, and this fixes the *dev-cache* data
  only; `docs/PLAN.md` §8.3's Sectors-price cross-check obligation is
  unchanged by this fix.
- ~~**The return measure excludes dividends...**~~ **Resolved 2026-09-10**
  — the return calculation now uses `adjclose`, which includes dividends
  and splits. This was the original write-up's own top candidate
  explanation for the value null, and fixing it changed the result exactly
  as speculated: value is now significant in both explore and holdout.
- **New limitation, found while fixing the schema, not previously
  disclosed: the effective outcome-window length varies by stock, by up
  to ~20 days (~15% of the ~127-day window), and this isn't new to the
  2026-09-10 correction — it was already true of the original code, just
  not previously named.** Both the formation-date and outcome-date price
  lookups independently tolerate up to 10 days' gap, so a stock with
  perfect data gets the full May 1 → Sep 4 window while a more illiquid
  one could get anywhere from ~107 to ~147 days, depending on which side
  of each 10-day tolerance its nearest trades fall on. Since illiquidity
  correlates with company size, this is a real confound specifically for
  the size leg — not fixed here, because changing it would be a
  methodology change to an already-frozen, once-run holdout, which this
  project's own anti-p-hacking discipline forbids mid-flight. Flagged for
  whoever next revises H5's methodology from scratch (e.g. the H5
  follow-up in `BACKLOG.md`), not fixed as part of this data correction.
- **Single-regime risk on the holdout itself — worse after correction, not
  better:** only two years (2024, 2025) make up the entire holdout, and one
  of them (2024) drives nearly the whole size result. ~~2024 t=−7.00~~ →
  **corrected 2024 t=−7.48, while 2025 weakened from t=−1.40 to t=−0.51** —
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
  have excluded. Not re-run without financials — that would be a
  methodology change to a frozen holdout, tracked instead as a candidate
  follow-up in `BACKLOG.md`.
- **External literature runs opposite to what we found, and a specific,
  checked explanation — not just a general tension — accounts for it.**
  The general pattern in emerging-market factor research is that *value*
  survives real trading costs while the *size* premium is fragile to them
  — in one 11-market study, size returns were "obliterated" by liquidity
  constraints while value was "the only premium left standing" (Zaremba &
  Konieczka 2015, via The Evidence-Based Investor, Feb 2025 — see
  `docs/SOURCES.md` §3). H5 found the reverse: value did not confirm,
  size did. Two checks done against our own data, not just literature
  comparison:
  - **Checked and ruled out:** the specific small-cap names in a
    widely-reported December 2025 single-day rally (IPOL, NATO, TRUE,
    TRON — Jakarta Globe, 4 Dec 2025) do not explain the holdout result.
    IPOL and TRON sat in the second size quintile, not the smallest; NATO
    in the third; TRUE wasn't in the eligible sample at all; and TRON's
    actual measured return in H5's own May–Sep 2025 window was **−28%**
    (a reversal, not the reported surge, which in any case happened three
    months after that window closed).
  - **Best-supported explanation found (not proven):** Bank Indonesia cut
    its benchmark rate three times in 2025 — 15 Jan, **21 May**, and
    15–16 Jul, −25bp each — with the May cut landing right at the start
    of the 2024-formation holdout's outcome window (May–Sep 2025). This
    matches a documented general mechanism (small/thin names
    disproportionately rallying on falling rates, as seen internationally
    in the 2025 Russell 2000 rally) and fits the shape of the actual
    result — a broad, roughly monotonic staircase across all five size
    quintiles, not a few outliers. The explore years (2022–2023) had no
    comparable rate-cutting cycle, consistent with exploration never
    predicting this. No direct causal test was possible with only 4 years
    of data — this is a well-supported explanation, not a proven one.
  - **Read together — corrected 2026-09-10:** the size result still looks
    like a real but regime-specific rate-cut rotation, not a persistent IDX
    size premium. ~~which is also consistent with the general literature
    above, even though H5's specific pattern (size significant, value not)
    inverts which leg looked fragile~~ — **that inversion is now gone**:
    with dividends included, H5's pattern (value significant and durable,
    size significant but fragile across years) now matches the general
    literature's shape directly, not just its themes. Read plainly: this
    correction made H5's results *more* consistent with the outside
    literature, not less.
- **Size's significance cannot yet be told apart from a one-period fluke —
  if anything more true after correction**, given the widened gap between
  the two holdout years' individual t-statistics above. Ruling that out
  needs a genuinely new, independent year of data, which doesn't exist
  yet — re-testing on the same four years would violate the exact
  explore/holdout discipline that surfaced this lead in the first place.
- **Dev-only price data, same status as H1:** every number here comes from
  Yahoo, never shipped, and owes the same Sectors price cross-check already
  tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3) before any of this reaches
  the product.
- **The outcome-window-length limitation above (up to ~20 days'
  variability between stocks) applies to both legs but is a specific
  concern for size**, since illiquidity (which drives which stocks get a
  shorter or longer effective window) correlates with company size.
- **Trial count: 3** (H1, H1b, H5) — unchanged. The 2026-09-10 re-run is a
  data correction, not a new trial (same hypothesis, proxies, lag, and year
  split — only the price series changed), per this file's own convention
  for exactly this situation.

### Stress tests (2026-09-11) — the checks H1 got that H5 never had

H1 has a dedicated stress-test module (`pipeline/hypotheses/h1_stress.py`:
a placebo test and a random split-half). H5 only ever had its
explore/holdout split and a value-vs-size confound check — a real gap,
now closed by `pipeline/hypotheses/h5_stress.py`.

**Design note, important for reading the results correctly:** pooling all
4 formation years gives a stock up to 4 rows (one per year) — repeated
observations of the same company, not independent draws. Two
independent review passes caught that testing on that raw pooled sample
(n=2319) would make a split-half test's two "halves" not actually
independent (a company's own persistent traits can land in both halves
via different years) and would inflate the placebo test's significance.
**Fixed by collapsing to one row per symbol** (averaging
earnings_yield/size/return across whichever years a symbol has) before
either test — 2319 pooled rows collapse to **770 distinct symbols**.

**Test 1 — placebo** (shuffle earnings_yield, separately shuffle size;
each against real returns; hard gate at |ρ| < 0.1):

| Shuffled | ρ | t | Gate |
|---|---|---|---|
| earnings_yield | −0.0008 | −0.02 | **PASS** |
| size | +0.0170 | +0.47 | **PASS** |

Both collapse to ~0 as required. The statistical pipeline is not
manufacturing correlation from noise.

**Test 2 — random split-half** (770 symbols → 385/385, independent by
construction since each symbol appears in only one half):

| | n | value ρ | value t | size ρ | size t |
|---|---|---|---|---|---|
| Half A | 385 | +0.159 | +3.15 | −0.104 | −2.04 |
| Half B | 385 | +0.110 | +2.17 | −0.080 | −1.56 |

**Value:** both halves positive and significant — corroborates the
already-confirmed explore/holdout result on a genuinely independent
split of companies, not just of years.
**Size:** both halves negative, one significant (t=−2.04) and one
borderline (t=−1.56, just under the usual 1.96 threshold) — more
consistent under a random split than the year-by-year breakdown alone
might suggest. **This does not resolve the size leg's core concern.** A
random split mixes years together, so it cannot detect (or rule out) a
result that depends on *which year* a row comes from — that's a
different question, already answered separately by the year-by-year
table further up (2024→2025 t=−7.48 vs. 2025→2026 t=−0.51). Read
together: size is reasonably stable across *which companies* you sample,
but still concentrated in *which year* you sample — two distinct and not
mutually resolving robustness questions.

### What this opens up

- **The explore/holdout split worked as intended, in both directions.**
  On the original (uncorrected) data it flagged a size pattern as needing
  confirmation rather than letting one untouched-data run count as proof —
  and on the corrected data, it let a real value effect (present in *both*
  phases) be told apart from a one-phase fluke, which single-phase testing
  never could have done either way.
- ~~The size lead is not actionable until it's tested against data this
  project hasn't seen yet... or once the Sectors price cross-check (owed
  anyway) replaces the Yahoo dev cache and removes the coverage-gap and
  dividend-exclusion caveats above.~~ **Partially superseded 2026-09-10:**
  the coverage-gap and dividend-exclusion caveats are now resolved (Chunk
  B/D). The size lead is still not actionable, for the same reason as
  before — it needs a genuinely new, independent formation year, which
  doesn't exist yet regardless of data quality.
- ~~A dividend-inclusive return measure would directly address the value
  leg's biggest named limitation and might change its outcome...~~ **Done,
  2026-09-10 — and it did change the outcome, in exactly the direction
  speculated.** The next open question for the value leg is the
  Financials-exclusion limitation above, not dividends.
- **New from this correction:** the outcome-window-length variability
  limitation (up to ~20 days between stocks) was not previously named and
  is now the most-recently-found open methodological question for H5,
  parallel to how H1's boundary conditions kept surfacing on re-verification
  rather than all being found in the first pass.

### Timing-precision diagnostic (2026-09-12) — is the confirmed year's effect concentrated around the rate cut?

**Not a new trial, not a fix for the "confirmed in only one year" weakness
— a diagnostic on an already-observed result**, run once
(`pipeline/hypotheses/h5_timing_diagnostic.py`). Verified first, before
running anything: there is **no way to add a genuinely new, independent
formation year before the 2026-09-30 freeze** — `pe[2021]` is confirmed
absent from every field capable of reconstructing it (checked every
equity/book-value/earnings-related field in the owned schema; none
exist), and the next new year (formation 2026) needs `pe[2026]`, not
public until well after the freeze. This diagnostic cannot change that;
it can only test whether the one confirmed year's effect is internally
consistent with the rate-cut explanation already on record.

**What was tested:** the 2024-formation holdout window (return 1 May – 4
Sep 2025, size ρ=−0.292/t=−7.48) was split at **21 May 2025** — the
middle of the three 2025 BI rate cuts, and the first one to fall inside
this window (15 Jan is before the window opens) — into a pre-cut and
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
size quintile medians tell the same story — the smallest-quintile median
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
  result — it cannot substitute for an independent year, and doesn't
  attempt to. A single window split two ways, along a dimension (calendar
  time within one year) that was never itself pre-registered as a
  predictor, is a low-power, after-the-fact check — informative about
  internal consistency, not new evidence of the effect's existence or
  durability.
- **Product decision unchanged:** size stays scoreboard-only, not shipped
  as a feature, regardless of this result.

---

## H14 — Do retail's own technical indicators (RSI, 200-day MA, momentum) predict returns on IDX?

**Date:** 2026-09-12. **Status:** Tested, explore + holdout, with a real
holdout confirmation run. **All three indicators come back null** — no
sign-consistent, significant relationship survives from explore into
holdout for any of them. Reported in full per this file's own rule (item
6: ship the null if it's null), not filed away quietly.

### The hypothesis, written down before looking

1. RSI(14) < 30 ("oversold") predicts a bounce (positive forward return);
   RSI(14) > 70 ("overbought") predicts a pullback (negative forward
   return).
2. Price above its 200-day moving average (an uptrend) predicts
   continuation; below predicts further weakness (trend-following).
3. 60-trading-day trailing momentum predicts the next window's return —
   the sign of the correlation answers both competing beliefs at once
   (positive = continuation, negative = mean-reversion).

**Falsified (per indicator) if:** the correlation is not significant, or
does not survive from explore into holdout in the same direction.

### Holdout discipline

Cost: **$0** — uses only the owned Yahoo 5-year dev cache, no Sectors
call, and (unlike H1/H5) no snapshot field either, so the usual
predictor-before-outcome risk doesn't apply: every indicator is computed
strictly from `close` values up to the signal date, forward return
measured strictly after it, by construction. Explore/holdout split by
calendar year of the signal date, same boundary H5 uses for consistency:
explore = 2021–2023 signal dates, holdout = 2024–2026.

**Sampling design — avoiding the pseudo-replication bug found and fixed
in H5's stress test this session, before it could recur:** one signal
date per stock roughly every 20 trading days (~1 month), with a
20-trading-day forward-return horizon, so consecutive sample windows for
the same stock are back-to-back rather than overlapping. Uses `close`
(raw price), not `adjclose` — same reasoning as H1: a technical signal is
about the chart a trader actually watches, not a dividend-adjusted series.

Full runnable code: `pipeline/hypotheses/h14_technical_indicators.py`.
Explore only: `.venv/bin/python -m pipeline.hypotheses.h14_technical_indicators`.
With holdout (touched once, this run): `... --confirm-holdout`.

### What we found

| Indicator | Explore ρ | Explore t | Holdout ρ | Holdout t | Sign-consistent? |
|---|---|---|---|---|---|
| RSI(14) vs next-20-day return | −0.056 | −6.56 | +0.021 | +3.41 | **No — flips** |
| price-vs-200d-MA vs next-20-day return | +0.006 | +0.75 | −0.042 | −6.94 | **No — explore null, holdout flips negative** |
| 60-day momentum vs next-20-day return | +0.006 | +0.68 | −0.012 | −2.00 | **No — explore null, holdout weakly negative** |

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
their own baseline by a similar amount — no differentiation between the
two supposedly opposite signals, which is itself evidence against the
belief. In holdout, "overbought" (43.6%) actually beat "oversold"
(36.7%) — the *opposite* of what the bounce/pullback belief predicts.
None of this is a stable pattern; it moves around between phases in ways
that look like noise, not signal.

### What it means in plain language

**None of the three most common retail technical indicators predicted
IDX returns in a way that held up.** RSI showed a real, significant
relationship in explore — but it flipped sign in holdout, which is
exactly the outcome an honest holdout test exists to catch (a purely
in-sample pattern that doesn't generalize). The 200-day moving average
and momentum signals were statistically indistinguishable from zero in
explore and only picked up a weak, opposite-of-expected signal in
holdout. **A user following any of these three signals on IDX would not
have had a real edge over the base rate.**

### Why it came out this way (inferred, not verified)

Not independently investigated this session — noted as a plausible,
unverified explanation rather than left blank: retail technical
indicators are backward-looking, price-only heuristics with no
theoretical link to a specific market's fundamentals; their most common
empirical support comes from developed, highly liquid markets with
different microstructure (tick size, participation mix) than IDX, where
H1 already found free float and liquidity effects on volatility that
don't hold universally. A genuinely thin/illiquid market could plausibly
break the assumptions (continuous, efficiently-arbitraged price
discovery) these indicators are built on — but this is speculation, not
a tested explanation, and is not claimed as one.

### Limits

- **This module cannot rule out a shorter or longer horizon working
  where the 20-trading-day one tested here didn't** — a genuinely
  different pre-registered horizon would be a new trial, not a re-run of
  this one.
- **Sample points from the same stock across nearby months are not
  fully independent draws**, even with the ~20-day spacing designed to
  remove the dominant mechanical overlap (see the module docstring) — no
  claim of full independence is made; this is a real, acknowledged
  limitation shared with every panel-style test in this project.
- **Dev-only price data, same status as H1/H5:** every number here comes
  from Yahoo, never shipped, and owes the same Sectors price cross-check
  already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 6** (H1, H1b, H5, plus 3 new: RSI, MA, momentum) — each
  of the three indicators is one pre-registered trial (explore phase
  doesn't count separately, matching how H5's explore phase is treated).

### What it opens up

- **This is exactly the content the honesty scoreboard exists for** —
  "RSI/moving-average/momentum: no link found on IDX" is a plain,
  directly usable sentence for a user about to trust a chart signal, and
  no competitor product publishes anything like it.
- **Chunk P's remaining method upgrades** (future-shifted-timestamp
  placebo, Monte Carlo permutation) could be applied here as a further
  robustness check, but given all three indicators already failed the
  much simpler explore→holdout sign-consistency bar, that additional
  work is low-priority against other queued items.

---

## H15 — Do technical × fundamental factor combinations predict returns on IDX better than either factor alone?

**Date:** 2026-09-12. **Status:** Tested, explore + holdout, with a real
holdout confirmation run. **All three pre-registered interactions come
back null** — no combination clears both the usual and the stricter
multiple-comparisons bar with sign agreement between explore and
holdout. Reported in full per this file's own rule (item 6: ship the
null if it's null).

### Why this hypothesis exists, and what it deliberately is NOT

H14 tested RSI, 200-day-MA position, and momentum standalone and found
all three null — and literature search confirmed IDX-specific research
on these three already exists and disagrees with itself, so re-testing
them one at a time adds little. The more original question: does
**combining** a technical signal with a fundamental one predict anything
neither predicts alone — something no retail screener tests, since they
only ever show factors in isolation.

**Not a composite score.** `CLAUDE.md`'s hard constraint — *"No score or
combined verdict across findings"* — governs anything this project
ships; a weighted/blended signal is exactly what it forbids. This is
also the statistically sounder choice independent of that rule: a fitted
multi-factor model has many tunable parameters against a holdout of only
~600-1,200 rows — the same setup that produced H5's size leg, a result
that looked real until it needed to survive out-of-sample. Chosen
instead: **3 pre-registered, theory-justified interaction tests**, the
same low-free-parameter design that already worked for H1 and H5. If any
interaction had survived, it would have become its own finding card with
its own limits — never a "buy/sell algorithm."

### Pre-registered interactions (written before looking at results)

1. **Cheap (top-tercile earnings_yield, `pe>0` only) × oversold
   (RSI(14) < 30).** Why expect one: a temporarily oversold cheap stock
   is a different situation from an oversold expensive one — value
   provides a floor an overbought/expensive stock lacks.
2. **Quality (top-tercile ROE) × uptrend (price above its 200-day MA at
   formation).** Why expect one: trend-confirmation — good fundamentals
   the market hasn't priced in should show sustained price strength.
3. **High leverage (top-tercile debt-to-equity) × downtrend (price at or
   below its 200-day MA).** Why expect one: risk-confirmation — leverage
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
year)**, not H14's dense monthly sampling — the fundamental side only
changes once a year, so resampling technical signals monthly around a
fixed yearly fundamental value would add rows without adding independent
information. Terciles for the "top tercile" factors are computed
**separately within each phase's own pooled sample** — explore terciles
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
- **Interaction 2 (quality × uptrend) — the one case that looks
  interesting, and why it still doesn't survive:** holdout shows the
  combo beating quality-alone (t=+2.50, clears the usual 1.96 bar) but
  *losing* to uptrend-alone (t=−2.33) — the standout performer in
  holdout was **uptrend by itself** (+34.8% mean), not the combination.
  Neither comparison clears the stricter Bonferroni-style bar this
  module's own output states (~2.6 for 6 simultaneous tests), and explore
  showed neither comparison anywhere near significant (t=+0.49, −1.20)
  — no sign-agreement between phases. Falsified by this hypothesis's own
  pre-registered criteria.
- **Interaction 3 (high leverage × downtrend):** null in both phases.

**None of the three pre-registered combinations added anything beyond
what a single factor already captured.** This is a comprehensive null,
not a partial one — every one of the 6 holdout comparisons either misses
the loose bar, misses the stricter bar, or (interaction 2) actually shows
a single factor alone outperforming the combination.

### Comparison against H1 and H5 (the question this hypothesis exists to answer) — plain numbers, side by side, never combined

| Finding | Type | Explore/main ρ (t) | Holdout ρ (t) |
|---|---|---|---|
| **H1** — free float vs volatility | Single factor | (exploratory only, no holdout split) | ρ=+0.177, t=+5.42 (n=913) |
| **H5 value** — earnings yield vs return | Single factor | ρ=+0.166, t=+5.77 (n=1171) | ρ=+0.088, t=+2.99 (n=1148) |
| **H5 size** — market cap vs return | Single factor | ρ=+0.002, t=+0.05 (n=1171) | ρ=−0.183, t=−6.31 (n=1148) — single-year-driven, unconfirmed |
| **H15** — best-surviving interaction | Combination | none clear the pre-registered bar | none clear the pre-registered bar |

**Answering the user's question directly:** combining technical and
fundamental factors, at least for these 3 theory-motivated pairs, does
**not** produce a stronger or more reliable signal than the single-factor
findings this project already has. H1's free-float result and H5's value
result — both single factors — remain the strongest evidence-backed
results in the project. This is a real answer, not a non-answer: it
means the "combination adds value" intuition, plausible on its face,
doesn't hold for these three specific combinations on this data.

### Limits

- **Only 3 combinations were tested — this is not a claim that NO
  technical×fundamental combination works on IDX**, only that these
  three theory-motivated ones don't. A different pairing (not
  pre-registered here) remains untested, and testing it now would be a
  new trial, not a re-run of this one.
- **Interaction 1's sample is restricted to profitable companies
  (`pe>0`)** — same limitation H5's value leg already carries, inherited
  here, not introduced by this module.
- **Small holdout cells for interaction 1** (`cheap AND oversold`,
  n=13) — a t-test on 13 observations is very low-powered; the null
  result there is weak evidence of absence, not strong evidence.
- **No p-value/FDR correction machinery exists in this project** (no
  scipy dependency) — t-statistics are reported against the same ~1.96
  asymptotic-normal threshold every other hypothesis module here uses,
  with an explicit stricter Bonferroni-style note (~2.6 for 6
  simultaneous holdout tests) rather than a computed p-value.
- **Dev-only price data, same status as H1/H5/H14:** every number here
  comes from Yahoo, never shipped, and owes the same Sectors
  price cross-check already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 9** (H1, H1b, H5, H14's 3 indicators, plus H15's 3
  interactions) — each interaction is one pre-registered trial (explore
  doesn't count separately, matching H5's own convention).

### What it opens up

- **Directly answers the question that motivated this hypothesis:**
  combining factors is not automatically better, at least not for
  arbitrary theory-plausible pairs — a genuinely useful, non-obvious
  finding for the honesty scoreboard, distinct from H14's "indicators
  don't work alone" finding.
- **The quality×uptrend near-miss is worth a plain-language callout on
  its own, separate from any combined claim:** in the holdout window,
  simply being above the 200-day MA (with no fundamental filter at all)
  outperformed everything else tested here, including the combination.
  That is itself closer to H14's already-published MA finding than to a
  new result — H14 found the *continuous* MA-distance correlation was
  null; this finds a *binary* above/below split had one strong holdout
  window. Worth flagging as a possible follow-up diagnostic (in the same
  spirit as H5's timing-precision check) rather than a standalone claim,
  since one strong holdout window from a binary split is exactly the
  single-period-fragile pattern H5's size leg already taught this
  project to distrust.

---

## H10 — Broad pre-registered feature screen: which single features predict IDX returns?

**Date:** 2026-09-12. Adopted 2026-09-09 (`docs/PLAN.md`'s H10 section),
built once the comprehensive screener sweep (`data/raw/universe_2026-09-12.json`,
`industry`/`sub_industry`/`earnings[YYYY]`/price bands) landed.

### Why this exists

H1 and H5 each answer "does this one specific thing predict returns" —
one feature, tested carefully. This asks the broader question a retail
screener never answers honestly: **of the popular signals people watch,
which actually hold up, tested all at once with the multiple-comparisons
correction that honesty requires?** Testing 20 unrelated things yields
~1 "significant" result by chance alone at the usual 5% threshold —
reporting only the winner is p-hacking. The discipline that prevents it:
every feature below is pre-registered (frozen before any result is
seen), tested identically in explore and holdout, and reported in full
— including nulls — with Benjamini-Hochberg FDR correction across the
whole batch.

### Pre-registered features (committed before running anything)

All seven are yearly `field[year]` values — snapshot fields are excluded
by rule (`CLAUDE.md`'s predictor-before-outcome constraint):

1. **earnings_yield** = 1/pe[year], pe>0 only. **Overlaps H5's already-
   confirmed value leg** — not independent evidence, kept for
   completeness under this module's different (sector-neutral-rank)
   methodology, disclosed rather than presented as fresh.
2. **roe[year]** — quality. H15 tested this only inside an interaction
   (quality × uptrend, null); first standalone test.
3. **debt_to_equity_ratio[year]** — leverage. Same story: H15 tested it
   only inside an interaction (high-leverage × downtrend, null); first
   standalone test. Predicted direction: negative.
4. **total_yield[year]** — realized dividend yield. Belief under test:
   "high dividend yield means better returns." Not tested standalone
   anywhere else in this project.
5. **size** = outstanding_shares[year] × raw close at formation.
   **Overlaps H5's size leg** (an unconfirmed lead there, not a
   validated finding) — disclosed, not independent evidence.
6. **revenue_growth** = revenue[year]/revenue[year−1] − 1, prior-year
   revenue > 0 only. Belief under test: growth persists (or is already
   priced in).
7. **payout_ratio** = total_dividend[year]/earnings[year], earnings>0
   only. Belief under test: a high payout predicts *worse* forward
   returns (the "unsustainable yield" story). Distinct outcome from the
   still-pending H4 (payout ratio → dividend CUT) despite the same
   ratio construction — no overlap in what's being predicted.

No interaction terms — H15 already covers pre-registered interactions
under its own trial count; repeating them here would double-count.

### Method

**Sector-neutral ranks, not raw pooled values** — decided before
building: a bank's P/E isn't comparable to a miner's, so each feature is
converted to a percentile rank *within the company's own sub_sector*
(`pipeline.stats.sector_neutral_rank`, new this module) before pooling
across all 33 sub-sectors. Strips systematic sector differences while
keeping the full sample.

**Explore/holdout: the same boundary H1/H5/H14/H15 already use** —
2022–2023 explore, 2024–2025 holdout, May-1-to-Sep-4 formation-lag
window, imported directly from `h5_value_size.py` so this can't
silently drift from that boundary.

**Multiple-comparisons correction, pre-declared:** Benjamini-Hochberg
FDR at q=0.10 across all 7 holdout tests (`pipeline.stats.
benjamini_hochberg`, new this session — p-values via the standard-normal
approximation this project already implicitly uses for its ~1.96
threshold, `math.erfc`, no scipy). Explore doesn't count as a separate
trial (matching H5/H15's own convention).

**A feature is called CONFIRMED only if it clears FDR *and* explore and
holdout agree in sign** — FDR survival alone is not enough, matching
every earlier hypothesis here (a result that only shows up in one phase
is exactly H5's own already-documented size-leg weakness).

Full runnable code: `pipeline/hypotheses/h10_broad_feature_screen.py`.

### What we found

**Holdout, n=1,774 pooled (symbol, formation-year) rows** (per-feature n
varies — see table; not every feature is defined for every row, e.g.
`earnings_yield` requires `pe>0`):

| Feature | Explore rho/t | Holdout rho/t (p) | FDR (q=0.10) | Sign agreement | Verdict |
|---|---|---|---|---|---|
| earnings_yield | +0.162 / +5.66 | +0.120 / +4.26 (p<0.0001) | survives | same | **CONFIRMED** (overlaps H5) |
| total_yield (dividend yield) | +0.079 / +1.95 | +0.078 / +2.06 (p=0.040) | survives | same | **CONFIRMED — new** |
| size (small→higher return) | −0.027 / −1.11 | −0.199 / −8.00 (p<0.0001) | survives | same | **CONFIRMED** (overlaps H5's size lead) |
| revenue_growth | −0.002 / −0.06 | +0.051 / +2.07 (p=0.038) | survives | **flipped** | NOT confirmed |
| roe (quality) | +0.019 / +0.76 | −0.025 / −1.04 (p=0.301) | does not survive | flipped | NOT confirmed |
| debt_to_equity_ratio (leverage) | −0.011 / −0.45 | −0.024 / −1.00 (p=0.318) | does not survive | same | NOT confirmed |
| payout_ratio | +0.007 / +0.17 | +0.016 / +0.42 (p=0.676) | does not survive | same | NOT confirmed |

**Three of seven confirmed, four null** — reported in full regardless.

### What's new here, not just a re-run

**Dividend yield → better returns is a genuinely new confirmed finding**
— `docs/PRODUCT.md`'s honesty-scoreboard row for this belief was marked
"untested" until this run; it is now the second real, positive finding
alongside H1 and H5's value leg. Modest (rho ≈ +0.08), same order of
magnitude as H5's value effect, but consistent in sign and significant
in both phases.

**The size result here is on firmer footing than H5's own size leg**,
and this needs stating plainly because it looks at the same underlying
relationship two different ways: H5's own timing-precision diagnostic
(`h5_timing_diagnostic.py`, see above) found its size effect
concentrated almost entirely in the 2024→2025 (post-rate-cut) holdout
window — "confirmed in one year" was H5's stated, unresolved weakness.
Here, the same size proxy, tested by pooling formation years within
each phase (2022+2023 explore vs. 2024+2025 holdout) and ranking
sector-neutrally rather than per-year, shows the *same negative sign* in
both phases, with holdout far stronger than explore (t=−1.11 → t=−8.00).
**This does not resolve H5's weakness** — the holdout is still dominated
by the same 2024→2025 window driving H5's own result, and the two
modules share the same underlying price data, so this is not
independent replication in the strict sense. But the sign holding in
explore too (even if weakly) is evidence H10's own pre-registration
didn't have when H5 was first written up. Treat this as "somewhat
firmer than before," not "resolved."

### Limits

- **earnings_yield and size are not independent evidence** — both
  overlap H5's already-published legs; their appearance in this table is
  disclosure of the overlap, not a second confirmation from a different
  dataset.
- **revenue_growth's holdout significance is not trustworthy** — it
  survives FDR but its sign flipped from explore (−0.002, essentially
  zero) to holdout (+0.051, barely significant). A near-zero explore
  estimate flipping sign under a different sample is weak evidence of
  nothing, not evidence of a real relationship the correction merely
  detected. Reported for completeness, not treated as confirmed.
- **total_yield's n is much smaller than the other features** (603
  explore, 701 holdout) — many stocks pay no dividend in a given year,
  so this factor is only defined for a dividend-paying subset. The
  effect may not generalize to non-payers by definition.
- **Sector-neutral ranking assumes sub_sector is the right comparison
  group** — the same 13-of-33-sub-sectors-under-15-companies problem
  `docs/PLAN.md` already documents for the product's peer groups applies
  here too; a handful of tiny sub-sectors contribute noisy within-group
  ranks.
- **No p-value/FDR machinery existed in this project before this
  module** — the p-values here use a standard-normal approximation
  (`math.erfc`), the same asymptotic assumption every earlier
  hypothesis's ~1.96 threshold already implicitly relied on, now made
  numeric rather than a new, unverified method.
- **Dev-only price data, same status as H1/H5/H14/H15:** every number
  here comes from Yahoo, never shipped, and owes the same Sectors
  price cross-check already tracked in `BACKLOG.md` (`docs/PLAN.md` §8.3).
- **Trial count: 16** (H1, H1b, H5, H14's 3 indicators, H15's 3
  interactions, plus H10's 7 features) — each feature is one
  pre-registered trial (explore doesn't count separately, matching
  H5/H14/H15's own convention).

### What it opens up

- **A second real, positive, user-facing finding** (dividend yield) —
  directly powers a finding card and updates the honesty scoreboard from
  "untested" to "yes, modestly," alongside H1 and H5.
- **The scoreboard itself gets three more null rows** (quality, leverage,
  growth, payout — 4 of 7 null) — exactly the content `docs/PLAN.md`
  argues is itself a differentiator: "we tested 7 more things; 3 held up."
- **H4** (payout ratio → dividend cut, a different outcome) remains
  unaffected by payout_ratio's null result here — that tested payout
  ratio against *return*, not against *whether the dividend gets cut*;
  still a live, distinct candidate.

---

## H16 — Of IDX stocks, how many actually beat the alternatives to picking them?

**Date:** 2026-09-12. **NOT a falsifiable predictive hypothesis** — no
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
2018) asked of the entire US market since 1926 — nobody has published
an IDX version. His finding: 4 of 7 US stocks underperformed T-bills
over their lifetime, and the best-performing 4% of firms explain the
*entire* market's net wealth creation above cash; the other 96%
collectively just matched it. That comes from positive skew (a handful
of huge winners), not from typical stocks being good bets.

**Honest scope limitation, stated up front:** Bessembinder used ~90
years of data; this uses the ~5 years of Yahoo price history this
project already owns. This measures "how IDX stocks did over roughly
2021–2026," not "over their lifetimes" — a narrower, different claim
from his, not a like-for-like replication.

### The five benchmarks, and why each was chosen (decided with the user, 2026-09-12)

1. **IDX Composite index (^JKSE)** — the standard "just buy the market."
2. **Gold, in rupiah.** Verified via search: **67% of Indonesians hold
   gold** as an investment; it returned **32% (2024) and 44% (2025
   YTD)** in rupiah terms `[snippet]`. For much of this product's
   target audience this may be the *actual* alternative to buying a
   stock, not a theoretical one.
3. **Bank deposit / BI policy rate.** No API exposes this as a queryable
   series — built from a small manually-compiled table, sourced
   directly from `bi.go.id` for 2025–2026 (`[fetched]`, day-precise) and
   a secondary aggregator for 2021–2024 (`[snippet]`, month-precise).
   One disclosed gap: the exact date of the drop from 5.25% (Jul 2025)
   to 4.75% (by Dec 2025) wasn't pinned down — approximated as a single
   step at the later, verified date. Proxies a floating-rate deposit,
   not any specific bank's actual (typically lower) offered rate.
4. **The typical stock, not just the index — Bessembinder's actual
   point.** The cap-weighted index is itself dragged up by the same
   handful of giant winners a given stock was never realistically going
   to weight like. Computed as the cross-sectional median of every
   stock's own annualized return.
5. **Sector/sub-sector peer median** — reuses the peer-group split
   already planned for the product's 4 lenses.

### How we tested it

Each stock's OWN available window in the Yahoo cache (first to last
timestamp), not a forced common window — a forced window would bias
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
  median — the right-skewed shape Bessembinder describes: a few big
  winners pull the average up while the typical stock trails it.
- Bottom decile (88 stocks): mean **−36.1%** annualized.
- Top decile (88 stocks): mean **+68.0%** annualized.
- **418 of 887 stocks (47.1%) had a negative annualized return** over
  their own available window.

### What it means in plain language

**Roughly a coin flip against the index, but a landslide loss against
gold.** Half of IDX stocks didn't even beat simply holding the index —
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
inside this project's own 5-year measurement window — a period-specific
tailwind for gold, not a claim that gold structurally beats IDX stocks
over all horizons. Stated as plausible, not tested: a different 5-year
window (e.g. one without a gold rally) could show a very different
gold-comparison number. This is exactly the kind of period-dependency
this project's own H1/H5 write-ups already flag for their findings — not
unique to H16.

### Limits

- **Not a lifetime measure** — see the scope limitation above. A stock
  that IPO'd in 2025 is measured over ~1 year, not 5; its annualized
  number carries much more noise than a stock measured over the full
  window. Not adjusted for here beyond the 1-year minimum.
- **Survivorship, in the direction this project's other findings don't
  usually have:** a stock that was suspended or effectively delisted
  mid-window and never resumed trading would show a truncated window
  ending at its last traded price, not a "zero" outcome — if any such
  cases exist in the 887, this could modestly overstate average
  performance. Not checked this session.
- **The BI-rate table's 2021–2024 entries are month-precision,
  `[snippet]`-sourced, not independently re-verified against `bi.go.id`
  day-by-day** — adequate for an annualized comparison over a 1-5 year
  window, not precise enough for a monetary-policy analysis.
- **Gold priced via GC=F (a US futures contract) × USDIDR=X, not a
  domestic Indonesian gold price (e.g. Pegadaian or Antam rates)** —
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
  scoreboard treatment** — "beat gold: 16%" is a single, visceral,
  directly usable sentence, more so than any correlation this project
  has produced.
- **Reframes the H14/H15 nulls as expected, not disappointing:** if
  most individual stocks are mediocre by the shape found here, it's
  unsurprising that short-horizon technical signals struggle to
  reliably separate the few winners from the many — the nulls and this
  finding tell one coherent story, not several unconnected ones.
- **Both product renderings planned, not yet built:** (1) home-page
  ranking of stocks by how they did against each benchmark; (2) a
  per-stock detail chart plotting that stock's own cumulative-return
  line against the index, gold, and typical-stock lines — free, reuses
  owned Yahoo data, no new Sectors call. Both deferred to the app-build
  phase (Chunk N), per the product's own "detailed product planning is
  its own pass" rule.

---

*(Next entries land here as later hypotheses are tested — see the
hypothesis register in `docs/PLAN.md` §6 for what's queued.)*
