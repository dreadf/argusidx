#!/usr/bin/env bash
# Rebuild every data/app/*.json from the data in data/raw/ (0 Sectors credits).
# Order matters for build_market_condition (reads rankings.json) and
# build_stock_pages (embeds the situations and flags), so they run last.
# build_base_rates must also run before build_base_rate_uncertainty, which
# cross-checks its own recomputation against base_rates.json's shipped
# figures (found 2026-10-08: plain alphabetical order runs the uncertainty
# check first, against a base_rates.json an earlier universe sweep wrote,
# and the check correctly fails the moment the universe is ever refreshed).
# Needs data/raw/ (kept in the private data repo).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
echo "== build_base_rates"
"$PY" -m pipeline.appdata.build_base_rates
for m in $(ls pipeline/appdata/build_*.py | xargs -n1 basename | sed 's/\.py$//' | grep -v '^build_stock_pages$' | grep -v '^build_market_condition$' | grep -v '^build_base_rates$'); do
  echo "== $m"
  "$PY" -m "pipeline.appdata.$m"
done
echo "== build_market_condition"
"$PY" -m pipeline.appdata.build_market_condition
echo "== build_stock_pages"
"$PY" -m pipeline.appdata.build_stock_pages
