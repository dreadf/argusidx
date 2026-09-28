import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { CompareLines } from "@/components/charts/axis-charts";
import { RangeBar } from "@/components/charts/range-bar";
import { GlossaryTerm } from "@/components/glossary-term";
import { Card, Cells, Neg, Pos, Stat } from "@/components/kit";
import { RecentTracker } from "@/components/recent-tracker";
import { StockHead, getFarRank } from "@/components/stock-head";
import { EmptyNote, OtherSituations, StockSituations, type Ctx } from "@/components/stock-situation-blocks";
import { EmphasisStrip } from "@/components/viz/emphasis-strip";
import { BackLink } from "@/components/back-link";
import { getBaseRatesData } from "@/lib/base-rates-data";
import { getBeatGoldData } from "@/lib/beat-gold-data";
import { formatDateId, formatPrice, idNum, pctFrom, signedPct } from "@/lib/format";
import { getInsiderSummary } from "@/lib/insider-data";
import { getIpoBoardsData } from "@/lib/ipo-boards-data";
import { formatPe, isMeaningfulPe } from "@/lib/pe";
import { getRoeHistory } from "@/lib/roe-data";
import { sectorByKey } from "@/lib/sectors-id";
import { getSituations } from "@/lib/situations";
import { getSituationsFile } from "@/lib/stock-situations";
import { getForeignFlow, getIpoPrice } from "@/lib/stock-optional-data";
import { foreignFlowLine, ipoPriceLine } from "@/lib/stock-summary";
import { getAllStockCodes, getStockData, getStocksAsOf } from "@/lib/stock-data";
import type { StockPageData } from "@/lib/stock-data";
import { getSuspensionSummary } from "@/lib/suspensions-data";

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

const body = "text-sm leading-normal";
const fine = "mt-2 text-xs leading-normal text-muted-foreground";

/**
 * One row of "Data lengkap": a title with a one-line summary that opens to
 * the detail. Native <details name="..."> so only one is open at a time
 * (board: Saham-Data-Mobile, "Di aplikasi, satu per satu"), no client JS.
 */
function DataRow({ title, summary, children }: { title: string; summary: string; children: ReactNode }) {
  return (
    <details name="data-lengkap" className="group border-b border-border">
      <summary className="flex min-h-[52px] cursor-pointer list-none items-center gap-2.5 py-2 [&::-webkit-details-marker]:hidden">
        <span className="flex-1 text-sm">{title}</span>
        <span className="text-right text-[13px] text-muted-foreground">{summary}</span>
        <ChevronRight className="size-[18px] shrink-0 text-muted-foreground transition-transform group-open:rotate-90" />
      </summary>
      <div className="pb-4 pt-1">{children}</div>
    </details>
  );
}

