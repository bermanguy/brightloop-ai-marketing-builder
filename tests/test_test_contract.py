"""The brief's test contract across its three doors: ./run, Test upload (POST /api/test) and MCP's run_test.

All three must give the same result.json for the same file, with the dashboard's interpretation flag on or
off, and the per-id rows that explain it must agree with result.json. Added in the final audit (D44).
"""

import copy
import glob
import json
import os
import subprocess
import sys

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from pricewatch import interpret, web  # noqa: E402
from pricewatch.store import Store  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
CASE_FILES = ["fixtures/sample-cases.json", *sorted(glob.glob("tests/cases/*.json", root_dir=ROOT))]
DISPLAY_FIELDS = ("category", "category_label", "interpretation", "display_headline", "display_steps", "latest_item_id")


def without_time(result):
    result = copy.deepcopy(result)
    result["run"].pop("started_at")
    return result


def cli(path, tmp_path):
    out = tmp_path / "result.json"
    done = subprocess.run([sys.executable, os.path.join(ROOT, "run"), "--input", os.path.join(ROOT, path), "--output", str(out)],
                          capture_output=True, text=True, env={"PATH": os.environ.get("PATH", "")})  # no keys at all
    assert done.returncode == 0, done.stderr
    return json.loads(out.read_text())


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "web.db"))
    monkeypatch.setattr(web, "_store", store)
    return TestClient(web.app), store


@pytest.mark.parametrize("flag", ["off", "on"])
@pytest.mark.parametrize("path", CASE_FILES)
def test_cli_test_upload_and_mcp_give_the_same_result(path, flag, client, tmp_path, monkeypatch):
    monkeypatch.setenv("PRICEWATCH_INTERPRET", flag)
    c, _ = client
    raw = open(os.path.join(ROOT, path), "rb").read()
    upload = c.post("/api/test", files={"cases": ("cases.json", raw)}).json()
    mcp = web.mcp_run_test(json.loads(raw))
    expected = without_time(cli(path, tmp_path))
    assert without_time(upload["result"]) == expected
    assert without_time(mcp["result"]) == expected and mcp["rows"] == upload["rows"]
    # The dashboard's display layer never reaches the test contract, flag or not.
    assert not any(key in item for item in upload["result"]["items"] for key in DISPLAY_FIELDS)


@pytest.mark.parametrize("path", CASE_FILES)
def test_rows_agree_with_result_json_one_row_per_accounted_id(path, client):
    c, _ = client
    answer = c.post("/api/test", files={"cases": ("cases.json", open(os.path.join(ROOT, path), "rb").read())}).json()
    result = answer["result"]
    items = {sid for item in result["items"] for sid in item["source_ids"]}
    skipped = {s["id"] for s in result["skipped"]}
    rows = {r["id"]: r for r in answer["rows"]}
    assert len(rows) == len(answer["rows"])  # one row per id
    assert set(rows) == items | skipped  # exactly the ids result.json accounts for
    for sid, row in rows.items():
        assert row["result"] == ("item" if sid in items else "skipped")
        assert row["why"], f"{sid} has no reason"


def test_a_numeric_id_is_an_item_row_and_an_empty_id_has_no_row(client):
    # Found in the final audit: 3-malformed-input.json's id 42 showed as "Skipped" with no reason, and the
    # entry with id "" showed as a skip carrying every error in the file. result.json was right both times.
    c, _ = client
    cases = {"signals": [
        {"id": 42, "type": "pricing", "competitor": "Lovable", "source": "lovable.dev/pricing", "text": "Pro is $25/month"},
        {"id": "", "type": "pricing", "text": "Pro is $25/month"},
        {"id": 7, "type": "ad", "text": "An ad"},
    ]}
    answer = c.post("/api/test", files={"cases": ("cases.json", json.dumps(cases).encode())}).json()
    assert [i["id"] for i in answer["result"]["items"]] == ["item-42"]
    assert [(r["id"], r["result"]) for r in answer["rows"]] == [("42", "item"), ("7", "skipped")]
    assert answer["rows"][0]["why"] == ["From Lovable's own pricing page, so confidence 0.9."]
    assert answer["result"]["run"]["errors"] == ["Signal #1 has no id, so it can't be accounted for."]


def test_test_upload_writes_nothing_and_sends_nothing_unless_an_alert_is_asked_for(client, monkeypatch):
    c, store = client
    sent = []
    monkeypatch.setattr(web.notify, "send", lambda *a, **k: sent.append(a) or [])
    for path in CASE_FILES:
        c.post("/api/test", files={"cases": ("cases.json", open(os.path.join(ROOT, path), "rb").read())})
    assert store.runs(100) == [] and store.snapshots(10) == [] and store.alerts() == [] and sent == []


@pytest.mark.parametrize("body", [b"", b"{\"signals\": [", b"[]", b"{}", b"\xff\xfe{"])
def test_unreadable_or_malformed_uploads_get_a_result_with_errors_not_a_crash(body, client):
    c, _ = client
    response = c.post("/api/test", files={"cases": ("cases.json", body)})
    assert response.status_code == 200
    answer = response.json()
    assert answer["result"]["items"] == [] and answer["result"]["skipped"] == [] and answer["rows"] == []
    assert answer["result"]["run"]["errors"]


# The live cards exactly as production holds them on 3 Nov: the replayed set plus the 18:46 check.

FIX = os.path.join(ROOT, "fixtures", "interpret")
PRODUCTION = [i for name in ("live-items-2026-11-03.json", "live-items-2026-11-03-late.json")
              for i in json.load(open(os.path.join(FIX, name), encoding="utf-8"))["items"]]


def test_on_the_production_cards_only_replayed_cards_carry_an_analysis_and_every_card_has_a_next_step():
    out = {i["id"]: i for i in interpret.annotate(PRODUCTION, interpret.load())}
    replayed = set(interpret.load())
    for item_id, item in out.items():
        if item_id not in replayed:
            # Never presented as analysed: no interpretation, so no status, question or impact on the card.
            assert item["interpretation"] is None
        if not item["interpretation"] and not item["display_steps"]:
            # Only the discount cards keep their own rule-written steps (already specific, with quoted figures).
            assert item["change"] == "discount", item_id
    # The six cards from the 18:46 check came after the replay: rule-written steps only.
    late = [i for i in out.values() if i["id"].endswith(("20261103184729", "20261103184717"))]
    assert len(late) == 6 and all(i["interpretation"] is None and i["display_steps"] for i in late)


def test_on_the_production_cards_older_cards_link_to_the_18_46_check_only_through_a_shared_line():
    latest = interpret.latest_of(PRODUCTION)
    # The asterisk cards quote "$25/month" and "$30/month", which the 18:46 check split into "$25" and "/month".
    assert latest["item-live-bolt-pro-details-20261102185917"] == "item-live-bolt-pro-details-20261103184717"
    assert latest["item-live-bolt-teams-details-20261102185917"] == "item-live-bolt-teams-details-20261103184717"
    # Replit's plan descriptions appeared on 28 Oct and were gone on 3 Nov.
    assert latest["item-live-replit-core-details-20261028214846"] == "item-live-replit-core-details-20261103184729"
    assert latest["item-live-replit-pro-details-20261028214846"] == "item-live-replit-pro-details-20261103184729"
    # Bolt's Free and Enterprise cards share no line with an older card; the newest cards link nowhere.
    assert not any(k.endswith(("20261103184729", "20261103184717")) for k in latest)
