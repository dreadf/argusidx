"""Build data/app/base_rate_uncertainty.json -- ST0 of EXPERIMENT.md's
"Pre-registration, 2026-09-27 -- stress tests of the newest hypotheses and
situations": an uncertainty interval for every proportion the app quotes as
"N dari 100".

Per rate: the count, n and a Wilson 95% interval. For the event-based rates where
one stock contributes several events (situation C, situation S2, the recent
spike), also a cluster bootstrap that resamples STOCKS (B = 2,000, seed 20260927)
and the number of distinct stocks. Rule (pre-registered): an interval wider than
20 percentage points is marked `wide` (the page says "lebar"); `wide` uses the
widest interval available for the rate (Wilson, and the cluster interval where it
exists).

Schema (all proportions are fractions in [0, 1]; `width_points` is in percentage
points):

    {
      "as_of": "2026-09-13",              # date of the data behind the rates (base_rates.json's)
      "computed_on": "2026-09-27",
      "method": {...},                    # what each field means
      "rates": {
        "<key>": {
          "situation": "<group>",         # which base rate / situation
          "label": "<what the proportion is>",
          "count": int, "n": int, "rate": float,
          "wilson_low": float, "wilson_high": float,
          "n_stocks": int | null,         # distinct stocks behind n; null when not computed
          "cluster_low": float | null,    # stock-cluster bootstrap 95%; only where pre-registered
          "cluster_high": float | null,
          "width_points": float,          # widest available interval, in points
          "wide": bool,                   # width_points > 20
          "as_of": "2026-09-13"
        }
      }
    }

Derived facts only, same compliance shape as `build_base_rates.py`: the Yahoo
research cache is read at build time and only counts and intervals are written,
never a price series. Each rate's count and n are checked against the figure
already in `data/app/base_rates.json` / `ipo_boards.json` / `suspensions.json`
before the file is written; a mismatch raises instead of writing.

Run: .venv/bin/python -m pipeline.appdata.build_base_rate_uncertainty
"""
from __future__ import annotations

import json
from collections import defaultdict

from pipeline.appdata.build_base_rates import build_loss_maker_rows
from pipeline.appdata.build_ipo_boards import ALL_BOARDS, EXPLORE_YEARS as IPO_EXPLORE, HOLDOUT_YEARS as IPO_HOLDOUT
from pipeline.appdata.build_ipo_boards import HORIZONS_DAYS as IPO_HORIZONS
from pipeline.appdata.build_ipo_boards import _parse_listings, build_rows as ipo_build_rows
from pipeline.appdata.common import APP_DIR, RAW_DIR, REPO_ROOT, UNIVERSE_GLOB, latest_dated_file
from pipeline.hypotheses import h11_suspension_underperformance as h11
from pipeline.hypotheses._stress_common import (
    BOOTSTRAP_B,
    SEED,
    WIDE_POINTS,
    cluster_bootstrap_rate,
    is_wide,
    rate,
)
from pipeline.hypotheses.h4_payout_dividend_cuts import EXPLORE_YEARS, HOLDOUT_YEARS, build_pooled_rows
from pipeline.hypotheses.h4_payout_dividend_cuts import UNIVERSE_PATH as H4_UNIVERSE_PATH
from pipeline.hypotheses.m_dividend_streaks import END_YEARS, STREAK_LENGTHS, streak_cell
from pipeline.hypotheses.m_earnings_streaks import doubled_rows, two_year_decline_rows
from pipeline.hypotheses.m_payout_flag_check import PAYOUT_RATIO_THRESHOLD
from pipeline.hypotheses.m_recent_spike import detect_spike_events, event_outcome, usable_closes
from pipeline.hypotheses.m_repeat_spike_suspension import price_increase_events
from pipeline.hypotheses.m_yield_spike_cut import build_yield_spike_cut
from pipeline.hypotheses.stress_baselines import i3_year
from pipeline.hypotheses.stress_c_s2 import c_clusters, c_rows, s2_clusters, s2_events

PRICES_5Y_PATH = REPO_ROOT / "data" / "dev_cache" / "prices_5y.json"
BENCHMARKS_PATH = REPO_ROOT / "data" / "dev_cache" / "benchmarks_5y.json"
AS_OF = "2026-09-13"
COMPUTED_ON = "2026-09-27"
I3_YEARS = [2022, 2023, 2024]


