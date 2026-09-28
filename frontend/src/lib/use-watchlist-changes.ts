"use client";

import { useEffect, useRef, useState } from "react";
import { useWatchlist } from "@/lib/use-watchlist";
import { getSeenMap, pruneSeen, recordSeen } from "@/lib/watchlist-changes-store";
import type { StockFingerprint } from "@/lib/watchlist-changes";

export interface ChangeResult {
  current: StockFingerprint;
  changes: string[];
}

type ChangesResponse = { results: Record<string, ChangeResult> } | null;

// Shared across every mounted instance of the hook (the sidebar nav, the
// bottom nav, and the watchlist page itself all mount at once): one
// in-flight POST per distinct symbol set, not one per instance.
let inFlight: { key: string; promise: Promise<ChangesResponse> } | null = null;

function fetchChanges(symbols: string[]): Promise<ChangesResponse> {
  const key = symbols.join(",");
  if (inFlight && inFlight.key === key) return inFlight.promise;
  const seen = getSeenMap();
  const promise = fetch("/api/watchlist-changes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols, seen: Object.fromEntries(symbols.map((s) => [s, seen[s] ?? null])) }),
  })
    .then((r) => (r.ok ? (r.json() as Promise<{ results: Record<string, ChangeResult> }>) : null))
    .catch(() => null)
    .finally(() => {
      if (inFlight?.key === key) inFlight = null;
    });
  inFlight = { key, promise };
  return promise;
}

/**
 * Checks /api/watchlist-changes once per distinct set of watched stocks.
 * `markSeen`: the watchlist page passes true (viewing the page IS reading
 * the change, so the fingerprint just fetched becomes the new baseline);
 * the nav badge passes false (peeking must not clear it before the page
 * that actually shows it is opened).
 *
 * Fetched results are filtered to the CURRENT watchlist on every render
 * rather than cleared imperatively when it empties: an effect must not call
 * setState synchronously just to reset state a derived filter already
 * hides (react-hooks/set-state-in-effect).
 */
export function useWatchlistChanges(markSeen: boolean): { results: Record<string, ChangeResult>; hasChanges: boolean } {
  const { entries } = useWatchlist();
  const [results, setResults] = useState<Record<string, ChangeResult>>({});
  const fetchedFor = useRef("");

  const symbols = [...new Set(entries.map((e) => e.symbol))].sort();
  const key = `${markSeen}:${symbols.join(",")}`;

  useEffect(() => {
    if (symbols.length === 0) {
      // Nothing to check right now, but don't leave a stale key behind: if
      // this exact symbol set comes back later (removed, then re-added),
      // it must be re-checked, not skipped as "already fetched".
      fetchedFor.current = "";
      return;
    }
    if (fetchedFor.current === key) return;
    fetchedFor.current = key;
    pruneSeen(symbols);
    fetchChanges(symbols).then((json) => {
      if (!json) return;
      setResults(json.results);
      if (markSeen) for (const [symbol, r] of Object.entries(json.results)) recordSeen(symbol, r.current);
    });
    // symbols/key are recomputed fresh each render from entries; re-running the effect on `key` alone is correct here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const symbolSet = new Set(symbols);
  const filtered = Object.fromEntries(Object.entries(results).filter(([s]) => symbolSet.has(s)));
  return { results: filtered, hasChanges: Object.values(filtered).some((r) => r.changes.length > 0) };
}
