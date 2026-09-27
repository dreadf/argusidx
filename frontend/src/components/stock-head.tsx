import type { ReactNode } from "react";
import { RangeBar } from "@/components/charts/range-bar";
import { Neg } from "@/components/kit";
import { WatchlistButton } from "@/components/watchlist-button";
import { formatDateId, formatPrice, idNum, pctFrom, signedPct } from "@/lib/format";
import { getQuoteIndex, type StockPageData } from "@/lib/stock-data";
import { pricePosition } from "@/lib/stock-summary";

const FLOAT_WORD: Record<string, string> = { low: "tipis", mid: "di tengah", high: "lebar" };

/** Rank by "furthest below the 52-week high" among all stocks (1 = furthest), and the universe size. */
export async function getFarRank(price: number | null, high: number | null): Promise<{ rank: number | null; universe: number }> {
  const quotes = await getQuoteIndex();
  const below = (q: { price: number | null; high: number | null }) => (q.price !== null && q.high ? (q.high - q.price) / q.high : null);
  const own = below({ price, high });
  if (own === null) return { rank: null, universe: quotes.length };
  return {
    rank: 1 + quotes.filter((q) => {
      const b = below(q);
      return b !== null && b > own;
    }).length,
    universe: quotes.length,
  };
}

/**
 * Top of every stock page: code, price, 52-week range, the three ranks.
 * Boards: Saham-Alasan-Mobile / Saham-PACK-Mobile / Saham-ASII-Mobile.
 * `below` is what sits under the ranks (the reason link on the main page).
 */
export function StockHead({ code, data, asOf, rank, universe, below }: { code: string; data: StockPageData; asOf: string; rank: number | null; universe: number; below?: ReactNode }) {
  const { snapshot, h1_finding } = data;
  const price = snapshot.last_close_price;
  const low = snapshot["52_w_low_price"];
  const high = snapshot["52_w_high_price"];
  const hasRange = price !== null && low !== null && high !== null && high > low;
  const distHigh = price !== null && high ? pctFrom(price, high) : null;
  const pos = pricePosition(snapshot.position_in_52w_range);
  const ffTercile = h1_finding?.free_float_tercile;
  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[13px] font-bold text-accent-foreground md:size-[52px]">{code.slice(0, 2)}</span>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold leading-tight tracking-[-0.02em] md:text-[32px]">{code}</h1>
            <p className="truncate text-xs text-muted-foreground md:text-[13px]">{snapshot.company_name}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span className="hidden whitespace-nowrap rounded-md border border-border px-[9px] py-[3px] text-[11.5px] text-muted-foreground md:inline">Data {formatDateId(asOf)}</span>
          <WatchlistButton symbol={code} companyName={snapshot.company_name} />
        </div>
      </div>

      {price !== null && (
        <div className="mt-5">
          <div className="font-mono text-[28px] font-bold tabular-nums">{formatPrice(price)}</div>
          <div className="mt-1 flex flex-wrap items-baseline gap-2 text-[13px]">
            {distHigh !== null && <Neg>{signedPct(distHigh)}</Neg>}
            {distHigh !== null && <span className="text-xs text-muted-foreground">dari tertinggi setahun</span>}
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">Harga per {formatDateId(asOf)}</div>
        </div>
      )}

      {hasRange && (
        <div className="mt-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Rentang setahun</span>
            {pos && <span className="inline-flex h-6 items-center rounded-md border border-border px-2.5 text-[11px] text-muted-foreground">{pos}</span>}
          </div>
          <RangeBar low={low} high={high} price={price} />
        </div>
      )}

      <div className="mt-5 grid grid-cols-3 overflow-hidden rounded-2xl border border-border bg-card">
        <div className="p-3.5">
          <div className="font-mono text-lg font-bold">{rank === null ? "-" : `#${rank}`}</div>
          <div className="mt-0.5 text-xs font-semibold leading-snug">Jauh dari puncak</div>
          <div className="text-[11px] text-muted-foreground">dari {universe} saham</div>
        </div>
        <div className="border-l border-border p-3.5">
          <div className="font-mono text-lg font-bold">{snapshot.market_cap_rank === null ? "-" : `#${snapshot.market_cap_rank}`}</div>
          <div className="mt-0.5 text-xs font-semibold leading-snug">Nilai pasar</div>
          <div className="text-[11px] text-muted-foreground">dari {universe} saham</div>
        </div>
        <div className="border-l border-border p-3.5">
          <div className="font-mono text-lg font-bold">{snapshot.free_float === null ? "-" : `${idNum(snapshot.free_float * 100)}%`}</div>
          <div className="mt-0.5 text-xs font-semibold leading-snug">Free float</div>
          <div className="text-[11px] text-muted-foreground">{ffTercile ? FLOAT_WORD[ffTercile] : "belum dikelompokkan"}</div>
        </div>
      </div>
      <p className="mt-2 text-[11.5px] text-muted-foreground">Nilai pasar dan free float adalah angka sesaat per {formatDateId(asOf)}, bisa berubah tiap hari.</p>
      {below}
    </>
  );
}
