"""Build data/app/stocks.json from the purchased universe sweep plus this
session's other appdata outputs.

Stock page sections 1-5 (docs/PRODUCT.md §4): snapshot, peer comparison,
flags & suspension history, beat-gold (§7.3), and now H1 resolved to this
stock (§5.2, via data/app/h1_applicability.json). The rest of the honesty
scoreboard (H4, H5, H10, H11, etc.) is NOT resolved per-stock here - only
H1 has a real, current, re-verified per-stock boundary condition; the
spec explicitly allows other findings to "apply broadly with a caveat
instead" rather than inventing a per-stock branch nothing supports. The
summary template lands separately.

Depends on: data/app/peer_groups.json, data/app/flags.json,
data/app/suspensions.json, data/app/lens_banking.json,
data/app/lens_extractive.json, data/app/beat_gold.json,
data/app/h1_applicability.json, data/app/insider_activity.json,
data/app/sector_breakdown.json, data/app/commodity_context.json,
data/app/corporate_actions.json, data/app/situations.json - run those
builders first.

Run: .venv/bin/python -m pipeline.appdata.build_stock_pages
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file, position_in_range

PEER_COMPARISON_METRIC = "roe_ttm"  # the one profitability field this sweep actually has


def _load_app_json(name: str) -> dict:
    path = APP_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found - run its builder first (pipeline/appdata/{name.replace('.json', '.py')} "
            f"or the matching build_*.py module)"
        )
    return json.loads(path.read_text())


def build_snapshot(row: dict) -> dict:
    qv = row["query_values"]
    return {
        "symbol": row["symbol"],
        "company_name": row["company_name"],
        "sector": qv.get("sector"),
        "sub_sector": qv.get("sub_sector"),
        "industry": qv.get("industry"),
        "sub_industry": qv.get("sub_industry"),
        "market_cap": qv.get("market_cap"),
        "market_cap_rank": qv.get("market_cap_rank"),
        "free_float": qv.get("free_float"),
        "last_close_price": qv.get("last_close_price"),
        "52_w_low_price": qv.get("52_w_low_price"),
        "52_w_high_price": qv.get("52_w_high_price"),
        "position_in_52w_range": position_in_range(
            qv.get("52_w_low_price"), qv.get("52_w_high_price"), qv.get("last_close_price")
        ),
        "listing_date": qv.get("listing_date"),
        "listing_board": qv.get("listing_board"),
    }


def build_peer_comparison(row: dict, rows_by_symbol: dict[str, dict], peer_groups: dict) -> dict | None:
    symbol = row["symbol"]
    assignment = peer_groups["assignments"].get(symbol)
    if assignment is None:
        return None
    group_key = f"{assignment['level']}:{assignment['group']}"
    peer_symbols = peer_groups["group_members"][group_key]

    own_value = row["query_values"].get(PEER_COMPARISON_METRIC)
    if own_value is None:
        return {
            "level": assignment["level"],
            "group": assignment["group"],
            "peer_count": len(peer_symbols),
            "metric": PEER_COMPARISON_METRIC,
            "own_value": None,
            "better_than_count": None,
            "comparable_count": None,
        }

    comparable_values = []
    better_than = 0
    for peer_symbol in peer_symbols:
        if peer_symbol == symbol:
            continue
        peer_row = rows_by_symbol.get(peer_symbol)
        if peer_row is None:
            continue
        peer_value = peer_row["query_values"].get(PEER_COMPARISON_METRIC)
        if peer_value is None:
            continue
        comparable_values.append(peer_value)
        if own_value > peer_value:
            better_than += 1

    return {
        "level": assignment["level"],
        "group": assignment["group"],
        "peer_count": len(peer_symbols),
        "metric": PEER_COMPARISON_METRIC,
        "own_value": own_value,
        "better_than_count": better_than,
        "comparable_count": len(comparable_values),
    }


def build_sector_context(row: dict, sector_breakdown: list[dict]) -> dict | None:
    """This stock's own ROE/P/E next to its SECTOR's typical values
    (`data/app/sector_breakdown.json`, built from the same universe sweep
    - zero extra Sectors cost). Deliberately separate from
    `build_peer_comparison`: that one ranks a stock against its narrowest
    valid cascade group (sub_industry/industry/sub_sector - PRODUCT.md §4
    rule 3, never coarsen a peer group silently, cigarette maker vs.
    bottled water). This one is not a peer ranking at all - it never
    counts "better than N of M" - it just states two real medians and the
    stock's own value side by side, which stays honest at the broader
    sector grain precisely because it makes no ranking claim.
    """
    sector = row["query_values"].get("sector")
    if sector is None:
        return None
    sector_row = next((s for s in sector_breakdown if s["sector"] == sector), None)
    if sector_row is None:
        return None
    own_roe_ttm = row["query_values"].get("roe_ttm")
    return {
        "sector": sector,
        "own_roe_pct": own_roe_ttm * 100 if own_roe_ttm is not None else None,
        "own_pe": row["query_values"].get("pe_ttm"),
        "sector_typical_roe_pct": sector_row["typical_roe_pct"],
        "sector_roe_n": sector_row["roe_n"],
        "sector_typical_pe": sector_row["typical_pe"],
        "sector_pe_n": sector_row["pe_n"],
        "sector_company_count": sector_row["company_count"],
    }


def build_lens_extractive_for_stock(entry: dict | None, commodity_context: dict) -> dict | None:
    """The stock's extractive-lens entry plus, for each commodity it is
    exposed to that we hold a price history for, that commodity's dated
    trend. Commodities with no fetched history (silver, aluminium, zinc/
    lead: too few listed miners to be worth a credit) are simply absent
    from `commodity_trends`, never filled with a guess."""
    if entry is None:
        return None
    trends = []
    for commodity in entry.get("commodity_type") or []:
        context = commodity_context.get(commodity)
        if context is not None:
            trends.append({"commodity": commodity, **context})
    return {**entry, "commodity_trends": trends}


def build_corporate_actions_for_stock(symbol: str, corporate_actions: dict) -> dict:
    """Always returns the window (so a page can say "nothing recorded between
    X and Y" rather than implying no events ever exist); the event lists are
    empty for a company with none in the window."""
    events = corporate_actions["by_symbol"].get(symbol) or {}
    return {
        "as_of": corporate_actions["as_of"],
        "window_start": corporate_actions["window"]["start"],
        "window_end": corporate_actions["window"]["end"],
        "dividends": events.get("dividends", []),
        "agms": events.get("agms", []),
        "rights_issues": events.get("rights_issues", []),
        "stock_splits": events.get("stock_splits", []),
    }


def build_suspension_history(symbol: str, suspensions: dict) -> dict | None:
    events = suspensions["by_symbol"].get(symbol)
    if not events:
        return None
    base_rate = suspensions["base_rates"].get(symbol)
    if base_rate is None:
        # `by_symbol` is built directly from raw suspension records;
        # `base_rates` only covers symbols in the universe snapshot
        # suspensions.json was last built against (build_suspensions.py's
        # build_base_rates). A symbol can have real events but no base
        # rate if it dropped out of the universe between builds - fail
        # loudly rather than silently drop real, purchased suspension
        # history for this symbol (verified live, 2026-09-19: HDTX.JK,
        # MFIN.JK, FREN.JK are in this exact state today, just not in the
        # current universe snapshot so this path isn't hit yet).
        raise ValueError(
            f"{symbol} has suspension events but no base_rates entry - "
            "rebuild data/app/suspensions.json against the same universe "
            "snapshot build_stock_pages.py is using"
        )
    return {
        "events": events,
        "count": base_rate["count"],
        "universe_count": suspensions["universe_count"],
        "companies_with_suspensions": suspensions["companies_with_suspensions"],
        "base_rate_pct": suspensions["base_rate_pct"],
        "more_than_pct": base_rate["more_than_pct"],
    }


def build_insider_activity_for_stock(symbol: str, insider_activity: dict) -> dict | None:
    """Section: "Aktivitas insider" (docs/PRODUCT.md - derived, not the
    raw filing feed; see build_insider_activity.py's own docstring for
    why only counts/direction/date ship, never a magnitude field)."""
    return insider_activity.get(symbol)


def build_h1_finding(symbol: str, h1_applicability: dict) -> dict | None:
    """Section 5 (docs/PRODUCT.md §5.2): H1 resolved to this specific
    stock, using data/app/h1_applicability.json's size-bucket/float-tercile
    placement. `state` is one of the four real renderings the spec
    describes - never a fifth invented state, never a bare number."""
    entry = h1_applicability.get(symbol)
    if entry is None:
        return None
    if not entry["size_bucket_significant"]:
        state = "weaker_evidence_for_size_range"
    elif entry["free_float_tercile"] == "high":
        state = "risky_side"
    elif entry["free_float_tercile"] == "low":
        state = "calm_side"
    else:
        state = "in_between"
    return {
        "state": state,
        "size_bucket": entry["size_bucket"],
        "free_float_tercile": entry["free_float_tercile"],
    }


def build_flags_for_stock(symbol: str, flags: dict) -> list[dict]:
    tripped = []
    flag_specs = [
        ("payout_above_earnings", "Bayar dividen > untung"),
        ("near_ath_earnings_decline", "Dekat titik tertinggi, tapi laba turun"),
        ("yield_far_above_average", "Dividen jauh di atas rata-rata sendiri"),
        ("lq45_low_float", "Kepemilikan publik kecil, meski masuk LQ45"),
    ]
    for key, label in flag_specs:
        bucket = flags[key]
        match = next((f for f in bucket["flagged"] if f["symbol"] == symbol), None)
        if match is not None:
            tripped.append({"key": key, "label": label, "detail": match})
    return tripped


def build_situations_for_stock(symbol: str, situations_by_symbol: dict) -> dict:
    entry = situations_by_symbol.get(symbol)
    if entry is None:
        # Every universe symbol gets an entry (all-null when in no situation),
        # so a missing one means situations.json was built against another
        # universe snapshot - fail loudly rather than show "no situation".
        raise ValueError(
            f"{symbol} has no entry in situations.json - rebuild it with "
            "pipeline.appdata.build_situations against the same universe snapshot"
        )
    return entry


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    as_of = universe_path.stem.replace("universe_", "")
    rows = json.loads(universe_path.read_text())
    rows_by_symbol = {row["symbol"]: row for row in rows}

    peer_groups = _load_app_json("peer_groups.json")
    flags = _load_app_json("flags.json")
    suspensions = _load_app_json("suspensions.json")
    lens_banking = _load_app_json("lens_banking.json")["banks"]
    lens_extractive = _load_app_json("lens_extractive.json")["miners"]
    beat_gold = _load_app_json("beat_gold.json")
    h1_applicability = _load_app_json("h1_applicability.json")["by_symbol"]
    insider_activity = _load_app_json("insider_activity.json")["by_symbol"]
    sector_breakdown = _load_app_json("sector_breakdown.json")["sectors"]
    commodity_context = _load_app_json("commodity_context.json")["commodities"]
    corporate_actions = _load_app_json("corporate_actions.json")
    situations = _load_app_json("situations.json")["by_symbol"]

    stocks = {}
    for row in rows:
        symbol = row["symbol"]
        stocks[symbol] = {
            "snapshot": build_snapshot(row),
            "peer_comparison": build_peer_comparison(row, rows_by_symbol, peer_groups),
            "sector_context": build_sector_context(row, sector_breakdown),
            "flags": build_flags_for_stock(symbol, flags),
            "suspension_history": build_suspension_history(symbol, suspensions),
            "lens_banking": lens_banking.get(symbol),
            "lens_extractive": build_lens_extractive_for_stock(lens_extractive.get(symbol), commodity_context),
            "beat_gold": beat_gold["by_symbol"].get(symbol),
            "h1_finding": build_h1_finding(symbol, h1_applicability),
            "insider_activity": build_insider_activity_for_stock(symbol, insider_activity),
            "corporate_actions": build_corporate_actions_for_stock(symbol, corporate_actions),
            "situations": build_situations_for_stock(symbol, situations),
        }

    output = {
        "as_of": as_of,
        "source_file": universe_path.name,
        "stocks": stocks,
    }

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "stocks.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} from {universe_path.name} (as_of {as_of})")
    print(f"{len(stocks)} companies, {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
