import { CariView } from "@/components/cari-view";
import { PageTitle } from "@/components/kit";
import { formatDateId } from "@/lib/format";
import { getQuoteIndex, getStocksAsOf } from "@/lib/stock-data";

export default async function CariPage() {
  const [quotes, asOf] = await Promise.all([getQuoteIndex(), getStocksAsOf()]);
  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <PageTitle title="Cari saham" />
      <div className="mt-4">
        <CariView quotes={quotes} asOf={formatDateId(asOf)} />
      </div>
    </main>
  );
}
