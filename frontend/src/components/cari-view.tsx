"use client";

import Link from "next/link";
import { useMemo, useState, useSyncExternalStore } from "react";
import { Search } from "lucide-react";
import { formatPrice, pctFrom, shortName, signedPct } from "@/lib/format";
import { getRecentServerSnapshot, getRecentSnapshot, subscribeRecent } from "@/lib/recent-store";
import { SECTOR_META } from "@/lib/sectors-id";
import type { QuoteEntry } from "@/lib/stock-data";

const sectorLabel = (key: string | null) => SECTOR_META.find((s) => s.key === key)?.label ?? "";

function Row({ q }: { q: QuoteEntry }) {
  const dist = q.price != null && q.high ? pctFrom(q.price, q.high) : null;
  return (
    <Link href={`/saham/${q.code}`} className="flex items-center gap-3 border-b border-border py-3 md:px-3">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent font-mono text-xs font-bold text-accent-foreground">{q.code.slice(0, 2)}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-bold">{q.code}</span>
        <span className="block truncate text-xs text-muted-foreground">{shortName(q.name)}</span>
      </span>
      <span className="hidden w-40 shrink-0 text-xs text-muted-foreground md:block">{sectorLabel(q.sector)}</span>
      <span className="text-right">
        <span className="block font-mono text-sm tabular-nums">{q.price != null ? formatPrice(q.price) : "-"}</span>
        {dist != null && <span className="block font-mono text-xs tabular-nums text-[var(--viz-diverging-neg)]">{signedPct(dist)}</span>}
      </span>
    </Link>
  );
}

/** Find a stock by code or name. Not Tanya: this only opens stock pages. */
export function CariView({ quotes, asOf }: { quotes: QuoteEntry[]; asOf: string }) {
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState(8);
  const recent = useSyncExternalStore(subscribeRecent, getRecentSnapshot, getRecentServerSnapshot);
  const byCode = useMemo(() => new Map(quotes.map((q) => [q.code, q])), [quotes]);

  const q = query.trim().toLowerCase();
  const matches = useMemo(() => {
    if (!q) return [];
    const starts = quotes.filter((e) => e.code.toLowerCase().startsWith(q));
    const rest = quotes.filter((e) => !e.code.toLowerCase().startsWith(q) && (e.code.toLowerCase().includes(q) || e.name.toLowerCase().includes(q)));
    return [...starts, ...rest];
  }, [q, quotes]);

  return (
    <div>
      <label className="flex min-h-[46px] items-center gap-2.5 rounded-full border border-[var(--viz-accent)] bg-card px-4 md:max-w-[560px]">
        <Search className="size-[18px] shrink-0 text-muted-foreground" />
        <input
          autoFocus
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShown(8);
          }}
          placeholder="Kode atau nama saham"
          aria-label="Cari saham"
          className="min-w-0 flex-1 bg-transparent text-[15px] text-foreground outline-none placeholder:text-muted-foreground"
        />
      </label>

      {q === "" ? (
        <section className="mt-7">
          <h2 className="text-xl font-bold md:text-[22px]">Terakhir dilihat</h2>
          {recent.length === 0 ? (
            <p className="mt-2 text-[13px] text-muted-foreground">Belum ada. Halaman saham yang Anda buka muncul di sini.</p>
          ) : (
            <div className="mt-1 md:max-w-3xl">
              {recent.map((code) => byCode.get(code)).filter((e): e is QuoteEntry => e !== undefined).map((e) => <Row key={e.code} q={e} />)}
            </div>
          )}
          <p className="mt-2 text-xs text-muted-foreground">Harga {asOf}, jarak dari tertinggi setahun.</p>
        </section>
      ) : (
        <section className="mt-7">
          <h2 className="text-xl font-bold md:text-[22px]">
            {matches.length} hasil untuk &ldquo;{query.trim()}&rdquo;
          </h2>
          <div className="mt-3 hidden items-center gap-3 rounded-[10px] bg-[var(--viz-raised)] px-3 py-2.5 text-xs font-semibold tracking-[0.04em] text-[#B9C4D8] md:flex">
            <span className="w-10" />
            <span className="flex-1">Saham</span>
            <span className="w-40">Sektor</span>
            <span className="w-[120px] text-right">Harga, dari tertinggi setahun</span>
          </div>
          <div className="mt-1 md:max-w-4xl md:[&_a]:gap-3">
            {matches.slice(0, shown).map((e) => (
              <Row key={e.code} q={e} />
            ))}
          </div>
          {matches.length === 0 && <p className="mt-3 text-sm text-muted-foreground">Tidak ada saham dengan kode atau nama itu.</p>}
          {shown < matches.length && (
            <button type="button" onClick={() => setShown(shown + 20)} className="mt-3 inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
              Lihat lebih banyak dari {matches.length} hasil &rarr;
            </button>
          )}
          <p className="mt-3 text-xs text-muted-foreground">Harga {asOf}, jarak dari tertinggi setahun.</p>
        </section>
      )}
    </div>
  );
}
