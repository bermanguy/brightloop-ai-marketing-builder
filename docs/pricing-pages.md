# Pricing pages: plain HTML or browser?

Monday's first task (see `CLAUDE.md`): for each competitor's pricing page, can a plain HTTP fetch see the plans and prices, or does the page need a browser to run its JavaScript? The answer decides whether the live source needs Playwright.

## Check 1 · 2026-10-25 · preliminary

**How.** The build container's network policy blocks direct requests to all four sites (`403` on `CONNECT`), so `curl` couldn't run. Instead each page was read through a fetch tool that downloads the HTML **without running JavaScript** and converts it to text. If prices show up there, they are in the server's HTML.

**Limits of this check.** The tool summarises the page with a small model, so the figures below are indicative only, not quotes we can rely on. They are not used anywhere. Check 2 must repeat this with a raw `curl` (and a real browser for Lovable) and look at the HTML itself.

| Competitor | URL | Plans visible without JS? | What was seen |
| --- | --- | --- | --- |
| Lovable | https://lovable.dev/pricing | **No** | "Plans" heading with nothing under it; FAQ answers empty. Only a per-prompt credit table is present. Plans are likely loaded by JavaScript, or hidden in embedded JSON |
| Bolt | https://bolt.new/pricing | Yes | Free, Pro, Teams, Enterprise, with prices and token limits |
| Replit | https://replit.com/pricing | Yes | Core, Pro, Enterprise. Only the yearly-billed prices appear (monthly prices sit behind a toggle) |
| v0 | https://v0.app/pricing | Yes | Free, Plus, Business, Enterprise. Plus shows two prices run together ("$30$90"), probably a toggle or strike-through; needs a look at the raw HTML |

**Early implications (to confirm in check 2).**
- Three of four pages look fine with `httpx`.
- Lovable probably needs Playwright, unless the plans are in a JSON blob in the HTML (e.g. Next.js page data) that we can read without a browser.
- Monthly/yearly toggles (Replit, possibly v0) mean one page can hold two prices per plan. Extraction must record which billing period each price belongs to, and quotes must keep the period wording.

## Check 2 · to do

Raw `curl` of each page, plus a Playwright render of Lovable, from a machine that can reach the sites. Record: HTTP status, HTML size, whether each price string is in the raw HTML, and whether a browser render adds it.
