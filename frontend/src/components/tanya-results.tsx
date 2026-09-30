"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { BarChart3, ChartNoAxesColumnIncreasing, ChevronRight, Info, Pause, Rocket, TrendingDown, TrendingUp, TriangleAlert, Wallet, type LucideIcon } from "lucide-react";
import type { SituationLine } from "@/lib/ask/stock-card";
import { MAX_TIP_CHARS } from "@/lib/ask/tip-reader";
import { VERDICT_CHIP, type ClaimRowView, type TipNotice } from "@/lib/ask/tip-view";
import type { Verdict } from "@/lib/findings-data";

/** Pieces of a Tanya result (boards Tanya-Tempel-Hasil, Tanya-AI-Habis, Kondisi-Kosong). */

export const DATA_ONLY_LINE = "Dijawab dari data kami, tanpa AI.";
/** Shown on a pasted-tip result, distinct from DATA_ONLY_LINE: this is never
 * about AI being unavailable, tips are always checked this way. Without a
 * distinct line here, choosing "Dengan AI" then pasting a tip reads as if
 * that choice was ignored or AI failed, when it was never in play. */
export const TIP_DATA_ONLY_LINE = "Klaim dicek langsung dari hasil uji kami, bukan ditanyakan ke AI. Jawabannya selalu begini, apa pun mode yang dipilih.";

export function UserBubble({ children }: { children: ReactNode }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[88%] whitespace-pre-line break-words rounded-xl border border-border bg-muted px-3.5 py-2.5 text-[13.5px] leading-[1.55]">{children}</div>
    </div>
  );
}

export interface CardView {
  code: string;
  name: string;
  price: string | null;
  change: string | null;
  negative: boolean;
  situations?: SituationLine[];
}

const SITUATION_ICON: Record<SituationLine["kind"], LucideIcon> = {
  fall: TrendingDown,
  older_fall: TrendingDown,
  recent_spike: TrendingUp,
  recent_price_suspension: Pause,
  loss_year: Wallet,
  earnings_two_year_decline: BarChart3,
  earnings_more_than_doubled: ChartNoAxesColumnIncreasing,
  recent_ipo: Rocket,
};

/** Stock head line (links to the stock page), with one row per situation the stock is in. */
export function StockCardView({ card }: { card: CardView }) {
  return (
    <div className="overflow-hidden rounded-[14px] border border-border bg-card">
      <Link href={`/saham/${card.code}`} className="flex items-center gap-3 px-3.5 py-3 transition-colors hover:bg-muted">
        <span className="flex size-[34px] shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[11px] font-bold text-accent-foreground">{card.code.slice(0, 2)}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-[14.5px] font-semibold leading-snug">{card.code}</span>
          <span className="block truncate text-xs text-muted-foreground">{card.name}</span>
        </span>
        {card.price && (
          <span className="text-right font-mono tabular-nums">
            <span className="block text-[13.5px]">{card.price}</span>
            {card.change && <span className={`block text-[11.5px] ${card.negative ? "text-[var(--viz-diverging-neg)]" : "text-muted-foreground"}`}>{card.change}</span>}
          </span>
        )}
        <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
      </Link>
      {card.situations?.map((s) => {
        const Icon = SITUATION_ICON[s.kind];
        return (
          <Link key={s.kind} href={s.href} className="flex items-center gap-2.5 border-t border-border px-3.5 py-[11px] transition-colors hover:bg-muted">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Icon className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[13.5px] font-semibold">{s.title}</span>
              <span className="mt-px block text-xs leading-[1.45] text-muted-foreground">{s.line}</span>
            </span>
            <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
          </Link>
        );
      })}
    </div>
  );
}

/** "Maksud Anda saham X?" with a small confirm chip. */
export function ConfirmRow({ prompt, code, onConfirm }: { prompt: string; code: string; onConfirm: () => void }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex-1 text-[12.5px] text-muted-foreground">{prompt}</span>
      <button
        type="button"
        onClick={onConfirm}
        className="inline-flex h-7 items-center rounded-md border border-[var(--viz-accent)] bg-accent px-2.5 text-xs font-semibold text-[var(--viz-accent)] transition-[filter] hover:brightness-125"
      >
        Ya, {code}
      </button>
    </div>
  );
}