def entry(
    key: str,
    situation: str,
    label: str,
    count: int,
    n: int,
    *,
    n_stocks: int | None = None,
    clusters: dict[str, tuple[int, int]] | None = None,
) -> dict:
    """One rate with its Wilson interval and, if `clusters` is given, the stock-cluster bootstrap interval."""
    r = rate(count, n)
    cl = cluster_bootstrap_rate(clusters) if clusters else None
    widths = [(r["wilson_high"] - r["wilson_low"]) if r["n"] else None]
    if cl:
        widths.append(cl["high"] - cl["low"])
    real = [w for w in widths if w is not None]
    return {
        "key": key,
        "situation": situation,
        "label": label,
        "count": count,
        "n": n,
        "rate": r["rate"],
        "wilson_low": r["wilson_low"],
        "wilson_high": r["wilson_high"],
        "n_stocks": n_stocks,
        "cluster_low": cl["low"] if cl else None,
        "cluster_high": cl["high"] if cl else None,
        "width_points": (max(real) * 100) if real else None,
        "wide": is_wide(*widths),
        "as_of": AS_OF,
    }


def _clusters(pairs: list[tuple[str, bool]]) -> dict[str, tuple[int, int]]:
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for sym, hit in pairs:
        acc[sym][0] += int(hit)
        acc[sym][1] += 1
    return {k: (v[0], v[1]) for k, v in acc.items()}


# --------------------------------------------------------------- collectors
def collect_recent_spike(prices: dict) -> list[dict]:
    """Recent spike (S1): events closing lower 60 bars later, pooled with a stock-cluster bootstrap, and one event per stock."""
    pairs: list[tuple[str, bool]] = []
    first: list[bool] = []
    for sym in sorted(prices):
        closes = usable_closes(prices[sym])
        if closes is None:
            continue
        outcomes = [o for o in (event_outcome(closes, i) for i in detect_spike_events(closes)) if o is not None]
        pairs.extend((sym, o["change"] < 0) for o in outcomes)
        if outcomes:
            first.append(outcomes[0]["change"] < 0)
    pooled_clusters = _clusters(pairs)
    return [
        entry("recent_spike_pooled", "recent_spike", "events closing lower 60 trading days after a 40%+ jump in 20 days", sum(h for _, h in pairs), len(pairs), n_stocks=len(pooled_clusters), clusters=pooled_clusters),
        entry("recent_spike_first_event_per_stock", "recent_spike", "first event per stock closing lower 60 trading days later", sum(first), len(first), n_stocks=len(first)),
    ]


def collect_suspensions(suspensions_app: dict, suspensions_raw: list[dict], prices: dict, jkse: dict) -> list[dict]:
    """34 dari 100 ever suspended, and H11's share trailing the index over 90 days (holdout 2026 and explore 2025)."""
    out = [
        entry(
            "ever_suspended",
            "ever_suspended",
            "listed companies with at least one suspension",
            suspensions_app["companies_with_suspensions"],
            suspensions_app["universe_count"],
            n_stocks=suspensions_app["companies_with_suspensions"],
        )
    ]
    events = h11._parse_events(suspensions_raw)
    for phase, year in (("holdout", 2026), ("explore", 2025)):
        rows = h11.build_rows([e for e in events if e["t0"].year == year], prices, jkse)
        pairs = [(r["sym"], r["ret_90d"] <= r["jkse_90d"]) for r in rows if r["ret_90d"] is not None and r["jkse_90d"] is not None]
        out.append(
            entry(
                f"price_spike_suspension_trailed_index_90d_{phase}",
                "price_spike_suspension",
                f"price-increase suspensions whose stock did not beat the index over the next 90 days ({phase} {year})",
                sum(h for _, h in pairs),
                len(pairs),
                n_stocks=len({s for s, _ in pairs}),
            )
        )
    return out


def collect_s2(suspensions_raw: list[dict]) -> list[dict]:
    events = price_increase_events(suspensions_raw)
    rows = s2_events(events)
    cl = s2_clusters(rows)
    repeat = sum(1 for v in events.values() if len(v) >= 2)
    return [
        entry("s2_followed_within_365d", "s2", "eligible price-increase suspensions followed by another within 365 days", sum(r["followed"] for r in rows), len(rows), n_stocks=len(cl), clusters=cl),
        entry("s2_stocks_with_2_or_more", "s2", "stocks with a price-increase suspension that have two or more", repeat, len(events), n_stocks=len(events)),
    ]


def collect_c(prices: dict) -> list[dict]:
    _, rows = c_rows(prices)
    cl = c_clusters(rows)
    return [entry("c_recovered_by_trigger_plus_504", "c", "still-below-the-peak events back at or above the peak a year later", sum(r["recovered"] for r in rows), len(rows), n_stocks=len(cl), clusters=cl)]


