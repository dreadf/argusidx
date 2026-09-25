import { readFile } from "node:fs/promises";
import path from "node:path";

interface RoeFile {
  as_of: string;
  years: number[];
  sectors: Record<string, { median: (number | null)[]; n: number[] }>;
  by_symbol: Record<string, (number | null)[]>;
}

let cache: RoeFile | null = null;

async function load(): Promise<RoeFile> {
  if (cache) return cache;
  const filePath = path.join(process.cwd(), "..", "data", "app", "roe_history.json");
  cache = JSON.parse(await readFile(filePath, "utf-8")) as RoeFile;
  return cache;
}

export interface RoeHistory {
  years: number[];
  own: (number | null)[];
  sector: (number | null)[];
  sectorReporting: number[];
}

/**
 * ROE (percent) by year for one stock and its sector's median by year, from
 * data/app/roe_history.json (pipeline/appdata/build_roe_history.py).
 * Server-only (fs). Null when the stock reports no ROE in any year.
 */
export async function getRoeHistory(code: string, sector: string | null): Promise<RoeHistory | null> {
  const file = await load();
  const own = file.by_symbol[`${code}.JK`];
  const sec = sector ? file.sectors[sector] : undefined;
  if (!own || !sec || own.every((v) => v === null)) return null;
  return { years: file.years, own, sector: sec.median, sectorReporting: sec.n };
}
