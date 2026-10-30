"""Live source, step 1: download each competitor's pricing page, in every billing view it offers.

Replit and v0 put everything in the server's HTML, so plain HTTP is enough.
Lovable builds its plans with JavaScript, and Lovable and Bolt hide one billing
period behind a Monthly/Yearly toggle, so both are rendered in a headless
browser that clicks each side of the toggle. Lovable's credit dropdowns are
opened too, and their options (each a credit amount and its price) are kept
as the page shows them. Replit blocks headless browsers, so it stays on HTTP;
its monthly price is the struck-through one next to the yearly price.
(docs/pricing-pages.md)

Each view of a page is its own record ("view": "Monthly", "Yearly", or None for
a page with one view), read and compared on its own. "opens_on" says which view
the page shows on first load, which is itself a packaging signal (D20).

A page that can't be fetched or read comes back with ok=False and the reason.
It never stops the other pages, and it is never replaced by older data (D12).
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

# views: (name, ARIA role of the toggle control, its label), clicked in turn.
PAGES = {
    "Lovable": {"url": "https://lovable.dev/pricing", "method": "browser", "dropdowns": True,
                "views": [("Monthly", "button", r"^Monthly"), ("Yearly", "button", r"^Yearly")]},
    "Bolt": {"url": "https://bolt.new/pricing", "method": "browser",
             "views": [("Monthly", "tab", r"^Monthly"), ("Yearly", "tab", r"^Yearly")]},
    "Replit": {"url": "https://replit.com/pricing", "method": "http"},
    "v0": {"url": "https://v0.app/pricing", "method": "http"},
}

USER_AGENT = "Mozilla/5.0 (compatible; BrightloopPricewatch/0.1)"
TIMEOUT_S = 30

# Signs that we got a block or challenge page instead of the pricing page.
BLOCKED = re.compile(r"you have been blocked|just a moment\.\.\.|verify you are human|access denied", re.I)
PRICE = re.compile(r"\$\s?\d")


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _TextExtractor(HTMLParser):
    """Visible text of a page, one block per line. Scripts, styles and hidden templates are dropped.

    Each <option> of a dropdown is its own line, so a plan's tiers aren't run
    together ("$90 / month$215 / month").

    Struck-through text (<del>, <s>, or a CSS "line-through" class as on Replit)
    is wrapped in ~~ so a crossed-out list price can't be read as the plan's
    price: v0's "$30 ~~$90~~", not "$30$90".

    An inline element styled as a block ("block", "flex" or "grid" class, as on
    Lovable and v0) ends its line, so a plan name and its description aren't run
    together ("v0 Mini" then "Lightning-fast speed...", not "v0 MiniLightning-fast
    speed..."). A link inside a sentence stays in it ("Centralized billing on
    vercel.com"); a link on its own, like a menu item, is its own line.
    """

    STRUCK = {"del", "s", "strike"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    SKIP = {"script", "style", "noscript", "template", "svg", "head"}
    BLOCK = {
        "p", "div", "section", "article", "header", "footer", "main", "nav", "aside", "li", "ul", "ol",
        "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th", "table", "br", "hr", "button", "label", "option",
    }
    BLOCK_CLASSES = {"block", "flex", "grid"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipping = 0
        self.struck_open = []  # tag names of open struck-through elements
        self.styled_open = []  # (tag, styled as a block) for each open inline element
        self.selects = []  # each <select>'s options, and the page line it sits after
        self.in_option = False

    def handle_starttag(self, tag, attrs):
        if tag == "select":
            done = "".join(self.parts).split("\n")
            self.selects.append({"line": sum(1 for line in done if line.strip()), "options": []})
        if tag == "option" and self.selects:
            self.selects[-1]["options"].append("")
            self.in_option = True
        if tag in self.SKIP:
            self.skipping += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag not in self.VOID:
            styled = not self.BLOCK_CLASSES.isdisjoint((dict(attrs).get("class") or "").split())
            # A link inside a sentence stays inline; one on its own (a menu item, a button) is its own line.
            if tag == "a" and not self._after_text():
                styled = True
                self.parts.append("\n")
            self.styled_open.append((tag, styled))
        if tag not in self.VOID and self._is_struck(tag, attrs):
            self.struck_open.append(tag)
            self.parts.append(" ~~")
        elif self.struck_open and tag == self.struck_open[-1]:
            self.struck_open.append(tag + "/plain")  # same tag nested inside: not a closer

    def handle_endtag(self, tag):
        if tag in ("option", "select"):
            self.in_option = False
        if tag in self.SKIP:
            self.skipping = max(0, self.skipping - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif any(open_tag == tag for open_tag, _ in self.styled_open):
            while self.styled_open:
                open_tag, styled = self.styled_open.pop()
                if open_tag == tag:
                    if styled:
                        self.parts.append("\n")
                    break
        if self.struck_open and self.struck_open[-1] == tag + "/plain":
            self.struck_open.pop()
        elif self.struck_open and self.struck_open[-1] == tag:
            self.struck_open.pop()
            # Close the ~~ on the struck text's own line (Lovable's "~~$25~~"), not after a line break.
            breaks = 0
            while self.parts and self.parts[-1] == "\n":
                self.parts.pop()
                breaks += 1
            self.parts.append("~~ " + "\n" * breaks)

    def _after_text(self):
        for part in reversed(self.parts):
            if part.strip(" "):
                return not part.endswith("\n")
        return False

    def _is_struck(self, tag, attrs):
        if tag in self.STRUCK:
            return True
        classes = dict(attrs).get("class") or ""
        return "line-through" in classes.split()

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)
            if self.in_option:
                self.selects[-1]["options"][-1] += data


def visible_text(html):
    parser = _TextExtractor()
    parser.feed(html or "")
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def selects(html):
    """The options of each <select> on a server-rendered page, as written, and the page line
    they follow: Replit's Pro credit tiers ("$90 / month" … "$2,000 / month"), 2026-10-27."""
    parser = _TextExtractor()
    parser.feed(html or "")
    found = []
    for select in parser.selects:
        options = [" ".join(o.split()) for o in select["options"]]
        if any(options):
            found.append({"plan": None, "after_line": select["line"], "options": [o for o in options if o]})
    return found


def check_page(status, text):
    """Return None if the page looks like a pricing page, else why it doesn't."""
    if status != 200:
        return f"HTTP {status}"
    if BLOCKED.search(text[:5000]):
        return "blocked or challenge page"
    if not PRICE.search(text):
        return "no prices found on the page (layout change, or plans not rendered)"
    return None


def label(page):
    """How a page is named in notes and errors: "Bolt (Yearly)", or "Replit" for a one-view page."""
    return f"{page['competitor']} ({page['view']})" if page.get("view") else page["competitor"]


def _fetch_http(spec):
    import httpx

    response = httpx.get(spec["url"], headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=TIMEOUT_S)
    return {"status": response.status_code, "opens_on": None,
            "views": [{"view": None, "html": response.text, "dropdowns": selects(response.text)}]}


def _price_lines(html):
    return {line for line in visible_text(html).split("\n") if PRICE.search(line)}


def _open_dropdowns(page):
    """Each credit dropdown's options, as shown: [{"plan": "Pro", "label": "100 monthly credits", "options": [...]}]."""
    found = []
    for index in range(page.get_by_role("combobox").count()):
        box = page.get_by_role("combobox").nth(index)
        # The plan is the heading of the smallest block around the dropdown that has one.
        plan = box.evaluate(
            """el => { for (let n = el.parentElement; n; n = n.parentElement) {
                 const h = n.querySelector('h1, h2, h3, h4'); if (h) return h.innerText.trim(); } return null; }"""
        )
        default = " ".join(box.inner_text().split())
        box.click()
        page.get_by_role("option").first.wait_for(timeout=TIMEOUT_S * 1000)
        options = [" ".join(option.inner_text().split()) for option in page.get_by_role("option").all()]
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        found.append({"plan": plan, "label": default, "options": options})
    return found


# A toggle side counts as chosen once the page marks it so: Bolt's tabs use
# aria-selected, Lovable's buttons aria-pressed.
CHOSEN = """el => ['aria-selected', 'aria-pressed', 'aria-checked'].some(a => el.getAttribute(a) === 'true')
               || !['aria-selected', 'aria-pressed', 'aria-checked'].some(a => el.hasAttribute(a))"""


def _choose_view(page, role, control, name):
    """Click one side of a billing toggle until the page marks it as chosen.

    Bolt shows its prices about three seconds before its JavaScript is ready, and a
    click in that gap is silently lost: the "Yearly" view came back with the monthly
    prices (2026-10-30). So each click is followed by a check that it took, and
    retried until it does. A click Playwright can't make (something over the toggle)
    is retried with force, which skips its checks and clicks the spot anyway.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    toggle = page.get_by_role(role, name=re.compile(control, re.I)).first
    toggle.wait_for(timeout=TIMEOUT_S * 1000)
    for _ in range(5):
        try:
            toggle.click(timeout=5000)
        except PlaywrightTimeout:
            toggle.click(timeout=5000, force=True)
        try:
            page.wait_for_function(f"el => ({CHOSEN})(el)", arg=toggle.element_handle(), timeout=3000)
            return
        except PlaywrightTimeout:
            continue
    raise RuntimeError(f"the {name} toggle didn't switch the page after 5 clicks")


def _same_prices(views):
    """Views after the first whose prices match an earlier view's: a toggle that didn't switch."""
    seen, repeats = [], set()
    for view in views:
        lines = _price_lines(view["html"])
        if lines and lines in seen:
            repeats.add(view["view"])
        seen.append(lines)
    return repeats


def _fetch_browser(spec):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # CHROMIUM_PATH lets a machine with a preinstalled Chromium use it.
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            response = page.goto(spec["url"], wait_until="domcontentloaded", timeout=TIMEOUT_S * 1000)
            # Lovable never reaches network idle; wait for a visible price instead.
            page.locator("text=/\\$\\s?\\d/ >> visible=true").first.wait_for(timeout=TIMEOUT_S * 1000)
            page.wait_for_timeout(1000)
            first = page.content()
            views = []
            for name, role, control in spec.get("views") or [(None, None, None)]:
                if role:
                    _choose_view(page, role, control, name)
                    page.wait_for_timeout(1000)
                html = page.content()  # before any dropdown is opened, so its options aren't in the text
                dropdowns = _open_dropdowns(page) if spec.get("dropdowns") else []
                views.append({"view": name, "html": html, "dropdowns": dropdowns})
            # The view whose prices match the first load is the one the page opens on.
            opens_on = next((v["view"] for v in views if v["view"] and _price_lines(v["html"]) == _price_lines(first)), None)
            return {"status": response.status if response else 0, "opens_on": opens_on, "views": views}
        finally:
            browser.close()


def _reason(exc):
    """An error's first line, plus the last line of Playwright's call log when there is one,
    which says what it was waiting for ("<div …> intercepts pointer events")."""
    lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
    if not lines:
        return ""
    reason = lines[0][:200]
    if len(lines) > 1 and any(line.startswith("Call log") for line in lines):
        reason += f" ({lines[-1].lstrip('- ')[:200]})"
    return reason


def fetch_page(competitor):
    """Fetch one competitor's pricing page: one record per view. Never raises."""
    spec = PAGES[competitor]
    base = {
        "competitor": competitor,
        "url": spec["url"],
        "method": spec["method"],
        "fetched_at": now_utc(),
        "ok": False,
        "status": None,
        "error": None,
        "opens_on": None,
    }
    names = [name for name, _, _ in spec.get("views", [])] or [None]
    try:
        fetched = (_fetch_browser if spec["method"] == "browser" else _fetch_http)(spec)
    except Exception as exc:  # network errors, timeouts, browser failures, a toggle that's gone
        error = f"{exc.__class__.__name__}: {_reason(exc)}"
        return [dict(base, view=name, view_index=i, error=error, html="", text="", dropdowns=[]) for i, name in enumerate(names)]

    repeats = _same_prices(fetched["views"]) if len(fetched["views"]) > 1 else set()
    records = []
    for index, view in enumerate(fetched["views"]):
        record = dict(base, view=view["view"], view_index=index, status=fetched["status"], opens_on=fetched["opens_on"],
                      html=view["html"], text=visible_text(view["html"]), dropdowns=view["dropdowns"])
        record["error"] = check_page(record["status"], record["text"])
        if not record["error"] and view["view"] in repeats:
            record["error"] = f"the {view['view']} view shows the same prices as another view (the toggle didn't switch)"
        record["ok"] = record["error"] is None
        records.append(record)
    return records


def fetch_all(competitors=None):
    return [record for name in (competitors or PAGES) for record in fetch_page(name)]


def save_pages(pages, out_dir):
    """Write <competitor>[-<view>].html (raw page) and .json (everything else, incl. visible text)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for page in pages:
        name = page["competitor"].lower() + (f"-{page['view'].lower()}" if page.get("view") else "")
        (out / f"{name}.html").write_text(page["html"], encoding="utf-8")
        meta = {key: value for key, value in page.items() if key != "html"}
        (out / f"{name}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch the competitors' pricing pages and save them.")
    parser.add_argument("--out", help="directory to save into (default: data/pages/<time>)")
    parser.add_argument("--only", nargs="*", choices=list(PAGES), help="fetch only these competitors")
    args = parser.parse_args(argv)

    pages = fetch_all(args.only)
    out = save_pages(pages, args.out or Path("data") / "pages" / now_utc().replace(":", ""))
    for page in pages:
        state = "ok" if page["ok"] else f"FAILED: {page['error']}"
        print(f"{label(page):18} {page['method']:7} {len(page['text']):6} chars  {state}")
    print(f"saved to {out}")
    return 0 if all(page["ok"] for page in pages) else 1


if __name__ == "__main__":
    sys.exit(main())