def collect_i2(h4_universe: list[dict]) -> list[dict]:
    out = []
    for phase, years in (("explore", EXPLORE_YEARS), ("holdout", HOLDOUT_YEARS)):
        rows = [r for r in build_pooled_rows(h4_universe, years) if r["payout_ratio"] > PAYOUT_RATIO_THRESHOLD]
        out.append(entry(f"i2_payout_above_100_cut_{phase}", "i2", f"stock-years with payout above 100% followed by a dividend cut (H4 {phase} years)", int(sum(r["cut"] for r in rows)), len(rows), n_stocks=len({r["sym"] for r in rows})))
    return out


def collect_i3(universe: list[dict], prices: dict) -> list[dict]:
    out = []
    years = [i3_year(universe, prices, y) for y in I3_YEARS]
    cells = [(str(y["year"]), [y]) for y in years] + [("pooled", years)]
    for label, ys in cells:
        n = sum(len(y["flagged"]) for y in ys)
        out.append(entry(f"i3_{label}_negative_return", "i3", f"near-the-high, earnings-down stock-years with a negative 1 May to 4 Sep return ({label})", sum(r < 0 for y in ys for r in y["flagged"]), n))
        out.append(entry(f"i3_{label}_beat_median", "i3", f"near-the-high, earnings-down stock-years beating the median stock ({label})", sum(r > y["median"] for y in ys for r in y["flagged"]), n))
    return out


def collect_i6(universe: list[dict]) -> list[dict]:
    out = []
    for n_years in STREAK_LENGTHS:
        for y in END_YEARS:
            cell = streak_cell(universe, n_years, y)
            if cell is None:
                continue
            a, b = cell["paid_again"], cell["paid_at_least_as_much"]
            out.append(entry(f"i6_paid_again_N{n_years}_Y{y}", "i6", f"payers with a {n_years}-year streak ending {y} that paid again in {y + 1}", a["count"], a["n"], n_stocks=a["n"]))
            out.append(entry(f"i6_paid_at_least_as_much_N{n_years}_Y{y}", "i6", f"payers with a {n_years}-year streak ending {y} that paid at least as much in {y + 1}", b["count"], b["n"], n_stocks=b["n"]))
    return out


def collect_i9(universe: list[dict]) -> list[dict]:
    r = build_yield_spike_cut(universe)[2024]["cut_missing_counted_as_cut"]
    return [entry("i9_cut_Y2024", "i9", "stocks with a yield 1.5x or more above their own average in 2024 that cut the 2025 dividend (missing counted as a cut)", r["count"], r["n"], n_stocks=r["n"])]


def collect_loss_turnaround(universe: list[dict]) -> list[dict]:
    rows = build_loss_maker_rows(universe)
    out = [entry("loss_turnaround_pooled", "loss_turnaround", "loss-making company-years that were profitable the next year", sum(r["turned_around"] for r in rows), len(rows), n_stocks=len({r["sym"] for r in rows}))]
    for y in (2021, 2022, 2023, 2024):
        sub = [r for r in rows if r["year"] == y]
        out.append(entry(f"loss_turnaround_{y}", "loss_turnaround", f"loss-making {y} company-years that were profitable in {y + 1}", sum(r["turned_around"] for r in sub), len(sub), n_stocks=len({r["sym"] for r in sub})))
    return out


def collect_earnings(universe: list[dict]) -> list[dict]:
    out = []
    rows = two_year_decline_rows(universe, [2023, 2024])
    out.append(entry("earnings_two_year_decline_rose_pooled", "earnings_two_year_decline", "two-year earnings decliners whose earnings rose the next year", sum(r["rose_next_year"] for r in rows), len(rows)))
    for y in (2023, 2024):
        sub = [r for r in rows if r["year"] == y]
        out.append(entry(f"earnings_two_year_decline_rose_{y}", "earnings_two_year_decline", f"two-year earnings decliners ({y}) whose earnings rose the next year", sum(r["rose_next_year"] for r in sub), len(sub)))
    d_rows = doubled_rows(universe, [2022, 2023, 2024])
    for field, text in (("gave_part_back", "were lower the next year"), ("gave_all_back", "ended below the pre-jump level")):
        out.append(entry(f"earnings_more_than_doubled_{field}_pooled", "earnings_more_than_doubled", f"companies whose earnings more than doubled and {text}", sum(r[field] for r in d_rows), len(d_rows)))
        for y in (2022, 2023, 2024):
            sub = [r for r in d_rows if r["year"] == y]
            out.append(entry(f"earnings_more_than_doubled_{field}_{y}", "earnings_more_than_doubled", f"companies ({y}) whose earnings more than doubled and {text}", sum(r[field] for r in sub), len(sub)))
    return out


