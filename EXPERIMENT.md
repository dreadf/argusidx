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

**Date:** 2026-09-06
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
   Finance (free, development-time only — see `pipeline/dev/`). 853 of
   961 had enough history to use.
3. For each stock, computed how much its price swings day to day
   (annualized volatility) and its worst fall from a peak (max
   drawdown) over that year.
4. Sorted all 853 stocks by free float into five equal groups
   (quintiles) and compared the groups.
5. Measured the relationship with a rank correlation (Spearman's rho)
   and checked whether it could be coincidence (the t-statistic).

Full runnable code: `pipeline/hypotheses/h1_free_float.py`. Run with
`python -m pipeline.hypotheses.h1_free_float` — every number below comes
from that command, byte-for-byte.

### What we found

The opposite of what we expected, and not by a small margin.

- The fifth of stocks with the **least** public ownership (about 9% of
  shares) swung about **60%** a year.
- The fifth with the **most** public ownership (about 49% of shares)
  swung about **90%** a year.

So wide-float stocks were the wild ones, not the thin-float ones. The
odds this is a coincidence are under 1 in a million (rho = +0.225,
t = +6.72 — a t-statistic that large essentially never happens by chance).

There was **no relationship at all** between free float and how much
money a stock actually made or lost over the year (rho = +0.007,
statistically indistinguishable from zero). This finding is about how
bumpy the ride was, not where it ended up.

### Two ways this could have been a false alarm — both checked and ruled out

**Could it be that thin-float stocks just don't trade much, so their
prices only look calm because nobody's actually buying or selling?**
We checked by counting, for every stock, how many days its price didn't
move at all. Thin-float stocks sat still on 14.2% of days; wide-float
stocks sat still on 13.1% of days — almost identical. We also reran the
whole test using only stocks that genuinely trade often, and the result
held up just as strongly.

**Could this just be describing the 2026 market crash**, where foreign
investors pulled money out of Indonesia and hit the big, widely-owned
stocks hardest for reasons that have nothing to do with free float? We
checked by running the same test separately for every year from 2022 to
2026. The same pattern showed up **every single year**, and it's been
getting stronger, not weaker — the opposite of what a one-off crash
explanation would predict.

### A confound we did find, and it sharpened the finding

We wondered whether "free float" was secretly just a stand-in for
"company size" (big companies vs small ones). It isn't — the two are
barely related. But splitting stocks into four groups by size and
re-running the test inside each group revealed something more precise:

**The whole effect lives in small companies.** Among the smallest IDX
companies, high-float stocks swing about **102%** a year against **75%**
for closely-held ones — a huge gap. Among the largest companies, free
float barely matters at all (53% vs 47%).

### What this means, in one sentence

**Among small Indonesian companies, the ones where a lot of stock is
publicly available are far more turbulent than the ones a founder or
family still tightly controls — which is the opposite of the common
warning that thinly-held stocks are the dangerous ones.**

### Why it might be true

A guess, not yet tested: a tightly-held small company barely trades —
whoever owns most of it isn't selling — so its quoted price barely
moves. A widely-held small company is one the public actually owns and
actively trades, and the public trading it is exactly what makes it
choppy. This would mean "low liquidity" and "low free float" are not
the same danger signal, even though they're often talked about as if
they were.

### Limits — read this before using the finding anywhere

- **This describes volatility, not money made or lost.** A stock can be
  wildly turbulent and still go up. Don't read "turbulent" as "bad."
- **Correlation, not cause.** We haven't shown *why* — only that the two
  things move together, reliably, across five years.
- **Exploratory, not confirmatory.** This was tested on all the data at
  once, with nothing held back to check against later. Its strength
  comes from holding up across five separate years, not from a formal
  train/test split. Later hypotheses (H2 onward) should hold out a
  period and test against it properly, per RULES.md.
- **Unresolved tension with the manipulation ("gorengan") literature**,
  which treats *low* free float as the dangerous signal. Both could be
  true at once if manipulated stocks are a small enough group that they
  don't move the average for all 961 companies — or "free float" in
  that context might mean something slightly different than the public
  ownership percentage used here. We haven't resolved this.
- **Trial count: 1.** This is the first hypothesis tested. Any claim
  made from this finding should say so, the same way Argus (the
  previous project) always quoted its Deflated Sharpe Ratio together
  with how many things had been tried.

### What this opens up

- A defensible, real finding for the "sizing up a stock" part of the
  product (see the plan's product design section).
- Worth a second look at whether "free float" and "genuinely thin
  liquidity" should be treated as different measurements, not the same
  one, given the gorengan-literature tension above.
- H1b (queued, free — uses data already owned): does the *drawdown*
  relationship survive the same size-control test that volatility did?

---

*(Next entries land here as later hypotheses are tested — see the
hypothesis register in the plan file for what's queued.)*
