import { redirect } from "next/navigation";

/**
 * Jelajah became Pasar (2026-09-28). Its old tabs moved: Peringkat and Deteksi
 * anomali are tabs under Temuan, sector pages live under Pasar. Old links used
 * /jelajah?urut=<measure>; those go straight to that ranking.
 */
export default async function JelajahRedirect({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const urut = Array.isArray(sp.urut) ? sp.urut[0] : sp.urut;
  redirect(urut ? `/temuan/peringkat/${urut}` : "/pasar");
}
