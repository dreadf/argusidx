import Link from "next/link";
import { notFound } from "next/navigation";
import { DistChart } from "@/components/charts/axis-charts";
import { Note } from "@/components/explore-list";
import { RankList, type RankRow } from "@/components/rank-list";
import { Card, H2, Neg, Pos, Sub, TwoCol, PageTitle } from "@/components/kit";
import { distanceBins } from "@/lib/distribution";
import { buildDerivedView, DERIVED_SLUGS, getRankingsDerived, type DerivedSlug } from "@/lib/derived-rankings-data";
import { formatDateId, formatPrice, idNum, sharePct, shortName, signedPct } from "@/lib/format";
import { getRankingsData } from "@/lib/rankings-data";
import { getQuoteIndex } from "@/lib/stock-data";

const MEASURES = ["jauh-dari-puncak", "float-terendah", "pergerakan", "nilai-pasar-naik", "nilai-pasar-turun"] as const;
type Measure = (typeof MEASURES)[number];
const PAGE = 10;

const moreButton = "mt-4 flex h-9 items-center justify-center rounded-md border border-border text-[13px] font-semibold text-[var(--viz-accent)] transition-colors hover:bg-muted";
const wrap = "mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8";

export default async function PeringkatDetailPage({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { slug } = await params;
  const back = { href: "/temuan/peringkat", label: "Peringkat" };

  if ((DERIVED_SLUGS as string[]).includes(slug)) {
    const derived = await getRankingsDerived();
    const view = buildDerivedView(slug as DerivedSlug, derived);
    return (
      <main className={wrap}>
        <PageTitle title={view.title} pill={`Data ${formatDateId(derived.as_of)}`} back={back} />
        <div>
          <Sub>{view.line}</Sub>
          <div className="mt-4">
            <RankList rows={view.rows} />
          </div>
          <div className="mt-4 flex flex-col gap-3">
            {view.ties && <Note>{view.ties}</Note>}
            {view.excluded && <Note>{view.excluded}</Note>}
          </div>
          <p className="mt-5 text-[13px] leading-normal text-muted-foreground">{view.method}</p>
        </div>
      </main>
    );
  }

  if (!(MEASURES as readonly string[]).includes(slug)) notFound();
  const measure = slug as Measure;
  const sp = await searchParams;
  const shown = Math.min(100, Math.max(PAGE, Number(Array.isArray(sp.tampil) ? sp.tampil[0] : sp.tampil) || PAGE));

  const [rankings, quotes] = await Promise.all([getRankingsData(), getQuoteIndex()]);
  const quote = new Map(quotes.map((q) => [q.code, q]));
  const priceOf = (code: string) => {
    const p = quote.get(code)?.price;
    return p == null ? undefined : formatPrice(p);
  };

  let title = "";
  let line = "";
  let total = 0;
  let rows: RankRow[] = [];
  let side: React.ReactNode = null;

  if (measure === "jauh-dari-puncak") {
    const all = rankings.furthest_below_52w_high;
    total = all.length;
    title = "Paling jauh dari puncak";
    line = "Jarak dari harga tertinggi setahun terakhir.";
    rows = all.slice(0, shown).map((r) => ({ code: r.symbol, name: shortName(r.company_name), value: <Neg>{signedPct(r.pct_below_high * 100)}</Neg>, sub: priceOf(r.symbol) }));
    const { bins, medianRatio, medianPos } = distanceBins(all.map((r) => r.pct_below_high));
    side = (
      <Card className="md:p-5">
        <div className="text-[15px] font-semibold">Sebaran {idNum(all.length, 0)} saham</div>
        <div className="mb-3 mt-0.5 text-[13px] text-muted-foreground">Berapa saham di tiap jarak dari harga tertinggi setahun</div>
        <DistChart
          bins={bins}
          median={medianPos}
          medianLabel={`Nilai tengah ${signedPct(medianRatio * 100)}`}
          yTitle="Jumlah saham"
          xTitle="Harga sekarang dibanding titik tertinggi setahun (%)"
          label={`Sebaran jarak harga dari tertinggi setahun untuk ${all.length} saham`}
        />
        <p className="mt-3 text-[13.5px] leading-normal">
          Saham tipikal ada di <Neg>{signedPct(medianRatio * 100)}</Neg> dari tertinggi setahun.
        </p>
      </Card>
    );
  } else if (measure === "float-terendah") {
    const all = rankings.lowest_free_float;
    total = all.length;
    const sorted = all.map((r) => r.free_float).sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];
    title = "Free float terendah";
    line = "Bagian saham yang dipegang publik, paling kecil dulu.";
    rows = all.slice(0, shown).map((r) => ({ code: r.symbol, name: shortName(r.company_name), value: sharePct(r.free_float), sub: priceOf(r.symbol) }));
    side = (
      <Card className="md:p-5">
        <div className="text-[15px] font-semibold">Pembanding</div>
        <p className="mt-2 text-[13.5px] leading-normal">
          Free float tipikal seluruh saham: <b className="font-mono">{sharePct(median)}</b>. Free float kecil bukan tanda baik atau buruk; diuji, saham dengan free float besar justru lebih bergejolak.
        </p>
        <Link href="/situasi/float-tipis" className="mt-2 inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)] hover:underline">
          Lihat buktinya &rarr;
        </Link>
      </Card>
    );
  } else if (measure === "pergerakan") {
    const all = rankings.biggest_daily_moves;
    total = all.length;
    title = "Pergerakan harga terbesar hari ini";
    line = `Naik dan turun, urut menurut besarnya. Data ${formatDateId(rankings.as_of)}.`;
    rows = all.slice(0, shown).map((r) => ({
      code: r.symbol,
      name: shortName(r.company_name),
      value: r.daily_close_change < 0 ? <Neg>{signedPct(r.daily_close_change * 100, 1)}</Neg> : <Pos>{signedPct(r.daily_close_change * 100, 1, true)}</Pos>,
      sub: priceOf(r.symbol),
    }));
  } else {
    const inc = measure === "nilai-pasar-naik";
    const all = inc ? rankings.mcap_change.increases : rankings.mcap_change.decreases;
    total = all.length;
    title = inc ? "Nilai pasar naik terbanyak" : "Nilai pasar turun terbanyak";
    line = "Perubahan nilai pasar dalam setahun. Naik dan turun ditampilkan terpisah.";
    rows = all.slice(0, shown).map((r) => ({
      code: r.symbol,
      name: shortName(r.company_name),
      value: r.yearly_mcap_change < 0 ? <Neg>{signedPct(r.yearly_mcap_change * 100, 0)}</Neg> : <Pos>{signedPct(r.yearly_mcap_change * 100, 0, true)}</Pos>,
      sub: priceOf(r.symbol),
    }));
  }

  const list = (
    <div>
      <H2>{title}</H2>
      <Sub>{line}</Sub>
      <div className="mt-2">
        <RankList rows={rows} />
      </div>
      {shown < Math.min(100, total) && (
        <Link href={`/temuan/peringkat/${measure}?tampil=${Math.min(100, shown + PAGE)}`} scroll={false} className={moreButton}>
          Tampilkan {PAGE} berikutnya
        </Link>
      )}
      <p className="mt-2.5 text-center text-xs text-muted-foreground md:text-left">
        1 sampai {Math.min(shown, total)} dari {Math.min(100, total)}
        {total > 100 ? ` teratas (${idNum(total, 0)} seluruhnya)` : ""}
      </p>
    </div>
  );

  return (
    <main className={wrap}>
      <PageTitle title="Peringkat" pill={`Data ${formatDateId(rankings.as_of)}`} back={back} />
      {side ? (
        <div className="mt-5 md:mt-6">
          <TwoCol left={list} right={side} ratio="1.5fr 1fr" rightFirstOnMobile />
        </div>
      ) : (
        <div className="mt-5 md:mt-6">{list}</div>
      )}
    </main>
  );
}
