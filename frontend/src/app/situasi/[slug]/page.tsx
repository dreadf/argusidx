import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { AxisColumns, RangeChart, TwoLineChart } from "@/components/charts/axis-charts";
import { IconDots, Key } from "@/components/charts/dots";
import { H2, Page, PageTitle, ResearchNote, Sub, TwoCol } from "@/components/kit";
import { rangeNote } from "@/lib/uncertainty-data";
import { EvidenceSide, Legend, LimitList, QCard, SideBlock } from "@/components/qcard";
import { PairBars, StockListRow } from "@/components/situation-ui";
import { getBaseRatesData } from "@/lib/base-rates-data";
import { getBeatGoldData } from "@/lib/beat-gold-data";
import { PRICE_CACHE_START_YEAR, PRICE_SUSPENSION_SPAN, SUSPENSIONS_SINCE_2025 } from "@/lib/evidence-constants";
import { getFlagsData } from "@/lib/flags-data";
import { idNum, signedPct } from "@/lib/format";
import { getIpoBoardsData } from "@/lib/ipo-boards-data";
import { getSituation, getSituations, H1_VOL_TERCILES, H11_UNDERPERFORM, H4_CUT_RATES, type SituationMeta } from "@/lib/situations";
import { getSituationRows, getSituationsFile, kindOfSlug, LIST_SUB } from "@/lib/stock-situations";
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

/** Chart and basis for a QCard that puts 100 dots beside its text: spread onto the card. */
function dots({ filled, keyA, keyB, note }: { filled: number; keyA: ReactNode; keyB: ReactNode; note: string }) {
  return {
    children: <IconDots filled={filled} size={128} label={`${filled} dari 100`} />,
    basis: (
      <div className="flex flex-col gap-2">
        <Key color="var(--viz-chart-blue)">{keyA}</Key>
        <Key color="#3a4358">{keyB}</Key>
        <span>{note}</span>
      </div>
    ),
  };
}

