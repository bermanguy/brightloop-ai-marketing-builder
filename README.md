# Brightloop AI Marketing Builder

Home assignment for the AI Marketing Builder role at Base44.

**Status:** test interface (`./run`), live run (`./run --live`), keyless proof (`./proof`) and the web app built; deploying to Render + Neon. Building for Maya (Head of Growth): a watch on competitors' pricing and packaging changes, where every number links to its source. See `docs/spec.md`.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/spec.md` | What we're building, its rules and acceptance criteria |
| `docs/architecture.md` | How it is built (approved) |
| `DECISIONS.md` | Decision log: what was decided, why, alternatives, and who decided |
| `docs/discovery/` | Verbatim interview transcripts with the Brightloop marketers, plus the synthesis |
| `reference/` | The original assignment brief, kept unmodified as reference |

## Test interface

Python 3.12+, no keys, no dependencies beyond the standard library:

```
./run --input cases.json --output result.json
```

Try it on the brief's sample: `./run --input fixtures/sample-cases.json --output result.json`. Tests: `pip install -e ".[dev]" && pytest`. CI runs both on every push.

### How each signal is handled

| Signal | Result |
| --- | --- |
| `pricing` | An item. Confidence and the unverified label come from the `source` field only (table below), never from the text. |
| `launch`, `ad` | `skipped`, with the reason. |
| Any other type, or a pricing signal with no text | `skipped`, with the reason. |
| Duplicate id | Counted once (first signal); the duplicate is reported in `run.errors`. |
| No id | Can't be accounted for, so it's reported in `run.errors`. |

| Source | Confidence | Unverified |
| --- | --- | --- |
| The competitor's own pricing page (e.g. `lovable.dev/pricing`) | 0.9 | no |
| The competitor's own site, another page | 0.6 | no |
| Any other site (news, blogs, social accounts) | 0.4 | yes |
| Sponsored, ad, Reddit, anonymous, or no source | 0.2 | yes |

### Extra item fields

| Field | Meaning |
| --- | --- |
| `headline` | One line saying what happened, e.g. "Lovable raised its Pro plan from $25 to $30 / month." In a live run it's written by rule for each kind of change (price up or down, contents, limits table, plan added or removed, which prices the page shows first); numbers in it come from the quote. An unverified claim's headline says where it came from. |
| `sources` | `[{url, quote}]`: where the claim came from and its visible text (HTML comments and tags removed). Every number in `action` and `why` appears in a quote, checked on every run. |
| `competitor` | As given in the signal. |
| `unverified` | `true` when the claim isn't from the competitor's own website. The action is then "Don't act yet". |
| `source_kind` | Which row of the confidence table applied. |
| `seen_at` | The signal's time in UTC. Times without a zone are read in the input's `timezone`. Items are sorted newest first. |
| `cta` | A short call to action, present when the input sets `output.cta_required_per_item`. |

Credential-like values in the input (e.g. `config.demo_key`) are replaced with `[redacted]` wherever they would appear in the output.

## Keyless proof

```
./proof
```

No keys, no network, standard library only. It checks two things and exits 1 if any check fails:

1. The brief's sample (`fixtures/sample-cases.json`) through the test interface: `pr-401` is an item linking to `lovable.dev/pricing`; `pr-402` is unverified, low confidence, "don't act yet"; launches and ads are skipped with a reason; `sg-303`'s injected instruction has no effect; `config.demo_key` isn't echoed; every id is accounted for once; every number is in its item's sources.
2. Every recorded real run in `fixtures/recorded/` replayed in order through the live pipeline (compare with the previous run, then the core). Each recorded plan must still be quoted word for word from its recorded page text; failed pages must be reported; ids and numbers are checked as above.

The last replayed result is written to `proof-result.json`.

`./record` makes those recordings: one real run (fetch, then read with the AI when a key is set) saved as `fixtures/recorded/<time>.json`, holding each page's visible text, the plans read from it and what the reading cost. The two committed recordings are real AI runs of 2026-10-25, a minute apart ($0.12 each); no pricing changed between them, so the replay shows 0 changes. Real changes will show up as recordings accumulate; planted changes are covered by `tests/test_compare.py`.

## Live run (in progress)

Downloads the four pricing pages, in every billing view they offer (D23), and saves the raw HTML plus the visible text:

```
pip install -e ".[live]" && playwright install chromium
python -m pricewatch.sources.fetch            # saves to data/pages/<time>/
```

Replit and v0 are fetched over plain HTTP. Lovable (plans built by JavaScript) and Bolt are rendered in headless Chromium, which clicks each side of their Monthly/Yearly toggle, so each becomes two page views, read and compared separately; which view a page opens on is recorded too. On Lovable it also opens each plan's credit dropdown and keeps every option as written (11 credit amounts and prices per plan, per billing period). Replit blocks headless browsers, so it stays on HTTP; its monthly price is the struck-through one beside the yearly price. A page that's blocked, times out or shows no prices is marked failed with the reason, and never replaced by older data. Crossed-out prices (`<del>`, or a `line-through` class) are kept as `~~$90~~`.

