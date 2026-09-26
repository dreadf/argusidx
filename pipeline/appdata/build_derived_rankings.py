"""Build data/app/rankings_derived.json: four derived rankings (item I10).

Each is a documented method applied to owned data -- a list with a stated way of
computing it, never a score and never a combined verdict across lists. Frozen in
EXPERIMENT.md ("Pre-registration, 2026-09-26 (batch 2)"). No prices and no API
calls; only the universe sweep and the owned insider filings.

(a) ROE percentile within the stock's peer group (`peer_groups.py`'s cascade and
    MIN_GROUP_SIZE), `roe[2025]`. Percentile = peers with a strictly lower ROE
    divided by (peers with a reported ROE - 1), in percent; groups with fewer
    than MIN_GROUP_SIZE reported ROEs are skipped. Many groups have a member at
    100%, so ties are broken by the larger group, then the higher ROE, then the
    ticker (a choice made in this builder, stated in the list's text).
(b) Dividend consistency: years with `total_dividend` > 0 out of 2021-2025;
    ties broken by the smaller coefficient of variation (population standard
    deviation / mean) of the positive dividends, then ticker.
(c) Earnings streaks: the longest current run of rising annual earnings ending
    2025 (each year above the one before, all years in the run positive);
    ties broken by ticker. The list records how many stocks share the top length.
(d) Net insider buying: (sum of buy shares - sum of sell shares) over the owned
    2025-01 to 2026-09 filings, each filing's shares = |holding_after -
    holding_before|, as a share of `outstanding_shares[2025]`. Top 20 net buyers
    and top 20 net sellers from filings NOT tagged `takeover`; takeover-tagged
    filings are shown separately, unranked (by absolute share). Identical
    filings (same symbol, time, holder, holdings, direction) are counted once.
    A ratio above 100% of outstanding shares is kept but marked
    `over_100_percent` (likely a data artefact or a takeover-scale event).

Run: .venv/bin/python -m pipeline.appdata.build_derived_rankings
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from pipeline.appdata.common import (
    APP_DIR,
    INSIDER_BUYS_GLOB,
    INSIDER_SELLS_GLOB,
    RAW_DIR,
    UNIVERSE_GLOB,
    latest_dated_file,
)
from pipeline.appdata.peer_groups import MIN_GROUP_SIZE, build_peer_groups

TOP_N = 20
YEARS = [2021, 2022, 2023, 2024, 2025]
TAKEOVER_TAG = "takeover"

TEXT_ROE = (
    "Cara menghitung: ROE 2025 tiap saham dibandingkan dengan ROE 2025 saham lain dalam kelompok sebanding "
    f"(kelompok sub-industri, industri, sub-sektor, atau sektor; minimal {MIN_GROUP_SIZE} saham). Persentil = "
    "jumlah pesaing dengan ROE lebih rendah dibagi (jumlah pesaing - 1). Banyak kelompok punya satu saham di 100%, "
    "jadi urutan seri: kelompok lebih besar, lalu ROE lebih tinggi, lalu kode saham. Bukan skor gabungan."
)
TEXT_DIVIDEND = (
    "Cara menghitung: jumlah tahun dari 2021-2025 dengan dividen per saham lebih dari nol. Seri diurutkan dari "
    "variasi dividen yang lebih kecil (simpangan baku dibagi rata-rata dari tahun-tahun berdividen), lalu kode saham. "
    "Daftar ini menunjukkan riwayat, bukan janji dividen berikutnya."
)
TEXT_EARNINGS = (
    "Cara menghitung: jumlah tahun beruntun sampai 2025 di mana laba tahunan lebih tinggi dari tahun sebelumnya, "
    "dengan semua laba dalam rentang itu positif. Seri diurutkan menurut kode saham; jumlah saham di panjang teratas "
    "dicatat di daftar."
)
TEXT_INSIDER = (
    "Cara menghitung: selisih saham yang dibeli dikurangi dijual dalam laporan kepemilikan Januari 2025 sampai "
    "September 2026 (dari kepemilikan sebelum dan sesudah tiap laporan), dibagi jumlah saham beredar 2025. Laporan "
    "bertanda takeover ditampilkan terpisah. Sebuah laporan belum tentu berasal dari orang dalam dalam arti umum."
)


def _qv(row: dict) -> dict:
    return row.get("query_values") or {}


def build_roe_percentile(rows: list[dict], top: int = TOP_N) -> dict:
    peer = build_peer_groups(rows)
    roe = {r["symbol"]: _qv(r).get("roe[2025]") for r in rows}
    names = {r["symbol"]: r.get("company_name") for r in rows}
    entries = []
    evaluable = 0
    for sym, a in peer["assignments"].items():
        value = roe.get(sym)
        if value is None:
            continue
        key = f"{a['level']}:{a['group']}"
        peers = [roe[m] for m in peer["group_members"][key] if roe.get(m) is not None]
        if len(peers) < MIN_GROUP_SIZE:
            continue
        evaluable += 1
        below = sum(1 for p in peers if p < value)
        entries.append({
            "symbol": sym,
            "company_name": names[sym],
            "roe_2025": value,
            "percentile": 100.0 * below / (len(peers) - 1),
            "group": a["group"],
            "group_level": a["level"],
            "group_size": len(peers),
        })
    # ROE above 100% is almost always near-zero or negative equity, not performance
    # (lead decision 2026-09-26): kept out of the ranked list, reported separately.
    excluded = sorted((e for e in entries if e["roe_2025"] > 1.0), key=lambda e: e["symbol"])
    entries = [e for e in entries if e["roe_2025"] <= 1.0]
    entries.sort(key=lambda e: (-e["percentile"], -e["group_size"], -e["roe_2025"], e["symbol"]))
    return {"cara_menghitung": TEXT_ROE, "evaluable_count": evaluable, "excluded_over_100_percent": excluded, "top": entries[:top]}


def dividend_years(qv: dict) -> list[float]:
    vals = [qv.get(f"total_dividend[{y}]") for y in YEARS]
    return [v for v in vals if v is not None and v > 0]


def build_dividend_consistency(rows: list[dict], top: int = TOP_N) -> dict:
    entries = []
    for r in rows:
        paid = dividend_years(_qv(r))
        if not paid:
            continue
        cv = statistics.pstdev(paid) / statistics.fmean(paid)
        entries.append({
            "symbol": r["symbol"],
            "company_name": r.get("company_name"),
            "years_paid": len(paid),
            "of_years": len(YEARS),
            "variation": cv,
        })
    entries.sort(key=lambda e: (-e["years_paid"], e["variation"], e["symbol"]))
    return {"cara_menghitung": TEXT_DIVIDEND, "evaluable_count": len(entries), "top": entries[:top]}


def earnings_run(qv: dict) -> int:
    """Rising annual earnings ending 2025: consecutive years each above the previous, all positive."""
    run = 0
    for y in range(YEARS[-1], YEARS[0], -1):
        now, prev = qv.get(f"earnings[{y}]"), qv.get(f"earnings[{y - 1}]")
        if now is None or prev is None or prev <= 0 or now <= prev:
            break
        run += 1
    return run


def build_earnings_streaks(rows: list[dict], top: int = TOP_N) -> dict:
    entries = []
    for r in rows:
        run = earnings_run(_qv(r))
        if run > 0:
            entries.append({"symbol": r["symbol"], "company_name": r.get("company_name"), "rising_years": run})
    entries.sort(key=lambda e: (-e["rising_years"], e["symbol"]))
    longest = entries[0]["rising_years"] if entries else 0
    return {
        "cara_menghitung": TEXT_EARNINGS,
        "evaluable_count": len(entries),
        "longest_run": longest,
        "stocks_at_longest_run": sum(1 for e in entries if e["rising_years"] == longest),
        "top": entries[:top],
    }


def load_filings(path: Path, direction: str) -> list[dict]:
    """Filings with holdings on both sides; shares = |after - before| signed by `direction` ('buy' +, 'sell' -)."""
    seen = set()
    out = []
    with path.open() as f:
        for line in f:
            d = json.loads(line)
            before, after, sym = d.get("holding_before"), d.get("holding_after"), d.get("symbol")
            if sym is None or before is None or after is None:
                continue
            key = (sym, d.get("timestamp"), d.get("holder_name"), before, after, direction)
            if key in seen:
                continue
            seen.add(key)
            shares = abs(after - before)
            out.append({
                "symbol": sym,
                "signed_shares": shares if direction == "buy" else -shares,
                "takeover": TAKEOVER_TAG in (d.get("tags") or []),
            })
    return out


def _aggregate(filings: list[dict], shares_out: dict[str, float], names: dict) -> list[dict]:
    per: dict[str, dict] = {}
    for f in filings:
        p = per.setdefault(f["symbol"], {"buy": 0.0, "sell": 0.0, "n": 0})
        if f["signed_shares"] >= 0:
            p["buy"] += f["signed_shares"]
        else:
            p["sell"] += -f["signed_shares"]
        p["n"] += 1
    entries = []
    for sym, p in per.items():
        out_shares = shares_out.get(sym)
        if not out_shares:
            continue
        net = p["buy"] - p["sell"]
        ratio = net / out_shares
        entries.append({
            "symbol": sym,
            "company_name": names.get(sym),
            "buy_shares": p["buy"],
            "sell_shares": p["sell"],
            "net_shares": net,
            "share_of_outstanding": ratio,
            "n_filings": p["n"],
            "over_100_percent": abs(ratio) > 1.0,
        })
    return entries


def build_net_insider(rows: list[dict], filings: list[dict], top: int = TOP_N) -> dict:
    shares_out = {r["symbol"]: _qv(r).get("outstanding_shares[2025]") for r in rows}
    names = {r["symbol"]: r.get("company_name") for r in rows}
    regular = _aggregate([f for f in filings if not f["takeover"]], shares_out, names)
    tagged = _aggregate([f for f in filings if f["takeover"]], shares_out, names)
    # Net changes above 100% of outstanding shares are likely data artefacts or
    # takeover-scale events (lead decision 2026-09-26): kept out of the ranked
    # lists and reported separately so nothing is silently dropped.
    excluded = sorted((e for e in regular if e["over_100_percent"]), key=lambda e: e["symbol"])
    ranked = [e for e in regular if not e["over_100_percent"]]
    buyers = sorted((e for e in ranked if e["net_shares"] > 0), key=lambda e: (-e["share_of_outstanding"], e["symbol"]))
    sellers = sorted((e for e in ranked if e["net_shares"] < 0), key=lambda e: (e["share_of_outstanding"], e["symbol"]))
    tagged.sort(key=lambda e: (-abs(e["share_of_outstanding"]), e["symbol"]))
    return {
        "cara_menghitung": TEXT_INSIDER,
        "filings_used": len(filings),
        "filings_tagged_takeover": sum(1 for f in filings if f["takeover"]),
        "evaluable_count": len(ranked),
        "excluded_over_100_percent": excluded,
        "top_net_buyers": buyers[:top],
        "top_net_sellers": sellers[:top],
        "takeover_tagged_separate": tagged[:top],
    }


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    buys_path = latest_dated_file(RAW_DIR, INSIDER_BUYS_GLOB)
    sells_path = latest_dated_file(RAW_DIR, INSIDER_SELLS_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())
    filings = load_filings(buys_path, "buy") + load_filings(sells_path, "sell")

    derived = {
        "as_of": as_of,
        "source_files": [universe_path.name, buys_path.name, sells_path.name],
        "roe_vs_peers": build_roe_percentile(rows),
        "dividend_consistency": build_dividend_consistency(rows),
        "earnings_streaks": build_earnings_streaks(rows),
        "net_insider": build_net_insider(rows, filings),
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "rankings_derived.json"
    out_path.write_text(json.dumps(derived, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} (as_of {as_of})")
    for key in ("roe_vs_peers", "dividend_consistency", "earnings_streaks"):
        print(f"{key}: {derived[key]['evaluable_count']} evaluable, top {len(derived[key]['top'])}")
    ni = derived["net_insider"]
    print(
        f"net_insider: {ni['filings_used']} filings ({ni['filings_tagged_takeover']} takeover-tagged), "
        f"{ni['evaluable_count']} stocks, buyers {len(ni['top_net_buyers'])}, sellers {len(ni['top_net_sellers'])}, "
        f"takeover-tagged {len(ni['takeover_tagged_separate'])}"
    )
    es = derived["earnings_streaks"]
    print(f"earnings_streaks: longest run {es['longest_run']} years, {es['stocks_at_longest_run']} stocks at that length")


if __name__ == "__main__":
    main()
