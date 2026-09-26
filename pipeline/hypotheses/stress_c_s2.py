"""
Stress tests ST1 (situation C, "Masih di bawah puncak lama") and ST2 (situation
S2, "Langganan suspensi"), pre-registered in EXPERIMENT.md ("Pre-registration,
2026-09-27 -- stress tests of the newest hypotheses and situations"), run once.

NOT new trials and not falsifiable hypotheses: no verdict changes. Only the
fragility rules below can flag a situation; no app flag threshold changes.
Owned data only (Yahoo research cache for C, the owned Sectors suspensions file
for S2), no API call.

Reproduction first. Before any variant each half recomputes the frozen figure
with its own generalised code and prints it next to the frozen value: C 121 of
999 (12.1%), S2 100 of 174 (57.5%). A mismatch stops that half.

ST1 (C). Recovery rate (share back at or above the pre-fall peak) among events
still below the peak `wait` bars after the trigger, judged `wait + 252` bars after
the trigger (the last bar stands in when the cache ends first, as in
`m_long_below_peak`); events with fewer than 200 bars after trigger + wait are left
out. Variants: (a) by trigger year; (b) the first such event per stock; (c) by
market-cap tercile (a snapshot, description only, not part of the fragility rule);
(d) trigger drop of -20% and -40% instead of -30%, wait of 126 and 378 bars instead
of 252, one parameter at a time. Reading choices left open by the text, stated
here: the outcome horizon stays one further year (252 bars) after the wait, so
only the wait changes; "the first" event is the first of the measured events
still below the peak. Fragile if the rate varies by more than 10 points across
trigger years, or the one-per-stock rate differs from the pooled rate by more than
5 points, or any sensitivity variant moves it by more than 5 points.

ST2 (S2). Same event and follow-up rule as `m_repeat_spike_suspension` (price-
increase suspensions, follow-up strictly after the event and within the window).
An event is eligible if its date is at least `window` days before the file's last
date (2026-09-11). Variants: (a) the first event per stock; (b) without the three
stocks with the most events (ties broken alphabetically, disclosed); (c) by year
of the stock's first event; (d) window 180 and 730 days; (e) the baseline: among
stocks with any price-increase suspension, the share that had one in an arbitrary
365-day window, over start dates from the first event date to the last eligible
event date (the same calendar span the 174 eligible events cover), compared with
the event rate. The baseline has no threshold; the other variants use the same
5/10-point rules.

Run:
    .venv/bin/python -m pipeline.hypotheses.stress_c_s2
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline.hypotheses._stress_common import (
    check_frozen,
    fmt_pct,
    fmt_rate,
    newcombe_diff,
    rate,
)
from pipeline.hypotheses.m_long_below_peak import build_long_below_peak
from pipeline.hypotheses.m_repeat_spike_suspension import (
    LAST_FULL_FOLLOW_UP_EVENT,
    build_repeat_spike_suspension,
    price_increase_events,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
MARKET_CAP_PATH = REPO_ROOT / "data" / "raw" / "market_cap_2026-09-06.json"
SUSPENSIONS_PATH = REPO_ROOT / "data" / "raw" / "suspensions_2026-09-13.json"

FALL_THRESHOLD = 0.70
WAIT_BARS = 252
OUTCOME_BARS = 252  # judged this many bars after the wait
MIN_BARS_AFTER = 200
MIN_HISTORY_BARS = 100
FROZEN_C = (121, 999)
FROZEN_S2 = (100, 174)
YEAR_RANGE_POINTS = 10.0
VARIANT_POINTS = 5.0

SUSPENSIONS_LAST_DATE = date(2026, 9, 11)
WINDOW_DAYS = 365


# ------------------------------------------------------------------ ST1 (C)
def usable_series(entry: dict | None) -> tuple[list[date], list[float]] | None:
    """(bar dates, closes) with the same filter as `m_long_below_peak.usable_closes`, or None."""
    if not entry:
        return None
    pairs = [
        (datetime.fromtimestamp(t, tz=timezone.utc).date(), c)
        for t, c in zip(entry.get("timestamps", []), entry.get("close", []))
        if c is not None and c > 0
    ]
    if len(pairs) < MIN_HISTORY_BARS:
        return None
    return [d for d, _ in pairs], [c for _, c in pairs]


def detect_falls(closes: list[float], threshold: float = FALL_THRESHOLD) -> list[dict]:
    """`m_recovery_after_fall._detect_fall_events` with the trigger level as a parameter (0.70 = the frozen one)."""
    events: list[dict] = []
    if not closes:
        return events
    peak, armed = closes[0], True
    for i, c in enumerate(closes):
        if c > peak:
            peak, armed = c, True
            continue
        if armed and c <= peak * threshold:
            events.append({"peak_price": peak, "trigger_idx": i})
            armed = False
    return events


def below_peak_events(
    dates: list[date], closes: list[float], threshold: float = FALL_THRESHOLD, wait: int = WAIT_BARS
) -> tuple[int, list[dict]]:
    """(measurable events, those still below the peak `wait` bars after the trigger, each with its outcome)."""
    last = len(closes) - 1
    measurable = 0
    below: list[dict] = []
    for ev in detect_falls(closes, threshold):
        t_wait = ev["trigger_idx"] + wait
        if last - t_wait < MIN_BARS_AFTER:
            continue
        measurable += 1
        if closes[t_wait] >= ev["peak_price"]:
            continue
        end = min(t_wait + OUTCOME_BARS, last)
        below.append(
            {
                "trigger_date": dates[ev["trigger_idx"]],
                "recovered": closes[end] >= ev["peak_price"],
                "truncated": t_wait + OUTCOME_BARS > last,
            }
        )
    return measurable, below


def c_rows(prices: dict, threshold: float = FALL_THRESHOLD, wait: int = WAIT_BARS) -> tuple[int, list[dict]]:
    """Every still-below event over the cache: {sym, trigger_date, recovered, truncated}, and the measurable count."""
    measurable = 0
    rows: list[dict] = []
    for sym in sorted(prices):
        s = usable_series(prices[sym])
        if s is None:
            continue
        m, below = below_peak_events(s[0], s[1], threshold, wait)
        measurable += m
        rows.extend({"sym": sym, **b} for b in below)
    return measurable, rows


def c_rate(rows: list[dict]) -> dict:
    return rate(sum(r["recovered"] for r in rows), len(rows))


def first_per_stock(rows: list[dict]) -> list[dict]:
    """The earliest event of each stock (rows are in symbol order, then trigger order)."""
    seen: set[str] = set()
    out = []
    for r in rows:
        if r["sym"] not in seen:
            seen.add(r["sym"])
            out.append(r)
    return out


def size_terciles(market_cap: dict[str, float], symbols: list[str]) -> dict[str, str]:
    """smallest / mid / largest by market cap over `symbols` with a cap; sorted (cap, symbol), n // 3 each, remainder to the largest."""
    ranked = sorted((s for s in symbols if market_cap.get(s)), key=lambda s: (market_cap[s], s))
    k = len(ranked) // 3
    out = {}
    for i, s in enumerate(ranked):
        out[s] = "smallest" if i < k else ("mid" if i < 2 * k else "largest")
    return out


