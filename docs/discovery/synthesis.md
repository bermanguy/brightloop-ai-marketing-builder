# Discovery synthesis — 2026-10-25, updated 15:55

Draft scores by Claude, to be reviewed and changed by Guy. Every score cites the quote it rests on. Scale: 1 (weak) to 3 (strong).

## What each marketer told us (verbatim)

**Maya — Head of Growth** (6/25 used; 2 of those were repeats)
- "I act on competitors' pricing and packaging changes, including what a plan contains even if its price stays the same. Feature launches I mostly ignore; features are product's problem."
- "I'm Head of Growth. I need more signups, honestly anything that moves trial starts."
- "Last quarter an AI summary said a competitor had cut prices 30%, leadership reacted, and it was wrong. Since then, no link, no number: I need a source link next to any number before I trust it."

**Noa — PMM / content lead** (5/25 used)
- "Tell me what competitors ship; I need to know before Twitter does."
- "The same launch reaches me three or four times from different sources at different times, and I have to work out that it's one thing. Time zones make it worse: the US posts on Saturday night, and it's Sunday morning for me."
- "Last month I almost posted a reaction to a Reddit thread claiming v0 was shutting down. It was false. If it's a rumour, I don't want to see it, or at least don't label it huge."

**Daniel — Paid ads manager** (3/26 used)
- "I was given a tool that scored ads with predicted CTR. It ranked a two-day-old ad as the best one, and that ad died a week later. I don't trust predicted anything."
- "I work in Meta and LinkedIn, and every brief goes in Notion. A brief that isn't in Notion doesn't exist."
- "Ideas aren't the bottleneck; approvals are. I have 30 ideas in a doc, and four got approved last month. Briefs come back from Maya two or three times when they lack a rationale and an expected CPA."

## Pattern

Each marketer owns one signal type in the test contract, and each one's pain matches a trap in the sample input:

| Marketer | Signal type | Matching trap in the sample |
| --- | --- | --- |
| Maya | `pricing` | `pr-402` "Bolt is now free forever", a sponsored post rather than Bolt's own pricing page |
| Noa | `launch` | `sg-301`/`sg-302`: the same Replit launch in two sources and two time formats; `sg-304` Reddit rumour |
| Daniel | `ad` | `ad-117`/`ad-118`: `predicted_ctr` ranks a two-day-old ad above one running since August |

## Scores

| Criterion | Maya | Noa | Daniel |
| --- | --- | --- | --- |
| Pain | 3 — an AI summary wrongly reported a 30% price cut, "leadership reacted, and it was wrong" | 3 — recurring duplicate work, plus a near-miss: almost reacting publicly to a false v0 rumour | 3 — "four got approved last month", briefs bounce "two or three times" |
| Business impact | 3 — tied to her metric: "signups… trial starts" | 2 — avoiding public mistakes and reacting fast; no metric stated | 2 — approval throughput; no metric stated |
| Evidence strength | 3 — three distinct facts, including a concrete incident | 3 — three distinct facts, including a concrete incident | 3 — three distinct facts, including an incident |
| Public-data fit | 3 — competitor pricing pages are public. Risk: some may be JavaScript-rendered and need a headless browser | 2 — changelogs, blogs and Hacker News are easy; Reddit is limited; X is paid | 1 — expected CPA needs Brightloop's private ad data |
| Contract fit | 3 — `pricing` | 3 — `launch`; merging reports into one item maps directly onto `source_ids` holding several ids | 2 — `ad`, but his core pain is approvals |
| Buildable in ~12h | 3 — scheduled fetch + snapshot comparison + change classification | 2 — several sources plus cross-source matching | 1 — blocked on private data |
| Demoable | 3 — a real price or plan change | 3 — one launch merged from several real sources, with a rumour held back | 1 — cannot show a real expected CPA |
| **Total** | **21** | **18** | **13** |

## Requirements each marketer stated

**Maya:**
1. Act on price changes **and** on plan-content changes even when the price is unchanged.
2. Ignore feature launches.
3. "No link, no number": every number needs a source link next to it.
4. What matters is signups and trial starts.

**Noa:**
1. Merge reports of the same launch from different sources into one item.
2. Normalise time zones so a US Saturday-night post is understood as her Sunday morning.
3. Hold back rumours, or at least don't present them as big news.
4. Speed: know before it spreads on Twitter.

Noa's requirements line up one-to-one with the sample's launch traps: `sg-301`/`sg-302` (one launch, two sources, two time formats), `sg-304` (the Reddit v0 rumour), and `sg-303`, whose embedded text tries to force "most important launch of the year" and confidence 1.0, the opposite of "don't label it huge".

## Hard stops

- **Daniel:** his central need, expected CPA, depends on private ad-account data. That fails "real, live, public data". Not selected.
- Maya and Noa: no hard stops.

## Observations about the interview app

- **Each marketer appears to hold exactly three prepared facts.** All three have now given three distinct facts; further questions return either a free clarification or a paid repeat. Maya: about 20 probes after her third fact found nothing new.

- Questions outside a marketer's prepared facts return a free clarification.
- Questions on a covered topic sometimes repeat an earlier answer, and a repeat costs a message. Maya 2/25 and Noa 3/25 were repeats. This suggests each marketer's prepared facts are close to exhausted.

## Open

Selection between Maya and Noa: Guy's decision.
