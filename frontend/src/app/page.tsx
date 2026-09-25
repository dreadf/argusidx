import Link from "next/link";
import { ArrowDown, ArrowUp, ChevronRight, Flag } from "lucide-react";
import { MarketLine } from "@/components/charts/axis-charts";
import { Cells, H2, LinkRow, Neg, Page, Stat, Sub, TextLink } from "@/components/kit";
import { RankList } from "@/components/rank-list";
import { formatDateId, idNum, pctFrom, rpTrillion, shortName, signedPct } from "@/lib/format";
import { getFindingsData } from "@/lib/findings-data";
import { getFlagsData } from "@/lib/flags-data";
import { getIdxTotalData, type IdxTotalPoint } from "@/lib/idx-total-data";
import { getMarketData } from "@/lib/market-data";
import { getRankingsData } from "@/lib/rankings-data";
import { getSituations } from "@/lib/situations";
import { getQuoteIndex } from "@/lib/stock-data";

const HOME_SITUATION_SLUGS = ["turun-banyak", "beli-saat-turun", "perusahaan-rugi", "ikut-ipo"];

/** ~350 of 1,373 daily points is plenty for a 300-700px line, and keeps the page payload small. The peak, the last point and each year's first point are always kept. */
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
  return (
    <Link href={`/saham/${code}`} className={`flex items-center gap-3 py-3 ${last ? "" : "border-b border-border"}`}>
      <Arrow className="size-4 shrink-0" style={{ color: up ? "var(--viz-diverging-pos)" : "var(--viz-diverging-neg)" }} />
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-bold">{code}</span>
        <span className="block truncate text-xs text-muted-foreground">{name}</span>
      </span>
      <span className="font-mono text-[17px] font-bold tabular-nums" style={{ color: up ? "var(--viz-diverging-pos)" : "var(--viz-diverging-neg)" }}>
        {signedPct(change * 100, 1, true)}
      </span>
      <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
    </Link>
  );
}

