"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { TanyaComposer, aiUsable, type AskMode } from "@/components/tanya-composer";
import { ClaimRow, ConfirmRow, DATA_ONLY_LINE, LimitNote, StockCardView, TipNoticeView, UnavailableCard, UserBubble } from "@/components/tanya-results";
import type { Quota } from "@/lib/ask/quota";
import { readTip, type TipReading } from "@/lib/ask/tip-reader";
import { beliefSlug, buildTipView, findUnknownCodes, routeInput, tipDeps, type ClaimRowView, type TipBundle } from "@/lib/ask/tip-view";
import type { AskResponse } from "@/lib/ask/types";
import type { FindingRow } from "@/lib/findings-data";

const EXAMPLES = ["BBCA oversold pasti mantul, asing borong", "Jelaskan BBCA dengan bahasa sederhana", "Dividen gede, TLKM wajib koleksi"];

type Turn =
  | { kind: "tip"; q: string; reading: TipReading; unknown: string[]; confirmed: string[] }
  | { kind: "ask"; q: string; state: "loading" }
  | { kind: "ask"; q: string; state: "error" }
  | { kind: "ask"; q: string; state: "done"; data: AskResponse; limitNote: boolean }
  | { kind: "unavailable"; q: string };

/**
 * Tanya: one composer for two things. A pasted message is read in the
 * browser against the tested findings and never leaves it; a question goes
 * to /api/ask, answered from data and, when the user picks it and has
 * allowance left, worded by AI. Neither path gives advice.
 */
