import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { AxisColumns } from "@/components/charts/axis-charts";
import { BackLink } from "@/components/back-link";
import { Card, Cells, Page, ResearchNote, Stat, TwoCol } from "@/components/kit";
import { recheckNote } from "@/lib/sectors-recheck";
import { EvidenceSide, LimitList, NumberRow, QCard, SideBlock } from "@/components/qcard";
import { PairBars } from "@/components/situation-ui";
import { VerdictMark } from "@/components/verdict-mark";
import { H6, H18 } from "@/lib/evidence-constants";
import { isRetested, sampleLine } from "@/lib/finding-copy";
import { findingSlug, getFindingsData, VERDICT_CHIP, VERDICT_TAB, type FindingRow } from "@/lib/findings-data";
import { idNum, signedPct } from "@/lib/format";
import { H1_VOL_TERCILES, H4_CUT_RATES } from "@/lib/situations";

export async function generateStaticParams() {
  return (await getFindingsData()).scoreboard.map((r) => ({ slug: findingSlug(r) }));
}

interface AppearsRow {
  label: string;
  /** Second line under the label, when the board has one. */
  sub?: string;
  href: string;
}

/** Where the finding is used elsewhere in the app, keyed by research hypothesis id. */
const APPEARS: Record<string, AppearsRow[]> = {
  H4: [
    { label: "Situasi: dividen besar dibanding laba", href: "/situasi/dividen-besar" },
    { label: "Tanda: dividen melebihi laba", href: "/jelajah/tanda" },
  ],
  H1: [
    { label: "Situasi: free float-nya tipis", href: "/situasi/float-tipis" },
    { label: "Halaman saham: bagian temuan untuk saham ini", href: "/saham/BBCA" },
  ],
  H11: [{ label: "Situasi: saham pernah disuspensi", href: "/situasi/pernah-disuspensi" }],
  H6: [{ label: "Tempel pesan", sub: "Saat pesan berisi “asing borong”", href: "/tanya" }],
  H18: [{ label: "Tempel pesan", sub: "Saat pesan berisi “info orang dalam” atau “insider beli”", href: "/tanya" }],
};

/** "+2,6%" with a real minus sign, as on the boards. */
const pct = (v: number) => signedPct(v, 1, true).replace("-", "−");
const tone = (v: number) => (v < 0 ? ("neg" as const) : ("pos" as const));

/** H6 and H18 get their own sides (board TemuanDetail-Asing / -OrangDalam): what was tested, three counts, limits. */
interface Extra {
  tested: string;
  counts: { value: string; label: string }[];
  limits: string[];
}

const EXTRA: Record<string, Extra> = {
  H6: {
    tested: "Daftar 30 saham asing beli bersih terbesar dan 30 jual bersih terbesar, dari data Sectors, dibandingkan hasil 5 hari bursa sesudahnya terhadap IHSG.",
    counts: [
      { value: String(H6.dates), label: "hari daftar" },
      { value: idNum(H6.appearances, 0), label: "saham di daftar" },
      { value: `${H6.windowDays} hari`, label: "jendela hasil" },
    ],
    limits: [
      "Daftar asing harian baru tersedia sejak Januari 2025: sekitar 20 bulan, satu keadaan pasar (termasuk penurunan 2026).",
      `Selisih di bawah sekitar ${idNum(H6.minDetectable, 1)}% per lima hari tidak akan terdeteksi dengan data sebanyak ini.`,
      "Ini hanya daftar harian, bukan kepemilikan asing selama berbulan-bulan.",
      "Uji acak dan tujuh cara menghitung lain (jendela 1, 10 dan 20 hari, 10 teratas, tanpa periode tinjauan indeks) juga tidak menunjukkan perbedaan.",
      `Uji satu-kali yang dirancang sebelum data diambil, dihitung sebagai percobaan ke-${H6.trial}.`,
    ],
  },
  H18: {
    tested: `Satu kejadian per saham per 60 hari, dari ${idNum(H18.filings, 0)} pemberitahuan pembelian menjadi ${idNum(H18.events, 0)} kejadian. Hasil 20 hari bursa dibanding IHSG, dirata-rata per bulan.`,
    counts: [
      { value: idNum(H18.events, 0), label: "kejadian" },
      { value: String(H18.months), label: "bulan diukur" },
      { value: `${H18.windowDays} hari`, label: "jendela hasil" },
    ],
    limits: [
      "Pemberitahuan baru tersedia sejak Januari 2025, dan hanya 8 bulan 2026 yang punya hasil 20 hari penuh.",
      "Pemberitahuan berarti ada perubahan kepemilikan, belum tentu “orang dalam” seperti yang dimaksud di grup.",
      "Hasil tanpa pembelian yang terkait pengambilalihan hampir sama.",
      "Bila dihitung dengan cara lain yang tidak didaftarkan sebelumnya (jendela 60 hari, hasil dipotong di ujung), sebagian hasil awal 2025 dan satu hasil 2026 menjadi signifikan. Itu tidak mengubah kesimpulan, karena yang menentukan adalah cara yang didaftarkan.",
      `Uji satu-kali yang dirancang sebelum data dilihat, dihitung sebagai percobaan ke-${H18.trial}.`,
    ],
  },
};

