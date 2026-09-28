import { readFile } from "node:fs/promises";
import path from "node:path";

export interface MarketConditionData {
  ihsg_source_file: string;
  rankings_as_of: string;
  ihsg: {
    date: string;
    close: number;
    /** T1's rule. T1 was not confirmed: a description of today, never a forecast. */
    state: "tertekan" | "normal";
    pct_from_peak: number;
    peak_date: string;
    peak_close: number;
    pct_vs_ma200: number;
    /** 0-100: today's 20-day volatility within its own history since 2019. */
    vol20_percentile: number;
    days_since_peak: number;
    rule: { below_peak_and_ma200: boolean; volatility_above_p90: boolean };
  };
  distance_from_high: { n: number; median: number; n_down_30_or_more: number; bins: number[] };
}

/**
 * Reads data/app/market_condition.json, written by
 * pipeline/appdata/build_market_condition.py. Server-only (fs): never
 * import from a "use client" component.
 */
export async function getMarketConditionData(): Promise<MarketConditionData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "market_condition.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as MarketConditionData;
}
