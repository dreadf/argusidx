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

export interface BaseRatesData {
  as_of: string;
  note: string;
  loss_maker_turnaround: LossMakerTurnaround;
  typical_drawdown: TypicalDrawdown;
  recovery_after_fall: RecoveryAfterFall;
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
