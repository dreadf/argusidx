"use client";

import { Suspense, useEffect, useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getPreviousServerSnapshot, getPreviousSnapshot, labelForPath, recordVisit, subscribeTrail } from "@/lib/trail";

/** Renders nothing; records every page shown so back links can lead where the user came from. */
function TrailInner() {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  useEffect(() => {
    recordVisit(search ? `${pathname}?${search}` : pathname);
  }, [pathname, search]);
  return null;
}

export function TrailTracker() {
  return (
    <Suspense fallback={null}>
      <TrailInner />
    </Suspense>
  );
}

/**
 * "← <page the user came from>". Falls back to the page's own parent when the
 * tab has no earlier page (a shared link, a fresh tab). With an earlier page it
 * goes back in history, so scroll position and filters come back too.
 */
export function BackLink({ fallback }: { fallback: { href: string; label: string } }) {
  const router = useRouter();
  const previous = useSyncExternalStore(subscribeTrail, getPreviousSnapshot, getPreviousServerSnapshot);
  const href = previous ?? fallback.href;
  const label = previous ? labelForPath(previous) : fallback.label;
  return (
    <Link
      href={href}
      onClick={(e) => {
        if (previous && e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) {
          e.preventDefault();
          router.back();
        }
      }}
      className="mb-3 inline-flex min-h-8 items-center gap-1 text-[12.5px] font-medium text-[var(--viz-accent)]"
    >
      <ArrowLeft className="size-4" />
      {label}
    </Link>
  );
}
