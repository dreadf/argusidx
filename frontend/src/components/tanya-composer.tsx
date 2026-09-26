"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowUp, Check, ChevronDown, MessageSquare, Sparkle } from "lucide-react";
import { MAX_TIP_CHARS } from "@/lib/ask/tip-reader";
import type { Quota } from "@/lib/ask/quota";

export type AskMode = "ai" | "data";

export const PLACEHOLDER = "Tempel pesan atau tanya soal saham...";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  /** What the user picked. */
  mode: AskMode;
  onMode: (mode: AskMode) => void;
  /** False when the server has no model configured; null until known. */
  aiConfigured: boolean | null;
  quota: Quota | null;
  busy: boolean;
  /** Open the menu upward (composer sits at the bottom of a conversation). */
  menuUp: boolean;
}

/** True when an AI answer can be asked for right now. */
export function aiUsable(aiConfigured: boolean | null, quota: Quota | null): boolean {
  return aiConfigured !== false && (quota === null || quota.remaining > 0);
}

/**
 * The one composer on Tanya (boards Tanya-Tempel-Kosong, Tanya-Menu): a
 * textarea, a small mode chip bottom-left that opens a two-item menu, the
 * remaining allowance and a square send button bottom-right.
 */
export function TanyaComposer({ value, onChange, onSubmit, mode, onMode, aiConfigured, quota, busy, menuUp }: Props) {
  const [open, setOpen] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const usable = aiUsable(aiConfigured, quota);
  const shown: AskMode = usable ? mode : "data";
  const over = value.length > MAX_TIP_CHARS;

  useLayoutEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const right = over ? (
    <span className="text-[11.5px] tabular-nums text-[var(--viz-status-critical)]">
      {value.length.toLocaleString("id-ID")} / {MAX_TIP_CHARS.toLocaleString("id-ID")}
    </span>
  ) : shown === "data" ? (
    <span className="text-[11.5px] text-muted-foreground">Tanpa AI</span>
  ) : quota ? (
    <span className="text-[11.5px] text-muted-foreground">
      Sisa {quota.remaining} dari {quota.limit} hari ini
    </span>
  ) : null;

  const aiHint = aiConfigured === false ? "Sedang tidak tersedia." : quota ? `Merangkai jawaban dari data kami. Sisa ${quota.remaining} dari ${quota.limit} hari ini.` : "Merangkai jawaban dari data kami.";

  return (
    <div ref={wrap} className="relative w-full">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="rounded-[14px] border border-foreground/15 bg-card py-3.5 pb-2.5 pl-3.5 pr-3"
      >
        <textarea
          ref={area}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder={PLACEHOLDER}
          aria-label="Pesan atau pertanyaan"
          rows={1}
          className="block min-h-[44px] w-full resize-none bg-transparent text-sm leading-[1.55] text-foreground outline-none placeholder:text-muted-foreground"
        />
        <div className="mt-2 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-haspopup="menu"
            aria-expanded={open}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-foreground/15 bg-muted px-2.5 text-[12.5px] font-semibold text-foreground"
          >
            {shown === "ai" ? <Sparkle className="size-3.5" /> : <MessageSquare className="size-3.5" />}
            {shown === "ai" ? "Dengan AI" : "Data saja"}
            <ChevronDown className="size-3.5 text-muted-foreground" />
          </button>
          <div className="flex items-center gap-2.5">
            {right}
            <button type="submit" disabled={busy || value.trim().length === 0} aria-label="Kirim" className="inline-flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground disabled:opacity-50">
              <ArrowUp className="size-[18px]" />
            </button>
          </div>
        </div>
      </form>

      {open && (
        <div role="menu" className={`absolute left-3 z-10 w-[310px] max-w-[calc(100%-24px)] rounded-xl border border-foreground/15 bg-card p-1.5 shadow-[0_8px_24px_rgba(0,0,0,0.4)] ${menuUp ? "bottom-[calc(100%+6px)]" : "top-[calc(100%+6px)]"}`}>
          <MenuItem
            icon={<Sparkle className="size-4 text-muted-foreground" />}
            title="Dengan AI"
            hint={aiHint}
            selected={shown === "ai"}
            disabled={!usable}
            onPick={() => {
              onMode("ai");
              setOpen(false);
            }}
          />
          <MenuItem
            icon={<MessageSquare className="size-4 text-muted-foreground" />}
            title="Data saja"
            hint="Jawaban langsung dari data, tanpa AI. Selalu tersedia."
            selected={shown === "data"}
            onPick={() => {
              onMode("data");
              setOpen(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

function MenuItem({ icon, title, hint, selected, disabled = false, onPick }: { icon: React.ReactNode; title: string; hint: string; selected: boolean; disabled?: boolean; onPick: () => void }) {
  return (
    <button type="button" role="menuitem" disabled={disabled} onClick={onPick} className={`flex w-full items-center gap-2.5 rounded-md px-3 py-2.5 text-left disabled:opacity-60 ${selected ? "bg-muted" : ""}`}>
      {icon}
      <span className="min-w-0 flex-1">
        <span className="block text-[13.5px] font-semibold text-foreground">{title}</span>
        <span className="block text-xs leading-[1.45] text-muted-foreground">{hint}</span>
      </span>
      {selected && <Check className="size-4 shrink-0 text-[var(--viz-accent)]" />}
    </button>
  );
}
