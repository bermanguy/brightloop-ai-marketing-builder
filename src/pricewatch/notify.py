"""Alerts: after a run, send the new changes that pass the filters by email and to a Slack channel.

Everything comes from environment variables, and each channel is off until its own are set:

    ALERT_EMAIL_TO                     where email goes by default
    SMTP_USER, SMTP_PASSWORD           email through Gmail (an app password; SMTP_HOST for another server),
                                       sent from SMTP_USER to any address
    RESEND_API_KEY                     or email through Resend (ALERT_EMAIL_FROM is optional); without a
                                       verified domain Resend only delivers to the account's own address
    SLACK_BOT_TOKEN, SLACK_CHANNEL_ID  a message in one Slack channel (the bot must be in it)
    ALERT_MIN_CONFIDENCE               default 0.6: changes seen on the competitor's own site
    ALERT_COMPETITORS                  comma-separated names; empty means all companies

The app can save changes to these (on/off per channel and per trigger, up to
MAX_EXTRA_EMAILS more addresses, the filters); `settings(saved)` merges them over
the environment. Keys and the channels themselves stay in the environment.

Only the web app calls this (a live run, or a Test upload that asks for it), so
./run and ./proof never send anything. The filters are rules, not AI (D13). The
text sent is the item's own text, with every source quote and link (no link, no
number); signal text is escaped so it can't format or mention anyone (D1).
"""

import html
import json
import os
import re
import smtplib
import urllib.error
from email.message import EmailMessage
import urllib.request

RESEND_URL = "https://api.resend.com/emails"
SLACK_URL = "https://slack.com/api/chat.postMessage"
DEFAULT_FROM = "Brightloop Pricing Watch <onboarding@resend.dev>"
TIMEOUT_S = 15
TEST_NOTE = "TEST: not real pricing data. These changes come from a file uploaded on Test upload."
SAFE_URL = re.compile(r"https?://[\w.-]+(/[\w./%?=&#~+-]*)?")


CONFIDENCE_LEVELS = (0.9, 0.6, 0.4, 0.2)
MAX_EXTRA_EMAILS = 3
SWITCHES = ("email_on", "slack_on", "on_schedule", "on_check_now")
# Which switch a run's trigger obeys: Check now is "manual"; every other live run counts as scheduled.
TRIGGER_SWITCH = {"manual": "on_check_now"}


def settings(saved=None):
    """The alert settings, safe to show: which channels are set up, what's switched on, the filters,
    masked addresses, never a key. `saved` is what the app saved (Store.alert_settings())."""
    saved = saved or {}
    to = os.environ.get("ALERT_EMAIL_TO", "")
    return {
        "email": bool(to and (_smtp_ready() or os.environ.get("RESEND_API_KEY"))),
        "email_to": _mask(to),
        "slack": bool(os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("SLACK_CHANNEL_ID")),
        "slack_channel": os.environ.get("SLACK_CHANNEL_ID") or None,
        **{key: saved.get(key, True) for key in SWITCHES},
        "extra_emails": [_mask(a) for a in saved.get("extra_emails") or []],
        "min_confidence": min_confidence(saved.get("min_confidence")),
        "competitors": competitors(saved["competitors"]) if "competitors" in saved else competitors(),
        "changed_at": saved.get("changed_at"),
    }


def update(saved, changes):
    """Apply a settings change from the app. Returns (new saved settings, None) or (None, why not).

    `changes` may hold any of SWITCHES (true/false), min_confidence (one of CONFIDENCE_LEVELS),
    competitors (a list or "Lovable, Bolt"; empty is all), add_email (one address) and
    remove_email (the position of an extra address, from 0)."""
    if not isinstance(changes, dict):
        return None, "Send the changes as a JSON object."
    new = dict(saved or {})
    for key in SWITCHES:
        if key in changes:
            if not isinstance(changes[key], bool):
                return None, f"{key} must be true or false."
            new[key] = changes[key]
    if "min_confidence" in changes:
        try:
            level = float(changes["min_confidence"])
        except (TypeError, ValueError):
            level = None
        if level not in CONFIDENCE_LEVELS:
            return None, "min_confidence must be one of 0.9, 0.6, 0.4, 0.2."
        new["min_confidence"] = level
    if "competitors" in changes:
        value = changes["competitors"]
        if not isinstance(value, (str, list)) or not all(isinstance(n, str) for n in (value if isinstance(value, list) else [])):
            return None, "competitors must be a list of names."
        names = competitors(value)
        if len(names) > 10 or any(len(n) > 40 for n in names):
            return None, "competitors takes at most 10 names."
        new["competitors"] = names
    extras = list(new.get("extra_emails") or [])
    if changes.get("remove_email") is not None:
        index = changes["remove_email"]
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(extras):
            return None, "remove_email must be the position of an extra address."
        extras.pop(index)
    if changes.get("add_email"):
        address = str(changes["add_email"]).strip()
        if not valid_email(address):
            return None, "add_email needs one email address."
        if address.lower() not in {a.lower() for a in extras}:
            if len(extras) >= MAX_EXTRA_EMAILS:
                return None, f"At most {MAX_EXTRA_EMAILS} extra addresses; remove one first."
            extras.append(address)
    new["extra_emails"] = extras
    return new, None


