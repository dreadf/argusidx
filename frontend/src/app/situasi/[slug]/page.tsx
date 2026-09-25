import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { AxisColumns, RangeChart, TwoLineChart } from "@/components/charts/axis-charts";
import { IconDots, Key } from "@/components/charts/dots";
import { H2, Page, PageTitle, ResearchNote, TwoCol } from "@/components/kit";
import { Legend, QCard } from "@/components/qcard";
import { getBaseRatesData } from "@/lib/base-rates-data";
import { getBeatGoldData } from "@/lib/beat-gold-data";
import { getFlagsData } from "@/lib/flags-data";
import { idNum, signedPct } from "@/lib/format";
import { getIpoBoardsData } from "@/lib/ipo-boards-data";
import { getSituation, getSituations, H1_VOL_TERCILES, H11_UNDERPERFORM, H4_CUT_RATES, type SituationMeta } from "@/lib/situations";
import { getSuspensionSummary } from "@/lib/suspensions-data";

export async function generateStaticParams() {
  return (await getSituations()).map((s) => ({ slug: s.slug }));
}

/** H11 (pipeline.hypotheses.h11_suspension_underperformance), EXPERIMENT.md: price-spike suspensions in 2026 (holdout), 90 days on: 33.7% beat the index, so 66 of 100 trailed it (n=83). The 2025 explore phase was less lopsided: 43.3% beat it (57 of 100 trailed). */

const SUSPENSION_LABELS: Record<string, [string, string]> = {
  "Pergerakan harga tidak wajar": ["Harga", "tak wajar"],
  "Pelaporan atau kepatuhan": ["Laporan", "& aturan"],
  "Suspensi berkepanjangan": ["Suspensi", "lama"],
  "Terkait delisting": ["Delisting", ""],
};

function DotsBlock({ filled, keyA, keyB, note, size = 170 }: { filled: number; keyA: ReactNode; keyB: ReactNode; note: string; size?: number }) {
  return (
    <div className="flex flex-wrap items-center gap-[18px]">
      <IconDots filled={filled} size={size} label={`${filled} dari 100`} />
      <div className="flex flex-col gap-2.5">
        <Key color="var(--viz-chart-blue)">{keyA}</Key>
        <Key color="#3a4358">{keyB}</Key>
        <span className="text-xs text-muted-foreground">{note}</span>
      </div>
    </div>
  );
}

