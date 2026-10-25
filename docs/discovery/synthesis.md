# Discovery synthesis — 2026-10-25, 15:30

Draft scores by Claude, to be reviewed and changed by Guy. Every score cites the quote it rests on. Scale: 1 (weak) to 3 (strong).

## What each marketer told us (verbatim)

**Maya — Head of Growth** (3/25 used)
- "I act on competitors' pricing and packaging changes, including what a plan contains even if its price stays the same. Feature launches I mostly ignore; features are product's problem."
- "I'm Head of Growth. I need more signups, honestly anything that moves trial starts."

**Noa — PMM / content lead** (3/25 used)
- "Tell me what competitors ship; I need to know before Twitter does."
- "The same launch reaches me three or four times from different sources at different times, and I have to work out that it's one thing. Time zones make it worse: the US posts on Saturday night, and it's Sunday morning for me."

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
| Pain | 2 — clear rule of what she acts on, no incident or cost given | 3 — a concrete, recurring problem ("three or four times… time zones") | 3 — "four got approved last month", briefs bounce "two or three times" |
| Business impact | 3 — tied to her metric: "signups… trial starts" | 2 — speed and accuracy of launch response; no metric stated | 2 — approval throughput; no metric stated |
| Evidence strength | 2 — two facts, one repeated | 2 — two facts, one repeated | 3 — three distinct facts, including an incident |
| Public-data fit | 3 — competitor pricing pages are public and easy to fetch and compare over time | 2 — changelogs and blogs are easy; X and Reddit are paid or restricted, and "before Twitter" is hard to prove | 1 — expected CPA needs Brightloop's private ad data; Meta and LinkedIn ad libraries are hard to reach |
| Contract fit | 3 — `pricing` | 3 — `launch`, including the dedup and time-zone cases | 2 — `ad`, but his core pain is approvals, not ad signals |
| Buildable in ~12h | 3 — scheduled fetch + snapshot comparison + change classification | 2 — several sources plus cross-source matching | 1 — blocked on private data |
| Demoable | 3 — a real price or plan change on a real competitor page | 3 — one launch merged from several real sources | 1 — cannot show a real expected CPA |
| **Total** | **19** | **17** | **13** |

## Hard stops

- **Daniel:** his central need, expected CPA, depends on private ad-account data. That fails "real, live, public data". Not selected.
- Maya and Noa: no hard stops.

## Observations about the interview app

- Questions outside a marketer's prepared facts return a free clarification.
- Questions on a covered topic sometimes repeat an earlier answer, and a repeat costs a message. Maya 2/25 and Noa 3/25 were repeats. This suggests each marketer's prepared facts are close to exhausted.

## Open

Selection between Maya and Noa: Guy's decision.
