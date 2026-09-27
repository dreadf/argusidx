"""Plain-Bahasa translations for docs/PRODUCT.md's honesty scoreboard.

The source table (§5.3) is genuinely curated research content, correctly
parsed live rather than hand-copied (build_findings.py): but its labels
are research shorthand ("(H10, new 2026-09-12)", "(H14)"), not
beginner-facing copy, and the table mixes English into an otherwise
Bahasa-Indonesia product (user feedback, 2026-09-13: "still lacking,
would confuse readers, don't release it as a feature").

Keyed by the EXACT English `belief` text parsed from the source table,
so a row added there without a matching entry here fails the build
loudly (build_findings.py) instead of silently shipping untranslated
jargon: the fix isn't "make the scanner smarter", it's "a human decides
the plain-language version before it ships", same discipline as every
other translated string in this app.
"""
from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "Cheap stocks (low P/E) do better": {
        "belief_id": "Saham dengan valuasi murah (P/E rendah) memberi hasil lebih baik",
        "label_id": "Ya, terbukti, meski pengaruhnya tidak besar",
    },
    "High dividend yield means better returns": {
        "belief_id": "Dividen yang tinggi berarti hasil investasi lebih baik",
        "label_id": "Ya, terbukti, meski pengaruhnya tidak besar",
    },
    "Small companies earn more": {
        "belief_id": "Perusahaan kecil memberi keuntungan lebih besar",
        "label_id": (
            "Ya, tapi buktinya lebih lemah dari perkiraan awal: sebagian besar "
            "pengaruhnya berasal dari satu periode tertentu di tahun 2025, meski "
            "pengujian ulang di tahun-tahun lain menunjukkan arah yang sama"
        ),
    },
    "Oversold (RSI < 30) means a bounce": {
        "belief_id": "Saham yang 'oversold' (RSI di bawah 30) akan segera memantul naik",
        "label_id": "Tidak terbukti: tidak ada kaitan yang bisa diandalkan",
    },
    "Price above its 200-day average keeps going up": {
        "belief_id": "Harga di atas rata-rata 200 hari akan terus naik",
        "label_id": "Tidak terbukti: tidak ada kaitan yang bisa diandalkan",
    },
    "Recent 60-day momentum predicts next month": {
        "belief_id": "Tren pergerakan harga 60 hari terakhir bisa memprediksi bulan berikutnya",
        "label_id": "Tidak terbukti: tidak ada kaitan yang bisa diandalkan",
    },
    "High ROE (quality) predicts better returns": {
        "belief_id": "Profitabilitas tinggi (ROE) memprediksi hasil investasi yang lebih baik",
        "label_id": "Tidak terbukti: tidak ada kaitan yang bisa diandalkan",
    },
    "High leverage (debt/equity) predicts worse returns": {
        "belief_id": "Utang yang tinggi memprediksi hasil investasi yang lebih buruk",
        "label_id": "Tidak terbukti: tidak ada kaitan yang bisa diandalkan",
    },
    "A stock suspended for a sudden price spike keeps rising": {
        "belief_id": "Saham yang disuspensi karena lonjakan harga akan terus naik",
        "label_id": (
            "Terbelah: sekitar 2 dari 3 saham justru kalah dari indeks dalam 90 hari "
            "setelahnya, tapi sebagian kecil terus melonjak tajam"
        ),
    },
    "Fast revenue growth predicts better returns": {
        "belief_id": "Pertumbuhan pendapatan yang cepat memprediksi hasil investasi yang lebih baik",
        "label_id": "Tidak terbukti: hasil pengujian tidak konsisten di data yang berbeda",
    },
    "High payout ratio predicts worse returns": {
        "belief_id": "Rasio pembayaran dividen yang tinggi memprediksi hasil investasi yang lebih buruk",
        "label_id": "Tidak terbukti: tidak ada kaitan yang bisa diandalkan",
    },
    "A high payout ratio predicts a dividend cut": {
        "belief_id": "Rasio pembayaran dividen yang tinggi memprediksi pemotongan dividen di masa depan",
        "label_id": (
            "Ya, terbukti kuat: kemungkinan pemotongan dividen naik dari sekitar "
            "14% menjadi 66% pada kelompok dengan rasio pembayaran tertinggi"
        ),
    },
    "Combining a cheap/quality/leverage signal with a technical one beats either alone": {
        "belief_id": (
            "Menggabungkan sinyal fundamental (valuasi/kualitas/utang) dengan sinyal "
            "teknikal memberi hasil lebih baik daripada salah satunya saja"
        ),
        "label_id": "Tidak terbukti: ketiga kombinasi yang diuji tidak menunjukkan hasil lebih baik",
    },
    "Thin float means wild swings": {
        "belief_id": "Kepemilikan publik yang kecil (free float rendah) membuat harga lebih bergejolak",
        "label_id": "Terbalik dari dugaan: justru saham dengan free float besar yang lebih bergejolak",
    },
    "Insiders selling before a price spike warns of a coming crash": {
        "belief_id": "Penjualan oleh insider sebelum lonjakan harga adalah tanda peringatan akan terjadi crash",
        "label_id": "Tidak terbukti: hasilnya malah terbalik saat diuji ulang, dan hanya 4 kejadian",
    },
    "Rising profits mean a rising share price": {
        "belief_id": "Laba perusahaan yang naik membuat harga sahamnya ikut naik",
        "label_id": "Tidak terbukti: pada data uji ulang, tidak ada kaitan antara kenaikan laba dan hasil harga",
    },
    "Foreign investors buying heavily means the price will rise": {
        "belief_id": "Kalau asing sedang borong suatu saham, harganya akan naik",
        "label_id": "Tidak terbukti: saham di daftar asing beli terbanyak tidak lebih sering mengungguli IHSG pekan berikutnya daripada daftar asing jual",
    },
    "Insiders buying their own stock means the price will rise": {
        "belief_id": "Kalau orang dalam membeli saham perusahaannya, harganya akan naik",
        "label_id": "Tidak terbukti: pada data uji, kejadian yang biasa tidak mengungguli IHSG; rata-rata terdongkrak beberapa kenaikan besar",
    },
    "Once IHSG looks \"tertekan\" (pressured), a further fall is more likely than a recovery": {
        "belief_id": "Kalau IHSG sudah terlihat \"tertekan\", penurunan lanjutan lebih mungkin daripada pemulihan",
        "label_id": "Tidak terbukti: arah hasilnya berbeda antara data awal dan data uji, dan rentang kepercayaan pada data uji masih meliputi nol",
    },
    "A stock long below its peak with a loss year does worse than either sign alone": {
        "belief_id": "Saham yang lama di bawah puncak dan rugi setahun lebih buruk dari salah satu tanda saja",
        "label_id": "Tidak terbukti: gabungan ini mengungguli tanda \"lama di bawah puncak\" sendiri, tapi tidak mengungguli tanda \"rugi setahun\" sendiri, jadi belum bisa dikatakan mengungguli keduanya",
    },
    "Active risk signs matter more when the market is already under pressure": {
        "belief_id": "Tanda risiko yang aktif lebih berarti saat pasar sedang tertekan",
        "label_id": "Tidak terbukti: selisihnya positif tapi rentang kepercayaannya masih meliputi nol",
    },
    "The stocks that gained the most today keep rising": {
        "belief_id": "Saham yang naik paling tinggi hari ini akan terus naik",
        "label_id": "Tidak terbukti: arah hasilnya berbeda antara data awal dan data uji, dan rentang kepercayaan pada data uji masih meliputi nol",
    },
    "Positive news coverage predicts a stock will rise": {
        "belief_id": "Pemberitaan positif memprediksi harga saham akan naik",
        "label_id": (
            "Belum jelas: arah hasilnya berbalik antara dua paruh data yang ada; "
            "menjanjikan tapi belum terbukti, perlu riwayat berita yang lebih panjang"
        ),
    },
}


