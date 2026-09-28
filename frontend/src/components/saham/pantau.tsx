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
 * The labelled watchlist toggle of the stock page: a small "Pantau" button in
 * the header on phones, the full-width button in the Pantau card on wider
 * screens (one or the other, never both). Same store as WatchlistButton.
 */
export function PantauButton({ symbol, companyName, wide = false }: { symbol: string; companyName: string; wide?: boolean }) {
  const watched = useSyncExternalStore(subscribe, () => isWatched(symbol), () => false);
  const label = wide ? (watched ? "Tersimpan di Watchlist" : "Tambah ke Watchlist") : watched ? "Dipantau" : "Pantau";
  return (
    <button
      type="button"
      onClick={() => toggleWatchlist({ symbol, company_name: companyName })}
      aria-pressed={watched}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-lg border px-3.5 text-[13.5px] font-semibold ${
        wide ? "mt-3.5 w-full border-primary bg-primary text-primary-foreground" : "border-border bg-[var(--viz-raised)] text-foreground"
      }`}
    >
      <Star className="size-4" strokeWidth={1.8} fill={watched ? "currentColor" : "none"} />
      {label}
    </button>
  );
}
