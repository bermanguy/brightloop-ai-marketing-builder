"""Comparing runs: snapshots of the real saved pages, with planted changes. No keys, no network."""

import json

from pricewatch.live import run_live
from pricewatch.store import Store
from pricewatch.sources import compare, extract
from test_extract import PAGES, saved


def reading(competitor, at="2026-10-25T06:00:00Z", reader="plain", changes=()):
    """A plain reading of a saved page, optionally after editing its text: [(old, new)]."""
    page = saved(competitor)
    for old, new in changes:
        assert old in page["text"]
        page["text"] = page["text"].replace(old, new, 1)
    page = extract.read_page(page)
    page.update(fetched_at=at, reader=reader, ai_error=None, cost_usd=0.0)
    return page


def plan(page, name):
    return next(p for p in page["plans"] if p["name"] == name)


def test_the_same_page_twice_is_no_change():
    for competitor in ("lovable", "bolt", "replit", "v0"):
        assert compare.compare_page(reading(competitor), reading(competitor, "2026-10-25T12:00:00Z")) == []


def test_a_price_change_is_one_signal_quoting_before_and_after():
    before, after = reading("lovable"), reading("lovable", "2026-10-25T12:00:00Z", changes=[("$25", "$30")])
    [signal] = compare.compare_page(before, after)
    assert signal["type"] == "pricing" and signal["source"] == "https://lovable.dev/pricing"
    assert signal["ts"] == "2026-10-25T12:00:00Z"
    assert "now shows $30 / month" in signal["text"] and "showed $25 / month" in signal["text"]
    assert signal["id"] == "live-lovable-pro-price-20261025120000"


def test_a_change_in_what_a_plan_includes_counts_even_at_the_same_price():
    # R2: "what a plan contains even if its price stays the same"
    before = reading("bolt")
    after = reading("bolt", "2026-10-25T12:00:00Z", changes=[("10M tokens/month", "15M tokens/month")])
    [signal] = compare.compare_page(before, after)
    assert signal["id"].startswith("live-bolt-pro-details-")
    assert '"15M tokens/month, rollover included"' in signal["text"]
    assert '"10M tokens/month, rollover included"' in signal["text"]


def test_the_same_lines_filed_under_other_fields_are_no_change():
    # Seen in two real AI readings a minute apart of Lovable's unchanged page.
    before, after = reading("lovable"), reading("lovable", "2026-10-25T12:00:00Z")
    enterprise = plan(after, "Enterprise")
    enterprise["billing"], enterprise["includes"] = "Volume based pricing", enterprise["includes"][1:]
    assert compare.compare_page(before, after) == []


def test_a_billing_change_at_the_same_price_is_a_details_change():
    before = reading("replit")
    after = reading("replit", "2026-10-25T12:00:00Z", changes=[("$18 / month, billed annually", "$18 / month, billed monthly")])
    [signal] = compare.compare_page(before, after)
    assert "live-replit-core-details-" in signal["id"]
    assert "billed monthly" in signal["text"] and "billed annually" in signal["text"]


def test_plans_that_appear_or_disappear():
    before, after = reading("v0"), reading("v0", "2026-10-25T12:00:00Z")
    after["plans"] = [p for p in after["plans"] if p["name"] != "Business"]
    after["plans"].append(dict(plan(before, "Plus"), name="Max", price="$200"))
    kinds = sorted(s["id"].split("-")[2:4] for s in compare.compare_page(before, after))
    assert kinds == [["business", "removed"], ["max", "added"]]


def test_a_failed_page_is_never_read_as_every_plan_removed():
    before = reading("replit")
    after = dict(reading("replit"), ok=False, error="HTTP 403", plans=[])
    assert compare.compare({"Replit": before}, {"Replit": after}) == []


# The whole live run, from saved pages, through the core.

def write_pages(directory, at, changes=None, failed=()):
    """Copy the saved pages into directory as fetched at `at`, editing page text: {competitor: [(old, new)]}."""
    directory.mkdir(parents=True, exist_ok=True)
    for path in PAGES.glob("*.json"):
        page = json.loads(path.read_text())
        page["fetched_at"] = at
        if path.stem in failed:
            page.update(ok=False, status=403, error="HTTP 403", text="")
        for old, new in (changes or {}).get(path.stem, []):
            assert old in page["text"]
            page["text"] = page["text"].replace(old, new, 1)
        (directory / path.name).write_text(json.dumps(page))
    return directory


def live(tmp_path, name, at, changes=None, failed=()):
    pages = write_pages(tmp_path / name, at, changes, failed)
    return run_live(Store(str(tmp_path / "db.sqlite")), pages, use_ai=False, started_at=at)


def test_first_run_saves_a_snapshot_and_reports_nothing_changed(tmp_path):
    result = live(tmp_path, "run1", "2026-10-25T06:00:00Z")
    assert result["items"] == [] and result["run"]["errors"] == []
    assert len(result["run"]["notes"]) == 4
    assert [p["plans"] for p in result["run"]["pages"]] == [4, 4, 3, 4]
    store = Store(str(tmp_path / "db.sqlite"))
    assert [s["taken_at"] for s in store.snapshots()] == ["2026-10-25T06:00:00Z"]
    assert store.runs()[0] == result


def test_a_planted_price_change_becomes_one_high_confidence_item(tmp_path):
    live(tmp_path, "run1", "2026-10-25T06:00:00Z")
    result = live(tmp_path, "run2", "2026-10-25T12:00:00Z", {"lovable": [("$25", "$30")]})
    [item] = result["items"]
    assert item["competitor"] == "Lovable" and item["confidence"] == 0.9 and item["unverified"] is False
    assert item["sources"][0]["url"] == "https://lovable.dev/pricing"
    assert "$30" in item["sources"][0]["quote"] and "$25" in item["sources"][0]["quote"]
    assert result["skipped"] == [] and result["run"]["errors"] == [] and result["run"]["notes"] == []


def test_a_page_that_fails_is_reported_then_compared_again_when_back(tmp_path):
    live(tmp_path, "run1", "2026-10-25T06:00:00Z")
    failed = live(tmp_path, "run2", "2026-10-25T12:00:00Z", failed=["bolt"])
    assert failed["items"] == []
    assert any(error.startswith("Bolt: couldn't read") for error in failed["run"]["errors"])
    # Back, with a change since the last good reading (run 1).
    back = live(tmp_path, "run3", "2026-10-25T18:00:00Z", {"bolt": [("$18", "$20")]})
    assert [item["competitor"] for item in back["items"]] == ["Bolt"]
    assert "since 2026-10-25T06:00:00Z" in back["items"][0]["why"]


def test_readings_by_different_readers_are_not_compared(tmp_path):
    pages = [dict(reading(c), reader="ai") for c in ("lovable", "bolt", "replit", "v0")]
    Store(str(tmp_path / "db.sqlite")).save_snapshot("2026-10-25T06:00:00Z", pages)
    result = live(tmp_path, "run2", "2026-10-25T12:00:00Z", {"lovable": [("$25", "$30")]})
    assert result["items"] == []
    assert len(result["run"]["notes"]) == 4


def test_every_signal_is_accounted_for_once(tmp_path):
    live(tmp_path, "run1", "2026-10-25T06:00:00Z")
    result = live(tmp_path, "run2", "2026-10-25T12:00:00Z",
                  {"lovable": [("$25", "$30")], "v0": [("$100", "$120")], "replit": [("$18", "$16")]})
    ids = [sid for item in result["items"] for sid in item["source_ids"]] + [s["id"] for s in result["skipped"]]
    assert len(ids) == len(set(ids)) == 3
