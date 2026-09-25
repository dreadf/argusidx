import type { LucideIcon } from "lucide-react";
import { Coins, Droplets, Mountain, Pause, RotateCcw, Rocket, Scale, TrendingDown, Wallet } from "lucide-react";
import { getBaseRatesData } from "@/lib/base-rates-data";
import { getBeatGoldData } from "@/lib/beat-gold-data";
import { getFlagsData } from "@/lib/flags-data";
import { formatDateId, idNum, signedPct } from "@/lib/format";
import { getIpoBoardsData } from "@/lib/ipo-boards-data";

/**
 * The nine "situations": the circumstance a user is actually in ("saham
 * saya turun banyak"), answered with a frequency: "what usually happens".
 * Distinct from /temuan, which asks "is this belief true".
 *
 * This module owns the list, the one-line summaries (natural frequencies,
 * "88 dari 100", not bare percentages: docs/PRODUCT.md §8 rule 1), the
 * limits and the related links. The charts themselves are composed per
 * slug in app/situasi/[slug]/page.tsx from the same data loaders.
 *
 * Numbers with no data/app source (H4's terciles, H1's volatility by
 * float tercile) are pinned constants below, each with the command that
 * reproduces it, and each checked against EXPERIMENT.md on 2026-09-20.
 */

/** H4 holdout (pipeline.hypotheses.h4_payout_dividend_cuts): share of companies cutting the dividend next year, by payout tercile. */
export const H4_CUT_RATES = { lowest: 13.9, middle: 39.4, highest: 65.6, n: 540 };
/** H1 stress test (pipeline.hypotheses.h1_robustness, Test 3 terciles): median 1y volatility (%) by free-float tercile, thinnest first. */
export const H1_VOL_TERCILES = { thin: 52, middle: 69, wide: 69, n: 913 };

/** H11 (pipeline.hypotheses.h11_suspension_underperformance), share of suspended stocks that trailed the index over the next 90 days: holdout 2026 vs explore 2025, holdout event count. */
export const H11_UNDERPERFORM = { holdout: 66, explore: 57, n: 83 };

export type SituationGroup = "Harga & penurunan" | "Perusahaan & IPO" | "Perbandingan";

export interface SituationMeta {
  slug: string;
  title: string;
  group: SituationGroup;
  icon: LucideIcon;
  /** One short line, natural frequency. */
  line: string;
  /** The same result in two or three plain sentences with its numbers: what the Ask layer retrieves. */
  explain: string;
  asOf: string;
  /** True when the result rests on research price history, not Sectors data (docs/PRODUCT.md §7.3): shows the disclosure note. */
  researchPrices: boolean;
  limits: string[];
  related: { label: string; href: string }[];
}

