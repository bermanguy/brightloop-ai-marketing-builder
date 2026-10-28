"""The web app, on a SQLite store filled from the saved pages. No keys, no network."""

import glob
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
    assert "<th>Started by</th>" in body


def test_a_run_records_what_started_it(tmp_path):
    from pricewatch.store import Store

    store = Store(str(tmp_path / "db.sqlite"))
    run_live(store, write_pages(tmp_path / "p", "2026-10-25T06:00:00Z"), use_ai=False, started_at="2026-10-25T06:00:00Z",
             trigger="schedule")
    assert store.runs(1)[0]["run"]["trigger"] == "schedule"


def test_run_needs_the_token(client, monkeypatch):
    assert client.post("/run").status_code == 403
    assert client.post("/run", headers={"Authorization": "Bearer wrong"}).status_code == 403
    monkeypatch.delenv("RUN_TOKEN")
    assert client.post("/run", headers={"Authorization": "Bearer test-token"}).status_code == 403


def test_run_with_the_token_starts_a_live_run(client, monkeypatch):
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: calls.append(trigger) or store.runs(1)[0])
    response = client.post("/run", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200 and response.json()["items"] == 1 and len(calls) == 1
    form = client.post("/run", data={"token": "test-token"}, follow_redirects=False)
    assert form.status_code == 303 and len(calls) == 2
    assert calls == ["API", "manual"]


def test_test_upload_returns_the_same_result_as_run(client):
    sample = open("fixtures/sample-cases.json", "rb").read()
    response = client.post("/test?format=json", files={"cases": ("cases.json", sample)})
    result = response.json()
    assert len(result["items"]) == 2 and len(result["skipped"]) == 6
    assert "bl_demo_4c19e2" not in response.text


def test_test_upload_matches_the_run_command_byte_for_byte(client, tmp_path):
    from pricewatch import cli

    for cases in ["fixtures/sample-cases.json", *sorted(glob.glob("tests/cases/*.json"))]:
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
    def crash(store, trigger=None):
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(web, "run_live", crash)
    crashing = TestClient(web.app, raise_server_exceptions=False)
    assert crashing.post("/run", headers={"Authorization": "Bearer test-token"}).status_code == 500
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: store.runs(1)[0])
    assert client.post("/run", headers={"Authorization": "Bearer test-token"}).status_code == 200


