"""Command line: ./run --input cases.json --output result.json"""

import argparse
import json
import sys

from .core import process
from .sources.file import read_cases


def main(argv=None):
    parser = argparse.ArgumentParser(prog="run", description="Turn competitor signals into Maya's items.")
    parser.add_argument("--input", required=True, help="cases.json")
    parser.add_argument("--output", required=True, help="where to write result.json")
    args = parser.parse_args(argv)

    cases, error = read_cases(args.input)
    result = process(cases)
    if error:
        result["run"]["errors"].insert(0, error)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(
        f"{len(result['items'])} items, {len(result['skipped'])} skipped, "
        f"{len(result['run']['errors'])} errors -> {args.output}"
    )
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
