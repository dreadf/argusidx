import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { BackLink } from "@/components/back-link";

/**
 * Small layout kit shared by every page. The hierarchy scale is fixed:
 * page title (H1) 26/32px, section title (H2) 20/22px, item 15px,
 * supporting line 13px muted. Section titles are always larger than
 * anything inside them; muted text never carries a heading role.
 */

export function Page({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <main className={`mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8 ${className}`}>{children}</main>;
}

export function DatePill({ children }: { children: ReactNode }) {
  return (
    <span className="whitespace-nowrap rounded-md border border-border px-2.5 py-1 text-[11.5px] text-muted-foreground">{children}</span>
  );
}

/** Small uppercase label above a block. `muted` for secondary blocks. */
export function Eyebrow({ children, muted = false, className = "" }: { children: ReactNode; muted?: boolean; className?: string }) {
  return <div className={`text-[11px] font-semibold uppercase tracking-[0.08em] ${muted ? "text-muted-foreground" : "text-[var(--viz-accent)]"} ${className}`}>{children}</div>;
}

export function PageTitle({ title, pill, back }: { title: string; pill?: ReactNode; back?: { href: string; label: string } }) {
  return (
    <div>
      {back && <BackLink fallback={back} />}
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-[26px] font-bold leading-tight tracking-[-0.02em] text-foreground md:text-[32px]">{title}</h1>
        {pill && <DatePill>{pill}</DatePill>}
      </div>
    </div>
  );
}

/** One short supporting line under a title. Keep it to a sentence. */
export function Sub({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`mt-1.5 text-[13px] leading-normal text-muted-foreground md:text-sm ${className}`}>{children}</p>;
}

export function H2({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <h2 className={`text-xl font-bold leading-tight tracking-[-0.01em] text-foreground md:text-[22px] ${className}`}>{children}</h2>;
}

export function H3({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <h3 className={`text-[15px] font-semibold leading-snug text-foreground ${className}`}>{children}</h3>;
}

export function TextLink({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link href={href} className={`inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)] hover:underline ${className}`}>
      {children}&nbsp;&rarr;
    </Link>
  );
}

/** Two columns with a divider between them (stacked on phones). */
export function TwoCol({ left, right, ratio = "1.5fr 1fr", className = "", rightFirstOnMobile = false }: { left: ReactNode; right: ReactNode; ratio?: string; className?: string; rightFirstOnMobile?: boolean }) {
  return (
    <div className={`grid gap-8 md:gap-0 md:[grid-template-columns:var(--cols)] ${className}`} style={{ ["--cols" as string]: ratio }}>
      <div className="min-w-0 md:pr-10">{left}</div>
      <div className={`min-w-0 md:order-none md:border-l md:border-border md:pl-10 ${rightFirstOnMobile ? "order-first" : ""}`}>{right}</div>
    </div>
  );
}

export function ThreeCol({ children }: { children: [ReactNode, ReactNode, ReactNode] }) {
  return (
    <div className="grid gap-8 md:grid-cols-3 md:gap-0">
      <div className="min-w-0 md:pr-8">{children[0]}</div>
      <div className="min-w-0 md:border-l md:border-border md:px-8">{children[1]}</div>
      <div className="min-w-0 md:border-l md:border-border md:pl-8">{children[2]}</div>
    </div>
  );
}

/** Equal cells in a row with dividers between them. */
export function Cells({ children }: { children: ReactNode[] }) {
  return (
    <div className="grid" style={{ gridTemplateColumns: `repeat(${children.length}, minmax(0, 1fr))` }}>
      {children.map((child, i) => (
        <div key={i} className={`min-w-0 ${i > 0 ? "border-l border-border pl-3.5" : ""} ${i < children.length - 1 ? "pr-3.5" : ""}`}>
          {child}
        </div>
      ))}
    </div>
  );
}

export function Stat({ value, label, tone = "default", size = 22 }: { value: ReactNode; label: string; tone?: "default" | "pos" | "neg"; size?: number }) {
  const color = tone === "pos" ? "var(--viz-diverging-pos)" : tone === "neg" ? "var(--viz-diverging-neg)" : "var(--foreground)";
  return (
    <div>
      <div className="font-mono font-bold tabular-nums" style={{ color, fontSize: size }}>
        {value}
      </div>
      <div className="mt-0.5 text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

/** Underline tab bar made of links. The page decides which one is active. */
export function UnderlineTabs({ items }: { items: { label: string; href: string; active: boolean; count?: number }[] }) {
  return (
    <div className="flex gap-6 overflow-x-auto border-b border-border md:gap-8" role="tablist">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          scroll={false}
          role="tab"
          aria-selected={item.active}
          className={`-mb-px inline-flex min-h-11 items-center whitespace-nowrap border-b-2 py-3.5 text-[13px] ${
            item.active ? "border-[var(--viz-accent)] font-semibold text-[var(--viz-accent)]" : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {item.label}
          {item.count !== undefined && <span className="ml-1.5 font-mono text-xs">{item.count}</span>}
        </Link>
      ))}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-border bg-card p-4 ${className}`}>{children}</div>;
}

/** Table header row with real contrast (the previous header was barely visible). */
export function THead({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-3.5 rounded-[10px] bg-[var(--viz-raised)] px-3 py-2.5 text-xs font-semibold tracking-[0.04em] text-[#B9C4D8]">{children}</div>
  );
}

/** A tappable list row: title, one supporting line, chevron. */
export function LinkRow({
  href,
  title,
  line,
  icon,
  last,
}: {
  href: string;
  title: string;
  line?: string;
  icon?: ReactNode;
  last?: boolean;
}) {
  return (
    <Link href={href} className={`group/row flex items-center gap-3 py-3.5 transition-colors hover:bg-muted ${last ? "" : "border-b border-border"}`}>
      {icon && <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">{icon}</div>}
      <div className="min-w-0 flex-1">
        <div className="text-[15px] font-semibold leading-snug text-foreground">{title}</div>
        {line && <div className="mt-0.5 text-[13px] leading-snug text-muted-foreground">{line}</div>}
      </div>
      <ChevronRight className="size-[18px] shrink-0 text-muted-foreground transition-transform group-hover/row:translate-x-0.5" />
    </Link>
  );
}

export function Neg({ children }: { children: ReactNode }) {
  return <span className="font-mono tabular-nums text-[var(--viz-diverging-neg)]">{children}</span>;
}
export function Pos({ children }: { children: ReactNode }) {
  return <span className="font-mono tabular-nums text-[var(--viz-diverging-pos)]">{children}</span>;
}

/**
 * Disclosure required by docs/PRODUCT.md §7.3 wherever a result rests on
 * research price history rather than Sectors data (the findings' outcomes,
 * the five-year beat-gold comparison, IPO boards, the recovery and drawdown
 * base rates). Frozen dates: beat_gold.json 2026-09-12, base_rates.json and
 * ipo_boards.json 2026-09-13.
 */
export function ResearchNote({ className = "" }: { className?: string }) {
  return (
    <p className={`text-xs leading-normal text-muted-foreground ${className}`}>
      Dihitung sekali dari riwayat harga riset di luar Sectors, dan dibekukan per 12-13 Sep 2026. Bukan data langsung.
    </p>
  );
}
