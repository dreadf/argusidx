"use client";

import Link from "next/link";
import { Star, Trash2 } from "lucide-react";
import { RangeBar } from "@/components/charts/range-bar";
import { formatPrice, pctFrom, shortName, signedPct } from "@/lib/format";
import { useWatchlist } from "@/lib/use-watchlist";
import { removeFromWatchlist } from "@/lib/watchlist-store";

export interface QuoteMap {
  [code: string]: { price: number | null; low: number | null; high: number | null };
}

/** Saved stocks, each with today's price, its signed distance from the year's high, and the year's range (both ends labelled). */
export function WatchlistView({ quotes }: { quotes: QuoteMap }) {
  const { entries } = useWatchlist();

  if (entries.length === 0) {
    return (
      <div className="mt-14 flex flex-col items-center gap-3.5 text-center">
        <div className="flex size-16 items-center justify-center rounded-[20px] bg-accent text-accent-foreground">
          <Star className="size-7" strokeWidth={1.7} />
        </div>
        <div className="text-xl font-bold">Belum ada saham</div>
        <p className="max-w-[260px] text-[13px] leading-normal text-muted-foreground">Ketuk bintang di halaman saham untuk menyimpannya.</p>
        <Link href="/cari" className="mt-2 inline-flex h-10 items-center rounded-md bg-primary px-7 text-sm font-semibold text-primary-foreground">
          Cari saham
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h2 className="mt-6 text-xl font-bold md:mt-8 md:text-[22px]">{entries.length} saham</h2>
      <div className="mt-3 hidden items-center gap-3.5 rounded-[10px] bg-[var(--viz-raised)] px-3 py-2.5 text-xs font-semibold tracking-[0.04em] text-[#B9C4D8] md:flex">
        <span className="w-[220px] shrink-0">Saham</span>
        <span className="w-[150px] shrink-0">Harga</span>
        <span className="flex-1">Rentang harga setahun terakhir</span>
        <span className="w-11" />
      </div>
      <ul>
        {entries.map((entry) => {
          const q = quotes[entry.symbol];
          const dist = q && q.price != null && q.high ? pctFrom(q.price, q.high) : null;
          const range = q && q.price != null && q.low != null && q.high != null ? <RangeBar low={q.low} high={q.high} price={q.price} /> : null;
          const remove = (
            <button
              type="button"
              onClick={() => removeFromWatchlist(entry.symbol)}
              aria-label={`Hapus ${entry.symbol} dari watchlist`}
              className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-[rgba(230,103,103,0.12)]"
            >
              <Trash2 className="size-5 text-[#e66767]" strokeWidth={1.8} />
            </button>
          );
          const priceBlock = (
            <>
              <div className="font-mono text-base font-bold tabular-nums">{q?.price != null ? formatPrice(q.price) : "-"}</div>
              {dist != null && <div className="font-mono text-[12.5px] tabular-nums text-[var(--viz-diverging-neg)]">{signedPct(dist)} dari tertinggi</div>}
            </>
          );
          return (
            <li key={entry.symbol} className="border-b border-border py-4 md:px-3">
              <div className="flex items-center gap-3 md:hidden">
                <Link href={`/saham/${entry.symbol}`} className="min-w-0 flex-1">
                  <div className="text-[15px] font-bold">{entry.symbol}</div>
                  <div className="truncate text-xs text-muted-foreground">{shortName(entry.company_name)}</div>
                </Link>
                <div className="text-right">{priceBlock}</div>
                {remove}
              </div>
              {range && (
                <div className="mr-14 mt-2 md:hidden">
                  <div className="text-[11.5px] text-muted-foreground">Rentang harga setahun terakhir</div>
                  {range}
                </div>
              )}
              <div className="hidden items-center gap-3.5 md:flex">
                <Link href={`/saham/${entry.symbol}`} className="w-[220px] shrink-0">
                  <div className="text-[15px] font-bold">{entry.symbol}</div>
                  <div className="truncate text-xs text-muted-foreground">{shortName(entry.company_name)}</div>
                </Link>
                <div className="w-[150px] shrink-0">{priceBlock}</div>
                <div className="flex-1">{range}</div>
                <span className="ml-auto">{remove}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
