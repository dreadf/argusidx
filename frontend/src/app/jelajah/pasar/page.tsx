import Link from "next/link";
import { ArrowDown, ArrowUp, ChevronRight } from "lucide-react";
import { MarketLine } from "@/components/charts/axis-charts";
import { JelajahHead } from "@/components/jelajah-head";
import { Cells, DatePill, H2, Neg, Stat, Sub, TextLink } from "@/components/kit";
import { formatDateId, idNum, pctFrom, rpTrillion, shortName, signedPct } from "@/lib/format";
import { getIdxTotalData, type IdxTotalPoint } from "@/lib/idx-total-data";
import { getMarketData } from "@/lib/market-data";
import { getRankingsData } from "@/lib/rankings-data";

/** ~350 of 1,373 daily points is plenty for a 300-700px line. The peak, the last point and each year's first point are always kept. */
function thin(series: IdxTotalPoint[]): IdxTotalPoint[] {
  let peak = 0;
  series.forEach((p, i) => {
    if (p.value > series[peak].value) peak = i;
  });
  const seenYear = new Set<string>();
  return series.filter((p, i) => {
    const year = p.date.slice(0, 4);
    const firstOfYear = !seenYear.has(year);
    seenYear.add(year);
    return i % 4 === 0 || i === series.length - 1 || i === peak || firstOfYear;
  });
}

function Mover({ code, name, change, last }: { code: string; name: string; change: number; last?: boolean }) {
  const up = change >= 0;
  const Arrow = up ? ArrowUp : ArrowDown;
  const color = up ? "var(--viz-diverging-pos)" : "var(--viz-diverging-neg)";
  return (
    <Link href={`/saham/${code}`} className={`flex items-center gap-3 py-3 ${last ? "" : "border-b border-border"}`}>
      <Arrow className="size-4 shrink-0" style={{ color }} />
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-bold">{code}</span>
        <span className="block truncate text-xs text-muted-foreground">{name}</span>
      </span>
      <span className="font-mono text-[17px] font-bold tabular-nums" style={{ color }}>
        {signedPct(change * 100, 1, true)}
      </span>
      <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
    </Link>
  );
}

/**
 * Jelajah > Pasar. Board: Usulan-Pasar-Mobile / Usulan-Pasar-Web ("Jelajah:
 * Pasar, baru"). The board's heading says "Pasar hari ini"; per G2 it uses
 * the data's own date instead ("Pasar per 13/09/2026").
 */
export default async function PasarPage() {
  const [market, idxTotal, rankings] = await Promise.all([getMarketData(), getIdxTotalData(), getRankingsData()]);
  const { movers } = market;
  const latest = idxTotal.latest;
  const peak = idxTotal.max;
  const topMoves = rankings.biggest_daily_moves.slice(0, 3);

  const pasar = (
    <div>
      <H2>Pasar per {formatDateId(market.as_of)}</H2>
      <div className="mt-3.5 rounded-2xl border border-border bg-card p-[18px] md:p-[22px]">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.07em] text-[var(--viz-accent)]">Nilai total pasar</span>
          {latest && <DatePill>Grafik sampai {formatDateId(latest.date)}</DatePill>}
        </div>
        {latest && peak && (
          <>
            <div className="mt-3">
              <MarketLine series={thin(idxTotal.series)} maxLabel={`Tertinggi ${idNum(peak.value / 1e12, 0)}`} yTitle="Nilai pasar (Rp T)" label="Nilai total pasar IDX dari 2021 sampai sekarang" />
            </div>
            <p className="mt-2.5 text-[13.5px] leading-normal">
              <b className="font-mono">{rpTrillion(latest.value)}</b> <Neg>{signedPct(pctFrom(latest.value, peak.value))}</Neg> dari tertinggi ({rpTrillion(peak.value, 0)}, {formatDateId(peak.date)})
            </p>
          </>
        )}
        <div className="my-4 h-px bg-border" />
        <div className="mb-2.5 text-xs text-muted-foreground">Pergerakan harga {formatDateId(market.as_of)}</div>
        <Cells>
          {[
            <Stat key="u" value={movers.up} label="saham naik" tone="pos" size={20} />,
            <Stat key="d" value={movers.down} label="saham turun" tone="neg" size={20} />,
            <Stat key="f" value={movers.flat} label="saham tetap" size={20} />,
          ]}
        </Cells>
      </div>
    </div>
  );

  const hariIni = (
    <div>
      <H2>Saham hari ini</H2>
      <Sub>Pergerakan harga terbesar, {formatDateId(market.as_of)}.</Sub>
      <div className="mt-1.5">
        {topMoves.map((m, i) => (
          <Mover key={m.symbol} code={m.symbol} name={shortName(m.company_name)} change={m.daily_close_change} last={i === topMoves.length - 1} />
        ))}
      </div>
      <TextLink href="/jelajah?urut=pergerakan">Lihat semua pergerakan</TextLink>
    </div>
  );

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <JelajahHead active="pasar" pill={`Data ${formatDateId(market.as_of)}`} />
      <div className="mt-6 grid gap-9 md:mt-7 md:grid-cols-[1.6fr_1fr] md:gap-0">
        <div className="min-w-0 md:pr-10">{pasar}</div>
        <div className="min-w-0 md:border-l md:border-border md:pl-10">{hariIni}</div>
      </div>
    </main>
  );
}
