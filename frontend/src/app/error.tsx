"use client";

import Link from "next/link";
import { useEffect } from "react";
import { TriangleAlert } from "lucide-react";
import { Page } from "@/components/kit";

/**
 * Branded error boundary: without this file, an unhandled exception in any
 * page, layout or loading state below the root layout fell through to
 * Next's generic error screen, outside the app's own dark theme and
 * navigation entirely. Must be a Client Component (Next.js's own
 * requirement for error.tsx).
 *
 * Does NOT cover the root layout itself (AppShell's own data read, for
 * example): error.js wraps page.js and nested layout.js files, but not the
 * layout.js in its own segment. That gap is global-error.tsx, which must
 * render its own <html>/<body> with no access to this app's CSS.
 */
export default function PageError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Page className="flex flex-col items-center py-20 text-center md:py-28">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-[color-mix(in_oklch,var(--destructive),transparent_85%)] text-destructive">
        <TriangleAlert className="size-6" strokeWidth={1.7} aria-hidden />
      </span>
      <h1 className="mt-5 text-[22px] font-bold leading-tight text-foreground md:text-2xl">Ada yang salah</h1>
      <p className="mt-2 max-w-[360px] text-[13.5px] leading-normal text-muted-foreground">
        Halaman ini gagal dimuat. Coba lagi, atau kembali ke Beranda.
        {error.digest && <span className="mt-1 block font-mono text-[11px] text-muted-foreground/70">Kode: {error.digest}</span>}
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
        <button
          type="button"
          onClick={() => retry()}
          className="inline-flex min-h-11 items-center rounded-lg bg-primary px-4 text-[13.5px] font-bold text-primary-foreground transition-colors hover:bg-primary/85"
        >
          Coba lagi
        </button>
        <Link
          href="/"
          className="inline-flex min-h-11 items-center rounded-lg border border-border px-4 text-[13.5px] font-semibold text-foreground transition-colors hover:bg-muted"
        >
          Ke Beranda
        </Link>
      </div>
    </Page>
  );
}