def load_market_cap(path: Path = MARKET_CAP_PATH) -> dict[str, float]:
    out = {}
    for r in json.loads(path.read_text()):
        mc = (r.get("query_values") or {}).get("market_cap")
        if mc is not None:
            out[r["symbol"]] = mc
    return out


def c_clusters(rows: list[dict]) -> dict[str, tuple[int, int]]:
    """stock -> (recovered, events) for the cluster bootstrap in ST0."""
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in rows:
        acc[r["sym"]][0] += int(r["recovered"])
        acc[r["sym"]][1] += 1
    return {k: (v[0], v[1]) for k, v in acc.items()}


def run_st1(prices: dict, market_cap: dict[str, float]) -> dict:
    print("=" * 78)
    print("ST1 -- situation C (still below the old peak), recovery rate")
    print("=" * 78)
    measurable, rows = c_rows(prices)
    pooled = c_rate(rows)
    cross = build_long_below_peak(prices)
    print("Reproduction (before any variant):")
    ok = check_frozen("C recovered / still-below", (pooled["count"], pooled["n"]), FROZEN_C)
    ok &= check_frozen("C measurable events (m_long_below_peak)", measurable, cross["events_measurable"])
    if not ok:
        print("STOP: frozen C figure not reproduced; no variant computed.")
        return {"reproduced": False}
    print(f"  pooled: {fmt_rate(pooled)}  distinct stocks: {len(c_clusters(rows))}\n")

    out: dict = {"reproduced": True, "pooled": pooled, "variants": {}}
    variants_examined = 0

    # (a) by trigger year
    by_year: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_year[r["trigger_date"].year].append(r)
    year_rates = {y: c_rate(v) for y, v in sorted(by_year.items())}
    print("(a) by trigger year")
    for y, r in year_rates.items():
        print(f"    {y}: {fmt_rate(r)}")
    spread_pts = (max(r["rate"] for r in year_rates.values()) - min(r["rate"] for r in year_rates.values())) * 100
    fragile_year = spread_pts > YEAR_RANGE_POINTS
    print(f"    range across years: {spread_pts:.1f} points  -> {'FRAGILE (> 10 points)' if fragile_year else 'not fragile (<= 10 points)'}")
    out["variants"]["a_by_trigger_year"] = {"rates": {str(y): r for y, r in year_rates.items()}, "range_points": spread_pts, "fragile": fragile_year}
    variants_examined += 1

    # (b) one event per stock
    one = c_rate(first_per_stock(rows))
    diff_b = (one["rate"] - pooled["rate"]) * 100
    fragile_b = abs(diff_b) > VARIANT_POINTS
    print(f"(b) first event per stock: {fmt_rate(one)}  vs pooled {diff_b:+.1f} points -> {'FRAGILE (> 5 points)' if fragile_b else 'not fragile'}")
    out["variants"]["b_one_per_stock"] = {"rate": one, "diff_points": diff_b, "fragile": fragile_b}
    variants_examined += 1

    # (c) size tercile, description only
    tercile = size_terciles(market_cap, list(prices))
    print("(c) by market-cap tercile (snapshot cap, description only, not in the fragility rule)")
    c_out = {}
    for name in ("smallest", "mid", "largest"):
        sub = [r for r in rows if tercile.get(r["sym"]) == name]
        c_out[name] = c_rate(sub)
        print(f"    {name}: {fmt_rate(c_out[name])}")
    out["variants"]["c_size_tercile"] = c_out
    variants_examined += 1

    # (d) sensitivity: one parameter at a time
    print("(d) sensitivity (one parameter at a time)")
    d_out = {}
    fragile_d = []
    for label, thr, wait in (
        ("trigger -20%", 0.80, WAIT_BARS),
        ("trigger -40%", 0.60, WAIT_BARS),
        ("wait 126", FALL_THRESHOLD, 126),
        ("wait 378", FALL_THRESHOLD, 378),
    ):
        m, v_rows = c_rows(prices, thr, wait)
        r = c_rate(v_rows)
        diff = (r["rate"] - pooled["rate"]) * 100 if r["n"] else float("nan")
        frag = r["n"] > 0 and abs(diff) > VARIANT_POINTS
        if frag:
            fragile_d.append(label)
        print(f"    {label}: measurable {m}, {fmt_rate(r)}  vs pooled {diff:+.1f} points -> {'FRAGILE (> 5 points)' if frag else 'not fragile'}")
        d_out[label] = {"measurable": m, "rate": r, "diff_points": diff, "fragile": frag}
        variants_examined += 1
    out["variants"]["d_sensitivity"] = d_out

    out["variants_examined"] = variants_examined
    out["fragile"] = fragile_year or fragile_b or bool(fragile_d)
    print(f"\nVariants examined for ST1: {variants_examined} (a: by-year table, b, c, d: 4)")
    print(f"ST1 fragility: by-year {fragile_year}, one-per-stock {fragile_b}, sensitivity {fragile_d or 'none'} -> overall {'FRAGILE' if out['fragile'] else 'not fragile'}")
    return out


