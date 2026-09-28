import { formatDateId } from "@/lib/format";
import { getStockData, getStocksAsOf } from "@/lib/stock-data";
import TanyaView from "./tanya-view";

/** ?kode=ASII attaches a stock (the "Tentang ASII" chip); ?q= asks a question straight away (from the stock page). */
export default async function TanyaPage(props: PageProps<"/tanya">) {
  const sp = await props.searchParams;
  const kode = typeof sp.kode === "string" ? sp.kode.toUpperCase() : null;
  const stock = kode && /^[A-Z0-9]{4}$/.test(kode) && (await getStockData(kode)) ? kode : null;
  const q = typeof sp.q === "string" ? sp.q.slice(0, 5000) : "";
  return <TanyaView asOf={formatDateId(await getStocksAsOf())} stock={stock} initialQuestion={q} />;
}
