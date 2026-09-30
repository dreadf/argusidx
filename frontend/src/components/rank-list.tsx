import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

export interface RankRow {
  code: string;
  name: string;
  /** Right-aligned headline value (already formatted, sign included). */
  value: ReactNode;
  /** Small line under the value. */
  sub?: ReactNode;
  href?: string;
}

/**
 * Leaderboard rows: rank badge, code + name, one bold value. The first
 * row is raised so the list reads as a ranking, not as a table of cards.
 */
export function RankList({ rows, startRank = 1 }: { rows: RankRow[]; startRank?: number }) {
  return (
    <div>
      {rows.map((row, i) => {
        const rank = startRank + i;
        const first = rank === 1;
        return (
          <Link
            key={row.code}
            href={row.href ?? `/saham/${row.code}`}
            className={`group/row flex items-center gap-3 px-3 py-3 transition-colors ${first ? "mb-1 rounded-[14px] bg-[var(--viz-raised)] hover:brightness-110" : "border-b border-border hover:bg-muted"}`}
          >
            <span
              className={`flex size-7 shrink-0 items-center justify-center rounded-md text-[12.5px] font-bold ${
                first ? "bg-accent text-accent-foreground" : "bg-[var(--viz-raised)] text-muted-foreground"
              }`}
            >
              {rank}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[15px] font-bold leading-snug text-foreground">{row.code}</span>
              <span className="block truncate text-xs text-muted-foreground">{row.name}</span>
            </span>
            <span className="text-right">
              <span className={`block font-mono font-bold tabular-nums text-foreground ${first ? "text-lg" : "text-base"}`}>{row.value}</span>
              {row.sub && <span className="block font-mono text-[11.5px] text-muted-foreground">{row.sub}</span>}
            </span>
            <ChevronRight className="size-[18px] shrink-0 text-muted-foreground transition-transform group-hover/row:translate-x-0.5" />
          </Link>
        );
      })}
    </div>
  );
}
