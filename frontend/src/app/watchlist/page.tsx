import { PageTitle, Sub } from "@/components/kit";
import { WatchlistView, type QuoteMap } from "@/components/watchlist-view";
import { formatDateId } from "@/lib/format";
import { getQuoteIndex, getStocksAsOf } from "@/lib/stock-data";

export default async function WatchlistPage() {
  const [quotes, asOf] = await Promise.all([getQuoteIndex(), getStocksAsOf()]);
  const map: QuoteMap = Object.fromEntries(quotes.map((q) => [q.code, { price: q.price, low: q.low, high: q.high }]));
  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <PageTitle title="Watchlist" pill={`Harga ${formatDateId(asOf)}`} />
      <Sub>Disimpan di perangkat ini, tanpa akun.</Sub>
      <WatchlistView quotes={map} />
    </main>
  );
}
