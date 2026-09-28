"""Build data/app/market_analysis.json: two Pasar readings for the window
since the IHSG peak (plan `kind-juggling-hoare.md` §7, "Sejak puncak IHSG"
and "100 saham terbesar"), added alongside the existing Pasar sections, not
in place of them.

Descriptive, one snapshot, like R3/R4 (EXPERIMENT.md, 2026-09-28): no
explore/holdout split, no significance test. The window is the same
PEAK_DAY..WINDOW_END pair build_stock_profile.py already uses for
"sejak puncak IHSG" on the stock page, imported from there so the two
pages can never drift apart.

1. Who dragged total market value down. Each stock's share count is
   inferred, not measured: market_cap / last_close_price from the CURRENT
   universe snapshot (query_values, single point in time, no history),
   held constant back to PEAK_DAY. A buyback, rights issue or new listing
   between PEAK_DAY and now would misstate that stock's two values. This
   is a descriptive read of value, not a predictor of anything, so the
   snapshot-column rule (CLAUDE.md "Predictor before outcome") does not
   forbid it, but the constant-share assumption is still real and is
   disclosed on the card.
2. Among the 100 largest stocks by value at PEAK_DAY, how many rose
   since, and how many of those are commodity producers. PRODUCER is a
   fixed set of Sectors sub_industry values (checked against the live
   universe file 2026-09-28: every producer-like label in that field is
   one of these five, nothing was left out or invented).

Run: .venv/bin/python -m pipeline.appdata.build_market_analysis
"""
from __future__ import annotations

import json
import statistics

from pipeline.appdata.build_stock_profile import PEAK_DAY, PEAK_CLOSE_GLOB, DAILY_CLOSE_GLOB, WINDOW_START, WINDOW_END, closes_on
from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file
from pipeline.hypotheses.t1_market_state import load_ihsg

LQ45_GLOB = "lq45_????-??-??.json"
IDXHIDIV20_GLOB = "idxhidiv20_????-??-??.json"
LARGE_CAP_N = 100
DRAG_ROWS = 8
UP_ROWS = 8

# Sub-industries read as "commodity producers" for the large-cap resilience
# read. Checked against every sub_industry value in the live universe file
# (2026-09-28): these are the only producer-like labels; distribution/
# service labels (Coal Distribution, Oil & Gas Drilling Service, Oil & Gas
# Storage & Distribution, Oil, Gas & Coal Equipment & Services) are
# deliberately excluded, since they sell services around the commodity, not
# the commodity itself.
PRODUCER_SUB_INDUSTRIES = {"Coal Production", "Gold", "Diversified Metals & Minerals", "Oil & Gas Production & Refinery", "Plantations & Crops"}


def _index_series(path) -> dict[str, float]:
    return {r["date"]: r["price"] for r in json.loads(path.read_text())}


def build(rows: list[dict], peak_close: dict[str, float], end_close: dict[str, float]) -> dict:
    candidates = []
    for row in rows:
        sym, name, q = row["symbol"], row["company_name"], row["query_values"]
        p0, p1 = peak_close.get(sym), end_close.get(sym)
        mcap, last = q.get("market_cap"), q.get("last_close_price")
        if p0 is None or p1 is None or not mcap or not last:
            continue
        shares = mcap / last
        candidates.append({"symbol": sym, "company_name": name, "sub_industry": q.get("sub_industry"), "ret": p1 / p0 - 1, "m0": shares * p0, "m1": shares * p1})

    t0 = sum(r["m0"] for r in candidates)
    t1 = sum(r["m1"] for r in candidates)
    fall = t1 - t0
    drag = sorted(candidates, key=lambda r: r["m1"] - r["m0"])[:DRAG_ROWS]
    top5_share = sum((r["m1"] - r["m0"]) / fall for r in drag[:5]) if fall else None

    big = sorted(candidates, key=lambda r: -r["m0"])[:LARGE_CAP_N]
    up = sorted([r for r in big if r["ret"] > 0], key=lambda r: -r["ret"])
    n_producer = sum(r["sub_industry"] in PRODUCER_SUB_INDUSTRIES for r in up)

    return {
        "universe": {
            "n": len(candidates),
            "market_value_start": t0,
            "market_value_end": t1,
            "median_return": statistics.median(r["ret"] for r in candidates),
            "down": sum(1 for r in candidates if r["ret"] < 0),
        },
        "top5_drag_share": top5_share,
        "drag": [{"symbol": r["symbol"], "company_name": r["company_name"], "return": r["ret"], "value_change": r["m1"] - r["m0"], "drag_share": (r["m1"] - r["m0"]) / fall if fall else None} for r in drag],
        "large_caps": {
            "n": len(big),
            "n_up": len(up),
            "n_producer": n_producer,
            "median_return": statistics.median(r["ret"] for r in big),
            "up": [{"symbol": r["symbol"], "company_name": r["company_name"], "return": r["ret"]} for r in up[:UP_ROWS]],
        },
    }


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    daily_path = latest_dated_file(RAW_DIR, DAILY_CLOSE_GLOB)
    peak_path = latest_dated_file(RAW_DIR, PEAK_CLOSE_GLOB)
    lq45_path = latest_dated_file(RAW_DIR, LQ45_GLOB)
    idxhidiv20_path = latest_dated_file(RAW_DIR, IDXHIDIV20_GLOB)

    rows = json.loads(universe_path.read_text())
    daily = json.loads(daily_path.read_text())
    peak = json.loads(peak_path.read_text())
    end_close = closes_on(daily, WINDOW_END)
    peak_close = closes_on(peak, PEAK_DAY)

    dates, closes = load_ihsg()
    ihsg = dict(zip(dates, closes))
    lq45 = _index_series(lq45_path)
    idxhidiv20 = _index_series(idxhidiv20_path)
    for name, series in (("IHSG", ihsg), ("LQ45", lq45), ("IDXHIDIV20", idxhidiv20)):
        for day in (PEAK_DAY, WINDOW_START, WINDOW_END):
            if day not in series:
                raise KeyError(f"{name} has no close on {day}")

    def idx_row(code: str, label: str, series: dict[str, float]) -> dict:
        return {
            "code": code,
            "label": label,
            "change_since_peak": series[WINDOW_END] / series[PEAK_DAY] - 1,
            "change_1y": series[WINDOW_END] / series[WINDOW_START] - 1,
        }

    out = {
        "as_of": universe_path.stem.replace("universe_", ""),
        "source_files": [universe_path.name, daily_path.name, peak_path.name, lq45_path.name, idxhidiv20_path.name],
        "peak_window": {"start": PEAK_DAY, "end": WINDOW_END},
        "indices": [
            idx_row("IHSG", "semua saham", ihsg),
            idx_row("LQ45", "45 saham besar dan teramai", lq45),
            idx_row("IDXHIDIV20", "20 saham berdividen tinggi", idxhidiv20),
        ],
        **build(rows, peak_close, end_close),
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    path = APP_DIR / "market_analysis.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"Wrote {path} ({out['universe']['n']} stocks, top5_drag_share={out['top5_drag_share']:.3f}, large-cap up={out['large_caps']['n_up']}/{out['large_caps']['n']}, producers={out['large_caps']['n_producer']})")


if __name__ == "__main__":
    main()
