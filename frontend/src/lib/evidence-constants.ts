/**
 * Numbers shown on the evidence pages that have no data/app source. Each is
 * pinned here with the EXPERIMENT.md section it was read from (checked
 * 2026-09-27), the same convention as H4_CUT_RATES in lib/situations.ts.
 * Percent values are as printed there; pages round them for display.
 */

/** Situation C (EXPERIMENT.md "C - still below the old peak"): stocks in the price cache, the denominator of "703 dari 887". */
export const CACHED_STOCKS = 887;
/** First year of the price cache (Sep 2021): "2021 sampai 2026" on the old-peak page. */
export const PRICE_CACHE_START_YEAR = 2021;

/** Earliest event in data/app/suspensions.json is 2018-12-28 (checked 2026-09-27): "sejak 2018" on the repeat-suspension page. */
export const PRICE_SUSPENSION_SINCE_YEAR = 2018;

/** H6 results, run once 2026-09-26 (EXPERIMENT.md "Results, H6"). Share of each list beating ^JKSE over 5 trading days. */
export const H6 = {
  holdout: { buy: 48.9, sell: 50.3, dates: 35 },
  explore: { buy: 44.7, sell: 45.9 },
  /** Descriptive, holdout: buy list return on the list day, sell list the same day, buy list over the previous 20 days. */
  listDay: { buy: 2.6, sell: -0.8 },
  prior20d: { buy: 6.7 },
  dates: 61,
  appearances: 3660,
  windowDays: 5,
  trial: 34,
  /** Smallest effect the test could detect, percent per 5 days. */
  minDetectable: 1.2,
};

/** H18 results, run once 2026-09-26 (EXPERIMENT.md "Results, H18"). Share of events beating ^JKSE over 20 trading days. */
export const H18 = {
  explore: { beat: 43.3, monthlyMean: 7.2, medianEvent: -2.1 },
  holdout: { beat: 50.7, monthlyMean: 3.0 },
  /** 314 events in 2025 plus 346 in 2026. */
  events: 660,
  /** 1,767 buy filings reduce to 660 events, one per stock per 60 days. The 1,767 is the H8b pull (EXPERIMENT.md, credit ledger); that the H18 file is that same pull is inferred, from the board copy. */
  filings: 1767,
  /** 10 explore months plus 8 holdout months. */
  months: 18,
  windowDays: 20,
  trial: 35,
};

/** Tests run so far, every result shown (EXPERIMENT.md trial counter; H18 is trial 35). */
export const TRIALS = 35;