def test_the_schedule_keeps_the_six_hour_pace(client, monkeypatch):
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: calls.append(trigger) or store.runs(1)[0])
    auth = {"Authorization": "Bearer test-token"}
    # The fixture's last run is from 2026-10-25, long enough ago: this call runs.
    assert "items" in client.post("/run?unless_ran_within_hours=5.5", headers=auth).json() and len(calls) == 1
    now = web.datetime.now(web.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    web.store().save_run({"items": [], "skipped": [], "run": {"started_at": now, "errors": [], "cost_usd": 0.0}})
    assert client.post("/run?unless_ran_within_hours=5.5", headers=auth).json() == {"skipped": f"last run started at {now}"}
    assert len(calls) == 1
    # Check now always runs.
    assert client.post("/run", headers=auth).status_code == 200 and len(calls) == 2
    assert calls == ["backup schedule", "API"]


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


def test_other_sites_can_check_now_and_test_but_never_send_the_run_token(client):
    origin = {"Origin": "https://example.base44.app", "Access-Control-Request-Method": "POST"}
    assert client.options("/api/check", headers=origin).status_code == 200
    with_token = client.options("/run", headers={**origin, "Access-Control-Request-Headers": "authorization"})
    assert with_token.status_code == 400  # a browser on another site can't send the Bearer token


def test_api_check_starts_a_run_in_the_background_at_most_every_30_minutes(client, monkeypatch):
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: calls.append(trigger))
    started = client.post("/api/check")
    assert started.status_code == 202 and started.json()["status"] == "started"
    for _ in range(100):  # the background run releases the lock when done
        if web._running.acquire(blocking=False):
            web._running.release()
            break
        web.time.sleep(0.01)
    assert calls == ["manual"]
    now = web.datetime.now(web.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    web.store().save_run({"items": [], "skipped": [], "run": {"started_at": now, "errors": [], "cost_usd": 0.0}})
    again = client.post("/api/check")
    assert again.status_code == 429 and again.json()["last_check"] == now and again.json()["next_allowed_at"] > now
    assert calls == ["manual"]


def test_api_check_is_refused_while_a_run_is_going_and_off_without_run_token(client, monkeypatch):
    web._running.acquire()
    try:
        assert client.post("/api/check").status_code == 409
    finally:
        web._running.release()
    monkeypatch.delenv("RUN_TOKEN")
    assert client.post("/api/check").status_code == 503


def test_api_test_gives_the_run_result_and_the_same_rows_as_the_page(client):
    cases = open("fixtures/sample-cases.json", "rb").read()
    answer = client.post("/api/test", files={"cases": ("cases.json", cases)}).json()
    file_result = client.post("/test?format=json", files={"cases": ("cases.json", cases)}).json()
    assert answer["result"]["items"] == file_result["items"] and answer["result"]["skipped"] == file_result["skipped"]
    assert answer["summary"] == {"signals": 8, "items": 2, "skipped": 6, "errors": 0} and len(answer["rows"]) == 8
    assert "bl_demo_4c19e2" not in json.dumps(answer)  # the demo key is never echoed
    page = client.post("/test", files={"cases": ("cases.json", cases)}).text
    for row in answer["rows"]:
        assert f"<td>{row['id']}</td>" in page and row["result"] in ("item", "skipped") and row["why"]


def test_the_app_starts_a_run_every_six_hours_by_itself(client, monkeypatch):
    # The client's last run started at 2026-10-25T12:00:00Z.
    from datetime import datetime, timezone
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: calls.append(trigger))
    at = lambda text: datetime.fromisoformat(text).replace(tzinfo=timezone.utc)  # noqa: E731
    assert web.run_if_due(6, at("2026-10-25T17:30:00")) == "not due" and calls == []
    assert web.run_if_due(6, at("2026-10-25T17:56:00")) == "ran" and calls == ["schedule"]  # within 5 minutes counts
    web._running.acquire()
    try:
        assert web.run_if_due(6, at("2026-10-25T18:30:00")) == "busy"
    finally:
        web._running.release()


def test_a_scheduled_run_that_crashes_does_not_stop_the_schedule(client, monkeypatch):
    def crash(store, trigger=None):
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
    assert "hidden part" in page  # t-02's injection, noted and not followed
    assert "<td>t-05</td>" in page and "<b>Skipped</b>" in page  # the ad
    assert "<td>t-03</td>" in page and "unverified" in page  # the rumor
    assert "appears more than once" in page and "Download result.json" in page
    assert "bl_demo_test" not in page and "TIDEPOOL-OK" not in page
    assert len(web.store().runs(100)) == before


def test_changes_filter_by_time_range_and_company(client):
    runs = web.store().runs()
    later = web.datetime(2026, 11, 20, tzinfo=web.timezone.utc)  # the fixture's runs are from 2026-10-25
    assert web.changes_in(runs, "7", now=later) == [] and web.changes_in(runs, "30", now=later)
    assert web.changes_in(runs, "all", now=later) == web.changes_in(runs, "nonsense", now=web.datetime(2026, 10, 26, tzinfo=web.timezone.utc))
    everyone = web.changes_in(runs, "all")
    one = everyone[0]["competitor"]
    assert web.changes_in(runs, "all", one) == [i for i in everyone if i["competitor"] == one]
    assert web.changes_in(runs, "all", "Nobody") == []


def test_filters_on_the_pages_and_the_api(client):
    page = client.get("/?days=all&competitor=Lovable").text
    assert "<option value='all' selected>" in page and "<option value='Lovable' selected>" in page
    assert client.get("/api/changes?days=all&competitor=Nobody").json()["items"] == []
    assert "Lovable" in client.get("/api/changes").json()["competitors"]
    pricing = client.get("/api/pricing?competitor=Lovable").json()["pages"]
    assert pricing and {p["competitor"] for p in pricing} == {"Lovable"}
    assert "Bolt" not in client.get("/pricing?competitor=Lovable").text.split("</form>", 1)[1]


