# Pricing Watch, explained in plain English

For Guy, for the Base44 interview on 4 November 2026. The facts here were checked against the code and production on 3 November (D44). The two scripts and the Q&A answers are suggested wording: adjust them to how you would say it. The technical detail is in `docs/architecture.md`; the decisions are in `DECISIONS.md`.

## The 60-second architecture explanation

> Maya runs growth at Brightloop. Her team once acted on an AI summary that said a competitor cut prices 30%, and it was wrong. So her rule is "no link, no number".
>
> Pricing Watch checks Lovable, Bolt, Replit and v0's pricing pages every 6 hours, on its own. Claude reads each page and lists the plans and prices, and every value has to come with a quote. Then plain code takes over: it checks each quote is on the page word for word, compares the reading with the last one, and turns each difference into a card. Code, not AI, sets the confidence, the "unverified" label and the next steps, and checks that every number on a card is in its quote.
>
> The cards land in a Base44 dashboard, in email and Slack alerts, and in Claude through an MCP connector. The brief's test file goes through exactly the same core, from the command line or the Test upload page, with no keys. And `./proof` replays recorded real runs on a fresh clone and checks every rule.
>
> So: AI reads, rules decide, and every number keeps its link.

## The 60-second post-submission explanation

> I submitted on 29 October. In the first week of real data, two things showed up.
>
> First, reliability: Bolt's billing toggle sometimes didn't switch on Render, and Lovable's "Platform fee" was flagged as a price change when the reader filed it differently. I fixed both, and failed pages are always reported and never compared.
>
> Second, usefulness: the cards were accurate but repetitive. Every plan-contents change said the same thing, "anything we publish is now out of date, update it", even when the page had only lost an asterisk or reworded a description. So I added a layer that says what the page actually changed and what to check next. For eight real cards, Claude interpreted the change offline, picking only from an approved playbook, and rules decided what to show. Every new change gets safe next steps written by rules. I also simplified the dashboard and added a Focused view.
>
> What I deliberately didn't change: the core, the confidence rules, the quote check, the alerts and the brief's test contract.

## What was working on 29 October (the original submission)

- The live watch: four pricing pages every 6 hours (Render, always on, with a GitHub backup), both billing views for Lovable and Bolt, read by Claude with a word-for-word quote check, compared with the last snapshot, stored in Neon Postgres.
- Hacker News pricing claims, always labelled unverified.
- The shared core with all the brief's rules.
- The Base44 app: Changes, Current pricing, Run log, Alerts, Test upload, Check now.
- Email and Slack alerts with filters and an alert log.
- The MCP connector with four read-only tools.
- `./run`, `./proof`, 210 tests, CI on every push.

## What changed after the submission, and why

| What was weak | What changed | Why |
| --- | --- | --- |
| Bolt's page failed on some nights (the billing toggle timed out on Render's slower CPU) | PRs #40–#44: confirm each toggle click, let the page settle, skip unneeded clicks, retry on a fresh load | A failed page means no comparison for that page. Since #44 (2 Nov) every run has read all six page views |
| Lovable's Enterprise "Platform fee" showed up as a price change | PR #42: a worded price read as "no price" on the same card isn't a change | False alerts cost trust, which is the whole product |
| Every plan-contents card had the same generic action | D40: offline AI interpretation, rules choose actions from an approved playbook | Rule-only text repeated itself and missed the meaning (Guy, D40) |
| Cards were long and mixed fact, guess and advice | D41–D42: one card component, a plain headline from the page lines, a status set by rule, the uncertainty stated once | Maya should tell a page change from an offer change in seconds (Guy, D41) |
| New changes had no specific next step | D43: rule-written next steps for every new card | So no card is left with a generic or misleading action |
| No way to set a card aside | D43: Focused view / Hide, in the browser only | A focused view without losing the monitoring history (Guy, D43) |
| Test upload rows misread numeric and empty ids; its cards didn't say what they show | D44 (this audit): fixed, and explained on the page | The test contract is what reviewers check |

## Where AI is used, and where code takes over

There are exactly three places where AI is involved, and only one runs by itself in production.

1. **Reading pricing pages (automatic, every run).** Claude gets the page text and returns plans and prices, each with a quote. Code then checks each quote is on the page word for word and drops anything that isn't. If the AI fails or there's no key, a plain reader does the job.
2. **Interpreting a change (offline, by hand).** For a verified change in what a plan includes, Claude returns a category, the old and new page lines, a direction, whether the meaning is clear, and ids from an approved list of actions. It writes no sentences. Code checks every part and writes the text. I ran it once on 3 November over 8 cards ($0.06), reviewed the result and shipped it as a file.
3. **Answering questions (when someone asks).** Any MCP client, such as Claude, can query the data. That AI is the user's own; the server tells it to quote and link every number.