function chartFor(row: FindingRow): ReactNode {
  const id = row.evidence.hypothesis_id;
  if (id === "H6") {
    const buy = Math.round(H6.holdout.buy);
    const sell = Math.round(H6.holdout.sell);
    return [
      <QCard
        key="a"
        question="Apakah saham di daftar asing beli terbanyak menang dari IHSG pekan berikutnya?"
        define={`Setiap 6 hari bursa dari Januari 2025 sampai September 2026, diambil 30 saham asing beli terbanyak dan 30 asing jual terbanyak hari itu. Hasilnya dilihat ${H6.windowDays} hari bursa setelah daftar muncul.`}
        howTo="kedua batang hampir sama tinggi berarti masuk daftar asing beli tidak membedakan hasil pekan berikutnya."
        takeaway={`Tidak ada perbedaan. Data awal (2025) juga sama: ${Math.round(H6.explore.buy)} dan ${Math.round(H6.explore.sell)} dari 100.`}
        basis={`Dari 100 saham di tiap daftar, yang mengungguli IHSG dalam ${H6.windowDays} hari bursa berikutnya. Data uji: Oktober 2025 sampai September 2026, ${H6.holdout.dates} hari.`}
      >
        <PairBars a={{ n: buy, label: "Daftar asing beli" }} b={{ n: sell, label: "Daftar asing jual" }} />
      </QCard>,
      <QCard
        key="b"
        question="Lalu kenapa daftar itu terlihat menjanjikan?"
        define="Karena saham yang sedang dibeli asing biasanya sudah naik sebelum daftarnya muncul."
        howTo="angka di atas sudah terjadi sebelum Anda bisa melihat daftarnya. Yang kami ukur hanya sesudahnya."
        takeaway={"“Asing borong” menggambarkan kenaikan yang sudah lewat."}
        basis={null}
      >
        <NumberRow
          items={[
            { value: pct(H6.listDay.buy), caption: "Daftar beli, di hari daftar muncul", tone: tone(H6.listDay.buy) },
            { value: pct(H6.listDay.sell), caption: "Daftar jual, di hari yang sama", tone: tone(H6.listDay.sell) },
            { value: pct(H6.prior20d.buy), caption: "Daftar beli, 20 hari sebelumnya", tone: tone(H6.prior20d.buy) },
          ]}
        />
      </QCard>,
    ];
  }
  if (id === "H18") {
    const a = Math.round(H18.explore.beat);
    const b = Math.round(H18.holdout.beat);
    return [
      <QCard
        key="a"
        question="Setelah orang dalam membeli, apakah harga saham menang dari IHSG dalam 20 hari bursa?"
        define="Setiap pemberitahuan pembelian oleh direksi, komisaris, atau pemegang besar (Januari 2025 sampai September 2026), dihitung mulai hari bursa setelah pemberitahuan."
        howTo="50 berarti sama dengan tidak ada informasi. Di bawah 50 berarti lebih sering kalah dari IHSG."
        takeaway={`Tidak lebih sering menang dari IHSG. Data uji: ${b} dari 100.`}
        basis={`Dari 100 saham setelah ada pembelian orang dalam, yang mengungguli IHSG dalam ${H18.windowDays} hari bursa berikutnya.`}
      >
        <PairBars a={{ n: a, label: "2025 (data awal)" }} b={{ n: b, label: "2026 (data uji)" }} />
      </QCard>,
      <QCard
        key="b"
        question="Kenapa rata-rata tahun 2025 terlihat tinggi?"
        define="Beberapa kenaikan besar mengangkat rata-rata, sementara kejadian yang biasa justru kalah."
        howTo="rata-rata mudah terdongkrak oleh beberapa pemenang besar; nilai tengah menunjukkan kejadian yang biasa."
        takeaway="Tidak ada keunggulan yang luas dan konsisten."
        basis={null}
      >
        <NumberRow
          items={[
            { value: pct(H18.explore.monthlyMean), caption: "Rata-rata bulanan 2025", tone: tone(H18.explore.monthlyMean) },
            { value: pct(H18.explore.medianEvent), caption: "Kejadian di tengah, 2025", tone: tone(H18.explore.medianEvent) },
            { value: pct(H18.holdout.monthlyMean), caption: "Rata-rata bulanan 2026, tidak signifikan", tone: tone(H18.holdout.monthlyMean) },
          ]}
        />
      </QCard>,
    ];
  }
  if (id === "H4") {
    return (
      <QCard
        question="Perusahaan mana yang lebih sering memotong dividen?"
        define={`Payout ratio: dividen yang dibayar dibanding laba. ${H4_CUT_RATES.n} pengamatan perusahaan-tahun.`}
        howTo={`Batang tertinggi ${idNum(H4_CUT_RATES.highest)}%: sekitar ${Math.round(H4_CUT_RATES.highest)} dari 100 perusahaan di kelompok itu memotong dividen.`}
        takeaway={`Terendah: sekitar ${Math.round(H4_CUT_RATES.lowest)} dari 100. Tertinggi: sekitar ${Math.round(H4_CUT_RATES.highest)}. Arah sama di data awal (8% ke 51%).`}
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
      </QCard>
    );
  }
  if (id === "H17") {
    // Spearman rho, sector-neutral, from EXPERIMENT.md "H17 - NOT confirmed" (run 2026-09-22): explore 2022-2023 n=1,196 rho +0.050; holdout 2024-2025 n=1,256 rho +0.002.
    const cells = [
      { v: "+0,05", cap: "Data awal, 2022 sampai 2023 (1.196 pengamatan)" },
      { v: "+0,00", cap: "Data uji, 2024 sampai 2025 (1.256 pengamatan)" },
    ];
    return (
      <QCard
        question="Apakah perusahaan yang labanya naik hasil harganya lebih baik?"
        define="Kenaikan laba bersih dibanding tahun sebelumnya, dicocokkan dengan hasil harga Mei sampai September tahun berikutnya."
        howTo="Angka ini korelasi: 0 berarti kenaikan laba tidak membantu menebak hasil harga, +1 berarti selalu sejalan."
        takeaway="Di data uji, tidak ada kaitan. Di data awal pun hanya samar."
      >
        <div className="flex gap-3.5">
          {cells.map((c) => (
            <div key={c.cap} className="min-w-0 flex-1">
              <div className="font-mono text-[26px] font-bold tracking-[-0.02em] text-muted-foreground">{c.v}</div>
              <div className="mt-1 text-xs leading-snug text-muted-foreground">{c.cap}</div>
            </div>
          ))}
        </div>
      </QCard>
    );
  }
  if (id === "H1") {
    return (
      <QCard
        question="Apakah saham berfloat kecil lebih bergejolak?"
        define={`Volatilitas: seberapa besar harga naik-turun dalam setahun. ${H1_VOL_TERCILES.n} saham, 2024-2026.`}
        howTo={`Batang lebih tinggi berarti lebih bergejolak. Float besar ${H1_VOL_TERCILES.wide}%, float kecil ${H1_VOL_TERCILES.thin}%.`}
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
      </QCard>
    );
  }
  return null;
}