# ------------------------------------------------------------------ ST2 (S2)
def _last_eligible(window: int) -> date:
    return SUSPENSIONS_LAST_DATE - timedelta(days=window)


def followed(dates: list[date], event: date, window: int) -> bool:
    """Another event strictly after `event` and within `window` days."""
    return any(0 < (d - event).days <= window for d in dates)


def s2_events(events: dict[str, list[date]], window: int = WINDOW_DAYS, exclude: set[str] | None = None) -> list[dict]:
    """Eligible events {sym, date, followed}: event date on or before last date - window, same-stock same-date already merged."""
    cutoff = _last_eligible(window)
    rows = []
    for sym in sorted(events):
        if exclude and sym in exclude:
            continue
        for d in events[sym]:
            if d <= cutoff:
                rows.append({"sym": sym, "date": d, "followed": followed(events[sym], d, window)})
    return rows


def s2_rate(rows: list[dict]) -> dict:
    return rate(sum(r["followed"] for r in rows), len(rows))


def s2_clusters(rows: list[dict]) -> dict[str, tuple[int, int]]:
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in rows:
        acc[r["sym"]][0] += int(r["followed"])
        acc[r["sym"]][1] += 1
    return {k: (v[0], v[1]) for k, v in acc.items()}


def first_event_rows(events: dict[str, list[date]], window: int = WINDOW_DAYS) -> list[dict]:
    """One row per stock: its first event, if that event is eligible."""
    cutoff = _last_eligible(window)
    return [
        {"sym": sym, "date": ds[0], "followed": followed(ds, ds[0], window)}
        for sym, ds in sorted(events.items())
        if ds and ds[0] <= cutoff
    ]