export default async function StockPage(props: PageProps<"/saham/[kode]">) {
  const { kode } = await props.params;
  const data = await getStockData(kode);
  if (!data) notFound();

  const code = data.snapshot.symbol.replace(".JK", "");
  const [asOf, insiderMarket, suspMarket, situationsFile, base, ipo, gold, hubSituations, foreignFlow, ipoPrice] = await Promise.all([
    getStocksAsOf(),
    getInsiderSummary(),
    getSuspensionSummary(),
    getSituationsFile(),
    getBaseRatesData(),
    getIpoBoardsData(),
    getBeatGoldData(),
    getSituations(),
    getForeignFlow(code),
    getIpoPrice(code),
  ]);
  const { snapshot, peer_comparison, sector_context, flags, suspension_history, lens_banking, lens_extractive, beat_gold, h1_finding, insider_activity, corporate_actions } = data;
  const roe = await getRoeHistory(code, snapshot.sector);
  const sectorMeta = sectorByKey(snapshot.sector);
  const price = snapshot.last_close_price;
  const low = snapshot["52_w_low_price"];
  const high = snapshot["52_w_high_price"];
  const hasRange = price !== null && low !== null && high !== null && high > low;
  const distHigh = price !== null && high ? pctFrom(price, high) : null;
  const distLow = price !== null && low ? pctFrom(price, low) : null;

  const { rank: farRank, universe } = await getFarRank(price, high);

  const ctx: Ctx = { code, entry: situationsFile.by_symbol[`${code}.JK`], data, base, ipo, hubCount: hubSituations.length };
  const summary = gold.summary;

  const header = (
    <StockHead
      code={code}
      data={data}
      asOf={asOf}
      rank={farRank}
      universe={universe}
      below={
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>Menampilkan semua data {code}.</span>
          <Link href={`/saham/${code}/alasan`} className="inline-flex min-h-11 items-center text-[13px] font-semibold text-[var(--viz-accent)]">
            Pilih alasan Anda &rarr;
          </Link>
        </div>
      }
    />
  );

  /* ---------------- Data lengkap rows ---------------- */
  const noFinancials = sector_context !== null && sector_context.own_roe_pct === null && sector_context.own_pe === null;
  const sectorBody = noFinancials ? (
    <EmptyNote title="Belum ada data untuk bagian ini" extra="Bagian lain di halaman ini tetap tersedia.">
      Perusahaan ini belum punya laporan keuangan tahunan yang lengkap, jadi bagian laba dan valuasi tidak dihitung.
    </EmptyNote>
  ) : (
    <div>
      {sector_context ? (
        <>
          <Cells>
            {[
              <Stat key="r" value={sector_context.own_roe_pct === null ? "-" : `${idNum(sector_context.own_roe_pct)}%`} label={`laba dibanding modal (ROE), sektor ${sector_context.sector_typical_roe_pct === null ? "-" : idNum(sector_context.sector_typical_roe_pct) + "%"}`} size={24} />,
              <Stat key="p" value={isMeaningfulPe(sector_context.own_pe) ? formatPe(sector_context.own_pe) : <span className="text-base leading-tight">{formatPe(sector_context.own_pe)}</span>} size={isMeaningfulPe(sector_context.own_pe) ? 24 : 16} label={`harga dibanding laba (P/E), sektor ${sector_context.sector_typical_pe === null || sector_context.sector_typical_pe <= 0 ? "-" : formatPe(sector_context.sector_typical_pe)}`} />,
            ]}
          </Cells>
          <p className={fine}>
            Nilai tipikal sektor{sectorMeta ? ` ${sectorMeta.label}` : ""}: nilai tengah dari yang melapor ({sector_context.sector_roe_n} dari {sector_context.sector_company_count} untuk ROE). Bukan peringkat antar sektor.{" "}
            <Link href="/pasar#sektor" className="underline">
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
            <CompareLines years={roe.years} own={roe.own} sector={roe.sector} ownLabel={code} sectorLabel="Nilai tengah sektor" yTitle="ROE (%)" xTitle="Tahun laporan" label={`ROE ${code} per tahun dibanding nilai tengah sektor`} />
            <p className="mx-2 mt-1.5 text-xs text-muted-foreground">Bukan grafik harga. ROE tahunan dari laporan; angka di atas memakai 12 bulan terakhir, jadi bisa sedikit berbeda.</p>
          </Card>
        </div>
      )}
    </div>
  );

  const hargaBody = (
    <div>
      {price !== null && (
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[22px] font-bold tabular-nums">{formatPrice(price)}</span>
          <span className="text-xs text-muted-foreground">per {formatDateId(asOf)}</span>
        </div>
      )}
      {hasRange ? <RangeBar low={low} high={high} price={price} /> : <p className={fine}>Harga tertinggi dan terendah setahun sama, atau datanya tidak lengkap, jadi posisi tidak bisa dihitung.</p>}
      {distHigh !== null && (
        <div className="mt-3 text-[13px]">
          <Neg>{signedPct(distHigh)}</Neg> dari tertinggi{distLow !== null && <> &middot; <Pos>{signedPct(distLow, 1, true)}</Pos> dari terendah</>}
        </div>
      )}
    </div>
  );

  const suspensiBody = (
    <div>
      {suspension_history ? (
        <>
          <p className={`${body} mb-2`}>
            <b>
              Pernah <GlossaryTerm term="suspensi">disuspensi</GlossaryTerm> {suspension_history.count}x
            </b>
            , lebih sering dari {suspension_history.more_than_pct}% perusahaan ({idNum(suspension_history.universe_count, 0)} perusahaan).
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
        </>
      ) : (
        <p className={body}>
          <b>{code} belum pernah disuspensi.</b>
        </p>
      )}
      <p className={fine}>
        {idNum(suspMarket.base_rate_pct, 0)} dari 100 perusahaan IDX ({idNum(suspMarket.companies_with_suspensions, 0)} dari {idNum(suspMarket.universe_count, 0)}) pernah disuspensi setidaknya sekali.{" "}
        <Link href="/situasi/pernah-disuspensi" className="underline">
          Lihat alasan suspensi
        </Link>
      </p>
    </div>
  );

  const insiderBody = (
    <div>
      {insider_activity ? (
        <p className={body}>
          <b>
            {code} {insider_activity.net_direction === "net_buying" ? "pembeli bersih" : insider_activity.net_direction === "net_selling" ? "penjual bersih" : "seimbang"}
          </b>
          : {insider_activity.buy_count} pembelian, {insider_activity.sell_count} penjualan{insider_activity.last_transaction_date ? `, terakhir ${formatDate(insider_activity.last_transaction_date)}` : ""}. Direksi, komisaris, dan pemegang besar, {insiderMarket.window.start.slice(0, 4)} sampai {String(insiderMarket.window.end).slice(0, 4)}.
        </p>
      ) : (
        <p className={body}>Tidak ada transaksi insider tercatat untuk saham ini pada periode data.</p>
      )}
      <div className="mb-2 mt-3.5 text-xs text-muted-foreground">Dari {idNum(insiderMarket.companies_with_activity, 0)} saham dengan catatan insider</div>
      <Cells>
        {[
          <Stat key="b" value={insiderMarket.net_buying} label="pembeli bersih" tone="pos" size={22} />,
          <Stat key="s" value={insiderMarket.net_selling} label="penjual bersih" tone="neg" size={22} />,
          <Stat key="e" value={insiderMarket.balanced} label="seimbang" size={22} />,
        ]}
      </Cells>
      <p className="mt-3.5 text-[13px] leading-normal text-muted-foreground">
        Insider menjual sebelum lonjakan sebagai tanda akan anjlok: <b className="text-foreground">tidak terbukti</b> saat diuji (4 kejadian).{" "}
        <Link href="/temuan?hasil=tidak-terbukti" className="underline">
          Lihat temuannya
        </Link>
      </p>
    </div>
  );

  const lima = beat_gold ? (
    <div>
      <ul className={`${body} space-y-2.5`}>
        {(
          [
            ["deposito", beat_gold.beat_deposit, summary.beat_deposit.pct],
            ["IHSG", beat_gold.beat_index, summary.beat_index.pct],
            ["saham tipikal", beat_gold.beat_typical_stock, summary.beat_typical_stock.pct],
            ["sub-sektornya", beat_gold.beat_sector_peer, summary.beat_sector_peer.pct],
            ["emas", beat_gold.beat_gold, summary.beat_gold.pct],
          ] as [string, boolean | null, number | null][]
        ).map(([label, won, pct]) => (
          <li key={label}>
            <div>{won === null ? `Tidak tersedia: ${label}` : `${won ? "Menang" : "Kalah"} dari ${label}`}</div>
            {pct !== null && <div className="text-xs text-muted-foreground">{Math.round(pct)} dari 100 saham menang</div>}
          </li>
        ))}
      </ul>
      <p className={fine}>Lima tahun sampai {formatDateId(summary.research_date)}. Riwayat harga riset, dibekukan sejak dihitung, bukan data Sectors. Mengukur masa lalu, bukan prediksi.</p>
      <Link href="/situasi/vs-emas-deposito" className="inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
        Lihat pembandingnya untuk semua saham &rarr;
      </Link>
    </div>
  ) : (
    <p className={`${body} text-muted-foreground`}>Belum cukup riwayat harga untuk menghitung perbandingan ini (minimal 1 tahun).</p>
  );

  const lensBank = lens_banking && (
    <div>
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
    </div>
  );

  const lensMining = lens_extractive && (
    <div>
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
          <p className={fine}>Riwayat harga komoditas dari Sectors berakhir pada tanggal yang tertera, yang bisa berbeda dari tanggal data saham di halaman ini. Ini konteks tentang komoditasnya, bukan prediksi harga saham perusahaan ini.</p>
        </>
      )}
      <p className={fine}>Ini fakta keterkaitan komoditas, bukan perbandingan dengan perusahaan tambang lain: data reservasi, produksi, dan ekspor yang tersedia hanya angka nasional, bukan per perusahaan.</p>
    </div>
  );

  const nActions = corporate_actions.dividends.length + corporate_actions.agms.length + corporate_actions.rights_issues.length + corporate_actions.stock_splits.length;
  const aksi = (
    <div>
      {nActions === 0 ? (
        <p className={`${body} text-muted-foreground`}>Tidak ada dividen, RUPS, penawaran saham baru, atau pemecahan saham yang tercatat untuk perusahaan ini antara {formatDate(corporate_actions.window_start)} dan {formatDate(corporate_actions.window_end)}.</p>
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
      <p className={fine}>Data per {formatDate(corporate_actions.as_of)}. Tanggal ex adalah hari pertama saham diperdagangkan tanpa hak atas dividen tersebut. Ini catatan peristiwa, bukan penilaian.</p>
    </div>
  );

  const h1 = h1_finding ? h1Sentences(h1_finding, snapshot.free_float) : null;

  const beatSummary = beat_gold ? (beat_gold.beat_gold === null ? "emas: tidak tersedia" : `${beat_gold.beat_gold ? "menang" : "kalah"} dari emas`) : "belum cukup riwayat";
  const insiderSummaryText = insider_activity ? `${insider_activity.buy_count} beli, ${insider_activity.sell_count} jual` : "tidak ada catatan";
  const suspSummary = suspension_history ? `${suspension_history.count} kali, ${formatDateId(suspension_history.events.map((e) => e.date).reduce((a, b) => (a > b ? a : b)))}` : "belum pernah";
  const sectorSummary =
    sector_context && sector_context.own_roe_pct !== null && sector_context.sector_typical_roe_pct !== null
      ? `ROE ${idNum(sector_context.own_roe_pct)}% vs ${idNum(sector_context.sector_typical_roe_pct)}%`
      : sector_context
        ? "ROE tidak tersedia"
        : "sektor belum diketahui";

  const dataLengkap = (
    <section>
      <h3 className="text-[15px] font-semibold leading-snug">Data lengkap {code}</h3>
      <div className="mt-2 border-t border-border">
        <DataRow title="Harga setahun" summary={low !== null && high !== null ? `${formatPrice(low)} sampai ${high.toLocaleString("id-ID")}` : "tidak lengkap"}>
          {hargaBody}
        </DataRow>
        <DataRow title="Dibanding sektor" summary={sectorSummary}>
          {sectorBody}
        </DataRow>
        <DataRow title="Riwayat suspensi" summary={suspSummary}>
          {suspensiBody}
        </DataRow>
        <DataRow title="Transaksi insider" summary={insiderSummaryText}>
          {insiderBody}
        </DataRow>
        {foreignFlow && (
          <DataRow title="Arus asing 20 hari" summary={foreignFlowLine(foreignFlow.net_idr, foreignFlow.as_of)}>
            <p className={body}>Aliran bersih investor asing dalam 20 hari bursa terakhir, dari data Sectors.</p>
            <p className={fine}>Angka harian yang dijumlahkan, bukan kepemilikan asing selama berbulan-bulan.</p>
          </DataRow>
        )}
        {ipoPrice && price !== null && (
          <DataRow title="Harga IPO" summary={ipoPriceLine(ipoPrice.offer_price, price)}>
            <p className={body}>
              Harga penawaran saat IPO {formatDateId(ipoPrice.listing_date)} {formatPrice(ipoPrice.offer_price)}, dibanding harga terakhir {formatPrice(price)}.
            </p>
            <p className={fine}>Perbandingan dua angka, bukan ukuran hasil bagi pembeli mana pun.</p>
          </DataRow>
        )}
        <DataRow title="Lima tahun" summary={beatSummary}>
          {lima}
        </DataRow>
        <DataRow title="Tanda dari laporan" summary={flags.length === 0 ? "tidak ada tanda" : `${flags.length} tanda`}>
          {flags.length === 0 ? (
            <p className={body}>Tidak ada tanda dari 4 jenis yang terdeteksi saat ini.</p>
          ) : (
            <ul className={`${body} space-y-1`}>
              {flags.map((flag) => (
                <li key={flag.key}>&bull; {flag.label}</li>
              ))}
            </ul>
          )}
          <Link href="/temuan/tanda" className="inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
            Lihat semua tanda &rarr;
          </Link>
        </DataRow>
        {h1 && (
          <DataRow title="Free float dan gejolak harga" summary={snapshot.free_float === null ? "tidak tersedia" : `${idNum(snapshot.free_float * 100)}%`}>
            <p className={body}>{h1.lead}</p>
            <p className={fine}>{h1.caveat}</p>
            <Link href="/situasi/float-tipis" className="inline-flex min-h-11 items-center text-[13px] font-medium text-[var(--viz-accent)]">
              Lihat situasi free float &rarr;
            </Link>
          </DataRow>
        )}
        {lensBank && (
          <DataRow title="Sudut pandang perbankan" summary="dibanding bank lain">
            {lensBank}
          </DataRow>
        )}
        {lensMining && (
          <DataRow title="Eksposur komoditas" summary="komoditas terkait">
            {lensMining}
          </DataRow>
        )}
        <DataRow title="Aksi korporasi" summary={nActions === 0 ? "tidak ada tercatat" : `${nActions} tercatat`}>
          {aksi}
        </DataRow>
      </div>
    </section>
  );

  return (
    <main className="mx-auto w-full max-w-3xl px-[18px] py-5 md:px-8 md:py-8">
      <RecentTracker code={code} />
      <BackLink fallback={{ href: "/", label: "Beranda" }} />
      {header}
      <div className="mt-8">
        <StockSituations ctx={ctx} />
      </div>
      <div className="mt-8">{dataLengkap}</div>
      <div className="mt-8">
        <OtherSituations ctx={ctx} />
      </div>
    </main>
  );
}
