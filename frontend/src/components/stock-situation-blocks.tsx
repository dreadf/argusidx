import Link from "next/link";
import type { ReactNode } from "react";
import { BarChart3, ChartNoAxesColumnIncreasing, Circle, Coins, Droplets, Mountain, Pause, Rocket, TrendingDown, TrendingUp, Wallet, type LucideIcon } from "lucide-react";
import { PairBars, Note } from "@/components/situation-ui";
import type { BaseRatesData } from "@/lib/base-rates-data";
import { formatDateId, formatPrice, idNum } from "@/lib/format";
import type { IpoBoardsData } from "@/lib/ipo-boards-data";
import { H1_VOL_TERCILES, H11_UNDERPERFORM, H4_CUT_RATES } from "@/lib/situations";
import { rpShort, SLUG_BY_KIND, type SituationKey, type StockSituationEntry } from "@/lib/stock-situations";
import type { StockPageData } from "@/lib/stock-data";

/**
 * "Situasi saham ini", "Situasi lain yang kami periksa" and the empty state
 * of the stock page. Boards: Saham-Alasan-Mobile (FILM, three situations),
 * Saham-PACK-Mobile (grouped), Saham-ASII-Mobile (none). Each situation
 * stands on its own: no combined value across them.
 */

export type StockKind = SituationKey | "payout_above_earnings" | "near_ath_earnings_decline" | "thin_float";

type Group = "Harga & penurunan" | "Perusahaan & IPO";

interface KindMeta {
  group: Group;
  icon: LucideIcon;
  /** Title of an active card. */
  title: string;
  /** Title in the "tidak sedang di" list. */
  short: string;
  href: string;
}

const META: Record<StockKind, KindMeta> = {
  fall: { group: "Harga & penurunan", icon: TrendingDown, title: "Jatuh jauh dari puncak", short: "Jatuh 30% dari puncak", href: `/situasi/${SLUG_BY_KIND.fall}` },
  recent_spike: { group: "Harga & penurunan", icon: TrendingUp, title: "Harga baru melonjak", short: "Harga baru melonjak", href: `/situasi/${SLUG_BY_KIND.recent_spike}` },
  recent_price_suspension: { group: "Harga & penurunan", icon: Pause, title: "Suspensi karena lonjakan", short: "Suspensi lonjakan, 90 hari", href: `/situasi/${SLUG_BY_KIND.recent_price_suspension}` },
  loss_year: { group: "Perusahaan & IPO", icon: Wallet, title: "Perusahaan rugi setahun", short: "Perusahaan rugi setahun", href: `/situasi/${SLUG_BY_KIND.loss_year}` },
  earnings_two_year_decline: { group: "Perusahaan & IPO", icon: BarChart3, title: "Laba turun dua tahun", short: "Laba turun dua tahun berturut-turut", href: `/situasi/${SLUG_BY_KIND.earnings_two_year_decline}` },
  recent_ipo: { group: "Perusahaan & IPO", icon: Rocket, title: "IPO setahun terakhir", short: "IPO setahun terakhir", href: `/situasi/${SLUG_BY_KIND.recent_ipo}` },
  earnings_more_than_doubled: { group: "Perusahaan & IPO", icon: ChartNoAxesColumnIncreasing, title: "Laba lebih dari dua kali lipat", short: "Laba lebih dari dua kali lipat", href: `/situasi/${SLUG_BY_KIND.earnings_more_than_doubled}` },
  payout_above_earnings: { group: "Perusahaan & IPO", icon: Coins, title: "Dividen melebihi laba", short: "Dividen melebihi laba", href: "/situasi/dividen-besar" },
  near_ath_earnings_decline: { group: "Perusahaan & IPO", icon: Mountain, title: "Dekat puncak, laba turun", short: "Dekat puncak, laba turun", href: "/situasi/dekat-puncak-laba-turun" },
  thin_float: { group: "Perusahaan & IPO", icon: Droplets, title: "Free float tipis", short: "Free float tipis", href: "/situasi/float-tipis" },
};

/** Order used everywhere on the stock page. */
export const KIND_ORDER: StockKind[] = ["fall", "recent_price_suspension", "recent_spike", "loss_year", "earnings_two_year_decline", "recent_ipo", "earnings_more_than_doubled", "payout_above_earnings", "near_ath_earnings_decline", "thin_float"];

const GROUPS: Group[] = ["Harga & penurunan", "Perusahaan & IPO"];
const BOARD_ID: Record<string, string> = { Acceleration: "Akselerasi", Main: "Utama", Development: "Pengembangan", Watchlist: "Pemantauan Khusus" };

