# Architecture — proposed

Status: **proposal, awaiting Guy's approval.** 2026-10-25. Implements `docs/spec.md`.

## One idea holds it together

The brief requires the live app and the test mode to share the same logic, with only the input source different. So the system is split into **sources** that produce signals and **one core** that turns signals into Maya's items:

```
LIVE:  pricing pages ─▶ fetch ─▶ extract plans ─▶ compare with last snapshot ─┐
                                                                             ├─▶ CORE ─▶ result (items, skipped, run)
TEST:  cases.json ───────────────────────────────▶ read signals ──────────────┘
```

- **Core** (shared): checks every input id is accounted for once; normalises timestamps; decides relevance (pricing yes; launches and ads skipped with a reason); sets confidence; writes `action` and `why`; attaches `sources`; validates the output before returning it.
- **Live source**: fetches the four pricing pages, extracts each plan, stores a snapshot, and compares it with the previous one. Every difference becomes a `pricing` signal in the same shape as the test file's signals.
- **Test source**: reads `cases.json`.

## Where AI is used, and where it isn't

Maya was burned by an AI summary that invented a number. So AI never decides a number, a confidence or what gets skipped.

| Step | How | Why |
| --- | --- | --- |
| Relevance, skip reasons, id accounting | Plain code | Must be exact and testable |
| Confidence | Plain code, from the source type (competitor's own page vs. anything else) | So no text inside a signal can change it (D1) |
| Comparing snapshots | Plain code | Exact |
| `action` and `why` text | Plain-code templates with the exact numbers from the source | Runs with no keys; can't invent figures |
| Reading plans from a pricing page | **Depends on Monday's page check.** Clean HTML → a small parser per site. Messy HTML → an LLM that must quote the page text for every value; any value whose quote isn't found word for word in the page is rejected | Keeps "no link, no number" true even if an LLM is involved |

The test-file path (what reviewers run) is plain code end to end, so it works on a fresh clone with **no keys**. An LLM, if used at all, sits only in the live source; its extracted results are stored with each snapshot, so recorded runs replay without keys. `run.cost_usd` reports actual LLM spend (0 when none is used).

Optional later: an LLM to reword `action` text, with a check that it adds no new numbers. Not in the first version.

## Stack

| Part | Choice | Why |
| --- | --- | --- |
| Language | **Python 3.12** | Good for fetching and parsing pages, and for tests |
| Web app | **FastAPI**, plain server-rendered HTML | Small; no front-end build step; no UI polish needed |
| Fetching | `httpx`; **Playwright** only if a page needs a browser | Start simple |
| Storage | **Postgres** (Neon free tier) in production; **SQLite** locally and for the keyless proof | Snapshots and the run log must survive restarts |
| Hosting | **Render** web service (free tier) | Public URL, deploys from GitHub. Sleeps when idle, so the first request after a pause is a real cold start |
| Schedule | **GitHub Actions** cron every 6 hours calls the app's protected `/run` endpoint | Keeps the schedule in the repo and wakes the sleeping app. "Check now" calls the same endpoint |
| Tests and CI | **pytest** + GitHub Actions on every push | Includes the keyless proof run |

**Not chosen: a Base44 front end.** Tempting for a Base44 role, but the brief requires all code in the repo, and I couldn't confirm Base44's GitHub sync or scheduling within our time. It could be added on top later if time allows.

## What the app has

- **Changes** page: the latest items, newest first, each with action, why, confidence, unverified label if any, and source links.
- **Current pricing** page (D12): one table per competitor, with source link and check time per row, and failed pages marked as failed.
- **Check now** button.
- **Run log** page: start time, pages fetched, errors, cost.
- **Test upload** page: upload `cases.json`, download `result.json`. Same core as the command.

## Commands

| Command | What it does |
| --- | --- |
| `./run --input cases.json --output result.json` | The brief's test interface |
| `./proof` | Keyless proof: replays recorded real snapshots through the full pipeline and checks the output |
| `./run --live` | One live run (fetch, compare, core), as the schedule does |
| `./record` | Saves the latest real snapshots into `fixtures/` for keyless replay |

## Repository layout

```
src/pricewatch/
  core/        signals → items: relevance, confidence, text, sources, accounting, validation
  sources/     live (fetch, extract, compare) and file (cases.json)
  web/         FastAPI app and HTML templates
  store.py     snapshots and run log (Postgres or SQLite)
fixtures/      recorded real snapshots + sample cases (including the brief's sample)
tests/         unit tests + tricky cases: injection, sponsored claims, time zones, id accounting
.github/workflows/  ci.yml (tests + proof on every push), schedule.yml (every 6 hours)
run, proof, record   entry-point scripts
```

## What Guy needs to set up

Accounts the session can't create: **Render** and **Neon**, both free. Optional: an LLM API key, only if Monday's check shows the pages need one. All secrets go in environment variables, never in the repo.

## Risks

1. **Pages need a browser** → Playwright adds weight to the build and the Render deploy. Checked first thing Monday.
2. **A site blocks automated requests** → the table shows that page as failed (D12). Fall back to fewer competitors if needed; logged.
3. **Free-tier cold start** (~30–60 s) → acceptable, and it shows the cold start the recording asks for.
