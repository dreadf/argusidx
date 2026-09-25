"""Build data/app/lens_extractive.json — the Extractive "lens" (docs/PRODUCT.md §9).

Not a ranked comparison scorecard like the Banking lens - checked all
three candidate mining endpoints directly (2026-09-13) and none exist at
company granularity: `/v2/mining/resources-reserves/` is
province+commodity+year (H12 finding, hypothesis-testing session),
`/v2/mining/total-production/` is a national total per commodity, and
`/v2/mining/exports/` ranks countries, not companies. There is nothing
to rank a listed miner against another listed miner on.

What this builds instead: a plain commodity-exposure fact per real
listed miner, from data already owned (`/v2/mining/companies/`, fetched
2026-09-13 by the hypothesis-testing session for H12 - zero new cost
here). 68 real listed miners, out of 366 total entries in that file
(the rest are unlisted subsidiaries/holdcos with no ticker).

Run: .venv/bin/python -m pipeline.appdata.build_lens_extractive
"""
from __future__ import annotations

import json

from pipeline.appdata.common import APP_DIR, RAW_DIR, latest_dated_file

MINING_COMPANIES_GLOB = "mining_companies_????-??-??.json"


def build_lens_extractive(entries: list[dict]) -> dict:
    listed = [e for e in entries if e.get("symbol")]
    result = {}
    for entry in listed:
        result[entry["symbol"]] = {
            "company_type": entry.get("company_type"),
            "key_operation": entry.get("key_operation"),
            "commodity_type": entry.get("commodity_type") or [],
        }
    return result


def main() -> None:
    source_path = latest_dated_file(RAW_DIR, MINING_COMPANIES_GLOB)
    as_of = source_path.stem.replace("mining_companies_", "")
    entries = json.loads(source_path.read_text())

    lens = build_lens_extractive(entries)

    output = {"as_of": as_of, "source_file": source_path.name, "miners": lens}

    APP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = APP_DIR / "lens_extractive.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} from {source_path.name} (as_of {as_of})")
    print(f"{len(lens)} real listed miners (of {len(entries)} total entries)")


if __name__ == "__main__":
    main()