def collect_ipo(universe: list[dict], prices: dict) -> list[dict]:
    listings = _parse_listings(universe)
    out = []
    for phase, years in (("explore", IPO_EXPLORE), ("holdout", IPO_HOLDOUT)):
        rows = ipo_build_rows([ev for ev in listings if ev["year"] in years], prices)
        for h in IPO_HORIZONS:
            for board in ALL_BOARDS:
                rets = [r[f"ret_{h}d"] for r in rows if r["board"] == board and r[f"ret_{h}d"] is not None]
                if not rets:
                    continue
                out.append(entry(f"ipo_{phase}_{h}d_{board.replace(' ', '_')}_negative", "ipo_board", f"{board} board IPOs below their first-day close after {h} days ({phase})", sum(x < 0 for x in rets), len(rets), n_stocks=len(rets)))
    return out


# --------------------------------------------------------------- guards
def check_against_app_files(rates: dict[str, dict], base_rates: dict, ipo_boards: dict) -> None:
    """Raise if a recomputed count/n differs from the figure the app already ships."""
    expected: dict[str, tuple[int, int]] = {
        "c_recovered_by_trigger_plus_504": (base_rates["long_below_peak"]["recovered_by_504"]["count"], base_rates["long_below_peak"]["recovered_by_504"]["n"]),
        "s2_followed_within_365d": (base_rates["repeat_spike_suspension"]["followed_within_365d"], base_rates["repeat_spike_suspension"]["eligible_events"]),
        "s2_stocks_with_2_or_more": (base_rates["repeat_spike_suspension"]["stocks_with_2_or_more"], base_rates["repeat_spike_suspension"]["stocks"]),
        "recent_spike_pooled": (round(base_rates["recent_spike"]["pooled"]["share_below_event_close"] * base_rates["recent_spike"]["pooled"]["n_events"]), base_rates["recent_spike"]["pooled"]["n_events"]),
        "recent_spike_first_event_per_stock": (round(base_rates["recent_spike"]["first_event_per_stock"]["share_below_event_close"] * base_rates["recent_spike"]["first_event_per_stock"]["n_events"]), base_rates["recent_spike"]["first_event_per_stock"]["n_events"]),
        "i2_payout_above_100_cut_explore": (base_rates["payout_above_100_cut_rate"]["explore"]["cuts"], base_rates["payout_above_100_cut_rate"]["explore"]["n"]),
        "i2_payout_above_100_cut_holdout": (base_rates["payout_above_100_cut_rate"]["holdout"]["cuts"], base_rates["payout_above_100_cut_rate"]["holdout"]["n"]),
        "i9_cut_Y2024": (base_rates["yield_spike_cut"]["2024"]["cut_missing_counted_as_cut"]["count"], base_rates["yield_spike_cut"]["2024"]["cut_missing_counted_as_cut"]["n"]),
        "loss_turnaround_pooled": (base_rates["loss_maker_turnaround"]["turned_around"], base_rates["loss_maker_turnaround"]["n"]),
        "earnings_two_year_decline_rose_pooled": (base_rates["earnings_two_year_decline"]["pooled"]["count"], base_rates["earnings_two_year_decline"]["pooled"]["n"]),
        "earnings_more_than_doubled_gave_part_back_pooled": (base_rates["earnings_more_than_doubled"]["gave_part_back"]["count"], base_rates["earnings_more_than_doubled"]["gave_part_back"]["n"]),
        "earnings_more_than_doubled_gave_all_back_pooled": (base_rates["earnings_more_than_doubled"]["gave_all_back"]["count"], base_rates["earnings_more_than_doubled"]["gave_all_back"]["n"]),
        "i3_pooled_negative_return": (base_rates["near_peak_earnings_decline"]["pooled"]["negative"], base_rates["near_peak_earnings_decline"]["pooled"]["n"]),
        "i3_pooled_beat_median": (base_rates["near_peak_earnings_decline"]["pooled"]["beat_median"], base_rates["near_peak_earnings_decline"]["pooled"]["n"]),
    }
    for k, cell in base_rates["dividend_streaks"].items():
        if cell is None:
            continue
        n_years, y = k.replace("N=", "").replace("Y=", "").split(",")
        expected[f"i6_paid_again_N{n_years}_Y{y}"] = (cell["paid_again"]["count"], cell["paid_again"]["n"])
    for phase in ("explore", "holdout"):
        for h in IPO_HORIZONS:
            for board, s in ipo_boards[phase]["horizons"][f"{h}d"]["by_board"].items():
                key = f"ipo_{phase}_{h}d_{board.replace(' ', '_')}_negative"
                got = rates.get(key)
                if got is None or got["n"] != s["n"] or abs(100 * got["count"] / got["n"] - s["negative_rate_pct"]) > 0.05:
                    raise ValueError(f"{key}: recomputed {got and (got['count'], got['n'])} vs shipped n={s['n']} neg={s['negative_rate_pct']}%")
    for key, (count, n) in expected.items():
        got = rates.get(key)
        if got is None or (got["count"], got["n"]) != (count, n):
            raise ValueError(f"{key}: recomputed {got and (got['count'], got['n'])} does not match the shipped figure {(count, n)}")


