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
 * The watchlist toggle of the stock page: an icon-only star at the top right
 * of the header on phones, the full-width labelled button in the Pantau card
 * on wider screens (one or the other, never both). Same store as
 * WatchlistButton.
 */
export function PantauButton({ symbol, companyName, wide = false }: { symbol: string; companyName: string; wide?: boolean }) {
  const watched = useSyncExternalStore(subscribe, () => isWatched(symbol), () => false);
  const label = wide ? (watched ? "Tersimpan di Watchlist" : "Tambah ke Watchlist") : watched ? `Hapus ${symbol} dari pantauan` : `Pantau ${symbol}`;
  return (
    <button
      type="button"
      onClick={() => toggleWatchlist({ symbol, company_name: companyName })}
      aria-pressed={watched}
      aria-label={wide ? undefined : label}
      title={wide ? undefined : label}
      className={
        wide
          ? "mt-3.5 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-primary bg-primary px-3.5 text-[13.5px] font-semibold text-primary-foreground transition-colors hover:bg-primary/85"
          : `inline-flex size-10 shrink-0 items-center justify-center rounded-[10px] border transition-colors ${
              watched ? "border-[var(--viz-accent)] bg-accent text-[var(--viz-accent)]" : "border-border bg-[var(--viz-raised)] text-foreground hover:border-[var(--viz-accent)] hover:text-[var(--viz-accent)]"
            }`
      }
    >
      <Star className={wide ? "size-4" : "size-[18px]"} strokeWidth={1.8} fill={watched ? "currentColor" : "none"} />
      {wide ? label : null}
    </button>
  );
}
