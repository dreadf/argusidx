"use client";

import { useSyncExternalStore } from "react";
import { getWatchlistSnapshot, invalidateWatchlistSnapshot, WATCHLIST_EVENT, type WatchlistEntry } from "./watchlist-store";

function subscribe(onChange: () => void): () => void {
  const handler = () => {
    invalidateWatchlistSnapshot();
    onChange();
  };
  window.addEventListener(WATCHLIST_EVENT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(WATCHLIST_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}

function getServerSnapshot(): WatchlistEntry[] {
  // The server has no concept of localStorage; an empty list is also
  // exactly what a first client render should show before hydration
  // catches up, so there's no mismatch to guard against separately.
  return [];
}

/**
 * Reactive read of the watchlist via React's own external-store primitive
 * (the textbook fit for "state that lives outside React and can change
 * from other places": localStorage, a custom event, and another tab's
 * `storage` event all qualify). Replaces an earlier manual
 * useState+useEffect version that triggered React's
 * `react-hooks/set-state-in-effect` lint rule; this has no effect body at
 * all; and it avoids the `hydrated` flag entirely.
 */
export function useWatchlist() {
  const entries = useSyncExternalStore(subscribe, getWatchlistSnapshot, getServerSnapshot);
  return { entries };
}
