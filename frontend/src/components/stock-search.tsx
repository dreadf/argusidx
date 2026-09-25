"use client";

import { useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { SearchEntry } from "@/lib/stock-data";

/**
 * Site-wide stock search — the thing this app was missing entirely
 * before: 962 stock pages existed, but nothing let a user type a ticker
 * or company name and land on one (BACKLOG.md's "Product & features"
 * audit, 2026-09-19). Client-side filter over a small pre-fetched index
 * (~40KB, passed down from SiteHeader) — no live lookup call, matching
 * this product's "everything precomputed" architecture.
 *
 * Case-insensitive by design (a trader typing "bbca" must not fail where
 * "BBCA" would work — the same case-sensitivity mistake already fixed
 * once in lib/ask/stock-lookup.ts must not be reintroduced here).
 */
export function StockSearch({ index }: { index: SearchEntry[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length === 0) return [];
    return index
      .filter((entry) => entry.code.toLowerCase().includes(q) || entry.name.toLowerCase().includes(q))
      .slice(0, 8);
  }, [query, index]);

  function go(code: string) {
    setQuery("");
    setOpen(false);
    router.push(`/saham/${code}`);
  }

  return (
    <div className="relative">
      <input
        type="search"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActiveIndex(0);
        }}
        onKeyDown={(e) => {
          if (!open || results.length === 0) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActiveIndex((i) => Math.min(i + 1, results.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActiveIndex((i) => Math.max(i - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            go(results[activeIndex].code);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
        onFocus={() => query.length > 0 && setOpen(true)}
        onBlur={() => {
          // Let a click on a result register before the list unmounts.
          blurTimer.current = setTimeout(() => setOpen(false), 150);
        }}
        placeholder="Cari saham..."
        aria-label="Cari saham"
        aria-autocomplete="list"
        aria-expanded={open && results.length > 0}
        aria-controls="stock-search-list"
        role="combobox"
        className="w-full rounded-md border border-border bg-[var(--viz-surface)] px-3 py-2 text-sm text-[var(--viz-ink-primary)] outline-none focus:border-[var(--viz-diverging-pos)]"
      />
      {open && results.length > 0 && (
        <ul
          id="stock-search-list"
          role="listbox"
          className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-md border border-border bg-[var(--viz-surface)] shadow-lg"
        >
          {results.map((entry, i) => (
            <li key={entry.code} role="option" aria-selected={i === activeIndex}>
              <button
                type="button"
                onMouseDown={(e) => {
                  // Fire before the input's onBlur closes the list.
                  e.preventDefault();
                  if (blurTimer.current) clearTimeout(blurTimer.current);
                  go(entry.code);
                }}
                className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm ${
                  i === activeIndex ? "bg-[var(--viz-baseline)]" : ""
                }`}
              >
                <span className="shrink-0 font-medium text-[var(--viz-ink-primary)]">{entry.code}</span>
                <span className="truncate text-[var(--viz-ink-secondary)]">{entry.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
