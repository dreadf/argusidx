import Link from "next/link";
import { notFound } from "next/navigation";
import { AxisColumns } from "@/components/charts/axis-charts";
import { Card, Cells, H2, Page, PageTitle, ResearchNote, Stat, TwoCol } from "@/components/kit";
import { QCard } from "@/components/qcard";
import { findingSlug, getFindingsData, VERDICT_TAB, type FindingRow } from "@/lib/findings-data";
import { idNum } from "@/lib/format";
import { H1_VOL_TERCILES, H4_CUT_RATES } from "@/lib/situations";
import { VerdictMark } from "@/components/verdict-mark";

export async function generateStaticParams() {
  return (await getFindingsData()).scoreboard.map((r) => ({ slug: findingSlug(r) }));
}

/** Where the finding is used elsewhere in the app, keyed by research hypothesis id. */
const APPEARS: Record<string, { label: string; href: string }[]> = {
  H4: [
    { label: "Situasi: dividen besar dibanding laba", href: "/situasi/dividen-besar" },
    { label: "Tanda: dividen melebihi laba", href: "/jelajah/tanda" },
  ],
  H1: [
    { label: "Situasi: free float-nya tipis", href: "/situasi/float-tipis" },
    { label: "Halaman saham: bagian temuan untuk saham ini", href: "/saham/BBCA" },
  ],
  H11: [{ label: "Situasi: saham pernah disuspensi", href: "/situasi/pernah-disuspensi" }],
  H9: [{ label: "Jelajah: berita dan sentimen", href: "/jelajah/berita" }],
};

function chartFor(row: FindingRow) {
  const id = row.evidence.hypothesis_id;
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
  const chart = chartFor(row);
  const tab = VERDICT_TAB[row.verdict];

  const tested = (
    <div>
      <H2 className="!text-lg">Apa yang diuji</H2>
      <Card className="mt-3">
        <p className="text-sm leading-normal">{row.belief_id}</p>
        <div className="mt-3.5">
          <Cells>
            {[<Stat key="n" value={ev.n} label="sampel" size={15} />, <Stat key="p" value={ev.period_id} label="periode" size={15} />]}
          </Cells>
        </div>
        <p className="mt-3.5 text-xs text-muted-foreground">Kode uji: {ev.hypothesis_id}</p>
      </Card>
    </div>
  );
  const limits = (
    <div>
      <H2 className="!text-lg">Batasan</H2>
      <p className="mt-2.5 text-[13.5px] leading-[1.7] text-muted-foreground">{ev.limit_id}</p>
    </div>
  );
  const links = appears.length > 0 && (
    <div>
      <H2 className="!text-lg">Muncul di aplikasi</H2>
      <div className="mt-2.5 flex flex-col gap-2.5">
        {appears.map((a) => (
          <Link key={a.href} href={a.href} className="text-[13.5px] font-medium text-[var(--viz-accent)]">
            {a.label} &rarr;
          </Link>
        ))}
      </div>
    </div>
  );

  const main = (
    <div className="flex flex-col gap-6">
      <Card className="flex items-center gap-3">
        <VerdictMark verdict={row.verdict} size={24} />
        <div>
          <div className="text-[13px] text-muted-foreground">Hasil pengujian</div>
          <div className="text-[15px] font-semibold leading-snug">{row.result_short_id}</div>
        </div>
      </Card>
      {chart}
      {tested}
    </div>
  );
  const side = (
    <div className="flex flex-col gap-7">
      {limits}
      <ResearchNote />
      {links}
      <Link href="/temuan/cara-kami-menguji" className="text-[13.5px] font-medium text-[var(--viz-accent)]">
        Cara kami menguji &rarr;
      </Link>
    </div>
  );

  return (
    <Page>
      <PageTitle title={row.title_short_id} back={{ href: `/temuan?hasil=${tab.key}`, label: "Temuan" }} />
      <div className="mt-5 md:mt-7">
        <TwoCol left={main} right={side} ratio="1.5fr 1fr" />
      </div>
    </Page>
  );
}