/** "Rp 96,6 miliar" / "Rp 19,1 triliun" / "rugi" for the one-line earnings history. */
function rpLong(v: number): string {
  if (v < 0) return "rugi";
  const abs = Math.abs(v);
  if (abs >= 1e12) return `Rp ${idNum(v / 1e12, 1)} triliun`;
  return `Rp ${idNum(v / 1e9, abs >= 1e11 ? 0 : 1)} miliar`;
}

const yearOf = (iso: string) => iso.slice(0, 4);

export interface Ctx {
  code: string;
  entry: StockSituationEntry | undefined;
  data: StockPageData;
  base: BaseRatesData;
  ipo: IpoBoardsData;
}

/** Which of the ten kinds this stock is in right now. */
export function activeKinds(ctx: Ctx): StockKind[] {
  const { entry, data } = ctx;
  const active: StockKind[] = [];
  for (const k of KIND_ORDER) {
    if (k === "payout_above_earnings" || k === "near_ath_earnings_decline") {
      if (data.flags.some((f) => f.key === k)) active.push(k);
    } else if (k === "thin_float") {
      if (data.h1_finding?.free_float_tercile === "low") active.push(k);
    } else if (entry?.[k]) active.push(k);
  }
  return active;
}

interface CardContent {
  sub: string;
  pair?: { a: { n: number; label: string }; b: { n: number; label: string }; unit: string };
  sentence?: ReactNode;
  n?: string;
  note: ReactNode;
  chip?: string;
}