def test_check_now_needs_no_token_but_runs_at_most_every_30_minutes(client, monkeypatch):
    calls = []
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: calls.append(trigger))
    # The fixture's last run is from 2026-10-25, long ago: the button runs, with no token.
    response = client.post("/check", follow_redirects=False)
    assert response.status_code == 303 and calls == ["manual"]
    now = web.datetime.now(web.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    web.store().save_run({"items": [], "skipped": [], "run": {"started_at": now, "errors": [], "cost_usd": 0.0}})
    again = client.post("/check?now=2030-01-01T00:00:00", follow_redirects=False)
    assert again.status_code == 200 and "at most once every 30 minutes" in again.text and calls == ["manual"]
    assert "name='token'" not in client.get("/runs").text


def test_check_now_is_off_without_run_token(client, monkeypatch):
    monkeypatch.delenv("RUN_TOKEN")
    assert "switched off" in client.post("/check").text


def test_run_log_rows_expand_to_what_the_run_read_found_and_decided(client):
    body = client.get("/runs").text
    assert "<details><summary>Details</summary>" in body
    assert "<b>Read.</b>" in body and "plans" in body and "<b>Found</b>" in body
    assert "<b>Decided.</b>" in body and "so confidence 0.9" in body  # the rule behind a pricing-page change


def test_api_runs_carries_the_same_details_as_the_run_log(client):
    [latest, _] = client.get("/api/runs").json()
    details = latest["details"]
    assert details["found"].startswith("1 change on the pricing pages")
    assert details["decided"][0]["rule"].endswith("so confidence 0.9.") and details["decided"][0]["next_step"]
    assert any("couldn't read" in line for line in details["read"])


def test_counters_count_the_cards_in_the_filter_and_each_one_shows_its_cards(client):
    items = [
        {"competitor": "Lovable", "unverified": False, "change": "price_up"},
        {"competitor": "Lovable", "unverified": True, "change": None},
        {"competitor": "Bolt", "unverified": False, "change": "options"},
    ]
    summary = web.summary_of(items)
    assert (summary["total"], summary["verified"], summary["unverified"]) == (3, 2, 1)
    assert summary["by_competitor"] == [{"competitor": "Lovable", "count": 2}, {"competitor": "Bolt", "count": 1}]
    assert {c["change"] for c in summary["by_change"]} == {"price up", "new price options"}
    assert web.focused(items, "unverified") == [items[1]] and web.focused(items, "price up") == [items[0]]
    assert web.focused(items, "nonsense") == items


def test_changes_page_and_api_show_the_counters(client):
    page = client.get("/?days=all").text
    assert "class='strip'" in page and "<span class='n'>1</span><span class='t'>All changes</span>" in page
    assert "Show more stats" not in page and "<span class='t'>price up</span>" not in page  # D33: three tiles only
    data = client.get("/api/changes?days=all&focus=unverified").json()
    assert data["summary"]["total"] == 1 and data["items"] == []


def test_every_page_shows_how_fresh_the_data_is(client):
    from datetime import datetime, timezone

    fresh = web.freshness(datetime(2026, 10, 25, 14, 0, tzinfo=timezone.utc))
    assert "Last checked 2h ago" in fresh and "dot old" not in fresh and "out of date" not in fresh
    stale = web.freshness(datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc))
    assert "Last checked 8h ago · may be out of date" in stale and "dot old" in stale
    for path in ["/", "/pricing", "/runs", "/test"]:
        assert "Last checked" in client.get(path).text


def test_api_check_says_when_a_run_is_in_progress(client, monkeypatch):
    seen = []
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: seen.append(client.get("/api/check").json()))
    assert client.get("/api/check").json() == {"running": False, "started_at": None, "trigger": None}
    with web._running:
        web.run_now("manual")
    assert seen[0]["running"] and seen[0]["trigger"] == "manual" and seen[0]["started_at"]
    assert client.get("/api/check").json()["running"] is False


