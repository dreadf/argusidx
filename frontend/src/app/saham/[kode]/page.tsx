import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { CompareLines } from "@/components/charts/axis-charts";
import { RangeBar } from "@/components/charts/range-bar";
import { GlossaryTerm } from "@/components/glossary-term";
import { Card, Cells, DatePill, H2, Neg, Pos, ResearchNote, Stat, TextLink } from "@/components/kit";
import { RecentTracker } from "@/components/recent-tracker";
import { EmphasisStrip } from "@/components/viz/emphasis-strip";
import { WatchlistButton } from "@/components/watchlist-button";
import { formatDateId, formatPrice, idNum, pctFrom, signedPct } from "@/lib/format";
import { BackLink } from "@/components/back-link";
import { getInsiderSummary } from "@/lib/insider-data";
import { getNewsSentiment } from "@/lib/news-data";
import { getRoeHistory } from "@/lib/roe-data";
import { getSuspensionSummary } from "@/lib/suspensions-data";
import { sectorByKey } from "@/lib/sectors-id";
import { fiveYearPhrase, newsRelative, pricePosition, relativeToTypical, sizePhrase } from "@/lib/stock-summary";
import { getAllStockCodes, getStockData, getStocksAsOf } from "@/lib/stock-data";
import type { StockPageData } from "@/lib/stock-data";

export async function generateStaticParams() {
  const codes = await getAllStockCodes();
  return codes.map((kode) => ({ kode }));
}

const COMPANY_TYPE_ID: Record<string, string> = {
  Holding: "Induk usaha (holding)",
  Contractor: "Kontraktor tambang",
  "Mine Owner": "Pemilik tambang",
  Trader: "Pedagang komoditas",
};

const COMMODITY_ID: Record<string, string> = {
  Coal: "Batu bara",
  Nickel: "Nikel",
  Gold: "Emas",
  Copper: "Tembaga",
  Silver: "Perak",
  Aluminium: "Aluminium",
  "Zinc and Lead": "Seng dan Timbal",
};

const SIZE_BUCKET_ID: Record<string, string> = {
  smallest: "terkecil",
  small_mid: "kecil-menengah",
  mid_large: "menengah-besar",
  largest: "terbesar",
};

const MONTH_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

function formatMonthYear(iso: string): string {
  const [year, month] = iso.split("-");
  return `${MONTH_ID[Number(month) - 1] ?? month} ${year}`;
}

