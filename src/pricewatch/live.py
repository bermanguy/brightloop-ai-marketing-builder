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
from .sources import ai_extract, compare, fetch


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_pages(directory):
    """Pages saved by fetch.save_pages (<competitor>.json), instead of fetching."""
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


def compare_and_report(read, cost, store, started_at):
    """Compare readings with the last snapshot, save them as a snapshot, run the core, log the run.

    Return (result, the signals the comparison produced).
    """
    good = store.last_good_pages()
    previous = {page["competitor"]: good.get((page["competitor"], page["reader"])) for page in read}
    previous = {competitor: page for competitor, page in previous.items() if page}
    signals = compare.compare(previous, {page["competitor"]: page for page in read})
    store.save_snapshot(started_at, read)

    result = process({"signals": signals, "timezone": "UTC"}, started_at=started_at, cost_usd=cost)
    result["run"]["notes"] = []
    for page in read:
        if not page["ok"]:
            result["run"]["errors"].append(f"{page['competitor']}: couldn't read {page['url']} ({page['error']}); not compared.")
            continue
        if page["ai_error"]:
            result["run"]["errors"].append(f"{page['competitor']}: AI reader: {page['ai_error']}.")
        if page["competitor"] not in previous:
            result["run"]["notes"].append(f"{page['competitor']}: first good reading, nothing to compare with yet (reader: {page['reader']}).")
    result["run"]["pages"] = [
        {"competitor": p["competitor"], "url": p["url"], "ok": p["ok"], "reader": p["reader"], "plans": len(p["plans"])}
        for p in read
    ]
    store.save_run(result)
    return result, signals


def run_live(store, pages_dir=None, use_ai=True, started_at=None):
    """One run, saved to the store. Returns the result, in the same shape as ./run's output."""
    started_at = started_at or now_utc()
    read, cost = collect(pages_dir, use_ai)
    return compare_and_report(read, cost, store, started_at)[0]
