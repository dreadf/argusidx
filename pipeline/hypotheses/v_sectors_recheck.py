"""
V -- the three "proven" price-outcome results (cheap earnings multiple, small
size, high dividend yield) re-checked on Sectors' own closing prices.

Definitions frozen in EXPERIMENT.md ("Pre-registration, 2026-09-27 -- V"); run
once. NOT a new trial: it repeats tests already counted (H5, H10), so the trial
counter does not move. Only the H10 HOLDOUT is repeated (formation years 2024
and 2025, windows 2025-04-30 to 2025-09-04 and 2026-04-30 to 2026-09-04, the
dates H10's nearest-price rule selects). H10's own row builder and statistic are
used unchanged; only the price table is swapped.

Three runs, printed together:
  (a) research history, dividend-adjusted `adjclose` (the frozen H10 holdout);
  (b) research history, unadjusted `close` (the like-for-like reference, since
      Sectors closes are not adjusted for dividends);
  (c) Sectors closes.
(b) versus (c) isolates the price source; (a) versus (b) isolates dividend
adjustment. Decision per feature: "replicated" if the (c) rho has the sign of (a)
and p < 0.0167 (0.05 / 3); the price source is "inconsistent" if |rho(b) - rho(c)|
exceeds 0.02.

Run:
    .venv/bin/python -m pipeline.hypotheses.v_sectors_recheck
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from pipeline.hypotheses import h10_broad_feature_screen as h10
from pipeline.hypotheses.h5_value_size import HOLDOUT_YEARS, PRICES_5Y_PATH

REPO_ROOT = Path(__file__).resolve().parents[2]
CLOSES_PATH = REPO_ROOT / "data" / "raw" / "sectors_daily_close_2026-09-27.json"
OUT_PATH = REPO_ROOT / "data" / "app" / "sectors_recheck.json"

FEATURES = ("earnings_yield", "size", "total_yield")
ALPHA = 0.05 / 3
INCONSISTENT_GAP = 0.02


def _ts(day: str) -> float:
    return datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()


def sectors_price_table(closes: dict) -> tuple[dict, dict]:
    """{symbol: {timestamps, close, adjclose}} in the research cache's shape, from the
    saved Sectors pages, plus per-date ticker counts. Sectors closes are unadjusted, so
    `adjclose` is the same series as `close`."""
    table: dict = {}
    counts: dict = {}
    for day in sorted(closes):
        rows = [r for page in closes[day]["pages"].values() for r in page]
        counts[day] = len(rows)
        for r in rows:
            sym = r["symbol"] if r["symbol"].endswith(".JK") else r["symbol"] + ".JK"
            price = r.get("close")
            if price is None or price <= 0:
                continue
            e = table.setdefault(sym, {"timestamps": [], "close": [], "adjclose": []})
            e["timestamps"].append(_ts(day))
            e["close"].append(float(price))
            e["adjclose"].append(float(price))
    return table, counts


def run(universe: list[dict], prices: dict, label: str, field: str) -> dict:
    with mock.patch.object(h10, "RETURN_FIELD", field):
        res = h10.run_phase(universe, prices, HOLDOUT_YEARS, label)
    return {f: (None if res[f] is None else {"n": res[f][0].n, "rho": res[f][0].rho, "t": res[f][0].t, "p": res[f][1]}) for f in FEATURES}


def verdicts(a: dict, b: dict, c: dict) -> dict:
    out = {}
    for f in FEATURES:
        if a[f] is None or c[f] is None:
            out[f] = {"replicated": None, "price_source_inconsistent": None}
            continue
        same_sign = (a[f]["rho"] > 0) == (c[f]["rho"] > 0)
        out[f] = {
            "replicated": bool(same_sign and c[f]["p"] < ALPHA),
            "price_source_inconsistent": bool(b[f] is not None and abs(b[f]["rho"] - c[f]["rho"]) > INCONSISTENT_GAP),
        }
    return out


def main() -> None:
    universe = json.loads(h10.UNIVERSE_PATH.read_text())
    research = json.loads(PRICES_5Y_PATH.read_text())
    closes = json.loads(CLOSES_PATH.read_text())
    sectors, counts = sectors_price_table(closes)
    covered = sum(1 for r in universe if r.get("symbol") in sectors)
    print(f"Sectors closes per date: {counts}; universe symbols with a Sectors close: {covered} of {len(universe)}")

    a = run(universe, research, "(a) research adjclose", "adjclose")
    b = run(universe, research, "(b) research close (like-for-like)", "close")
    c = run(universe, sectors, "(c) Sectors closes", "close")
    v = verdicts(a, b, c)
    print("\nDecision per pre-registered rule:")
    for f in FEATURES:
        print(f"  {f:<16} (a) rho {a[f]['rho']:+.3f}  (b) rho {b[f]['rho']:+.3f}  (c) rho {c[f]['rho']:+.3f} p={c[f]['p']:.4f}  -> {v[f]}")
    OUT_PATH.write_text(json.dumps({"as_of": "2026-09-27", "coverage": {"universe": len(universe), "with_sectors_close": covered, "per_date": counts}, "adjclose": a, "close_research": b, "sectors": c, "verdict": v}, indent=1))
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
