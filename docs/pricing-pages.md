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

## Check 2 · 2026-10-25 · from the build container

**How.** The project environment now allows the four domains. Each page was fetched with `curl` (browser user agent, redirects followed) and the raw HTML searched for the price strings, with `<script>`/`<style>` removed so only server-rendered text counts. Each page was then rendered in headless Chromium (Playwright) and the billing toggles clicked. Prices below were read straight from the HTML or the rendered page around 20:30 UTC; they are a snapshot for this check, not data the app uses.

| Competitor | `curl` | Plans and prices in raw HTML? | Billing toggle (default) | Browser needed? |
| --- | --- | --- | --- | --- |
| Lovable | 200, 186 KB | **No.** "Plans" heading, nothing under it; no `$` anywhere in the HTML or inline scripts | Monthly / Yearly ("2 months free"); default **Monthly** | **Yes** |
| Bolt | 200, 172 KB | **Yes**, yearly view only | Yearly / Monthly ("Save up to 28%"); default **Yearly** | Only for the monthly figures |
| Replit | 200, 261 KB | **Yes** (Next.js server render) | Monthly / Yearly ("Up to 10% off"); default **Yearly** | No |
| v0 | 200, 283 KB | **Yes** | None | No |

**What each page shows**

- **Lovable.** Rendered: Free `$0`; Pro `$25 / month`; Business `$50 / month`; Enterprise "Platform fee" (no number). Yearly toggle: Pro "Originally $25 per month" `$21 / month, billed annually`, Business "Originally $50 per month" `$42 / month, billed annually`. **Extra dimension:** Pro and Business each have a credits dropdown (default "100 monthly credits") that changes the price. Pro has 11 tiers, from "100 credits $25/mo" to "10,000 credits Save 10% $2250/mo". The JSON calls the page makes (`/_serverFn/…`) carry a status banner and a blog teaser, not prices; plans come from the JS bundle.
- **Bolt.** Raw HTML: Free `$0 /month`; Pro `$18 * /month`, "Total of $216 $300 / year Billed annually"; Teams `$27 * /month`, "Total of $324 $360 / year Per member, billed annually"; Enterprise "Custom". Monthly toggle (browser only): Pro `$25`, Teams `$30`. `$25` appears nowhere in the raw HTML, so monthly prices can only be quoted from a rendered page.
- **Replit.** Raw HTML: Core `<span>$20</span> $18 / month, billed annually`; Pro `$100 $90 / month, billed annually`; Enterprise "Custom". The `$20`/`$100` sit in their own span (shown struck through), so both periods are in the HTML, but the monthly figure is only labelled by position, not by words.
- **v0.** Free `$0 /month`; Plus `$30` followed by `<del>$90</del> /user/month` (a struck-through price, not a toggle; plain text extraction runs them together as "$30 $90", which is what check 1 saw); Business `$100 /user/month`; Enterprise "Custom". Also a per-model token price table (`$0.20/1M` etc.).

**Things that surprised us**

- **Replit blocks headless browsers after a couple of loads.** The first Playwright render worked; the next ones got a Cloudflare "Sorry, you have been blocked" page. `curl` kept returning 200 throughout. Replit should be fetched with plain HTTP only.
- **Lovable never reaches "network idle"** (it keeps a connection open); waiting for `networkidle` timed out at 45 s. Waiting for the DOM plus a few seconds, or for a price element, works.
- **Struck-through prices** appear on all four pages (Replit, v0, Lovable yearly, Bolt yearly totals). Plain text extraction loses the strike-through, so "$30 $90" reads like two prices for one thing.

**Implications (proposals for Guy, not decisions)**

1. Bolt, Replit and v0 can use `httpx`. Lovable needs Playwright (Chromium is already in this container; Render would need it installed).
2. Track one billing period per page as the default view (Lovable monthly, Bolt yearly, Replit yearly, v0 monthly) and record that period on every price. Clicking toggles adds browser work to three pages and Replit blocks the browser anyway. A toggle default changing is itself a packaging signal worth reporting.
3. For Lovable, track only the default credit tier (100 credits) unless Maya says the tier ladder matters.
4. Quotes must keep strike-through context (e.g. "Originally $25 per month"); extraction should treat a struck price as a list/previous price, never as the plan's price.
