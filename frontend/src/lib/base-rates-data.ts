import { readFile } from "node:fs/promises";
import path from "node:path";

export interface LossMakerYear {
  from_year: number;
  to_year: number;
  n: number;
  turned_around: number;
  pct: number;
}

export interface LossMakerTurnaround {
  n: number;
  turned_around: number;
  pct: number | null;
  by_year: LossMakerYear[];
}

export interface DrawdownBucket {
  n: number;
  p25_pct: number;
  median_pct: number;
  p75_pct: number;
}

export interface TypicalDrawdown {
  overall: DrawdownBucket;
  by_size_tercile: { smallest: DrawdownBucket; mid: DrawdownBucket; largest: DrawdownBucket };
}

export interface RecoveryAfterFall {
  n_events: number;
  n_stocks: number;
  still_below_peak: { n: number; pct: number | null };
  recovered: { n: number; pct: number | null };
  still_down_median_gap_pct: number | null;
}

export interface SpikeBucket {
  n_events: number;
  share_below_event_close: number;
  median_change: number;
  p25_change: number;
  p75_change: number;
  share_deep_drop: number;
}

export interface RateCell {
  n: number;
  count: number;
  rate: number;
}

export interface RecentSpikeRates {
  pooled: SpikeBucket;
  first_event_per_stock: SpikeBucket;
  stocks_with_event: number;
}

export interface EarningsTwoYearDecline {
  pooled: RateCell;
  by_year: Record<string, RateCell>;
}

export interface EarningsMoreThanDoubled {
  gave_part_back: RateCell;
  gave_all_back: RateCell;
  by_year: Record<string, { gave_part_back: RateCell; gave_all_back: RateCell }>;
}

export interface LongBelowPeak {
  events_measurable: number;
  still_below_at_252: number;
  recovered_by_504: RateCell;
}

export interface RepeatSpikeSuspension {
  events: number;
  stocks: number;
  eligible_events: number;
  followed_within_365d: number;
  share_followed: number;
  followed_by_gap_over_7d: number;
  share_followed_by_gap_over_7d: number;
  stocks_with_2_or_more: number;
}

export interface NearPeakEarningsDecline {
  pooled: { n: number; negative: number; share_negative: number };
}

export interface PayoutAbove100CutRate {
  explore: { n: number; cuts: number; cut_rate: number };
  holdout: { n: number; cuts: number; cut_rate: number };
}

export interface BaseRatesData {
  as_of: string;
  note: string;
  recent_spike: RecentSpikeRates;
  earnings_two_year_decline: EarningsTwoYearDecline;
  earnings_more_than_doubled: EarningsMoreThanDoubled;
  loss_maker_turnaround: LossMakerTurnaround;
  typical_drawdown: TypicalDrawdown;
  recovery_after_fall: RecoveryAfterFall;
  long_below_peak: LongBelowPeak;
  repeat_spike_suspension: RepeatSpikeSuspension;
  near_peak_earnings_decline: NearPeakEarningsDecline;
  payout_above_100_cut_rate: PayoutAbove100CutRate;
}

/**
 * Reads data/app/base_rates.json, written by
 * pipeline/appdata/build_base_rates.py. Server-only (fs): never import
 * from a "use client" component.
 *
 * Two of the three results here (typical_drawdown, recovery_after_fall)
 * trace back to development-only Yahoo Finance price history, same
 * disclosure status as data/app/beat_gold.json (docs/PRODUCT.md §7.3):
 * `note` and `as_of` carry that through to whatever renders this data;
 * never drop them. All three are descriptive base rates, not predictions
 * for any individual stock: never render one as if it forecasts a
 * specific stock's future.
 */
export async function getBaseRatesData(): Promise<BaseRatesData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "base_rates.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as BaseRatesData;
}