export default async function Home() {
  const [market, rankings, flags, findings, idxTotal, situations, quotes] = await Promise.all([
    getMarketData(),
    getRankingsData(),
    getFlagsData(),
    getFindingsData(),
    getIdxTotalData(),
    getSituations(),
    getQuoteIndex(),
  ]);
  const { movers } = market;

  const count = { yes: 0, no: 0, mixed_or_inconclusive: 0 } as Record<string, number>;
  for (const row of findings.scoreboard) count[row.verdict] = (count[row.verdict] ?? 0) + 1;
  const total = findings.scoreboard.length;

  const situationRows = HOME_SITUATION_SLUGS.map((slug) => situations.find((s) => s.slug === slug)).filter((s): s is NonNullable<typeof s> => s !== undefined);
  const price = new Map(quotes.map((q) => [q.code, q.price]));
  const topMoves = rankings.biggest_daily_moves.slice(0, 3);
  const farRows = rankings.furthest_below_52w_high.slice(0, 5);

  const hero = (
    <div className="rounded-[20px] bg-gradient-to-br from-[#0C2E6E] via-[#16489F] to-[#1B57C4] px-5 py-[22px] md:flex md:items-center md:justify-between md:gap-6 md:px-[34px] md:py-[30px]">
      <div>
        <div className="font-mono text-[26px] font-bold leading-tight text-white md:text-[34px]">
          Hanya {count.yes} dari {total} keyakinan saham yang terbukti
        </div>
        <p className="mt-3 text-sm text-white">
          <b>{count.mixed_or_inconclusive}</b> tidak konsisten &middot; <b>{count.no}</b> tidak terbukti
        </p>
      </div>
      <Link href="/temuan" className="mt-2 inline-flex min-h-11 items-center whitespace-nowrap text-sm font-semibold text-white md:mt-0 md:rounded-full md:border md:border-white/75 md:px-6">
        Lihat buktinya &rarr;
      </Link>
    </div>
  );

  const situasi = (
    <div>
      <H2>Situasi Anda</H2>
      <Sub>Apa yang biasanya terjadi saat Anda mengalami ini.</Sub>
      <div className="mt-1">
        {situationRows.map((s, i) => (
          <LinkRow key={s.slug} href={`/situasi/${s.slug}`} title={s.title} line={s.line} last={i === situationRows.length - 1} />
        ))}
      </div>
      <TextLink href="/situasi">Lihat semua {situations.length} situasi</TextLink>
    </div>
  );

  const latest = idxTotal.latest;
  const peak = idxTotal.max;
  const pasar = (
    <div>
      <H2>Pasar hari ini</H2>
      <div className="mt-3.5 rounded-2xl border border-border bg-card p-[18px] md:p-[22px]">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">Nilai total pasar</span>
          {latest && <span className="whitespace-nowrap rounded-full border border-border px-2.5 py-1 text-[11.5px] text-muted-foreground">Grafik sampai {formatDateId(latest.date)}</span>}
        </div>
        {latest && peak && (
          <>
            <div className="mt-3">
              <MarketLine
                series={thin(idxTotal.series)}
                maxLabel={`Tertinggi ${idNum(peak.value / 1e12, 0)}`}
                yTitle="Nilai pasar (Rp T)"
                label="Nilai total pasar IDX dari 2021 sampai sekarang"
              />
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

  const jauh = (
    <div>
      <H2>Jauh dari puncak</H2>
      <Sub>Jarak harga dari tertinggi setahun terakhir.</Sub>
      <div className="mt-2">
        <RankList
          rows={farRows.map((r) => ({
            code: r.symbol,
            name: shortName(r.company_name),
            value: <Neg>{signedPct(r.pct_below_high * 100)}</Neg>,
            sub: price.get(r.symbol) != null ? `Rp ${(price.get(r.symbol) as number).toLocaleString("id-ID")}` : undefined,
          }))}
        />
      </div>
      <TextLink href="/jelajah">Lihat peringkat lengkap</TextLink>
    </div>
  );

  const tanda = (
    <div>
      <H2>Tanda-tanda</H2>
      <Sub>Fakta dari laporan perusahaan, bukan penilaian.</Sub>
      <div className="mt-1">
        <LinkRow
          href="/jelajah/tanda"
          title="Dividen dibayar melebihi laba"
          line={`${flags.payout_above_earnings.flagged_count} dari ${flags.payout_above_earnings.evaluable_count} perusahaan`}
          icon={<Flag className="size-[18px]" strokeWidth={1.7} />}
        />
        <LinkRow
          href="/jelajah/tanda?jenis=puncak-laba"
          title="Harga dekat tertinggi, laba menurun"
          line={`${flags.near_ath_earnings_decline.flagged_count} dari ${flags.near_ath_earnings_decline.evaluable_count} perusahaan`}
          icon={<Flag className="size-[18px]" strokeWidth={1.7} />}
          last
        />
      </div>
      <TextLink href="/jelajah/tanda">Lihat semua tanda</TextLink>
    </div>
  );

  // One tree, reordered with CSS instead of rendering everything twice: phone
  // order is hero, situasi, pasar, saham hari ini, jauh dari puncak, tanda;
  // from md up the hero spans the top and two columns sit below it.
  return (
    <Page>
      <div className="flex flex-col gap-9 md:grid md:grid-cols-[1.6fr_1fr] md:gap-x-0 md:gap-y-8">
        <div className="order-1 md:order-first md:col-span-2">
          <H2 className="mb-3.5 md:hidden">Yang sudah teruji</H2>
          {hero}
        </div>
        <div className="contents md:flex md:min-w-0 md:flex-col md:gap-8 md:pr-10">
          <div className="order-3 md:order-none">{pasar}</div>
          <div className="order-4 md:order-none">{hariIni}</div>
          <div className="order-5 md:order-none">{jauh}</div>
        </div>
        <div className="contents md:flex md:min-w-0 md:flex-col md:gap-9 md:border-l md:border-border md:pl-10">
          <div className="order-2 md:order-none">{situasi}</div>
          <div className="order-6 md:order-none">{tanda}</div>
        </div>
      </div>
    </Page>
  );
}
