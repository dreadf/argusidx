import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { Page, PageTitle, Sub, TwoCol } from "@/components/kit";
import { VerdictMark } from "@/components/verdict-mark";

/**
 * "Cara kami menguji": the process behind every verdict, and how this
 * project has caught its own mistakes. Every claim traces to
 * EXPERIMENT.md; nothing is asserted that is not on record there.
 */
function Step({ n, title, children }: { n: number; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex gap-3.5">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent text-[13px] font-bold text-accent-foreground">{n}</span>
      <div className="min-w-0 flex-1">
        <div className="text-[15px] font-semibold leading-snug">{title}</div>
        {children}
      </div>
    </div>
  );
}

const line = "mt-1 text-[13.5px] leading-normal text-muted-foreground";

export default function CaraKamiMengujiPage() {
  const left = (
    <div className="flex flex-col gap-[22px]">
      <Step n={1} title="Tiga hasil pengujian">
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-[13.5px]">
          <span className="inline-flex items-center gap-1.5">
            <VerdictMark verdict="yes" size={18} /> Terbukti
          </span>
          <span className="inline-flex items-center gap-1.5">
            <VerdictMark verdict="mixed_or_inconclusive" size={18} /> Tidak konsisten
          </span>
          <span className="inline-flex items-center gap-1.5">
            <VerdictMark verdict="no" size={18} /> Tidak terbukti
          </span>
        </div>
      </Step>
      <Step n={2} title="Tebakan ditulis dulu">
        <p className={line}>Sebelum data dilihat.</p>
      </Step>
      <Step n={3} title="Sebab sebelum akibat">
        <p className={line}>Penyebab diukur sebelum hasilnya.</p>
      </Step>
      <Step n={4} title="Data dibagi dua">
        <p className={line}>Satu bagian untuk mencari, satu untuk memastikan.</p>
      </Step>
    </div>
  );
  const right = (
    <div className="flex flex-col gap-[22px]">
      <Step n={5} title="Ambang naik seiring jumlah uji">
        <p className={line}>35 percobaan sejauh ini.</p>
      </Step>
      <Step n={6} title="Kami koreksi diri sendiri">
        <ul className="mt-2 flex flex-col gap-1.5 text-[13.5px] leading-normal text-muted-foreground">
          <li>P/E rendah: sebagian efek dari satu periode suku bunga.</li>
          <li>Suspensi: rata-rata naik, tapi 2 dari 3 saham tertinggal.</li>
          <li>Angka penurunan pertama (-74,7%) salah, jadi -49,5%.</li>
        </ul>
      </Step>
      <Step n={7} title="Setiap baris punya buktinya">
        <Link href="/temuan/a-high-payout-ratio-predicts-a-dividend-cut" className="mt-2.5 flex items-center justify-between gap-3 border-y border-border py-3.5">
          <span>
            <span className="block text-sm font-semibold">Contoh: dividen besar dan pemotongan dividen</span>
            <span className="mt-0.5 block text-xs text-muted-foreground">Lihat angka aslinya</span>
          </span>
          <ChevronRight className="size-[18px] shrink-0 text-muted-foreground" />
        </Link>
      </Step>
    </div>
  );
  return (
    <Page>
      <PageTitle title="Cara kami menguji" back={{ href: "/temuan", label: "Temuan" }} />
      <Sub>7 aturan di balik setiap hasil.</Sub>
      <div className="mt-6 md:mt-8">
        <TwoCol left={left} right={right} ratio="1fr 1fr" />
      </div>
      <p className="mt-8 text-[13px] text-muted-foreground">35 percobaan untuk 19 keyakinan, termasuk yang gagal.</p>
    </Page>
  );
}
