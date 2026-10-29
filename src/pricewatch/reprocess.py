"""Rebuild one logged run's cards from its saved snapshot, with the current comparison rules.

    python -m pricewatch.reprocess 2026-10-29T03:45:25Z            dry run: show old and new headlines
    python -m pricewatch.reprocess 2026-10-29T03:45:25Z --apply    print the old run as a backup, then save

For a card worded by an older rule (Lovable's crossed-out yearly prices, 2026-10-29,
first shown as "changed what it includes"). Nothing is fetched or read again: the
run's saved snapshot is compared with the last good reading before it, exactly as
the run did, and the core writes the cards. Only runs whose cards all came from the
pricing pages are rebuilt, since rumors found on the day aren't saved, and a rebuild
may drop cards but never add one.
"""

import argparse
import json
import sys

from .core import process
from .sources import compare, fetch
from .store import Store


def rebuild(store, started_at):
    """(old result, new result) for the run that started at `started_at`. Raises ValueError if it can't be rebuilt."""
    old = next((run for run in store.runs() if run["run"]["started_at"] == started_at), None)
    if not old:
        raise ValueError(f"No run started at {started_at}.")
    if old["skipped"] or any(not source.startswith("live-") for item in old["items"] for source in item["source_ids"]):
        raise ValueError("This run has rumors or skipped signals, which aren't saved, so it can't be rebuilt.")
    snapshots = store.snapshots()
    now = next((s for s in snapshots if s["taken_at"] == started_at), None)
    if not now:
        raise ValueError(f"No snapshot taken at {started_at}.")
    good = {}
    for snapshot in snapshots:  # newest first: the last good reading of each page before this run
        if snapshot["taken_at"] < started_at:
            for page in snapshot["pages"]:
                if page.get("ok"):
                    good.setdefault((page["competitor"], page.get("view"), page["reader"]), page)
    read = now["pages"]
    previous = {fetch.label(p): good.get((p["competitor"], p.get("view"), p["reader"])) for p in read}
    signals = compare.compare({k: v for k, v in previous.items() if v}, {fetch.label(p): p for p in read})
    new = process({"signals": signals, "timezone": "UTC"}, started_at=started_at, cost_usd=old["run"]["cost_usd"])
    # Fewer cards is a rule no longer seeing a change (a reader's variance, 2026-10-29); more would be a change
    # never alerted on, so that's refused.
    if len(new["items"]) > len(old["items"]) or new["skipped"]:
        raise ValueError(f"Rebuilding gives {len(new['items'])} cards, more than {len(old['items'])}; nothing changed.")
    return old, dict(old, items=new["items"])


def main(argv=None):
    parser = argparse.ArgumentParser(prog="reprocess", description=__doc__.splitlines()[0])
    parser.add_argument("started_at", help="the run's start time, as on the run log, e.g. 2026-10-29T03:45:25Z")
    parser.add_argument("--apply", action="store_true", help="save the rebuilt cards (default: dry run)")
    parser.add_argument("--db", help="DATABASE_URL or SQLite file (default: $DATABASE_URL, else data/pricewatch.db)")
    args = parser.parse_args(argv)
    store = Store(args.db)
    try:
        old, new = rebuild(store, args.started_at)
    except ValueError as exc:
        print(exc)
        return 1
    for label, result in (("Before", old), ("After", new)):
        print(f"{label}:")
        for item in result["items"]:
            print(f"  {item['id']}: {item['headline']}")
    if old["items"] == new["items"]:
        print("No change.")
        return 0
    if not args.apply:
        print("Dry run: nothing saved. Add --apply to save.")
        return 0
    print("Backup of the run as it was:")
    print(json.dumps(old, ensure_ascii=False))
    store.replace_run(args.started_at, new)
    print("Saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
