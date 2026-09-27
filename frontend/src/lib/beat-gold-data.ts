import { readFile } from "node:fs/promises";
import path from "node:path";
import { stripJk } from "@/lib/format";

export interface BeatGoldWinRate {
  wins: number;
  n: number;
  pct: number | null;
}

export interface BeatGoldSummary {
  research_date: string;
  n: number;
  beat_index: BeatGoldWinRate;
  beat_gold: BeatGoldWinRate;
  beat_deposit: BeatGoldWinRate;
  beat_typical_stock: BeatGoldWinRate;
  beat_sector_peer: BeatGoldWinRate;
  median_annualized_return_pct: number;
  mean_annualized_return_pct: number;
  negative_return: { count: number; n: number; pct: number };
}

export interface BeatGoldRow {
  symbol: string;
  company_name: string | null;
  years: number;
  beat_index: boolean | null;
  beat_gold: boolean | null;
  beat_deposit: boolean | null;
  beat_typical_stock: boolean;
  beat_sector_peer: boolean | null;
}

export interface BeatGoldData {
  as_of: string;
  note: string;
  summary: BeatGoldSummary;
  rows: BeatGoldRow[];
}

/**
 * Reads data/app/beat_gold.json, written by pipeline/appdata/build_beat_gold.py.
 * Server-only (fs): never import from a "use client" component.
 *
 * This is the ONE place in the product that traces back to Yahoo-sourced
 * data (docs/PRODUCT.md §7.3): a frozen, dated research result, computed
 * once, never a live Yahoo call. `note` and `research_date` carry that
 * disclosure through to whatever renders this data; never drop them.
 */
export async function getBeatGoldData(): Promise<BeatGoldData> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "beat_gold.json");
  const raw = await readFile(filePath, "utf-8");
  const parsed = JSON.parse(raw) as {
    as_of: string;
    note: string;
    summary: BeatGoldSummary;
    by_symbol: Record<string, Omit<BeatGoldRow, "symbol">>;
  };
  const rows = Object.entries(parsed.by_symbol).map(([symbol, data]) => ({ symbol: stripJk(symbol), ...data }));
  return { as_of: parsed.as_of, note: parsed.note, summary: parsed.summary, rows };
}
