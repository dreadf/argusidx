import { readFile } from "node:fs/promises";
import path from "node:path";

export interface InsiderMarketSummary {
  universe_count: number;
  companies_with_activity: number;
  net_buying: number;
  net_selling: number;
  balanced: number;
  window: { start: string; end: number | string };
}

/**
 * Market-wide insider totals from data/app/insider_activity.json
 * (pipeline/appdata/build_insider_activity.py), used to put one stock's
 * buy/sell counts next to how many companies are net buyers or sellers.
 * Server-only (fs).
 */
async function load_getInsiderSummary(): Promise<InsiderMarketSummary> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "insider_activity.json");
  const parsed = JSON.parse(await readFile(filePath, "utf-8")) as { summary: Omit<InsiderMarketSummary, "window">; window: InsiderMarketSummary["window"] };
  return { ...parsed.summary, window: parsed.window };
}

let cached_getInsiderSummary: InsiderMarketSummary | null = null;

/** Parsed once per build/process: the stock page calls this for each of 962 pages, and re-reading the file each time exhausted memory during static generation. */
export async function getInsiderSummary(): Promise<InsiderMarketSummary> {
  if (cached_getInsiderSummary === null) cached_getInsiderSummary = await load_getInsiderSummary();
  return cached_getInsiderSummary;
}