export async function getSituations(): Promise<SituationMeta[]> {
  const [base, ipo, flags, gold] = await Promise.all([getBaseRatesData(), getIpoBoardsData(), getFlagsData(), getBeatGoldData()]);
  const rec = base.recovery_after_fall;
  const lmt = base.loss_maker_turnaround;
  const acc365 = ipo.holdout.horizons["365d"].by_board["Acceleration"]?.negative_rate_pct ?? 0;
  const asOfResearch = formatDateId(base.as_of);

  return [
    {
      slug: "turun-banyak",
      researchPrices: true,
      title: "Saham saya turun banyak",
      group: "Harga & penurunan",
      icon: TrendingDown,
      line: `Penurunan terdalam setahun: biasanya ${signedPct(base.typical_drawdown.overall.median_pct)}`,
      explain: `Dari ${idNum(base.typical_drawdown.overall.n, 0)} saham IDX, penurunan terdalam dalam satu tahun biasanya ${signedPct(base.typical_drawdown.overall.median_pct)} (nilai tengah). Seperempat saham turun lebih dalam dari ${signedPct(base.typical_drawdown.overall.p25_pct)}. Saham kecil biasanya ${signedPct(base.typical_drawdown.by_size_tercile.smallest.median_pct)}, saham besar ${signedPct(base.typical_drawdown.by_size_tercile.largest.median_pct)}.`,
      asOf: asOfResearch,
      limits: [`Riwayat harga riset per ${asOfResearch}, bukan data langsung.`, "Kecil, menengah, besar: sepertiga saham menurut nilai pasar."],
      related: [
        { label: "Jelajah: peringkat jauh dari puncak", href: "/jelajah" },
        { label: "Situasi: ingin beli saat harga turun", href: "/situasi/beli-saat-turun" },
      ],
    },
    {
      slug: "beli-saat-turun",
      researchPrices: true,
      title: "Ingin beli saat harga turun",
      group: "Harga & penurunan",
      icon: RotateCcw,
      line: `${Math.round(rec.still_below_peak.pct ?? 0)} dari 100 belum pulih setahun kemudian`,
      explain: `Dari ${idNum(rec.n_events, 0)} kejadian saham IDX jatuh 30% atau lebih, ${idNum(rec.still_below_peak.n, 0)} (${idNum(rec.still_below_peak.pct ?? 0)}%) masih di bawah puncak lamanya setahun kemudian dan ${idNum(rec.recovered.n, 0)} (${idNum(rec.recovered.pct ?? 0)}%) sudah kembali. Yang belum pulih, nilai tengah jaraknya ke puncak lama masih ${signedPct(rec.still_down_median_gap_pct ?? 0)}.`,
      asOf: asOfResearch,
      limits: ["Pulih berarti kembali ke puncak lama, bukan sekadar naik dari dasar.", `Riwayat harga riset per ${asOfResearch}, bukan data langsung.`],
      related: [
        { label: "Jelajah: peringkat jauh dari puncak", href: "/jelajah" },
        { label: "Temuan: apakah oversold berarti memantul?", href: "/temuan?hasil=tidak-terbukti" },
      ],
    },
    {
      slug: "dekat-puncak-laba-turun",
      researchPrices: false,
      title: "Harga dekat puncak, laba menurun",
      group: "Harga & penurunan",
      icon: Mountain,
      line: `${flags.near_ath_earnings_decline.flagged_count} dari ${flags.near_ath_earnings_decline.evaluable_count} perusahaan sekarang`,
      explain: `${flags.near_ath_earnings_decline.flagged_count} dari ${flags.near_ath_earnings_decline.evaluable_count} perusahaan sekarang berharga dalam 10% dari tertinggi sepanjang masa, sementara laba tahunan 2025 lebih rendah dari 2024. Ini fakta dari laporan perusahaan, bukan penilaian.`,
      asOf: formatDateId(flags.as_of),
      limits: ["Laba bersih tahunan 2024 dan 2025.", "Sebagian adalah rugi yang makin dalam, bukan laba yang menyusut."],
      related: [
        { label: "Jelajah: daftar lengkap tanda ini", href: "/jelajah/tanda?jenis=puncak-laba" },
        { label: "Situasi: perusahaan sedang rugi", href: "/situasi/perusahaan-rugi" },
      ],
    },
    {
      slug: "pernah-disuspensi",
      researchPrices: true,
      title: "Saham pernah disuspensi",
      group: "Harga & penurunan",
      icon: Pause,
      line: "34 dari 100 perusahaan pernah disuspensi",
      explain: `34 dari 100 perusahaan IDX pernah disuspensi (perdagangannya dihentikan sementara oleh bursa). Setelah suspensi karena lonjakan harga, ${H11_UNDERPERFORM.holdout} dari 100 saham kalah dari indeks dalam 90 hari berikutnya pada uji akhir 2026 (${H11_UNDERPERFORM.n} kejadian), dan ${H11_UNDERPERFORM.explore} dari 100 pada data awal 2025.`,
      asOf: "13/09/2026",
      limits: ["Hanya data uji akhir 2026 yang ditampilkan; data awal 2025 lebih seimbang.", "Hasil rata-rata tidak signifikan secara statistik.", "Kalah dari indeks tidak berarti harga turun."],
      related: [{ label: "Temuan: suspensi karena lonjakan akan terus naik?", href: "/temuan?hasil=tidak-konsisten" }],
    },
    {
      slug: "perusahaan-rugi",
      researchPrices: false,
      title: "Perusahaan sedang rugi",
      group: "Perusahaan & IPO",
      icon: Wallet,
      line: `Hanya 1 dari 4 untung lagi tahun depan (${idNum(lmt.pct ?? 0)}%)`,
      explain: `Dari ${idNum(lmt.n, 0)} kejadian perusahaan IDX rugi dalam setahun (2021 sampai 2025), ${idNum(lmt.turned_around, 0)} (${idNum(lmt.pct ?? 0)}%) untung lagi di tahun berikutnya. Per tahun angkanya berkisar ${idNum(Math.min(...lmt.by_year.map((y) => y.pct ?? 0)))}% sampai ${idNum(Math.max(...lmt.by_year.map((y) => y.pct ?? 0)))}%.`,
      asOf: asOfResearch,
      limits: ["Untung lagi: laba bersih positif tahun berikutnya, sekecil apa pun.", "Satu perusahaan bisa dihitung lebih dari sekali."],
      related: [
        { label: "Situasi: ingin beli saat harga turun", href: "/situasi/beli-saat-turun" },
        { label: "Jelajah: tanda harga dekat tertinggi, laba turun", href: "/jelajah/tanda?jenis=puncak-laba" },
      ],
    },
    {
      slug: "ikut-ipo",
      researchPrices: true,
      title: "Ingin ikut IPO",
      group: "Perusahaan & IPO",
      icon: Rocket,
      line: `Papan Akselerasi: sekitar ${Math.round(acc365 / 10)} dari 10 turun`,
      explain: `Setahun (365 hari) setelah listing, ${idNum(acc365, 0)}% IPO di Papan Akselerasi harganya di bawah penutupan hari pertama, dibanding ${idNum(ipo.holdout.horizons["365d"].by_board["Main"]?.negative_rate_pct ?? 0, 0)}% di Papan Utama. Kelompoknya kecil (${ipo.holdout.horizons["365d"].by_board["Acceleration"]?.n ?? 0} dan ${ipo.holdout.horizons["365d"].by_board["Main"]?.n ?? 0} perusahaan), dan uji statistik formalnya tidak lolos.`,
      asOf: formatDateId(ipo.as_of),
      limits: [
        "Harga listing: penutupan hari pertama, bukan harga penawaran IPO.",
        "Papan yang dipakai adalah papan saat ini, bukan saat IPO.",
        `Riwayat harga riset per ${asOfResearch}.`,
      ],
      related: [
        { label: "Temuan: cara kami menguji", href: "/temuan/cara-kami-menguji" },
        { label: "Situasi: perusahaan sedang rugi", href: "/situasi/perusahaan-rugi" },
      ],
    },
    {
      slug: "dividen-besar",
      researchPrices: false,
      title: "Dividen besar dibanding laba",
      group: "Perusahaan & IPO",
      icon: Coins,
      line: `Dipotong tahun depan: ${Math.round(H4_CUT_RATES.lowest)} sampai ${Math.round(H4_CUT_RATES.highest)} dari 100`,
      explain: `Dari perusahaan dengan rasio dividen terhadap laba paling rendah, ${Math.round(H4_CUT_RATES.lowest)} dari 100 memotong dividen tahun berikutnya. Untuk yang paling tinggi, ${Math.round(H4_CUT_RATES.highest)} dari 100 (${H4_CUT_RATES.n} pengamatan perusahaan-tahun). Sekarang ${flags.payout_above_earnings.flagged_count} dari ${flags.payout_above_earnings.evaluable_count} pembayar dividen membayar lebih dari labanya.`,
      asOf: formatDateId(flags.as_of),
      limits: ["Sebagian efek mekanis: laba turun membuat rasio dividen naik.", "Satu perusahaan bisa muncul di dua tahun pengamatan.", `Sekarang ${flags.payout_above_earnings.flagged_count} dari ${flags.payout_above_earnings.evaluable_count} pembayar dividen membayar lebih dari labanya.`],
      related: [
        { label: "Temuan: payout tinggi memprediksi pemotongan", href: "/temuan?hasil=terbukti" },
        { label: "Jelajah: tanda dividen melebihi laba", href: "/jelajah/tanda" },
      ],
    },
    {
      slug: "float-tipis",
      researchPrices: true,
      title: "Free float-nya tipis",
      group: "Perusahaan & IPO",
      icon: Droplets,
      line: "Kebalikan dugaan: float besar lebih bergejolak",
      explain: `Nilai tengah volatilitas setahun (${H1_VOL_TERCILES.n} saham): free float tipis ${H1_VOL_TERCILES.thin}%, menengah ${H1_VOL_TERCILES.middle}%, lebar ${H1_VOL_TERCILES.wide}%. Dugaan umum bahwa float tipis lebih liar tidak terbukti: yang lebar justru lebih bergejolak. Diukur bersamaan, bukan prediksi dan bukan sebab.`,
      asOf: formatDateId(flags.as_of),
      limits: ["Diukur bersamaan, bukan prediksi dan bukan sebab.", "Teramati 2024-2026, tidak di 2022-2023."],
      related: [
        { label: "Temuan: free float kecil membuat harga bergejolak?", href: "/temuan?hasil=tidak-terbukti" },
        { label: "Jelajah: free float terendah", href: "/jelajah?urut=float-terendah" },
      ],
    },
    {
      slug: "vs-emas-deposito",
      researchPrices: true,
      title: "Lebih baik dari emas atau deposito?",
      group: "Perbandingan",
      icon: Scale,
      line: `Hanya ${Math.round(gold.summary.beat_gold.pct ?? 0)} dari 100 saham mengalahkan emas`,
      explain: `Dari ${idNum(gold.summary.n, 0)} saham dengan riwayat harga lima tahun, ${idNum(gold.summary.beat_gold.pct ?? 0)}% mengalahkan emas, ${idNum(gold.summary.beat_deposit.pct ?? 0)}% mengalahkan deposito, dan ${idNum(gold.summary.beat_index.pct ?? 0)}% mengalahkan IHSG.`,
      asOf: formatDateId(gold.summary.research_date),
      limits: [`Riwayat harga riset per ${formatDateId(gold.summary.research_date)}, bukan data langsung.`, "Harga emas dari sumber riset, tidak ada di data Sectors."],
      related: [{ label: "Halaman saham: lima tahun terakhir", href: "/saham/BBCA" }, { label: "Temuan: cara kami menguji", href: "/temuan/cara-kami-menguji" }],
    },
  ];
}

export async function getSituation(slug: string): Promise<SituationMeta | null> {
  return (await getSituations()).find((s) => s.slug === slug) ?? null;
}
