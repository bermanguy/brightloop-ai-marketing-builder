"""Live source, step 1: download each competitor's pricing page as it looks on first load (D14).

Bolt, Replit and v0 put their plans in the server's HTML, so plain HTTP is
enough. Lovable builds its plans with JavaScript, so it is rendered in a
headless browser. Replit blocks headless browsers, so it must stay on HTTP
(docs/pricing-pages.md).

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

PAGES = {
    "Lovable": {"url": "https://lovable.dev/pricing", "method": "browser"},
    "Bolt": {"url": "https://bolt.new/pricing", "method": "http"},
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

    Struck-through text (<del>, <s>, or a CSS "line-through" class as on Replit)
    is wrapped in ~~ so a crossed-out list price can't be read as the plan's
    price: v0's "$30 ~~$90~~", not "$30$90".
    """

    STRUCK = {"del", "s", "strike"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    SKIP = {"script", "style", "noscript", "template", "svg", "head"}
    BLOCK = {
        "p", "div", "section", "article", "header", "footer", "main", "nav", "aside", "li", "ul", "ol",
        "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th", "table", "br", "hr", "button", "a", "label",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipping = 0
        self.struck_open = []  # tag names of open struck-through elements

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        if tag not in self.VOID and self._is_struck(tag, attrs):
            self.struck_open.append(tag)
            self.parts.append(" ~~")
        elif self.struck_open and tag == self.struck_open[-1]:
            self.struck_open.append(tag + "/plain")  # same tag nested inside: not a closer

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skipping = max(0, self.skipping - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")
        if self.struck_open and self.struck_open[-1] == tag + "/plain":
            self.struck_open.pop()
        elif self.struck_open and self.struck_open[-1] == tag:
            self.struck_open.pop()
            self.parts.append("~~ ")

    def _is_struck(self, tag, attrs):
        if tag in self.STRUCK:
            return True
        classes = dict(attrs).get("class") or ""
        return "line-through" in classes.split()

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def visible_text(html):
    parser = _TextExtractor()
    parser.feed(html or "")
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def check_page(status, text):
    """Return None if the page looks like a pricing page, else why it doesn't."""
    if status != 200:
        return f"HTTP {status}"
    if BLOCKED.search(text[:5000]):
        return "blocked or challenge page"
    if not PRICE.search(text):
        return "no prices found on the page (layout change, or plans not rendered)"
    return None


def _fetch_http(url):
    import httpx

    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=TIMEOUT_S)
    return response.status_code, response.text


def _fetch_browser(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # CHROMIUM_PATH lets a machine with a preinstalled Chromium use it.
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            response = page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_S * 1000)
            # Lovable never reaches network idle; wait for a price to render instead.
            page.get_by_text(re.compile(r"\$\s?\d")).first.wait_for(timeout=TIMEOUT_S * 1000)
            return (response.status if response else 0), page.content()
        finally:
            browser.close()


def fetch_page(competitor):
    """Fetch one competitor's pricing page. Never raises."""
    spec = PAGES[competitor]
    page = {
        "competitor": competitor,
        "url": spec["url"],
        "method": spec["method"],
        "fetched_at": now_utc(),
        "ok": False,
        "status": None,
        "error": None,
        "html": "",
        "text": "",
    }
    try:
        fetch = _fetch_browser if spec["method"] == "browser" else _fetch_http
        page["status"], page["html"] = fetch(spec["url"])
        page["text"] = visible_text(page["html"])
        page["error"] = check_page(page["status"], page["text"])
    except Exception as exc:  # network errors, timeouts, browser failures
        page["error"] = f"{exc.__class__.__name__}: {str(exc).splitlines()[0][:200] if str(exc) else ''}"
    page["ok"] = page["error"] is None
    return page


def fetch_all(competitors=None):
    return [fetch_page(name) for name in (competitors or PAGES)]


def save_pages(pages, out_dir):
    """Write <competitor>.html (raw page) and <competitor>.json (everything else, incl. visible text)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for page in pages:
        name = page["competitor"].lower()
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
        print(f"{page['competitor']:8} {page['method']:7} {len(page['text']):6} chars  {state}")
    print(f"saved to {out}")
    return 0 if all(page["ok"] for page in pages) else 1


if __name__ == "__main__":
    sys.exit(main())
