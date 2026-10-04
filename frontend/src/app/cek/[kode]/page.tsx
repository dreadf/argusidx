import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MessageCircle } from "lucide-react";
import { DatePill } from "@/components/kit";
import { ClaimRow, StockCardView, TIP_DATA_ONLY_LINE } from "@/components/tanya-results";
import { ogPath, parseShareParams, resolveShare, shareTitle } from "@/lib/ask/share";
import { getTipBundleFor } from "@/lib/ask/tip-bundle";
import { VERDICT_CHIP } from "@/lib/ask/tip-view";
import { formatDateId } from "@/lib/format";
import { getStocksAsOf } from "@/lib/stock-data";

/**
 * The page behind a shared result: the stock card and the tested claims a
 * sender chose to share, rebuilt from the link's stock codes and claim ids
 * alone. It never shows what the sender typed. Dynamic (reads the query), and
 * kept out of search results: any combination of codes and claims is valid.
 */
async function load(props: PageProps<"/cek/[kode]">) {
  const { kode } = await props.params;
  const sp = await props.searchParams;
  const k = Array.isArray(sp.k) ? sp.k[0] : sp.k;
  const target = parseShareParams(kode, k);
  if (!target) return null;
  const result = resolveShare(await getTipBundleFor(target.codes), target);
  return result.stocks.length > 0 && result.claims.length > 0 ? { target, result } : null;
}

export async function generateMetadata(props: PageProps<"/cek/[kode]">): Promise<Metadata> {
  const data = await load(props);
  if (!data) return { title: "ArgusIDX", robots: { index: false } };
  const { target, result } = data;
  const first = result.claims[0];
  const title = shareTitle(result);
  const description = `${first.verdict ? `${VERDICT_CHIP[first.verdict]}. ` : ""}${first.line} Bukan saran investasi.`;
  const image = { url: ogPath(target), width: 1200, height: 630, alt: title };
  return {
    title,
    description,
    robots: { index: false, follow: false },
    openGraph: { title, description, type: "website", images: [image] },
    twitter: { card: "summary_large_image", title, description, images: [image.url] },
  };
}

export default async function SharedResultPage(props: PageProps<"/cek/[kode]">) {
  const data = await load(props);
  if (!data) notFound();
  const { result } = data;
  const asOf = formatDateId(await getStocksAsOf());
  const codes = result.stocks.map((s) => s.code).join(", ");
  return (
    <main className="mx-auto w-full max-w-[784px] px-4 pb-8 pt-5 md:px-8 md:pt-8">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">Hasil periksa yang dibagikan</span>
        <DatePill>Data {asOf}</DatePill>
      </div>
      <h1 className="mt-2 text-[22px] font-bold leading-tight tracking-[-0.02em] md:text-[28px]">Hasil periksa {codes}</h1>
      <p className="mt-1.5 text-[13px] leading-normal text-muted-foreground">Seseorang membagikan hasil ini dari ArgusIDX. Isi pesan aslinya tidak ikut dibagikan.</p>

      <section className="mt-5 flex flex-col gap-3 rounded-2xl border border-border bg-card p-3.5 [&_[data-slot=stock-card]]:bg-[var(--viz-raised)]">
        <div className="text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">Klaim yang diperiksa</div>
        {result.stocks.map((s) => (
          <StockCardView key={s.code} card={{ code: s.code, name: s.short, price: s.price, change: s.change, negative: s.negative, situations: s.situations }} />
        ))}
        <div className="border-t border-border">
          {result.claims.map((row) => (
            <ClaimRow key={row.key} row={row} />
          ))}
        </div>
        <p className="text-xs leading-normal text-muted-foreground">{TIP_DATA_ONLY_LINE}</p>
      </section>

      <section className="mt-4 rounded-2xl border border-border bg-card p-4">
        <div className="flex items-center gap-3">
          <span className="flex size-[34px] shrink-0 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
            <MessageCircle className="size-[18px]" />
          </span>
          <h2 className="text-[15px] font-semibold leading-snug">Dapat tips saham juga?</h2>
        </div>
        <p className="mt-2 text-[13px] leading-normal text-muted-foreground">Tempel pesannya di Tanya. Setiap klaim dicocokkan dengan yang sudah diuji, tanpa saran beli atau jual.</p>
        <Link href="/tanya" className="mt-3.5 inline-flex h-11 w-full items-center justify-center rounded-[10px] bg-primary text-sm font-semibold text-primary-foreground transition-[filter] hover:brightness-110">
          Periksa pesan saya
        </Link>
      </section>

      <p className="mt-6 text-center text-[11px] text-muted-foreground">Bukan penasihat keuangan. Tanpa saran beli, jual, atau tahan.</p>
    </main>
  );
}
