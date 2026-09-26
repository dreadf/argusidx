import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { getFarRank, StockHead } from "@/components/stock-head";
import { Note, PairBars } from "@/components/situation-ui";
import { activeKinds, KIND_ORDER, type Ctx } from "@/components/stock-situation-blocks";
import { VerdictMark } from "@/components/verdict-mark";
import { getBaseRatesData } from "@/lib/base-rates-data";
import { sampleLine } from "@/lib/finding-copy";
import { getFindingsData } from "@/lib/findings-data";
import { idNum, pctFrom, signedPct } from "@/lib/format";
import { getIpoBoardsData } from "@/lib/ipo-boards-data";
import { getSituationsFile } from "@/lib/stock-situations";
import { getAllStockCodes, getStockData, getStocksAsOf } from "@/lib/stock-data";

const REASONS = ["turun", "murah", "rekomendasi"] as const;
type Reason = (typeof REASONS)[number];
const REASON_LABEL: Record<Reason, string> = { turun: "Harganya turun banyak", murah: "Kelihatan murah", rekomendasi: "Ada yang merekomendasikan" };

export async function generateStaticParams() {
  const codes = await getAllStockCodes();
  return codes.flatMap((kode) => REASONS.map((alasan) => ({ kode, alasan })));
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-[20px] border border-border bg-card p-[18px]">
      <h3 className="text-[15px] font-semibold leading-snug">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

/** Two columns, typical stock vs this one, drawn as columns (never horizontal bars). */
function DepthColumns({ typical, own, code }: { typical: number; own: number; code: string }) {
  const max = Math.max(Math.abs(typical), Math.abs(own), 1);
  const h = (v: number) => Math.max(4, (Math.abs(v) / max) * 120);
  const col = (v: number, label: string, color: string) => (
    <div className="flex w-[74px] flex-col items-center">
      <div className="flex h-[120px] items-start">
        <div className="w-[54px] rounded-[5px]" style={{ height: h(v), background: color }} />
      </div>
      <div className="mt-1.5 font-mono text-[12.5px] font-bold">{signedPct(v)}</div>
      <div className="mt-0.5 text-center text-[11.5px] leading-tight text-muted-foreground">{label}</div>
    </div>
  );
  return (
    <div role="img" aria-label={`Saham biasa ${signedPct(typical)}, ${code} ${signedPct(own)}`} className="flex items-start gap-3 border-t border-border pt-0">
      {col(typical, "Saham biasa (tengah)", "var(--viz-neutral, #5F6C84)")}
      {col(own, code, "var(--viz-diverging-neg)")}
    </div>
  );
}

/**
 * The page a reason opens. Board: Saham-Alasan-Turun-Mobile / -Web
 * ("Harga FILM turun banyak"): three things we have, what we do not know,
 * and a way back to everything. "Kelihatan murah" and "Ada yang
 * merekomendasikan" (Saham-Alasan-Murah / -Rekomendasi) are not built yet.
 */
export default async function AlasanDetailPage(props: PageProps<"/saham/[kode]/alasan/[alasan]">) {
  const { kode, alasan } = await props.params;
  const data = await getStockData(kode);
  if (!data || !(REASONS as readonly string[]).includes(alasan)) notFound();
  const reason = alasan as Reason;
  const code = data.snapshot.symbol.replace(".JK", "");
  const price = data.snapshot.last_close_price;
  const high = data.snapshot["52_w_high_price"];
  const dist = price !== null && high ? pctFrom(price, high) : null;

  const [asOf, base, ipo, situations, findings] = await Promise.all([getStocksAsOf(), getBaseRatesData(), getIpoBoardsData(), getSituationsFile(), getFindingsData()]);
  const { rank, universe } = await getFarRank(price, high);
  const ctx: Ctx = { code, entry: situations.by_symbol[`${code}.JK`], data, base, ipo };
  const nActive = activeKinds(ctx).length;

  const reasonRow = (
    <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-border px-3 py-2 text-[13px]">
      <span className="text-xs text-muted-foreground">Alasan Anda:</span>
      <span className="font-semibold">{REASON_LABEL[reason]}</span>
      <Link href={`/saham/${code}/alasan`} className="ml-auto inline-flex min-h-9 items-center text-[13px] font-semibold text-[var(--viz-accent)]">
        Ubah
      </Link>
    </div>
  );

  const allAbout = (
    <div className="mt-8">
      <h3 className="text-[15px] font-semibold leading-snug">Semua tentang {code}</h3>
      <div className="mt-2 border-t border-border">
        {[
          { k: "Situasi saham ini", v: nActive === 0 ? "tidak ada" : `${nActive} situasi` },
          { k: `Data lengkap ${code}`, v: "harga, sektor, suspensi, insider, lima tahun" },
          { k: "Situasi lain yang kami periksa", v: nActive === 0 ? "" : `${KIND_ORDER.length - nActive} situasi` },
        ].map((r) => (
          <Link key={r.k} href={`/saham/${code}`} className="flex min-h-[52px] items-center gap-2.5 border-b border-border py-2">
            <span className="flex-1 text-sm">{r.k}</span>
            <span className="text-right text-[13px] text-muted-foreground">{r.v}</span>
            <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
          </Link>
        ))}
      </div>
    </div>
  );

  let content: ReactNode;
  if (reason === "turun") {
    const dd = base.typical_drawdown.overall;
    const rec = base.recovery_after_fall;
    const belowPct = Math.round(rec.still_below_peak.pct ?? 0);
    const depth = dist === null ? null : Math.abs(dist);
    const deeperThan =
      depth === null ? null : depth >= Math.abs(dd.p25_pct) ? "3 dari 4" : depth >= Math.abs(dd.median_pct) ? "1 dari 2" : depth >= Math.abs(dd.p75_pct) ? "1 dari 4" : null;
    const oversold = findings.scoreboard.find((r) => r.belief.startsWith("Oversold"));
    content = (
      <>
        <div className="mt-6">
          <h2 className="text-xl font-bold leading-tight tracking-[-0.01em]">Harga {code} turun banyak</h2>
          <p className="mt-1.5 text-[13px] text-muted-foreground">Tiga hal yang kami punya tentang ini.</p>
        </div>
        <div className="mt-4 flex flex-col gap-3.5">
          {dist !== null && (
            <Card title="Seberapa dalam?">
              <div className="flex items-end gap-4">
                <DepthColumns typical={dd.median_pct} own={dist} code={code} />
                <div className="min-w-0 flex-1">
                  {deeperThan ? (
                    <p className="text-sm leading-normal">
                      {code} turun lebih dalam dari penurunan terburuk setahun <b>{deeperThan}</b> saham IDX.
                    </p>
                  ) : (
                    <p className="text-sm leading-normal">
                      {code} turun {idNum(depth ?? 0)}% dari tertinggi setahun, kurang dalam dari penurunan terburuk setahun 3 dari 4 saham IDX.
                    </p>
                  )}
                  <p className="mt-1.5 text-xs leading-normal text-muted-foreground">
                    Kolom abu-abu: nilai tengah {idNum(dd.n, 0)} saham. Seperempat terdalam mulai {signedPct(dd.p25_pct)}, seperempat terdangkal sampai {signedPct(dd.p75_pct)}.
                  </p>
                </div>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">Riwayat harga riset per {base.as_of.split("-").reverse().join("/")}. {code} diukur dari tertinggi setahun.</p>
            </Card>
          )}
          <Card title="Apa yang biasanya terjadi setelahnya?">
            <div className="flex items-end gap-4">
              <PairBars compact a={{ n: belowPct, label: "Belum pulih" }} b={{ n: 100 - belowPct, label: "Sudah pulih" }} unit="dari 100 saham" />
              <div className="min-w-0 flex-1 pb-6">
                <p className="text-sm leading-normal">
                  Dari 100 saham yang jatuh 30%, <b>{belowPct}</b> belum kembali ke puncaknya setahun kemudian.
                </p>
                <p className="mt-1.5 text-xs text-muted-foreground">
                  Dari {idNum(rec.n_events, 0)} kejadian. Yang belum pulih masih {signedPct(rec.still_down_median_gap_pct ?? 0)} dari puncak lamanya.
                </p>
              </div>
            </div>
          </Card>
          {oversold && (
            <Card title="Keyakinan yang sering menyertai">
              <div className="flex gap-3">
                <span className="pt-0.5">
                  <VerdictMark verdict={oversold.verdict} />
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold">&ldquo;Sudah oversold, pasti memantul&rdquo;</div>
                  <div className="mt-0.5 text-[13px]">
                    <b>Tidak terbukti</b>
                    <span className="text-xs text-muted-foreground"> &middot; RSI di bawah 30 tidak terkait dengan kenaikan berikutnya, {sampleLine(oversold.evidence)}</span>
                  </div>
                  {dist !== null && (
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {code}: turun {idNum(Math.abs(dist))}% dari tertinggi setahun
                    </div>
                  )}
                </div>
              </div>
            </Card>
          )}
        </div>
        <div className="mt-5 rounded-2xl border border-border p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">Yang tidak kami ketahui</div>
          <ol className="mt-2.5 space-y-2 text-sm">
            <li className="flex gap-3">
              <span className="font-mono text-xs text-muted-foreground">01</span>Kenapa harga {code} turun sedalam ini.
            </li>
            <li className="flex gap-3">
              <span className="font-mono text-xs text-muted-foreground">02</span>Apakah penyebabnya sudah selesai atau masih berjalan.
            </li>
            <li className="flex gap-3">
              <span className="font-mono text-xs text-muted-foreground">03</span>Tempat mencarinya: keterbukaan informasi {code} di idx.co.id.
            </li>
          </ol>
        </div>
        <div className="mt-4">
          <Note>Ini frekuensi masa lalu, bukan ramalan untuk {code}. Data ini tidak menjelaskan bisnis, manajemen, atau arah harga.</Note>
        </div>
      </>
    );
  } else {
    content = (
      <div className="mt-6">
        <h2 className="text-xl font-bold leading-tight tracking-[-0.01em]">{REASON_LABEL[reason]}</h2>
        <p className="mt-2 text-sm leading-normal text-muted-foreground">Halaman untuk alasan ini belum tersedia. Semua data {code} ada di halaman sahamnya.</p>
        <Link href={`/saham/${code}`} className="inline-flex min-h-11 items-center text-[13.5px] font-semibold text-[var(--viz-accent)]">
          Lihat semua data {code} &rarr;
        </Link>
      </div>
    );
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-[18px] py-5 md:px-8 md:py-8">
      <Link href={`/saham/${code}/alasan`} className="mb-3 inline-flex min-h-11 items-center text-[12.5px] font-medium text-[var(--viz-accent)]">
        &larr; Alasan
      </Link>
      <StockHead code={code} data={data} asOf={asOf} rank={rank} universe={universe} below={reasonRow} />
      {content}
      {allAbout}
    </main>
  );
}
