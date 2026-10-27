"""The web app, on a SQLite store filled from the saved pages. No keys, no network."""

import json
import re

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from pricewatch import web  # noqa: E402
from pricewatch.live import run_live  # noqa: E402
from pricewatch.store import Store  # noqa: E402
from test_compare import write_pages  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "web.db"))
    run_live(store, write_pages(tmp_path / "r1", "2026-10-25T06:00:00Z"), use_ai=False, started_at="2026-10-25T06:00:00Z")
    pages = write_pages(tmp_path / "r2", "2026-10-25T12:00:00Z", {"lovable": [("$25", "$30")]}, failed=["replit"])
    run_live(store, pages, use_ai=False, started_at="2026-10-25T12:00:00Z")
    monkeypatch.setattr(web, "_store", store)
    monkeypatch.setenv("RUN_TOKEN", "test-token")
    return TestClient(web.app)


def test_changes_page_shows_the_item_with_its_source(client):
    body = client.get("/").text
    assert "Lovable" in body and "$30" in body and "$25" in body
    assert '<a href="https://lovable.dev/pricing">' in body
    assert "couldn't read: Replit" in body


def test_pricing_page_shows_latest_plans_and_never_old_data_for_a_failed_page(client):
    body = client.get("/pricing").text
    assert "$30" in body and "<s>$90</s>" in body  # v0 Plus list price, struck
    replit = body.split("<h2>Replit</h2>")[1].split("<h2>")[0]
    assert "Couldn't read this page" in replit
    assert "$18" not in replit  # Replit's older $18 isn't shown as current


def test_run_log_lists_runs_with_cost_and_errors(client):
    body = client.get("/runs").text
    assert "2026-10-25T12:00:00Z" in body and "Replit FAILED" in body and "$0.0000" in body


def test_run_needs_the_token(client, monkeypatch):
    assert client.post("/run").status_code == 403
    assert client.post("/run", headers={"Authorization": "Bearer wrong"}).status_code == 403
    monkeypatch.delenv("RUN_TOKEN")
    assert client.post("/run", headers={"Authorization": "Bearer test-token"}).status_code == 403


