import Link from "next/link";
import { DistChart } from "@/components/charts/axis-charts";
import { JelajahHead } from "@/components/jelajah-head";
import { Picker } from "@/components/picker";
import { RankList, type RankRow } from "@/components/rank-list";
import { Card, H2, Neg, Pos, Sub, TwoCol } from "@/components/kit";
import { distanceBins } from "@/lib/distribution";
import { formatDateId, formatPrice, idNum, sharePct, shortName, signedPct } from "@/lib/format";
import { getNewsSentiment } from "@/lib/news-data";
import { getRankingsData } from "@/lib/rankings-data";
import { getQuoteIndex } from "@/lib/stock-data";

const MEASURES = [
  { value: "jauh-dari-puncak", label: "Jauh dari puncak" },
  { value: "float-terendah", label: "Free float terendah" },
  { value: "pergerakan", label: "Pergerakan hari ini" },
  { value: "banyak-diberitakan", label: "Banyak diberitakan" },
  { value: "nilai-pasar-naik", label: "Nilai pasar naik terbanyak, setahun" },
  { value: "nilai-pasar-turun", label: "Nilai pasar turun terbanyak, setahun" },
] as const;

type Measure = (typeof MEASURES)[number]["value"];
const PAGE = 10;

function pickMeasure(raw: string | string[] | undefined): Measure {
  const v = Array.isArray(raw) ? raw[0] : raw;
  return MEASURES.some((m) => m.value === v) ? (v as Measure) : "jauh-dari-puncak";
}

export default async function JelajahPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const measure = pickMeasure(sp.urut);
  const shown = Math.min(100, Math.max(PAGE, Number(Array.isArray(sp.tampil) ? sp.tampil[0] : sp.tampil) || PAGE));

  const [rankings, quotes, news] = await Promise.all([getRankingsData(), getQuoteIndex(), getNewsSentiment()]);
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
        <Link href="/situasi/float-tipis" className="mt-2 inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
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
  } else if (measure === "banyak-diberitakan") {
    const all = news.most_covered;
    total = all.length;
    title = "Paling banyak diberitakan";
    line = `Jumlah berita yang menyebut saham ini, ${formatDateId(news.first_date)} sampai ${formatDateId(news.last_date)}.`;
    rows = all.slice(0, shown).map((r) => ({
      code: r.symbol,
      name: shortName(r.company_name ?? r.symbol),
      value: idNum(r.mentions, 0),
      sub: (
        <>
          <span className="text-[var(--viz-diverging-pos)]">{r.bullish}</span> &middot; <span className="text-[var(--viz-diverging-neg)]">{r.bearish}</span>
        </>
      ),
    }));
    side = (
      <Card className="md:p-5">
        <div className="text-[15px] font-semibold">Pembanding</div>
        <p className="mt-2 text-[13.5px] leading-normal">
          Dari {idNum(news.n_mentions, 0)} penyebutan saham, <b className="font-mono text-[var(--viz-diverging-pos)]">{idNum(news.bullish_mentions_pct, 0)}%</b> bertanda bullish. Angka kecil: bullish &middot; bearish.
        </p>
        <Link href="/jelajah/berita" className="mt-2 inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
          Ringkasan berita &rarr;
        </Link>
      </Card>
    );
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

  const nextHref = `/jelajah?urut=${measure}&tampil=${Math.min(100, shown + PAGE)}`;
  const list = (
    <div>
      <H2>{title}</H2>
      <Sub>{line}</Sub>
      <div className="mt-2">
        <RankList rows={rows} />
      </div>
      {shown < Math.min(100, total) && (
        <Link href={nextHref} scroll={false} className="mt-4 flex h-11 items-center justify-center rounded-full border border-border text-[13.5px] font-semibold text-[var(--viz-accent)]">
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
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <JelajahHead active="peringkat" pill={`Data ${formatDateId(rankings.as_of)}`} />
      <Picker label="Urut menurut" param="urut" value={measure} options={MEASURES.map((m) => ({ value: m.value, label: m.label }))} />
      {side ? (
        <div className="mt-5 md:mt-6">
          <TwoCol left={list} right={side} ratio="1.5fr 1fr" rightFirstOnMobile />
        </div>
      ) : (
        <div className="mt-5 md:mt-6 md:max-w-2xl">{list}</div>
      )}
    </main>
  );
}
