"""Rebuilding a logged run's cards from its saved snapshot (reprocess.py). SQLite, no keys."""

import copy

from pricewatch import reprocess
from pricewatch.live import compare_and_report
from pricewatch.store import Store
from test_compare import RECORDED, plan


def pages(at, struck=False):
    read = copy.deepcopy(RECORDED["pages"])
    for page in read:
        page["fetched_at"] = at
        if struck and page["competitor"] == "Lovable" and page.get("view") == "Yearly":
            plan(page, "Pro")["quotes"][1:1] = ["~~$25~~", "Originally $25 per month"]
    return read


def two_runs(tmp_path):
    store = Store(str(tmp_path / "db.sqlite"))
    compare_and_report(pages("2026-10-28T21:48:14Z"), 0.0, store, "2026-10-28T21:48:14Z")
    compare_and_report(pages("2026-10-29T03:45:25Z", struck=True), 0.0, store, "2026-10-29T03:45:25Z")
    return store


def test_a_card_worded_by_an_older_rule_is_rebuilt_and_saved(tmp_path, capsys):
    store = two_runs(tmp_path)
    run = store.runs()[0]
    [item] = run["items"]
    assert "as a discount" in item["headline"]
    stale = dict(item, id="item-old", headline="Lovable changed what its Pro plan (Yearly view) includes, at the same price.")
    store.replace_run("2026-10-29T03:45:25Z", dict(run, items=[stale]))

    assert reprocess.main(["2026-10-29T03:45:25Z", "--db", str(tmp_path / "db.sqlite")]) == 0
    assert "Dry run" in capsys.readouterr().out
    assert store.runs()[0]["items"] == [stale]

    assert reprocess.main(["2026-10-29T03:45:25Z", "--db", str(tmp_path / "db.sqlite"), "--apply"]) == 0
    out = capsys.readouterr().out
    assert "Backup of the run as it was" in out and "item-old" in out and "Saved." in out
    assert store.runs()[0]["items"] == [item]
    assert store.runs()[1]["run"]["started_at"] == "2026-10-28T21:48:14Z"  # the other run is untouched


def test_an_up_to_date_run_is_left_alone(tmp_path, capsys):
    store = two_runs(tmp_path)
    before = store.runs()
    assert reprocess.main(["2026-10-29T03:45:25Z", "--db", str(tmp_path / "db.sqlite"), "--apply"]) == 0
    assert "No change." in capsys.readouterr().out
    assert store.runs() == before


def test_an_unknown_run_is_an_error(tmp_path):
    store = two_runs(tmp_path)
    assert reprocess.main(["2026-01-01T00:00:00Z", "--db", str(tmp_path / "db.sqlite")]) == 1
    assert len(store.runs()) == 2


def test_a_card_the_rules_no_longer_see_is_dropped(tmp_path, capsys):
    store = two_runs(tmp_path)
    run = store.runs()[1]  # 21:48, the first run: nothing to compare, no cards
    fake = {"id": "item-live-spurious", "source_ids": ["live-spurious"], "headline": "A change that wasn't."}
    store.replace_run("2026-10-28T21:48:14Z", dict(run, items=[fake]))
    assert reprocess.main(["2026-10-28T21:48:14Z", "--db", str(tmp_path / "db.sqlite"), "--apply"]) == 0
    assert "Saved." in capsys.readouterr().out
    assert store.runs()[1]["items"] == []
