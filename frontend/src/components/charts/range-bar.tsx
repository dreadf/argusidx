import { formatPrice } from "@/lib/format";

/**
 * Where today's price sits between the lowest and highest price of the
 * last year. The two ends are labelled with real prices so the bar never
 * needs explaining; the caller prints the signed distances beside it.
 */
export function RangeBar({ low, high, price }: { low: number; high: number; price: number }) {
  const span = high - low;
  const p = span > 0 ? Math.min(100, Math.max(0, ((price - low) / span) * 100)) : 0;
  return (
    <div>
      <div className="relative my-2 h-1.5 rounded-[3px] bg-[var(--viz-raised)]" role="img" aria-label={`Harga ${formatPrice(price)} di antara terendah ${formatPrice(low)} dan tertinggi ${formatPrice(high)} setahun terakhir`}>
        <div className="absolute top-[-3px] size-3 rounded-full bg-[var(--viz-accent)]" style={{ left: `${p}%`, transform: `translateX(-${p}%)` }} />
      </div>
      <div className="flex justify-between text-[11.5px] text-muted-foreground">
        <span>
          {formatPrice(low)} <span className="opacity-80">terendah</span>
        </span>
        <span>
          {formatPrice(high)} <span className="opacity-80">tertinggi</span>
        </span>
      </div>
    </div>
  );
}
