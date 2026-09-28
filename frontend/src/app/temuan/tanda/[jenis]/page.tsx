import Link from "next/link";
import { notFound } from "next/navigation";
import { H2, PageTitle, Sub, TextLink, TwoCol, Cells, Stat } from "@/components/kit";
import { RankList, type RankRow } from "@/components/rank-list";
import { formatDateId, idNum, sharePct, shortName, signedPct } from "@/lib/format";
import { getFlagsData } from "@/lib/flags-data";

type Kind = "payout" | "puncak-laba" | "dividen-tinggi" | "float-lq45";
const KINDS: Kind[] = ["payout", "puncak-laba", "dividen-tinggi", "float-lq45"];
const TITLES: Record<Kind, string> = {
  payout: "Dividen melebihi laba",
  "puncak-laba": "Dekat puncak, laba menurun",
  "dividen-tinggi": "Dividen jauh di atas rata-rata sendiri",
  "float-lq45": "Saham publik kecil di LQ45",
};
const PAGE = 10;

function miliar(v: number): string {
  return `${idNum(v / 1e9, 1)} M`;
}

export default async function AnomaliDetailPage({ params, searchParams }: { params: Promise<{ jenis: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { jenis } = await params;
  if (!(KINDS as string[]).includes(jenis)) notFound();
  const kind = jenis as Kind;
  const sp = await searchParams;
  const flags = await getFlagsData();
  const shown = Math.min(100, Math.max(PAGE, Number(Array.isArray(sp.tampil) ? sp.tampil[0] : sp.tampil) || PAGE));

  let heading = "";
  let meaning = "";
  let exampleTitle = "";
  let exampleStat: { value: string; label: string } = { value: "", label: "" };
  let flagged = 0;
  let evaluable = 0;
  let related: { text: string; href: string } | null = null;
  let rows: RankRow[] = [];
  let order = "";

  if (kind === "payout") {
    const b = flags.payout_above_earnings;
    flagged = b.flagged_count;
    evaluable = b.evaluable_count;
    heading = `${flagged} dari ${evaluable} perusahaan`;
    order = "Urut dari dividen terbesar dibanding laba.";
    meaning = "Dividen yang dibayar lebih besar dari laba (payout ratio di atas 100%).";
    const first = b.flagged[0];
    exampleTitle = `Contoh, ${first.symbol}`;
    exampleStat = { value: `${idNum(first.payout_ratio, 1)}x`, label: "dividen dibanding laba" };
    related = { text: "Payout tinggi sering diikuti dividen dipotong: 14 sampai 66 dari 100.", href: "/temuan" };
    rows = b.flagged.slice(0, shown).map((r) => ({ code: r.symbol, name: shortName(r.company_name ?? r.symbol), value: `${idNum(r.payout_ratio, 1)}x`, sub: "dividen / laba" }));
  } else if (kind === "puncak-laba") {
    const b = flags.near_ath_earnings_decline;
    flagged = b.flagged_count;
    evaluable = b.evaluable_count;
    heading = `${flagged} dari ${evaluable} perusahaan`;
    order = "Urut dari yang paling dekat dengan harga tertinggi.";
    meaning = "Harga dalam 10% dari tertinggi sepanjang masa, sementara laba tahunan lebih rendah dari tahun sebelumnya.";
    const first = b.flagged.find((r) => r.earnings_2024 > 0 && r.earnings_2025 > 0) ?? b.flagged[0];
    exampleTitle = `Contoh, ${first.symbol}`;
    exampleStat = {
      value: signedPct(((first.earnings_2025 - first.earnings_2024) / Math.abs(first.earnings_2024)) * 100),
      label: `laba 2025 (Rp ${miliar(first.earnings_2025)}) dari 2024 (Rp ${miliar(first.earnings_2024)})`,
    };
    rows = b.flagged.slice(0, shown).map((r) => ({
      code: r.symbol,
      name: shortName(r.company_name ?? r.symbol),
      value: signedPct(-r.pct_below_ath * 100),
      sub: `laba ${miliar(r.earnings_2024)} → ${miliar(r.earnings_2025)}`,
    }));
  } else if (kind === "dividen-tinggi") {
    const b = flags.yield_far_above_average;
    flagged = b.flagged_count;
    evaluable = b.evaluable_count;
    heading = `${flagged} dari ${evaluable} perusahaan`;
    order = "Urut sesuai daftar data.";
    meaning = "Imbal hasil dividen tahun ini setidaknya 1,5x rata-rata perusahaan itu sendiri.";
    const first = b.flagged[0];
    exampleTitle = `Contoh, ${first.symbol}`;
    exampleStat = { value: `${idNum(first.yield_ttm / first.yield_avg, 1)}x`, label: `imbal hasil ${sharePct(first.yield_ttm)} dibanding rata-rata sendiri ${sharePct(first.yield_avg)}` };
    rows = b.flagged.slice(0, shown).map((r) => ({ code: r.symbol, name: shortName(r.company_name ?? r.symbol), value: `${idNum(r.yield_ttm / r.yield_avg, 1)}x`, sub: "rata-rata sendiri" }));
  } else {
    const b = flags.lq45_low_float;
    flagged = b.flagged_count;
    evaluable = b.evaluable_count;
    heading = `${flagged} dari ${evaluable} anggota LQ45`;
    order = "Urut dari free float terkecil.";
    meaning = "Free float di bawah 25% padahal saham masuk LQ45, 45 saham paling likuid di IDX.";
    const first = b.flagged[0];
    exampleTitle = `Contoh, ${first.symbol}`;
    exampleStat = { value: sharePct(first.free_float), label: "saham dipegang publik" };
    related = { text: "Diuji: saham dengan free float besar justru lebih bergejolak.", href: "/situasi/float-tipis" };
    rows = b.flagged.slice(0, shown).map((r) => ({ code: r.symbol, name: shortName(r.company_name ?? r.symbol), value: sharePct(r.free_float), sub: "free float" }));
  }

  const side = (
    <div>
      <div className="text-[15px] font-semibold">Artinya</div>
      <p className="mt-1.5 text-sm leading-normal">{meaning}</p>
      <div className="mt-3.5 rounded-xl bg-[var(--viz-raised)] p-3.5">
        <div className="text-xs text-muted-foreground">{exampleTitle}</div>
        <div className="mt-1.5">
          <Cells>
            {[<Stat key="a" value={exampleStat.value} label={exampleStat.label} size={20} />, <Stat key="b" value={`${flagged} dari ${evaluable}`} label="perusahaan kena aturan ini" size={16} />]}
          </Cells>
        </div>
      </div>
      {related && (
        <>
          <div className="mt-6 text-[15px] font-semibold">Temuan terkait</div>
          <p className="mt-1.5 text-[13.5px] leading-normal text-muted-foreground">{related.text}</p>
          <TextLink href={related.href}>Lihat buktinya</TextLink>
        </>
      )}
      <p className="mt-4 text-xs text-muted-foreground">Fakta dari laporan perusahaan, bukan penilaian dan bukan ramalan.</p>
    </div>
  );

  const list = (
    <div>
      <H2>{heading}</H2>
      <Sub>{order}</Sub>
      <div className="mt-2">
        <RankList rows={rows} />
      </div>
      {shown < flagged && (
        <Link
          href={`/temuan/tanda/${kind}?tampil=${Math.min(100, shown + PAGE)}`}
          scroll={false}
          className="mt-4 flex h-9 items-center justify-center rounded-md border border-border text-[13px] font-semibold text-[var(--viz-accent)]"
        >
          Tampilkan {Math.min(PAGE, flagged - shown)} lainnya
        </Link>
      )}
    </div>
  );

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <PageTitle title={TITLES[kind]} pill={`Data ${formatDateId(flags.as_of)}`} back={{ href: "/temuan/tanda", label: "Tanda" }} />
      <div className="mt-4 md:mt-6">
        <TwoCol
          left={list}
          right={<div className="rounded-2xl border border-border bg-card p-4 md:rounded-none md:border-0 md:bg-transparent md:p-0">{side}</div>}
          ratio="2fr 1fr"
          rightFirstOnMobile
        />
      </div>
    </main>
  );
}
