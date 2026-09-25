import { TrailTracker } from "@/components/back-link";
import { BottomNav, MobileHeader, Sidebar } from "@/components/app-nav";
import { getSearchIndex } from "@/lib/stock-data";

/**
 * Persistent shell, mounted once in app/layout.tsx. Phone: slim header
 * (logo + search) and a five-tab bottom bar. Desktop: a fixed sidebar with
 * the same five destinations and a search box. Server component: the
 * search index comes from the already-cached stocks.json.
 */
export async function AppShell({ children }: { children: React.ReactNode }) {
  const index = await getSearchIndex();
  return (
    <>
      <TrailTracker />
      <Sidebar index={index} />
      <div className="flex min-h-screen min-w-0 flex-col md:pl-60">
        <MobileHeader />
        <div className="app-content min-w-0 flex-1">{children}</div>
        <footer className="border-t border-border px-[18px] py-4 text-center text-[11px] text-[var(--viz-ink-muted)] md:px-8 md:text-left">
          Data dari{" "}
          <a href="https://sectors.app" target="_blank" rel="noopener noreferrer" className="underline">
            Sectors
          </a>
          . Bukan penasihat keuangan. Tanpa saran beli, jual, atau tahan.
        </footer>
      </div>
      <BottomNav />
    </>
  );
}
