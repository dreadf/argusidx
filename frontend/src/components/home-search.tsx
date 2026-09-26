"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import type { SearchEntry } from "@/lib/stock-data";

/**
 * Beranda's one big question box (board: Beranda-Baru-Mobile / -Web). Same
 * case-insensitive client-side filter as the sidebar search; submitting
 * opens the exact code if typed, otherwise the first match.
 */
export function HomeSearch({ index, examples }: { index: SearchEntry[]; examples: string[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length === 0) return [];
    const exact = index.filter((e) => e.code.toLowerCase() === q);
    const rest = index.filter((e) => e.code.toLowerCase() !== q && (e.code.toLowerCase().includes(q) || e.name.toLowerCase().includes(q)));
    return [...exact, ...rest].slice(0, 6);
  }, [query, index]);

  function go(code: string) {
    setOpen(false);
    router.push(`/saham/${code}`);
  }

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (results.length > 0) go(results[0].code);
        }}
        className="relative"
      >
        <div className="flex h-16 items-center gap-3 rounded-[18px] border-[1.5px] border-[var(--viz-accent)] bg-card pl-[18px] pr-2 shadow-[0_0_0_4px_rgba(143,180,238,0.10)] md:h-[72px] md:rounded-[20px] md:pl-6 md:pr-2.5">
          <Search className="size-[22px] shrink-0 text-[var(--viz-accent)] md:size-6" strokeWidth={1.7} aria-hidden />
          <input
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
            }}
            onFocus={() => query.length > 0 && setOpen(true)}
            onBlur={() => {
              blurTimer.current = setTimeout(() => setOpen(false), 150);
            }}
            placeholder="Kode atau nama saham"
            aria-label="Kode atau nama saham"
            autoComplete="off"
            className="h-12 min-w-0 flex-1 bg-transparent text-[17px] text-foreground outline-none placeholder:text-muted-foreground md:h-[52px] md:text-lg"
          />
          <button type="submit" aria-label="Periksa saham" className="flex h-12 w-12 shrink-0 items-center justify-center gap-2 rounded-[14px] bg-primary text-[15px] font-bold text-primary-foreground md:h-[52px] md:w-auto md:px-[26px]">
            <span className="hidden md:inline">Periksa saham</span>
            <ArrowRight className="size-[22px] md:size-[18px]" strokeWidth={1.7} aria-hidden />
          </button>
        </div>
        {open && results.length > 0 && (
          <ul role="listbox" className="absolute z-20 mt-1.5 w-full overflow-hidden rounded-2xl border border-border bg-card shadow-lg">
            {results.map((entry) => (
              <li key={entry.code} role="option" aria-selected={false}>
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    if (blurTimer.current) clearTimeout(blurTimer.current);
                    go(entry.code);
                  }}
                  className="flex min-h-11 w-full items-center gap-3 px-4 py-2 text-left text-sm"
                >
                  <span className="shrink-0 font-bold">{entry.code}</span>
                  <span className="truncate text-muted-foreground">{entry.name}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </form>
      <div className="mt-4 flex flex-wrap items-center gap-2.5">
        <span className="text-xs text-muted-foreground">Coba</span>
        {examples.map((code) => (
          <Link key={code} href={`/saham/${code}`} className="inline-flex min-h-8 items-center rounded-md border border-border bg-[var(--viz-raised)] px-3.5 text-[13.5px] font-bold text-foreground">
            {code}
          </Link>
        ))}
      </div>
    </div>
  );
}
