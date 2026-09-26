"""
Disclosure (item F1): how many stocks does each app flag mark at its threshold
and at +/-20% of it?

Outcome-free: no returns, no cut rates and no other outcome is read, and no
threshold is changed. Definitions frozen in EXPERIMENT.md ("Pre-registration,
2026-09-26 (batch 2)"); run once. The rationale text per threshold is written
by the lead, not here.

Method: the flag functions of `pipeline.appdata.build_flags` are called
unchanged; only the module-level threshold constant they read is temporarily
replaced (`unittest.mock.patch.object`) for each call, so the counts come from
the shipped code, not a re-implementation. Thresholds: payout ratio 1.0,
near-high 0.10, yield multiplier 1.5, LQ45 float 0.25; variants x0.8 and x1.2.

Run:
    .venv/bin/python -m pipeline.hypotheses.flag_sensitivity
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from pipeline.appdata import build_flags

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = REPO_ROOT / "data" / "raw" / "universe_2026-09-13.json"

SCALES = (0.8, 1.0, 1.2)

# (flag name, builder function name, constant name in build_flags)
FLAGS = (
    ("payout_above_earnings", "build_payout_above_earnings", "PAYOUT_RATIO_THRESHOLD"),  # H4 construct (shipped since 2026-09-26)
    ("payout_snapshot_legacy", "build_payout_snapshot_flag", "PAYOUT_RATIO_THRESHOLD"),  # the earlier snapshot version
    ("near_ath_earnings_decline", "build_near_ath_earnings_decline", "NEAR_ATH_THRESHOLD"),
    ("yield_far_above_average", "build_yield_far_above_average", "YIELD_ABOVE_AVG_MULTIPLIER"),
    ("lq45_low_float", "build_lq45_low_float", "LQ45_LOW_FLOAT_THRESHOLD"),
)


def count_at(rows: list[dict], builder_name: str, const_name: str, value: float) -> dict:
    with mock.patch.object(build_flags, const_name, value):
        result = getattr(build_flags, builder_name)(rows)
    return {"threshold": value, "flagged": result["flagged_count"], "evaluable": result["evaluable_count"]}


def build_sensitivity(rows: list[dict]) -> dict:
    out: dict = {}
    for name, builder, const in FLAGS:
        base = getattr(build_flags, const)
        out[name] = {
            f"x{scale}": count_at(rows, builder, const, base * scale) for scale in SCALES
        }
        out[name]["shipped_threshold"] = base
    return out


def main() -> None:
    result = build_sensitivity(json.loads(UNIVERSE_PATH.read_text()))
    for name, res in result.items():
        print(f"{name} (shipped threshold {res['shipped_threshold']}):")
        for scale in SCALES:
            r = res[f"x{scale}"]
            print(f"  x{scale}: threshold={r['threshold']:.4g}  flagged={r['flagged']} of {r['evaluable']}")


if __name__ == "__main__":
    main()