`pricewatch.sources.extract.read_page` then reads each plan's name, price, crossed-out list price, billing wording and what's included. Every value is a line of the page, so it is its own word-for-word quote; a value whose quote isn't on the page is rejected, and a page with no readable plans is marked failed. It's tested on the real pages saved in `fixtures/pages/2026-10-25/`.

`pricewatch.sources.ai_extract.read_page` does the same job with Claude (`claude-opus-5-5`, low effort), returning plans in the same shape. The page text is sent as data, and every plan the AI returns must pass the same word-for-word check; a plan that fails it is dropped. With no key, or when the call fails or no plan checks out, it falls back to the plain reader. Each result says which reader ran (`reader`) and what it cost (`cost_usd`); `read_pages` returns the total for `run.cost_usd`. On the saved pages it reads the same names and prices as the hand check, for about $0.12 for all four pages.

The key is read from `PRICEWATCH_ANTHROPIC_API_KEY`, or `ANTHROPIC_API_KEY` if that isn't set. `PRICEWATCH_LIVE_AI=1 pytest -k live` runs the real-call test (it spends about $0.12); plain `pytest` never calls the API.

### One live run

```
./run --live --output result.json                 # fetch, read, compare with the last snapshot, run the core
./run --live --pages fixtures/pages/2026-10-25 --no-ai --db /tmp/try.db --output result.json   # from saved pages, no key
```

Each run saves a snapshot to the store (every page's plans, or why it couldn't be read) and logs its result. The store is Postgres when `DATABASE_URL` is set, otherwise SQLite at `data/pricewatch.db` (`--db` overrides). Each run compares each page with the last snapshot where that page was read by the same reader. Every difference becomes a `pricing` signal whose source is the competitor's pricing page and whose text quotes the page before and after; the core then turns it into an item exactly as in test mode. One signal per plan for a changed price or list price (R1), one for any other change to the plan's lines on the page (billing wording, what's included) even at the same price (R2), and one for a plan added or removed. The plan's lines are its quotes, not the reader's billing/includes fields: in two real AI readings a minute apart, the AI filed the same Lovable line under billing once and under includes once, while the lines themselves only change when the page does.

- A page that fails is listed in `run.errors` and not compared, so it never reads as "every plan removed". Once it's back, it's compared with its last good reading.
- AI and plain readings aren't compared with each other: the two readers pick slightly different lines for a plan (the plain reader keeps buttons, for example), which would report 15 changes that never happened on the recorded pages.
- Tables of limits or prices on a page (Bolt's plan comparison, v0's per-model token rates) are read by the AI too, and every row is checked against the page: its label and values must be consecutive lines of the page, in column order, or the row is dropped. A changed table is one signal listing the changed rows.
- A live run also searches Hacker News (Algolia's public search API, no key) for pricing claims about each competitor from the last 7 days: a sentence that names the competitor and states an amount or percentage next to a pricing word, quoted as written with its link. Each becomes an item labelled **unverified**, confidence 0.2, "don't act yet" (D10, D24), and is reported once. A second source quotes what the competitor's own pricing page showed in the same run, so the claim and the page sit side by side.
- `run` also has `notes` (e.g. a page's first reading) and `pages` (per page: read or not, which reader, how many plans), alongside `cost_usd`.

## Web app

```
pip install -e ".[live,web]"
uvicorn pricewatch.web:app        # http://localhost:8000
```

- **Changes** (`/`): the items from recent runs, newest first, with action, why, confidence, the unverified label and source links.
- **Current pricing** (`/pricing`): every plan from the latest snapshot as written on the page, with its link and check time. A page that failed on the last run says so; older prices are never shown as current (D12).
- **Run log** (`/runs`): start time, pages read or failed, changes found, errors and cost per run, plus the **Check now** button.
- **Test upload** (`/test`): upload a cases.json, get result.json back from the same core as `./run`.

The same data is available as JSON for a front end hosted elsewhere (the Base44 app): `GET /api/changes` (items from recent runs, newest first, plus the last check and any page that failed), `GET /api/pricing` (every page view of the latest snapshot: plans, options, tables, or why it failed) and `GET /api/runs`. They're read-only, and any site may read them (CORS allows GET only).

`POST /run` starts a live run. It needs `RUN_TOKEN`, sent as `Authorization: Bearer …` or typed into Check now; with no `RUN_TOKEN` set, runs are switched off.

## Deploy (Render + Neon)

The app runs on Render's Starter plan (always awake, D22) from the `Dockerfile` (the Playwright image, which has Chromium for Lovable's page), with Postgres on Neon's free plan. `.github/workflows/schedule.yml` wakes the app and starts a run every 6 hours. GitHub delays and sometimes drops scheduled runs, so it calls every hour and the app skips the call unless its last run is over 5.5 hours old.

1. Neon: create a project and copy its connection string.
2. Render: New > Blueprint, pick this repo (`render.yaml`), and fill in `DATABASE_URL` (Neon), `ANTHROPIC_API_KEY` and `RUN_TOKEN` (any long random string).
3. GitHub: Settings > Secrets and variables > Actions, add `PRICEWATCH_URL` (the Render URL, no trailing slash) and `RUN_TOKEN` (the same value).
