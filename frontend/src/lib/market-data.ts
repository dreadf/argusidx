import { readFile } from "node:fs/promises";
import path from "node:path";

export interface MarketData {
  as_of: string;
  source_file: string;
  breadth: { near_high: number; middle: number; near_low: number; excluded: number; total_evaluable: number };
  movers: { up: number; down: number; flat: number };
  intensity: { calm: number; moderate: number; choppy: number };
}

/**
 * Reads data/app/market.json, written by
 * pipeline/appdata/build_market.py. Server-only (fs) — this file must
 * never be imported from a "use client" component.
 */
export async function getMarketData(): Promise<MarketData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "market.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as MarketData;
}
