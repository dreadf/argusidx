import type { ReactNode } from "react";

/**
 * The evidence card every situation and finding chart sits in: a plain
 * question as the title, one line saying what is measured, then the chart
 * and its text. With a `basis` line the chart sits BESIDE the text on web
 * (bold takeaway, basis, "Cara membaca" box) and stacks on a phone as chart
 * plus basis, the box, then the takeaway (boards SituasiDetail-BawahPuncak,
 * -Langganan). A chart too wide to sit beside text (axes, tables) passes no
 * `basis` and keeps the stacked order: chart, box, takeaway. The "dari 100"
 * unit is carried by the takeaway sentence, not by an axis label.
 */
export function QCard({
  question,
  define,
  children,
  howTo,
  takeaway,
  basis,
}: {
  question: string;
  define: string;
  children: ReactNode;
  howTo: ReactNode;
  takeaway: ReactNode;
  /** Text under the takeaway, beside the chart. `null`: sit beside the takeaway without a basis line (numbers). Omitted: stacked. */
  basis?: ReactNode | null;
}) {
  const box = (
    <div className="rounded-xl bg-[var(--viz-raised)] px-3.5 py-3 text-[13px] leading-normal text-foreground">
      <b className="text-[var(--viz-accent)]">Cara membaca:</b> {howTo}
    </div>
  );
  return (
    <div className="rounded-2xl border border-border bg-card px-[18px] py-[22px] md:p-7">
      <h3 className="text-base font-bold leading-snug text-foreground md:text-[17px]">{question}</h3>
      <p className="mt-1 text-[12.5px] leading-normal text-muted-foreground">{define}</p>
      {basis === undefined ? (
        <>
          <div className="mt-5">{children}</div>
          <div className="mt-4">{box}</div>
          <p className="mt-3.5 text-sm font-semibold leading-normal text-foreground md:text-[15px]">{takeaway}</p>
        </>
      ) : basis === null ? (
        // Beside without a basis line: a row of numbers (1.7fr) next to takeaway and box (1fr), board TemuanDetail-Asing "kenapa terlihat menjanjikan".
        <div className="mt-5 grid items-center gap-y-4 md:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)] md:gap-x-8 md:gap-y-3">
          <div className="md:row-span-2">{children}</div>
          <div className="md:col-start-2 md:row-start-2">{box}</div>
          <p className="text-[15px] font-semibold leading-normal text-foreground md:col-start-2 md:row-start-1">{takeaway}</p>
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-5 gap-y-4 md:gap-x-9 md:gap-y-3">
          <div className="col-start-1 row-start-1 md:row-span-3">{children}</div>
          <div className="col-start-2 row-start-1 text-[12.5px] leading-normal text-muted-foreground md:row-start-2">{basis}</div>
          <div className="col-span-2 row-start-2 md:col-span-1 md:col-start-2 md:row-start-3">{box}</div>
          <p className="col-span-2 row-start-3 text-[15px] font-semibold leading-normal text-foreground md:col-span-1 md:col-start-2 md:row-start-1">{takeaway}</p>
        </div>
      )}
    </div>
  );
}

export function Legend({ children }: { children: ReactNode }) {
  return <div className="mt-3 flex flex-col gap-2">{children}</div>;
}

/**
 * The side column of an evidence page: "Apa yang diuji" or "Kapan situasi
 * ini berlaku" first, then "Muncul di aplikasi", then "Batasan". Callers
 * render only the blocks they have content for.
 */
export function EvidenceSide({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-7">{children}</div>;
}

export function SideBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h2 className="text-lg font-bold leading-tight tracking-[-0.01em] text-foreground">{title}</h2>
      <div className="mt-2.5">{children}</div>
    </div>
  );
}

/** A row of big numbers with a caption each, coloured by sign (boards: "+2,6%", "-0,8%", "+6,7%"). */
export function NumberRow({ items }: { items: { value: string; caption: string; tone?: "pos" | "neg" | "plain" }[] }) {
  const color = { pos: "var(--viz-diverging-pos)", neg: "var(--viz-diverging-neg)", plain: "var(--foreground)" };
  return (
    <div className="flex gap-3.5">
      {items.map((x) => (
        <div key={x.caption} className="min-w-0 flex-1">
          <div className="font-mono text-2xl font-bold tracking-[-0.02em] md:text-[26px]" style={{ color: color[x.tone ?? "plain"] }}>
            {x.value}
          </div>
          <div className="mt-1 text-xs leading-snug text-muted-foreground">{x.caption}</div>
        </div>
      ))}
    </div>
  );
}

/** Bulleted "Batasan" list, board type size. */
export function LimitList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-[18px] text-[13.5px] leading-[1.7] text-muted-foreground">
      {items.map((l) => (
        <li key={l}>{l}</li>
      ))}
    </ul>
  );
}