function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${Number(day)} ${MONTH_ID[Number(month) - 1] ?? month} ${year}`;
}

const FLOAT_TERCILE_ID: Record<string, string> = { low: "sepertiga tersempit", mid: "sepertiga tengah", high: "sepertiga terlebar" };

/**
 * H1 resolved to this specific stock (docs/PRODUCT.md §5.2), shortened for
 * the redesigned page. Four real states, no invented fifth, and always the
 * calendar-period caveat: the pattern was seen in 2024-2026, not 2022-2023.
 */
function h1Sentences(finding: NonNullable<StockPageData["h1_finding"]>, freeFloat: number | null): { lead: string; caveat: string } {
  const size = SIZE_BUCKET_ID[finding.size_bucket] ?? finding.size_bucket;
  const floatText = freeFloat === null ? "Free float" : `Free float ${idNum(freeFloat * 100)}%`;
  const caveat = "Teramati 2024-2026 saja, bukan 2022-2023. Bukan ramalan arah harga.";
  if (finding.state === "weaker_evidence_for_size_range") {
    return { lead: `Saham ini di kelompok ukuran ${size}, tempat hubungan free float dan gejolak harga tidak terbukti signifikan. Bukti lebih lemah, bukan berarti tidak berlaku.`, caveat };
  }
  if (finding.state === "risky_side") {
    return { lead: `${floatText} (saham beredar di publik), ${FLOAT_TERCILE_ID.high} untuk ukuran ${size}. Float lebar bersamaan dengan harga lebih bergejolak, bukan sebab.`, caveat };
  }
  if (finding.state === "calm_side") {
    return { lead: `${floatText} (saham beredar di publik), ${FLOAT_TERCILE_ID.low} untuk ukuran ${size}. Float sempit bersamaan dengan harga lebih tenang, bukan sebab.`, caveat };
  }
  return { lead: `${floatText} (saham beredar di publik), ${FLOAT_TERCILE_ID.mid} untuk ukuran ${size}. Tidak condong ke sisi lebih bergejolak maupun lebih tenang.`, caveat };
}

function Bold({ children }: { children: ReactNode }) {
  return <b className="font-semibold text-foreground">{children}</b>;
}

function Section({ title, sub, children }: { title: string; sub?: string; children: ReactNode }) {
  return (
    <section>
      <H2>{title}</H2>
      {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

const body = "text-sm leading-normal";
const fine = "mt-2 text-xs leading-normal text-muted-foreground";

export default async function StockPage(props: PageProps<"/saham/[kode]">) {
  const { kode } = await props.params;
  const data = await getStockData(kode);
  if (!data) notFound();

  const code = data.snapshot.symbol.replace(".JK", "");
  const [asOf, news, insiderMarket, allCodes, suspMarket] = await Promise.all([getStocksAsOf(), getNewsSentiment(), getInsiderSummary(), getAllStockCodes(), getSuspensionSummary()]);
  const { snapshot, peer_comparison, sector_context, flags, suspension_history, lens_banking, lens_extractive, beat_gold, h1_finding, insider_activity, corporate_actions } = data;
  const roe = await getRoeHistory(code, snapshot.sector);
  const sectorMeta = sectorByKey(snapshot.sector);
  const price = snapshot.last_close_price;
  const low = snapshot["52_w_low_price"];
  const high = snapshot["52_w_high_price"];
  const hasRange = price !== null && low !== null && high !== null && high > low;
  const distHigh = price !== null && high ? pctFrom(price, high) : null;
  const distLow = price !== null && low ? pctFrom(price, low) : null;
  const newsCounts = news.by_symbol[code];
  const newsTotal = newsCounts ? newsCounts.bullish + newsCounts.bearish : 0;
  const newsShare = newsTotal > 0 ? (newsCounts.bullish / newsTotal) * 100 : null;

  /* ---------------- Ringkasan: six short rows, each one comparison ---------------- */
  const rows: { label: string; text: ReactNode }[] = [];

  const pos = pricePosition(snapshot.position_in_52w_range);
  if (pos) {
    rows.push({
      label: "Harga",
      text: (
        <>
          <Bold>{pos}</Bold> rentang setahun. {distHigh !== null && <Neg>{signedPct(distHigh)}</Neg>}
          {distHigh !== null && " dari tertinggi."}
        </>
      ),
    });
  }
  const size = sizePhrase(snapshot.market_cap, snapshot.market_cap_rank, allCodes.length);
  if (size) rows.push({ label: "Ukuran", text: size });

  if (sector_context) {
    const parts: ReactNode[] = [];
    if (sector_context.own_roe_pct !== null && sector_context.sector_typical_roe_pct !== null) {
      parts.push(
        <span key="roe">
          Laba dibanding modal (<GlossaryTerm term="roe">ROE</GlossaryTerm>) {idNum(sector_context.own_roe_pct)}%, <Bold>{relativeToTypical(sector_context.own_roe_pct, sector_context.sector_typical_roe_pct)}</Bold> sektor ({idNum(sector_context.sector_typical_roe_pct)}%).{" "}
        </span>,
      );
    }
    if (sector_context.own_pe !== null && sector_context.sector_typical_pe !== null) {
      parts.push(
        <span key="pe">
          Harga dibanding laba (<GlossaryTerm term="pe_ratio">P/E</GlossaryTerm>) {idNum(sector_context.own_pe)}x, <Bold>{relativeToTypical(sector_context.own_pe, sector_context.sector_typical_pe)}</Bold> sektor ({idNum(sector_context.sector_typical_pe)}x).
        </span>,
      );
    }
    if (parts.length > 0) rows.push({ label: "Laba dan valuasi", text: <>{parts}</> });
  }

  if (newsShare !== null && newsTotal >= 5) {
    rows.push({
      label: "Berita",
      text: (
        <>
          {idNum(newsShare, 0)}% bullish, <Bold>{newsRelative(newsShare, news.bullish_mentions_pct)}</Bold> rata-rata semua saham ({idNum(news.bullish_mentions_pct, 0)}%).
        </>
      ),
    });
  } else {
    rows.push({ label: "Berita", text: "Belum cukup berita tercatat untuk dibandingkan." });
  }

  rows.push({
    label: "Tanda",
    text: flags.length === 0 ? <><Bold>Tidak ada tanda</Bold> dari 4 jenis.</> : <><Bold>{flags.length} tanda</Bold>: {flags[0].label.toLowerCase()}{flags.length > 1 ? `, dan ${flags.length - 1} lainnya` : ""}.</>,
  });

  if (beat_gold) {
    const { won, lost } = fiveYearPhrase(beat_gold);
    if (won.length + lost.length > 0) {
      rows.push({
        label: "Lima tahun",
        text: (
          <>
            {won.length > 0 && (
              <>
                <Bold>Menang</Bold> dari {won.join(" dan ")}
              </>
            )}
            {won.length > 0 && lost.length > 0 && ", "}
            {lost.length > 0 && (
              <>
                <Bold>kalah</Bold> dari {lost.join(" dan ")}
              </>
            )}
            .
          </>
        ),
      });
    }
  }

  const ringkasan = (
    <section aria-label="Ringkasan" className="overflow-hidden rounded-[20px] border border-[var(--viz-accent)] bg-card">
      <div className="px-[18px] pt-[18px] md:px-[22px]">
        <span className="inline-flex rounded-full bg-accent px-3 py-1.5 text-[11.5px] font-bold uppercase tracking-[0.06em] text-accent-foreground">Ringkasan</span>
      </div>
      <div className="mt-3 grid border-t border-border md:grid-cols-3">
        {rows.map((r, i) => (
          <div key={r.label} className={`flex gap-3 px-[18px] py-3 md:block md:px-[22px] md:py-4 ${i > 0 ? "border-t border-border" : ""} ${i % 3 !== 0 ? "md:border-l md:border-border" : ""} ${i < 3 ? "md:border-t-0" : ""}`}>
            <div className="w-[84px] shrink-0 text-[12.5px] font-semibold text-[var(--viz-accent)] md:w-auto">{r.label}</div>
            <div className="min-w-0 flex-1 text-sm leading-normal md:mt-1.5 md:text-[14.5px]">{r.text}</div>
          </div>
        ))}
      </div>
      {rows.some((r) => r.label === "Lima tahun") && <ResearchNote className="border-t border-border px-[18px] py-2.5 md:px-[22px]" />}
    </section>
  );

  /* ---------------- sections ---------------- */
  const harga = price !== null && (
    <Section title="Harga setahun terakhir">
      <div className="font-mono text-[22px] font-bold tabular-nums">{formatPrice(price)}</div>
      {distHigh !== null && (
        <div className="mt-1 text-[13px]">
          <Neg>{signedPct(distHigh)}</Neg> dari tertinggi{distLow !== null && <> &middot; <Pos>{signedPct(distLow, 1, true)}</Pos> dari terendah</>}
        </div>
      )}
      {hasRange ? <RangeBar low={low} high={high} price={price} /> : <p className={fine}>Harga tertinggi dan terendah setahun sama, atau datanya tidak lengkap, jadi posisi tidak bisa dihitung.</p>}
    </Section>
  );

  const sektor = (
    <Section title={sectorMeta ? `Dibanding sektor ${sectorMeta.label}` : "Dibanding sektor"}>
      {sector_context ? (
        <>
          <Cells>
            {[
              <Stat key="r" value={sector_context.own_roe_pct === null ? "-" : `${idNum(sector_context.own_roe_pct)}%`} label={`laba dibanding modal (ROE), sektor ${sector_context.sector_typical_roe_pct === null ? "-" : idNum(sector_context.sector_typical_roe_pct) + "%"}`} size={24} />,
              <Stat key="p" value={sector_context.own_pe === null ? "-" : `${idNum(sector_context.own_pe)}x`} label={`harga dibanding laba (P/E), sektor ${sector_context.sector_typical_pe === null ? "-" : idNum(sector_context.sector_typical_pe) + "x"}`} size={24} />,
            ]}
          </Cells>
          <p className={fine}>
            Nilai tipikal sektor: nilai tengah dari yang melapor ({sector_context.sector_roe_n} dari {sector_context.sector_company_count} untuk ROE). Bukan peringkat antar sektor.{" "}
            <Link href="/jelajah/sektor" className="underline">
              Lihat semua sektor
            </Link>
          </p>
        </>
      ) : (
        <p className={fine}>Sektor saham ini belum diketahui.</p>
      )}
      {peer_comparison !== null && peer_comparison.own_value !== null && peer_comparison.comparable_count !== null && peer_comparison.comparable_count > 0 && peer_comparison.better_than_count !== null && (
        <div className="mt-4">
          <p className={body}>
            <GlossaryTerm term="roe">ROE</GlossaryTerm> lebih tinggi dari {peer_comparison.better_than_count} dari {peer_comparison.comparable_count} perusahaan sejenis di <GlossaryTerm term="peer_group">kelompok pembanding</GlossaryTerm> <b>{peer_comparison.group}</b>.
          </p>
          <div className="mt-3">
            <EmphasisStrip betterThanCount={peer_comparison.better_than_count} comparableCount={peer_comparison.comparable_count} lowLabel="ROE lebih rendah" highLabel="ROE lebih tinggi" />
            <p className="mt-1 text-xs text-muted-foreground">Titik terang: perusahaan ini. Titik abu-abu: {peer_comparison.comparable_count} perusahaan sejenis, dari ROE terendah ke tertinggi.</p>
          </div>
        </div>
      )}
      {peer_comparison !== null && peer_comparison.own_value === null && (
        <p className={fine}>Data ROE perusahaan ini tidak tersedia, jadi tidak bisa dibandingkan dengan {peer_comparison.peer_count} perusahaan sejenis di {peer_comparison.group}.</p>
      )}
      {peer_comparison === null && <p className={fine}>Belum bisa dikelompokkan dengan perusahaan sejenis.</p>}
      {roe && roe.own.some((v) => v !== null && Math.abs(v) > 150) && (
        <p className={fine}>ROE perusahaan ini sangat jauh di luar kisaran biasa (di atas 150% atau di bawah -150% pada salah satu tahun), biasanya karena modalnya hampir habis atau negatif. Grafiknya tidak ditampilkan supaya skalanya tidak menyesatkan.</p>
      )}
      {roe && !roe.own.some((v) => v !== null && Math.abs(v) > 150) && (
        <div className="mt-5">
          <div className="text-[15px] font-semibold">Laba dibanding modal (ROE) per tahun</div>
          <Card className="mt-2.5 px-3 pb-3 pt-4">
            <CompareLines
              years={roe.years}
              own={roe.own}
              sector={roe.sector}
              ownLabel={code}
              sectorLabel="Nilai tengah sektor"
              yTitle="ROE (%)"
              xTitle="Tahun laporan"
              label={`ROE ${code} per tahun dibanding nilai tengah sektor`}
            />
            <p className="mx-2 mt-1.5 text-xs text-muted-foreground">Bukan grafik harga. ROE tahunan dari laporan; angka di atas memakai 12 bulan terakhir, jadi bisa sedikit berbeda.</p>
          </Card>
        </div>
      )}
    </Section>
  );

  const berita = (
    <Section title="Berita" sub={`${newsTotal > 0 ? idNum(newsTotal, 0) : "0"} berita, ${formatDateId(news.first_date)} sampai ${formatDateId(news.last_date)}`}>
      {newsTotal > 0 && newsShare !== null ? (
        <Card className="p-[18px]">
          <Cells>{[<Stat key="b" value={newsCounts.bullish} label="bullish" tone="pos" size={26} />, <Stat key="r" value={newsCounts.bearish} label="bearish" tone="neg" size={26} />]}</Cells>
          <p className="mt-3.5 text-[13.5px] leading-normal">
            {idNum(newsShare, 0)}% bullish, rata-rata semua saham {idNum(news.bullish_mentions_pct, 0)}%.
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Tanda bullish atau bearish dari Sectors, bukan dari kami.</p>
          <TextLink href="/temuan?hasil=tidak-konsisten">Apakah berita memprediksi kenaikan? Belum jelas</TextLink>
        </Card>
      ) : (
        <p className={fine}>Tidak ada berita yang menyebut saham ini pada periode data.</p>
      )}
    </Section>
  );

  const h1 = h1_finding ? h1Sentences(h1_finding, snapshot.free_float) : null;
  const temuan = (
    <Section title="Temuan untuk saham ini">
      <Card className="p-[18px]">
        {h1 ? (
          <>
            <span className="mb-2.5 inline-flex rounded-full bg-accent px-2.5 py-1 text-[11.5px] font-semibold text-accent-foreground">Free float</span>
            <p className="text-sm leading-normal">{h1.lead}</p>
            <p className="mt-2 border-t border-border pt-2 text-xs text-muted-foreground">{h1.caveat}</p>
          </>
        ) : (
          <p className={body}>Belum bisa ditempatkan di kelompok ukuran dan kepemilikan publik untuk temuan ini (data nilai pasar atau free float tidak lengkap).</p>
        )}
        <p className="mt-2 text-xs text-muted-foreground">Temuan lain (nilai murah, pemotongan dividen, dan lainnya) berlaku umum di pasar, bukan dihitung khusus untuk saham ini.</p>
        <TextLink href="/temuan">Lihat semua temuan</TextLink>
      </Card>
    </Section>
  );

  const insider = (
    <Section title="Transaksi insider" sub={`Direksi, komisaris dan pemegang besar, ${insiderMarket.window.start.slice(0, 4)} sampai ${String(insiderMarket.window.end).slice(0, 4)}`}>
      <Card className="p-[18px]">
        {insider_activity ? (
          <p className="text-sm leading-normal">
            <b>
              {snapshot.symbol.replace(".JK", "")}{" "}
              {insider_activity.net_direction === "net_buying" ? "pembeli bersih" : insider_activity.net_direction === "net_selling" ? "penjual bersih" : "seimbang"}
            </b>
            : {insider_activity.buy_count} pembelian, {insider_activity.sell_count} penjualan{insider_activity.last_transaction_date ? `, terakhir ${formatDate(insider_activity.last_transaction_date)}` : ""}.
          </p>
        ) : (
          <p className="text-sm leading-normal">Tidak ada transaksi insider tercatat untuk saham ini pada periode data.</p>
        )}
        <div className="mb-2 mt-3.5 text-xs text-muted-foreground">Dari {idNum(insiderMarket.companies_with_activity, 0)} saham dengan catatan insider</div>
        <Cells>
          {[
            <Stat key="b" value={insiderMarket.net_buying} label="pembeli bersih" tone="pos" size={22} />,
            <Stat key="s" value={insiderMarket.net_selling} label="penjual bersih" tone="neg" size={22} />,
            <Stat key="e" value={insiderMarket.balanced} label="seimbang" size={22} />,
          ]}
        </Cells>
        <div className="my-3.5 h-px bg-border" />
        <p className="text-[13px] leading-normal text-muted-foreground">
          Insider menjual sebelum lonjakan sebagai tanda akan anjlok: <b className="text-foreground">tidak terbukti</b> saat diuji (4 kejadian).
        </p>
        <TextLink href="/temuan?hasil=tidak-terbukti">Lihat temuannya</TextLink>
      </Card>
    </Section>
  );

  const suspensi = (
    <Section title="Tanda dan riwayat suspensi">
      {flags.length === 0 ? (
        <p className={body}>Tidak ada tanda dari 4 jenis yang terdeteksi saat ini.</p>
      ) : (
        <ul className={`${body} space-y-1`}>
          {flags.map((flag) => (
            <li key={flag.key}>&bull; {flag.label}</li>
          ))}
        </ul>
      )}
      {suspension_history ? (
        <div className="mt-3 border-t border-border pt-3">
          <p className={`${body} mb-2`}>
            <b>Pernah <GlossaryTerm term="suspensi">disuspensi</GlossaryTerm> {suspension_history.count}x</b>, lebih sering dari {suspension_history.more_than_pct}% perusahaan ({idNum(suspension_history.universe_count, 0)} perusahaan). {idNum(suspension_history.base_rate_pct)}% perusahaan IDX pernah disuspensi setidaknya sekali.
          </p>
          <ul className="space-y-2 text-sm">
            {suspension_history.events.slice(0, 5).map((s) => (
              <li key={s.date}>
                <span className="text-foreground">{formatDateId(s.date)}</span>: <span className="text-foreground">{s.category_label_id}</span>
                <span className="block text-xs text-muted-foreground">{s.reason}</span>
              </li>
            ))}
          </ul>
          {suspension_history.count > 5 && <p className={fine}>Menampilkan 5 dari {suspension_history.count} riwayat suspensi.</p>}
        </div>
      ) : (
        <p className={`${body} mt-3 border-t border-border pt-3`}>
          <b>{code} belum pernah disuspensi.</b> Dari {idNum(suspMarket.universe_count, 0)} perusahaan, {idNum(suspMarket.companies_with_suspensions, 0)} pernah ({Math.round(suspMarket.base_rate_pct)} dari 100).
        </p>
      )}
      <TextLink href="/situasi/pernah-disuspensi">Lihat alasan suspensi</TextLink>
    </Section>
  );

  const lensBank = lens_banking && (
    <Section title="Sudut pandang perbankan" sub="Bank dinilai dengan ukuran berbeda: seberapa murah dananya dan seberapa sehat pinjamannya.">
      <ul className={`${body} space-y-1.5`}>
        {lens_banking.ratios["casa_ratio[2025]"] && (
          <li>
            Dana murah (<GlossaryTerm term="casa_ratio">CASA</GlossaryTerm>) lebih tinggi dari {lens_banking.ratios["casa_ratio[2025]"].better_than_count} dari {lens_banking.ratios["casa_ratio[2025]"].comparable_count} bank lain ({idNum(lens_banking.ratios["casa_ratio[2025]"].value * 100)}%)
          </li>
        )}
        {lens_banking.ratios.npl_ratio && (
          <li>
            Kredit bermasalah (<GlossaryTerm term="npl_ratio">NPL</GlossaryTerm>) lebih rendah dari {lens_banking.ratios.npl_ratio.better_than_count} dari {lens_banking.ratios.npl_ratio.comparable_count} bank lain ({idNum(lens_banking.ratios.npl_ratio.value * 100, 2)}%)
          </li>
        )}
        {lens_banking.ratios["capital_adequacy_ratio[2025]"] && (
          <li>
            Kecukupan modal (<GlossaryTerm term="capital_adequacy_ratio">CAR</GlossaryTerm>) lebih tinggi dari {lens_banking.ratios["capital_adequacy_ratio[2025]"].better_than_count} dari {lens_banking.ratios["capital_adequacy_ratio[2025]"].comparable_count} bank lain ({idNum(lens_banking.ratios["capital_adequacy_ratio[2025]"].value * 100)}%)
          </li>
        )}
        {lens_banking.ratios["net_interest_margin[2025]"] && (
          <li>
            Margin bunga bersih (<GlossaryTerm term="net_interest_margin">NIM</GlossaryTerm>) lebih tinggi dari {lens_banking.ratios["net_interest_margin[2025]"].better_than_count} dari {lens_banking.ratios["net_interest_margin[2025]"].comparable_count} bank lain ({idNum(lens_banking.ratios["net_interest_margin[2025]"].value * 100)}%)
          </li>
        )}
      </ul>
      <div className="mt-3 border-t border-border pt-3 text-sm text-muted-foreground">
        {lens_banking.loan_to_deposit_ratio !== null && (
          <p>
            Rasio kredit terhadap dana pihak ketiga (<GlossaryTerm term="loan_to_deposit_ratio">LDR</GlossaryTerm>): <span className="text-foreground">{idNum(lens_banking.loan_to_deposit_ratio * 100, 0)}%</span>. Terlalu rendah maupun terlalu tinggi punya artinya masing-masing, jadi tidak dibandingkan sebagai lebih baik atau buruk.
          </p>
        )}
        {lens_banking.loan_growth !== null && (
          <p className="mt-1">
            <GlossaryTerm term="loan_growth">Pertumbuhan kredit</GlossaryTerm> tahun ini: {idNum(lens_banking.loan_growth * 100)}%
          </p>
        )}
      </div>
    </Section>
  );

  const lensMining = lens_extractive && (
    <Section title="Eksposur komoditas">
      <p className={body}>
        {COMPANY_TYPE_ID[lens_extractive.company_type ?? ""] ?? lens_extractive.company_type ?? "Perusahaan tambang"}
        {lens_extractive.commodity_type.length > 0 && (
          <>
            , terkait <GlossaryTerm term="commodity_exposure">komoditas</GlossaryTerm> {lens_extractive.commodity_type.map((c) => COMMODITY_ID[c] ?? c).join(", ")}
          </>
        )}
        .
      </p>
      {lens_extractive.commodity_trends.length > 0 && (
        <>
          <ul className={`${body} mt-2 space-y-1`}>
            {lens_extractive.commodity_trends.map((trend) => (
              <li key={trend.commodity}>
                &bull; Harga {COMMODITY_ID[trend.commodity] ?? trend.commodity} pada data terakhir ({formatMonthYear(trend.latest_date)}):{" "}
                {trend.change_12m_pct !== null ? (
                  <>
                    <span className="font-mono">{signedPct(trend.change_12m_pct, 1, true)}</span> dibanding 12 bulan sebelumnya
                  </>
                ) : (
                  "belum cukup riwayat untuk perbandingan 12 bulan"
                )}
                {trend.position_in_range !== null && `, berada di ${(trend.position_in_range * 100).toFixed(0)}% antara titik terendah dan tertinggi sejak ${formatMonthYear(trend.range_start)}`}.
              </li>
            ))}
          </ul>
          <p className={fine}>
            Riwayat harga komoditas dari Sectors berakhir pada tanggal yang tertera, yang bisa berbeda dari tanggal data saham di halaman ini. Ini konteks tentang komoditasnya, bukan prediksi harga saham perusahaan ini.
          </p>
        </>
      )}
      <p className={fine}>
        Ini fakta keterkaitan komoditas, bukan perbandingan dengan perusahaan tambang lain: data reservasi, produksi, dan ekspor yang tersedia hanya angka nasional, bukan per perusahaan, jadi tidak bisa dijadikan dasar perbandingan yang adil di sini.
      </p>
    </Section>
  );

  const nActions = corporate_actions.dividends.length + corporate_actions.agms.length + corporate_actions.rights_issues.length + corporate_actions.stock_splits.length;
  const aksi = (
    <Section title="Aksi korporasi">
      {nActions === 0 ? (
        <p className={`${body} text-muted-foreground`}>
          Tidak ada dividen, RUPS, penawaran saham baru, atau pemecahan saham yang tercatat untuk perusahaan ini antara {formatDate(corporate_actions.window_start)} dan {formatDate(corporate_actions.window_end)}.
        </p>
      ) : (
        <ul className={`${body} space-y-1`}>
          {corporate_actions.dividends.map((d) => (
            <li key={`div-${d.ex_date}`}>
              {"• Dividen " +
                (d.amount !== null ? `${formatPrice(d.amount)} per saham` : "(jumlah belum tercatat)") +
                (d.implied_yield !== null ? ` (${idNum(d.implied_yield * 100)}% dari harga terakhir, hanya untuk pembayaran ini)` : "") +
                `: tanggal ex ${formatDate(d.ex_date)}` +
                (d.payment_date ? `, pembayaran ${formatDate(d.payment_date)}` : "") +
                "."}
            </li>
          ))}
          {corporate_actions.agms.map((a) => (
            <li key={`agm-${a.agm_date}`}>
              &bull; RUPS {formatDate(a.agm_date)}
              {a.agm_time && ` pukul ${a.agm_time.slice(0, 5)}`}
              {a.cancelled && " (tercatat dibatalkan)"}.
            </li>
          ))}
          {corporate_actions.rights_issues.map((r) => (
            <li key={`rights-${r.ex_date}`}>
              &bull; Penawaran saham baru (rights issue): tanggal ex {formatDate(r.ex_date)}
              {r.price !== null && `, harga tebus ${formatPrice(r.price)}`}
              {r.old_ratio !== null && r.new_ratio !== null && `, rasio lama:baru ${r.old_ratio}:${r.new_ratio}`}
              {r.trading_period_start && r.trading_period_end && `, periode perdagangan hak ${formatDate(r.trading_period_start)} sampai ${formatDate(r.trading_period_end)}`}.
            </li>
          ))}
          {corporate_actions.stock_splits.map((sp) => (
            <li key={`split-${sp.date}`}>&bull; Pemecahan saham{sp.ratio ? ` ${sp.ratio}` : ""}: tanggal {formatDate(sp.date)}.</li>
          ))}
        </ul>
      )}
      <p className={fine}>
        Data per {formatDate(corporate_actions.as_of)}, hanya peristiwa yang tercatat antara {formatDate(corporate_actions.window_start)} dan {formatDate(corporate_actions.window_end)}; kejadian yang diumumkan setelahnya belum ada di sini. Tanggal ex adalah hari pertama saham diperdagangkan tanpa hak atas dividen tersebut. Ini catatan peristiwa, bukan penilaian.
      </p>
    </Section>
  );

  const jangkaPanjang = (
    <Section title="Perbandingan jangka panjang" sub={beat_gold ? `Riwayat harga ${beat_gold.years} tahun. Mengukur masa lalu, bukan prediksi.` : undefined}>
      {beat_gold ? (
        <>
          <ul className={`${body} space-y-1`}>
            <li>
              &bull; <GlossaryTerm term="beat_gold">Mengalahkan emas</GlossaryTerm>: {beat_gold.beat_gold === null ? "tidak tersedia" : beat_gold.beat_gold ? "ya" : "tidak"}
            </li>
            <li>
              &bull; Mengalahkan <GlossaryTerm term="ihsg">IHSG</GlossaryTerm>: {beat_gold.beat_index === null ? "tidak tersedia" : beat_gold.beat_index ? "ya" : "tidak"}
            </li>
            <li>&bull; Mengalahkan deposito (proxy suku bunga BI): {beat_gold.beat_deposit === null ? "tidak tersedia" : beat_gold.beat_deposit ? "ya" : "tidak"}</li>
            <li>&bull; Mengalahkan saham tipikal di pasar: {beat_gold.beat_typical_stock ? "ya" : "tidak"}</li>
            <li>&bull; Mengalahkan rata-rata sub-sektornya sendiri: {beat_gold.beat_sector_peer === null ? "tidak tersedia" : beat_gold.beat_sector_peer ? "ya" : "tidak"}</li>
          </ul>
          <p className={fine}>Angka dibekukan sejak dihitung, tidak berjalan langsung, dan sumbernya bukan Sectors (emas tidak punya padanan di data IDX).</p>
          <ResearchNote className="mt-1" />
          <TextLink href="/situasi/vs-emas-deposito">Lihat pembandingnya untuk semua saham</TextLink>
        </>
      ) : (
        <p className={`${body} text-muted-foreground`}>Belum cukup riwayat harga untuk menghitung perbandingan ini (minimal 1 tahun).</p>
      )}
    </Section>
  );

  // One tree, reordered with CSS (not rendered twice): on phones every
  // section is a flex item in the mobile order below; from md up the two
  // wrappers become real columns. Tailwind needs the order classes spelled out.
  const MOBILE_ORDER = ["order-1", "order-2", "order-3", "order-4", "order-5", "order-6", "order-7", "order-8", "order-9", "order-10"];
  const place = (node: ReactNode, mobileIndex: number, key: string) =>
    node ? (
      <div key={key} className={`${MOBILE_ORDER[mobileIndex]} md:order-none`}>
        {node}
      </div>
    ) : null;
  // mobile order: harga, sektor, berita, temuan, insider, suspensi, bank, tambang, aksi, jangka panjang
  const leftColumn = [place(harga, 0, "harga"), place(sektor, 1, "sektor"), place(lensBank, 6, "bank"), place(lensMining, 7, "tambang"), place(jangkaPanjang, 9, "panjang")];
  const rightColumn = [place(berita, 2, "berita"), place(temuan, 3, "temuan"), place(insider, 4, "insider"), place(suspensi, 5, "suspensi"), place(aksi, 8, "aksi")];

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <RecentTracker code={code} />
      <BackLink fallback={{ href: "/jelajah", label: "Jelajah" }} />
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[13px] font-bold text-accent-foreground md:size-[52px]">{code.slice(0, 2)}</span>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold leading-tight tracking-[-0.02em] md:text-[32px]">{code}</h1>
            <p className="truncate text-xs text-muted-foreground md:text-[13px]">{snapshot.company_name}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2.5">
          <DatePill>{formatDateId(asOf)}</DatePill>
          <WatchlistButton symbol={code} companyName={snapshot.company_name} />
        </div>
      </div>
      <p className="mt-2 text-[11.5px] text-muted-foreground">Nilai pasar dan free float adalah angka sesaat per {formatDateId(asOf)}, bisa berubah tiap hari.</p>

      <div className="mt-5 md:mt-6">{ringkasan}</div>

      <div className="mt-8 flex flex-col gap-8 md:grid md:grid-cols-[1.2fr_1fr] md:gap-0">
        <div className="contents md:flex md:min-w-0 md:flex-col md:gap-8 md:pr-10">{leftColumn}</div>
        <div className="contents md:flex md:min-w-0 md:flex-col md:gap-8 md:border-l md:border-border md:pl-10">{rightColumn}</div>
      </div>
    </main>
  );
}