def top_event_stocks(events: dict[str, list[date]], k: int = 3) -> tuple[list[str], list[str]]:
    """The k stocks with the most events (ties broken alphabetically) and every stock tied at the cut count."""
    ranked = sorted(events, key=lambda s: (-len(events[s]), s))
    chosen = ranked[:k]
    cut = len(events[chosen[-1]])
    tied = [s for s in ranked if len(events[s]) == cut]
    return chosen, tied


def window_baseline(events: dict[str, list[date]], window: int = WINDOW_DAYS) -> dict:
    """Share of stocks (each with at least one event) having an event in (s, s + window] for each start day s.

    Start days run daily from the first event date to the last eligible event date, so the span is
    the one the eligible events cover. Returns the mean over start days, the min and the max.
    """
    stocks = sorted(events)
    first = min(d for ds in events.values() for d in ds)
    last_start = _last_eligible(window)
    shares = []
    s = first
    while s <= last_start:
        hit = sum(1 for sym in stocks if any(0 < (d - s).days <= window for d in events[sym]))
        shares.append(hit / len(stocks))
        s += timedelta(days=1)
    mean = sum(shares) / len(shares)
    return {
        "n_stocks": len(stocks),
        "start_first": first.isoformat(),
        "start_last": last_start.isoformat(),
        "n_start_days": len(shares),
        "mean_share": mean,
        "min_share": min(shares),
        "max_share": max(shares),
    }


