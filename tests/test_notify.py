"""Alerts by email and Slack: filters by rule, escaped text, never a key in what's shown. No network."""

import json

import pytest

from pricewatch import notify
from pricewatch.core import process

ITEMS = process(json.load(open("tests/cases/2-injections-and-secrets.json")))["items"]


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_secret_123")
    monkeypatch.setenv("ALERT_EMAIL_TO", "maya@example.com")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret-456")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C0123456")
    sent = []
    monkeypatch.setattr(notify, "_post", lambda url, body, bearer: (sent.append((url, body, bearer)), (200, {"ok": True}))[1])
    return sent


def test_channels_are_off_until_their_settings_are_there(monkeypatch):
    for name in ("RESEND_API_KEY", "ALERT_EMAIL_TO", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID", "ALERT_MIN_CONFIDENCE", "ALERT_COMPETITORS"):
        monkeypatch.delenv(name, raising=False)
    settings = notify.settings()
    assert settings["email"] is False and settings["slack"] is False
    assert settings["min_confidence"] == 0.6 and settings["competitors"] == []
    assert notify.send(ITEMS, ["email", "slack"]) == ["Email is not set up on this server.", "Slack is not set up on this server."]


def test_settings_never_show_a_key_and_mask_the_address(configured):
    shown = json.dumps(notify.settings())
    assert "re_secret_123" not in shown and "xoxb-secret-456" not in shown and "maya@" not in shown
    assert notify.settings()["email_to"] == "m***@example.com" and notify.settings()["slack_channel"] == "C0123456"


def test_filters_are_rules_on_confidence_and_company():
    assert {i["confidence"] for i in notify.pick(ITEMS, 0.6, [])} == {0.9}
    lovable = notify.pick(ITEMS, 0.2, ["lovable"])
    assert lovable and all(i["competitor"] == "Lovable" for i in lovable)
    assert notify.competitors(" Lovable, ,Bolt ") == ["Lovable", "Bolt"] and notify.min_confidence("x") == 0.6


def test_messages_carry_quotes_and_links_and_escape_signal_text(configured):
    item = dict(ITEMS[0], headline="<!channel> <https://evil.example|click> & co", action="Act.")
    lines = notify.send([item], ["email", "slack"], test=True)
    assert lines == ["Email sent to m***@example.com.", "Slack message posted to channel C0123456."]
    (email_url, email, key), (slack_url, slack, token) = configured
    assert key == "re_secret_123" and token == "xoxb-secret-456" and slack["channel"] == "C0123456"
    assert "<!channel>" not in slack["text"] and "&lt;!channel&gt;" in slack["text"]
    assert "&lt;https://evil.example|click&gt; &amp; co" in slack["text"]
    assert "<!channel>" not in email["html"] and email["subject"].startswith("[TEST]")
    assert notify.TEST_NOTE in slack["text"] and item["sources"][0]["quote"][:20] in email["html"]


def test_a_failed_channel_says_so_without_the_key(configured, monkeypatch):
    monkeypatch.setattr(notify, "_post", lambda url, body, bearer: (403, {"ok": False, "error": "not_in_channel"}))
    lines = notify.send(ITEMS[:1], ["email", "slack"])
    assert lines == ["Email failed: Resend answered 403.", "Slack failed: not_in_channel."]
    assert "secret" not in " ".join(lines)


def test_nothing_is_sent_when_no_change_passes(configured):
    assert notify.send([], ["email"]) == ["Nothing to send: no change passed the filters."] and configured == []


def test_email_goes_through_gmail_when_smtp_is_set_up(monkeypatch):
    for name in ("RESEND_API_KEY",):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ALERT_EMAIL_TO", "guy@example.com")
    monkeypatch.setenv("SMTP_USER", "guy@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")
    sent = []
    monkeypatch.setattr(notify, "_smtp", lambda to, title, body: sent.append((to, title, body)))
    assert notify.settings()["email"] is True and "abcd" not in json.dumps(notify.settings())
    assert notify.send(ITEMS[:1], ["email"], test=True, email_to="reviewer@example.org") == ["Email sent to r***@example.org."]
    assert sent[0][0] == ["reviewer@example.org"] and sent[0][1].startswith("[TEST]") and notify.TEST_NOTE in sent[0][2]


def test_a_failed_smtp_login_is_reported_without_the_password(monkeypatch):
    monkeypatch.setenv("ALERT_EMAIL_TO", "guy@example.com")
    monkeypatch.setenv("SMTP_USER", "guy@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secretpass")

    def refuse(*args):
        raise notify.smtplib.SMTPAuthenticationError(535, b"bad secretpass")
    monkeypatch.setattr(notify, "_smtp", refuse)
    assert notify.send(ITEMS[:1], ["email"]) == ["Email failed: SMTPAuthenticationError."]
