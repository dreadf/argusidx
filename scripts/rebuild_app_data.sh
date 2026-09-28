#!/usr/bin/env bash
# Rebuild every data/app/*.json from the data in data/raw/ (0 Sectors credits).
# Order matters for build_market_condition (reads rankings.json) and
# build_stock_pages (embeds the situations and flags), so they run last.
# Needs data/raw/ (kept in the private data repo).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
for m in $(ls pipeline/appdata/build_*.py | xargs -n1 basename | sed 's/\.py$//' | grep -v '^build_stock_pages$' | grep -v '^build_market_condition$'); do
  echo "== $m"
  "$PY" -m "pipeline.appdata.$m"
done
echo "== build_market_condition"
"$PY" -m pipeline.appdata.build_market_condition
echo "== build_stock_pages"
"$PY" -m pipeline.appdata.build_stock_pages
