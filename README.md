# Brightloop AI Marketing Builder

Home assignment for the AI Marketing Builder role at Base44.

**Status:** core test interface built (`./run`); live fetching, the app and the keyless proof come next. Building for Maya (Head of Growth): a watch on competitors' pricing and packaging changes, where every number links to its source. See `docs/spec.md`.

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
| `sources` | `[{url, quote}]`: where the claim came from and its visible text (HTML comments and tags removed). Every number in `action` and `why` appears in a quote, checked on every run. |
| `competitor` | As given in the signal. |
| `unverified` | `true` when the claim isn't from the competitor's own website. The action is then "Don't act yet". |
| `source_kind` | Which row of the confidence table applied. |
| `seen_at` | The signal's time in UTC. Times without a zone are read in the input's `timezone`. Items are sorted newest first. |
| `cta` | A short call to action, present when the input sets `output.cta_required_per_item`. |

## Live fetch (in progress)

Downloads the four pricing pages as they look on first load (D14) and saves the raw HTML plus the visible text:

```
pip install -e ".[live]" && playwright install chromium
python -m pricewatch.sources.fetch            # saves to data/pages/<time>/
```

Bolt, Replit and v0 are fetched over plain HTTP; Lovable is rendered in headless Chromium because its plans are built by JavaScript. A page that's blocked, times out or shows no prices is marked failed with the reason, and never replaced by older data. Reading plans from the text and comparing runs come next.

Credential-like values in the input (e.g. `config.demo_key`) are replaced with `[redacted]` wherever they would appear in the output.
