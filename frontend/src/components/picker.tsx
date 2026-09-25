"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChevronDown } from "lucide-react";

/**
 * "Urut menurut" / "Jenis tanda" control: level two under a tab bar.
 * Native <select> (works with any screen reader and any phone's own
 * picker) that writes its choice to a query parameter, so every state is
 * a plain, shareable, server-rendered URL.
 */
export function Picker({
  label,
  param,
  value,
  options,
  className = "",
}: {
  label: string;
  param: string;
  value: string;
  options: { value: string; label: string }[];
  className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  return (
    <label className={`mt-4 flex items-center gap-3 ${className}`}>
      <span className="whitespace-nowrap text-xs text-muted-foreground">{label}</span>
      <span className="relative flex-1 md:max-w-[320px]">
        <select
          value={value}
          onChange={(e) => {
            const next = new URLSearchParams(search.toString());
            next.set(param, e.target.value);
            router.push(`${pathname}?${next.toString()}`, { scroll: false });
          }}
          className="min-h-11 w-full appearance-none rounded-xl border border-border bg-card px-3.5 pr-10 text-sm font-semibold text-foreground"
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-[18px] -translate-y-1/2 text-muted-foreground" />
      </span>
    </label>
  );
}
