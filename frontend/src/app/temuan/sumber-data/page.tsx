import { Page, PageTitle, Sub } from "@/components/kit";
import { getCreditsUsed } from "@/lib/credit-ledger";
import { formatDateId, idNum } from "@/lib/format";
import { getMarketData } from "@/lib/market-data";

/** Where each block of numbers comes from. Copy is the board's ("Sumber-Data"). */
const SOURCES = [
  { title: "Daftar perusahaan dan laporan keuangan", endpoint: "companies", usedFor: "Semua situasi dan tanda", via: "MCP" },
  { title: "Suspensi", endpoint: "suspensions", usedFor: "Pernah disuspensi, langganan suspensi", via: "MCP" },
  { title: "Transaksi insider", endpoint: "filings", usedFor: "Orang dalam beli", via: "MCP" },
  { title: "Berita bertanda bullish dan bearish", endpoint: "news", usedFor: "Temuan sentimen berita", via: "MCP" },
  { title: "Harga komoditas dan tambang", endpoint: "mining", usedFor: "Konteks komoditas", via: "MCP" },
  { title: "Kinerja sejak IPO", endpoint: "listing-performance", usedFor: "Harga IPO dibanding sekarang", via: "MCP" },
  { title: "Arus asing harian semua saham", endpoint: "foreign-flow (daftar)", usedFor: "Asing borong", via: "REST" },
  { title: "Total IHSG dan indeks", endpoint: "idx-total, index-daily", usedFor: "Pasar per tanggal", via: "MCP" },
];

const BUDGET = 1000;

export default async function SumberDataPage() {
  const [market, used] = await Promise.all([getMarketData(), getCreditsUsed()]);
  return (
    <Page>
      <PageTitle title="Sumber data" pill={`Data ${formatDateId(market.as_of)}`} back={{ href: "/temuan", label: "Temuan" }} />
      <div className="md:max-w-3xl">
        <Sub>Dari mana angka aplikasi ini berasal.</Sub>
        {used !== null && (
          <div className="mt-4 flex items-baseline gap-2.5">
            <span className="font-mono text-[26px] font-bold tabular-nums leading-none">{idNum(used, 0)}</span>
            <span className="text-[13px] text-muted-foreground">dari {idNum(BUDGET, 0)} kredit terpakai, semua dicatat satu per satu</span>
          </div>
        )}
        <ul className="mt-3 border-t border-border">
          {SOURCES.map((s) => (
            <li key={s.title} className="flex items-start gap-2.5 border-b border-border py-2.5">
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold leading-snug text-foreground">{s.title}</div>
                <div className="mt-0.5 text-xs leading-normal text-muted-foreground">
                  {s.endpoint} &middot; untuk: {s.usedFor}
                </div>
              </div>
              <span className="inline-flex h-6 shrink-0 items-center rounded-md border border-border px-2 text-[11px] text-muted-foreground">{s.via}</span>
            </li>
          ))}
        </ul>
        <h2 className="mt-6 text-lg font-bold leading-tight tracking-[-0.01em]">Data dibekukan</h2>
        <Sub>Terakhir diambil 6 Oktober 2026 dan tidak diperbarui lagi, sesuai aturan lomba. Setiap halaman menyebut tanggal datanya.</Sub>
      </div>
    </Page>
  );
}