function contentFor(kind: StockKind, ctx: Ctx): CardContent {
  const { code, entry, base, ipo, data } = ctx;
  switch (kind) {
    case "fall": {
      const f = entry!.fall!;
      const rec = base.recovery_after_fall;
      const below = Math.round(rec.still_below_peak.pct ?? 0);
      const depth = Math.abs(f.pct_from_peak);
      return {
        sub: `Puncak ${formatPrice(f.peak_price)} (${formatDateId(f.peak_date)}), turun 30% pada ${formatDateId(f.trigger_date)}`,
        pair: { a: { n: below, label: "Belum pulih" }, b: { n: 100 - below, label: "Sudah pulih" }, unit: "dari 100 saham" },
        sentence: (
          <>
            Dari 100 saham yang jatuh 30%, <b>{below}</b> belum kembali ke puncaknya setahun kemudian.
          </>
        ),
        n: `Dari ${idNum(rec.n_events, 0)} kejadian.`,
        note: depth >= 40 ? `${code} kini jauh lebih dalam dari 30%. Angka ini mencampur semua kedalaman.` : `${code} kini ${idNum(depth, 0)}% di bawah puncaknya. Angka ini mencampur semua kedalaman.`,
        chip: "Riwayat harga riset",
      };
    }
    case "recent_spike": {
      const s = entry!.recent_spike!;
      const sp = base.recent_spike;
      const below = Math.round(sp.pooled.share_below_event_close * 100);
      return {
        sub: `Naik ${Math.round(s.jump_pct)}% dalam ${s.lookback_trading_days} hari bursa, sampai ${formatDateId(s.event_date)}`,
        pair: { a: { n: below, label: "Lebih rendah" }, b: { n: 100 - below, label: "Sama/lebih tinggi" }, unit: "dari 100 saham" },
        sentence: (
          <>
            Dari 100 saham yang naik 40% atau lebih dalam 20 hari bursa, <b>{below}</b> berakhir lebih rendah 60 hari bursa kemudian.
          </>
        ),
        n: `Dari ${idNum(sp.pooled.n_events, 0)} kejadian.`,
        note: `${code} baru ${s.trading_days_since} hari bursa sejak lonjakan, dan kini ${idNum(Math.abs(s.pct_since_event), 0)}% ${s.pct_since_event >= 0 ? "di atas" : "di bawah"} harga hari itu. Angka ini mengukur 60 hari penuh.`,
        chip: "Riwayat harga riset",
      };
    }
    case "recent_price_suspension": {
      const s = entry!.recent_price_suspension!;
      return {
        sub: `${s.days_ago} hari lalu, ${formatDateId(s.date)}`,
        pair: { a: { n: H11_UNDERPERFORM.holdout, label: "Kalah dari indeks" }, b: { n: 100 - H11_UNDERPERFORM.holdout, label: "Menang/setara" }, unit: "dari 100 saham" },
        sentence: (
          <>
            Dari 100 saham yang disuspensi karena lonjakan harga, <b>{H11_UNDERPERFORM.holdout}</b> kalah dari indeks dalam 90 hari sesudahnya.
          </>
        ),
        n: `Dari ${H11_UNDERPERFORM.n} kejadian pada uji akhir 2026.`,
        note: "Sebagian terus melonjak; hasilnya terbelah, bukan satu arah.",
      };
    }
    case "loss_year": {
      const l = entry!.loss_year!;
      const lm = base.loss_maker_turnaround;
      const up = Math.round(lm.pct ?? 0);
      return {
        sub: `Rugi bersih ${l.year} sekitar ${rpLong(-l.net_income)}`,
        pair: { a: { n: up, label: "Untung lagi" }, b: { n: 100 - up, label: "Belum untung" }, unit: "dari 100 perusahaan" },
        sentence: (
          <>
            Dari 100 perusahaan yang rugi setahun, <b>{up}</b> untung lagi di tahun berikutnya.
          </>
        ),
        n: `Dari ${idNum(lm.n, 0)} pengamatan.`,
        note: `Untung lagi berarti laba positif, sekecil apa pun. Hasil ${code} ${l.year + 1} belum diketahui.`,
      };
    }
    case "earnings_two_year_decline": {
      const d = entry!.earnings_two_year_decline!;
      const b = base.earnings_two_year_decline;
      const up = Math.round(b.pooled.rate * 100);
      const years = Object.keys(b.by_year);
      return {
        sub: `Laba bersih ${d.year - 2} ${rpLong(d.earnings[0])}, ${d.year - 1} ${rpLong(d.earnings[1])}, ${d.year} ${rpLong(d.earnings[2])}`,
        pair: { a: { n: up, label: "Naik lagi" }, b: { n: 100 - up, label: "Tidak naik" }, unit: "dari 100 perusahaan" },
        sentence: (
          <>
            Dari 100 perusahaan yang labanya turun dua tahun, <b>{up}</b> labanya naik lagi tahun berikutnya.
          </>
        ),
        n: `Dari ${idNum(b.pooled.n, 0)} pengamatan, ${years.join(" dan ")}.`,
        note: "Naik lagi tidak berarti kembali ke laba semula. Hanya dua tahun pengamatan.",
      };
    }
    case "earnings_more_than_doubled": {
      const d = entry!.earnings_more_than_doubled!;
      const b = base.earnings_more_than_doubled;
      const lower = Math.round(b.gave_part_back.rate * 100);
      const all = Math.round(b.gave_all_back.rate * 100);
      const years = Object.keys(b.by_year);
      return {
        sub: `Rp ${rpShort(d.earnings[0])} ke Rp ${rpShort(d.earnings[1])}, ${d.year - 1} ke ${d.year}`,
        pair: { a: { n: lower, label: "Turun lagi" }, b: { n: 100 - lower, label: "Naik/tetap" }, unit: "dari 100 saham" },
        sentence: (
          <>
            Dari 100 perusahaan yang labanya lebih dari dua kali lipat, <b>{lower}</b> labanya lebih rendah tahun berikutnya.
          </>
        ),
        n: `Dari ${idNum(b.gave_part_back.n, 0)} pengamatan, ${years[0]} sampai ${years[years.length - 1]}.`,
        note: `${all} dari 100 bahkan turun ke bawah tingkat sebelum lonjakan.`,
      };
    }
    case "recent_ipo": {
      const i = entry!.recent_ipo!;
      const cell = ipo.holdout.horizons["365d"].by_board[i.board];
      const testedBoard = i.board === "Acceleration" || i.board === "Main";
      const boardId = BOARD_ID[i.board] ?? i.board;
      const sub = `Listing ${formatDateId(i.listing_date)}, Papan ${boardId}, ${i.days_since} hari lalu`;
      if (!testedBoard || !cell) {
        return { sub, note: `Papan ${boardId} tidak masuk dalam uji IPO kami (hanya Papan Utama dan Akselerasi), jadi belum ada frekuensi untuk ditampilkan.` };
      }
      const down = Math.round(cell.negative_rate_pct);
      return {
        sub,
        pair: { a: { n: down, label: "Harga turun" }, b: { n: 100 - down, label: "Tidak turun" }, unit: "dari 100 IPO" },
        sentence: (
          <>
            Dari 100 IPO di Papan {boardId}, <b>{down}</b> harganya di bawah penutupan hari pertama setahun kemudian.
          </>
        ),
        n: `Dari ${cell.n} IPO, 2023 dan 2024.`,
        note: "Kelompoknya kecil dan uji statistik formalnya tidak lolos.",
        chip: "Riwayat harga riset",
      };
    }
    case "payout_above_earnings":
      return {
        sub: "Dividen yang dibayar lebih besar dari labanya",
        pair: { a: { n: Math.round(H4_CUT_RATES.highest), label: "Dipotong" }, b: { n: 100 - Math.round(H4_CUT_RATES.highest), label: "Tidak dipotong" }, unit: "dari 100 perusahaan" },
        sentence: (
          <>
            Dari 100 perusahaan dengan dividen paling besar dibanding laba, <b>{Math.round(H4_CUT_RATES.highest)}</b> memotong dividen tahun berikutnya.
          </>
        ),
        n: `Dari ${H4_CUT_RATES.n} pengamatan.`,
        note: "Sebagian efek mekanis: laba turun membuat rasio dividen naik.",
      };
    case "near_ath_earnings_decline":
      return {
        sub: "Harga dalam 10% dari tertinggi sepanjang masa, laba 2025 lebih rendah dari 2024",
        note: "Ini fakta dari laporan perusahaan dan harga, bukan penilaian. Kami belum punya frekuensi hasil ke depan untuk ditampilkan.",
      };
    default: {
      const ff = data.snapshot.free_float;
      return {
        sub: ff === null ? "Free float sempit" : `Free float ${idNum(ff * 100)}%, sepertiga tersempit`,
        sentence: (
          <>
            Nilai tengah gejolak harga setahun: free float tipis <b>{H1_VOL_TERCILES.thin}%</b>, lebar <b>{H1_VOL_TERCILES.wide}%</b>.
          </>
        ),
        n: `Dari ${H1_VOL_TERCILES.n} saham, 2024-2026.`,
        note: "Dugaan umum bahwa float tipis lebih liar tidak terbukti. Diukur bersamaan, bukan prediksi dan bukan sebab.",
      };
    }
  }
}

