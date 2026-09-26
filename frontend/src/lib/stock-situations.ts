import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Per-stock situations from data/app/situations.json (built by the
 * pipeline; not the hub copy in lib/situations.ts). Server-only (fs).
 * `older_fall` is deliberately not a situation: a fall older than the
 * window is context, not something the stock is in now.
 */
export type SituationKey = "fall" | "loss_year" | "recent_price_suspension" | "recent_ipo" | "recent_spike" | "earnings_two_year_decline" | "earnings_more_than_doubled";

export const SITUATION_KEYS: SituationKey[] = ["fall", "loss_year", "recent_price_suspension", "recent_ipo", "recent_spike", "earnings_two_year_decline", "earnings_more_than_doubled"];

export interface StockSituationEntry {
  older_fall: unknown | null;
  [key: string]: unknown;
}

export interface SituationsFile {
  as_of: string;
  counts: Record<string, number>;
  by_symbol: Record<string, StockSituationEntry>;
}

export async function getSituationsFile(): Promise<SituationsFile> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "situations.json");
  return JSON.parse(await readFile(filePath, "utf-8")) as SituationsFile;
}

/** Situation keys a stock is currently in (non-null entries only). */
export function situationsOf(file: SituationsFile, code: string): SituationKey[] {
  const entry = file.by_symbol[`${code}.JK`];
  if (!entry) return [];
  return SITUATION_KEYS.filter((k) => entry[k] != null);
}