def test_run_with_the_token_starts_a_live_run(client, monkeypatch):
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store: calls.append(store) or store.runs(1)[0])
    response = client.post("/run", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200 and response.json()["items"] == 1 and len(calls) == 1
    form = client.post("/run", data={"token": "test-token"}, follow_redirects=False)
    assert form.status_code == 303 and len(calls) == 2


def test_test_upload_returns_the_same_result_as_run(client):
    sample = open("fixtures/sample-cases.json", "rb").read()
    response = client.post("/test?format=json", files={"cases": ("cases.json", sample)})
    result = response.json()
    assert len(result["items"]) == 2 and len(result["skipped"]) == 6
    assert "bl_demo_4c19e2" not in response.text


def test_test_upload_matches_the_run_command_byte_for_byte(client, tmp_path):
    from pricewatch import cli

    for cases in ("fixtures/sample-cases.json", "tests/cases/tricky-cases.json"):
        out = tmp_path / "result.json"
        cli.main(["--input", cases, "--output", str(out)])
        response = client.post("/test?format=json", files={"cases": ("cases.json", open(cases, "rb").read())})
        # Same bytes once the start time is set aside: the two runs can straddle a second.
        same_time = lambda text: re.sub(r'"started_at": "[^"]*"', '"started_at": ""', text)
        assert same_time(response.text) == same_time(out.read_text(encoding="utf-8"))


def test_page_text_is_escaped(client):
    assert "<script>" not in web.esc("<script>alert(1)</script>")
    assert web.link("javascript:alert(1)") == "javascript:alert(1)"


def test_a_second_run_while_one_is_going_is_refused(client):
    assert web._running.acquire(blocking=False)
    try:
        response = client.post("/run", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 409
    finally:
        web._running.release()


def test_a_run_that_crashes_does_not_block_the_next_one(client, monkeypatch):
    def crash(store):
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(web, "run_live", crash)
    crashing = TestClient(web.app, raise_server_exceptions=False)
    assert crashing.post("/run", headers={"Authorization": "Bearer test-token"}).status_code == 500
    monkeypatch.setattr(web, "run_live", lambda store: store.runs(1)[0])
    assert client.post("/run", headers={"Authorization": "Bearer test-token"}).status_code == 200


def test_the_schedule_keeps_the_six_hour_pace(client, monkeypatch):
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store: calls.append(store) or store.runs(1)[0])
    auth = {"Authorization": "Bearer test-token"}
    # The fixture's last run is from 2026-10-25, long enough ago: this call runs.
    assert "items" in client.post("/run?unless_ran_within_hours=5.5", headers=auth).json() and len(calls) == 1
    now = web.datetime.now(web.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    web.store().save_run({"items": [], "skipped": [], "run": {"started_at": now, "errors": [], "cost_usd": 0.0}})
    assert client.post("/run?unless_ran_within_hours=5.5", headers=auth).json() == {"skipped": f"last run started at {now}"}
    assert len(calls) == 1
    # Check now always runs.
    assert client.post("/run", headers=auth).status_code == 200 and len(calls) == 2


def test_pricing_page_shows_every_view_its_dropdown_options_and_tables(tmp_path, monkeypatch):
    from test_compare import views
    from pricewatch.live import compare_and_report

    store = Store(str(tmp_path / "views.db"))
    compare_and_report(list(views().values()), 0.0, store, "2026-10-26T20:28:29Z")
    monkeypatch.setattr(web, "_store", store)
    body = TestClient(web.app).get("/pricing").text
    for name in ("Bolt (Monthly)", "Bolt (Yearly)", "Lovable (Monthly)", "Lovable (Yearly)", "Replit", "v0"):
        assert f"<h2>{name}</h2>" in body
    assert "11 options in the page's dropdown" in body and "10,000 credits Save 11% $1875/mo" in body
    assert "Bolt: Pro plan comparison" in body and "Daily Token Limit" in body and "v0: Model pricing" in body


def test_the_json_api_gives_the_same_data_as_the_pages(client):
    changes = client.get("/api/changes", headers={"Origin": "https://example.base44.app"})
    assert changes.headers["access-control-allow-origin"] == "*"
    data = changes.json()
    assert data["last_check"] == "2026-10-25T12:00:00Z" and data["failed_pages"] == ["Replit"]
    assert len(data["items"]) == 1 and data["items"][0]["sources"][0]["url"] == "https://lovable.dev/pricing"

    pricing = client.get("/api/pricing").json()
    replit = next(p for p in pricing["pages"] if p["competitor"] == "Replit")
    assert replit["ok"] is False and replit["plans"] == [] and "html" not in replit and "text" not in replit
    lovable = next(p for p in pricing["pages"] if p["competitor"] == "Lovable")
    assert any(plan["price"] == "$30" for plan in lovable["plans"]) and lovable["label"] == "Lovable"

    runs = client.get("/api/runs").json()
    assert [r["started_at"] for r in runs] == ["2026-10-25T12:00:00Z", "2026-10-25T06:00:00Z"]
    assert {"label": "Replit", "ok": False} in runs[0]["pages"] and runs[0]["changes"] == 1


def test_the_json_api_is_read_only_from_other_sites(client):
    preflight = client.options("/run", headers={"Origin": "https://example.base44.app", "Access-Control-Request-Method": "POST"})
    assert preflight.status_code == 400 and "POST" not in preflight.headers.get("access-control-allow-methods", "")


def test_the_app_starts_a_run_every_six_hours_by_itself(client, monkeypatch):
    # The client's last run started at 2026-10-25T12:00:00Z.
    from datetime import datetime, timezone
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store: calls.append(store))
    at = lambda text: datetime.fromisoformat(text).replace(tzinfo=timezone.utc)  # noqa: E731
    assert web.run_if_due(6, at("2026-10-25T17:30:00")) == "not due" and calls == []
    assert web.run_if_due(6, at("2026-10-25T17:56:00")) == "ran" and len(calls) == 1  # within 5 minutes counts
    web._running.acquire()
    try:
        assert web.run_if_due(6, at("2026-10-25T18:30:00")) == "busy"
    finally:
        web._running.release()


def test_a_scheduled_run_that_crashes_does_not_stop_the_schedule(client, monkeypatch):
    def crash(store):
        raise RuntimeError("browser died")
    monkeypatch.setattr(web, "run_live", crash)
    from datetime import datetime, timezone
    assert web.run_if_due(6, datetime(2026, 10, 26, tzinfo=timezone.utc)) == "ran"
    assert web._running.acquire(blocking=False)
    web._running.release()


def test_test_upload_shows_what_each_id_led_to_and_saves_nothing(client):
    before = len(web.store().runs(100))
    response = client.post("/test", files={"cases": ("cases.json", open("tests/cases/tricky-cases.json", "rb").read())})
    page = response.text
    assert response.status_code == 200 and "What each input led to" in page and "<form" in page
    assert "so confidence 0.2 and labelled unverified" in page  # the rule behind t-03
    assert "hidden comment" in page  # t-02's injection, noted and not followed
    assert "<td>t-05</td>" in page and "<b>Skipped</b>" in page  # the ad
    assert "<td>t-03</td>" in page and "unverified" in page  # the rumor
    assert "appears more than once" in page and "Download result.json" in page
    assert "bl_demo_test" not in page and "TIDEPOOL-OK" not in page
    assert len(web.store().runs(100)) == before
