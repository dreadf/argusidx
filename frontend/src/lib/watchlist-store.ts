/**
 * Watchlist persistence (docs/PRODUCT.md §11): "save stocks locally on the
 * device, no account needed." Plain localStorage, no backend, no database:
 * consistent with §2's architecture (nothing runs live except the Ask
 * layer). Stores {symbol, company_name} pairs, not just symbols, so the
 * /watchlist page can render immediately from what's already saved without
 * a second data fetch: the trade-off is a saved name won't update if a
 * company is later renamed, an acceptable, disclosed limitation for a v1.
 *
 * Not a React hook itself (plain functions) so it can be called from event
 * handlers directly; see use-watchlist.ts for the reactive hook wrapper.
 */
const STORAGE_KEY = "argusidx:watchlist";
export const WATCHLIST_EVENT = "argusidx:watchlist-changed";

export interface WatchlistEntry {
  symbol: string;
  company_name: string;
}

function isWatchlistEntry(value: unknown): value is WatchlistEntry {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as WatchlistEntry).symbol === "string" &&
    typeof (value as WatchlistEntry).company_name === "string"
  );
}

function readRaw(): WatchlistEntry[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isWatchlistEntry);
  } catch {
    // Private browsing, blocked storage, or corrupted JSON - never crash the
    // page over a convenience feature; just behave as if nothing is saved.
    return [];
  }
}

function writeRaw(entries: WatchlistEntry[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    invalidateWatchlistSnapshot();
    window.dispatchEvent(new Event(WATCHLIST_EVENT));
  } catch {
    // Storage full or blocked - the toggle just won't persist this time.
  }
}

// `useSyncExternalStore` (use-watchlist.ts) requires getSnapshot to return
// the SAME reference until something actually changed, or React re-renders
// forever - readRaw() alone can't satisfy that, since JSON.parse produces a
// new array every call even when the content is identical. This caches the
// last computed array and only recomputes when explicitly invalidated (a
// local write, or another tab's `storage` event via the hook's subscribe).
let cachedSnapshot: WatchlistEntry[] | null = null;

export function invalidateWatchlistSnapshot(): void {
  cachedSnapshot = null;
}

export function getWatchlistSnapshot(): WatchlistEntry[] {
  if (cachedSnapshot === null) {
    cachedSnapshot = readRaw();
  }
  return cachedSnapshot;
}

export function isWatched(symbol: string): boolean {
  return readRaw().some((e) => e.symbol === symbol);
}

export function addToWatchlist(entry: WatchlistEntry): void {
  const current = readRaw();
  if (current.some((e) => e.symbol === entry.symbol)) return;
  writeRaw([...current, entry]);
}

export function removeFromWatchlist(symbol: string): void {
  writeRaw(readRaw().filter((e) => e.symbol !== symbol));
}

/** Returns the new watched state (true = now saved, false = now removed). */
export function toggleWatchlist(entry: WatchlistEntry): boolean {
  if (isWatched(entry.symbol)) {
    removeFromWatchlist(entry.symbol);
    return false;
  }
  addToWatchlist(entry);
  return true;
}
