import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight, Info, Pause, Star } from "lucide-react";
import { BackLink } from "@/components/back-link";
import { DatePill } from "@/components/kit";
import { RecentTracker } from "@/components/recent-tracker";
import { DataLengkap } from "@/components/saham/data-lengkap";
import { ICONS, NoteBox, PriceRange, RingkasanCard, SectionCard, SignalsSection, TwoFigures, WatchSection, YearColumns, amountUnit } from "@/components/saham/parts";
import { PantauButton } from "@/components/saham/pantau";
import { PurposeAnswer, PurposeChips } from "@/components/saham/purpose";
import { TanyaCard } from "@/components/saham/tanya-card";
import { dateLong } from "@/lib/dates";
import { getFindingsData } from "@/lib/findings-data";
import { formatDateId, formatPrice, idNum, shortName } from "@/lib/format";
import { getAllStockCodes, getStockData, getStocksAsOf } from "@/lib/stock-data";
import { WATCH_ORDER, agenda, answers, dividenLine, hargaLine, labaSeriesLine, pctPlain, pctSigned, popularSignals, ringkasan, roeLine, sizeLine, tanyaSuggestions, watchItems } from "@/lib/stock-read";
import { getPeerBanks, getReadInput } from "@/lib/stock-read-data";

export async function generateStaticParams() {
  const codes = await getAllStockCodes();
  return codes.map((kode) => ({ kode }));
}

const BOARD_ID: Record<string, string> = { Acceleration: "Akselerasi", Main: "Utama", Development: "Pengembangan", Watchlist: "Pemantauan Khusus" };
const tone = (x: number) => (x > 0 ? "var(--viz-diverging-pos)" : x < 0 ? "var(--viz-diverging-neg)" : "var(--foreground)");

/**
 * The stock page (boards Baru4-Saham-*): who the company is and its price,
 * the "why are you looking" chips, a Ringkasan with one state label per
 * part, the popular signals present in this stock with their test result,
 * the situations to note, the price / profit / dividend cards, Tanya with
 * the stock attached, and every raw number under "Data lengkap". Each part
 * stands on its own; nothing is combined into a score.
 */
