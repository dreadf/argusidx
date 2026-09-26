import { redirect } from "next/navigation";

/** Old address of Deteksi anomali (was "Tanda"): keeps existing links working. */
export default async function TandaRedirect({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const jenis = Array.isArray(sp.jenis) ? sp.jenis[0] : sp.jenis;
  redirect(jenis ? `/jelajah/anomali/${jenis}` : "/jelajah/anomali");
}