def test_test_upload_sends_alerts_only_when_asked_and_never_changes_the_result(client, monkeypatch):
    from pricewatch import notify
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C1")
    monkeypatch.setattr(web, "_last_test_alert", None)
    sent = []
    monkeypatch.setattr(notify, "_post", lambda url, body, bearer: (sent.append(body), (200, {"ok": True}))[1])
    cases = open("tests/cases/1-trust-and-scope.json", "rb").read()
    plain = client.post("/api/test", files={"cases": ("c.json", cases)}).json()
    assert plain["alerts"] == [] and sent == []  # off by default
    asked = client.post("/api/test", files={"cases": ("c.json", cases)},
                        data={"notify": ["slack"], "min_confidence": "0.9", "competitors": "Lovable"}).json()
    assert asked["result"]["items"] == plain["result"]["items"] and asked["alerts"] == ["Slack message posted to channel C1."]
    assert len(sent) == 1 and "[TEST]" in sent[0]["text"] and "Lovable" in sent[0]["text"] and "Bolt" not in sent[0]["text"]
    again = client.post("/api/test", files={"cases": ("c.json", cases)}, data={"notify": ["slack"]}).json()
    assert "at most once every 5 minutes" in again["alerts"][0] and len(sent) == 1
    log = client.get("/api/alerts/log").json()
    assert len(log) == 1 and log[0]["test"] and log[0]["trigger"] == "test upload" and log[0]["slack_channel"] == "C1"
    page = client.post("/test", files={"cases": ("c.json", cases)}, data={"notify": ["email"]}).text
    assert "<b>Alerts.</b>" in page
    assert client.get("/api/alerts").json()["slack"] is True and "xoxb" not in client.get("/api/alerts").text


def test_a_live_run_alerts_its_new_changes_when_a_channel_is_set_up(client, monkeypatch):
    from pricewatch import notify
    sent = []
    monkeypatch.setattr(notify, "send", lambda items, channels, test=False, email_to=None: sent.append((items, channels, email_to)) or ["ok"])
    item = {"confidence": 0.9, "competitor": "Lovable", "headline": "Pro now $30"}
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: {"items": [item, {"confidence": 0.2, "competitor": "Bolt"}]})
    web.run_now("manual")
    assert sent == []  # no channel set up
    monkeypatch.setenv("RESEND_API_KEY", "re_x")
    monkeypatch.setenv("ALERT_EMAIL_TO", "maya@example.com")
    web.run_now("schedule")
    assert sent == [([item], ["email"], "maya@example.com")]
    log = client.get("/api/alerts/log").json()
    assert log[0]["trigger"] == "schedule" and log[0]["sent"][0]["headline"] == "Pro now $30" and log[0]["outcome"] == ["ok"]
    assert log[0]["recipients"] == ["m***@example.com"] and log[1]["outcome"][0].startswith("Nothing sent")
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: {"items": []})
    web.run_now("schedule")
    assert len(client.get("/api/alerts/log").json()) == 2  # a run with no new changes notes nothing


