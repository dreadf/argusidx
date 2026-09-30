"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowUp, Sparkle } from "lucide-react";

/**
 * "Tanya tentang ASII" (board Baru4-Tanya-ASII): suggested questions and a
 * box that opens Tanya with the stock already attached (the "Tentang ASII"
 * chip there), so a question need not repeat the code.
 */
export function TanyaCard({ code, suggestions, className = "" }: { code: string; suggestions: string[]; className?: string }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const ask = (q: string) => `/tanya?kode=${code}&q=${encodeURIComponent(q)}`;
  return (
    <section className={`rounded-[20px] border border-border bg-card p-4 md:p-5 ${className}`}>
      <div className="flex items-center gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-[9px] bg-accent text-accent-foreground">
          <Sparkle className="size-4" strokeWidth={1.7} />
        </span>
        <h2 className="text-[17px] font-bold leading-tight tracking-[-0.01em]">Tanya tentang {code}</h2>
      </div>
      <div className="mt-3 flex flex-col items-start gap-1.5">
        {suggestions.map((s) => (
          <Link
            key={s}
            href={ask(s)}
            className="inline-flex min-h-8 items-center rounded-lg border border-border bg-[var(--viz-raised)] px-2.5 py-1.5 text-left text-[12.5px] font-medium leading-snug transition-colors hover:border-[var(--viz-accent)] hover:text-[var(--viz-accent)]"
          >
            {s}
          </Link>
        ))}
        <Link
          href={`/tanya?kode=${code}`}
          className="inline-flex min-h-8 items-center rounded-lg border border-border bg-[var(--viz-raised)] px-2.5 py-1.5 text-left text-[12.5px] font-medium leading-snug transition-colors hover:border-[var(--viz-accent)] hover:text-[var(--viz-accent)]"
        >
          Periksa pesan tentang {code}
        </Link>
      </div>
      <form
        className="mt-3 rounded-xl border border-[var(--viz-baseline)] px-3 pb-2 pt-2.5"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) router.push(ask(text.trim()));
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={`Tanya soal ${code}...`}
          aria-label={`Pertanyaan tentang ${code}`}
          className="h-7 w-full bg-transparent text-[13.5px] outline-none placeholder:text-muted-foreground"
        />
        <div className="mt-1.5 flex items-center justify-between gap-2">
          <span className="text-[11.5px] text-muted-foreground">Dijawab dari data ArgusIDX, bukan saran</span>
          <button
            type="submit"
            aria-label="Kirim pertanyaan"
            disabled={!text.trim()}
            className="inline-flex size-[30px] items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors enabled:hover:bg-primary/85 disabled:opacity-50"
          >
            <ArrowUp className="size-4" />
          </button>
        </div>
      </form>
    </section>
  );
}
