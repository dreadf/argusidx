"use client";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { GLOSSARY, type GlossaryKey } from "@/lib/glossary";

/**
 * Tap-to-read glossary (docs/PRODUCT.md §9): wraps a term with a dotted
 * underline; tapping (or clicking) shows its one-sentence definition in a
 * popover. Deliberately a Popover, not a Tooltip — a tooltip's hover-first
 * design doesn't reliably work on a touch phone, and this app is
 * mobile-first by construction.
 */
export function GlossaryTerm({ term, children }: { term: GlossaryKey; children: React.ReactNode }) {
  return (
    <Popover>
      <PopoverTrigger
        className="cursor-help underline decoration-dotted decoration-1 underline-offset-2"
        aria-label={`Apa itu ${children}?`}
      >
        {children}
      </PopoverTrigger>
      <PopoverContent>{GLOSSARY[term]}</PopoverContent>
    </Popover>
  );
}