def recipients(saved=None):
    """Every address a live alert goes to: ALERT_EMAIL_TO, then the extra addresses saved in the app."""
    owner = [a.strip() for a in os.environ.get("ALERT_EMAIL_TO", "").split(",") if a.strip()]
    return owner + [a for a in (saved or {}).get("extra_emails") or [] if a.lower() not in {o.lower() for o in owner}]


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


EMAIL = re.compile(r"[^@\s<>,;\"']{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")


def valid_email(address):
    return bool(EMAIL.fullmatch(str(address or "").strip())) and len(str(address)) <= 200


def send(items, channels, test=False, post=None, email_to=None):
    """Send the items to each channel in `channels` ("email", "slack") that is set up.

    email_to replaces ALERT_EMAIL_TO with one address (a Test upload's "Send to"; checked by the caller).

    Returns one line per channel saying what happened; never raises, never shows a key.
    """
    post = post or _post
    if not items:
        return ["Nothing to send: no change passed the filters."]
    lines = []
    for channel in channels:
        try:
            if channel == "email":
                lines.append(_send_email(items, test, post, email_to))
            elif channel == "slack":
                lines.append(_send_slack(items, test, post))
        except Exception as exc:  # a failed alert never fails the run
            lines.append(f"{channel.capitalize()} failed: {exc.__class__.__name__}.")
    return lines


def subject(items, test):
    names = ", ".join(sorted({str(i.get("competitor")) for i in items}))
    n = len(items)
    return f"{'[TEST] ' if test else ''}Pricing watch: {n} change{'s' if n != 1 else ''} ({names})"


def _smtp_ready():
    return bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def _send_email(items, test, post, email_to=None):
    key, to = os.environ.get("RESEND_API_KEY"), os.environ.get("ALERT_EMAIL_TO", "")
    if not (to and (_smtp_ready() or key)):
        return "Email is not set up on this server."
    to = email_to or to
    addresses = [a.strip() for a in to.split(",") if a.strip()]
    if _smtp_ready():
        _smtp(addresses, subject(items, test), email_html(items, test))
        return f"Email sent to {_mask(to)}."
    body = {"from": os.environ.get("ALERT_EMAIL_FROM") or DEFAULT_FROM, "to": addresses,
            "subject": subject(items, test), "html": email_html(items, test)}
    status, answer = post(RESEND_URL, body, key)
    if 200 <= status < 300:
        return f"Email sent to {_mask(to)}."
    if email_to and status == 403:  # Resend's answer for an address it won't send to yet
        return "Email failed: this server can only email its own inbox until a sending domain is verified."
    return f"Email failed: Resend answered {status}."


def _smtp(addresses, title, body_html):
    """Send through an SMTP server over SSL (Gmail by default), from SMTP_USER."""
    user = os.environ["SMTP_USER"]
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = f"Brightloop Pricing Watch <{user}>", ", ".join(addresses), title
    message.set_content("This alert is in HTML; open it in an email app that shows HTML.")
    message.add_alternative(body_html, subtype="html")
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), 465, timeout=TIMEOUT_S) as server:
        server.login(user, os.environ["SMTP_PASSWORD"].replace(" ", ""))
        server.send_message(message)


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


def mask(addresses):
    """Addresses as shown anywhere (the app, the alert log): first letter and domain only."""
    return _mask(addresses)


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
