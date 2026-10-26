"""One live run: fetch the pricing pages, read their plans, compare with the last snapshot, run the core.

    ./run --live --output result.json

Each run saves a snapshot to the store (store.py): every page's plans, or why
it couldn't be read, and logs the run's result. The next run compares each page
with the last snapshot in which that page was read by the same reader, so a
page that failed once is compared again as soon as it's back. The AI and plain readers pick
slightly different lines for a plan, so comparing across readers would report
changes that never happened (15 on the recorded pages).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .core import process
from .sources import ai_extract, compare, fetch, rumors


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_pages(directory):
    """Pages saved by fetch.save_pages (<competitor>[-<view>].json), instead of fetching."""
    pages = []
    for path in sorted(Path(directory).glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        html = path.with_suffix(".html")
        page["html"] = html.read_text(encoding="utf-8") if html.exists() else ""
        pages.append(page)
    return pages


def collect(pages_dir=None, use_ai=True):
    """Fetch (or load) the pages and read their plans. Return (readings, cost in USD)."""
    pages = load_pages(pages_dir) if pages_dir else fetch.fetch_all()
    return ai_extract.read_pages(pages, ai_extract.make_client() if use_ai else None)


def with_page_check(rumor, read):
    """The rumor, plus what the competitor's own pricing page showed in this run (the view it opens on),
    so Maya sees the claim and the page side by side. Unchanged if the page wasn't read."""
    page = next((p for p in read if p["competitor"] == rumor["competitor"] and p["ok"] and not p.get("view_index")), None)
    if not page or not page["plans"]:
        return rumor
    shown = "; ".join(f"{plan['name']}: {compare._price_words(plan)}" for plan in page["plans"])
    view = f" ({page['view']} view)" if page.get("view") else ""
    return dict(rumor, page_check={"url": page["url"], "checked_at": page["fetched_at"], "quote": f"Plans on the page{view}: {shown}."})


def compare_and_report(read, cost, store, started_at, rumor_signals=(), rumor_errors=()):
    """Compare readings with the last snapshot, save them as a snapshot, run the core, log the run.

    rumor_signals: pricing claims found elsewhere (rumors.find), reported alongside.
    Return (result, the signals the comparison produced, then the rumors).
    """
    good = store.last_good_pages()
    label = fetch.label
    previous = {label(page): good.get((page["competitor"], page.get("view"), page["reader"])) for page in read}
    previous = {name: page for name, page in previous.items() if page}
    signals = compare.compare(previous, {label(page): page for page in read}) + [with_page_check(s, read) for s in rumor_signals]
    store.save_snapshot(started_at, read, rumors=[s["hn_id"] for s in rumor_signals if s.get("hn_id")])

    result = process({"signals": signals, "timezone": "UTC"}, started_at=started_at, cost_usd=cost)
    result["run"]["notes"] = []
    result["run"]["errors"].extend(rumor_errors)
    for page in read:
        if not page["ok"]:
            result["run"]["errors"].append(f"{label(page)}: couldn't read {page['url']} ({page['error']}); not compared.")
            continue
        if page["ai_error"]:
            result["run"]["errors"].append(f"{label(page)}: AI reader: {page['ai_error']}.")
        if label(page) not in previous:
            result["run"]["notes"].append(f"{label(page)}: first good reading, nothing to compare with yet (reader: {page['reader']}).")
    result["run"]["pages"] = [
        {"competitor": p["competitor"], "view": p.get("view"), "url": p["url"], "ok": p["ok"], "reader": p["reader"],
         "plans": len(p["plans"]), "tables": len(p.get("tables") or [])}
        for p in read
    ]
    store.save_run(result)
    return result, signals


def run_live(store, pages_dir=None, use_ai=True, started_at=None):
    """One run, saved to the store. Returns the result, in the same shape as ./run's output.

    A live run also searches Hacker News for pricing claims; a run from saved pages doesn't.
    """
    started_at = started_at or now_utc()
    read, cost = collect(pages_dir, use_ai)
    found, errors = ([], []) if pages_dir else rumors.find(store.seen_rumors())
    return compare_and_report(read, cost, store, started_at, found, errors)[0]
