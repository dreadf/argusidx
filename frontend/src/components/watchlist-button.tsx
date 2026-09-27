"use client";

import { useSyncExternalStore } from "react";
import { Star } from "lucide-react";
import { isWatched, toggleWatchlist, WATCHLIST_EVENT } from "@/lib/watchlist-store";

function subscribe(onChange: () => void): () => void {
  window.addEventListener(WATCHLIST_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(WATCHLIST_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/**
 * Star toggle for saving a stock to the on-device watchlist (docs/PRODUCT.md
 * §11). Uses `useSyncExternalStore` (matching `use-watchlist.ts`'s hook)
 * rather than a manual `useState`+`useEffect` pair: the server always
 * reports "not watched" (it has no concept of localStorage), and React's
 * own hydration handling for this primitive means the star can simply
 * flip to ★ right after mount for an already-saved stock, with no
 * hydration-mismatch warning and no placeholder element needed meanwhile.
 */
export function WatchlistButton({ symbol, companyName }: { symbol: string; companyName: string }) {
  const watched = useSyncExternalStore(
    subscribe,
    () => isWatched(symbol),
    () => false
  );

  return (
    <button
      type="button"
      onClick={() => toggleWatchlist({ symbol, company_name: companyName })}
      aria-pressed={watched}
      aria-label={watched ? `Hapus ${symbol} dari watchlist` : `Tambah ${symbol} ke watchlist`}
      className="inline-flex size-10 items-center justify-center rounded-lg border border-border bg-[var(--viz-raised)] text-muted-foreground hover:text-foreground"
    >
      <Star className="size-5" strokeWidth={1.7} fill={watched ? "var(--viz-accent)" : "none"} stroke={watched ? "var(--viz-accent)" : "currentColor"} />
    </button>
  );
}
