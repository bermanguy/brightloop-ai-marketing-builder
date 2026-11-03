"""The interpretation step behind its flag: off, every endpoint is exactly as before; on, cards gain three fields."""

import copy
import json
import os

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from pricewatch import interpret, web  # noqa: E402
from pricewatch.live import run_live  # noqa: E402
from pricewatch.store import Store  # noqa: E402
from test_compare import write_pages  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "interpret")
with open(os.path.join(FIX, "live-items-2026-11-03.json"), encoding="utf-8") as f:
    # The replay input keeps only what the replay reads; a stored card also has its action and why.
    LIVE = [dict(i, action="Stored action.", steps=["Stored action."], why="Stored why.") for i in json.load(f)["items"]]
ADDED = ("category", "category_label", "interpretation", "display_headline", "display_steps", "latest_item_id")


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A store holding today's live cards as one logged run, plus one real keyless live run."""
    store = Store(str(tmp_path / "web.db"))
    store.save_run({"built_for": "maya", "items": copy.deepcopy(LIVE), "skipped": [],
                    "run": {"started_at": "2026-11-03T06:52:34Z", "cost_usd": 0.0, "errors": [], "pages": []}})
    run_live(store, write_pages(tmp_path / "r1", "2026-10-25T06:00:00Z"), use_ai=False, started_at="2026-10-25T06:00:00Z")
    monkeypatch.setattr(web, "_store", store)
    monkeypatch.delenv("PRICEWATCH_INTERPRET", raising=False)
    return TestClient(web.app), store


def get_all(c):
    return {
        "changes": c.get("/api/changes?days=all").json(),
        "focused": c.get("/api/changes?days=all&focus=plan contents").json(),
        "runs": c.get("/api/runs").json(),
        "pricing": c.get("/api/pricing").json(),
        "page": c.get("/?days=all").text,
        "mcp": c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                    "params": {"name": "get_changes", "arguments": {"days": "all", "limit": 100}}}).json(),
    }


def test_flag_off_every_endpoint_is_exactly_as_stored(client, monkeypatch):
    c, store = client
    unset = get_all(c)
    monkeypatch.setenv("PRICEWATCH_INTERPRET", "off")
    assert get_all(c) == unset
    stored = sorted(LIVE, key=lambda i: i["seen_at"], reverse=True)
    assert unset["changes"]["items"] == stored  # byte for byte what the run document holds
    assert not any(key in item for item in unset["changes"]["items"] for key in ADDED)


def test_flag_on_only_adds_three_fields_and_never_writes(client, monkeypatch):
    c, store = client
    off = get_all(c)
    runs_before = json.dumps(store.runs())
    monkeypatch.setenv("PRICEWATCH_INTERPRET", "on")
    on = get_all(c)
    assert on["pricing"] == off["pricing"]
    # The run log and the admin page show the dashboard's headline and next steps (D45); nothing else changes.
    strip = lambda runs: [dict(r, details=dict(r["details"], decided=[{k: v for k, v in d.items() if k not in ("headline", "next_step")}
                                                                    for d in r["details"]["decided"]])) for r in runs]  # noqa: E731
    assert strip(on["runs"]) == strip(off["runs"])
    assert on["changes"]["summary"] == off["changes"]["summary"]
    for before, after in zip(off["changes"]["items"], on["changes"]["items"]):
        assert {k: v for k, v in after.items() if k not in ADDED} == before
    assert [i["id"] for i in on["focused"]["items"]] == [i["id"] for i in off["focused"]["items"]]
    assert json.dumps(store.runs()) == runs_before  # run documents untouched

    by_id = {i["id"]: i for i in on["changes"]["items"]}
    bolt = by_id["item-live-bolt-pro-details-20261102185917"]["interpretation"]
    assert bolt["interpretation_status"] == "ambiguous" and bolt["actions"][0]["id"] == "check_removed_mark"
    lovable = by_id["item-live-lovable-yearly-free-details-20261103005623"]["interpretation"]
    assert lovable["observation"]["text"].startswith("Across recent checks") and lovable["interpretation_status"] == "ambiguous"
    assert [a["id"] for a in lovable["actions"]] == ["check_signup_flow", "messaging_investigation"]
    old_card = by_id["item-live-replit-pro-details-20261027051056"]  # stored before kinds of change: not sent
    assert old_card["interpretation"] is None and old_card["category"] == "other"
    discount = by_id["item-live-lovable-yearly-pro-discount-20261029034525"]
    assert discount["interpretation"] is None and discount["category"] == "pricing"  # rule category, not sent
    replayed = {i["id"] for i in LIVE}
    others = [i for i in on["changes"]["items"] if i["id"] not in replayed]
    assert all(i["interpretation"] is None for i in others)  # a card the replay never saw: shown as before

    mcp_items = json.loads(on["mcp"]["result"]["content"][0]["text"])["items"]
    assert mcp_items == on["changes"]["items"]


