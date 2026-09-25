"use client";

import { useEffect } from "react";
import { pushRecent } from "@/lib/recent-store";

/** Renders nothing; records that this stock page was opened. */
export function RecentTracker({ code }: { code: string }) {
  useEffect(() => {
    pushRecent(code);
  }, [code]);
  return null;
}
