import type { CorporateActions, StockPageData } from "@/lib/stock-data";
import type { WatchItem } from "@/lib/stock-read";

/**
 * "Ada yang berubah" (the Pantau card's promise, board Baru4-Saham-*): a
 * small snapshot of what could change for a watched stock between data
 * refreshes, compared against what the browser last saw. No accounts, no
 * server state (docs/PRODUCT.md §11): the browser stores its own last-seen
 * fingerprint per symbol (watchlist-changes-store.ts) and sends it back on
 * every check; the server only recomputes the current one from data/app,
 * already-loaded local data, 0 Sectors credits.
 *
 * Deliberately narrow: only what `watchItems()` and `corporate_actions`
 * already track. No "laporan laba" event, because the data has yearly
 * totals, not a dated filing event, to track one against.
 */
export function isFingerprint(v: unknown): v is StockFingerprint {
  if (typeof v !== "object" || v === null) return false;
  const f = v as Record<string, unknown>;
  return Array.isArray(f.watch) && f.watch.every((k) => typeof k === "string");
}

export interface StockFingerprint {
  /** Sorted, de-duplicated WatchKind values currently active (situations and tanda alike). */
  watch: string[];
  lastDividendExDate: string | null;
  lastAgmDate: string | null;
  lastRightsExDate: string | null;
  lastSplitDate: string | null;
  lastSuspensionDate: string | null;
  insiderLastDate: string | null;
}

function maxDate(dates: (string | null | undefined)[]): string | null {
  const known = dates.filter((d): d is string => Boolean(d));
  return known.length === 0 ? null : known.reduce((a, b) => (a > b ? a : b));
}

function latestCorporateActionDates(ca: CorporateActions): Pick<StockFingerprint, "lastDividendExDate" | "lastAgmDate" | "lastRightsExDate" | "lastSplitDate"> {
  return {
    lastDividendExDate: maxDate(ca.dividends.map((d) => d.ex_date)),
    lastAgmDate: maxDate(ca.agms.map((a) => a.agm_date)),
    lastRightsExDate: maxDate(ca.rights_issues.map((r) => r.ex_date)),
    lastSplitDate: maxDate(ca.stock_splits.map((s) => s.date)),
  };
}

export function buildFingerprint(data: StockPageData, watch: WatchItem[]): StockFingerprint {
  return {
    watch: [...new Set(watch.map((w) => w.kind))].sort(),
    ...latestCorporateActionDates(data.corporate_actions),
    lastSuspensionDate: maxDate(data.suspension_history?.events.map((e) => e.date) ?? []),
    insiderLastDate: data.insider_activity?.last_transaction_date ?? null,
  };
}

const DATED_CHANGE: [keyof StockFingerprint, string][] = [
  ["lastDividendExDate", "Dividen baru tercatat"],
  ["lastAgmDate", "RUPS baru dijadwalkan"],
  ["lastRightsExDate", "Penawaran saham baru (rights issue)"],
  ["lastSplitDate", "Pemecahan saham baru"],
  ["lastSuspensionDate", "Disuspensi bursa"],
  ["insiderLastDate", "Laporan transaksi orang dalam baru"],
];

/**
 * What changed between the fingerprint the browser last saw and the current
 * one, as short Indonesian phrases. `seen === null` means this stock was
 * never checked before (just added to the watchlist, or the browser's
 * storage was cleared): nothing to report yet, there is no baseline.
 * `watchTitles` are the CURRENT watch items' own titles (`WatchItem.title`,
 * keyed by `.kind`), so a newly active situation is named the same way the
 * stock page itself names it.
 */
export function describeChanges(seen: StockFingerprint | null, current: StockFingerprint, watchTitles: Record<string, string>): string[] {
  if (seen === null) return [];
  const out: string[] = [];
  for (const kind of current.watch) {
    if (!seen.watch.includes(kind)) out.push(watchTitles[kind] ?? kind);
  }
  for (const [key, label] of DATED_CHANGE) {
    const cur = current[key] as string | null;
    const prev = seen[key] as string | null;
    if (cur !== null && cur !== prev) out.push(label);
  }
  return out;
}
