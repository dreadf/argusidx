"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy, Share2 } from "lucide-react";

/**
 * Small "Bagikan" button under an ArgusIDX reply. On a phone it opens the
 * system share sheet; elsewhere (or when that is unavailable) a small panel
 * shows the link preview and a copy button. The link holds only stock codes
 * and claim ids, never the message the user pasted.
 */
export function ShareButton({ path, preview, title }: { path: string; preview: string; title: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLInputElement>(null);
  const url = typeof window === "undefined" ? path : new URL(path, window.location.origin).toString();

  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  async function onShare() {
    const touch = typeof window.matchMedia === "function" && window.matchMedia("(pointer: coarse)").matches;
    if (touch && typeof navigator.share === "function") {
      try {
        await navigator.share({ title, text: `${title}. Bukan saran investasi.`, url });
        return;
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
      }
    }
    setOpen((o) => !o);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      field.current?.select();
    }
  }

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        onClick={() => void onShare()}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-[12.5px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <Share2 className="size-[15px]" strokeWidth={1.8} />
        Bagikan
      </button>
      {open && (
        <div role="dialog" aria-label="Bagikan hasil periksa" className="absolute bottom-full left-0 z-20 mb-2 w-[340px] max-w-[calc(100vw-3rem)] rounded-2xl border border-foreground/15 bg-card p-3.5 shadow-[0_12px_32px_rgba(0,0,0,0.45)] md:bottom-auto md:top-full md:mb-0 md:mt-2">
          <div className="mb-2 text-sm font-bold">Bagikan hasil periksa</div>
          {/* eslint-disable-next-line @next/next/no-img-element -- a generated card, not a static asset */}
          <img src={preview} alt="Pratinjau tautan" width={1200} height={630} className="aspect-[1200/630] w-full rounded-lg border border-border bg-muted" />
          <p className="mb-2.5 mt-1.5 text-[11.5px] leading-snug text-muted-foreground">Begini tampilan tautan di grup chat. Isi pesan Anda tidak ikut.</p>
          <div className="flex items-center gap-2 rounded-[10px] border border-foreground/15 bg-background py-1 pl-3 pr-1">
            <input ref={field} readOnly value={url} onFocus={(e) => e.currentTarget.select()} aria-label="Tautan hasil periksa" className="min-w-0 flex-1 bg-transparent text-xs text-foreground outline-none" />
            <button
              type="button"
              onClick={() => void copy()}
              className={`inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border px-2.5 text-[12.5px] font-semibold transition-colors ${
                copied ? "border-[var(--viz-diverging-pos)] bg-[var(--viz-diverging-pos)]/15 text-[var(--viz-diverging-pos)]" : "border-foreground/15 bg-[var(--viz-raised)] text-foreground hover:border-[var(--viz-accent)]"
              }`}
            >
              {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              {copied ? "Disalin" : "Salin"}
            </button>
          </div>
          <span className="sr-only" aria-live="polite">
            {copied ? "Tautan disalin" : ""}
          </span>
        </div>
      )}
    </div>
  );
}
