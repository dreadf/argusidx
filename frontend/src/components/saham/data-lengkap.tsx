import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight, Info } from "lucide-react";
import { CompareLines } from "@/components/charts/axis-charts";
import { GlossaryTerm } from "@/components/glossary-term";
import { Card, Cells, Stat } from "@/components/kit";
import { SectionCard, ICONS } from "@/components/saham/parts";
import { EmphasisStrip } from "@/components/viz/emphasis-strip";
import { getBeatGoldData } from "@/lib/beat-gold-data";
import { dateLong } from "@/lib/dates";
import { formatDateId, formatPrice, idNum } from "@/lib/format";
import { getInsiderSummary } from "@/lib/insider-data";
import { formatPe, isMeaningfulPe } from "@/lib/pe";
import { getRoeHistory } from "@/lib/roe-data";
import type { StockPageData } from "@/lib/stock-data";
import { getForeignFlow, getIpoPrice } from "@/lib/stock-optional-data";
import type { ProfileMeta, StockProfile } from "@/lib/stock-profile-data";
import { foreignFlowLine, ipoPriceLine } from "@/lib/stock-summary";
import { getSuspensionSummary } from "@/lib/suspensions-data";

/**
 * "Data lengkap ASII" (board Baru4-Saham-ASII-Data): the raw numbers for
 * anyone who wants to check for themselves, one row per topic, closed by
 * default. Native <details name="..."> so only one is open at a time and no
 * client JS is needed. Two columns on wide screens.
 */

const body = "text-sm leading-normal";

/** A row with nothing to show: what is missing and what stays available, never worded as a verdict. */
function EmptyNote({ title, children, extra }: { title: string; children: ReactNode; extra?: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <span className="flex size-[34px] shrink-0 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
          <Info className="size-[18px]" strokeWidth={1.7} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[15px] font-semibold leading-snug">{title}</div>
          <p className="mt-1.5 text-[13.5px] leading-[1.55] text-muted-foreground">{children}</p>
          {extra && <div className="mt-2.5 text-xs text-muted-foreground">{extra}</div>}
        </div>
      </div>
    </div>
  );
}
const fine = "mt-2 text-xs leading-normal text-muted-foreground";

function DataRow({ title, summary, children }: { title: string; summary: string; children: ReactNode }) {
  return (
    <details name="data-lengkap" className="group border-b border-border">
      <summary className="flex min-h-[56px] cursor-pointer list-none items-center gap-3 py-2.5 [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 flex-1">
          <span className="block text-[14.5px] font-semibold">{title}</span>
          <span className="mt-0.5 block text-[12.5px] leading-snug text-muted-foreground">{summary}</span>
        </span>
        <ChevronRight className="size-[18px] shrink-0 text-muted-foreground transition-transform group-open:rotate-90" />
      </summary>
      <div className="pb-4 pt-1">{children}</div>
    </details>
  );
}

function KV({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <div>
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-t border-border py-2 text-[13.5px] first:border-t-0">
          <span className="text-[13px] text-muted-foreground">{k}</span>
          <span className="text-right">{v}</span>
        </div>
      ))}
    </div>
  );
}

const yearOf = (iso: string | null) => (iso ? iso.slice(0, 4) : "");

