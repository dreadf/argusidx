"""Peer-group assignment (docs/PRODUCT.md §8).

Rule: group companies from most specific to least specific
(sub_industry -> industry -> sub_sector -> sector). Use the most specific
level that still has >= MIN_GROUP_SIZE companies; otherwise zoom out one
level. Every company lands in a group at some level, since `sector` alone
is guaranteed to have >= 15 members across the whole universe.

Run: .venv/bin/python -m pipeline.appdata.peer_groups
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from pipeline.appdata.common import APP_DIR, RAW_DIR, UNIVERSE_GLOB, latest_dated_file

MIN_GROUP_SIZE = 15

CASCADE_LEVELS = ["sub_industry", "industry", "sub_sector", "sector"]


def build_peer_groups(rows: list[dict]) -> dict:
    """Cascade sub_industry -> industry -> sub_sector -> sector.

    Two distinct things must not be conflated:
    - the THRESHOLD CHECK ("does this level have >= 15 companies?") is
      against the full market-wide census for that label, independent of
      how any individual company resolves;
    - a company's PEER GROUP, once its level is decided, is every company
      sharing that label at that level - including companies that
      themselves resolve at a finer level. A silver-mining sub-industry
      too small on its own falls back to its industry, and its peers there
      are *all* companies in that industry (large sub-industries included),
      not just the other leftover companies who also fell back.
    """
    census: dict[str, Counter] = {
        level: Counter(
            row["query_values"][level]
            for row in rows
            if row["query_values"].get(level) is not None
        )
        for level in CASCADE_LEVELS
    }

    assignments: dict[str, dict] = {}
    level_used_counts: Counter = Counter()

    for row in rows:
        qv = row["query_values"]
        for level in CASCADE_LEVELS:
            key = qv.get(level)
            is_last_level = level == CASCADE_LEVELS[-1]
            if key is not None and (is_last_level or census[level][key] >= MIN_GROUP_SIZE):
                assignments[row["symbol"]] = {"level": level, "group": key}
                level_used_counts[level] += 1
                break
        else:
            # sector is guaranteed >= MIN_GROUP_SIZE for every real sector
            # in this universe (verified: smallest sector has 40
            # companies) - reaching here means every cascade field is
            # missing for this row.
            raise ValueError(f"No cascade level reached MIN_GROUP_SIZE for {row['symbol']}")

    # Full membership per assigned (level, key) pair - the census count,
    # not the subset that happened to resolve there themselves.
    groups: dict[str, list[str]] = defaultdict(list)
    used_pairs = {(a["level"], a["group"]) for a in assignments.values()}
    for row in rows:
        qv = row["query_values"]
        for level, key in used_pairs:
            if qv.get(level) == key:
                groups[f"{level}:{key}"].append(row["symbol"])

    group_sizes = sorted(len(members) for members in groups.values())
    median_size = group_sizes[len(group_sizes) // 2]

    return {
        "assignments": assignments,
        "group_members": dict(groups),
        "summary": {
            "total_companies": len(rows),
            "total_groups": len(groups),
            "smallest_group": min(group_sizes),
            "median_group_size": median_size,
            "largest_group": max(group_sizes),
            "companies_by_level_used": dict(level_used_counts),
        },
    }


def main() -> None:
    universe_path = latest_dated_file(RAW_DIR, UNIVERSE_GLOB)
    rows = json.loads(universe_path.read_text())

    result = build_peer_groups(rows)

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "peer_groups.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {universe_path.name}")
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
