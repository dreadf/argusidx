"use client";

import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";
import { X } from "lucide-react";
import { EvidenceRows } from "@/components/saham/evidence";
import { PURPOSES, type Answer, type Purpose } from "@/lib/purposes";

/**
 * "Kenapa Anda membuka ASII?" chips and the answer card they open (boards
 * Baru4-Saham-ASII-Turun/-Murah/-Dividen/-Tip, JARR-Naik). The choice lives
 * in the URL hash (#alasan-turun) so the chips in the header and the card
 * below it share it, a link can open a stock at one answer, and the page
 * itself stays static.
 */

const PREFIX = "#alasan-";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

function readHash(): Purpose | null {
  const h = window.location.hash;
  if (!h.startsWith(PREFIX)) return null;
  const key = h.slice(PREFIX.length);
  return PURPOSES.some((p) => p.key === key) ? (key as Purpose) : null;
}

function usePurpose(): Purpose | null {
  return useSyncExternalStore(subscribe, readHash, () => null);
}

function setPurpose(next: Purpose | null) {
  const url = `${window.location.pathname}${window.location.search}${next ? PREFIX + next : ""}`;
  window.history.replaceState(null, "", url);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function PurposeChips({ code }: { code: string }) {
  const active = usePurpose();
  return (
    <div className="mt-4 border-t border-border pt-4">
      <div className="mb-2.5">
        <div className="text-[14.5px] font-bold leading-snug">Kenapa Anda membuka {code}?</div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">Pilih untuk melihat jawabannya dulu.</div>
      </div>
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0">
        {PURPOSES.map((p) => {
          const on = p.key === active;
          return (
            <button
              key={p.key}
              type="button"
              aria-pressed={on}
              onClick={() => setPurpose(on ? null : p.key)}
              className={`inline-flex h-[34px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border px-3 text-[13px] font-semibold ${
                on ? "border-[var(--viz-accent)] bg-accent text-[var(--viz-accent)]" : "border-border bg-[var(--viz-raised)] text-foreground"
              }`}
            >
              {p.label}
              {on && <X className="size-3.5" strokeWidth={2} />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function PasteBox({ code }: { code: string }) {
  const router = useRouter();
  const [text, setText] = useState("");
  return (
    <form
      className="mt-3.5 flex flex-col gap-2 rounded-[10px] border border-border p-3 sm:flex-row sm:items-end"
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim()) router.push(`/tanya?kode=${code}&q=${encodeURIComponent(text.trim())}`);
      }}
    >
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={2}
        placeholder={`Tempel pesan tentang ${code} dari grup atau teman...`}
        aria-label={`Pesan tentang ${code}`}
        className="min-h-11 flex-1 resize-none bg-transparent text-[13.5px] leading-normal outline-none placeholder:text-muted-foreground"
      />
      <button type="submit" disabled={!text.trim()} className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg bg-primary px-3.5 text-[13.5px] font-semibold text-primary-foreground disabled:opacity-50">
        Periksa
      </button>
    </form>
  );
}

export function PurposeAnswer({ code, answers }: { code: string; answers: Record<Purpose, Answer> }) {
  const active = usePurpose();
  if (!active) return null;
  const a = answers[active];
  const label = PURPOSES.find((p) => p.key === active)!.label;
  return (
    <section className="mt-5 rounded-[20px] border border-[var(--viz-accent)] bg-card p-4 md:p-5" aria-live="polite">
      <div className="flex items-start justify-between gap-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--viz-accent)]">Jawaban untuk: {label.toLowerCase()}</div>
        <button type="button" onClick={() => setPurpose(null)} aria-label="Tutup jawaban" className="-mr-1.5 -mt-1.5 inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:text-foreground">
          <X className="size-4" />
        </button>
      </div>
      <p className="mt-1 text-[17px] font-semibold leading-[1.45]">{a.lead}</p>
      {a.body && <p className="mt-2 text-sm leading-[1.55]">{a.body}</p>}
      {a.paste && <PasteBox code={code} />}
      <div className="mb-0.5 mt-[18px] text-sm font-semibold">Apa kata data untuk {code}</div>
      <EvidenceRows items={a.evidence} />
      {a.check.length > 0 && (
        <>
          <div className="mt-4 text-sm font-semibold">Yang bisa Anda periksa sendiri tentang {code}</div>
          <ul className="mt-1 list-disc pl-[18px] text-[13.5px] leading-normal">
            {a.check.map((c) => (
              <li key={c} className="mt-1.5">
                {c}
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="mt-3 text-xs text-muted-foreground">Ini informasi, bukan saran beli, jual, atau tahan. Rincian tiap bagian ada di bawah.</p>
    </section>
  );
}