/** Five years of the numbers behind the cards; units sit in the row labels so the columns stay narrow. */
function FinTable({ p, years }: { p: StockProfile; years: number[] }) {
  const row = (label: string, vals: (number | null)[], fmt: (v: number) => string) => (
    <tr key={label}>
      <td className="border-b border-border py-2 pr-1 text-left text-xs leading-tight text-muted-foreground">{label}</td>
      {vals.map((v, i) => (
        <td key={i} className="whitespace-nowrap border-b border-border px-0.5 py-2 text-right font-mono tabular-nums">
          {v === null ? "-" : fmt(v)}
        </td>
      ))}
    </tr>
  );
  const big = Math.max(0, ...p.revenue.filter((v): v is number => v !== null).map(Math.abs)) >= 1e12;
  const [div, unit] = big ? [1e12, "Rp T"] : [1e9, "Rp M"];
  const amt = (v: number) => idNum(v / div, Math.abs(v / div) < 10 ? 1 : 0);
  return (
    <div>
      <table className="w-full table-fixed border-collapse text-[12.5px]">
        <colgroup>
          <col className="w-[27%]" />
          {years.map((y) => (
            <col key={y} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th />
            {years.map((y) => (
              <th key={y} className="border-b border-border px-0.5 py-2 text-right text-[11.5px] font-semibold text-muted-foreground">
                {y}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {row(`Pendapatan, ${unit}`, p.revenue, amt)}
          {row(`Laba, ${unit}`, p.earnings, amt)}
          {row("ROE, %", p.roe, (v) => idNum(v * 100, 1))}
          {row("Utang/modal, x", p.der, (v) => idNum(v, 2))}
          {row("Dividen/saham, Rp", p.dividend, (v) => idNum(v, v < 10 ? 2 : 0))}
          {row("P/E, x", p.pe, (v) => (isMeaningfulPe(v) ? idNum(v, 1) : "rugi"))}
        </tbody>
      </table>
      <p className={fine}>Dari laporan tahunan. P/E dihitung dari harga akhir tahun; &quot;rugi&quot; berarti P/E tidak bermakna.</p>
    </div>
  );
}

export async function DataLengkap({
  code,
  data,
  profile: p,
  meta,
  sectorLabel,
  news,
  newsMarket,
  className = "",
}: {
  code: string;
  data: StockPageData;
  profile: StockProfile;
  meta: ProfileMeta;
  sectorLabel: string | null;
  news: { bullish: number; bearish: number } | null;
  newsMarket: { bullishPct: number; first: string; last: string };
  className?: string;
}) {
  const { snapshot, peer_comparison, sector_context, suspension_history, lens_banking, lens_extractive, beat_gold, h1_finding, insider_activity, corporate_actions } = data;
  const [insiderMarket, suspMarket, gold, foreignFlow, ipoPrice, roe] = await Promise.all([
    getInsiderSummary(),
    getSuspensionSummary(),
    getBeatGoldData(),
    getForeignFlow(code),
    getIpoPrice(code),
    getRoeHistory(code, snapshot.sector),
  ]);
  const price = snapshot.last_close_price;

  /* Valuasi */
  const peText = p.pe_meaningful && p.pe_ttm !== null ? `P/E ${idNum(p.pe_ttm)}x` : "P/E tidak bermakna";
  const valuasiSummary = [peText, p.pb_mrq !== null ? `P/B ${idNum(p.pb_mrq, 2)}x` : null, p.ps_ttm !== null ? `P/S ${idNum(p.ps_ttm, 2)}x` : null].filter(Boolean).join(" · ");
  const spe = sector_context?.sector_typical_pe ?? null;
  const valuasi = (
    <KV
      rows={[
        ["P/E (12 bulan terakhir)", p.pe_meaningful && p.pe_ttm !== null ? `${idNum(p.pe_ttm)}x` : "tidak bermakna"],
        ...(isMeaningfulPe(p.forward_pe) ? ([["P/E perkiraan analis", `${idNum(p.forward_pe)}x`]] as [string, string][]) : []),
        ["P/B (harga dibanding modal)", p.pb_mrq !== null ? `${idNum(p.pb_mrq, 2)}x` : "-"],
        ["P/S (harga dibanding pendapatan)", p.ps_ttm !== null ? `${idNum(p.ps_ttm, 2)}x` : "-"],
        [`Nilai tengah P/E sektor${sectorLabel ? ` ${sectorLabel.toLowerCase()}` : ""}`, isMeaningfulPe(spe) ? `${idNum(spe)}x` : "-"],
      ]}
    />
  );

  /* Dibanding sektor (ROE) */
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
              <Stat key="r" value={sector_context.own_roe_pct === null ? "-" : `${idNum(sector_context.own_roe_pct)}%`} label={`laba dibanding modal (ROE), sektor ${sector_context.sector_typical_roe_pct === null ? "-" : idNum(sector_context.sector_typical_roe_pct) + "%"}`} size={22} />,
              <Stat key="p" value={isMeaningfulPe(sector_context.own_pe) && p.pe_meaningful ? formatPe(sector_context.own_pe) : <span className="text-base leading-tight">tidak bermakna</span>} size={isMeaningfulPe(sector_context.own_pe) && p.pe_meaningful ? 22 : 16} label={`harga dibanding laba (P/E), sektor ${isMeaningfulPe(spe) ? formatPe(spe) : "-"}`} />,
            ]}
          </Cells>
          <p className={fine}>
            Nilai tengah dari perusahaan yang melapor ({sector_context.sector_roe_n} dari {sector_context.sector_company_count} untuk ROE). Bukan peringkat antar sektor.{" "}
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
            <p className="mt-1 text-xs text-muted-foreground">Titik terang: {code}. Titik abu-abu: {peer_comparison.comparable_count} perusahaan sejenis, dari ROE terendah ke tertinggi.</p>
          </div>
        </div>
      )}
      {roe && roe.own.some((v) => v !== null && Math.abs(v) > 150) && (
        <p className={fine}>ROE perusahaan ini sangat jauh di luar kisaran biasa (di atas 150% atau di bawah -150% pada salah satu tahun), biasanya karena modalnya hampir habis atau negatif. Grafiknya tidak ditampilkan supaya skalanya tidak menyesatkan.</p>
      )}
      {roe && !roe.own.some((v) => v !== null && Math.abs(v) > 150) && (
        <Card className="mt-4 px-3 pb-3 pt-4">
          <CompareLines years={roe.years} own={roe.own} sector={roe.sector} ownLabel={code} sectorLabel="Nilai tengah sektor" yTitle="ROE (%)" xTitle="Tahun laporan" label={`ROE ${code} per tahun dibanding nilai tengah sektor`} />
          <p className="mx-2 mt-1.5 text-xs text-muted-foreground">Bukan grafik harga. ROE tahunan dari laporan.</p>
        </Card>
      )}
    </div>
  );

  /* Rentang harga */
  const rentang = (
    <KV
      rows={[
        ["90 hari", p.d90_low !== null && p.d90_high !== null ? `${formatPrice(p.d90_low)} sampai ${idNum(p.d90_high, 0)}` : "-"],
        [
          "Setahun",
          snapshot["52_w_low_price"] !== null && snapshot["52_w_high_price"] !== null
            ? `${formatPrice(snapshot["52_w_low_price"])}${p.w52_low_date ? ` (${dateLong(p.w52_low_date)})` : ""} sampai ${idNum(snapshot["52_w_high_price"], 0)}${p.w52_high_date ? ` (${dateLong(p.w52_high_date)})` : ""}`
            : "-",
        ],
        ["Sepanjang masa", p.all_time_low !== null && p.all_time_high !== null ? `${formatPrice(p.all_time_low)} (${yearOf(p.all_time_low_date)}) sampai ${idNum(p.all_time_high, 0)} (${yearOf(p.all_time_high_date)})` : "-"],
      ]}
    />
  );

  /* Kepemilikan dan indeks */
  const ff = snapshot.free_float;
  const tercile = h1_finding?.free_float_tercile;
  const kepemilikan = (
    <div>
      <KV
        rows={[
          ["Free float (saham beredar di publik)", ff === null ? "-" : `${idNum(ff * 100)}%${p.free_float_higher_than !== null ? `, lebih besar dari ${Math.round(p.free_float_higher_than)} dari 100 saham` : ""}`],
          ["Indeks", p.indices.length === 0 ? "tidak masuk indeks" : p.indices.join(", ")],
        ]}
      />
      {h1_finding && (
        <p className={fine}>
          Free float {code} {tercile === "low" ? "termasuk sepertiga tersempit" : tercile === "high" ? "termasuk sepertiga terlebar" : "di sepertiga tengah"} untuk ukuran perusahaannya. Dugaan bahwa float sempit membuat harga lebih liar tidak terbukti; di data kami yang terlihat justru sebaliknya, diukur bersamaan, bukan ramalan.{" "}
          <Link href="/situasi/float-tipis" className="underline">
            Lihat buktinya
          </Link>
        </p>
      )}
    </div>
  );

  /* Transaksi orang dalam */
  const insiderBody = (
    <div>
      {insider_activity ? (
        <p className={body}>
          <b>
            {code} {insider_activity.net_direction === "net_buying" ? "pembeli bersih" : insider_activity.net_direction === "net_selling" ? "penjual bersih" : "seimbang"}
          </b>
          : {insider_activity.buy_count} pembelian, {insider_activity.sell_count} penjualan{insider_activity.last_transaction_date ? `, terakhir ${dateLong(insider_activity.last_transaction_date)}` : ""}. Direksi, komisaris, dan pemegang besar, sejak {dateLong(insiderMarket.window.start)}.
        </p>
      ) : (
        <p className={body}>Tidak ada transaksi orang dalam tercatat untuk {code} sejak {dateLong(insiderMarket.window.start)}.</p>
      )}
      <div className="mb-2 mt-3.5 text-xs text-muted-foreground">Dari {idNum(insiderMarket.companies_with_activity, 0)} saham dengan catatan orang dalam</div>
      <Cells>
        {[
          <Stat key="b" value={insiderMarket.net_buying} label="pembeli bersih" tone="pos" size={20} />,
          <Stat key="s" value={insiderMarket.net_selling} label="penjual bersih" tone="neg" size={20} />,
          <Stat key="e" value={insiderMarket.balanced} label="seimbang" size={20} />,
        ]}
      </Cells>
      <p className="mt-3.5 text-[13px] leading-normal text-muted-foreground">
        Setelah orang dalam membeli, harga <b className="text-foreground">tidak</b> lebih sering mengalahkan IHSG saat diuji.{" "}
        <Link href="/temuan?hasil=tidak-terbukti" className="underline">
          Lihat temuannya
        </Link>
      </p>
    </div>
  );

  /* Arus asing */
  const asing = (
    <div>
      <KV
        rows={[
          ["Hari di daftar beli bersih asing", `${p.foreign_buy_days} dari ${meta.foreign_flow.days}`],
          ["Hari di daftar jual bersih asing", `${p.foreign_sell_days} dari ${meta.foreign_flow.days}`],
          ...(foreignFlow ? ([["20 hari bursa terakhir", foreignFlowLine(foreignFlow.net_idr, foreignFlow.as_of)]] as [string, string][]) : []),
        ]}
      />
      <p className={fine}>
        Daftar harian saham dengan beli atau jual bersih asing terbesar dari Sectors, {meta.foreign_flow.days} hari antara {dateLong(meta.foreign_flow.first)} dan {dateLong(meta.foreign_flow.last)}. Saham di daftar beli tidak naik lebih dari saham di daftar jual saat diuji.
      </p>
    </div>
  );

  /* Berita */
  const nNews = news ? news.bullish + news.bearish : 0;
  const berita = (
    <div>
      {nNews === 0 ? (
        <p className={body}>Tidak ada artikel bernada positif atau negatif tentang {code} dalam data berita kami.</p>
      ) : (
        <KV
          rows={[
            ["Artikel bernada positif", String(news!.bullish)],
            ["Artikel bernada negatif", String(news!.bearish)],
            ["Positif, dibanding semua saham", `${idNum((news!.bullish / nNews) * 100, 0)}% vs ${idNum(newsMarket.bullishPct, 0)}%`],
          ]}
        />
      )}
      <p className={fine}>
        {dateLong(newsMarket.first)} sampai {dateLong(newsMarket.last)}. Label nada dari Sectors, bukan dihitung ArgusIDX. Nada berita belum terbukti memprediksi arah harga.
      </p>
    </div>
  );
  const beritaSummary = nNews === 0 ? "tidak ada artikel bernada" : `${news!.bullish} positif, ${news!.bearish} negatif`;

  /* Aksi korporasi dan suspensi */
  const nActions = corporate_actions.dividends.length + corporate_actions.agms.length + corporate_actions.rights_issues.length + corporate_actions.stock_splits.length;
  const aksi = (
    <div>
      {nActions === 0 ? (
        <p className={`${body} text-muted-foreground`}>
          Tidak ada dividen, RUPS, penawaran saham baru, atau pemecahan saham tercatat antara {dateLong(corporate_actions.window_start)} dan {dateLong(corporate_actions.window_end)}.
        </p>
      ) : (
        <ul className={`${body} space-y-1`}>
          {corporate_actions.dividends.map((d) => (
            <li key={`div-${d.ex_date}`}>
              {"• Dividen " +
                (d.amount !== null ? `${formatPrice(d.amount)} per saham` : "(jumlah belum tercatat)") +
                (d.implied_yield !== null ? ` (${idNum(d.implied_yield * 100)}% dari harga terakhir, hanya untuk pembayaran ini)` : "") +
                `: tanggal ex ${dateLong(d.ex_date)}` +
                (d.payment_date ? `, pembayaran ${dateLong(d.payment_date)}` : "") +
                "."}
            </li>
          ))}
          {corporate_actions.agms.map((a) => (
            <li key={`agm-${a.agm_date}`}>
              &bull; RUPS {dateLong(a.agm_date)}
              {a.agm_time && ` pukul ${a.agm_time.slice(0, 5)}`}
              {a.cancelled && " (tercatat dibatalkan)"}.
            </li>
          ))}
          {corporate_actions.rights_issues.map((r) => (
            <li key={`rights-${r.ex_date}`}>
              &bull; Penawaran saham baru (rights issue): tanggal ex {dateLong(r.ex_date)}
              {r.price !== null && `, harga tebus ${formatPrice(r.price)}`}
              {r.old_ratio !== null && r.new_ratio !== null && `, rasio lama:baru ${r.old_ratio}:${r.new_ratio}`}.
            </li>
          ))}
          {corporate_actions.stock_splits.map((sp) => (
            <li key={`split-${sp.date}`}>&bull; Pemecahan saham{sp.ratio ? ` ${sp.ratio}` : ""}: tanggal {dateLong(sp.date)}.</li>
          ))}
        </ul>
      )}
      <p className={fine}>Tanggal ex adalah hari pertama saham diperdagangkan tanpa hak atas dividen tersebut. Data per {dateLong(corporate_actions.as_of)}.</p>
      <div className="mt-4 border-t border-border pt-3">
        {suspension_history ? (
          <>
            <p className={`${body} mb-2`}>
              <b>
                Pernah <GlossaryTerm term="suspensi">disuspensi</GlossaryTerm> {suspension_history.count}x
              </b>
              , lebih sering dari {suspension_history.more_than_pct}% perusahaan.
            </p>
            <ul className="space-y-2 text-sm">
              {suspension_history.events.slice(0, 5).map((s) => (
                <li key={s.date}>
                  {dateLong(s.date)}: {s.category_label_id}
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
          {idNum(suspMarket.base_rate_pct, 0)} dari 100 perusahaan IDX pernah disuspensi setidaknya sekali.{" "}
          <Link href="/situasi/pernah-disuspensi" className="underline">
            Lihat alasan suspensi
          </Link>
        </p>
      </div>
    </div>
  );
  const lastSusp = suspension_history ? suspension_history.events.map((e) => e.date).reduce((a, b) => (a > b ? a : b)) : null;
  const aksiSummary = [nActions === 0 ? "tidak ada aksi tercatat" : `${nActions} aksi tercatat`, lastSusp ? `suspensi terakhir ${formatDateId(lastSusp)}` : "belum pernah disuspensi"].join(" · ");

  /* Lima tahun */
  const summary = gold.summary;
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
      <p className={fine}>Lima tahun sampai {dateLong(summary.research_date)}. Riwayat harga riset, dibekukan sejak dihitung, bukan data Sectors. Mengukur masa lalu, bukan prediksi.</p>
    </div>
  ) : (
    <p className={`${body} text-muted-foreground`}>Belum cukup riwayat harga untuk menghitung perbandingan ini.</p>
  );
  const limaSummary = beat_gold
    ? [`IHSG: ${beat_gold.beat_index === null ? "-" : beat_gold.beat_index ? "menang" : "kalah"}`, `emas: ${beat_gold.beat_gold === null ? "-" : beat_gold.beat_gold ? "menang" : "kalah"}`, `deposito: ${beat_gold.beat_deposit === null ? "-" : beat_gold.beat_deposit ? "menang" : "kalah"}`].join(" · ")
    : "belum cukup riwayat";

  /* Lenses */
  const lensBank = lens_banking && (
    <div className="text-sm text-muted-foreground">
      {lens_banking.loan_to_deposit_ratio !== null && (
        <p>
          Rasio kredit terhadap dana pihak ketiga (<GlossaryTerm term="loan_to_deposit_ratio">LDR</GlossaryTerm>): <span className="text-foreground">{idNum(lens_banking.loan_to_deposit_ratio * 100, 0)}%</span>. Terlalu rendah maupun terlalu tinggi punya artinya masing-masing, jadi tidak dibandingkan sebagai lebih baik atau buruk.
        </p>
      )}
      {lens_banking.loan_growth !== null && (
        <p className="mt-1">
          <GlossaryTerm term="loan_growth">Pertumbuhan kredit</GlossaryTerm> tahun ini: <span className="text-foreground">{idNum(lens_banking.loan_growth * 100)}%</span>
        </p>
      )}
    </div>
  );
  const COMMODITY_ID: Record<string, string> = { Coal: "Batu bara", Nickel: "Nikel", Gold: "Emas", Copper: "Tembaga", Silver: "Perak", Aluminium: "Aluminium", "Zinc and Lead": "Seng dan Timbal" };
  const lensMining = lens_extractive && (
    <div>
      <p className={body}>
        Terkait <GlossaryTerm term="commodity_exposure">komoditas</GlossaryTerm> {lens_extractive.commodity_type.map((c) => COMMODITY_ID[c] ?? c).join(", ") || "tidak tercatat"}.
      </p>
      {lens_extractive.commodity_trends.length > 0 && (
        <ul className={`${body} mt-2 space-y-1`}>
          {lens_extractive.commodity_trends.map((t) => (
            <li key={t.commodity}>
              &bull; Harga {COMMODITY_ID[t.commodity] ?? t.commodity} pada data terakhir: {t.change_12m_pct !== null ? `${t.change_12m_pct >= 0 ? "+" : ""}${idNum(t.change_12m_pct)}% dibanding 12 bulan sebelumnya` : "belum cukup riwayat untuk perbandingan 12 bulan"}.
            </li>
          ))}
        </ul>
      )}
      <p className={fine}>Konteks tentang komoditasnya, bukan prediksi harga saham perusahaan ini.</p>
    </div>
  );

  return (
    <SectionCard icon={ICONS.data} title={`Data lengkap ${code}`} sub="Angka mentah untuk yang ingin memeriksa sendiri." className={className}>
      <div className="md:grid md:grid-cols-2 md:gap-x-10">
        <div>
          <DataRow title="Valuasi" summary={valuasiSummary}>
            {valuasi}
          </DataRow>
          <DataRow title="Keuangan 5 tahun" summary={`Pendapatan, laba, ROE, utang, dividen, P/E, ${meta.years[0]} sampai ${meta.years[meta.years.length - 1]}`}>
            <FinTable p={p} years={meta.years} />
          </DataRow>
          <DataRow title="Rentang harga" summary={p.d90_low !== null && p.d90_high !== null ? `90 hari ${idNum(p.d90_low, 0)} sampai ${idNum(p.d90_high, 0)}` : "tidak lengkap"}>
            {rentang}
          </DataRow>
          <DataRow
            title="Dibanding sektor"
            summary={sector_context && sector_context.own_roe_pct !== null && sector_context.sector_typical_roe_pct !== null ? `ROE ${idNum(sector_context.own_roe_pct)}% vs ${idNum(sector_context.sector_typical_roe_pct)}%` : sector_context ? "ROE tidak tersedia" : "sektor belum diketahui"}
          >
            {sectorBody}
          </DataRow>
          <DataRow title="Kepemilikan dan indeks" summary={`Free float ${ff === null ? "-" : `${idNum(ff * 100)}%`} · ${p.indices.length === 0 ? "tidak masuk indeks" : `${p.indices.length} indeks`}`}>
            {kepemilikan}
          </DataRow>
          {lensBank && (
            <DataRow title="Kredit bank" summary="LDR dan pertumbuhan kredit">
              {lensBank}
            </DataRow>
          )}
          {lensMining && (
            <DataRow title="Eksposur komoditas" summary={lens_extractive!.commodity_type.map((c) => COMMODITY_ID[c] ?? c).join(", ") || "komoditas terkait"}>
              {lensMining}
            </DataRow>
          )}
        </div>
        <div>
          <DataRow title="Transaksi orang dalam" summary={insider_activity ? `${insider_activity.buy_count} beli, ${insider_activity.sell_count} jual sejak ${yearOf(insiderMarket.window.start)}` : "tidak ada catatan"}>
            {insiderBody}
          </DataRow>
          <DataRow title="Arus asing" summary={`Beli bersih ${p.foreign_buy_days} hari, jual bersih ${p.foreign_sell_days} hari`}>
            {asing}
          </DataRow>
          <DataRow title="Berita" summary={beritaSummary}>
            {berita}
          </DataRow>
          <DataRow title="Aksi korporasi dan suspensi" summary={aksiSummary}>
            {aksi}
          </DataRow>
          <DataRow title="Lima tahun vs emas dan deposito" summary={limaSummary}>
            {lima}
          </DataRow>
          {ipoPrice && price !== null && (
            <DataRow title="Harga IPO" summary={ipoPriceLine(ipoPrice.offer_price, price)}>
              <p className={body}>
                Harga penawaran saat IPO {dateLong(ipoPrice.listing_date)} {formatPrice(ipoPrice.offer_price)}, dibanding harga terakhir {formatPrice(price)}.
              </p>
            </DataRow>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