def test_alert_settings_can_be_changed_and_each_run_obeys_them(client, monkeypatch):
    from pricewatch import notify
    monkeypatch.setenv("RESEND_API_KEY", "re_x")
    monkeypatch.setenv("ALERT_EMAIL_TO", "maya@example.com")
    sent = []
    monkeypatch.setattr(notify, "send", lambda items, channels, test=False, email_to=None: sent.append(email_to) or ["ok"])
    monkeypatch.setattr(web, "run_live", lambda store, trigger=None: {"items": [{"confidence": 0.9, "competitor": "Lovable"}]})
    shown = client.get("/api/alerts").json()
    assert shown["email_on"] and shown["on_schedule"] and shown["on_check_now"] and shown["extra_emails"] == []
    changed = client.post("/api/alerts", json={"on_check_now": False, "add_email": "reviewer@example.org"}).json()
    assert changed["on_check_now"] is False and changed["extra_emails"] == ["r***@example.org"]
    assert "reviewer@" not in client.get("/api/alerts").text and "reviewer@" not in client.get("/api/alerts/log").text
    web.run_now("manual")
    web.run_now("schedule")
    assert sent == ["maya@example.com,reviewer@example.org"]
    log = client.get("/api/alerts/log").json()
    assert log[0]["recipients"] == ["m***@example.com", "r***@example.org"]
    assert log[1]["outcome"] == ["Nothing sent: alerts are off for Check now."]
    assert log[2]["kind"] == "settings" and "Check now off" in log[2]["outcome"][0]
    client.post("/api/alerts", json={"email_on": False, "remove_email": 0, "min_confidence": 0.4, "competitors": ["Bolt"]})
    assert client.get("/api/alerts").json()["extra_emails"] == []
    web.run_now("schedule")
    assert len(sent) == 1 and "none of the 1 changes passed the filters" in client.get("/api/alerts/log").json()[0]["outcome"][0]
    page = client.get("/alerts").text
    assert "Alert log" in page and "reviewer@" not in page and "re_x" not in page


@pytest.mark.parametrize("change, error", [
    ({"email_on": "no"}, "true or false"), ({"min_confidence": 0.5}, "one of 0.9"), ({"add_email": "not an email"}, "one email"),
    ({"remove_email": 3}, "position"), ({"competitors": [1]}, "list of names"), ([1, 2], "JSON object"),
])
def test_bad_alert_settings_are_refused_and_change_nothing(client, change, error):
    answer = client.post("/api/alerts", json=change)
    assert answer.status_code == 400 and error in answer.json()["error"]
    assert client.get("/api/alerts").json()["changed_at"] is None and client.get("/api/alerts/log").json() == []


def test_at_most_three_extra_addresses(client):
    for n in range(3):
        client.post("/api/alerts", json={"add_email": f"r{n}@example.org"})
    assert client.post("/api/alerts", json={"add_email": "r0@example.org"}).status_code == 200  # already there
    answer = client.post("/api/alerts", json={"add_email": "r9@example.org"})
    assert answer.status_code == 400 and "At most 3" in answer.json()["error"]


def test_a_test_alert_can_email_one_given_address_within_the_daily_cap(client, monkeypatch):
    from pricewatch import notify
    monkeypatch.setenv("RESEND_API_KEY", "re_x")
    monkeypatch.setenv("ALERT_EMAIL_TO", "guy@example.com")
    monkeypatch.setattr(web, "_last_test_alert", None)
    monkeypatch.setattr(web, "_test_alerts_today", {})
    monkeypatch.setattr(web, "TEST_ALERT_EVERY_MIN", 0)
    sent = []
    monkeypatch.setattr(notify, "_post", lambda url, body, bearer: (sent.append(body["to"]), (200, {}))[1])
    cases = {"cases": ("c.json", open("tests/cases/1-trust-and-scope.json", "rb").read())}
    bad = client.post("/api/test", files=cases, data={"notify": ["email"], "email_to": "a@b.com, c@d.com"}).json()
    assert bad["alerts"] == ['No alert sent: "Send to" needs one email address.'] and sent == []
    ok = client.post("/api/test", files=cases, data={"notify": ["email"], "email_to": "reviewer@example.org"}).json()
    assert ok["alerts"] == ["Email sent to r***@example.org."] and sent == [["reviewer@example.org"]]
    client.post("/api/test", files=cases, data={"notify": ["email"]})
    assert sent[-1] == ["guy@example.com"]  # no "Send to": this server's inbox
    monkeypatch.setattr(web, "TEST_ALERTS_PER_DAY", 2)
    capped = client.post("/api/test", files=cases, data={"notify": ["email"]}).json()
    assert "today's 2 test alerts have been used" in capped["alerts"][0] and len(sent) == 2
    monkeypatch.setattr(notify, "_post", lambda url, body, bearer: (403, {}))
    assert "until a sending domain is verified" in notify.send(ok["result"]["items"][:1], ["email"], True, email_to="x@y.com")[0]
