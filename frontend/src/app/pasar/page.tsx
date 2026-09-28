import Link from "next/link";
import { ArrowDown, ArrowUp, ChevronRight, Info } from "lucide-react";
import { DistChart, MarketLine } from "@/components/charts/axis-charts";
import { Cells, DatePill, H2, Neg, PageTitle, Stat, Sub, TextLink } from "@/components/kit";
import { findingSlug, getFindingsData } from "@/lib/findings-data";
import { getFlagsData, type FlagsData } from "@/lib/flags-data";
import { formatDateId, idNum, pctFrom, rpTrillion, shortName, signedPct } from "@/lib/format";
import { getIdxTotalData, type IdxTotalPoint } from "@/lib/idx-total-data";
import { getMarketAnalysisData } from "@/lib/market-analysis-data";
import { getMarketConditionData } from "@/lib/market-condition-data";
import { getMarketData } from "@/lib/market-data";
import { getRankingsData } from "@/lib/rankings-data";
import { getSectorBreakdownData } from "@/lib/sector-data";
import { sectorByKey } from "@/lib/sectors-id";

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

const cardCls = "rounded-2xl border border-border bg-card p-[18px] md:p-5";
const eyebrowCls = "text-[11px] font-semibold uppercase tracking-[0.07em] text-[var(--viz-accent)]";

function Row({ href, icon, title, line, trailing }: { href: string; icon?: React.ReactNode; title: string; line: React.ReactNode; trailing?: React.ReactNode }) {
  return (
    <Link href={href} className="flex items-center gap-3 border-b border-border py-3">
      {icon && <span className="flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">{icon}</span>}
      <span className="min-w-0 flex-1">
        <span className="block text-[14.5px] font-semibold leading-snug text-foreground">{title}</span>
        <span className="mt-0.5 block text-xs leading-normal text-muted-foreground">{line}</span>
      </span>
      {trailing}
      <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
    </Link>
  );
}

/** The four flags, by /temuan/tanda/<kind>. Each stays on its own: no combined count. */
const FLAG_ROWS: { key: keyof Omit<FlagsData, "as_of" | "source_file">; kind: string; title: string; unit: string }[] = [
  { key: "yield_far_above_average", kind: "dividen-tinggi", title: "Dividen jauh di atas biasanya", unit: "pembayar dividen" },
  { key: "payout_above_earnings", kind: "payout", title: "Dividen melebihi laba", unit: "pembayar dividen" },
  { key: "near_ath_earnings_decline", kind: "puncak-laba", title: "Dekat puncak, laba turun", unit: "saham" },
  { key: "lq45_low_float", kind: "float-lq45", title: "LQ45 dengan free float tipis", unit: "saham LQ45" },
];

/**
 * Pasar (replaced Jelajah, 2026-09-28). Board: Baru3-Pasar-Web / -Mobile.
 * No tabs: market condition first, then the Peringkat, Sektor and Tanda
 * data as readings of the whole market. The Kondisi pasar label is T1's
 * tested rule, which was NOT confirmed: the card says so in its own note.
 */