export default async function StockPage(props: PageProps<"/saham/[kode]">) {
  const { kode } = await props.params;
  const data = await getStockData(kode);
  if (!data) notFound();
  const code = data.snapshot.symbol.replace(".JK", "");
  const r = await getReadInput(code, data);
  if (!r) notFound();
  const [asOf, findings, peers] = await Promise.all([getStocksAsOf(), getFindingsData(), data.lens_banking ? getPeerBanks(code) : Promise.resolve([])]);

  const { snapshot, lens_banking } = data;
  const p = r.profile;
  const watch = watchItems(r);
  const signals = popularSignals(r, watch);
  const ring = ringkasan(r, watch);
  const ans = answers(r, watch);
  const price = snapshot.last_close_price;
  const low = snapshot["52_w_low_price"];
  const high = snapshot["52_w_high_price"];
  const daily = p.daily_close_change;
  const size = sizeLine(r);

  /* ---------------- header */
  const identity = (
    <div>
      <div className="flex items-start gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-accent text-sm font-bold text-accent-foreground md:size-14 md:rounded-2xl md:text-base">{code.slice(0, 2)}</span>
        <div className="min-w-0 flex-1">
          <h1 className="text-[26px] font-bold leading-tight tracking-[-0.02em] md:text-[40px]">{code}</h1>
          <p className="mt-0.5 text-[13px] leading-snug text-muted-foreground md:text-[15px]">
            {shortName(snapshot.company_name)}
            {r.sector ? ` · ${r.sector}` : ""}
          </p>
        </div>
        <span className="hidden md:inline">
          <DatePill>Data {formatDateId(asOf)}</DatePill>
        </span>
      </div>
      <div className="mt-4 flex items-end justify-between gap-3">
        {price !== null ? (
          <div>
            <div className="font-mono text-[30px] font-bold leading-none tracking-[-0.02em] tabular-nums md:text-[44px]">{formatPrice(price)}</div>
            <div className="mt-2 text-[13px] md:text-[14px]">
              {daily !== null && (
                <span className="font-mono font-bold tabular-nums" style={{ color: tone(daily) }}>
                  {pctSigned(daily)}
                </span>
              )}{" "}
              <span className="text-muted-foreground">pada {formatDateId(asOf)}</span>
            </div>
          </div>
        ) : (
          <div className="text-[13px] text-muted-foreground">Harga terakhir tidak tercatat.</div>
        )}
        <div className="lg:hidden">
          <PantauButton symbol={code} companyName={snapshot.company_name} />
        </div>
      </div>
      {size && <p className="mt-3 text-[13px] text-muted-foreground md:text-[14px]">{size}</p>}
    </div>
  );

  const susp = r.situations?.recent_price_suspension;
  const ipo = r.situations?.recent_ipo;
  const repeat = r.situations?.repeat_suspension;
  const banner = susp ? (
    <div className="mt-4 flex gap-3 rounded-[14px] border px-4 py-3.5 text-[13.5px] leading-normal" style={{ borderColor: "color-mix(in srgb, var(--viz-status-warning) 45%, transparent)", background: "color-mix(in srgb, var(--viz-status-warning) 10%, transparent)" }}>
      <Pause className="mt-px size-[18px] shrink-0" style={{ color: "var(--viz-status-warning)" }} />
      <div>
        <b>Disuspensi bursa {dateLong(susp.date)}</b> karena lonjakan harga.{repeat ? ` Ini suspensi ke-${repeat.n_events} sejak ${dateLong(repeat.first_date)}.` : ""}{" "}
        <a href={susp.pdf_url} target="_blank" rel="noopener noreferrer" className="underline">
          Pengumuman IDX
        </a>
      </div>
    </div>
  ) : ipo ? (
    <div className="mt-4 flex gap-3 rounded-[14px] border border-border bg-[var(--viz-raised)] px-4 py-3.5 text-[13.5px] leading-normal">
      <Info className="mt-px size-[18px] shrink-0 text-[var(--viz-accent)]" />
      <div>
        <b>Baru melantai {dateLong(ipo.listing_date)}</b> di Papan {BOARD_ID[ipo.board] ?? ipo.board}. Sebagian angka di halaman ini belum bisa dihitung karena riwayatnya belum setahun penuh.
      </div>
    </div>
  ) : null;

  const items = agenda(r);
  const pantau = (
    <section className="rounded-[20px] border border-border bg-card p-5">
      <div className="flex items-center gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-[9px] bg-accent text-accent-foreground">
          <Star className="size-4" strokeWidth={1.7} />
        </span>
        <h2 className="text-[17px] font-bold leading-tight">Pantau {code}</h2>
      </div>
      <p className="mt-2.5 text-[13.5px] leading-normal text-muted-foreground">Simpan {code} di Watchlist. Kami tandai di sana saat ada yang berubah: keadaan baru, dividen, RUPS, suspensi, atau laporan orang dalam.</p>
      {items.length > 0 && (
        <div className="mt-3">
          <div className="text-xs font-semibold text-muted-foreground">Jadwal tercatat</div>
          <div className="mt-1.5 flex flex-col gap-2">
            {items.map((a) => (
              <div key={`${a.date}-${a.label}`} className="flex gap-2 text-[13px]">
                <span className="w-[84px] shrink-0 font-mono tabular-nums text-muted-foreground">{formatDateId(a.date)}</span>
                <span>
                  {a.label}
                  {a.past ? <span className="text-muted-foreground">, sudah lewat</span> : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      <PantauButton symbol={code} companyName={snapshot.company_name} wide />
    </section>
  );

  /* ---------------- price, profit, dividend */
  const chg = p.change_1y;
  const rank = p.sector_rank_1y;
  const hLine = hargaLine(r);
  const harga = (
    <SectionCard icon={ICONS.harga} title={`Harga ${code}`} right={<DatePill>setahun</DatePill>}>
      {price !== null && low !== null && high !== null && high > low && <PriceRange low={low} high={high} price={price} lowDate={p.w52_low_date} highDate={p.w52_high_date} />}
      {hLine && <p className="mt-3.5 text-sm leading-[1.55]">{hLine}</p>}
      {chg !== null && (
        <>
          <TwoFigures
            items={[
              { value: pctSigned(chg), caption: `${code}, setahun`, color: tone(chg) },
              { value: pctSigned(r.meta.ihsg_change_1y), caption: "IHSG, setahun", color: tone(r.meta.ihsg_change_1y) },
            ]}
          />
          {rank && rank.n > 1 && (
            <p className="mt-2.5 text-[13px] text-muted-foreground">
              <b className="font-mono tabular-nums text-foreground">
                {rank.better} dari {rank.n}
              </b>{" "}
              saham {r.sector ? r.sector.toLowerCase() : "di sektornya"} bergerak lebih baik.
            </p>
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Setahun: {dateLong(r.meta.change_window.start)} sampai {dateLong(r.meta.change_window.end)}, harga penutupan dari Sectors.
          </p>
        </>
      )}
    </SectionCard>
  );

  const earningsKnown = p.earnings.some((v) => v !== null);
  const eu = amountUnit(p.earnings);
  const laba = earningsKnown ? (
    <div>
      <div className="mt-3 text-xs text-muted-foreground">Laba bersih per tahun ({eu.unit})</div>
      <div className="mt-2">
        <YearColumns values={p.earnings} years={r.meta.years} format={eu.format} label={`Laba bersih ${code} per tahun`} />
      </div>
      {labaSeriesLine(r) && <p className="mt-3 text-sm leading-[1.55]">{labaSeriesLine(r)}</p>}
      {roeLine(r) && <p className="mt-2 text-sm leading-[1.55]">{roeLine(r)}</p>}
    </div>
  ) : (
    <div className="mt-2">
      <NoteBox>Belum ada laporan laba tahunan untuk {code}.</NoteBox>
    </div>
  );

  const bankRatios = lens_banking
    ? (
        [
          ["net_interest_margin[2025]", "Selisih bunga (NIM)"],
          ["npl_ratio", "Kredit macet (NPL)"],
          ["casa_ratio[2025]", "Dana murah (CASA)"],
          ["capital_adequacy_ratio[2025]", "Kecukupan modal (CAR)"],
        ] as const
      )
        .map(([k, label]) => ({ label, v: lens_banking.ratios[k] }))
        .filter((x) => x.v !== null)
    : [];
  const bisnis = lens_banking ? (
    <SectionCard icon={ICONS.bank} title={`Bank ${code}`} sub="Untuk bank, angka-angka ini lebih berarti dari utang dibanding modal.">
      {bankRatios.length > 0 && (
        <div className="grid grid-cols-2 gap-x-5">
          {bankRatios.map(({ label, v }) => (
            <div key={label} className="border-b border-border py-3">
              <div className="font-mono text-xl font-bold leading-tight tabular-nums">{idNum(v!.value * 100, 1)}%</div>
              <div className="mt-0.5 text-[13px]">{label}</div>
              <div className="text-xs text-muted-foreground">
                lebih baik dari {v!.better_than_count} dari {v!.comparable_count} bank
              </div>
            </div>
          ))}
        </div>
      )}
      {laba}
      {peers.length > 0 && (
        <>
          <div className="mt-[18px] text-sm font-semibold">Bank besar lain</div>
          {peers.map((b) => (
            <Link key={b.code} href={`/saham/${b.code}`} className="flex items-center gap-3 border-b border-border py-3 last:border-0">
              <span className="w-12 shrink-0 text-sm font-bold">{b.code}</span>
              <span className="min-w-0 flex-1 text-[12.5px] leading-snug text-muted-foreground">
                {b.pe !== null ? `P/E ${idNum(b.pe)}x` : "P/E tidak bermakna"}
                {b.yield !== null && b.yield > 0 ? ` · dividen ${pctPlain(b.yield)}` : ""}
              </span>
              {b.change1y !== null && (
                <span className="shrink-0 text-right">
                  <span className="block font-mono text-[13px] font-semibold tabular-nums" style={{ color: tone(b.change1y) }}>
                    {pctSigned(b.change1y)}
                  </span>
                  <span className="block text-[11px] text-muted-foreground">setahun</span>
                </span>
              )}
              <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
            </Link>
          ))}
        </>
      )}
    </SectionCard>
  ) : (
    <SectionCard icon={ICONS.laba} title={`Laba ${code}`}>
      {laba}
    </SectionCard>
  );

  const paidAny = p.dividend.some((v) => v !== null && v > 0);
  const dividen = (
    <SectionCard icon={ICONS.dividen} title={`Dividen ${code}`}>
      {paidAny ? (
        <>
          <div className="mt-3 text-xs text-muted-foreground">Dividen per saham (Rp)</div>
          <div className="mt-2">
            <YearColumns values={p.dividend.map((v) => (v !== null && v > 0 ? v : null))} years={r.meta.years} format={(v) => idNum(v, v < 10 ? 2 : 0)} label={`Dividen per saham ${code} per tahun`} />
          </div>
          <p className="mt-3 text-sm leading-[1.55]">{dividenLine(r)}</p>
        </>
      ) : (
        <div className="mt-2">
          <NoteBox>
            {dividenLine(r)}
            {(p.earnings[p.earnings.length - 1] ?? 0) < 0 ? " Perusahaan rugi umumnya tidak membagikan dividen." : ""}
          </NoteBox>
        </div>
      )}
    </SectionCard>
  );

  const news = r.news;
  const suggestions = tanyaSuggestions(r);

  // Two columns from lg up. The left is the reading column and takes the
  // space (size = hierarchy): summary, popular signals, situations to note.
  // The right is a fixed, narrower supporting column. Space = grouping: 32px
  // between sections on the left, 20px between the smaller cards on the right.
  const cols = "lg:grid lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start lg:gap-10";
  return (
    <main className="mx-auto w-full max-w-[1320px] px-4 py-5 md:px-8 md:py-8">
      <RecentTracker code={code} />
      <BackLink fallback={{ href: "/", label: "Beranda" }} />
      <div className={cols}>
        <div className="min-w-0">
          {identity}
          {banner}
          <PurposeChips code={code} />
        </div>
        <div className="hidden min-w-0 lg:block">{pantau}</div>
      </div>
      <PurposeAnswer code={code} answers={ans} />
      <div className={`mt-8 lg:mt-10 ${cols}`}>
        <div className="flex min-w-0 flex-col gap-6 md:gap-8">
          <RingkasanCard code={code} lead={ring.lead} rows={ring.rows} />
          <SignalsSection code={code} signals={signals} findingsCount={findings.scoreboard.length} />
          <WatchSection code={code} items={watch} checked={WATCH_ORDER.length} />
        </div>
        <div className="mt-6 flex min-w-0 flex-col gap-5 md:mt-8 lg:mt-0">
          <TanyaCard code={code} suggestions={suggestions} className="hidden lg:block" />
          {harga}
          {bisnis}
          {dividen}
        </div>
      </div>
      <DataLengkap code={code} data={data} profile={p} meta={r.meta} sectorLabel={r.sector} news={news} newsMarket={r.newsMarket} className="mt-8 lg:mt-10" />
      <TanyaCard code={code} suggestions={suggestions} className="mt-6 lg:hidden" />
    </main>
  );
}
