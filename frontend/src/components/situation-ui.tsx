import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

/**
 * Shared pieces of the situation boards: the two-column "X dari 100"
 * frequency (Situasi-Baru-*, Saham-PACK), and the stock list row
 * (Situasi-Baru-Daftar). Columns, never horizontal bars.
 */

const BLUE = "#3987e5";
const GREY = "#5F6C84";

export function PairBars({ a, b, unit = "dari 100", compact = false }: { a: { n: number; label: string }; b: { n: number; label: string }; unit?: string; compact?: boolean }) {
  const scale = compact ? 1.0 : 1.68;
  const w = compact ? 56 : 68;
  const bar = compact ? 34 : 46;
  const col = (n: number, label: string, color: string, first: boolean) => (
    <div key={label} className="flex flex-col items-center" style={{ width: w }}>
      <div className="flex flex-col items-center justify-end gap-1.5" style={{ height: 100 * scale + 34 }}>
        <span className="font-mono font-bold" style={{ fontSize: compact ? 15 : 16, color: first ? undefined : "#B4BFD1" }}>
          {n}
        </span>
        <div style={{ width: bar, height: Math.max(3, n * scale), background: color, borderRadius: "8px 8px 3px 3px" }} />
      </div>
      <div className="mt-2 text-center text-[11.5px] leading-tight text-muted-foreground" style={{ width: w + 4 }}>
        {label}
      </div>
    </div>
  );
  return (
    <div role="img" aria-label={`${a.n} ${a.label}, ${b.n} ${b.label}, ${unit}`}>
      <div className="flex items-end gap-2 border-b border-border" style={{ paddingBottom: 0 }}>
        {col(a.n, a.label, BLUE, true)}
        {col(b.n, b.label, GREY, false)}
      </div>
      <div className="mt-1.5 text-[11px] text-muted-foreground">{unit}</div>
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
  return <div className="flex gap-2.5 rounded-[14px] border border-dashed border-[var(--border-strong,rgba(255,255,255,0.14))] px-3.5 py-3 text-[12.5px] leading-normal text-muted-foreground">{children}</div>;
}