const VERDICT_COLOR: Record<Verdict, string> = {
  yes: "var(--viz-status-good)",
  no: "var(--viz-diverging-neg)",
  mixed_or_inconclusive: "var(--viz-status-warning)",
};

export function VerdictChip({ verdict }: { verdict: Verdict }) {
  return (
    <span style={{ color: VERDICT_COLOR[verdict], borderColor: VERDICT_COLOR[verdict] }} className="inline-flex shrink-0 items-center whitespace-nowrap rounded-md border px-[7px] py-0.5 text-[11px] font-semibold">
      {VERDICT_CHIP[verdict]}
    </span>
  );
}

/** One tested claim: short title, verdict chip, one line, chevron to the evidence. */
export function ClaimRow({ row }: { row: ClaimRowView }) {
  return (
    <Link href={row.href} className="flex items-start gap-3 border-b border-border py-[11px] transition-colors last:border-b-0 hover:bg-muted">
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold leading-[1.4]">{row.title}</span>
        <span className="mt-0.5 block text-[12.5px] leading-[1.45] text-muted-foreground">{row.line}</span>
      </span>
      <span className="mt-px flex shrink-0 items-center gap-1.5">
        {row.verdict && <VerdictChip verdict={row.verdict} />}
        <ChevronRight className="size-[18px] text-muted-foreground" />
      </span>
    </Link>
  );
}

/** Icon + title + one or two lines, for states outside the main path (Kondisi-Kosong). */
export function NoticeCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-[14px] border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <span className="flex size-[34px] shrink-0 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
          <TriangleAlert className="size-[18px]" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[15px] font-semibold leading-snug">{title}</div>
          <p className="mt-1.5 text-[13.5px] leading-[1.55] text-muted-foreground">{children}</p>
        </div>
      </div>
    </div>
  );
}

export function UnavailableCard() {
  return <NoticeCard title="Tanya sedang tidak tersedia">Penjelasan tambahan sedang tidak dapat dimuat. Fakta dan hasil uji di halaman ini tetap sama.</NoticeCard>;
}

/** Dashed line under a data-only answer: why AI did not write it. */
export function LimitNote({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2.5 rounded-[14px] border border-dashed border-foreground/15 px-3.5 py-3 text-[12.5px] leading-normal text-muted-foreground">
      <Info className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

export function TipNoticeView({ notice }: { notice: TipNotice }) {
  if (notice.kind === "unknown-code") {
    return (
      <NoticeCard title="Kode saham tidak ditemukan">
        Kami tidak menemukan saham &ldquo;{notice.code}&rdquo; di daftar {notice.total.toLocaleString("id-ID")} perusahaan tercatat. Periksa ejaannya, atau cari dengan nama perusahaan.
        {notice.suggestions.length > 0 && (
          <span className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-xs">Mungkin maksud Anda</span>
            {notice.suggestions.map((c) => (
              <Link key={c} href={`/saham/${c}`} className="inline-flex min-h-9 items-center rounded-md border border-border bg-muted px-3.5 text-[13px] font-semibold text-foreground transition-colors hover:border-[var(--viz-accent)] hover:text-[var(--viz-accent)]">
                {c}
              </Link>
            ))}
          </span>
        )}
      </NoticeCard>
    );
  }
  if (notice.kind === "no-code") {
    return <NoticeCard title="Tidak ada kode saham di pesan ini">Kami tetap memeriksa klaimnya di bawah. Tempel lagi dengan kode saham jika ingin melihat situasi sahamnya.</NoticeCard>;
  }
  return <NoticeCard title="Pesan terlalu panjang">Kami membaca {MAX_TIP_CHARS.toLocaleString("id-ID")} karakter pertama saja. Bagian sisanya tidak diperiksa.</NoticeCard>;
}
