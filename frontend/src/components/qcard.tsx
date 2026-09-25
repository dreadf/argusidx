import type { ReactNode } from "react";

/**
 * The card every situation and finding chart sits in: a plain question as
 * the title, one line saying what is measured, the chart, a worked
 * "Cara membaca" example, and a one-sentence takeaway.
 */
export function QCard({
  question,
  define,
  children,
  howTo,
  takeaway,
}: {
  question: string;
  define: string;
  children: ReactNode;
  howTo: ReactNode;
  takeaway: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card px-[18px] py-[22px] md:p-7">
      <h3 className="text-[17px] font-bold leading-snug text-foreground">{question}</h3>
      <p className="mt-1.5 text-[13px] leading-normal text-muted-foreground">{define}</p>
      <div className="mt-5">{children}</div>
      <div className="mt-4 rounded-xl bg-[var(--viz-raised)] px-3.5 py-3 text-[13px] leading-normal text-foreground">
        <b className="text-[var(--viz-accent)]">Cara membaca:</b> {howTo}
      </div>
      <p className="mt-3.5 text-sm font-semibold leading-normal text-foreground md:text-[15px]">{takeaway}</p>
    </div>
  );
}

export function Legend({ children }: { children: ReactNode }) {
  return <div className="mt-3 flex flex-col gap-2">{children}</div>;
}