Everything else is plain code: whether something changed, the confidence and unverified label, which signals are skipped, every input id once, the stored headline and action, the dashboard's headlines and next steps, the statuses, the alerts and the counters.

## Test upload: what it proves, and why it looks different from the dashboard

**What it proves.** The brief asks that the live app and the test mode share one core, with only the source of signals different. Test upload sends a `cases.json` to the same core the live watch uses. It shows, for every input id, whether it became a card or was skipped and why, and lets you download `result.json`. The command line (`./run`), Test upload and Claude's `run_test` tool give the same `result.json` for the same file; a test checks this on every case file.

**Why the cards differ from the dashboard.** The dashboard adds a display layer to live cards: headlines and next steps written from the page lines a check compared, and the reviewed interpretations. That layer needs things a test file doesn't have: the comparison's "now shows … no longer shows …" wording and a live card id. So Test upload shows the core's own rule-written text, exactly as `result.json` has it. That's deliberate: the brief's contract shouldn't change to match a presentation. The page now says so above the cards.

**What it doesn't do.** It saves nothing and doesn't change the other tabs. The only exception is if you tick the TEST alert box: then it sends one email or Slack message, rate-limited, and logs it in the alert log.

## Known limitations

1. Only 8 cards have an AI interpretation. New changes get rule-written next steps, not an AI reading.
2. Since D45 every screen and alert shows the same next steps, but each card's stored `action` (in `result.json` and the raw API) is still the core's broader text.
3. `./proof` replays recorded runs from 25–26 October, which had no changes. Real changes are covered by tests on their stored cards.
4. The Test upload wording fix is in the repo's copy of the Base44 app, but not yet published to Base44. The row fix is in the engine, but not yet deployed to Render.
5. Anyone with the link can change alert settings and press Check now (rate-limited).
6. Test upload has no file-size limit (a 5,000-signal file answers in under a second).

## The next engineering step

Run the interpretation automatically for new changes, without weakening verification:

1. After a live run saves its cards, send only the eligible ones (verified, from the competitor's own pricing page, plan contents or limits) to `interpret.interpret`, with a cap on calls and cost.
2. Store each reading in its own table, keyed by card id. Never edit the card itself.
3. Keep every existing check: the lines must be quoted from the page, unclear meaning gets verification-only actions, every figure must be in the source, and any failure leaves the card with its rule-written steps.
4. Run it in shadow mode for a week (store, don't show), review the readings with Maya, then switch it on behind its own flag.

## Interview Q&A

**Why use AI for extraction?**
Pricing pages are built for people, change layout often, and differ per competitor. Hand-written parsers break on every redesign. Claude reads the page like a person would. But I don't trust its output: every value has to come with a quote that code finds on the page word for word, so the AI can only point at what's there.

**Why use rules for verification?**
Because verification has to be the same every time and can't be talked out of. Confidence comes from where a claim came from, never from its text, so an instruction hidden in a page can't raise it. A quote is either on the page or it isn't. Rules are cheap, testable and explainable to Maya.

**Why precompute the enhanced interpretations?**
For the demo, I wanted the interpretations reviewed before anyone saw them, with no model call in production I hadn't checked. It's the same code path that would run live: the model's answer goes through the same rule checks, and the result is matched by card id. Precomputing let me ship the layer safely, behind a flag that returns the original cards byte for byte when it's off.

**Why doesn't Test upload show the same recommendations as the dashboard?**
Test upload proves the brief's contract: one core for live and test data, with every id accounted for. The dashboard adds a display layer that only works on live cards, because it reads what the comparison wrote and live card ids. Forcing that into the test output would change the contract the assignment is judged on. So Test upload shows the core's text and says why.

**How do you prevent hallucinations?**
The AI never gets to state a fact on its own. In extraction, every value needs a word-for-word quote from the page. In interpretation, the model picks from enums and an approved playbook and copies page lines, which code checks against the quote; it writes no text. And every number shown anywhere must appear in that card's sources, or the text is replaced.

**How do you prevent prompt injection?**
Page and signal text is always data: it goes to the model inside tags, with a system prompt saying instructions in it are content. Hidden HTML is stripped before anything is quoted. The decisions that matter (confidence, labels, skips, actions) never read the text. The brief's two planted injections are checked in `./proof` and the tests, and at worst a crafted page could move the interpretation to another approved option, never outside the rules.

**How do you know the system works?**
`./proof` on a fresh clone with no keys: the brief's sample and three recorded real runs, every rule checked. 298 tests in CI on every push, including the test contract across the command line, Test upload and MCP. Four case files with the expected result for every id. And in production, the run log shows a run about every 6 hours, with the pages read, the changes, the errors and the cost.

**What would you build next?**
Automatic interpretation of new changes, stored separately and in shadow mode first, with the same checks. Then I'd validate the cards with Maya on real changes, and see whether the next steps lead to the decisions she actually makes.
