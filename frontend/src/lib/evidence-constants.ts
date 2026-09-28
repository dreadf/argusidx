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

/**
 * All 437 price-increase suspensions in data/raw/suspensions_2026-09-13.json fall between
 * January 2025 and September 2026 (323 in 2025, 114 in 2026; checked 2026-09-27). The
 * file holds 588 events in all, 535 of them since 2025 and the first in December 2018.
 */
export const PRICE_SUSPENSION_SPAN = "Januari 2025 sampai September 2026";
export const SUSPENSIONS_SINCE_2025 = 535;
export const SUSPENSIONS_TOTAL = 588;

/**
 * Stress-test results (EXPERIMENT.md "Results, stress tests 2026-09-27", run once,
 * pre-registered 2026-09-27). Percent values are as printed there.
 */
export const STRESS = {
  /** Situation C by trigger year and by size tercile (description only). */
  c: { year2021: 7.0, year2023: 18.0, smallest: 7.7, largest: 19.5 },
  /** Situation S2: one event per stock, and a 180-day instead of 365-day window. */
  s2: { firstPerStock: 68.0, firstStocks: 97, window180: 44.4 },
  /** Ordinary rates for comparison (EXPERIMENT.md ST3). */
  ordinary: { i3Negative: 35.5, i3BeatMedian: 48.7, i9CutAllPayers: 46.0 },
};

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