function SituationCard({ kind, ctx }: { kind: StockKind; ctx: Ctx }) {
  const m = META[kind];
  const c = contentFor(kind, ctx);
  const Icon = m.icon;
  return (
    <section className="rounded-[20px] border border-border bg-card p-[18px]">
      <div className="flex items-start gap-3">
        <div className="flex size-[34px] shrink-0 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
          <Icon className="size-5" strokeWidth={1.7} />
        </div>
        <div className="min-w-0">
          <div className="text-[15px] font-semibold leading-snug">{m.title}</div>
          <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{c.sub}</div>
        </div>
      </div>
      {(c.pair || c.sentence) && (
        <div className="mt-4 flex items-end gap-4">
          {c.pair && <PairBars compact a={c.pair.a} b={c.pair.b} unit={c.pair.unit} />}
          <div className="min-w-0 flex-1 pb-6">
            {c.sentence && <p className="text-sm leading-normal">{c.sentence}</p>}
            {c.n && <div className="mt-1.5 text-xs text-muted-foreground">{c.n}</div>}
          </div>
        </div>
      )}
      <div className="mt-3">
        <Note>{c.note}</Note>
      </div>
      <div className="mt-1 flex items-center justify-between gap-2">
        <Link href={m.href} className="inline-flex min-h-11 items-center text-[13.5px] font-semibold text-[var(--viz-accent)]">
          Lihat buktinya &rarr;
        </Link>
        {c.chip && <span className="inline-flex h-6 items-center rounded-full border border-border px-2.5 text-[11px] text-muted-foreground">{c.chip}</span>}
      </div>
    </section>
  );
}

/** One line for a situation the stock is NOT in. */
function absentReason(kind: StockKind, ctx: Ctx): string {
  const { entry, data } = ctx;
  switch (kind) {
    case "fall": {
      const o = entry?.older_fall;
      return o ? `turun ${idNum(Math.abs(o.pct_from_peak), 0)}% dari puncak ${yearOf(o.peak_date)}, lebih dari setahun lalu` : "tidak dalam setahun terakhir";
    }
    case "recent_price_suspension": {
      const dates = data.suspension_history?.events.map((e) => e.date) ?? [];
      return dates.length === 0 ? "belum pernah disuspensi" : `terakhir ${formatDateId(dates.reduce((a, b) => (a > b ? a : b)))}`;
    }
    case "recent_spike":
      return "tidak dalam 20 hari bursa terakhir";
    case "loss_year":
      return "tidak tercatat rugi di 2025";
    case "recent_ipo":
      return data.snapshot.listing_date ? `tidak, listing ${yearOf(data.snapshot.listing_date)}` : "tidak";
    case "payout_above_earnings":
    case "near_ath_earnings_decline":
      return "tidak ada tanda";
    case "thin_float": {
      const ff = data.snapshot.free_float;
      const t = data.h1_finding?.free_float_tercile;
      return ff === null ? "tidak tersedia" : `${idNum(ff * 100)}%, ${t === "high" ? "lebar" : t === "mid" ? "di tengah" : "belum dikelompokkan"}`;
    }
    default:
      return "tidak";
  }
}