async function cardsFor(slug: string): Promise<ReactNode[]> {
  switch (slug) {
    case "turun-banyak": {
      const { typical_drawdown: dd, recovery_after_fall: rec } = await getBaseRatesData();
      const below = Math.round(rec.still_below_peak.pct ?? 0);
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
        <QCard
          key="b"
          question="Setelah harga -30% atau lebih dari puncaknya, berapa yang pulih dalam setahun?"
          define={`${idNum(rec.n_events, 0)} kejadian harga -30% atau lebih dari puncaknya, di ${idNum(rec.n_stocks, 0)} saham. Pulih: kembali ke harga tertinggi sebelum jatuh.`}
          howTo={`Dari 100 kejadian, ${below} harganya masih di bawah puncak lama setahun kemudian.`}
          takeaway={`Yang belum pulih, nilai tengahnya masih ${signedPct(rec.still_down_median_gap_pct ?? 0)} dari puncak lamanya.`}
          {...dots({ filled: below, keyA: <><b>{below}</b> masih di bawah puncak lama</>, keyB: <><b>{100 - below}</b> sudah kembali</>, note: "Dari 100 kejadian harga -30% atau lebih dari puncaknya" })}
        />,
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
          {...dots({ filled: H11_UNDERPERFORM.holdout, keyA: <><b>{H11_UNDERPERFORM.holdout}</b> kalah dari indeks</>, keyB: "sisanya sama atau lebih baik", note: "Dari 100 saham, 90 hari setelah suspensi" })}
        />,
        <QCard
          key="b"
          question="Kenapa saham disuspensi?"
          define={`${idNum(s.total_events, 0)} suspensi sejak 2018, ${SUSPENSIONS_SINCE_2025} di antaranya sejak 2025.`}
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
    case "harga-baru-melonjak": {
      const { recent_spike: sp } = await getBaseRatesData();
      const below = Math.round(sp.pooled.share_below_event_close * 100);
      const deep = Math.round(sp.pooled.share_deep_drop * 100);
      const pc = (v: number) => signedPct(v * 100, 0, true);
      return [
        <QCard
          key="a"
          question="Setelah harga naik 40% atau lebih dalam 20 hari bursa, bagaimana 60 hari bursa berikutnya?"
          define={`${idNum(sp.pooled.n_events, 0)} kejadian di ${idNum(sp.stocks_with_event, 0)} saham, 2021 sampai 2026.`}
          howTo={`Dari 100 kejadian seperti ini, ${below} berakhir lebih rendah dan ${100 - below} sama atau lebih tinggi.`}
          takeaway={below < 60 ? `Lebih dari empat dari sepuluh tidak turun, jadi ini bukan pola satu arah.` : `Lebih dari separuh berakhir lebih rendah, tetapi sebagian tidak.`}
          basis={`Sekitar ${below} dari 100 kejadian berakhir lebih rendah dari harga hari lonjakan, 60 hari bursa kemudian; ${await rangeNote("recent_spike_pooled")}.`}
        >
          <PairBars a={{ n: below, label: "Lebih rendah" }} b={{ n: 100 - below, label: "Sama atau lebih tinggi" }} />
        </QCard>,
        <QCard
          key="b"
          question="Seberapa lebar sebarannya?"
          define={`Perubahan harga 60 hari bursa setelah hari lonjakan, dari ${idNum(sp.pooled.n_events, 0)} kejadian.`}
          howTo={`Urutkan 100 kejadian dari yang terburuk. Kejadian ke-25 ${sp.pooled.p25_change < 0 ? "turun" : "naik"} ${Math.abs(Math.round(sp.pooled.p25_change * 100))}%, ke-50 ${sp.pooled.median_change < 0 ? "turun" : "naik"} ${Math.abs(Math.round(sp.pooled.median_change * 100))}%, ke-75 ${sp.pooled.p75_change < 0 ? "turun" : "naik"} ${Math.abs(Math.round(sp.pooled.p75_change * 100))}%.`}
          takeaway="Rentangnya lebar ke dua arah."
        >
          <div className="flex gap-3.5">
            {[
              { v: sp.pooled.p25_change, cap: "Seperempat terburuk sama atau lebih rendah dari ini" },
              { v: sp.pooled.median_change, cap: "Nilai tengah" },
              { v: sp.pooled.p75_change, cap: "Seperempat terbaik sama atau lebih tinggi dari ini" },
            ].map((x) => (
              <div key={x.cap} className="min-w-0 flex-1">
                <div className="font-mono text-[26px] font-bold tracking-[-0.02em]" style={{ color: x.v < 0 ? "var(--viz-diverging-neg)" : "var(--viz-diverging-pos)" }}>
                  {pc(x.v)}
                </div>
                <div className="mt-1 text-xs leading-snug text-muted-foreground">{x.cap}</div>
              </div>
            ))}
          </div>
        </QCard>,
        <QCard
          key="c"
          question="Berapa yang sempat turun jauh?"
          define="Penutupan harian, dalam 60 hari bursa setelah hari lonjakan."
          howTo={`Dari 100 kejadian, ${deep} pernah ditutup sedalam itu pada satu hari atau lebih.`}
          takeaway="Ini menghitung titik terendah selama 60 hari, bukan harga di akhir."
          {...dots({ filled: deep, keyA: <><b>{deep}</b> pernah ditutup 30% atau lebih di bawah harga hari lonjakan</>, keyB: "sisanya tidak", note: "Dari 100 kejadian" })}
        />,
      ];
    }
    case "laba-turun-dua-tahun": {
      const { earnings_two_year_decline: d } = await getBaseRatesData();
      const up = Math.round(d.pooled.rate * 100);
      const years = Object.entries(d.by_year);
      const rates = years.map(([, c]) => Math.round(c.rate * 100));
      return [
        <QCard
          key="a"
          question="Setelah laba bersih turun dua tahun berturut-turut, bagaimana tahun berikutnya?"
          define={`${idNum(d.pooled.n, 0)} pengamatan perusahaan yang labanya turun dua tahun berturut-turut, tahun pengamatan ${years.map(([y]) => y).join(" dan ")}.`}
          howTo={`Dari 100 perusahaan seperti ini, ${up} labanya naik lagi tahun berikutnya dan ${100 - up} tidak.`}
          takeaway="Lebih dari separuh naik lagi, tetapi hampir setengahnya tidak."
          basis={`Sekitar ${up} dari 100 perusahaan labanya lebih tinggi di tahun berikutnya.`}
        >
          <PairBars a={{ n: up, label: "Laba naik lagi" }} b={{ n: 100 - up, label: "Laba tidak naik" }} />
        </QCard>,
        <QCard
          key="b"
          question="Apakah stabil dari tahun ke tahun?"
          define="Bagian yang laba tahun berikutnya lebih tinggi, per tahun pengamatan."
          howTo={`${years.length} tahun saja yang bisa diuji. Angkanya dekat, tetapi ${years.length} tahun bukan pola panjang.`}
          takeaway={`Selisih ${Math.max(...rates) - Math.min(...rates)} poin antar tahun.`}
        >
          <div className="flex gap-3.5">
            {years.map(([y, c]) => (
              <div key={y} className="min-w-0 flex-1">
                <div className="font-mono text-[26px] font-bold">{Math.round(c.rate * 100)}</div>
                <div className="mt-1 text-xs leading-snug text-muted-foreground">
                  dari 100, tahun {y} ({idNum(c.n, 0)} pengamatan)
                </div>
              </div>
            ))}
          </div>
        </QCard>,
      ];
    }
    case "laba-dua-kali-lipat": {
      const { earnings_more_than_doubled: d } = await getBaseRatesData();
      const lower = Math.round(d.gave_part_back.rate * 100);
      const all = Math.round(d.gave_all_back.rate * 100);
      const years = Object.entries(d.by_year);
      const ys = years.map(([, c]) => Math.round(c.gave_part_back.rate * 100));
      return [
        <QCard
          key="a"
          question="Setelah laba bersih lebih dari dua kali lipat, bagaimana tahun berikutnya?"
          define={`${idNum(d.gave_part_back.n, 0)} pengamatan, tahun lonjakan ${years[0][0]} sampai ${years[years.length - 1][0]}.`}
          howTo={`Dari 100 perusahaan seperti ini, ${lower} labanya lebih rendah tahun berikutnya dan ${100 - lower} sama atau lebih tinggi.`}
          takeaway="Hampir separuh mempertahankan atau menambah labanya."
          basis={`Sekitar ${lower} dari 100 perusahaan labanya lebih rendah dari tahun lonjakan.`}
        >
          <PairBars a={{ n: lower, label: "Lebih rendah" }} b={{ n: 100 - lower, label: "Sama atau lebih tinggi" }} />
        </QCard>,
        <QCard
          key="b"
          question="Seberapa banyak yang kembali ke bawah tingkat semula?"
          define="Laba tahun berikutnya dibanding laba sebelum lonjakan."
          howTo={`Dari 100 perusahaan, ${all} kehilangan seluruh kenaikannya, ${100 - all} masih di atas tingkat semula.`}
          takeaway="Kehilangan sebagian jauh lebih umum daripada kehilangan semuanya."
          {...dots({ filled: all, keyA: <><b>{all}</b> berakhir di bawah tingkat sebelum lonjakan</>, keyB: "sisanya masih di atas", note: "Dari 100 perusahaan" })}
        />,
        <QCard
          key="c"
          question="Stabil dari tahun ke tahun?"
          define="Bagian yang labanya lebih rendah dari tahun lonjakan, per tahun."
          howTo={`Antara ${Math.min(...ys)} dan ${Math.max(...ys)}, dengan sampel per tahun ${Math.min(...years.map(([, c]) => c.gave_part_back.n))} sampai ${Math.max(...years.map(([, c]) => c.gave_part_back.n))}.`}
          takeaway="Sampel tiap tahun kecil, jadi selisih ini bisa kebetulan."
        >
          <div className="flex gap-3.5">
            {years.map(([y, c]) => (
              <div key={y} className="min-w-0 flex-1">
                <div className="font-mono text-[26px] font-bold">{Math.round(c.gave_part_back.rate * 100)}</div>
                <div className="mt-1 text-xs leading-snug text-muted-foreground">
                  dari 100, {y} ({c.gave_part_back.n})
                </div>
              </div>
            ))}
          </div>
        </QCard>,
      ];
    }
    case "bawah-puncak-lama": {
      const [{ long_below_peak: lbp, as_of }, file] = await Promise.all([getBaseRatesData(), getSituationsFile()]);
      const back = Math.round((lbp.recovered_by_504.rate ?? 0) * 100);
      const fallPct = Math.round((1 - file.definitions.fall_threshold) * 100);
      return [
        <QCard
          key="a"
          question="Kalau sudah lebih dari setahun di bawah puncak, seberapa sering kembali?"
          define={`Saham yang jatuh ${fallPct}% atau lebih dan setahun kemudian masih di bawah puncaknya, dilihat lagi satu tahun sesudahnya.`}
          howTo="batang kiri pendek berarti jarang ada yang pulih penuh setelah dua tahun."
          takeaway={`${back} dari 100 kembali ke puncak. Sisanya masih di bawah.`}
          basis={`Dari 100 kejadian, hasil dua tahun setelah jatuh. Dasar: ${idNum(lbp.still_below_at_252, 0)} kejadian, ${PRICE_CACHE_START_YEAR} sampai ${as_of.slice(0, 4)}; ${await rangeNote("c_recovered_by_trigger_plus_504")}.`}
        >
          <PairBars a={{ n: back, label: "Kembali ke puncak" }} b={{ n: 100 - back, label: "Masih di bawah" }} />
        </QCard>,
      ];
    }
    case "langganan-suspensi": {
      const { repeat_spike_suspension: r } = await getBaseRatesData();
      const again = Math.round(r.share_followed * 100);
      const spaced = Math.round(r.share_followed_by_gap_over_7d * 100);
      return [
        <QCard
          key="a"
          question="Setelah disuspensi karena harga melonjak, seberapa sering disuspensi lagi?"
          define={`Semua suspensi karena kenaikan harga di data Sectors, ${PRICE_SUSPENSION_SPAN}, dilihat setahun sesudahnya.`}
          howTo="batang kiri lebih tinggi berarti suspensi berulang itu biasa, bukan kejadian langka."
          takeaway={`Sekitar ${again} dari 100 disuspensi lagi. Bila pengumuman yang hanya berselang 7 hari tidak dihitung, ${spaced} dari 100.`}
          basis={`Dari 100 suspensi, yang diikuti suspensi serupa dalam setahun. Dasar: ${r.eligible_events} kejadian dengan setahun pengamatan; ${await rangeNote("s2_followed_within_365d")}.`}
        >
          <PairBars a={{ n: again, label: "Disuspensi lagi" }} b={{ n: 100 - again, label: "Tidak lagi" }} />
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

  const kind = kindOfSlug(slug);
  // "Kapan situasi ini berlaku": the rule that puts a stock here, from the list definition and the current count.
  const when =
    situation.when ?? (kind && situation.count !== null ? { title: "Kapan situasi ini berlaku", text: `${LIST_SUB[kind].sub} Sekarang ${idNum(situation.count, 0)} ${kind === "loss_year" ? "perusahaan" : "saham"}.` } : null);

  const side = (
    <EvidenceSide>
      {when && (
        <SideBlock title={when.title}>
          <p className="text-[13px] leading-normal text-muted-foreground">{when.text}</p>
        </SideBlock>
      )}
      <SideBlock title="Batasan">
        <LimitList items={situation.limits} />
        {situation.researchPrices && <ResearchNote className="mt-4" />}
      </SideBlock>
      {situation.related.length > 0 && (
        <SideBlock title="Terkait">
          <div className="flex flex-col gap-2.5">
            {situation.related.map((r) => (
              <Link key={r.href + r.label} href={r.href} className="text-[13.5px] font-medium text-[var(--viz-accent)]">
                {r.label} &rarr;
              </Link>
            ))}
          </div>
        </SideBlock>
      )}
    </EvidenceSide>
  );

  // Two boards end at the card and the side column: no stock list under them.
  let listBlock: ReactNode = null;
  if (kind && !situation.noStockList) {
    const all = await getSituationRows(kind);
    const meta = LIST_SUB[kind];
    const sorted = [...all].sort((a, b) => (meta.datedOrder ? (b.date ?? "").localeCompare(a.date ?? "") : 0) || a.code.localeCompare(b.code));
    listBlock = (
      <div className="mt-7">
        <H2 className="!text-lg">
          {sorted.length} {meta.title}
        </H2>
        <p className="mt-1.5 text-[13px] leading-normal text-muted-foreground">{meta.sub} Diurutkan {meta.datedOrder ? "menurut tanggal, lalu kode" : "menurut kode"}.</p>
        <div className="mt-1.5 border-t border-border">
          {sorted.slice(0, 4).map((r) => (
            <StockListRow key={r.code} code={r.code} name={r.name} value={r.value} sub={r.sub} />
          ))}
        </div>
        <Link href={`/situasi/${slug}/daftar`} className="inline-flex min-h-11 items-center text-[13.5px] font-semibold text-[var(--viz-accent)]">
          Lihat semua {sorted.length} &rarr;
        </Link>
      </div>
    );
  }

  const body = (
    <div className="flex flex-col gap-4">
      {cards}
      {listBlock}
    </div>
  );

  return (
    <Page>
      <PageTitle title={situation.title} pill={`Data ${situation.asOf}`} back={{ href: "/situasi", label: "Situasi" }} />
      {situation.sub && <Sub>{situation.sub}</Sub>}
      <div className="mt-5 md:mt-6">
        <TwoCol left={body} right={side} ratio="1.5fr 1fr" />
      </div>
    </Page>
  );
}
