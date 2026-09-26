import { formatDateId } from "@/lib/format";
import { getStocksAsOf } from "@/lib/stock-data";
import TanyaView from "./tanya-view";

export default async function TanyaPage() {
  return <TanyaView asOf={formatDateId(await getStocksAsOf())} />;
}
