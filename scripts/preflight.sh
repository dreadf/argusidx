#!/usr/bin/env bash
# Pre-submission gate. Run from anywhere: scripts/preflight.sh
#
# Hard checks (any failure exits non-zero): pipeline tests, secret scan,
# frontend production build, and the LLM-off gate RULES.md asks for -
# the production server is started with GEMINI_API_KEY blanked and must
# still serve pages and answer /api/ask from templates.
#
# Advice-language scan is printed for human review, not gated: it flags
# disclaimers that name the very question they refuse to answer, which are
# legitimate (see scripts/check_no_advice_language.py's own docstring).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

PORT=3111
FAILED=0
step() { printf '\n== %s ==\n' "$1"; }
# `npm run start` spawns a next-server child that outlives the npm wrapper, so
# killing the wrapper leaves the port taken and a later run silently tests the
# OLD build. Always clear whatever listens on the port, before and after.
free_port() { lsof -ti "tcp:$PORT" -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null; sleep 1; }
fail() { printf 'FAIL: %s\n' "$1"; FAILED=1; }

step "pipeline tests"
.venv/bin/python -m pytest pipeline/tests/ -q || fail "pytest"

step "secret scan"
python3 scripts/check_no_secrets.py || fail "check_no_secrets"

step "advice-language scan (review hits by hand)"
python3 scripts/check_no_advice_language.py --dir frontend/src README.md docs/PRODUCT.md || \
  echo "(hits above need a human read; known-good: disclaimers, refusal templates, classifier regexes)"

step "frontend production build"
(cd frontend && npm run build > /tmp/argus_preflight_build.log 2>&1) || {
  tail -20 /tmp/argus_preflight_build.log
  fail "npm run build"
}

step "LLM-off gate (GEMINI_API_KEY blanked)"
if [ "$FAILED" -eq 0 ]; then
  free_port
  (cd frontend && GEMINI_API_KEY="" npm run start -- -p "$PORT" > /tmp/argus_preflight_server.log 2>&1) &
  SERVER_PID=$!
  READY=0
  for _ in $(seq 1 30); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/")" = "200" ]; then READY=1; break; fi
    sleep 1
  done
  if [ "$READY" -ne 1 ]; then
    fail "server did not start on :$PORT"
  else
    # -L: old URLs redirect to their new home (/peringkat -> /jelajah, etc.).
    PATHS="/ /jelajah /jelajah/sektor /jelajah/tanda /cari /peringkat /sektor /tanda /temuan /tanya /watchlist /saham/BBCA"
    for path in $PATHS; do
      code=$(curl -sL -o /dev/null -w '%{http_code}' "http://localhost:$PORT$path")
      [ "$code" = "200" ] && echo "ok   $path" || fail "$path returned $code"
    done
    RESPONSE=$(curl -s -X POST "http://localhost:$PORT/api/ask" \
      -H 'Content-Type: application/json' \
      -d '{"question":"Apa posisi harga BBCA sekarang?"}')
    RESPONSE="$RESPONSE" python3 - <<'PY' || fail "/api/ask with the LLM off"
import json, os, sys
d = json.loads(os.environ["RESPONSE"])
assert d["source"] == "template", f"expected template source, got {d['source']!r}"
assert d["prose"].strip(), "empty prose"
assert d["facts"], "no facts returned"
print("ok   /api/ask answered from templates with", len(d["facts"]), "facts")
PY
  fi
  free_port
  wait "$SERVER_PID" 2>/dev/null
else
  echo "skipped (an earlier step failed)"
fi

echo
if [ "$FAILED" -eq 0 ]; then echo "PREFLIGHT PASSED"; else echo "PREFLIGHT FAILED"; fi
exit "$FAILED"
