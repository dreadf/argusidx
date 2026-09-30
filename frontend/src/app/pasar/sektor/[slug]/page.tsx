import Link from "next/link";
import { notFound } from "next/navigation";
import { Cells, H2, Page, PageTitle, Stat, Sub, TextLink, TwoCol } from "@/components/kit";
import { RankList } from "@/components/rank-list";
import { formatDateId, formatPrice, idNum, rpTrillion, shortName } from "@/lib/format";
import { getSectorBreakdownData } from "@/lib/sector-data";
import { SECTOR_META, sectorBySlug } from "@/lib/sectors-id";
import { getSectorStocks } from "@/lib/stock-data";

export function generateStaticParams() {
  return SECTOR_META.map((s) => ({ slug: s.slug }));
}

export default async function SektorDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const meta = sectorBySlug(slug);
  if (!meta) notFound();
  const [data, stocks] = await Promise.all([getSectorBreakdownData(), getSectorStocks(meta.key)]);
  const row = data.sectors.find((s) => s.sector === meta.key);
  if (!row) notFound();

  const Icon = meta.icon;
  const top = stocks.slice(0, 5);
  const example = stocks.find((s) => s.low != null && s.high != null && s.high > s.low);
  const flagged = stocks.filter((s) => s.flagCount > 0).slice(0, 5);
  const totalFlagged = stocks.filter((s) => s.flagCount > 0).length;

  const left = (
    <div className="flex flex-col gap-8">
      <section>
        <H2>Harga dibanding rentang setahun</H2>
        <div className="mt-3">
          <Cells>
            {[
              <Stat key="l" value={row.breadth.near_low} label="dekat terendah" tone="neg" />,
              <Stat key="m" value={row.breadth.middle} label="di tengah" />,
              <Stat key="h" value={row.breadth.near_high} label="dekat tertinggi" tone="pos" />,
            ]}
          </Cells>
        </div>
        <p className="mt-2 text-xs leading-normal text-muted-foreground">
          Dekat = 20% terbawah atau teratas rentang harga setahun.
          {example && (
            <>
              {" "}
              Contoh {example.code}: rentang {formatPrice(example.low)} sampai {formatPrice(example.high)}, dekat terendah = di bawah{" "}
              {formatPrice(Math.round((example.low as number) + 0.2 * ((example.high as number) - (example.low as number))))}.
            </>
          )}
        </p>
        {row.breadth.excluded > 0 && <p className="mt-1 text-xs text-muted-foreground">{row.breadth.excluded} saham belum punya cukup riwayat harga.</p>}
      </section>
      <section>
        <H2>Nilai tipikal sektor</H2>
        <div className="mt-3">
          <Cells>
            {[
              <Stat key="r" value={row.typical_roe_pct == null ? "-" : `${idNum(row.typical_roe_pct)}%`} label={`laba dibanding modal (ROE), ${row.roe_n} dari ${row.company_count} melapor`} />,
              <Stat key="p" value={row.typical_pe == null || row.typical_pe <= 0 ? "-" : `${idNum(row.typical_pe)}x`} label={`harga dibanding laba (P/E), ${row.pe_n} dari ${row.company_count} melapor`} />,
            ]}
          </Cells>
        </div>
      </section>
    </div>
  );

  const right = (
    <div className="flex flex-col gap-8">
      <section>
        <H2>Saham terbesar</H2>
        <Sub>Menurut nilai pasar, bukan kinerja.</Sub>
        <div className="mt-2">
          <RankList
            rows={top.map((s) => ({
              code: s.code,
              name: shortName(s.name),
              value: s.marketCap == null ? "-" : rpTrillion(s.marketCap),
              sub: s.marketCapRank == null ? undefined : `ke-${s.marketCapRank} dari 962`,
            }))}
          />
        </div>
        <TextLink href={`/pasar/sektor/${meta.slug}/saham`}>Lihat {row.company_count} saham di sektor ini</TextLink>
      </section>
      <section>
        <H2>Saham dengan anomali</H2>
        <p className="mt-2 text-sm">{totalFlagged} dari {row.company_count} saham kena satu anomali atau lebih.</p>
        <div className="mt-2 flex flex-col">
          {flagged.map((s) => (
            <Link key={s.code} href={`/saham/${s.code}`} className="flex items-center justify-between border-b border-border py-3 text-sm transition-colors hover:bg-muted">
              <b>{s.code}</b>
              <span className="text-xs text-muted-foreground">{s.flagCount} anomali</span>
            </Link>
          ))}
        </div>
        <TextLink href="/temuan/tanda">Lihat semua anomali</TextLink>
      </section>
    </div>
  );

  return (
    <Page>
      <PageTitle title={meta.label} pill={`Data ${formatDateId(data.as_of)}`} back={{ href: "/pasar#sektor", label: "Sektor" }} />
      <div className="mt-2 flex items-center gap-2 text-[13px] text-muted-foreground">
        <span className="flex size-7 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Icon className="size-4" strokeWidth={1.7} />
        </span>
        {row.company_count} perusahaan
      </div>
      <div className="mt-6">
        <TwoCol left={left} right={right} ratio="1fr 1fr" />
      </div>
    </Page>
  );
}
