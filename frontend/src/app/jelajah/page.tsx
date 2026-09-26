import { redirect } from "next/navigation";
import { ExploreRow, Note } from "@/components/explore-list";
import { JelajahHead } from "@/components/jelajah-head";
import { Sub } from "@/components/kit";
import { formatDateId } from "@/lib/format";
import { getRankingsData } from "@/lib/rankings-data";

/** The six ranking lists, in board order. `line` is the board's own copy. */
const LISTS = [
  { slug: "jauh-dari-puncak", title: "Jauh dari puncak", line: "Paling jauh di bawah puncak 52 minggu", isNew: false },
  { slug: "float-terendah", title: "Free float terendah", line: "Float kecil tidak terbukti membuat harga bergejolak", isNew: false },
  { slug: "roe-dalam-kelompok", title: "ROE tertinggi dalam kelompoknya", line: "Persentil ROE di antara perusahaan sejenis", isNew: true },
  { slug: "dividen-rutin", title: "Dividen paling rutin", line: "Tahun membayar dividen dari 2021 sampai 2025", isNew: true },
  { slug: "laba-naik-berturut", title: "Laba naik berturut-turut", line: "Rentetan kenaikan laba tahunan", isNew: true },
  { slug: "orang-dalam-beli", title: "Pembelian bersih orang dalam", line: "Selisih beli dan jual, dibanding saham beredar", isNew: true },
];

/** Old links used /jelajah?urut=<measure>; they now live under /jelajah/peringkat/<measure>. */
export default async function JelajahPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const urut = Array.isArray(sp.urut) ? sp.urut[0] : sp.urut;
  if (urut) redirect(`/jelajah/peringkat/${urut}`);

  const rankings = await getRankingsData();
  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <JelajahHead active="peringkat" pill={`Data ${formatDateId(rankings.as_of)}`} />
      <Sub className="mt-4">Urutan menurut satu aturan yang terbuka.</Sub>
      <div className="mt-3">
        {LISTS.map((l) => (
          <ExploreRow key={l.slug} href={`/jelajah/peringkat/${l.slug}`} title={l.title} isNew={l.isNew} line={l.line} />
        ))}
      </div>
      <Note className="mt-4">Urutan menurut satu aturan, bukan pilihan atau rekomendasi.</Note>
    </main>
  );
}
