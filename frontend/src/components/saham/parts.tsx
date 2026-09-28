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
import { formatPrice, idNum, signedPct } from "@/lib/format";
import type { Kesimpulan, Signal, WatchItem, WatchKind } from "@/lib/stock-read";
import { dateLong } from "@/lib/dates";

/**
 * Building blocks of the stock page (boards Baru4-Saham-*). Every card has
 * the same frame: an icon, a title that names the stock, one supporting
 * line, then its body, so sections are clearly separated.
 *
 * Two sizes, because size is hierarchy: "primary" for the reading column
 * (Kesimpulan, signals, situations, Data lengkap) and "secondary" for the
 * narrow supporting column (price, profit, dividend).
 */

const FRAME = {
  primary: { box: "rounded-[22px] p-5 md:p-7", glyph: "size-10 rounded-xl", icon: "size-5", title: "text-[21px] md:text-[24px]", sub: "mt-1.5 text-[13.5px] md:text-[14.5px]", body: "mt-3" },
  secondary: { box: "rounded-[20px] p-4 md:p-5", glyph: "size-8 rounded-[9px]", icon: "size-4", title: "text-[17px]", sub: "mt-1 text-[12.5px]", body: "mt-2" },
};

export function SectionCard({
  icon: Icon,
  title,
  sub,
  right,
  children,
  className = "",
  id,
  size = "secondary",
}: {
  icon: LucideIcon;
  title: string;
  sub?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
  size?: keyof typeof FRAME;
}) {
  const f = FRAME[size];
  return (
    <section id={id} className={`border border-border bg-card ${f.box} ${className}`}>
      <div className="flex items-start gap-3">
        <span className={`flex shrink-0 items-center justify-center bg-accent text-accent-foreground ${f.glyph}`}>
          <Icon className={f.icon} strokeWidth={1.7} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2.5">
            <h2 className={`font-bold leading-tight tracking-[-0.01em] ${f.title}`}>{title}</h2>
            {right && <div className="shrink-0 whitespace-nowrap">{right}</div>}
          </div>
          {sub && <p className={`leading-normal text-muted-foreground ${f.sub}`}>{sub}</p>}
        </div>
      </div>
      <div className={f.body}>{children}</div>
    </section>
  );
}

