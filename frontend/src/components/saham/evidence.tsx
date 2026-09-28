import Link from "next/link";
import type { Evidence } from "@/lib/purposes";
import { VERDICT_CHIP } from "@/lib/verdict-chip";

/** Outline chip for a tested verdict, or a filled one for a past frequency. Client-safe. */
export function VerdictChip({ kind }: { kind: Evidence["kind"] }) {
  if (kind === null) return null;
  if (kind === "base")
    return <span className="inline-flex h-6 shrink-0 items-center whitespace-nowrap rounded-md border border-border bg-[var(--viz-raised)] px-2 text-[11.5px] font-semibold">Frekuensi</span>;
  const v = VERDICT_CHIP[kind];
  return (
    <span className="inline-flex h-6 shrink-0 items-center whitespace-nowrap rounded-md border px-2 text-[11.5px] font-semibold" style={{ color: v.color, borderColor: v.color }}>
      {v.label}
    </span>
  );
}

export function EvidenceRows({ items }: { items: Evidence[] }) {
  return (
    <>
      {items.map((e, i) => (
        <div key={i} className="flex items-start gap-2.5 border-t border-border py-3">
          <div className="min-w-0 flex-1 text-[13.5px] leading-[1.55]">
            {e.text}
            {e.href && (
              <>
                {" "}
                <Link href={e.href} className="whitespace-nowrap text-[var(--viz-accent)] underline">
                  Buktinya
                </Link>
              </>
            )}
          </div>
          <VerdictChip kind={e.kind} />
        </div>
      ))}
    </>
  );
}
