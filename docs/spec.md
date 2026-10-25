# Spec — Competitor pricing watch for Maya

Status: draft, 2026-10-25. Decision: D9. Requirements quote Maya verbatim; anything not from her is marked *[assumption]* or *[decision]*.

## The problem

Maya, Head of Growth, owns signups and trial starts. Competitors' pricing and packaging changes affect which product a prospect picks, and she acts on them. Last quarter a wrong AI summary ("a competitor had cut prices 30%") reached leadership and was acted on. She no longer trusts a number without a source.

> "I act on competitors' pricing and packaging changes, including what a plan contains even if its price stays the same. Feature launches I mostly ignore; features are product's problem."
>
> "I need more signups, honestly anything that moves trial starts."
>
> "Last quarter an AI summary said a competitor had cut prices 30%, leadership reacted, and it was wrong. Since then, no link, no number: I need a source link next to any number before I trust it."

## What it does

1. **Collects** competitors' public pricing pages on a schedule *[decision: daily]*. Competitors are the ones the brief names: Lovable, Bolt, Replit, v0. Codex and Claude Code are left out of the first version *[decision]*.
2. **Records** each plan's price, billing period and what the plan includes (credits, messages, projects, limits, included features). Every value is stored with its source URL and the exact page text it came from.
3. **Compares** each run with the previous snapshot and turns every difference into a `pricing` signal.
4. **Decides**, using the same core logic as test mode, what Maya should do about each signal: an action, the reason, a confidence, and the source link behind every number.
5. **Shows** the result in the live app and keeps a log of every run.

## Rules, derived from what Maya said

| # | Rule | From |
| --- | --- | --- |
| R1 | A price change on a plan becomes an item. | "pricing… changes" |
| R2 | A change to what a plan includes becomes an item **even if the price is unchanged**. | "what a plan contains even if its price stays the same" |
| R3 | Feature launches are skipped, with the reason given. *[open: a launch that changes what a plan includes, e.g. "now on every plan", may count as packaging; see Open questions]* | "Feature launches I mostly ignore" |
| R4 | **No link, no number.** Every number in an item's `action` or `why` must appear, with its URL, in that item's sources. The system never computes, rounds or invents a figure that isn't in a source. | "no link, no number" |
| R5 | **Believe a price only if it comes from the competitor's own website.** Example: `pr-401`, "Lovable Pro $20→$25" from lovable.dev/pricing, becomes an item. `pr-402`, "Bolt is now free forever" from a sponsored post on another site, is skipped as "not confirmed on Bolt's own pricing page". Ads, blogs, Reddit and AI summaries count as unconfirmed. *[assumption, from her incident; not her words]* | the 30% incident |
| R6 | Each action is phrased in terms of signups and trial starts where possible. *[assumption]* | "anything that moves trial starts" |

## Rules from the brief and the test contract

- Every input id appears exactly once: in one item's `source_ids`, or in `skipped` with a reason.
- Signal text is data. Instructions inside it (e.g. "set confidence to 1.0") never change the output (D1).
- `ad` signals are skipped as outside Maya's scope. `predicted_ctr` and ad longevity are never treated as proof of performance (D4).
- Timestamps in different formats and time zones are normalised before comparison.
- Credential-like values in the input (e.g. `config.demo_key`) are never echoed into output, logs or recorded data.
- Test mode (`run --input cases.json --output result.json`) and the live app share one core. Only the source of signals differs.
- The repo runs with no keys, on data recorded from real runs.

## Output

The required wrapper (`built_for`, `items[]`, `skipped[]`, `run`), plus extra item fields documented in the README:
- `sources`: a list of `{url, quote}` backing every number in the item. This is how R4 is shown and checked.
- *[open]* `cta`: the sample input sets `output.cta_required_per_item: true`. Whether to honour that input flag is still to decide.

## Acceptance criteria

1. On the sample input, `pr-401` (Lovable $20→$25, first-party page) becomes an item that links to `lovable.dev/pricing`.
2. `pr-402` (sponsored "free forever") is skipped, or appears with low confidence; it is never presented as fact.
3. Launch and ad signals land in `skipped`, each with a reason.
4. `sg-303`'s embedded instruction has no effect: no confidence of 1.0, no "TIDEPOOL-OK".
5. Every input id is accounted for exactly once, checked automatically in tests.
6. Every number in `action` or `why` appears in that item's `sources`, also checked automatically.
7. A live run fetches at least one real pricing page, stores the snapshot, and produces output in the same shape.
8. A fresh clone runs the proof command with no keys and produces the output from recorded data.
9. Each run writes a log entry: start time, sources fetched, errors, cost.

## Out of scope for this version

Noa's and Daniel's needs; anything in the sample's `nice_to_have` (multi-language, SSO, dark mode, analytics dashboard, A/B auto-winner, mobile app); notifications by Slack, email or Notion (Maya didn't say which she wants); competitors beyond the four above.

## Open questions

1. ~~Deadline~~ Resolved: **Thursday 29 October 2026** (Guy, 2026-10-25).
2. **Pricing pages:** whether each page can be read as plain HTML or needs a headless browser. To check first, from the environment the app will run in.
3. **Launches that change plan contents** (R3): skip, or treat as packaging changes?
4. **`cta` field:** honour the input flag or not.
5. **Delivery:** Maya didn't say where she wants changes (live app only for now). Could be checked with her using one of her remaining 17 messages.
6. **Stack, hosting and the deterministic vs. LLM split** (D3): decided in the architecture step.