export function StockSituations({ ctx }: { ctx: Ctx }) {
  const { code } = ctx;
  const active = activeKinds(ctx);

  if (active.length === 0) {
    // Saham-ASII-Mobile: none of the ten kinds; list them all, say we have no frequency to show.
    return (
      <div>
        <h2 className="text-xl font-bold leading-tight tracking-[-0.01em]">Situasi saham ini</h2>
        <p className="mt-1.5 text-[13px] leading-normal text-muted-foreground">Tidak ada dari {KIND_ORDER.length} jenis situasi yang sedang dialami {code} sekarang. Bukan penilaian: kami belum punya frekuensi untuk ditampilkan.</p>
        <div className="mt-4 rounded-[20px] border border-border bg-card p-[18px]">
          {GROUPS.map((g, gi) => (
            <div key={g} className={gi > 0 ? "mt-4" : ""}>
              <div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">{g}</div>
              {KIND_ORDER.filter((k) => META[k].group === g).map((k) => (
                <Link key={k} href={META[k].href} className="flex items-baseline justify-between gap-3 border-b border-border py-2.5 text-[13.5px] last:border-0">
                  <span className="flex items-center gap-2 text-foreground">
                    <Circle className="size-3 shrink-0 text-muted-foreground" strokeWidth={1.7} />
                    {META[k].short}
                  </span>
                  <span className="text-right text-xs text-muted-foreground">{absentReason(k, ctx)}</span>
                </Link>
              ))}
            </div>
          ))}
        </div>
        <div className="mt-4">
          <Note>Ini frekuensi masa lalu, bukan ramalan untuk {code}. Data ini tidak menjelaskan bisnis, manajemen, atau arah harga.</Note>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div>
        <h2 className="text-xl font-bold leading-tight tracking-[-0.01em]">Situasi saham ini</h2>
        <p className="mt-1.5 text-[13px] leading-normal text-muted-foreground">{active.length} situasi sedang dialami. Masing-masing berdiri sendiri, tanpa nilai gabungan.</p>
      </div>
      {GROUPS.map((g) => {
        const kinds = active.filter((k) => META[k].group === g);
        if (kinds.length === 0) return null;
        return (
          <div key={g} className="mt-5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-[var(--viz-accent)]">{g}</div>
            <div className="mt-2.5 flex flex-col gap-3.5">
              {kinds.map((k) => (
                <SituationCard key={k} kind={k} ctx={ctx} />
              ))}
            </div>
          </div>
        );
      })}
      <div className="mt-4">
        <Note>Ini frekuensi masa lalu, bukan ramalan untuk {code}. Data ini tidak menjelaskan bisnis, manajemen, atau arah harga.</Note>
      </div>
    </div>
  );
}

/** "Situasi lain yang kami periksa": what the stock is NOT in. Hidden when it is in none (the empty state already lists them). */
export function OtherSituations({ ctx }: { ctx: Ctx }) {
  const active = activeKinds(ctx);
  if (active.length === 0) return null;
  const inactive = KIND_ORDER.filter((k) => !active.includes(k));
  return (
    <div>
      <h3 className="text-[15px] font-semibold leading-snug">Situasi lain yang kami periksa</h3>
      <p className="mt-1 text-xs text-muted-foreground">{ctx.code} tidak sedang di:</p>
      <div className="mt-3 grid grid-cols-2 overflow-hidden rounded-2xl border border-border bg-card">
        {inactive.map((k, i) => (
          <Link key={k} href={META[k].href} className={`flex gap-2 p-3.5 ${i % 2 === 0 ? "border-r border-border" : ""} ${i < inactive.length - 2 ? "border-b border-border" : ""}`}>
            <Circle className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" strokeWidth={1.7} />
            <span className="min-w-0">
              <span className="block text-[13px] font-semibold leading-snug">{META[k].short}</span>
              <span className="mt-0.5 block text-[11.5px] leading-snug text-muted-foreground">{absentReason(k, ctx)}</span>
            </span>
          </Link>
        ))}
      </div>
      <Link href="/situasi" className="inline-flex min-h-11 items-center text-[13.5px] font-semibold text-[var(--viz-accent)]">
        Semua {KIND_ORDER.length} jenis situasi &rarr;
      </Link>
    </div>
  );
}
