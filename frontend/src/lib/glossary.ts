/**
 * Plain-Bahasa, one-sentence definitions for market terms used across the
 * app (docs/PRODUCT.md §9's "core requirement, not polish"). Every entry
 * is a definition only: never a judgment, a threshold recommendation, or
 * advice-shaped language, same discipline `scripts/check_no_advice_language.py`
 * enforces on the rest of the product's copy.
 *
 * Keyed by a stable slug, not the display term itself, so the same
 * definition can be reused verbatim wherever that concept appears
 * (stock pages, Rankings, the Banking lens, suspension categories) without
 * drifting into slightly different wording per screen.
 */
export const GLOSSARY = {
  free_float: "Persentase saham yang bisa diperjualbelikan publik, di luar kepemilikan pendiri, keluarga, atau pemegang saham pengendali.",
  market_cap: "Nilai total seluruh saham perusahaan yang beredar: harga saham dikalikan jumlah saham yang beredar.",
  market_cap_rank: "Peringkat sebuah perusahaan berdasarkan nilai kapitalisasi pasarnya, dibandingkan seluruh perusahaan yang tercatat di bursa.",
  pe_ratio: "Price-to-earnings ratio: harga saham dibagi laba bersih per saham. Angka yang lebih tinggi berarti harga lebih mahal relatif terhadap labanya, bukan otomatis lebih baik atau buruk.",
  roe: "Return on equity: seberapa besar laba yang dihasilkan perusahaan dibandingkan modal sendiri (ekuitas) yang dimilikinya.",
  fifty_two_week_range: "Rentang harga saham antara titik tertinggi dan titik terendah dalam 52 minggu (setahun) terakhir.",
  position_in_range: "Posisi harga saat ini di antara titik terendah dan tertinggi pada periode yang diukur, bukan tanda saham murah atau mahal.",
  dividend_yield: "Total dividen yang dibagikan dalam setahun, dibandingkan dengan harga saham saat ini.",
  payout_ratio: "Persentase laba bersih perusahaan yang dibagikan kembali sebagai dividen kepada pemegang saham.",
  lq45: "Indeks 45 saham dengan likuiditas perdagangan dan kapitalisasi pasar tertinggi di Bursa Efek Indonesia, dievaluasi ulang secara berkala.",
  peer_group: "Kelompok perusahaan sejenis (industri atau sektor yang sama) yang dipakai sebagai pembanding, bukan pembanding acak atau seluruh pasar.",
  sub_sector: "Kelompok industri yang lebih spesifik dari sektor, dipakai untuk menentukan kelompok pembanding (peer group) yang relevan bagi sebuah perusahaan.",
  casa_ratio: "CASA ratio: porsi dana bank yang berasal dari rekening giro dan tabungan (biasanya berbiaya rendah bagi bank) dibandingkan total simpanan nasabah.",
  loan_to_deposit_ratio: "Loan-to-Deposit Ratio: perbandingan jumlah kredit yang disalurkan bank dengan total dana simpanan nasabah yang dihimpunnya.",
  net_interest_margin: "Net Interest Margin: selisih pendapatan bunga dan beban bunga bank, dibandingkan dengan aset produktif yang dimilikinya.",
  capital_adequacy_ratio: "Capital Adequacy Ratio: rasio modal bank dibandingkan aset tertimbang menurut risiko, sebagai bantalan terhadap potensi kerugian.",
  npl_ratio: "Non-Performing Loan ratio: persentase kredit bermasalah (nasabah gagal bayar sesuai perjanjian) dari total kredit yang disalurkan bank.",
  loan_growth: "Pertumbuhan nilai kredit yang disalurkan bank dari tahun sebelumnya ke tahun ini.",
  suspensi: "Penghentian sementara perdagangan saham oleh Bursa Efek Indonesia, bisa karena pergerakan harga tidak wajar, keterlambatan pelaporan, atau alasan kepatuhan lain.",
  ihsg: "Indeks Harga Saham Gabungan: indikator pergerakan harga seluruh saham yang tercatat di Bursa Efek Indonesia, dihitung berdasarkan kapitalisasi pasar.",
  annualized_return: "Imbal hasil yang disetarakan menjadi basis per tahun, agar periode kepemilikan yang berbeda-beda bisa dibandingkan secara adil.",
  beat_gold: "Perbandingan imbal hasil tahunan sebuah saham dengan imbal hasil emas dalam rupiah, pada periode kepemilikan yang sama persis.",
  yearly_mcap_change: "Perubahan nilai kapitalisasi pasar sebuah perusahaan sejak awal tahun berjalan.",
  commodity_exposure: "Jenis komoditas utama yang menjadi sumber pendapatan sebuah perusahaan tambang, bukan penilaian atas prospek komoditas tersebut.",
} as const;

export type GlossaryKey = keyof typeof GLOSSARY;