export default async function PasarPage() {
  const [market, cond, idxTotal, rankings, sectors, flags, findings, ma] = await Promise.all([
    getMarketData(),
    getMarketConditionData(),
    getIdxTotalData(),
    getRankingsData(),
    getSectorBreakdownData(),
    getFlagsData(),
    getFindingsData(),
    getMarketAnalysisData(),
  ]);
  const ih = cond.ihsg;
  const dist = cond.distance_from_high;
  const latest = idxTotal.latest;
  const peak = idxTotal.max;
  const t1 = findings.scoreboard.find((r) => r.evidence.hypothesis_id === "T1");
  const tertekan = ih.state === "tertekan";

  const tiles = [
    { value: signedPct(ih.pct_from_peak * 100), label: `dari puncak, ${formatDateId(ih.peak_date)}`, neg: true },
    { value: signedPct(ih.pct_vs_ma200 * 100), label: "dari rata-rata 200 hari", neg: false },
    { value: `${Math.round(ih.vol20_percentile)} dari 100`, label: "hari dalam riwayat IHSG lebih tenang dari sekarang", neg: false },
    { value: `${ih.days_since_peak} hari`, label: "bursa sejak puncak", neg: false },
  ];

  const kondisi = (
    <section className={cardCls} aria-labelledby="kondisi-pasar">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div id="kondisi-pasar" className={eyebrowCls}>
            Kondisi pasar
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">IHSG, {formatDateId(ih.date)}</div>
        </div>
        <span
          className="inline-flex h-7 items-center rounded-lg px-3 text-[13px] font-bold"
          style={tertekan ? { background: "rgba(230,103,103,0.16)", color: "var(--viz-diverging-neg)" } : { background: "var(--accent)", color: "var(--viz-accent)" }}
        >
          {tertekan ? "Tertekan" : "Normal"}
        </span>
      </div>
      <div className="mt-3.5 grid grid-cols-2 overflow-hidden rounded-[14px] border border-border md:grid-cols-4">
        {tiles.map((t, i) => (
          <div key={t.label} className={`p-3.5 ${i % 2 === 0 ? "border-r border-border" : ""} ${i < 2 ? "border-b border-border md:border-b-0" : ""} ${i === 1 ? "md:border-r" : ""}`}>
            <div className="font-mono text-lg font-bold md:text-xl" style={{ color: t.neg ? "var(--viz-diverging-neg)" : undefined }}>
              {t.value}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{t.label}</div>
          </div>
        ))}
      </div>
      <div className="mt-3.5 flex gap-2.5 rounded-[14px] border border-dashed border-[var(--border-strong,rgba(255,255,255,0.14))] px-3.5 py-3 text-[12.5px] leading-normal text-muted-foreground">
        <Info className="mt-px size-4 shrink-0" strokeWidth={1.7} />
        <span>
          Label ini menggambarkan kondisi IHSG sekarang, bukan ramalan. Sudah diuji dan tidak terbukti memprediksi 20 hari berikutnya.{" "}
          {t1 && (
            <Link href={`/temuan/${findingSlug(t1)}`} className="text-[var(--viz-accent)] hover:underline">
              Lihat temuannya
            </Link>
          )}
        </span>
      </div>
    </section>
  );

  const total = (
    <section className={`${cardCls} h-full`}>
      <div className="flex items-center justify-between gap-2">
        <span className={eyebrowCls}>Nilai total pasar</span>
        {latest && <DatePill>Sampai {formatDateId(latest.date)}</DatePill>}
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
          <Stat key="u" value={market.movers.up} label="saham naik" tone="pos" size={20} />,
          <Stat key="d" value={market.movers.down} label="saham turun" tone="neg" size={20} />,
          <Stat key="f" value={market.movers.flat} label="saham tetap" size={20} />,
        ]}
      </Cells>
    </section>
  );

  const jarak = (
    <section className={`${cardCls} flex h-full flex-col`}>
      <div className="flex items-center justify-between gap-2">
        <span className={eyebrowCls}>Jarak dari harga tertinggi setahun</span>
        <DatePill>{formatDateId(cond.rankings_as_of)}</DatePill>
      </div>
      <div className="mt-4 grid grid-cols-2 items-start gap-5">
        <div>
          <div className="font-mono text-[28px] font-bold leading-none" style={{ color: "var(--viz-diverging-neg)" }}>
            {signedPct(dist.median * 100)}
          </div>
          <div className="mt-1.5 text-xs text-muted-foreground">saham tipikal, dari harga tertinggi setahun</div>
        </div>
        <p className="text-[13.5px] leading-normal">
          <b className="font-mono">{dist.n_down_30_or_more}</b> dari {idNum(dist.n, 0)} saham turun 30% atau lebih dari tertinggi setahunnya.
        </p>
      </div>
      <div className="mt-4 flex-1">
        <DistChart
          bins={dist.bins}
          median={-dist.median}
          medianLabel={`Tipikal ${signedPct(dist.median * 100)}`}
          yTitle="Jumlah saham"
          xTitle="Jarak dari tertinggi setahun"
          label={`Sebaran ${dist.n} saham menurut jarak dari harga tertinggi setahun`}
        />
      </div>
      <div className="mt-2 border-t border-border pt-1">
        <TextLink href="/temuan/peringkat/jauh-dari-puncak">Lihat peringkatnya</TextLink>
      </div>
    </section>
  );

  const sectorRows = sectors.sectors
    .map((s) => ({ s, meta: sectorByKey(s.sector), share: s.breadth.total_evaluable ? s.breadth.near_low / s.breadth.total_evaluable : 0 }))
    .filter((r) => r.meta)
    .sort((a, b) => b.share - a.share);
  const half = Math.ceil(sectorRows.length / 2);
  const sectorList = (rows: typeof sectorRows) =>
    rows.map(({ s, meta, share }) => {
      const Icon = meta!.icon;
      return (
        <Row
          key={s.sector}
          href={`/pasar/sektor/${meta!.slug}`}
          icon={<Icon className="size-[18px]" strokeWidth={1.7} />}
          title={meta!.label}
          line={
            <>
              <b className="font-mono" style={{ color: share >= 0.4 ? "var(--viz-diverging-neg)" : "var(--foreground)" }}>
                {s.breadth.near_low}
              </b>{" "}
              dari {s.breadth.total_evaluable} saham dekat terendah setahun
            </>
          }
        />
      );
    });

  const sektor = (
    <section id="sektor" className="scroll-mt-20">
      <H2>Sektor</H2>
      <Sub>
        Urut dari yang paling banyak sahamnya dekat harga terendah setahun. Seluruh pasar: <b className="font-mono text-foreground">{market.breadth.near_low}</b> dari {market.breadth.total_evaluable}.
      </Sub>
      <div className="mt-1.5 grid md:grid-cols-2 md:gap-x-10">
        <div>{sectorList(sectorRows.slice(0, half))}</div>
        <div>{sectorList(sectorRows.slice(half))}</div>
      </div>
    </section>
  );

  const tanda = (
    <section>
      <H2>Saham dengan tanda aktif</H2>
      <Sub>Setiap tanda berdiri sendiri, tidak digabung jadi skor.</Sub>
      <div className="mt-1.5">
        {FLAG_ROWS.map((f) => (
          <Row
            key={f.key}
            href={`/temuan/tanda/${f.kind}`}
            title={f.title}
            line={
              <>
                <b className="font-mono text-foreground">{flags[f.key].flagged_count}</b> dari {flags[f.key].evaluable_count} {f.unit}
              </>
            }
          />
        ))}
      </div>
      <TextLink href="/temuan/tanda">Lihat semua di Temuan</TextLink>
    </section>
  );

  // Since the IHSG peak (M5/M6 Sectors closes; see build_market_analysis.py):
  // who dragged total market value down, and how the two big-stock indices
  // held up against the whole market. Descriptive, one snapshot, not a
  // trial (EXPERIMENT.md, 2026-09-28). Addition to Sektor/Tanda/hari ini
  // below, not a replacement of them: no stock named here is a duplicate
  // of the day's movers or an active flag.
  const tone = (v: number) => (v < 0 ? "var(--viz-diverging-neg)" : v > 0 ? "var(--viz-diverging-pos)" : "var(--foreground)");
  const falling = ma.universe.market_value_end < ma.universe.market_value_start;
  const ihsgIdx = ma.indices.find((i) => i.code === "IHSG");
  const bestBig = ma.indices.filter((i) => i.code !== "IHSG").reduce((a, b) => (a.change_since_peak > b.change_since_peak ? a : b));
  const bigBeatsWhole = ihsgIdx !== undefined && bestBig.change_since_peak > ihsgIdx.change_since_peak;

  const sejakPuncak = (
    <section className={cardCls}>
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className={eyebrowCls}>Sejak puncak IHSG</div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            {formatDateId(ma.peak_window.start)} sampai {formatDateId(ma.peak_window.end)}
          </div>
        </div>
      </div>
      <p className="mt-2.5 text-[15px] font-semibold leading-snug">
        {falling && ma.top5_drag_share !== null
          ? `Lima saham menanggung ${idNum(ma.top5_drag_share * 100, 0)}% dari turunnya nilai pasar.`
          : `Nilai total pasar sejak puncak IHSG: ${signedPct((ma.universe.market_value_end / ma.universe.market_value_start - 1) * 100)}.`}
      </p>
      <div className="mt-3.5 grid grid-cols-3 overflow-hidden rounded-[14px] border border-border">
        {[
          { value: signedPct((ma.universe.market_value_end / ma.universe.market_value_start - 1) * 100), label: "nilai semua saham", color: tone(ma.universe.market_value_end - ma.universe.market_value_start) },
          { value: signedPct(ma.universe.median_return * 100), label: "saham tipikal", color: tone(ma.universe.median_return) },
          { value: `${ma.universe.down} dari ${ma.universe.n}`, label: "saham turun", color: "var(--foreground)" },
        ].map((t, i) => (
          <div key={t.label} className={`min-w-0 p-3 ${i < 2 ? "border-r border-border" : ""}`}>
            <div className="font-mono text-[15px] font-bold md:text-base" style={{ color: t.color }}>
              {t.value}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{t.label}</div>
          </div>
        ))}
      </div>
      {falling && (
        <>
          <div className="mt-4 text-[13px] font-semibold">Paling menanggung penurunan</div>
          <p className="mt-0.5 text-xs leading-normal text-muted-foreground">Urut dari besar kontribusinya ke turunnya nilai pasar, bukan dari besar penurunan harganya (angka kecil di kanan).</p>
          <div>
            {ma.drag
              .filter((r): r is typeof r & { drag_share: number } => r.drag_share !== null)
              .slice(0, 5)
              .map((r) => (
                <div key={r.symbol} className="flex items-center gap-2.5 border-t border-border py-2.5">
                  <span className="w-14 shrink-0 text-[13.5px] font-semibold">{r.symbol}</span>
                  <span className="min-w-0 flex-1 font-mono text-[13.5px] font-semibold" style={{ color: "var(--viz-diverging-neg)" }}>
                    {idNum(r.drag_share * 100, 1)}% dari penurunan
                  </span>
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">{signedPct(r.return * 100)}</span>
                </div>
              ))}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Nilai = jumlah saham x harga penutupan Sectors.</p>
          <div className="my-4 h-px bg-border" />
        </>
      )}
      <div className="text-[13px] font-semibold">Saham besar vs seluruh pasar</div>
      {bigBeatsWhole && bestBig.change_since_peak < 0 && <p className="mt-0.5 text-xs leading-normal text-muted-foreground">{bestBig.code} turun paling sedikit sejak puncak IHSG.</p>}
      <div className="mt-2.5">
        {ma.indices.map((r) => (
          <div key={r.code} className="flex items-center gap-3 border-t border-border py-2.5">
            <div className="min-w-0 flex-1">
              <div className="text-[14.5px] font-semibold">{r.code}</div>
              <div className="text-xs text-muted-foreground">{r.label}</div>
            </div>
            <div className="w-20 shrink-0 text-right">
              <div className="font-mono text-[14.5px] font-bold" style={{ color: tone(r.change_since_peak) }}>
                {signedPct(r.change_since_peak * 100)}
              </div>
              <div className="text-[10.5px] text-muted-foreground">sejak puncak</div>
            </div>
            <div className="w-20 shrink-0 text-right">
              <div className="font-mono text-[14.5px] font-bold" style={{ color: tone(r.change_1y) }}>
                {signedPct(r.change_1y * 100)}
              </div>
              <div className="text-[10.5px] text-muted-foreground">setahun</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );

  const largeCaps = (
    <section className={cardCls}>
      <div>
        <div className={eyebrowCls}>100 saham terbesar</div>
        <div className="mt-0.5 text-xs text-muted-foreground">
          Sejak puncak IHSG, {formatDateId(ma.peak_window.start)} sampai {formatDateId(ma.peak_window.end)}
        </div>
      </div>
      <p className="mt-2.5 text-[15px] font-semibold leading-snug">
        {ma.large_caps.n_up} dari {ma.large_caps.n} justru naik{ma.large_caps.n_producer > 0 ? `; ${ma.large_caps.n_producer} di antaranya produsen komoditas.` : "."}
      </p>
      <p className="mt-1 text-[13px] leading-normal text-muted-foreground">
        {ma.large_caps.n_producer > 0 && "Batu bara, emas dan logam, minyak, serta perkebunan. "}
        Saham tipikal dari {ma.large_caps.n} ini {signedPct(ma.large_caps.median_return * 100)}.
      </p>
      <div className="mt-1">
        {ma.large_caps.up.slice(0, 5).map((r) => (
          <Row
            key={r.symbol}
            href={`/saham/${r.symbol}`}
            title={r.symbol}
            line={shortName(r.company_name)}
            trailing={
              <span className="font-mono text-base font-bold tabular-nums" style={{ color: "var(--viz-diverging-pos)" }}>
                {signedPct(r.return * 100, 1, true)}
              </span>
            }
          />
        ))}
      </div>
      <p className="mt-2.5 text-xs text-muted-foreground">Mencatat yang sudah terjadi, bukan daftar pilihan.</p>
    </section>
  );

  const topMoves = rankings.biggest_daily_moves.slice(0, 3);
  const hariIni = (
    <section>
      <H2>Saham hari ini</H2>
      <Sub>Pergerakan terbesar, {formatDateId(market.as_of)}.</Sub>
      <div className="mt-1.5">
        {topMoves.map((m) => {
          const up = m.daily_close_change >= 0;
          const Arrow = up ? ArrowUp : ArrowDown;
          const color = up ? "var(--viz-diverging-pos)" : "var(--viz-diverging-neg)";
          return (
            <Row
              key={m.symbol}
              href={`/saham/${m.symbol}`}
              icon={<Arrow className="size-4" style={{ color }} />}
              title={m.symbol}
              line={shortName(m.company_name)}
              trailing={
                <span className="font-mono text-base font-bold tabular-nums" style={{ color }}>
                  {signedPct(m.daily_close_change * 100, 1, true)}
                </span>
              }
            />
          );
        })}
      </div>
      <TextLink href="/temuan/peringkat/pergerakan">Lihat semua pergerakan</TextLink>
    </section>
  );

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <PageTitle title="Pasar" pill={`Data ${formatDateId(market.as_of)}`} />
      <Sub>Kondisi pasar saham Indonesia hari ini.</Sub>
      <div className="mt-4 md:mt-5">{kondisi}</div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {total}
        {jarak}
      </div>
      <div className="mt-9 space-y-5">
        {sejakPuncak}
        {largeCaps}
      </div>
      <div className="mt-9">{sektor}</div>
      <div className="mt-9 grid gap-9 md:grid-cols-2 md:gap-x-10">
        {tanda}
        {hariIni}
      </div>
    </main>
  );
}
