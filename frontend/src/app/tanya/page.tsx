"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ChevronRight, Send } from "lucide-react";
import { DatePill } from "@/components/kit";
import { VerdictMark } from "@/components/verdict-mark";
import type { Quota } from "@/lib/ask/quota";
import type { AskResponse } from "@/lib/ask/types";

const EXAMPLE_QUESTIONS = [
  "Jelaskan BBCA dengan bahasa sederhana",
  "Apakah ada tanda peringatan di TLKM?",
  "Apakah saham murah (P/E rendah) lebih untung?",
  "Apa yang biasanya terjadi kalau saham turun 30%?",
];

type Turn = { q: string; state: "loading" } | { q: string; state: "error"; message: string } | { q: string; state: "done"; data: AskResponse };

/**
 * Tanya: ask a question about the data. Not search (the magnifier in the
 * header finds a stock by code or name). Every answer lists the facts it
 * rests on, names whether AI wrote the sentence, and never advises.
 */
export default function TanyaPage() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [initialQuota, setInitialQuota] = useState<Quota | null>(null);
  const busy = turns.some((t) => t.state === "loading");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/ask", { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { quota: Quota | null }) => setInitialQuota(j.quota))
      .catch(() => {});
  }, []);

  async function submit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || busy) return;
    setQuestion("");
    const index = turns.length;
    setTurns((prev) => [...prev, { q: trimmed, state: "loading" }]);
    const settle = (turn: Turn) => {
      setTurns((prev) => prev.map((t, i) => (i === index ? turn : t)));
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }), 50);
    };
    try {
      const history = turns
        .filter((t): t is Extract<Turn, { state: "done" }> => t.state === "done")
        .slice(-2)
        .map((t) => ({ q: t.q, a: t.data.prose, stockCode: t.data.stockCode }));
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, history }),
      });
      const json = await res.json();
      if (!res.ok) settle({ q: trimmed, state: "error", message: json.error ?? "Terjadi kesalahan." });
      else settle({ q: trimmed, state: "done", data: json as AskResponse });
    } catch {
      settle({ q: trimmed, state: "error", message: "Tidak bisa menghubungi server. Coba lagi." });
    }
  }

  const examples = (
    <div>
      <div className="text-[15px] font-semibold">Contoh pertanyaan</div>
      <ul className="mt-1">
        {EXAMPLE_QUESTIONS.map((q) => (
          <li key={q}>
            <button type="button" onClick={() => void submit(q)} className="flex min-h-[52px] w-full items-center justify-between gap-3 border-b border-border text-left text-sm">
              <span>{q}</span>
              <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-6 text-[15px] font-semibold">Tidak dijawab</div>
      <p className="mt-1.5 text-[13.5px] leading-normal text-muted-foreground">Saran beli, jual, tahan, dan prediksi harga.</p>
    </div>
  );

  const lastQuota = [...turns].reverse().find((t): t is Extract<Turn, { state: "done" }> => t.state === "done" && t.data.quota !== null)?.data.quota ?? initialQuota;
  const quotaLine = lastQuota
    ? lastQuota.remaining > 0
      ? `Sisa ${lastQuota.remaining} dari ${lastQuota.limit} jawaban AI dalam 6 jam.`
      : `Jawaban AI habis (${lastQuota.limit} per 6 jam). Sisanya dijawab dari data tanpa AI${lastQuota.resetAt ? `, AI kembali ${formatWait(lastQuota.resetAt)}` : ""}.`
    : null;

  const input = (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void submit(question);
      }}
      className="flex items-center gap-2.5 rounded-full border border-border bg-card py-1.5 pl-[18px] pr-1.5"
    >
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Tanya tentang saham IDX..."
        maxLength={300}
        aria-label="Pertanyaan"
        className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
      />
      {lastQuota && (
        <span
          title={`Sisa ${lastQuota.remaining} dari ${lastQuota.limit} jawaban AI dalam 6 jam`}
          className={`shrink-0 whitespace-nowrap rounded-full border px-2.5 py-1 font-mono text-[12px] font-semibold tabular-nums ${lastQuota.remaining > 0 ? "border-border text-[var(--viz-accent)]" : "border-[var(--viz-status-critical)] text-[var(--viz-status-critical)]"}`}
        >
          AI {lastQuota.remaining}/{lastQuota.limit}
        </span>
      )}
      <button type="submit" disabled={busy || question.trim().length === 0} aria-label="Kirim" className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground disabled:opacity-50">
        <Send className="size-[18px]" />
      </button>
    </form>
  );

  const conversation = (
    <div className="flex flex-col gap-3.5">
      {turns.length === 0 && (
        <p className="text-sm text-muted-foreground md:hidden">Pilih contoh di bawah, atau ketik pertanyaan sendiri.</p>
      )}
      {turns.map((turn, i) => (
        <div key={i} className="flex flex-col gap-3.5">
          <div className="max-w-[86%] self-end rounded-[18px_18px_4px_18px] bg-primary px-[15px] py-[11px] text-sm leading-snug text-primary-foreground">{turn.q}</div>
          {turn.state === "loading" && <div className="self-start text-sm text-muted-foreground">Memproses...</div>}
          {turn.state === "error" && <p className="self-start text-sm text-[var(--viz-status-critical)]">{turn.message}</p>}
          {turn.state === "done" && <AnswerView data={turn.data} />}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-[26px] font-bold leading-tight tracking-[-0.02em] md:text-[32px]">Tanya</h1>
        <DatePill>Data 13/09/2026</DatePill>
      </div>
      <p className="mt-1.5 text-[13px] text-muted-foreground md:text-sm">Tanya apa saja tentang data saham IDX. Bukan saran.</p>

      <div className="mt-5 grid gap-8 md:mt-6 md:grid-cols-[1.5fr_1fr] md:gap-0">
        <div className="min-w-0 md:pr-10">
          {conversation}
          <div className="sticky bottom-[66px] mt-5 bg-background pb-2 pt-2 md:static md:bg-transparent md:pb-0">
            {input}
            {quotaLine && <p className="mt-2 px-1 text-[11.5px] text-muted-foreground">{quotaLine}</p>}
            <div className="mt-2.5 flex gap-2 overflow-x-auto md:hidden">
              {EXAMPLE_QUESTIONS.slice(0, 3).map((q) => (
                <button key={q} type="button" onClick={() => void submit(q)} className="shrink-0 whitespace-nowrap rounded-full border border-border px-3.5 py-2 text-[12.5px] text-[var(--viz-accent)]">
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="hidden min-w-0 md:block md:border-l md:border-border md:pl-10">{examples}</div>
      </div>
    </main>
  );
}

function formatWait(resetAt: string): string {
  const minutes = Math.max(1, Math.ceil((new Date(resetAt).getTime() - Date.now()) / 60000));
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `dalam ${h > 0 ? `${h} jam ` : ""}${m > 0 || h === 0 ? `${m} menit` : ""}`.trim();
}

function AnswerView({ data }: { data: AskResponse }) {
  return (
    <div className="max-w-[96%] self-start rounded-[18px_18px_18px_4px] border border-border bg-card px-4 py-3.5">
      <p className="text-sm leading-normal">{data.prose}</p>

      {data.findings.length > 0 && (
        <ul className="mt-3 space-y-2.5 border-t border-border pt-3">
          {data.findings.map((row) => (
            <li key={row.belief} className="flex items-start gap-3">
              <span className="mt-0.5 shrink-0">
                <VerdictMark verdict={row.verdict} size={18} />
              </span>
              <div>
                <p className="text-sm leading-snug">{row.title_short_id ?? row.belief_id}</p>
                <p className="text-[13px] leading-snug text-muted-foreground">{row.result_short_id ?? row.label_id}</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {data.facts.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-border pt-3 text-[13px] leading-normal text-muted-foreground">
          {data.facts.map((fact) => (
            <li key={fact} className="flex gap-2">
              <span>&bull;</span>
              <span>{fact}</span>
            </li>
          ))}
        </ul>
      )}

      {data.stockCode && (
        <Link href={`/saham/${data.stockCode}`} className="mt-2.5 inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
          Halaman {data.stockCode} &rarr;
        </Link>
      )}

      {data.links.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-x-4">
          {data.links.map((l) => (
            <Link key={l.href} href={l.href} className="inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
              {l.label} &rarr;
            </Link>
          ))}
        </div>
      )}

      <p className="mt-2.5 text-[11px] text-muted-foreground">
        {data.source === "gemini"
          ? "Kalimat dirangkai dengan bantuan AI (Gemini), hanya dari fakta di atas."
          : data.limitReached
            ? `Batas jawaban AI (${data.quota?.limit ?? 3} per 6 jam) tercapai. Dijawab dari data kami, tanpa AI${data.quota?.resetAt ? `. AI kembali ${formatWait(data.quota.resetAt)}` : ""}.`
            : "Dijawab dari data kami, tanpa AI."}
      </p>
    </div>
  );
}
