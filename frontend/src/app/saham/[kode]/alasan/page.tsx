import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight, X } from "lucide-react";
import { formatPrice, pctFrom, signedPct } from "@/lib/format";
import { getAllStockCodes, getStockData } from "@/lib/stock-data";

export async function generateStaticParams() {
  return (await getAllStockCodes()).map((kode) => ({ kode }));
}

/**
 * "Kenapa Anda melihat X?" Board: Saham-Interstitial-Mobile / -Web (FILM;
 * the PACK and ASII variants differ only by the stock). Four ways in, none
 * of them advice; the last one shows everything.
 */
export default async function AlasanPage(props: PageProps<"/saham/[kode]/alasan">) {
  const { kode } = await props.params;
  const data = await getStockData(kode);
  if (!data) notFound();
  const code = data.snapshot.symbol.replace(".JK", "");
  const price = data.snapshot.last_close_price;
  const high = data.snapshot["52_w_high_price"];
  const dist = price !== null && high ? pctFrom(price, high) : null;

  const options = [
    { href: `/saham/${code}/alasan/turun`, title: "Harganya turun banyak", line: "Lihat seberapa dalam, dan apa yang biasanya terjadi setelahnya" },
    { href: `/saham/${code}/alasan/murah`, title: "Kelihatan murah", line: "Cek murah dibanding apa, dan apakah labanya mendukung" },
    { href: `/saham/${code}/alasan/rekomendasi`, title: "Ada yang merekomendasikan", line: "Uji alasan yang biasa menyertai rekomendasi" },
    { href: `/saham/${code}`, title: "Cuma melihat-lihat", line: `Tampilkan semua data ${code}` },
  ];

  return (
    <main className="mx-auto w-full max-w-xl px-[18px] py-3 md:px-8 md:py-10">
      <Link href="/" aria-label="Batal, kembali ke Beranda" className="inline-flex size-11 items-center justify-center text-muted-foreground">
        <X className="size-5" strokeWidth={1.7} />
      </Link>
      <div className="mt-2">
        <div className="flex items-center gap-3">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[13px] font-bold text-accent-foreground">{code.slice(0, 2)}</span>
          <div>
            <div className="text-[15px] font-bold">{code}</div>
            {price !== null && (
              <div className="text-xs text-muted-foreground">
                {formatPrice(price)}
                {dist !== null && <> &middot; {signedPct(dist)}</>}
              </div>
            )}
          </div>
        </div>
        <div className="mt-7 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--viz-accent)]">Mulai dari alasan Anda</div>
        <h1 className="mt-2 text-[26px] font-bold leading-tight tracking-[-0.02em] md:text-[32px]">Kenapa Anda melihat {code}?</h1>
        <p className="mt-2 text-[13px] leading-normal text-muted-foreground">Pilih satu. Kami tampilkan data yang paling terkait, bukan saran.</p>
        <div className="mt-6 flex flex-col gap-2.5">
          {options.map((o) => (
            <Link key={o.href} href={o.href} className="flex min-h-[68px] items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3.5">
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-semibold leading-snug">{o.title}</span>
                <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{o.line}</span>
              </span>
              <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
