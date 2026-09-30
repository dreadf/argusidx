import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight, Info } from "lucide-react";

/** Uppercase group label above a run of rows. */
export function GroupLabel({ children }: { children: ReactNode }) {
  return <div className="mb-1 mt-[22px] text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">{children}</div>;
}

/**
 * List row for the Temuan lists (Peringkat, Tanda): optional
 * icon tile, title, one supporting line, chevron.
 */
export function ExploreRow({ href, title, line, icon }: { href: string; title: string; line: string; icon?: ReactNode }) {
  return (
    <Link href={href} className="group/row flex items-center gap-3 border-b border-border py-3 transition-colors first:border-t hover:bg-muted">
      {icon && <span className="flex size-[30px] shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">{icon}</span>}
      <span className="min-w-0 flex-1">
        <span className="block text-[14.5px] font-semibold leading-snug text-foreground">{title}</span>
        <span className="mt-0.5 block text-xs leading-normal text-muted-foreground">{line}</span>
      </span>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover/row:translate-x-0.5" />
    </Link>
  );
}

/** Dashed info box used for the one-line rules note under a list. */
export function Note({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`flex gap-2.5 rounded-[14px] border border-dashed border-[var(--border-strong,rgba(255,255,255,0.14))] px-3.5 py-3 text-[12.5px] leading-normal text-muted-foreground ${className}`}>
      <Info className="mt-px size-4 shrink-0" strokeWidth={1.7} />
      <span>{children}</span>
    </div>
  );
}
