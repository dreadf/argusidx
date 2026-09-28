import Link from "next/link";
import { Info } from "lucide-react";
import { Sub, TextLink } from "@/components/kit";
import { TemuanHead } from "@/components/temuan-head";
import { TRIAL_COUNT } from "@/lib/findings-summary";
import { sampleLine } from "@/lib/finding-copy";
import { findingSlug, getFindingsData, orderFindings, VERDICT_CHIP, VERDICT_TAB, type Verdict } from "@/lib/findings-data";

const FIRST = 8;

/**
 * Temuan: "is this popular belief true?" A three-number summary, tabs per
 * outcome and one row per belief with its verdict chip (board Temuan-List-2).
 * Situasi (reached from Beranda) answers a different question: "what
 * usually happens to me in this circumstance".
 */
export default async function TemuanPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);
  const findings = await getFindingsData();
  const all = orderFindings(findings.scoreboard);
  const total = all.length;
  const count = (v: Verdict) => all.filter((r) => r.verdict === v).length;
  // "Belum jelas" has no tab of its own (board): it lives under Semua. Older links with ?hasil=tidak-konsisten still filter to it.
  const filter = (["yes", "mixed_or_inconclusive", "no"] as Verdict[]).find((v) => VERDICT_TAB[v].key === first(sp.hasil)) ?? null;
  const rows = filter ? all.filter((r) => r.verdict === filter) : all;
  const shown = Math.max(FIRST, Number(first(sp.tampil)) || FIRST);
  const more = rows.length - shown;
  const tabs: { label: string; href: string; active: boolean; count: number }[] = [
    { label: "Semua", href: "/temuan", active: filter === null, count: total },
    { label: "Terbukti", href: `/temuan?hasil=${VERDICT_TAB.yes.key}`, active: filter === "yes", count: count("yes") },
    { label: "Tidak terbukti", href: `/temuan?hasil=${VERDICT_TAB.no.key}`, active: filter === "no", count: count("no") },
  ];
  const newRows = all.filter((r) => ["H6", "H18"].includes(r.evidence.hypothesis_id));
  const newBothNo = newRows.length === 2 && newRows.every((r) => r.verdict === "no");

  return (
    <main className="mx-auto w-full max-w-6xl px-[18px] py-5 md:px-8 md:py-8">
      <div className="md:max-w-[860px]">
        <TemuanHead active="keyakinan" pill="Data 13/09/2026" />
        <Sub className="mt-4">Keyakinan populer yang kami uji terhadap data.</Sub>

        <div className="mt-4 overflow-hidden rounded-2xl border border-border bg-card">
          <div className="grid grid-cols-3">
            {(["yes", "mixed_or_inconclusive", "no"] as Verdict[]).map((v, i) => (
              <div key={v} className={`px-2 pb-3.5 pt-4 text-center ${i > 0 ? "border-l border-border" : ""}`}>
                <div className="font-mono text-[28px] font-bold leading-[1.1]" style={{ color: VERDICT_CHIP[v].color }}>
                  {count(v)}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">{VERDICT_CHIP[v].label}</div>
              </div>
            ))}
          </div>
          <p className="border-t border-border px-4 py-3 text-center text-[13px]">
            <b>
              Hanya {count("yes")} dari {total} keyakinan yang terbukti.
            </b>{" "}
            <span className="text-muted-foreground">{TRIAL_COUNT} uji, semua hasil tampil.</span>
          </p>
        </div>

        <div className="mt-4 flex flex-wrap gap-2" role="tablist">
          {tabs.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              scroll={false}
              role="tab"
              aria-selected={t.active}
              className={`inline-flex min-h-9 items-center rounded-md border px-3.5 text-[13px] font-semibold ${
                t.active ? "border-[var(--viz-accent)] bg-accent text-[var(--viz-accent)]" : "border-border bg-[var(--viz-raised)] text-foreground"
              }`}
            >
              {t.label} {t.count}
            </Link>
          ))}
        </div>

        <ul className="mt-2 border-t border-border">
          {rows.slice(0, shown).map((row) => {
            const chip = VERDICT_CHIP[row.verdict];
            return (
              <li key={row.belief}>
                <Link href={`/temuan/${findingSlug(row)}`} className="flex items-start gap-3 border-b border-border py-3">
                  <span className="min-w-0 flex-1">
                    <span className="block text-[14.5px] font-semibold leading-snug">{row.title_short_id}</span>
                    <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{sampleLine(row.evidence)}</span>
                  </span>
                  <span className="inline-flex h-6 shrink-0 items-center whitespace-nowrap rounded-md border px-[9px] text-[11px]" style={{ color: chip.color, borderColor: chip.color }}>
                    {chip.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
        {more > 0 && (
          <Link href={`${filter ? `/temuan?hasil=${VERDICT_TAB[filter].key}&` : "/temuan?"}tampil=${rows.length}`} scroll={false} className="mt-1.5 inline-flex min-h-11 items-center text-[13.5px] font-semibold text-[var(--viz-accent)]">
            Tampilkan {more} berikutnya
          </Link>
        )}

        {newBothNo && (
          <div className="mt-3.5 flex gap-2.5 rounded-[14px] border border-dashed border-[var(--border-strong,rgba(255,255,255,0.14))] px-3.5 py-3 text-[12.5px] leading-normal text-muted-foreground">
            <Info className="mt-px size-4 shrink-0" strokeWidth={1.7} />
            <span>Dua baris baru: asing borong dan orang dalam beli. Keduanya tidak terbukti pada data yang ada.</span>
          </div>
        )}
        <TextLink href="/temuan/cara-kami-menguji" className="mt-1.5 !text-[13.5px] !font-semibold">
          Cara kami menguji
        </TextLink>
      </div>
    </main>
  );
}
