"""./record: do one real run (fetch + read, with the AI if a key is set) and save it for keyless replay.

Saves fixtures/recorded/<time>.json: each page's visible text and the plans read
from it, plus what the reading cost. ./proof replays these files with no keys and
no network, so a fresh clone sees real pages and real AI readings.

Nothing credential-like is saved: pages hold only public page text and readings.
"""

import argparse
import json
import sys
from pathlib import Path

from .live import collect, now_utc
from .sources.fetch import label

RECORDED = Path("fixtures") / "recorded"
KEEP = ("competitor", "view", "view_index", "opens_on", "url", "method", "fetched_at", "ok", "status", "error", "reader",
        "ai_error", "cost_usd", "plans", "tables", "text", "dropdowns")


def record(out_dir=RECORDED, pages_dir=None, use_ai=True):
    recorded_at = now_utc()
    read, cost = collect(pages_dir, use_ai)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{recorded_at.replace(':', '')}.json"
    run = {"recorded_at": recorded_at, "cost_usd": cost, "pages": [{key: page.get(key) for key in KEEP} for page in read]}
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path, run


def main(argv=None):
    parser = argparse.ArgumentParser(prog="record", description="Save one real run for keyless replay by ./proof.")
    parser.add_argument("--out", default=str(RECORDED), help="where to save (default: fixtures/recorded)")
    args = parser.parse_args(argv)
    path, run = record(args.out)
    for page in run["pages"]:
        state = f"{page['reader']}, {len(page['plans'])} plans" if page["ok"] else f"FAILED: {page['error']}"
        print(f"{label(page):18} {state}")
    print(f"${run['cost_usd']:.4f} -> {path}")
    return 0 if all(page["ok"] for page in run["pages"]) else 1


if __name__ == "__main__":
    sys.exit(main())
