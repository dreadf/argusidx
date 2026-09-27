"""Evidence for each honesty-scoreboard row (docs/PRODUCT.md §5.3): which
hypothesis it comes from, the real sample size and period tested, and the
single most important limit a reader should know before trusting it.

Keyed by the exact English `belief` string from docs/PRODUCT.md's table
(same pattern as findings_translations.py, and for the same reason: the
table's prose is collaboratively-owned research content, not something
this module hand-transcribes or re-derives). A belief with no entry here
fails the build loudly, matching findings_translations.py's own
discipline: this is user-facing evidence, not an optional footnote.

Every number below was read directly out of EXPERIMENT.md's own "What we
found" / "Limits" sections for the named hypothesis (2026-09-19): not
recomputed, not inferred. If EXPERIMENT.md's numbers change, this file
goes stale; it is not auto-derived from that document, the same
trade-off findings_translations.py already accepts for the scoreboard's
prose.
"""
from __future__ import annotations

EVIDENCE: dict[str, dict[str, str]] = {
    "Cheap stocks (low P/E) do better": {
        "hypothesis_id": "H5, H10",
        "n": "n=1.148 (holdout)",
        "period_id": "Formasi 2024–2026, hasil diukur Mei–Sep tahun berikutnya",
        "limit_id": "Berdasarkan riwayat harga riset, belum divalidasi silang terhadap data harga Sectors.",
    },
    "High dividend yield means better returns": {
        "hypothesis_id": "H10",
        "n": "n=701 (holdout)",
        "period_id": "Formasi 2024–2025",
        "limit_id": "Hanya berlaku untuk saham yang membagikan dividen pada tahun itu, tidak mencakup saham yang tidak membagikan dividen sama sekali.",
    },
    "Small companies earn more": {
        "hypothesis_id": "H5, H10",
        "n": "n=1.148 (H5 holdout), n=1.774 (H10 holdout)",
        "period_id": "2022–2026",
        "limit_id": "Hasil holdout H5 sangat didominasi oleh satu tahun (2024→2025 setelah pemangkasan suku bunga), belum direplikasi secara independen di tahun lain.",
    },
    "Oversold (RSI < 30) means a bounce": {
        "hypothesis_id": "H14",
        "n": "n=26.701 titik data (holdout, 887 saham)",
        "period_id": "Formasi berulang 2022–2026",
        "limit_id": "Arah hubungan justru berbalik antara data eksplorasi dan data holdout, tidak konsisten sama sekali.",
    },
    "Price above its 200-day average keeps going up": {
        "hypothesis_id": "H14",
        "n": "n=26.701 titik data (holdout, 887 saham)",
        "period_id": "Formasi berulang 2022–2026",
        "limit_id": "Tidak signifikan di data eksplorasi, lalu berbalik jadi negatif di data holdout.",
    },
    "Recent 60-day momentum predicts next month": {
        "hypothesis_id": "H14",
        "n": "n=26.701 titik data (holdout, 887 saham)",
        "period_id": "Formasi berulang 2022–2026",
        "limit_id": "Tidak signifikan di data eksplorasi; sinyal di holdout lemah dan berlawanan arah dengan dugaan awal.",
    },
    "High ROE (quality) predicts better returns": {
        "hypothesis_id": "H10",
        "n": "n=1.774 (holdout, pooled)",
        "period_id": "Formasi 2024–2025",
        "limit_id": "Arah hubungan berbalik antara eksplorasi dan holdout, dan tidak lolos koreksi uji berganda (FDR).",
    },
    "High leverage (debt/equity) predicts worse returns": {
        "hypothesis_id": "H10",
        "n": "n=1.774 (holdout, pooled)",
        "period_id": "Formasi 2024–2025",
        "limit_id": "Tidak signifikan di kedua fase, dan tidak lolos koreksi uji berganda (FDR).",
    },
    "A stock suspended for a sudden price spike keeps rising": {
        "hypothesis_id": "H11",
        "n": "n=91 (holdout, +30 hari), n=83 (holdout, +90 hari)",
        "period_id": "Suspensi 2025 (data awal) dan 2026 (uji akhir)",
        "limit_id": "Uji statistik utama (rata-rata) tidak signifikan, tapi tingkat menang saham ini terhadap indeks konsisten di bawah 50% pada data holdout (33,7%–37,4%), dua cara membaca data ini bercerita berbeda, keduanya dilaporkan.",
    },
    "Fast revenue growth predicts better returns": {
        "hypothesis_id": "H10",
        "n": "n=1.774 (holdout, pooled)",
        "period_id": "Formasi 2024–2025",
        "limit_id": "Arah hubungan berubah dari nyaris nol di eksplorasi menjadi positif lemah di holdout, bukti lemah, bukan pola nyata.",
    },
    "High payout ratio predicts worse returns": {
        "hypothesis_id": "H10",
        "n": "n=1.774 (holdout, pooled)",
        "period_id": "Formasi 2024–2025",
        "limit_id": "Tidak signifikan di kedua fase, dan arah hubungan berbalik antar fase.",
    },
    "A high payout ratio predicts a dividend cut": {
        "hypothesis_id": "H4",
        "n": "n=540 (holdout)",
        "period_id": "Formasi 2023–2024, hasil diukur 2024–2025",
        "limit_id": "Sebagian efek ini bersifat mekanis (aritmetika akuntansi perusahaan yang laba turun), bukan murni perilaku, 'pemotongan' didefinisikan sebagai penurunan berapa pun, termasuk yang sangat kecil.",
    },
    "Combining a cheap/quality/leverage signal with a technical one beats either alone": {
        "hypothesis_id": "H15",
        "n": "3 kombinasi diuji, n bervariasi per sel (13–470)",
        "period_id": "2022–2026",
        "limit_id": "Hanya 3 kombinasi spesifik yang diuji, ini bukan bukti bahwa tidak ada kombinasi lain yang bisa berhasil.",
    },
    "Insiders selling before a price spike warns of a coming crash": {
        "hypothesis_id": "H8",
        "n": "n=4 (holdout)",
        "period_id": "Suspensi 2025 (data awal) dan 2026 (uji akhir)",
        "limit_id": "Sampel holdout hanya 4 kejadian, terlalu kecil untuk disimpulkan apa pun, dan hasil yang ada justru berbalik arah dari dugaan awal, bukan mendukungnya.",
    },
    "Positive news coverage predicts a stock will rise": {
        "hypothesis_id": "H9",
        "n": "n=1.863–4.555 (holdout, tergantung horizon)",
        "period_id": "Berita 2025–2026",
        "limit_id": "Kedua bagian data ('eksplorasi' dan 'holdout') berasal dari periode waktu yang berdekatan, bukan dua tahun yang benar-benar terpisah, jadi ini bukan holdout riil seperti pada temuan lain.",
    },
    "Rising profits mean a rising share price": {
        "hypothesis_id": "H17",
        "n": "n=1.256 (holdout)",
        "period_id": "Laba 2022–2025, hasil harga Mei–September 2023–2026",
        "limit_id": "Hanya perusahaan yang labanya positif di tahun sebelumnya yang bisa diukur pertumbuhannya, dan hasil harga diambil dari satu jendela Mei–September per tahun, dari riwayat harga riset.",
    },
    "Foreign investors buying heavily means the price will rise": {
        "hypothesis_id": "H6",
        "n": "n=61 hari, 3.660 saham di daftar",
        "period_id": "Daftar asing harian Januari 2025 sampai September 2026, hasil 5 hari bursa",
        "limit_id": "Riwayat daftar asing hanya sekitar 20 bulan dalam satu keadaan pasar, dan selisih di bawah sekitar 1,2% per lima hari tidak akan terdeteksi; hasil harga dari riwayat harga riset.",
    },
    "Insiders buying their own stock means the price will rise": {
        "hypothesis_id": "H18",
        "n": "n=292 kejadian (uji akhir 2026)",
        "period_id": "Pemberitahuan pembelian 2025 (data awal) dan 2026 (uji akhir), hasil 20 hari bursa",
        "limit_id": "Hanya 20 bulan pemberitahuan dan 8 bulan uji akhir; pemberitahuan berarti perubahan kepemilikan, belum tentu orang dalam seperti yang dimaksud di grup; hasil harga dari riwayat harga riset.",
    },
    "Thin float means wild swings": {
        "hypothesis_id": "H1",
        "n": "n=913",
        "period_id": "Pola ini teramati 2024–2026, tidak teramati pada 2022–2023",
        "limit_id": "Ini hubungan yang teramati bersamaan (kepemilikan publik dan volatilitas diukur pada waktu yang sama), bukan prediksi, free float adalah angka sesaat tanpa riwayat.",
    },
    "Once IHSG looks \"tertekan\" (pressured), a further fall is more likely than a recovery": {
        "hypothesis_id": "T1",
        "n": "n=861 hari (uji akhir), 711 hari (data awal)",
        "period_id": "IHSG 2019-01-02 hingga 2026-09-25; masa uji dimulai 2023-01-01",
        "limit_id": "Rentang kepercayaan pada data uji masih meliputi nol (-0,35 hingga +0,38), dan arahnya berbeda dari data awal, jadi hasil ini tidak dapat disimpulkan ke arah manapun.",
    },
    "A stock long below its peak with a loss year does worse than either sign alone": {
        "hypothesis_id": "R2b",
        "n": "n=2.359 kombinasi, 7.326 tanda \"lama di bawah puncak\" sendiri, 661 tanda \"rugi setahun\" sendiri (data uji)",
        "period_id": "Formasi bulanan Mei 2022-Agustus 2026, hasil diukur 126 hari bursa, hanya data uji (dari 2024-01-01)",
        "limit_id": "Kombinasi ini mengungguli tanda \"lama di bawah puncak\" sendiri, tapi kalah dari tanda \"rugi setahun\" sendiri, jadi syarat mengungguli keduanya tidak terpenuhi; dua pasangan tanda lain yang direncanakan tidak cukup datanya untuk diuji sama sekali.",
    },
    "Active risk signs matter more when the market is already under pressure": {
        "hypothesis_id": "R5",
        "n": "n=12.607 saham-bulan (data uji, semua kelompok)",
        "period_id": "Formasi bulanan data uji (2024-01-01 dan seterusnya), kondisi pasar dari T1",
        "limit_id": "Selisihnya positif (+0,03) tapi rentang kepercayaan bootstrap-nya (-0,04 hingga +0,09) masih meliputi nol, jadi belum bisa disimpulkan berbeda dari nol.",
    },
    "The stocks that gained the most today keep rising": {
        "hypothesis_id": "A1",
        "n": "n=860 hari (uji akhir), 225 hari (data awal)",
        "period_id": "Hari bursa 2022-01-01 hingga 2026-09-27, masa uji dimulai 2023-01-01",
        "limit_id": "Rentang kepercayaan pada data uji masih meliputi nol (-0,010 hingga +0,022), dan arahnya berbeda dari data awal, jadi hasil ini tidak dapat disimpulkan ke arah manapun. Hasil harga memakai adjclose (termasuk dividen), dan kejadian dengan aksi korporasi di dalam jendela 21 hari dikeluarkan, bukan hanya pada hari kejadiannya.",
    },
}