def assemble(entries: list[dict]) -> dict[str, dict]:
    rates: dict[str, dict] = {}
    for e in entries:
        key = e.pop("key")
        if key in rates:
            raise ValueError(f"duplicate key {key}")
        rates[key] = e
    return rates


def main() -> None:
    for p in (PRICES_5Y_PATH, BENCHMARKS_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found - dev_cache is gitignored and machine-local; never invent this data")
    universe = json.loads(latest_dated_file(RAW_DIR, UNIVERSE_GLOB).read_text())
    h4_universe = json.loads(H4_UNIVERSE_PATH.read_text())
    prices = json.loads(PRICES_5Y_PATH.read_text())
    jkse = json.loads(BENCHMARKS_PATH.read_text())["^JKSE"]
    suspensions_raw = json.loads(h11.SUSPENSIONS_PATH.read_text())
    suspensions_app = json.loads((APP_DIR / "suspensions.json").read_text())
    base_rates = json.loads((APP_DIR / "base_rates.json").read_text())
    ipo_boards = json.loads((APP_DIR / "ipo_boards.json").read_text())

    entries: list[dict] = []
    entries += collect_recent_spike(prices)
    entries += collect_suspensions(suspensions_app, suspensions_raw, prices, jkse)
    entries += collect_s2(suspensions_raw)
    entries += collect_c(prices)
    entries += collect_i2(h4_universe)
    entries += collect_i3(universe, prices)
    entries += collect_i6(universe)
    entries += collect_i9(universe)
    entries += collect_loss_turnaround(universe)
    entries += collect_earnings(universe)
    entries += collect_ipo(universe, prices)
    rates = assemble(entries)
    check_against_app_files(rates, base_rates, ipo_boards)

    output = {
        "as_of": AS_OF,
        "computed_on": COMPUTED_ON,
        "method": {
            "wilson": "Wilson score 95% interval for a proportion (fractions in [0, 1]).",
            "cluster": f"Stock-cluster bootstrap 95% percentile interval: whole stocks resampled with replacement, B = {BOOTSTRAP_B}, seed {SEED}. Only where pre-registered (situation C, situation S2, recent spike, pooled); null elsewhere.",
            "n_stocks": "Distinct stocks behind n where the source rows identify the stock, null otherwise.",
            "wide": f"true when the widest available interval is more than {WIDE_POINTS:g} percentage points; the page marks such a rate 'lebar'.",
            "source": "EXPERIMENT.md, Pre-registration 2026-09-27, ST0. Descriptive; no new trial.",
        },
        "rates": rates,
    }
    out_path = APP_DIR / "base_rate_uncertainty.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    wide = [k for k, v in rates.items() if v["wide"]]
    print(f"Wrote {out_path}: {len(rates)} rates, {len(wide)} marked wide (> {WIDE_POINTS:g} points)")
    for k, v in rates.items():
        cl = "" if v["cluster_low"] is None else f" cluster [{v['cluster_low'] * 100:.1f}, {v['cluster_high'] * 100:.1f}]"
        print(
            f"  {k}: {v['count']}/{v['n']} = {v['rate'] * 100:.1f}% Wilson [{v['wilson_low'] * 100:.1f}, {v['wilson_high'] * 100:.1f}]{cl}"
            f" stocks={v['n_stocks']} width={v['width_points']:.1f} {'LEBAR' if v['wide'] else ''}"
        )


if __name__ == "__main__":
    main()
