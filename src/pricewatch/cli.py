"""Command line.

    ./run --input cases.json --output result.json    the brief's test interface
    ./run --live --output result.json                one live run (fetch, read, compare, core)
"""

import argparse
import json
import sys

from .core import process
from .sources.file import read_cases


def main(argv=None):
    parser = argparse.ArgumentParser(prog="run", description="Turn competitor signals into Maya's items.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="cases.json")
    source.add_argument("--live", action="store_true", help="fetch the pricing pages and compare with the last snapshot")
    parser.add_argument("--output", required=True, help="where to write result.json")
    parser.add_argument("--db", help="live: DATABASE_URL or SQLite file for snapshots and the run log "
                        "(default: $DATABASE_URL, else data/pricewatch.db)")
    parser.add_argument("--pages", help="live: read pages saved by the fetcher from this directory instead of fetching")
    parser.add_argument("--no-ai", action="store_true", help="live: read pages with the plain reader even if a key is set")
    args = parser.parse_args(argv)

    error = None
    if args.live:
        from .live import run_live
        from .store import Store

        result = run_live(Store(args.db), args.pages, use_ai=not args.no_ai, trigger="command line")
    else:
        cases, error = read_cases(args.input)
        result = process(cases)
        if error:
            result["run"]["errors"].insert(0, error)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(
        f"{len(result['items'])} items, {len(result['skipped'])} skipped, "
        f"{len(result['run']['errors'])} errors, ${result['run']['cost_usd']:.4f} -> {args.output}"
    )
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
