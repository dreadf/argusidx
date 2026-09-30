import Link from "next/link";
import { SearchX } from "lucide-react";
import { Page } from "@/components/kit";

/**
 * Branded 404: every dynamic route (`/saham/[kode]`, `/situasi/[slug]`,
 * `/temuan/[slug]`, ...) calls notFound() on a bad param, which without this
 * file fell through to Next's generic, unstyled 404 page, a jarring break
 * from the rest of the app. Renders inside the normal AppShell (sidebar,
 * header, footer), so navigation stays available.
 */
export default function NotFound() {
  return (
    <Page className="flex flex-col items-center py-20 text-center md:py-28">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
        <SearchX className="size-6" strokeWidth={1.7} aria-hidden />
      </span>
      <h1 className="mt-5 text-[22px] font-bold leading-tight text-foreground md:text-2xl">Halaman tidak ditemukan</h1>
      <p className="mt-2 max-w-[360px] text-[13.5px] leading-normal text-muted-foreground">
        Kode saham, tautan, atau halaman ini tidak ada, atau sudah pindah.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
        <Link
          href="/"
          className="inline-flex min-h-11 items-center rounded-lg bg-primary px-4 text-[13.5px] font-bold text-primary-foreground transition-colors hover:bg-primary/85"
        >
          Ke Beranda
        </Link>
        <Link
          href="/cari"
          className="inline-flex min-h-11 items-center rounded-lg border border-border px-4 text-[13.5px] font-semibold text-foreground transition-colors hover:bg-muted"
        >
          Cari saham
        </Link>
        <Link
          href="/tanya"
          className="inline-flex min-h-11 items-center rounded-lg border border-border px-4 text-[13.5px] font-semibold text-foreground transition-colors hover:bg-muted"
        >
          Tanya
        </Link>
      </div>
    </Page>
  );
}