/** The "Artinya untuk ASII:" box under a signal or situation. */
export function Meaning({ code, children }: { code: string; children: ReactNode }) {
  return (
    <div className="mt-3 rounded-xl bg-[var(--viz-raised)] px-4 py-3 text-[14px] leading-[1.55]">
      <span className="font-bold text-[var(--viz-accent)]">Artinya untuk {code}:</span> {children}
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

/* ------------------------------------------------------------------ Kesimpulan */

const toneOf = (x: number) => (x > 0 ? "var(--viz-diverging-pos)" : x < 0 ? "var(--viz-diverging-neg)" : "var(--foreground)");

export function KesimpulanCard({ code, k }: { code: string; k: Kesimpulan }) {
  const label = "pt-0.5 text-xs font-semibold uppercase tracking-[0.05em] text-muted-foreground";
  const row = "grid gap-1 border-b border-border py-4 md:grid-cols-[170px_minmax(0,1fr)] md:gap-5 md:py-[18px]";
  return (
    <section className="rounded-[22px] border border-border bg-card p-5 md:p-7">
      <div className="text-[12px] font-semibold uppercase tracking-[0.08em] text-[var(--viz-accent)]">Kesimpulan {code}</div>
      <p className="mt-3 text-[18px] font-semibold leading-[1.45] md:text-[22px] md:leading-[1.4]">{k.headline}</p>
      {k.figures.length > 0 && (
        <div className="mt-4 grid gap-2 sm:grid-cols-2 sm:gap-3">
          {k.figures.map((f) => (
            <div key={f.label} className="rounded-xl bg-[var(--viz-raised)] px-4 py-3">
              <div className="text-xs text-muted-foreground">{f.label}</div>
              <div className="mt-1 flex items-baseline gap-4">
                <span className="font-mono text-[20px] font-bold tabular-nums" style={{ color: toneOf(f.stock) }}>
                  {signedPct(f.stock * 100, 1, true)}
                </span>
                <span className="text-[13px] text-muted-foreground">
                  {code}
                  {" · "}IHSG <span className="font-mono tabular-nums">{signedPct(f.ihsg * 100, 1, true)}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
      {k.caption && <p className="mt-2.5 text-[13px] leading-normal text-muted-foreground md:text-[13.5px]">{k.caption}</p>}
      <div className="mt-5 border-t border-border">
        <div className={row}>
          <div className={label}>Perlu diperhatikan</div>
          <div>
            {k.watch.length === 0 ? (
              <div className="text-[16px] font-bold leading-snug md:text-[17px]">Tidak ada</div>
            ) : (
              <ul className="flex flex-col gap-1">
                {k.watch.map((w) => (
                  <li key={w} className="text-[16px] font-bold leading-snug md:text-[17px]">
                    {w}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-1.5 text-[13.5px] leading-normal text-muted-foreground md:text-[14.5px]">
              {k.watch.length === 0 ? `Tidak ada keadaan khusus yang sedang terjadi di ${code}.` : (k.rarest ?? "Rinciannya ada di bawah.")}
            </div>
          </div>
        </div>
        {k.rows.map((r) => (
          <div key={r.label} className={row}>
            <div className={label}>{r.label}</div>
            <div>
              <div className="text-[16px] font-bold leading-snug md:text-[17px]">{r.state}</div>
              <div className="mt-1 text-[13.5px] leading-normal text-muted-foreground md:text-[14.5px]">{r.explain}</div>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs leading-normal text-muted-foreground">
        Setiap baris memakai aturan tetap yang sama untuk semua saham, dan berdiri sendiri: tidak ada nilai gabungan.{" "}
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
    <SectionCard size="primary" icon={FlaskConical} title={`Sinyal populer yang ada di ${code}`} sub="Alasan yang sering dipakai orang untuk memilih saham, dan hasil uji kami.">
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
          <div key={s.key} className={`py-5 ${i > 0 ? "border-t border-border" : ""}`}>
            <div className="flex items-start gap-3">
              <Link href={s.href} className="min-w-0 flex-1 text-[16px] font-semibold leading-snug hover:underline md:text-[17px]">
                {s.title}
              </Link>
              <VerdictChip kind={s.verdict} />
            </div>
            <p className="mt-2 text-[14px] leading-[1.55]">{s.here}</p>
            <p className="mt-1 text-[14px] leading-[1.55]">
              <Muted>Hasil uji:</Muted> {s.result.charAt(0).toUpperCase() + s.result.slice(1)}
            </p>
            {s.meaning && <Meaning code={code}>{s.meaning}</Meaning>}
          </div>
        ))
      )}
      <p className="mt-2 text-xs leading-normal text-muted-foreground">Terbukti berarti berlaku rata-rata pada ratusan saham di data uji, bukan jaminan untuk satu saham.</p>
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

export function WatchSection({ code, items, checked, className = "" }: { code: string; items: WatchItem[]; checked: number; className?: string }) {
  const title = `Yang perlu diperhatikan di ${code}`;
  if (items.length === 0) {
    return (
      <SectionCard size="primary" icon={Flag} title={title} className={className}>
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
    <SectionCard size="primary" icon={Flag} title={title} sub={`Keadaan ${code} sekarang, dan apa yang biasanya terjadi sesudahnya.`} className={className}>
      <div>
        {items.map((w, i) => {
          const Icon = WATCH_ICON[w.kind];
          return (
            <Link key={w.kind} href={w.href} className={`block py-5 ${i > 0 ? "border-t border-border" : ""}`}>
              <div className="flex items-center gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-[9px] bg-accent text-accent-foreground">
                  <Icon className="size-4" strokeWidth={1.8} />
                </span>
                <span className="min-w-0 flex-1 text-[16px] font-semibold leading-snug md:text-[17px]">{w.title}</span>
                <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
              </div>
              <p className="mt-2.5 text-[14px] leading-[1.55]">{w.here}</p>
              {(w.rate || w.note) && (
                <Meaning code={code}>
                  {w.rate && (
                    <>
                      {w.rate.lead} <b className="font-mono tabular-nums">{w.rate.figure}</b> {w.rate.rest}
                    </>
                  )}
                  {w.rate && w.note ? " " : ""}
                  {w.note}
                </Meaning>
              )}
            </Link>
          );
        })}
      </div>
      <p className="mt-2 text-xs leading-normal text-muted-foreground">Angka dari kejadian masa lalu, bukan ramalan.</p>
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
          <div className="mt-0.5 text-xs text-muted-foreground">terendah setahun</div>
          {lowDate && <div className="text-xs text-muted-foreground">{dateLong(lowDate)}</div>}
        </div>
        <div className="text-right">
          <div className="font-mono text-[13px] font-semibold tabular-nums">{formatPrice(high)}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">tertinggi setahun</div>
          {highDate && <div className="text-xs text-muted-foreground">{dateLong(highDate)}</div>}
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