export default function TanyaView({ asOf }: { asOf: string }) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<AskMode>("ai");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const bundleRef = useRef<Promise<TipBundle | null> | null>(null);
  const [bundle, setBundle] = useState<TipBundle | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const busy = turns.some((t) => t.kind === "ask" && t.state === "loading");

  useEffect(() => {
    fetch("/api/ask", { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { quota: Quota | null }) => {
        setQuota(j.quota);
        setAiConfigured(j.quota !== null);
      })
      .catch(() => {});
  }, []);

  /** Stocks, findings and situation lines for reading a message. Fetched once, and only when the user starts typing. */
  function loadBundle(): Promise<TipBundle | null> {
    bundleRef.current ??= fetch("/api/ask/tip-data")
      .then((r) => (r.ok ? (r.json() as Promise<TipBundle>) : null))
      .catch(() => null)
      .then((b) => {
        if (b) setBundle(b);
        else bundleRef.current = null;
        return b;
      });
    return bundleRef.current;
  }
  useEffect(() => {
    if (text.length > 0) void loadBundle();
  }, [text.length > 0]); // eslint-disable-line react-hooks/exhaustive-deps

  function scrollToEnd() {
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }), 50);
  }

  async function submit() {
    const q = text.trim();
    if (!q || busy) return;
    setText("");

    const b = await loadBundle();
    let route: "tip" | "question" = q.length <= 300 ? "question" : "tip";
    let reading: TipReading | null = null;
    let unknown: string[] = [];
    if (b) {
      reading = readTip(q, tipDeps(b));
      unknown = findUnknownCodes(q, new Set(b.stocks.map((s) => s.code)));
      route = routeInput(q, reading, unknown);
    } else if (route === "tip") {
      setTurns((prev) => [...prev, { kind: "unavailable", q }]);
      scrollToEnd();
      return;
    }

    if (route === "tip" && reading) {
      setTurns((prev) => [...prev, { kind: "tip", q, reading, unknown, confirmed: [] }]);
      scrollToEnd();
      return;
    }

    const usable = aiUsable(aiConfigured, quota);
    // The user wanted AI but the allowance is used up: answer from data and say why.
    const limitNote = mode === "ai" && aiConfigured === true && quota !== null && quota.remaining === 0;
    const sendMode: AskMode = usable ? mode : "data";
    const index = turns.length;
    setTurns((prev) => [...prev, { kind: "ask", q, state: "loading" }]);
    scrollToEnd();
    const settle = (turn: Turn) => {
      setTurns((prev) => prev.map((t, i) => (i === index ? turn : t)));
      scrollToEnd();
    };
    try {
      const history = turns
        .filter((t): t is Extract<Turn, { kind: "ask"; state: "done" }> => t.kind === "ask" && t.state === "done")
        .slice(-2)
        .map((t) => ({ q: t.q, a: t.data.prose, stockCode: t.data.stockCode }));
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, history, mode: sendMode }),
      });
      const json = await res.json();
      if (!res.ok) {
        settle({ kind: "ask", q, state: "error" });
      } else {
        const data = json as AskResponse;
        if (data.quota) setQuota(data.quota);
        settle({ kind: "ask", q, state: "done", data, limitNote: limitNote || data.notice === "limit" });
      }
    } catch {
      settle({ kind: "ask", q, state: "error" });
    }
  }

  const composer = (
    <TanyaComposer value={text} onChange={setText} onSubmit={() => void submit()} mode={mode} onMode={setMode} aiConfigured={aiConfigured} quota={quota} busy={busy} menuUp={turns.length > 0} />
  );

  if (turns.length === 0) {
    return (
      <main className="mx-auto w-full max-w-[784px] px-4 pb-8 pt-10 md:px-8 md:pt-[72px]">
        <div className="hidden justify-end md:flex">
          <DatePill>Data {asOf}</DatePill>
        </div>
        <div className="text-center md:mt-8">
          <h1 className="text-[26px] font-bold leading-tight tracking-[-0.02em] md:text-[32px]">Tanya</h1>
          <p className="mt-1.5 text-[13px] leading-normal text-muted-foreground">Tanya soal saham, atau tempel pesan yang Anda terima.</p>
        </div>
        <div className="mt-7">{composer}</div>
        <p className="mt-2.5 text-center text-[11.5px] leading-normal text-muted-foreground">Pesan yang ditempel dibaca di peramban Anda dan tidak dikirim ke AI.</p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {EXAMPLES.map((e) => (
            <button key={e} type="button" onClick={() => setText(e)} className="inline-flex h-8 items-center rounded-md border border-border bg-muted px-3 text-[12.5px] text-foreground">
              {e}
            </button>
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-[784px] px-4 pb-8 pt-4 md:px-8 md:pt-8">
      <div className="flex justify-center md:justify-end">
        <DatePill>Data {asOf}</DatePill>
      </div>
      <div className="mt-3.5 flex flex-col gap-3.5">
        {turns.map((turn, i) => (
          <div key={i} className="flex flex-col gap-3.5">
            <UserBubble>{turn.q}</UserBubble>
            {turn.kind === "tip" && bundle && (
              <TipResult
                turn={turn}
                bundle={bundle}
                onConfirm={(code) => setTurns((prev) => prev.map((t, j) => (j === i && t.kind === "tip" ? { ...t, confirmed: [...t.confirmed, code] } : t)))}
              />
            )}
            {turn.kind === "ask" && turn.state === "loading" && <p className="text-sm text-muted-foreground">Memproses...</p>}
            {(turn.kind === "unavailable" || (turn.kind === "ask" && turn.state === "error")) && <UnavailableCard />}
            {turn.kind === "ask" && turn.state === "done" && <AnswerView data={turn.data} limitNote={turn.limitNote} />}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="mt-5">{composer}</div>
    </main>
  );
}

function DatePill({ children }: { children: React.ReactNode }) {
  return <span className="whitespace-nowrap rounded-lg border border-border px-2.5 py-[3px] text-[11.5px] text-muted-foreground">{children}</span>;
}

/** The deterministic reading of a pasted message: stock cards, claim rows, one muted line. */
function TipResult({ turn, bundle, onConfirm }: { turn: Extract<Turn, { kind: "tip" }>; bundle: TipBundle; onConfirm: (code: string) => void }) {
  const view = useMemo(() => buildTipView(turn.q, turn.reading, bundle, turn.unknown, turn.confirmed), [turn, bundle]);
  return (
    <>
      {view.notices.map((n) => (
        <TipNoticeView key={n.kind} notice={n} />
      ))}
      {view.stocks.map((s) => (
        <StockCardView key={s.code} card={{ code: s.code, name: s.short, price: s.price, change: s.change, negative: s.negative, situations: s.situations }} />
      ))}
      {view.ambiguous.map((a) => (
        <ConfirmRow key={a.code} prompt={a.prompt} code={a.code} onConfirm={() => onConfirm(a.code)} />
      ))}
      {view.claims.length > 0 && (
        <div className="border-t border-border">
          {view.claims.map((row) => (
            <ClaimRow key={row.key} row={row} />
          ))}
        </div>
      )}
      <p className="text-xs leading-normal text-muted-foreground">
        {view.untested.length > 0 && <>Tidak ada uji untuk {view.untested.map((u) => `“${u}”`).join(", ")}. </>}
        {DATA_ONLY_LINE}
      </p>
    </>
  );
}

const PROSE_ONLY = new Set<AskResponse["bucket"]>(["advice_seeking", "unanswerable", "no_data", "ambiguous"]);

function findingRow(f: FindingRow): ClaimRowView {
  return { key: f.belief, title: f.title_short_id ?? f.belief_id, line: f.result_short_id ?? f.label_id, verdict: f.verdict, href: `/temuan/${beliefSlug(f.belief)}` };
}

function AnswerView({ data, limitNote }: { data: AskResponse; limitNote: boolean }) {
  const asProse = data.source === "gemini" || PROSE_ONLY.has(data.bucket) || (data.facts.length === 0 && data.findings.length === 0);
  const limit = data.quota?.limit ?? 3;
  return (
    <>
      {asProse ? (
        <div>
          <p className="text-sm leading-[1.55]">{data.prose}</p>
          <div className="mt-2 flex flex-wrap gap-x-4">
            {data.stockCode && (
              <Link href={`/saham/${data.stockCode}`} className="inline-flex min-h-11 items-center text-[13px] font-semibold text-[var(--viz-accent)]">
                Halaman {data.stockCode} &rarr;
              </Link>
            )}
            {data.links.map((l) => (
              <Link key={l.href} href={l.href} className="inline-flex min-h-11 items-center text-[13px] font-semibold text-[var(--viz-accent)]">
                {l.label} &rarr;
              </Link>
            ))}
          </div>
          <p className="text-[11.5px] text-muted-foreground">{data.source === "gemini" ? "Dirangkai dengan AI (Gemini), hanya dari fakta di halaman saham." : DATA_ONLY_LINE}</p>
        </div>
      ) : (
        <>
          {data.card && <StockCardView card={data.card} />}
          {data.findings.length > 0 && (
            <div className="border-t border-border">
              {data.findings.map((f) => (
                <ClaimRow key={f.belief} row={findingRow(f)} />
              ))}
            </div>
          )}
          {data.card && data.bucket === "untested_data" && data.card.rows.length > 0 ? (
            <div className="border-t border-border">
              {data.card.rows.map((r) => (
                <div key={r.label} className="flex min-h-10 items-center gap-2.5 border-b border-border py-2">
                  <span className="w-24 shrink-0 text-[13px] text-muted-foreground">{r.label}</span>
                  <span className="flex-1 text-[13.5px]">{r.value}</span>
                </div>
              ))}
            </div>
          ) : (
            data.facts.length > 0 && (
              <ul className="border-t border-border">
                {data.facts.map((fact) => (
                  <li key={fact} className="border-b border-border py-2.5 text-[13.5px] leading-normal">
                    {fact}
                  </li>
                ))}
              </ul>
            )
          )}
          {data.links.length > 0 && (
            <div className="flex flex-wrap gap-x-4">
              {data.links.map((l) => (
                <Link key={l.href} href={l.href} className="inline-flex min-h-11 items-center text-[13px] font-semibold text-[var(--viz-accent)]">
                  {l.label} &rarr;
                </Link>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground">{DATA_ONLY_LINE}</p>
        </>
      )}
      {limitNote && <LimitNote>Jawaban AI hari ini habis ({limit} per hari). Pertanyaan tetap dijawab dari data kami, tanpa AI. AI kembali besok.</LimitNote>}
      {data.notice === "unavailable" && <UnavailableCard />}
    </>
  );
}
