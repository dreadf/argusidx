import { readFile } from "node:fs/promises";
import path from "node:path";

export interface RateInterval {
  count: number;
  n: number;
  rate: number;
  wilson_low: number;
  wilson_high: number;
  cluster_low: number | null;
  cluster_high: number | null;
  wide: boolean;
}

interface UncertaintyFile {
  rates: Record<string, RateInterval>;
}

let cache: Promise<UncertaintyFile> | null = null;

function load(): Promise<UncertaintyFile> {
  cache ??= readFile(path.join(process.cwd(), "..", "data", "app", "base_rate_uncertainty.json"), "utf-8").then((t) => JSON.parse(t) as UncertaintyFile);
  return cache;
}

/**
 * "kisaran wajar 10 sampai 14 dari 100" for a base rate, from the 95% interval
 * (the stock-resampled one when the rate has repeated stocks, otherwise Wilson).
 * Null when the key is unknown.
 */
export async function rangeNote(key: string): Promise<string | null> {
  const r = (await load()).rates[key];
  if (!r) return null;
  const lo = r.cluster_low ?? r.wilson_low;
  const hi = r.cluster_high ?? r.wilson_high;
  return `kisaran wajar ${Math.round(lo * 100)} sampai ${Math.round(hi * 100)} dari 100${r.wide ? ", lebar" : ""}`;
}
