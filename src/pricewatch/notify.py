"""Alerts: after a run, send the new changes that pass the filters by email and to a Slack channel.

Everything comes from environment variables, and each channel is off until its own are set:

    RESEND_API_KEY, ALERT_EMAIL_TO     email through Resend (ALERT_EMAIL_FROM is optional)
    SLACK_BOT_TOKEN, SLACK_CHANNEL_ID  a message in one Slack channel (the bot must be in it)
    ALERT_MIN_CONFIDENCE               default 0.6: changes seen on the competitor's own site
    ALERT_COMPETITORS                  comma-separated names; empty means all companies

Only the web app calls this (a live run, or a Test upload that asks for it), so
./run and ./proof never send anything. The filters are rules, not AI (D13). The
text sent is the item's own text, with every source quote and link (no link, no
number); signal text is escaped so it can't format or mention anyone (D1).
"""

import html
import json
import os
import re
import urllib.error
import urllib.request

RESEND_URL = "https://api.resend.com/emails"
SLACK_URL = "https://slack.com/api/chat.postMessage"
DEFAULT_FROM = "Brightloop Pricing Watch <onboarding@resend.dev>"
TIMEOUT_S = 15
TEST_NOTE = "TEST: not real pricing data. These changes come from a file uploaded on Test upload."
SAFE_URL = re.compile(r"https?://[\w.-]+(/[\w./%?=&#~+-]*)?")


def settings():
    """The alert settings, safe to show: which channels are set up, the filters, never a key."""
    to = os.environ.get("ALERT_EMAIL_TO", "")
    return {
        "email": bool(os.environ.get("RESEND_API_KEY") and to),
        "email_to": _mask(to),
        "slack": bool(os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("SLACK_CHANNEL_ID")),
        "slack_channel": os.environ.get("SLACK_CHANNEL_ID") or None,
        "min_confidence": min_confidence(),
        "competitors": competitors(),
    }


def min_confidence(value=None):
    try:
        return float(value if value not in (None, "") else os.environ.get("ALERT_MIN_CONFIDENCE", "0.6"))
    except ValueError:
        return 0.6


def competitors(value=None):
    raw = value if value is not None else os.environ.get("ALERT_COMPETITORS", "")
    names = raw if isinstance(raw, list) else str(raw).split(",")
    return [n.strip() for n in names if n and n.strip()]


def pick(items, min_conf, names):
    """The items that pass the filters: confidence at least min_conf, and one of the companies (all if none)."""
    wanted = {n.lower() for n in names}
    return [i for i in items if i["confidence"] >= min_conf and (not wanted or str(i.get("competitor", "")).lower() in wanted)]


def send(items, channels, test=False, post=None):
    """Send the items to each channel in `channels` ("email", "slack") that is set up.

    Returns one line per channel saying what happened; never raises, never shows a key.
    """
    post = post or _post
    if not items:
        return ["Nothing to send: no change passed the filters."]
    lines = []
    for channel in channels:
        try:
            if channel == "email":
                lines.append(_send_email(items, test, post))
            elif channel == "slack":
                lines.append(_send_slack(items, test, post))
        except Exception as exc:  # a failed alert never fails the run
            lines.append(f"{channel.capitalize()} failed: {exc.__class__.__name__}.")
    return lines


def subject(items, test):
    names = ", ".join(sorted({str(i.get("competitor")) for i in items}))
    n = len(items)
    return f"{'[TEST] ' if test else ''}Pricing watch: {n} change{'s' if n != 1 else ''} ({names})"


def _send_email(items, test, post):
    key, to = os.environ.get("RESEND_API_KEY"), os.environ.get("ALERT_EMAIL_TO", "")
    if not (key and to):
        return "Email is not set up on this server."
    body = {"from": os.environ.get("ALERT_EMAIL_FROM") or DEFAULT_FROM,
            "to": [a.strip() for a in to.split(",") if a.strip()],
            "subject": subject(items, test), "html": email_html(items, test)}
    status, answer = post(RESEND_URL, body, key)
    return f"Email sent to {_mask(to)}." if 200 <= status < 300 else f"Email failed: Resend answered {status}."


def _send_slack(items, test, post):
    token, channel = os.environ.get("SLACK_BOT_TOKEN"), os.environ.get("SLACK_CHANNEL_ID")
    if not (token and channel):
        return "Slack is not set up on this server."
    body = {"channel": channel, "text": slack_text(items, test), "unfurl_links": False, "unfurl_media": False}
    status, answer = post(SLACK_URL, body, token)
    if status == 200 and answer.get("ok"):
        return f"Slack message posted to channel {channel}."
    return f"Slack failed: {str(answer.get('error') or status)[:60]}."


def _url(url):
    url = str(url or "")
    full = url if url.startswith(("http://", "https://")) else f"https://{url}"
    return full if SAFE_URL.fullmatch(full) else None


def _slack(value):
    # Slack's three control characters; escaping them stops <!channel>, <@user> and fake links.
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _label(item):
    return f"confidence {item['confidence']}" + (", unverified: don't act yet" if item.get("unverified") else "")


def slack_text(items, test):
    lines = [f"*{_slack(subject(items, test))}*"] + ([f"_{TEST_NOTE}_"] if test else [])
    for item in items:
        lines.append(f"\n*{_slack(item['headline'])}* ({_label(item)})\n{_slack(item['action'])}")
        for source in item["sources"]:
            url = _url(source["url"])
            where = f"<{url}|{_slack(source['url'])}>" if url else _slack(source["url"])
            lines.append(f"> “{_slack(source['quote'])}” — {where}")
    return "\n".join(lines)


def email_html(items, test):
    e = html.escape
    parts = [f"<h2>{e(subject(items, test))}</h2>"] + ([f"<p><b>{e(TEST_NOTE)}</b></p>"] if test else [])
    for item in items:
        sources = "".join(
            f"<li>&ldquo;{e(s['quote'])}&rdquo; &mdash; "
            + (f"<a href=\"{e(_url(s['url']))}\">{e(s['url'])}</a>" if _url(s["url"]) else e(s["url"])) + "</li>"
            for s in item["sources"])
        parts.append(f"<h3>{e(item['headline'])}</h3><p style='color:#555'>{e(_label(item))}</p>"
                     f"<p>{e(item['action'])}</p><ul>{sources}</ul>")
    return "".join(parts)


def _mask(addresses):
    def one(a):
        name, _, domain = a.strip().partition("@")
        return f"{name[:1]}***@{domain}" if domain else "***"
    return ", ".join(one(a) for a in addresses.split(",") if a.strip()) or None


def _post(url, body, bearer):
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {bearer}", "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {}
