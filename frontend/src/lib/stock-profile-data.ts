import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * data/app/stock_profile.json, written by
 * pipeline/appdata/build_stock_profile.py: the numbers the stock page reads
 * beyond stocks.json. Every "higher/cheaper than N of 100" share is computed
 * there, once. Server-only (fs).
 */

/** Five values, one per year in `years` (2021..2025); null when not reported. */
type Yearly = (number | null)[];

export interface StockProfile {
  pe_ttm: number | null;
  forward_pe: number | null;
  pb_mrq: number | null;
  ps_ttm: number | null;
  yield_ttm: number | null;
  payout_ratio: number | null;
  dividend_yield_avg: number | null;
  roe_ttm: number | null;
  der_mrq: number | null;
  daily_close_change: number | null;
  revenue: Yearly;
  earnings: Yearly;
  roe: Yearly;
  der: Yearly;
  dividend: Yearly;
  pe: Yearly;
  w52_low_date: string | null;
  w52_high_date: string | null;
  d90_low: number | null;
  d90_high: number | null;
  all_time_low: number | null;
  all_time_low_date: string | null;
  all_time_high: number | null;
  all_time_high_date: string | null;
  last_ex_dividend_date: string | null;
  indices: string[];
  /** Fraction, -0.109 = -10,9%, between change_window.start and .end. */
  change_1y: number | null;
  sector_rank_1y: { better: number; n: number } | null;
  /** P/E > 0 and 2025 not a loss year; otherwise P/E is never compared. */
  pe_meaningful: boolean;
  /** Shares 0..100 among all stocks with a value (see the builder's docstring). */
  pe_cheaper_than: number | null;
  yield_higher_than: number;
  /** Among dividend payers only; "high dividend" is judged on this. Null for a non-payer. */
  yield_higher_than_payers: number | null;
  roe_higher_than: number | null;
  der_higher_than: number | null;
  free_float_higher_than: number | null;
  revenue_growth: number | null;
  revenue_growth_higher_than: number | null;
  size_third: "small" | "mid" | "large" | null;
  daily_gain_rank: number | null;
  foreign_buy_days: number;
  foreign_sell_days: number;
}

export interface ProfileMeta {
  as_of: string;
  years: number[];
  change_window: { start: string; end: string };
  ihsg_change_1y: number;
  foreign_flow: { days: number; first: string; last: string };
}

interface ProfileFile extends ProfileMeta {
  stocks: Record<string, StockProfile>;
}

let cache: ProfileFile | null = null;

async function load(): Promise<ProfileFile> {
  if (cache) return cache;
  const raw = await readFile(path.join(process.cwd(), "..", "data", "app", "stock_profile.json"), "utf-8");
  cache = JSON.parse(raw) as ProfileFile;
  return cache;
}

export async function getStockProfile(code: string): Promise<StockProfile | null> {
  return (await load()).stocks[`${code.toUpperCase()}.JK`] ?? null;
}

export async function getProfileMeta(): Promise<ProfileMeta> {
  const { as_of, years, change_window, ihsg_change_1y, foreign_flow } = await load();
  return { as_of, years, change_window, ihsg_change_1y, foreign_flow };
}

/** Number of stocks ranked by one-day gain on the snapshot date. */
export async function getGainRankCount(): Promise<number> {
  return Object.values((await load()).stocks).filter((s) => s.daily_gain_rank !== null).length;
}
