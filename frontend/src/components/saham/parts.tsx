import Link from "next/link";
import type { ReactNode } from "react";
import {
  BarChart3,
  ChartColumnIncreasing,
  ChartLine,
  ChevronRight,
  CircleCheck,
  Coins,
  Flag,
  FlaskConical,
  Info,
  Landmark,
  List,
  Mountain,
  Pause,
  Percent,
  Rocket,
  TrendingDown,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { VerdictChip } from "@/components/saham/evidence";
import { formatPrice, idNum } from "@/lib/format";
import type { RingkasanRow, Signal, WatchItem, WatchKind } from "@/lib/stock-read";
import { dateLong } from "@/lib/dates";

/**
 * Building blocks of the stock page (boards Baru4-Saham-*). Every card has
 * the same frame: an icon, a title that names the stock, one supporting
 * line, then its body, so sections are clearly separated.
 */

export function SectionCard({ icon: Icon, title, sub, right, children, className = "", id }: { icon: LucideIcon; title: string; sub?: string; right?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={`rounded-[20px] border border-border bg-card p-4 md:p-5 ${className}`}>
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
          <Icon className="size-[18px]" strokeWidth={1.7} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2.5">
            <h2 className="text-[19px] font-bold leading-tight tracking-[-0.01em]">{title}</h2>
            {right && <div className="shrink-0 whitespace-nowrap">{right}</div>}
          </div>
          {sub && <p className="mt-1 text-[13px] leading-normal text-muted-foreground">{sub}</p>}
        </div>
      </div>
      <div className="mt-2">{children}</div>
    </section>
  );
}

/** The "Artinya untuk ASII:" box under a signal or situation. */
export function Meaning({ code, children }: { code: string; children: string }) {
  return (
    <div className="mt-2.5 rounded-[10px] bg-[var(--viz-raised)] px-3 py-2.5 text-[13px] leading-normal">
      <span className="font-bold text-[var(--viz-accent)]">Artinya untuk {code}:</span> {children.charAt(0).toUpperCase() + children.slice(1)}
    </div>
  );
}

function Muted({ children }: { children: ReactNode }) {
  return <span className="text-muted-foreground">{children}</span>;
}

export function NoteBox({ children, icon: Icon = Info, tone = "muted" }: { children: ReactNode; icon?: LucideIcon; tone?: "muted" | "good" }) {
  return (
    <div className="flex gap-2.5 rounded-xl border border-dashed border-border px-3.5 py-3 text-[13px] leading-normal text-muted-foreground">
      <Icon className="mt-px size-4 shrink-0" strokeWidth={1.8} style={tone === "good" ? { color: "var(--viz-diverging-pos)" } : undefined} />
      <span>{children}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ Ringkasan */

export function RingkasanCard({ code, lead, rows }: { code: string; lead: string; rows: RingkasanRow[] }) {
  return (
    <section className="rounded-[20px] border border-border bg-card p-4 md:p-5">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--viz-accent)]">Ringkasan {code}</div>
      <p className="mt-2 text-[17px] font-semibold leading-[1.45]">{lead}</p>
      <div className="mt-3 border-t border-border">
        {rows.map((r) => (
          <div key={r.label} className="grid gap-1 border-b border-border py-3 md:grid-cols-[110px_minmax(0,1fr)] md:gap-3">
            <div className="pt-0.5 text-xs font-semibold uppercase tracking-[0.04em] text-muted-foreground">{r.label}</div>
            <div>
              <div className="text-[15px] font-bold leading-snug">{r.state}</div>
              <div className="mt-0.5 text-[13px] leading-normal text-muted-foreground">{r.explain}</div>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs leading-normal text-muted-foreground">
        Tiap baris dihitung dengan aturan tetap dan berdiri sendiri, bukan nilai gabungan.{" "}
        <Link href="/temuan/cara-kami-menguji" className="underline">
          Cara kami menguji
        </Link>
      </p>
    </section>
  );
}

/* ------------------------------------------------------------------ Sinyal populer */

export function SignalsSection({ code, signals, findingsCount }: { code: string; signals: Signal[]; findingsCount: number }) {
  return (
    <SectionCard icon={FlaskConical} title={`Sinyal populer yang ada di ${code}`} sub={`Sinyal yang sering dipakai orang untuk memilih saham dan sedang terlihat di ${code}, dengan hasil uji kami.`}>
      {signals.length === 0 ? (
        <div className="mt-2">
          <NoteBox>
            Tidak ada sinyal populer yang sedang terlihat di {code}.{" "}
            <Link href="/temuan" className="underline">
              Lihat {findingsCount} keyakinan yang kami uji
            </Link>
          </NoteBox>
        </div>
      ) : (
        signals.map((s, i) => (
          <div key={s.key} className={`py-4 ${i > 0 ? "border-t border-border" : ""}`}>
            <div className="flex items-start gap-2.5">
              <Link href={s.href} className="min-w-0 flex-1 text-[15px] font-semibold leading-snug hover:underline">
                {s.title}
              </Link>
              <VerdictChip kind={s.verdict} />
            </div>
            <p className="mt-1.5 text-[13px] leading-normal">
              <Muted>Di {code}:</Muted> {s.here}
            </p>
            <p className="mt-1 text-[13px] leading-normal">
              <Muted>Hasil uji:</Muted> {s.result.charAt(0).toUpperCase() + s.result.slice(1)}
            </p>
            <Meaning code={code}>{s.meaning}</Meaning>
          </div>
        ))
      )}
      <p className="mt-1 text-xs leading-normal text-muted-foreground">Terbukti berarti berlaku rata-rata pada ratusan saham di data uji, bukan jaminan untuk satu saham.</p>
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ Yang perlu diperhatikan */

const WATCH_ICON: Record<WatchKind, LucideIcon> = {
  fall: TrendingDown,
  long_below_peak: TrendingDown,
  recent_price_suspension: Pause,
  repeat_suspension: Pause,
  recent_spike: TrendingUp,
  loss_year: Wallet,
  earnings_two_year_decline: BarChart3,
  recent_ipo: Rocket,
  earnings_more_than_doubled: ChartColumnIncreasing,
  payout_above_earnings: Coins,
  yield_far_above_average: Percent,
  near_ath_earnings_decline: Mountain,
};

export function WatchSection({ code, items, checked, className = "", narrow = false }: { code: string; items: WatchItem[]; checked: number; className?: string; narrow?: boolean }) {
  const title = `Yang perlu diperhatikan di ${code}`;
  if (items.length === 0) {
    return (
      <SectionCard icon={Flag} title={title} className={className}>
        <div className="mt-2">
          <NoteBox icon={CircleCheck} tone="good">
            <b className="text-foreground">Tidak ada.</b> Kami memeriksa {checked} keadaan di {code}, seperti rugi, suspensi, lonjakan harga dan laba turun; tidak satu pun sedang terjadi.{" "}
            <Link href="/situasi" className="underline">
              Lihat semua keadaan
            </Link>
          </NoteBox>
        </div>
      </SectionCard>
    );
  }
  return (
    <SectionCard icon={Flag} title={title} sub={`Keadaan yang sedang terjadi di ${code}, dan apa yang biasanya terjadi sesudahnya.`} className={className}>
      <div className={narrow ? "" : "md:grid md:grid-cols-2 md:gap-x-8"}>
        {items.map((w, i) => {
          const Icon = WATCH_ICON[w.kind];
          return (
            <Link key={w.kind} href={w.href} className={`block py-4 ${i > 0 ? "border-t border-border" : ""} ${!narrow && i === 1 ? "md:border-t-0" : ""} ${!narrow && i > 1 ? "md:border-t" : ""}`}>
              <div className="flex items-center gap-2.5">
                <span className="flex size-[30px] shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <Icon className="size-4" strokeWidth={1.8} />
                </span>
                <span className="min-w-0 flex-1 text-[15px] font-semibold leading-snug">{w.title}</span>
                <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
              </div>
              <p className="mt-2 text-[13px] leading-normal">
                <Muted>Di {code}:</Muted> {w.here}
              </p>
              {w.others && (
                <p className="mt-1 text-[13px] leading-normal">
                  <Muted>Pada saham lain:</Muted> <b className="font-mono tabular-nums">{w.others.figure}</b> {w.others.rest}
                </p>
              )}
              <Meaning code={code}>{w.meaning}</Meaning>
            </Link>
          );
        })}
      </div>
      <p className="mt-1 text-xs leading-normal text-muted-foreground">Frekuensi masa lalu, bukan ramalan. Setiap hal berdiri sendiri.</p>
    </SectionCard>
  );
}

/* ------------------------------------------------------------------ charts */

/** Where today's price sits in the one-year range, with both ends dated. */
export function PriceRange({ low, high, price, lowDate, highDate }: { low: number; high: number; price: number; lowDate: string | null; highDate: string | null }) {
  const p = high > low ? Math.min(1, Math.max(0, (price - low) / (high - low))) : 0;
  return (
    <div>
      <div className="mt-3.5 flex items-baseline justify-between gap-2.5">
        <span className="text-[12.5px] text-muted-foreground">Sekarang</span>
        <span className="font-mono text-[15px] font-bold tabular-nums">{formatPrice(price)}</span>
      </div>
      <div
        className="relative mx-[7px] mt-3 h-2 rounded"
        style={{ background: "linear-gradient(90deg, color-mix(in srgb, var(--viz-diverging-neg) 45%, transparent), var(--viz-raised) 50%, color-mix(in srgb, var(--viz-diverging-pos) 45%, transparent))" }}
        role="img"
        aria-label={`Harga ${formatPrice(price)} di antara terendah ${formatPrice(low)} dan tertinggi ${formatPrice(high)} setahun`}
      >
        <div className="absolute top-[-5px] h-[18px] w-3.5 rounded border-2 border-card bg-foreground" style={{ left: `calc(${p * 100}% - 7px)` }} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <div className="font-mono text-[13px] font-semibold tabular-nums">{formatPrice(low)}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">terendah setahun{lowDate ? `, ${dateLong(lowDate)}` : ""}</div>
        </div>
        <div className="text-right">
          <div className="font-mono text-[13px] font-semibold tabular-nums">{formatPrice(high)}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">tertinggi setahun{highDate ? `, ${dateLong(highDate)}` : ""}</div>
        </div>
      </div>
    </div>
  );
}

/**
 * One column per year, drawn in HTML so the labels stay the same size at
 * any width. The latest year is solid; losses hang below the zero line.
 */
export function YearColumns({ values, years, format, label }: { values: (number | null)[]; years: number[]; format: (v: number) => string; label: string }) {
  const nums = values.filter((v): v is number => v !== null);
  if (nums.length === 0) return null;
  const max = Math.max(0, ...nums);
  const min = Math.min(0, ...nums);
  const range = max - min || 1;
  const TOP = 20;
  const PLOT = 110;
  const zero = TOP + (PLOT * max) / range;
  const lastIdx = values.length - 1;
  return (
    <div role="img" aria-label={`${label}: ${values.map((v, i) => `${years[i]} ${v === null ? "tidak ada" : format(v)}`).join(", ")}`}>
      <div className="relative" style={{ height: TOP + PLOT + 4 }}>
        <div className="absolute inset-x-0 border-t border-[var(--viz-baseline)]" style={{ top: zero }} />
        <div className="absolute inset-0 grid" style={{ gridTemplateColumns: `repeat(${values.length}, minmax(0, 1fr))` }}>
          {values.map((v, i) => {
            const last = i === lastIdx;
            if (v === null)
              return (
                <div key={i} className="relative">
                  <span className="absolute inset-x-0 text-center text-[11px] text-muted-foreground" style={{ top: zero - 18 }}>
                    -
                  </span>
                </div>
              );
            const h = Math.max(2, (PLOT * Math.abs(v)) / range);
            const top = v >= 0 ? zero - h : zero;
            const color = v >= 0 ? "var(--viz-accent)" : "var(--viz-diverging-neg)";
            return (
              <div key={i} className="relative">
                <div className="absolute left-1/2 w-[58%] max-w-10 -translate-x-1/2 rounded-[3px]" style={{ top, height: h, background: color, opacity: last ? 1 : 0.42 }} />
                <span className={`absolute inset-x-0 whitespace-nowrap text-center font-mono text-[11px] tabular-nums ${last ? "font-semibold text-foreground" : "text-muted-foreground"}`} style={{ top: (v >= 0 ? top : zero) - 17 }}>
                  {format(v)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      <div className="grid" style={{ gridTemplateColumns: `repeat(${values.length}, minmax(0, 1fr))` }}>
        {years.map((y) => (
          <span key={y} className="text-center text-[11px] text-muted-foreground">
            {y}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Two figures side by side with a divider. */
export function TwoFigures({ items }: { items: { value: string; caption: string; color: string }[] }) {
  return (
    <div className="mt-3.5 grid grid-cols-2 gap-3">
      {items.map((it, i) => (
        <div key={it.caption} className={`min-w-0 ${i > 0 ? "border-l border-border pl-3" : ""}`}>
          <div className="font-mono text-xl font-bold leading-tight tabular-nums" style={{ color: it.color }}>
            {it.value}
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">{it.caption}</div>
        </div>
      ))}
    </div>
  );
}

/** Rupiah amounts on a chart axis, in one unit for the whole series. */
export function amountUnit(values: (number | null)[]): { divisor: number; unit: string; format: (v: number) => string } {
  const maxAbs = Math.max(0, ...values.filter((v): v is number => v !== null).map(Math.abs));
  const [divisor, unit] = maxAbs >= 1e12 ? [1e12, "Rp triliun"] : [1e9, "Rp miliar"];
  return {
    divisor,
    unit,
    format: (v: number) => {
      const x = v / divisor;
      return idNum(x, Math.abs(x) < 1 ? 2 : Math.abs(x) < 100 ? 1 : 0);
    },
  };
}

export const ICONS = { harga: ChartLine, laba: BarChart3, bank: Landmark, dividen: Coins, data: List };
