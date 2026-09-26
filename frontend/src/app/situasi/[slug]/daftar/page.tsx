import Link from "next/link";
import { notFound } from "next/navigation";
import { Page, PageTitle } from "@/components/kit";
import { Note, StockListRow } from "@/components/situation-ui";
import { formatDateId } from "@/lib/format";
import { getSituation } from "@/lib/situations";
import { getSituationRows, getSituationsFile, kindOfSlug, LIST_SUB, SLUG_BY_KIND } from "@/lib/stock-situations";

export function generateStaticParams() {
  return Object.values(SLUG_BY_KIND).map((slug) => ({ slug }));
}

const PAGE = 12;

/**
 * Everyone currently in one situation. Board: Situasi-Baru-Daftar-Mobile /
 * -Web ("daftar 79 saham harga baru melonjak"), generalised to every kind
 * in data/app/situations.json.
 */
export default async function SituasiDaftarPage({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { slug } = await params;
  const sp = await searchParams;
  const kind = kindOfSlug(slug);
  const situation = await getSituation(slug);
  if (!kind || !situation) notFound();
  const meta = LIST_SUB[kind];
  const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);
  const order = meta.datedOrder && first(sp.urut) !== "kode" ? "terbaru" : "kode";
  const shown = Math.max(PAGE, Number(first(sp.tampil)) || PAGE);

  const [all, file] = await Promise.all([getSituationRows(kind), getSituationsFile()]);
  const rows = [...all].sort((a, b) => (order === "terbaru" ? (b.date ?? "").localeCompare(a.date ?? "") : 0) || a.code.localeCompare(b.code));
  const base = `/situasi/${slug}/daftar`;

  return (
    <Page>
      <PageTitle title={`${rows.length} ${meta.title}`} pill={`Data ${formatDateId(file.as_of)}`} back={{ href: `/situasi/${slug}`, label: situation.title }} />
      <p className="mt-1.5 text-[13px] leading-normal text-muted-foreground md:text-sm">
        {meta.sub} Diurutkan {order === "terbaru" ? "dari yang paling baru" : "menurut kode"}.
      </p>
      <div className="md:max-w-2xl">
        {meta.datedOrder && (
          <div className="mt-3 flex gap-2 text-[12.5px]">
            <Link href={`${base}?urut=terbaru`} replace scroll={false} className={`rounded-md border px-3 py-1.5 ${order === "terbaru" ? "border-[var(--viz-accent)] text-[var(--viz-accent)]" : "border-border text-muted-foreground"}`}>
              Terbaru
            </Link>
            <Link href={`${base}?urut=kode`} replace scroll={false} className={`rounded-md border px-3 py-1.5 ${order === "kode" ? "border-[var(--viz-accent)] text-[var(--viz-accent)]" : "border-border text-muted-foreground"}`}>
              Kode A-Z
            </Link>
          </div>
        )}
        <div className="mt-2 border-t border-border">
          {rows.slice(0, shown).map((r) => (
            <StockListRow key={r.code} code={r.code} name={r.name} value={r.value} sub={r.sub} />
          ))}
        </div>
        {shown < rows.length && (
          <Link href={`${base}?urut=${order === "terbaru" ? "terbaru" : "kode"}&tampil=${shown + PAGE}`} scroll={false} className="inline-flex min-h-11 items-center text-[13.5px] font-semibold text-[var(--viz-accent)]">
            Tampilkan {Math.min(PAGE, rows.length - shown)} berikutnya
          </Link>
        )}
        <div className="mt-4">
          <Note>Daftar fakta menurut aturan situasi ini, bukan pilihan atau rekomendasi. Ketuk saham untuk melihat semua situasinya.</Note>
        </div>
      </div>
    </Page>
  );
}
