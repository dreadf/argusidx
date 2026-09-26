import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight, Info } from "lucide-react";

/**
 * Shared pieces of the situation boards: the two-column "X dari 100"
 * frequency (Situasi-Baru-*, Saham-PACK), and the stock list row
 * (Situasi-Baru-Daftar). Columns, never horizontal bars.
 */

const BLUE = "#3987e5";
const GREY = "#5F6C84";

/**
 * Two columns out of 100. `unit` is the small caption under the chart used on
 * the stock page ("dari 100 saham"); the evidence cards leave it out because
 * their sentence already says "X dari 100".
 */
export function PairBars({ a, b, unit, compact = false }: { a: { n: number; label: string }; b: { n: number; label: string }; unit?: string; compact?: boolean }) {
  // Evidence cards (boards): the taller column is always 96px, the other in proportion, both from a zero baseline.
  const scale = compact ? 1.0 : 96 / Math.max(a.n, b.n, 1);
  const w = compact ? 56 : 68;
  const bar = compact ? 34 : 46;
  const col = (n: number, color: string, first: boolean) => (
    <div key={color} className="flex flex-col items-center justify-end gap-1.5" style={{ width: w, height: compact ? 100 * scale + 34 : 134 }}>
      <span className="font-mono font-bold" style={{ fontSize: compact ? 15 : 16, color: first ? undefined : "#B4BFD1" }}>
        {n}
      </span>
      <div style={{ width: bar, height: Math.max(3, n * scale), background: color, borderRadius: "8px 8px 3px 3px" }} />
    </div>
  );
  const caption = (label: string) => (
    <div key={label} className="text-center text-[11.5px] leading-[1.3] text-muted-foreground" style={{ width: w }}>
      {label}
    </div>
  );
  return (
    <div role="img" aria-label={`${a.n} ${a.label}, ${b.n} ${b.label}${unit ? `, ${unit}` : ""}`}>
      <div className="flex items-end gap-2 border-b border-[var(--border-strong,rgba(255,255,255,0.14))]">
        {col(a.n, BLUE, true)}
        {col(b.n, GREY, false)}
      </div>
      <div className="mt-2 flex gap-2">
        {caption(a.label)}
        {caption(b.label)}
      </div>
      {unit && <div className="mt-1.5 text-[11px] text-muted-foreground">{unit}</div>}
    </div>
  );
}

export function StockListRow({ code, name, value, sub }: { code: string; name: string; value: ReactNode; sub: string }) {
  return (
    <Link href={`/saham/${code}`} className="flex items-center gap-3 border-b border-border py-3">
      <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-accent font-mono text-xs font-bold text-accent-foreground">{code.slice(0, 2)}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-semibold leading-snug">{code}</span>
        <span className="block truncate text-xs text-muted-foreground">{name}</span>
      </span>
      <span className="text-right">
        <span className="block font-mono text-sm font-semibold">{value}</span>
        <span className="block text-xs text-muted-foreground">{sub}</span>
      </span>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
    </Link>
  );
}

/** Dashed "note" box used under a situation's numbers. */
export function Note({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-2.5 rounded-[14px] border border-dashed border-[var(--border-strong,rgba(255,255,255,0.14))] px-3.5 py-3 text-[12.5px] leading-normal text-muted-foreground">
      <Info className="mt-px size-4 shrink-0" strokeWidth={1.7} />
      <span>{children}</span>
    </div>
  );
}