def test_a_live_run_with_the_flag_on_is_unchanged_and_calls_no_model(tmp_path, monkeypatch):
    monkeypatch.setenv("PRICEWATCH_INTERPRET", "on")
    called = []
    monkeypatch.setattr(interpret, "ask", lambda *a, **k: called.append(a))
    store = Store(str(tmp_path / "live.db"))
    run_live(store, write_pages(tmp_path / "a", "2026-10-25T06:00:00Z"), use_ai=False, started_at="2026-10-25T06:00:00Z")
    pages = write_pages(tmp_path / "b", "2026-10-25T12:00:00Z", {"lovable": [("$25", "$30")]})
    result = run_live(store, pages, use_ai=False, started_at="2026-10-25T12:00:00Z")
    assert called == [] and result["items"] and not any(key in i for i in result["items"] for key in ADDED)
    assert store.runs()[0]["items"] == result["items"]


def test_a_missing_or_broken_replay_file_means_no_interpretations(tmp_path, monkeypatch):
    monkeypatch.setenv("PRICEWATCH_INTERPRET_FILE", str(tmp_path / "missing.json"))
    assert interpret.load() == {}
    (tmp_path / "bad.json").write_text("{not json")
    monkeypatch.setenv("PRICEWATCH_INTERPRET_FILE", str(tmp_path / "bad.json"))
    assert interpret.load() == {}


# D45: the run log, alerts and admin pages show the same headline and next steps as the Changes tab.

def test_run_log_alerts_and_admin_page_use_the_dashboards_next_steps(client, monkeypatch):
    from pricewatch import notify
    c, store = client
    monkeypatch.setenv("PRICEWATCH_INTERPRET", "on")
    shown = {i["id"]: i for i in c.get("/api/changes?days=all").json()["items"]}
    decided = c.get("/api/runs").json()[-1]["details"]["decided"]
    stored = sorted(LIVE, key=lambda i: i["seen_at"], reverse=True)
    for item, row in zip(stored, decided):
        card = shown[item["id"]]
        assert row["next_step"] == interpret.next_steps(card)[0] and row["headline"] == interpret.shown_headline(card)
    bolt = shown["item-live-bolt-pro-details-20261102185917"]
    assert interpret.next_steps(bolt) == [a["text"] for a in bolt["interpretation"]["actions"]]
    page = c.get("/?days=all").text
    assert "Bolt removed an asterisk from the Pro plan&#x27;s displayed price." in page
    keeps_its_own = [i for i in shown.values() if i["id"] in {x["id"] for x in LIVE} and not i["interpretation"] and not i["display_steps"]]
    assert {i["change"] for i in keeps_its_own} == {"discount"}  # only discount cards keep their stored steps
    assert page.count("<li>Stored action.</li>") == len(keeps_its_own)
    annotated = interpret.for_display(LIVE)
    slack, email = notify.slack_text(annotated, False), notify.email_html(annotated, False)
    assert slack.count("Stored action.") == len(keeps_its_own)
    assert 'the "*" next to Bolt\'s Pro price' in slack and "Bolt removed an asterisk" in email


def test_with_the_flag_off_the_run_log_alerts_and_admin_page_keep_the_stored_text(client, monkeypatch):
    from pricewatch import notify
    c, _ = client
    monkeypatch.setenv("PRICEWATCH_INTERPRET", "off")
    decided = c.get("/api/runs").json()[-1]["details"]["decided"]
    assert all(row["next_step"] == "Stored action." for row in decided)
    assert interpret.for_display(LIVE) is LIVE
    assert notify.slack_text(LIVE, False).count("Stored action.") == len(LIVE)


def test_a_live_runs_alert_carries_the_dashboards_steps_and_the_run_is_saved_unchanged(client, monkeypatch):
    from pricewatch import notify
    c, store = client
    monkeypatch.setenv("PRICEWATCH_INTERPRET", "on")
    sent = []
    monkeypatch.setattr(notify, "settings", lambda saved=None: {"min_confidence": 0.6, "competitors": [], "email": False,
                                                               "slack": True, "email_on": False, "slack_on": True,
                                                               "on_schedule": True, "on_check_now": True, "slack_channel": "C1"})
    monkeypatch.setattr(notify, "send", lambda items, channels, **k: sent.append(items) or ["sent"])
    result = {"items": copy.deepcopy(LIVE), "run": {"started_at": "x"}}
    before = json.dumps(result)
    web.alert(result, "schedule")
    assert json.dumps(result) == before  # the run's own cards are untouched
    by_id = {i["id"]: i for i in sent[0]}
    replit = by_id["item-live-replit-core-details-20261028214846"]
    assert interpret.next_steps(replit)[0].startswith("Check Replit's other plans")
