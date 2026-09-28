import { isFingerprint, type StockFingerprint } from "@/lib/watchlist-changes";

/**
 * Per-symbol "last seen" fingerprint for the watchlist's "ada yang berubah"
 * (watchlist-changes.ts), plain localStorage like watchlist-store.ts. Not
 * reactive (no useSyncExternalStore wrapper): it's read once per check and
 * written once per response, never rendered directly.
 */
const STORAGE_KEY = "argusidx:watchlist-seen";

export function getSeenMap(): Record<string, StockFingerprint> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return {};
    return Object.fromEntries(Object.entries(parsed as Record<string, unknown>).filter(([, v]) => isFingerprint(v))) as Record<string, StockFingerprint>;
  } catch {
    return {};
  }
}

/** Records the fingerprint the browser has now shown the user for `symbol`. */
export function recordSeen(symbol: string, fingerprint: StockFingerprint): void {
  try {
    const next = { ...getSeenMap(), [symbol]: fingerprint };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Storage full or blocked: the change just won't be remembered as seen.
  }
}

/** Drops entries for symbols no longer on the watchlist, so removed stocks don't linger forever. */
export function pruneSeen(keepSymbols: string[]): void {
  try {
    const keep = new Set(keepSymbols);
    const seen = getSeenMap();
    const next = Object.fromEntries(Object.entries(seen).filter(([symbol]) => keep.has(symbol)));
    if (Object.keys(next).length !== Object.keys(seen).length) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Not essential: skip pruning this time.
  }
}
