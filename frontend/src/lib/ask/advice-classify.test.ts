import { describe, expect, it } from "vitest";
import { containsAdviceLanguage } from "./advice-language-guard";
import { classify } from "./classify";

// Characterisation tests: they pin what these modules do today.

describe("containsAdviceLanguage", () => {
  it.each([
    "Sebaiknya Anda membeli saham ini",
    "Ini rekomendasi kami",
    "saham ini layak beli",
    "Anda harus jual sekarang",
    "saatnya beli",
    "beli sekarang",
    "hindari saham ini",
    "lebih baik menjual",
    "You should buy this",
    "we recommend it",
    "a good buy",
    "strong buy",
    "buy now",
    "Waspada, saham ini sedang turun",
    "Hindari membeli saat kondisi begini",
    "Ini saham bahaya",
    "Hati-hati dengan saham ini",
    "Hati hati dengan saham ini",
  ])("flags: %s", (text) => {
    expect(containsAdviceLanguage(text)).toBe(true);
  });

  it("does not flag OJK's own programme name, a quoted proper noun", () => {
    expect(containsAdviceLanguage('Panduan OJK Waspada Investasi: cek "2L: Legal dan Logis".')).toBe(false);
  });

  it("still flags a real hit sharing a sentence with the OJK programme name", () => {
    expect(containsAdviceLanguage("Waspada Investasi kata OJK, tapi Anda harus jual sekarang.")).toBe(true);
  });

  it.each([
    "Dari 100 kasus, 88 turun dalam 90 hari.",
    "Hasil ini tidak konsisten antar periode.",
    "Tidak ada data uji untuk klaim ini.",
    "Maksud Anda saham BUMI?",
    "",
  ])("passes: %s", (text) => {
    expect(containsAdviceLanguage(text)).toBe(false);
  });

  it("is case-insensitive", () => {
    expect(containsAdviceLanguage("BELI SEKARANG")).toBe(true);
  });
});

describe("classify", () => {
  it("advice-seeking wins over a recognized stock", () => {
    expect(classify("apakah saya harus jual BBCA sekarang?", true).bucket).toBe("advice_seeking");
  });

  it("prediction questions are unanswerable", () => {
    expect(classify("apakah harga akan naik?", false).bucket).toBe("unanswerable");
    expect(classify("prediksi BBCA minggu depan", true).bucket).toBe("unanswerable");
  });

  it("topical questions route to findings with their belief keys", () => {
    const r = classify("apakah saham oversold memantul?", false);
    expect(r.bucket).toBe("finding");
    expect(r.matchedBeliefs).toEqual(["Oversold (RSI < 30) means a bounce"]);
  });

  it("a recognized stock with no topic is untested_data", () => {
    expect(classify("bagaimana kabar BBCA", true).bucket).toBe("untested_data");
  });

  it("unrecognized, intelligible question is no_data", () => {
    expect(classify("kapan libur bursa berikutnya", false).bucket).toBe("no_data");
  });

  it("greetings and gibberish are ambiguous", () => {
    expect(classify("halo", false).bucket).toBe("ambiguous");
    expect(classify("???", false).bucket).toBe("ambiguous");
    expect(classify("ab", false).bucket).toBe("ambiguous");
  });
});
