import { readFile } from "node:fs/promises";
import path from "node:path";

export interface SuspensionSummary {
  as_of: string;
  total_events: number;
  universe_count: number;
  companies_with_suspensions: number;
  base_rate_pct: number;
  /** Event counts by the exchange's reason group (Indonesian labels as published). */
  by_group: { label: string; count: number }[];
}

/**
 * Reads data/app/suspensions.json (pipeline/appdata/build_suspensions.py)
 * and totals the events by reason group. Server-only (fs).
 */
async function load_getSuspensionSummary(): Promise<SuspensionSummary> {
  const filePath = path.join(process.cwd(), "..", "data", "app", "suspensions.json");
  const parsed = JSON.parse(await readFile(filePath, "utf-8")) as {
    as_of: string;
    total_events: number;
    universe_count: number;
    companies_with_suspensions: number;
    base_rate_pct: number;
    by_symbol: Record<string, { group_label_id: string }[]>;
  };
  const counts = new Map<string, number>();
  for (const events of Object.values(parsed.by_symbol)) {
    for (const e of events) counts.set(e.group_label_id, (counts.get(e.group_label_id) ?? 0) + 1);
  }
  return {
    as_of: parsed.as_of,
    total_events: parsed.total_events,
    universe_count: parsed.universe_count,
    companies_with_suspensions: parsed.companies_with_suspensions,
    base_rate_pct: parsed.base_rate_pct,
    by_group: [...counts.entries()].map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count),
  };
}

let cached_getSuspensionSummary: SuspensionSummary | null = null;

/** Parsed once per build/process: the stock page calls this for each of 962 pages, and re-reading the file each time exhausted memory during static generation. */
export async function getSuspensionSummary(): Promise<SuspensionSummary> {
  if (cached_getSuspensionSummary === null) cached_getSuspensionSummary = await load_getSuspensionSummary();
  return cached_getSuspensionSummary;
}
