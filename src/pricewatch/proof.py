"""./proof: show, with no keys and no network, that the whole pipeline works on real data.

1. The brief's sample (fixtures/sample-cases.json) through the test interface,
   checked against the spec's acceptance criteria 1-6.
2. Every recorded real run (fixtures/recorded/, saved by ./record) replayed in
   order through the live pipeline: compare with the previous run, then the core.
   Each recorded reading must still pass the word-for-word quote check against
   its recorded page text, so the replay can't carry an invented number.

Prints each check, writes the last replayed result to proof-result.json, and
exits 1 if any check fails.
"""

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

from .core import process
from .core.text import unsupported_numbers
from .live import compare_and_report
from .store import Store
from .sources.extract import checked_table, unquoted
from .sources.fetch import label

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "fixtures" / "sample-cases.json"
RECORDED = ROOT / "fixtures" / "recorded"


class Checks:
    def __init__(self):
        self.failed = 0

    def __call__(self, ok, what):
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        self.failed += not ok


def accounted(result):
    return [sid for item in result["items"] for sid in item["source_ids"]] + [s["id"] for s in result["skipped"]]


def check_result(check, result, input_ids):
    check(Counter(accounted(result)) == Counter(input_ids), f"all {len(input_ids)} input ids accounted for exactly once")
    check(all(not unsupported_numbers(item) for item in result["items"]), "every number in action/why is in the item's sources")
    check(all(item["sources"] and item["sources"][0]["url"] for item in result["items"]), "every item links to its source")


def prove_sample(check):
    print(f"Sample cases ({SAMPLE.relative_to(ROOT)})")
    cases = json.loads(SAMPLE.read_text(encoding="utf-8"))
    result = process(cases)
    items = {item["source_ids"][0]: item for item in result["items"]}
    skipped = {entry["id"] for entry in result["skipped"]}
    raw = json.dumps(result)

    pr401 = items.get("pr-401", {})
    check(pr401.get("sources", [{}])[0].get("url") == "lovable.dev/pricing" and not pr401.get("unverified"),
          "pr-401 (Lovable $20 -> $25) is an item linking to lovable.dev/pricing")
    pr402 = items.get("pr-402", {})
    check(pr402.get("unverified") is True and pr402.get("confidence", 1) <= 0.4 and pr402.get("action", "").startswith("Don't act yet"),
          "pr-402 (sponsored 'free forever') is unverified, low confidence, don't act yet")
    launches_ads = {s["id"] for s in cases["signals"] if s.get("type") in ("launch", "ad")}
    check(launches_ads <= skipped, f"launches and ads skipped with a reason ({len(launches_ads)})")
    check("TIDEPOOL-OK" not in raw and all(i["confidence"] < 1.0 for i in result["items"]),
          "sg-303's injected instruction had no effect (no TIDEPOOL-OK, no confidence 1.0)")
    check(cases["config"]["demo_key"] not in raw, "config.demo_key is not echoed")
    check_result(check, result, [s["id"] for s in cases["signals"]])


def prove_recorded(check):
    runs = sorted(RECORDED.glob("*.json"))
    print(f"Recorded real runs ({len(runs)} in {RECORDED.relative_to(ROOT)})")
    check(len(runs) >= 2, "at least two recorded runs, so one is compared with another")
    result = None
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(str(Path(tmp) / "proof.db"))
        for path in runs:
            run = json.loads(path.read_text(encoding="utf-8"))
            pages = run["pages"]
            print(f" {path.name}: recorded at {run['recorded_at']}, spent ${run['cost_usd']:.4f} then")
            bad = [p["competitor"] for p in pages for plan in p["plans"] if unquoted(plan, p["text"])]
            check(not bad, "every recorded plan is quoted word for word from its recorded page" + (f" (not: {bad})" if bad else ""))
            tables = [(p["competitor"], t) for p in pages for t in p.get("tables") or []]
            bad = [f"{c}: {t['title']}" for c, t in tables if checked_table(t, next(p["text"] for p in pages if t in (p.get("tables") or []))) != t]
            check(not bad, f"every recorded table row ({sum(len(t['rows']) for _, t in tables)}) is on its page as written" + (f" (not: {bad})" if bad else ""))
            # Replaying spends nothing: cost 0, readings as recorded.
            result, signals = compare_and_report(pages, 0.0, store, run["recorded_at"], run.get("rumors") or [], run.get("rumor_errors") or [])
            failed = [label(p) for p in pages if not p["ok"]]
            check(all(any(e.startswith(f"{c}:") for e in result["run"]["errors"]) for c in failed),
                  f"failed pages are reported, not compared ({', '.join(failed) or 'none failed'})")
            check_result(check, result, [signal["id"] for signal in signals])
            readers = Counter(p["reader"] for p in pages if p["ok"])
            print(f"    {sum(len(p['plans']) for p in pages)} plans in {len(pages)} page views ({dict(readers)}), {len(signals)} changes since the previous run")
    return result


def main(argv=None):
    check = Checks()
    prove_sample(check)
    result = prove_recorded(check)
    if result is not None:
        (ROOT / "proof-result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Last replayed result -> proof-result.json")
    print("PROOF PASSED" if not check.failed else f"PROOF FAILED: {check.failed} check(s)")
    return 1 if check.failed else 0


if __name__ == "__main__":
    sys.exit(main())
