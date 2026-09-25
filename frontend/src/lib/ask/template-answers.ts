import type { Bucket } from "./classify";
import type { FindingRow } from "@/lib/findings-data";

/**
 * The guaranteed-available answer path (docs/PRODUCT.md §0 rule 4): pure
 * template text, zero I/O, zero external calls. Used whenever no LLM is
 * configured, whenever the LLM call fails, and whenever the LLM's own
 * output trips the advice-language guard: so this must independently
 * satisfy every compliance rule the feature has, not lean on the LLM path
 * to be the "safe" one.
 */
export function buildTemplateProse(
  bucket: Bucket,
  stockCode: string | null,
  findings: FindingRow[]
): string {
  switch (bucket) {
    case "advice_seeking":
      return (
        "Pertanyaan ini meminta rekomendasi (beli/jual/tahan), dan itu bukan yang " +
        "disediakan aplikasi ini, tidak ada saham yang direkomendasikan di sini. " +
        (stockCode
          ? `Yang bisa ditunjukkan: fakta-fakta yang tercatat tentang ${stockCode} di bawah ini.`
          : "Coba tanyakan fakta spesifik tentang sebuah saham, misalnya posisi harganya atau tanda peringatannya.")
      );
    case "unanswerable":
      return (
        "Tidak ada yang bisa menjawab pertanyaan ini dengan pasti, pergerakan harga " +
        "jangka pendek dipengaruhi banyak hal yang tidak tercakup dalam data ini, dan " +
        "aplikasi ini tidak membuat prediksi. " +
        (stockCode
          ? `Yang bisa ditunjukkan adalah fakta-fakta yang sudah tercatat tentang ${stockCode}:`
          : "Yang bisa ditunjukkan hanyalah fakta yang sudah tercatat, bukan ramalan.")
      );
    case "finding": {
      const names = findings.map((f) => `"${f.belief_id}"`).join(", ");
      return `Ini menyentuh temuan yang sudah diuji: ${names}. Hasilnya, apa adanya:`;
    }
    case "answered":
      return "Yang paling dekat dengan pertanyaan Anda, apa adanya:";
    case "untested_data":
      return (
        `Berikut fakta-fakta yang tercatat tentang ${stockCode}. Sebagian angka di sini ` +
        "belum pernah diuji sebagai penanda hasil investasi di masa depan, ditampilkan " +
        "sebagai perbandingan, bukan sinyal."
      );
    case "no_data":
      return (
        "Aplikasi ini belum punya data atau temuan untuk menjawab pertanyaan ini secara " +
        "langsung. Coba tanyakan tentang saham tertentu (mis. \"BBCA\"), atau lihat halaman " +
        "Peringkat dan Papan kejujuran untuk apa yang sudah tercatat."
      );
    case "ambiguous":
      return (
        "Belum jelas apa yang ditanyakan. Coba pertanyaan yang lebih spesifik, misalnya " +
        "\"apa posisi harga BBCA sekarang\" atau \"apakah saham murah lebih untung\"."
      );
  }
}
