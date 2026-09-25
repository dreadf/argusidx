import Link from "next/link";
import { notFound } from "next/navigation";
import { Neg, Page, PageTitle, Sub } from "@/components/kit";
import { Picker } from "@/components/picker";
import { RankList } from "@/components/rank-list";
import { formatPrice, pctFrom, rpTrillion, shortName, signedPct } from "@/lib/format";
import { SECTOR_META, sectorBySlug } from "@/lib/sectors-id";
import { getSectorStocks, getStocksAsOf } from "@/lib/stock-data";
import { formatDateId } from "@/lib/format";

export function generateStaticParams() {
  return SECTOR_META.map((s) => ({ slug: s.slug }));
}

const PAGE = 10;

export default async function SektorSahamPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { slug } = await params;
  const sp = await searchParams;
  const meta = sectorBySlug(slug);
  if (!meta) notFound();
  const [stocks, asOf] = await Promise.all([getSectorStocks(meta.key), getStocksAsOf()]);
  const urutRaw = Array.isArray(sp.urut) ? sp.urut[0] : sp.urut;
  const urut = urutRaw === "jarak" ? "jarak" : "nilai-pasar";
  const shown = Math.min(stocks.length, Math.max(PAGE, Number(Array.isArray(sp.tampil) ? sp.tampil[0] : sp.tampil) || PAGE));

  const dist = (s: (typeof stocks)[number]) => (s.price != null && s.high ? pctFrom(s.price, s.high) : null);
  const sorted = urut === "jarak" ? [...stocks].sort((a, b) => (dist(a) ?? 0) - (dist(b) ?? 0)) : stocks;
  const rows = sorted.slice(0, shown).map((s) => {
    const d = dist(s);
    return {
      code: s.code,
      name: shortName(s.name),
      value: s.marketCap == null ? "-" : rpTrillion(s.marketCap),
      sub: (
        <span>
          {s.price != null ? formatPrice(s.price) : "-"} {d != null && <Neg>{signedPct(d)}</Neg>}
        </span>
      ),
    };
  });

  return (
    <Page>
      <PageTitle title={meta.label} pill={`Data ${formatDateId(asOf)}`} back={{ href: `/jelajah/sektor/${meta.slug}`, label: `Sektor ${meta.label}` }} />
      <Sub>{stocks.length} saham. Nilai pasar, harga, dan jarak dari tertinggi setahun.</Sub>
      <Picker
        label="Urut menurut"
        param="urut"
        value={urut}
        options={[
          { value: "nilai-pasar", label: "Nilai pasar terbesar" },
          { value: "jarak", label: "Paling jauh dari tertinggi setahun" },
        ]}
      />
      <div className="mt-3 md:max-w-3xl">
        <RankList rows={rows} />
        {shown < stocks.length && (
          <Link
            href={`/jelajah/sektor/${meta.slug}/saham?urut=${urut}&tampil=${shown + PAGE}`}
            scroll={false}
            className="mt-4 flex h-11 items-center justify-center rounded-full border border-border text-[13.5px] font-semibold text-[var(--viz-accent)]"
          >
            Tampilkan {PAGE} berikutnya
          </Link>
        )}
        <p className="mt-2.5 text-center text-xs text-muted-foreground md:text-left">
          1 sampai {shown} dari {stocks.length}
        </p>
      </div>
    </Page>
  );
}