export default async function TemuanDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const findings = await getFindingsData();
  const row = findings.scoreboard.find((r) => findingSlug(r) === slug);
  if (!row) notFound();
  const ev = row.evidence;
  const appears = APPEARS[ev.hypothesis_id] ?? [];
  const extra = EXTRA[ev.hypothesis_id];
  const chart = chartFor(row);
  const recheck = await recheckNote(row.belief);
  const tab = VERDICT_TAB[row.verdict];
  const chip = VERDICT_CHIP[row.verdict];

  const tested = (
    <SideBlock title="Apa yang diuji">
      <Card>
        <p className="text-sm leading-[1.55]">{extra?.tested ?? row.belief_id}</p>
        <div className="mt-3.5">
          {extra ? (
            <div className="grid grid-cols-3">
              {extra.counts.map((c, i) => (
                <div key={c.label} className={i > 0 ? "border-l border-border pl-3" : ""}>
                  <div className="font-mono text-lg font-bold">{c.value}</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">{c.label}</div>
                </div>
              ))}
            </div>
          ) : (
            <Cells>
              {[<Stat key="n" value={sampleLine(ev)} label={isRetested(ev) ? "sampel, diuji ulang pada data terpisah" : "sampel"} size={15} />, <Stat key="p" value={ev.period_id} label="periode" size={15} />]}
            </Cells>
          )}
        </div>
        {!extra && <p className="mt-3.5 text-xs text-muted-foreground">Kode uji: {ev.hypothesis_id}</p>}
      </Card>
    </SideBlock>
  );
  const links = appears.length > 0 && (
    <SideBlock title="Muncul di aplikasi">
      <div className="-mt-1 flex flex-col">
        {appears.map((a) => (
          <Link key={a.href + a.label} href={a.href} className="flex items-center gap-3 border-b border-border py-3 last:border-0">
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-foreground">{a.label}</span>
              {a.sub && <span className="mt-0.5 block text-xs text-muted-foreground">{a.sub}</span>}
            </span>
            <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
          </Link>
        ))}
      </div>
    </SideBlock>
  );
  const rechecked = recheck ? (
    <SideBlock title="Dicek ulang dengan data Sectors">
      <p className="text-[13.5px] leading-relaxed text-muted-foreground">{recheck}</p>
    </SideBlock>
  ) : null;
  const limits = (
    <SideBlock title="Batasan">
      <LimitList items={extra?.limits ?? [ev.limit_id]} />
      <ResearchNote className="mt-4" />
    </SideBlock>
  );

  // Findings without a chart of their own keep the plain result line so the card column is never empty.
  const main = (
    <div className="flex flex-col gap-4">
      {chart ?? (
        <Card className="flex items-center gap-3">
          <VerdictMark verdict={row.verdict} size={24} />
          <div>
            <div className="text-[13px] text-muted-foreground">Hasil pengujian</div>
            <div className="text-[15px] font-semibold leading-snug">{row.result_short_id}</div>
          </div>
        </Card>
      )}
    </div>
  );
  const side = (
    <EvidenceSide>
      {tested}
      {rechecked}
      {links}
      {limits}
      <Link href="/temuan/cara-kami-menguji" className="text-[13.5px] font-medium text-[var(--viz-accent)]">
        Cara kami menguji &rarr;
      </Link>
    </EvidenceSide>
  );

  return (
    <Page>
      <BackLink fallback={{ href: `/temuan?hasil=${tab.key}`, label: "Temuan" }} />
      <div className="mt-3.5 flex items-center justify-between gap-3">
        <h1 className="text-[26px] font-bold leading-tight tracking-[-0.02em] text-foreground md:text-[32px]">{row.title_short_id}</h1>
        <span className="inline-flex shrink-0 items-center gap-[5px] rounded-md border px-[11px] py-1 text-xs font-semibold" style={{ color: chip.color, borderColor: chip.color }}>
          <VerdictMark verdict={row.verdict} size={14} />
          {chip.label}
        </span>
      </div>
      <div className="mt-5 md:mt-7">
        <TwoCol left={main} right={side} ratio="1.5fr 1fr" />
      </div>
    </Page>
  );
}