# Short display copy for the redesigned scoreboard (2026-09-20): one plain
# line for the belief and one for the result, so a list row stays scannable
# on a phone. The longer belief_id/label_id above remain for the Ask layer.
# Rules for this copy: no em dash, never the word "campuran" (user feedback:
# ambiguous), no jargon without its plain-language lead.
SHORT_COPY: dict[str, dict[str, str]] = {
    "Cheap stocks (low P/E) do better": {
        "title_short_id": "Saham murah (P/E rendah) memberi hasil lebih baik",
        "result_short_id": "Terbukti, tapi pengaruhnya kecil",
    },
    "High dividend yield means better returns": {
        "title_short_id": "Dividen tinggi berarti hasil lebih baik",
        "result_short_id": "Terbukti, tapi pengaruhnya kecil",
    },
    "Small companies earn more": {
        "title_short_id": "Perusahaan kecil memberi untung lebih besar",
        "result_short_id": "Terbukti, tapi lebih lemah dari perkiraan",
    },
    "Oversold (RSI < 30) means a bounce": {
        "title_short_id": "Saham oversold (RSI di bawah 30) akan memantul",
        "result_short_id": "Tidak ada kaitan yang bisa diandalkan",
    },
    "Price above its 200-day average keeps going up": {
        "title_short_id": "Harga di atas rata-rata 200 hari akan terus naik",
        "result_short_id": "Tidak ada kaitan yang bisa diandalkan",
    },
    "Recent 60-day momentum predicts next month": {
        "title_short_id": "Tren 60 hari memprediksi bulan berikutnya",
        "result_short_id": "Tidak ada kaitan yang bisa diandalkan",
    },
    "High ROE (quality) predicts better returns": {
        "title_short_id": "Laba tinggi dibanding modal (ROE) memprediksi hasil lebih baik",
        "result_short_id": "Tidak ada kaitan yang bisa diandalkan",
    },
    "High leverage (debt/equity) predicts worse returns": {
        "title_short_id": "Utang tinggi memprediksi hasil lebih buruk",
        "result_short_id": "Tidak ada kaitan yang bisa diandalkan",
    },
    "A stock suspended for a sudden price spike keeps rising": {
        "title_short_id": "Saham yang disuspensi karena lonjakan akan terus naik",
        "result_short_id": "Terbelah: 2 dari 3 kalah dari indeks dalam 90 hari, sebagian terus melonjak",
    },
    "Fast revenue growth predicts better returns": {
        "title_short_id": "Pendapatan tumbuh cepat memprediksi hasil lebih baik",
        "result_short_id": "Hasil tidak konsisten di data yang berbeda",
    },
    "High payout ratio predicts worse returns": {
        "title_short_id": "Dividen besar dibanding laba memprediksi hasil lebih buruk",
        "result_short_id": "Tidak ada kaitan yang bisa diandalkan",
    },
    "A high payout ratio predicts a dividend cut": {
        "title_short_id": "Dividen besar dibanding laba memprediksi dividen dipotong",
        "result_short_id": "Terbukti kuat: pemotongan naik dari 14 ke 66 dari 100",
    },
    "Combining a cheap/quality/leverage signal with a technical one beats either alone": {
        "title_short_id": "Menggabungkan sinyal fundamental dan teknikal lebih baik dari salah satunya",
        "result_short_id": "Tiga kombinasi diuji, tidak ada yang lebih baik",
    },
    "Thin float means wild swings": {
        "title_short_id": "Free float kecil membuat harga lebih bergejolak",
        "result_short_id": "Terbalik: float besar yang lebih bergejolak",
    },
    "Insiders selling before a price spike warns of a coming crash": {
        "title_short_id": "Insider menjual sebelum lonjakan adalah tanda akan anjlok",
        "result_short_id": "Terbalik saat diuji ulang, hanya 4 kejadian",
    },
    "Rising profits mean a rising share price": {
        "title_short_id": "Laba naik membuat harga saham naik",
        "result_short_id": "Tidak ada kaitan yang bisa diandalkan",
    },
    "Foreign investors buying heavily means the price will rise": {
        "title_short_id": "Asing borong membuat harga naik",
        "result_short_id": "Daftar asing beli tidak beda dari daftar jual",
    },
    "Insiders buying their own stock means the price will rise": {
        "title_short_id": "Orang dalam beli membuat harga naik",
        "result_short_id": "Tidak lebih sering menang dari IHSG",
    },
    "Positive news coverage predicts a stock will rise": {
        "title_short_id": "Berita positif memprediksi harga akan naik",
        "result_short_id": "Arah hasilnya berbalik antar paruh data, belum jelas",
    },
    "Once IHSG looks \"tertekan\" (pressured), a further fall is more likely than a recovery": {
        "title_short_id": "IHSG tertekan berarti penurunan lanjutan lebih mungkin",
        "result_short_id": "Tidak terbukti, arah hasilnya berbeda antar data",
    },
    "A stock long below its peak with a loss year does worse than either sign alone": {
        "title_short_id": "Lama di bawah puncak plus rugi setahun lebih buruk",
        "result_short_id": "Tidak terbukti, tidak mengungguli tanda rugi setahun sendiri",
    },
    "Active risk signs matter more when the market is already under pressure": {
        "title_short_id": "Tanda risiko lebih berarti saat pasar tertekan",
        "result_short_id": "Tidak terbukti, selisihnya belum jelas dari nol",
    },
    "The stocks that gained the most today keep rising": {
        "title_short_id": "Saham naik tertinggi hari ini akan terus naik",
        "result_short_id": "Tidak terbukti, arah hasilnya berbeda antar data",
    },
}

for _belief, _short in SHORT_COPY.items():
    TRANSLATIONS[_belief].update(_short)