async function cardsFor(slug: string): Promise<ReactNode[]> {
  switch (slug) {
    case "turun-banyak": {
      const { typical_drawdown: dd } = await getBaseRatesData();
      const group = (l1: string, l2: string | undefined, b: { median_pct: number; p25_pct: number; p75_pct: number }) => ({ l1, l2, median: b.median_pct, p25: b.p25_pct, p75: b.p75_pct });
      const small = dd.by_size_tercile.smallest;
      return [
        <QCard
          key="a"
          question="Seberapa dalam saham IDX biasanya jatuh dalam setahun?"
          define={`Penurunan terdalam tiap saham dalam setahun terakhir (${idNum(dd.overall.n, 0)} saham).`}
          howTo={`Kelompok Kecil, nilai tengah ${signedPct(small.median_pct)}: dari 100 saham kecil, sekitar 50 pernah jatuh lebih dalam.`}
          takeaway={`Nilai tengah semua saham: ${signedPct(dd.overall.median_pct)}. Penurunan -40% sampai -50% bukan hal luar biasa.`}
        >
          <RangeChart
            groups={[
              group("Semua", "saham", dd.overall),
              group("Kecil", "(1/3 terkecil)", small),
              group("Menengah", undefined, dd.by_size_tercile.mid),
              group("Besar", "(1/3 terbesar)", dd.by_size_tercile.largest),
            ]}
            yTitle="Penurunan terdalam (%)"
            xTitle="Ukuran perusahaan menurut nilai pasar"
            label="Penurunan terdalam dalam setahun menurut ukuran perusahaan"
          />
          <Legend>
            <Key color="rgba(76,141,240,.55)">Batang: kisaran kebanyakan saham</Key>
            <Key color="#fff">Garis putih: nilai tengah</Key>
          </Legend>
        </QCard>,
      ];
    }
    case "beli-saat-turun": {
      const { recovery_after_fall: rec } = await getBaseRatesData();
      const below = Math.round(rec.still_below_peak.pct ?? 0);
      return [
        <QCard
          key="a"
          question="Setelah harga -30% atau lebih dari puncaknya, berapa yang pulih dalam setahun?"
          define={`${idNum(rec.n_events, 0)} kejadian harga -30% atau lebih dari puncaknya, di ${idNum(rec.n_stocks, 0)} saham. Pulih: kembali ke harga tertinggi sebelum jatuh.`}
          howTo={`Dari 100 kejadian, ${below} harganya masih di bawah puncak lama setahun kemudian.`}
          takeaway={`Yang belum pulih, nilai tengahnya masih ${signedPct(rec.still_down_median_gap_pct ?? 0)} dari puncak lamanya.`}
        >
          <DotsBlock filled={below} keyA={<><b>{below}</b> masih di bawah puncak lama</>} keyB={<><b>{100 - below}</b> sudah kembali</>} note="Dari 100 kejadian harga -30% atau lebih dari puncaknya" />
        </QCard>,
      ];
    }
    case "perusahaan-rugi": {
      const { loss_maker_turnaround: lmt } = await getBaseRatesData();
      const pct = lmt.pct ?? 0;
      const years = lmt.by_year;
      const min = Math.min(...years.map((y) => y.pct));
      const max = Math.max(...years.map((y) => y.pct));
      return [
        <QCard
          key="a"
          question="Dari 100 perusahaan rugi, berapa yang untung lagi tahun depan?"
          define={`${idNum(lmt.n, 0)} kasus rugi, laporan ${years[0].from_year} sampai ${years[years.length - 1].to_year}.`}
          howTo={`Batang ${years[0].from_year}-${String(years[0].to_year).slice(2)}: ${years[0].turned_around} dari ${years[0].n} perusahaan rugi di ${years[0].from_year} untung lagi di ${years[0].to_year}.`}
          takeaway={`Keseluruhan ${idNum(pct)}% (${lmt.turned_around} dari ${idNum(lmt.n, 0)}), kira-kira 1 dari 4, dan tiap tahun ${idNum(min)}% sampai ${idNum(max)}%.`}
        >
          <DotsBlock filled={Math.round(pct)} size={150} keyA={<><b>{Math.round(pct)}</b> untung lagi</>} keyB={<><b>{100 - Math.round(pct)}</b> belum</>} note="Dari 100 perusahaan rugi" />
          <div className="mt-5">
            <AxisColumns
              items={years.map((y) => ({ l1: `${y.from_year}-${String(y.to_year).slice(2)}`, l2: `${y.turned_around}/${y.n}`, value: y.pct, text: `${idNum(y.pct)}%` }))}
              ymax={40}
              step={10}
              yTitle="Untung lagi (%)"
              xTitle="Dari tahun rugi ke tahun berikutnya"
              refLine={{ value: pct, line1: "Keseluruhan", line2: `${idNum(pct)}%` }}
              label="Persentase perusahaan rugi yang untung lagi tahun berikutnya"
            />
          </div>
        </QCard>,
      ];
    }
    case "ikut-ipo": {
      const ipo = await getIpoBoardsData();
      const hs = ["180d", "365d", "720d"];
      const acc = hs.map((h) => ipo.holdout.horizons[h].by_board["Acceleration"]?.negative_rate_pct ?? 0);
      const main = hs.map((h) => ipo.holdout.horizons[h].by_board["Main"]?.negative_rate_pct ?? 0);
      const ns = [ipo.explore, ipo.holdout].flatMap((p) => Object.values(p.horizons).flatMap((h) => ["Acceleration", "Main"].map((b) => h.by_board[b]?.n ?? 0))).filter((n) => n > 0);
      const nMin = Math.min(...ns);
      const nMax = Math.max(...ns);
      return [
        <QCard
          key="a"
          question="Dari 100 IPO, berapa yang harganya sudah turun?"
          define="IPO 2023 dan 2024, dibanding harga penutupan hari pertama."
          howTo={`Titik 365 hari: dari 100 IPO Papan Akselerasi, sekitar ${Math.round(acc[1])} harganya turun. Papan Utama: sekitar ${Math.round(main[1])}.`}
          takeaway={`Papan Akselerasi lebih sering turun. Kelompoknya kecil (${nMin} sampai ${nMax} IPO), jadi belum lolos uji statistik.`}
        >
          <TwoLineChart
            categories={["180 hari", "365 hari", "720 hari"]}
            a={{ name: "Papan Akselerasi", values: acc }}
            b={{ name: "Papan Utama", values: main }}
            yTitle="IPO yang harganya turun (%)"
            xTitle="Waktu sejak hari pertama listing"
            ref50="Separuh IPO"
            label="Persentase IPO yang harganya turun, Papan Akselerasi dan Papan Utama"
          />
          <Legend>
            <Key color="var(--viz-chart-blue)">
              <b>Papan Akselerasi</b>: syarat listing paling ringan
            </Key>
            <Key color="#7f8ca3">
              <b>Papan Utama</b>: syarat listing paling tinggi
            </Key>
          </Legend>
        </QCard>,
      ];
    }
    case "pernah-disuspensi": {
      const s = await getSuspensionSummary();
      const max = Math.max(...s.by_group.map((g) => g.count));
      const ymax = Math.ceil(max / 100) * 100;
      const price = s.by_group.find((g) => g.label === "Pergerakan harga tidak wajar");
      return [
        <QCard
          key="a"
          question="Setelah suspensi karena lonjakan harga, bagaimana 90 hari berikutnya?"
          define={`${H11_UNDERPERFORM.n} kejadian suspensi di 2026 (data uji akhir), diukur 90 hari sesudahnya.`}
          howTo={`Dari 100 saham seperti ini, ${H11_UNDERPERFORM.holdout} kalah dari indeks dalam 90 hari.`}
          takeaway={`Data awal (2025) lebih seimbang: ${H11_UNDERPERFORM.explore} dari 100 kalah. Sebagian kecil terus melonjak, jadi nilai rata-ratanya bisa tampak naik.`}
        >
          <DotsBlock
            filled={H11_UNDERPERFORM.holdout}
            keyA={<><b>{H11_UNDERPERFORM.holdout}</b> kalah dari indeks</>}
            keyB="sisanya sama atau lebih baik"
            note="Dari 100 saham, 90 hari setelah suspensi"
          />
        </QCard>,
        <QCard
          key="b"
          question="Kenapa saham disuspensi?"
          define={`${idNum(s.total_events, 0)} suspensi, 2021 sampai 2026.`}
          howTo={`Batang Harga tak wajar: ${price?.count ?? 0} dari ${idNum(s.total_events, 0)} suspensi.`}
          takeaway={`${idNum(s.companies_with_suspensions, 0)} dari ${idNum(s.universe_count, 0)} perusahaan (${idNum(s.base_rate_pct)}%) pernah disuspensi.`}
        >
          <AxisColumns
            items={s.by_group.map((g) => {
              const [l1, l2] = SUSPENSION_LABELS[g.label] ?? [g.label, ""];
              return { l1, l2, value: g.count, text: String(g.count) };
            })}
            ymax={ymax}
            step={100}
            unit=""
            yTitle="Jumlah suspensi"
            xTitle="Alasan suspensi"
            label="Jumlah suspensi menurut alasan"
          />
        </QCard>,
      ];
    }
    case "dekat-puncak-laba-turun": {
      const flags = await getFlagsData();
      const b = flags.near_ath_earnings_decline;
      const rows = b.flagged.slice(0, 6);
      const m = (v: number) => idNum(v / 1e9, 1);
      const ex = b.flagged.find((r) => r.earnings_2024 > 0 && r.earnings_2025 > 0);
      return [
        <QCard
          key="a"
          question="Siapa yang harganya dekat tertinggi tapi labanya turun?"
          define={`${b.flagged_count} dari ${b.evaluable_count} perusahaan. Dekat tertinggi: dalam 10% dari harga tertinggi sepanjang masa.`}
          howTo={ex ? `${ex.symbol}: laba 2025 Rp ${m(ex.earnings_2025)} M, ${signedPct(((ex.earnings_2025 - ex.earnings_2024) / ex.earnings_2024) * 100)} dari Rp ${m(ex.earnings_2024)} M di 2024.` : "Bandingkan kolom laba 2024 dan 2025."}
          takeaway="Dua fakta terpisah dari laporan dan harga, bukan penilaian."
        >
          <div>
            <div className="flex items-center gap-1.5 rounded-[10px] bg-[var(--viz-raised)] px-2 py-2.5 text-xs font-semibold tracking-[0.04em] text-[#B9C4D8] md:gap-3.5 md:px-3">
              <span className="w-[46px] shrink-0 md:w-[62px]">Kode</span>
              <span className="flex-1 text-right">Dari tertinggi</span>
              <span className="w-[74px] shrink-0 text-right md:w-24">Laba 2024</span>
              <span className="w-[74px] shrink-0 text-right md:w-24">Laba 2025</span>
            </div>
            {rows.map((r) => (
              <Link key={r.symbol} href={`/saham/${r.symbol}`} className="flex items-center gap-1.5 border-b border-border px-2 py-3 text-[13px] md:gap-3.5 md:px-3 md:text-[13.5px]">
                <b className="w-[46px] shrink-0 md:w-[62px]">{r.symbol}</b>
                <span className="flex-1 text-right font-mono">{signedPct(-r.pct_below_ath * 100)}</span>
                <span className="w-[74px] shrink-0 text-right font-mono md:w-24">{m(r.earnings_2024)}</span>
                <span className="w-[74px] shrink-0 text-right font-mono font-semibold md:w-24">{m(r.earnings_2025)}</span>
              </Link>
            ))}
            <div className="mt-2 text-xs text-muted-foreground">
              Laba dalam Rp miliar. {rows.length} dari {b.flagged_count} perusahaan.
            </div>
          </div>
        </QCard>,
      ];
    }
    case "dividen-besar": {
      const flags = await getFlagsData();
      return [
        <QCard
          key="a"
          question="Kalau dividen besar dibanding laba, seberapa sering dipotong?"
          define={`${H4_CUT_RATES.n} pengamatan perusahaan-tahun, tiga kelompok sama besar menurut dividen dibanding laba (payout ratio).`}
          howTo={`Kelompok tertinggi ${idNum(H4_CUT_RATES.highest)}%: sekitar ${Math.round(H4_CUT_RATES.highest)} dari 100 perusahaan di kelompok itu memotong dividen tahun berikutnya.`}
          takeaway={`Kelompok terendah: sekitar ${Math.round(H4_CUT_RATES.lowest)} dari 100 memotong. Tertinggi: sekitar ${Math.round(H4_CUT_RATES.highest)}. Sekarang ${flags.payout_above_earnings.flagged_count} dari ${flags.payout_above_earnings.evaluable_count} pembayar dividen membayar lebih dari labanya.`}
        >
          <AxisColumns
            items={[
              { l1: "Dividen/laba", l2: "terendah", value: H4_CUT_RATES.lowest, text: `${idNum(H4_CUT_RATES.lowest)}%` },
              { l1: "Dividen/laba", l2: "tengah", value: H4_CUT_RATES.middle, text: `${idNum(H4_CUT_RATES.middle)}%` },
              { l1: "Dividen/laba", l2: "tertinggi", value: H4_CUT_RATES.highest, text: `${idNum(H4_CUT_RATES.highest)}%` },
            ]}
            ymax={80}
            step={20}
            yTitle="Memotong dividen (%)"
            xTitle="Kelompok menurut dividen dibanding laba"
            colors={["#2C4A7C", "#3F73C4", "#6FA4F5"]}
            label="Persentase perusahaan yang memotong dividen menurut kelompok rasio dividen"
          />
        </QCard>,
      ];
    }
    case "float-tipis": {
      return [
        <QCard
          key="a"
          question="Apakah saham berfloat kecil lebih bergejolak?"
          define={`Volatilitas: seberapa besar harga naik-turun dalam setahun. ${H1_VOL_TERCILES.n} saham, 2024-2026.`}
          howTo={`Batang lebih tinggi berarti harga lebih bergejolak. Nilai tengah float besar ${H1_VOL_TERCILES.wide}%, float kecil ${H1_VOL_TERCILES.thin}%.`}
          takeaway="Kebalikan dugaan umum: float besar bersamaan dengan harga lebih bergejolak."
        >
          <AxisColumns
            items={[
              { l1: "Float", l2: "kecil", value: H1_VOL_TERCILES.thin, text: `${H1_VOL_TERCILES.thin}%` },
              { l1: "Float", l2: "sedang", value: H1_VOL_TERCILES.middle, text: `${H1_VOL_TERCILES.middle}%` },
              { l1: "Float", l2: "besar", value: H1_VOL_TERCILES.wide, text: `${H1_VOL_TERCILES.wide}%` },
            ]}
            ymax={100}
            step={25}
            yTitle="Volatilitas setahun (%)"
            xTitle="Free float, tiga kelompok sama besar"
            label="Volatilitas setahun menurut kelompok free float"
          />
        </QCard>,
      ];
    }
    case "vs-emas-deposito": {
      const { summary } = await getBeatGoldData();
      const gold = summary.beat_gold.pct ?? 0;
      const dep = summary.beat_deposit.pct ?? 0;
      return [
        <QCard
          key="a"
          question="Dari 100 saham, berapa yang mengalahkan emas atau deposito?"
          define={`${idNum(summary.n, 0)} saham, hasil harga 5 tahun terakhir.`}
          howTo={`Batang Emas ${idNum(gold)}%: ${Math.round(gold)} dari 100 saham memberi hasil lebih besar dari emas.`}
          takeaway={`Hanya ${Math.round(gold)} dari 100 saham mengalahkan emas. ${Math.round(dep)} dari 100 mengalahkan deposito.`}
        >
          <AxisColumns
            items={[
              { l1: "Indeks", l2: "IHSG", value: summary.beat_index.pct ?? 0, text: `${idNum(summary.beat_index.pct ?? 0)}%` },
              { l1: "Deposito", value: dep, text: `${idNum(dep)}%` },
              { l1: "Emas", value: gold, text: `${idNum(gold)}%` },
            ]}
            ymax={60}
            step={20}
            yTitle="Saham yang menang (%)"
            xTitle="Dibandingkan dengan"
            label="Persentase saham yang mengalahkan indeks, deposito, dan emas"
          />
        </QCard>,
      ];
    }
    default:
      return [];
  }
}

export default async function SituasiDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const situation: SituationMeta | null = await getSituation(slug);
  if (!situation) notFound();
  const cards = await cardsFor(slug);

  const side = (
    <div>
      <H2 className="!text-lg">Batasan</H2>
      <ul className="mt-2.5 list-disc space-y-1 pl-[18px] text-[13.5px] leading-[1.7] text-muted-foreground">
        {situation.limits.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
      {situation.researchPrices && <ResearchNote className="mt-5" />}
      <H2 className="!text-lg mt-7">Terkait</H2>
      <div className="mt-2.5 flex flex-col gap-2.5">
        {situation.related.map((r) => (
          <Link key={r.href + r.label} href={r.href} className="text-[13.5px] font-medium text-[var(--viz-accent)]">
            {r.label} &rarr;
          </Link>
        ))}
      </div>
    </div>
  );

  const body = (
    <div className="flex flex-col gap-4">
      {cards}
    </div>
  );

  return (
    <Page>
      <PageTitle title={situation.title} pill={situation.asOf} back={{ href: "/situasi", label: "Situasi" }} />
      <div className="mt-5 md:mt-7">
        <TwoCol left={body} right={side} ratio="1.5fr 1fr" />
      </div>
    </Page>
  );
}
