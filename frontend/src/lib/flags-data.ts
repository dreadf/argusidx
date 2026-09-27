import { readFile } from "node:fs/promises";
import path from "node:path";
import { stripJk } from "@/lib/format";

export interface FlagBucket<T> {
  flagged: T[];
  evaluable_count: number;
  flagged_count: number;
}

export interface FlagsData {
  as_of: string;
  source_file: string;
  payout_above_earnings: FlagBucket<{ symbol: string; company_name: string | null; payout_ratio: number }>;
  near_ath_earnings_decline: FlagBucket<{
    symbol: string;
    company_name: string | null;
    pct_below_ath: number;
    earnings_2025: number;
    earnings_2024: number;
  }>;
  yield_far_above_average: FlagBucket<{ symbol: string; company_name: string | null; yield_ttm: number; yield_avg: number }>;
  /** Was typed `null` here: stale from before this flag was implemented.
   * The real data/app/flags.json has always carried a populated bucket. */
  lq45_low_float: FlagBucket<{ symbol: string; company_name: string | null; free_float: number }>;
}

/**
 * Reads data/app/flags.json, written by pipeline/appdata/build_flags.py.
 * Server-only (fs): never import from a "use client" component.
 */
export async function getFlagsData(): Promise<FlagsData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "flags.json");
  const raw = await readFile(filePath, "utf-8");
  const parsed = JSON.parse(raw) as FlagsData;
  const stripBucket = <T extends { symbol: string }>(bucket: FlagBucket<T>): FlagBucket<T> => ({
    ...bucket,
    flagged: bucket.flagged.map((row) => ({ ...row, symbol: stripJk(row.symbol) })),
  });
  return {
    ...parsed,
    payout_above_earnings: stripBucket(parsed.payout_above_earnings),
    near_ath_earnings_decline: stripBucket(parsed.near_ath_earnings_decline),
    yield_far_above_average: stripBucket(parsed.yield_far_above_average),
    lq45_low_float: stripBucket(parsed.lq45_low_float),
  };
}
