# Architecture — proposed

Status: **approved by Guy, 2026-10-25** (D13). Implements `docs/spec.md`.

> **What changed since (see `DECISIONS.md`):** the app, always on (D22), schedules its own runs every 6 hours, with GitHub Actions as an hourly backup (D21). The AI reads the pages and every value is quote-checked (D16); action and why are written by rule (D26). Every billing view on each page is captured (D23). Hacker News is the rumor source (D24). Base44 became the marketers' front end over the JSON API, with Render as the admin fallback (D32). Alerts go by email and Slack (D34–D36). The current picture is the diagram in the README.

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

**AI reads; rules decide (D38).**

| Job | How | Guardrail |
| --- | --- | --- |
| Reading plans and prices from a pricing page | **AI** | Every value must come with a quote from the page; a value whose quote isn't found word for word in the page is rejected |
| Deciding whether a page change matters | **Rule** (D38): runs are compared by the page lines a plan was read from (D18–D20) | No AI, so nothing on the page can change it |
| Writing the headline, `action` and `why` | **Rule** (D38): one template per kind of change (D26) | Numbers come only from the item's sources |
| Answering questions about the data (MCP, D37) | **AI**: any MCP client, such as Claude, Claude Code or Cursor | Read-only tools that return items with their links and quotes |
| Confidence | **Rule**, from where the claim came from | No signal text is read, so hidden instructions can't move it |
| "Unverified" label | **Rule** (not the competitor's own site) | Same |
| What gets skipped (launch and ad signals) | **Rule**, from the signal type | Same |
| Every input id appears exactly once | **Rule** (counting) | Tested |

**Confidence rule (first version):**

| Where the claim came from | Confidence | Label |
| --- | --- | --- |
| The competitor's own pricing page | 0.9 | — |
| The competitor's own site, another page | 0.6 | — |
| News or other third party | 0.4 | unverified |
| Sponsored post, ad, Reddit, anonymous | 0.2 | unverified |

**No keys:** without an API key (a reviewer's fresh clone), the same pipeline uses plain-code fallbacks: templates for the text, and treating every material field change as significant. The output is less polished but correct. Recorded live runs store the AI's results, so the keyless proof replays real AI-quality output. `run.cost_usd` reports actual spend (expected: a few cents a day).

## Stack

| Part | Choice | Why |
| --- | --- | --- |
| Language | **Python 3.12** | Good for fetching and parsing pages, and for tests |
| Web app | **FastAPI**, plain server-rendered HTML | Small; no front-end build step; no UI polish needed |
| Fetching | `httpx` for Replit and v0; **Playwright** for Lovable and Bolt (D23) | Lovable's plans are rendered by JavaScript; Lovable's and Bolt's second billing period and Lovable's credit ladder need clicks |
| Storage | **Postgres** (Neon free tier) in production; **SQLite** locally and for the keyless proof | Snapshots and the run log must survive restarts |
| Hosting | **Render** web service (Starter plan since D22; free tier before) | Public URL, deploys from GitHub. Always awake, so Maya never waits for a cold start |
| Schedule | **GitHub Actions** cron every 6 hours calls the app's protected `/run` endpoint | Keeps the schedule in the repo and wakes the sleeping app. "Check now" calls the same endpoint |
| Tests and CI | **pytest** + GitHub Actions on every push | Includes the keyless proof run |

**Not chosen: a Base44 front end.** Tempting for a Base44 role, but the brief requires all code in the repo, and I couldn't confirm Base44's GitHub sync or scheduling within our time. It could be added on top later if time allows.

## What the app has

- **Changes** page: the latest items, newest first, each with action, why, confidence, unverified label if any, and source links.
- **Current pricing** page (D12): one table per competitor, with source link and check time per row, and failed pages marked as failed.
- **Check now** button: no token, at most one run every 30 minutes (D29).
- **Run log** page: start time, pages fetched, errors, cost.
- **Test upload** page: upload `cases.json`, see what each input id led to and the items, download `result.json`. Same core as the command; nothing is saved.

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

Accounts the session can't create: **Render** and **Neon**, both free. An **LLM API key** (Anthropic or OpenAI) for the live app. All secrets go in environment variables, never in the repo.

## Risks

1. **Pages need a browser** → checked 2026-10-25: only Lovable does (D14). Playwright adds weight to the build and the Render deploy.
2. **A site blocks automated requests** (Replit already blocks headless browsers after a few loads, so it is fetched with `httpx` only) → the table shows that page as failed (D12). Fall back to fewer competitors if needed; logged.
3. **Free-tier cold start** (~30–60 s) → acceptable, and it shows the cold start the recording asks for.
