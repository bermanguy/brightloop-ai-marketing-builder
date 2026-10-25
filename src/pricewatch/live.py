"""One live run: fetch the pricing pages, read their plans, compare with the last snapshot, run the core.

    ./run --live --output result.json

Each run saves a snapshot (data/snapshots/<time>.json): every page's plans,
or why it couldn't be read. The next run compares each page with the last
snapshot in which that page was read by the same reader, so a page that failed
once is compared again as soon as it's back. The AI and plain readers pick
slightly different lines for a plan, so comparing across readers would report
changes that never happened (15 on the recorded pages). Snapshots are JSON
files for now; the database replaces them at deploy.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .core import process
from .sources import ai_extract, compare, fetch

SNAPSHOTS = Path("data") / "snapshots"
PAGE_FIELDS = ("competitor", "url", "method", "fetched_at", "ok", "status", "error", "reader", "ai_error", "cost_usd", "plans")


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


def last_good_pages(snapshots_dir):
    """{(competitor, reader): page} from the newest snapshot in which each page was read by that reader."""
    found = {}
    for path in sorted(Path(snapshots_dir).glob("*.json"), reverse=True):
        for page in json.loads(path.read_text(encoding="utf-8"))["pages"]:
            key = (page["competitor"], page["reader"])
            if page.get("ok") and key not in found:
                found[key] = page
    return found


def save_snapshot(snapshots_dir, taken_at, pages):
    out = Path(snapshots_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{taken_at.replace(':', '')}.json"
    snapshot = {"taken_at": taken_at, "pages": [{key: page.get(key) for key in PAGE_FIELDS} for page in pages]}
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def collect(pages_dir=None, use_ai=True):
    """Fetch (or load) the pages and read their plans. Return (readings, cost in USD)."""
    pages = load_pages(pages_dir) if pages_dir else fetch.fetch_all()
    return ai_extract.read_pages(pages, ai_extract.make_client() if use_ai else None)


def compare_and_report(read, cost, snapshots_dir, started_at):
    """Compare readings with the last snapshot, save them as a snapshot, run the core.

    Return (result, snapshot path, the signals the comparison produced).
    """
    good = last_good_pages(snapshots_dir)
    previous = {page["competitor"]: good.get((page["competitor"], page["reader"])) for page in read}
    previous = {competitor: page for competitor, page in previous.items() if page}
    signals = compare.compare(previous, {page["competitor"]: page for page in read})
    snapshot = save_snapshot(snapshots_dir, started_at, read)

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
    return result, snapshot, signals


def run_live(snapshots_dir=SNAPSHOTS, pages_dir=None, use_ai=True, started_at=None):
    """Return (result, snapshot path). result has the same shape as ./run's output."""
    started_at = started_at or now_utc()
    read, cost = collect(pages_dir, use_ai)
    result, snapshot, _ = compare_and_report(read, cost, snapshots_dir, started_at)
    return result, snapshot
