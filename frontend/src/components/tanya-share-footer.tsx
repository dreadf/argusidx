"use client";

import { ShareButton } from "@/components/tanya-share";
import { ogPath, sharePath, shareTargetOf } from "@/lib/ask/share";
import type { TipView } from "@/lib/ask/tip-view";

/** The share button for a pasted-message result, or nothing when the result has no stock and tested claim to share. */
export function TanyaShare({ view }: { view: TipView }) {
  const target = shareTargetOf(view);
  if (!target) return null;
  const first = view.claims[0];
  return <ShareButton path={sharePath(target)} preview={ogPath(target)} title={`${target.codes.join(", ")}: ${first.title}`} />;
}