def run_st2(suspensions: list[dict]) -> dict:
    print("=" * 78)
    print("ST2 -- situation S2 (repeat price-increase suspension)")
    print("=" * 78)
    events = price_increase_events(suspensions)
    rows = s2_events(events)
    pooled = s2_rate(rows)
    cross = build_repeat_spike_suspension(suspensions)
    print("Reproduction (before any variant):")
    ok = check_frozen("S2 followed / eligible", (pooled["count"], pooled["n"]), FROZEN_S2)
    ok &= check_frozen("S2 (m_repeat_spike_suspension)", (cross["followed_within_365d"], cross["eligible_events"]), FROZEN_S2)
    ok &= check_frozen("S2 last eligible date", _last_eligible(WINDOW_DAYS), LAST_FULL_FOLLOW_UP_EVENT)
    if not ok:
        print("STOP: frozen S2 figure not reproduced; no variant computed.")
        return {"reproduced": False}
    n_events = sum(len(v) for v in events.values())
    all_dates = sorted(d for v in events.values() for d in v)
    print(f"  pooled: {fmt_rate(pooled)}  distinct stocks in the 174: {len(s2_clusters(rows))}; all events {n_events} over {len(events)} stocks, dated {all_dates[0]} to {all_dates[-1]}\n")

    out: dict = {"reproduced": True, "pooled": pooled, "variants": {}}
    examined = 0

    # (a) one per stock
    one_rows = first_event_rows(events)
    one = s2_rate(one_rows)
    diff_a = (one["rate"] - pooled["rate"]) * 100
    fragile_a = abs(diff_a) > VARIANT_POINTS
    print(f"(a) first event per stock: {fmt_rate(one)}  vs pooled {diff_a:+.1f} points -> {'FRAGILE (> 5 points)' if fragile_a else 'not fragile'}")
    out["variants"]["a_one_per_stock"] = {"rate": one, "diff_points": diff_a, "fragile": fragile_a}
    examined += 1

    # (b) leave out the three stocks with the most events
    top, tied = top_event_stocks(events)
    rest = s2_rate(s2_events(events, exclude=set(top)))
    diff_b = (rest["rate"] - pooled["rate"]) * 100
    fragile_b = abs(diff_b) > VARIANT_POINTS
    counts = ", ".join(f"{s} ({len(events[s])})" for s in top)
    print(f"(b) without the three stocks with the most events [{counts}; {len(tied)} stocks tie at the cut count, alphabetical tie-break]:")
    print(f"    {fmt_rate(rest)}  vs pooled {diff_b:+.1f} points -> {'FRAGILE (> 5 points)' if fragile_b else 'not fragile'}")
    out["variants"]["b_without_top3"] = {"left_out": top, "tied_at_cut": tied, "rate": rest, "diff_points": diff_b, "fragile": fragile_b}
    examined += 1

    # (c) by year of the stock's first event
    print("(c) by year of the stock's first event (first event per stock, eligible only)")
    by_year: dict[int, list[dict]] = defaultdict(list)
    for r in one_rows:
        by_year[r["date"].year].append(r)
    year_rates = {y: s2_rate(v) for y, v in sorted(by_year.items())}
    for y, r in year_rates.items():
        print(f"    {y}: {fmt_rate(r)}")
    later = sum(1 for ds in events.values() if ds[0] > _last_eligible(WINDOW_DAYS))
    print(f"    ({later} stocks have a first event after {_last_eligible(WINDOW_DAYS)}: no full 365 days, not measurable)")
    if len(year_rates) >= 2:
        rng = (max(r["rate"] for r in year_rates.values()) - min(r["rate"] for r in year_rates.values())) * 100
        fragile_c = rng > YEAR_RANGE_POINTS
        print(f"    range across years: {rng:.1f} points -> {'FRAGILE (> 10 points)' if fragile_c else 'not fragile'}")
    else:
        rng, fragile_c = None, None
        print("    only one first-event year is measurable, so the 10-point year rule cannot be evaluated")
    out["variants"]["c_by_first_event_year"] = {"rates": {str(y): r for y, r in year_rates.items()}, "range_points": rng, "fragile": fragile_c, "not_measurable_stocks": later}
    examined += 1

    # (d) follow-up window
    print("(d) follow-up window")
    d_out = {}
    fragile_d = []
    for w in (180, 730):
        w_rows = s2_events(events, w)
        r = s2_rate(w_rows)
        if r["n"]:
            diff = (r["rate"] - pooled["rate"]) * 100
            frag = abs(diff) > VARIANT_POINTS
            if frag:
                fragile_d.append(w)
            print(f"    {w} days (events on or before {_last_eligible(w)}): {fmt_rate(r)}  vs pooled {diff:+.1f} points -> {'FRAGILE (> 5 points)' if frag else 'not fragile'}")
        else:
            diff, frag = None, None
            print(f"    {w} days (events on or before {_last_eligible(w)}): 0 eligible events (first event is {all_dates[0]}): not computable")
        d_out[str(w)] = {"rate": r, "diff_points": diff, "fragile": frag, "last_eligible_event": _last_eligible(w).isoformat()}
        examined += 1
    out["variants"]["d_window"] = d_out

    # (e) baseline
    base = window_baseline(events)
    approx = rate(round(base["mean_share"] * base["n_stocks"]), base["n_stocks"])
    diff_e = newcombe_diff(pooled["count"], pooled["n"], approx["count"], approx["n"])
    print("(e) baseline: share of stocks with any price-increase suspension that had one in an arbitrary 365-day window")
    print(f"    {base['n_stocks']} stocks, window start days {base['start_first']} to {base['start_last']} ({base['n_start_days']} days)")
    print(f"    mean {fmt_pct(base['mean_share'])} (min {fmt_pct(base['min_share'])}, max {fmt_pct(base['max_share'])})")
    print(f"    S2 event rate {fmt_pct(pooled['rate'])} vs baseline {fmt_pct(base['mean_share'])}: {diff_e['diff'] * 100:+.1f} points "
          f"[Newcombe {diff_e['low'] * 100:+.1f} to {diff_e['high'] * 100:+.1f}; baseline count rounded to {approx['count']} of {approx['n']}, windows overlap so the interval is indicative only]")
    out["variants"]["e_baseline"] = {**base, "difference_vs_s2": diff_e}
    examined += 1

    out["variants_examined"] = examined
    fragile_list = [k for k, v in (("a", fragile_a), ("b", fragile_b), ("c", fragile_c), ("d", bool(fragile_d))) if v]
    out["fragile"] = bool(fragile_list)
    print(f"\nVariants examined for ST2: {examined} (a, b, c, d: 2, e)")
    print(f"ST2 fragility: variants triggering a rule: {fragile_list or 'none'} (d windows: {fragile_d or 'none'})")
    return out


def main() -> None:
    prices = json.loads(PRICES_5Y_PATH.read_text())
    market_cap = load_market_cap()
    suspensions = json.loads(SUSPENSIONS_PATH.read_text())
    run_st1(prices, market_cap)
    print()
    run_st2(suspensions)


if __name__ == "__main__":
    main()
