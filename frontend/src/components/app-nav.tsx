"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FlaskConical, House, MessageCircle, PanelLeftClose, PanelLeftOpen, Search, Star, TrendingUp, type LucideIcon } from "lucide-react";
import { StockSearch } from "@/components/stock-search";
import type { SearchEntry } from "@/lib/stock-data";
import { useWatchlistChanges } from "@/lib/use-watchlist-changes";

/**
 * The five destinations. Situasi is reached from Beranda (it is a "what
 * usually happens" entry point, not a top-level section), so it keeps
 * Beranda highlighted. Pasar replaced Jelajah (2026-09-28): sectors live
 * inside Pasar, and Peringkat and Tanda are tabs under Temuan. Search is not a destination: it is the
 * magnifier in the header (mobile) / the box in the sidebar (desktop).
 */
interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  isActive: (pathname: string) => boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Beranda", icon: House, isActive: (p) => p === "/" || p.startsWith("/situasi") },
  { href: "/pasar", label: "Pasar", icon: TrendingUp, isActive: (p) => p.startsWith("/pasar") || p.startsWith("/jelajah") },
  { href: "/temuan", label: "Temuan", icon: FlaskConical, isActive: (p) => p.startsWith("/temuan") },
  { href: "/tanya", label: "Tanya", icon: MessageCircle, isActive: (p) => p.startsWith("/tanya") },
  { href: "/watchlist", label: "Watchlist", icon: Star, isActive: (p) => p.startsWith("/watchlist") },
];

/** Small dot on the Watchlist nav item when a watched stock has something new since the browser last checked. Read-only: never marks anything as seen (only opening /watchlist does that). */
function WatchlistDot() {
  const { hasChanges } = useWatchlistChanges(false);
  if (!hasChanges) return null;
  return <span aria-hidden className="absolute right-0 top-0 size-2 rounded-full bg-[var(--viz-accent)]" />;
}

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-bold text-[var(--viz-ink-primary)]">
      <svg viewBox="0 0 24 24" className="size-5 fill-none stroke-current" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M2 12C5 6.5 9 4.3 12 4.3s7 2.2 10 7.7c-3 5.5-7 7.7-10 7.7S5 17.5 2 12Z" />
        <circle cx="12" cy="12" r="3.1" />
        <circle cx="12" cy="12" r="1" className="fill-current" stroke="none" />
      </svg>
      ArgusIDX
    </Link>
  );
}

export function MobileHeader() {
  return (
    <header className="sticky top-0 z-30 flex h-[52px] items-center justify-between border-b border-border bg-background px-[18px] md:hidden">
      <Logo />
      <Link href="/cari" aria-label="Cari saham" className="flex size-11 items-center justify-center text-muted-foreground">
        <Search className="size-5" />
      </Link>
    </header>
  );
}

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Navigasi utama"
      className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-around border-t border-border bg-background pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      {NAV_ITEMS.map((item) => {
        const active = item.isActive(pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-[58px] min-w-[60px] flex-col items-center justify-center gap-1 text-[11px] ${
              active ? "text-[var(--viz-accent)]" : "text-muted-foreground"
            }`}
          >
            <span className="relative">
              <item.icon className="size-5" strokeWidth={1.7} />
              {item.href === "/watchlist" && <WatchlistDot />}
            </span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

const SIDEBAR_KEY = "argus_sidebar";

function setSidebar(collapsed: boolean) {
  if (collapsed) document.documentElement.dataset.sidebar = "collapsed";
  else delete document.documentElement.dataset.sidebar;
  try {
    localStorage.setItem(SIDEBAR_KEY, collapsed ? "collapsed" : "open");
  } catch {
    // storage blocked: the state still works for this visit
  }
}

export function Sidebar({ index }: { index: SearchEntry[] }) {
  const pathname = usePathname();

  // State lives on <html data-sidebar>; layout.tsx restores it before first paint.
  function toggle(next: boolean, focusSearch = false) {
    setSidebar(next);
    if (focusSearch) setTimeout(() => document.getElementById("sidebar-search")?.focus(), 0);
  }

  const toggleBtn = "flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:text-foreground";
  return (
    <aside className="app-sidebar fixed inset-y-0 left-0 z-30 hidden flex-col gap-6 overflow-hidden border-r border-border bg-background px-4 py-6 md:flex">
      <div className="flex items-center justify-between pl-2 sb-expanded">
        <Logo />
        <button type="button" onClick={() => toggle(true)} aria-label="Ciutkan sidebar" title="Ciutkan sidebar" className={toggleBtn}>
          <PanelLeftClose className="size-4" strokeWidth={1.7} />
        </button>
      </div>
      <div className="flex flex-col items-center gap-3 sb-collapsed">
        <button type="button" onClick={() => toggle(false)} aria-label="Buka sidebar" title="Buka sidebar" className={toggleBtn}>
          <PanelLeftOpen className="size-4" strokeWidth={1.7} />
        </button>
        <button type="button" onClick={() => toggle(false, true)} aria-label="Cari saham" title="Cari saham" className={toggleBtn}>
          <Search className="size-4" strokeWidth={1.7} />
        </button>
      </div>
      <div className="sb-expanded">
        <StockSearch index={index} inputId="sidebar-search" />
      </div>
      <nav aria-label="Navigasi utama" className="flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => {
          const active = item.isActive(pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-[13.5px] ${
                active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span className="relative shrink-0">
                <item.icon className="size-4" strokeWidth={1.7} />
                {item.href === "/watchlist" && <WatchlistDot />}
              </span>
              <span className="sb-expanded">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
