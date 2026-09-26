import { Droplets, Scale } from "lucide-react";

/**
 * The four glyphs of the hub board (Situasi-Hub-2): declining bars, a rising
 * line, a pause and bars with an up arrow. Paths copied from the board's
 * symbols (si-decline, si-spike, si-pause, si-double).
 */
const PATHS: Record<string, string[]> = {
  decline: ["M5 5v14M12 9v10M19 13v6"],
  spike: ["M3 19l5-6 4 3 8-10", "M14 6h6v6"],
  double: ["M7 19v-5M17 19V6", "M14 9l3-3 3 3"],
  pause: [],
};

const BY_SLUG: Record<string, keyof typeof PATHS | "float" | "compare"> = {
  "turun-banyak": "decline",
  "bawah-puncak-lama": "decline",
  "harga-baru-melonjak": "spike",
  "pernah-disuspensi": "pause",
  "langganan-suspensi": "pause",
  "perusahaan-rugi": "decline",
  "laba-turun-dua-tahun": "decline",
  "laba-dua-kali-lipat": "double",
  "dekat-puncak-laba-turun": "double",
  "dividen-besar": "double",
  "ikut-ipo": "spike",
  "float-tipis": "float",
  "vs-emas-deposito": "compare",
};

export function SituationGlyph({ slug }: { slug: string }) {
  const kind = BY_SLUG[slug] ?? "decline";
  if (kind === "float") return <Droplets className="size-[18px]" strokeWidth={1.7} />;
  if (kind === "compare") return <Scale className="size-[18px]" strokeWidth={1.7} />;
  return (
    <svg viewBox="0 0 24 24" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {kind === "pause" ? (
        <>
          <rect x="6" y="5" width="4" height="14" rx="1" />
          <rect x="14" y="5" width="4" height="14" rx="1" />
        </>
      ) : (
        PATHS[kind].map((d) => <path key={d} d={d} />)
      )}
    </svg>
  );
}
