# Setup

## Run the app (0 credits, no keys)

Needs Node 22.

```bash
cd frontend
npm ci
npm run dev        # http://localhost:3000
```

`data/app/*.json` is committed, so the whole app works with no Sectors key and
no network. Without a Gemini key, Tanya answers from data only.

Production build: `npm run build && npm run start`.

Optional environment variables (put them in `frontend/.env.local`):

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Lets Tanya word answers with Gemini. Absent: data-only answers. |
| `GEMINI_MODEL` | Model name override. |
| `ASK_COOKIE_SECRET` | Signs the per-user AI allowance cookie (falls back to the Gemini key). |

## Test

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest pipeline/tests scripts -q
python3 scripts/check_no_secrets.py
cd frontend && npm test && npm run lint
```

A few tests read the purchased raw data and skip on a fresh clone.

## Re-run the research and rebuild the data (0 credits, needs `data/raw/`)

`data/raw/` is not in this repository (Sectors' terms forbid republishing the
data). With your own copy in `data/raw/`:

```bash
scripts/rebuild_app_data.sh                       # every data/app/*.json
.venv/bin/python -m pipeline.hypotheses.h18_insider_buying   # any hypothesis module
```

Four builders (`build_beat_gold`, `build_base_rates`, `build_ipo_boards`,
`build_situations`) also read the research price history in `data/dev_cache/`
(gitignored, free public source, development only). On a fresh clone fetch it
first with `pipeline/dev/fetch_yahoo_prices.py`; everything else runs on
`data/raw/` alone. Each hypothesis module prints numbers that match
`EXPERIMENT.md`.

## Fetch your own data (costs Sectors credits)

Get a key at Sectors, then `cp .env.example .env` and set `SECTORS_API_KEY`.
Check `docs/credit_ledger.md` for what each fetch cost here before running
it. Examples:

```bash
.venv/bin/python -m pipeline.appdata.fetch_idx_total          # about 24 credits
.venv/bin/python -m pipeline.hypotheses.h6_foreign_list       # about 126 credits
```

The client refuses queries below the 2021-01-01 data floor (they return empty
arrays and still bill). `pipeline/sectors_mcp.py` is the MCP client; it needs
`allow_billed=True` for billed tools.

## Price history for the price-outcome research (development only)

`pipeline/dev/fetch_yahoo_prices.py` downloads free public prices into
`data/dev_cache/` (gitignored). The app never imports it.

## Deploy

Any static/Node host that runs `next build` in `frontend/` works. The build
traces `../data/app/` and `../docs/credit_ledger.md` into the server routes
(`next.config.ts`). After submission the repository and the deployed app are
frozen; no data refresh is scheduled.

## Troubleshooting

- **Error 1010 from the Sectors API:** the request lacks a browser-like `User-Agent`.
- **Empty arrays for old dates:** the individual-stock data floor is 2021-01-01.
- **`PageProps`/`LayoutProps` type errors:** run `npx next typegen`, or delete `.next` and build again.
