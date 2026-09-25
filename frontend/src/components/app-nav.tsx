"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, FlaskConical, House, MessageCircle, Search, Star, type LucideIcon } from "lucide-react";
import { StockSearch } from "@/components/stock-search";
import type { SearchEntry } from "@/lib/stock-data";

/**
 * The five destinations. Situasi is reached from Beranda (it is a "what
 * usually happens" entry point, not a top-level section), so it keeps
 * Beranda highlighted. Peringkat, Sektor, Tanda and Berita all live
 * under Jelajah as tabs. Search is not a destination: it is the
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
  { href: "/jelajah", label: "Jelajah", icon: Compass, isActive: (p) => p.startsWith("/jelajah") },
  { href: "/temuan", label: "Temuan", icon: FlaskConical, isActive: (p) => p.startsWith("/temuan") },
  { href: "/tanya", label: "Tanya", icon: MessageCircle, isActive: (p) => p.startsWith("/tanya") },
  { href: "/watchlist", label: "Watchlist", icon: Star, isActive: (p) => p.startsWith("/watchlist") },
];

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
            <item.icon className="size-5" strokeWidth={1.7} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar({ index }: { index: SearchEntry[] }) {
  const pathname = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col gap-6 border-r border-border bg-background px-4 py-6 md:flex">
      <div className="pl-2">
        <Logo />
      </div>
      <StockSearch index={index} />
      <nav aria-label="Navigasi utama" className="flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => {
          const active = item.isActive(pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-[13.5px] ${
                active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <item.icon className="size-4" strokeWidth={1.7} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
