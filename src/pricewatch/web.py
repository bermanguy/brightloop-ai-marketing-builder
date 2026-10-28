"""The web app: what changed, current pricing, the run log, "Check now", and the test upload.

    uvicorn pricewatch.web:app

Plain server-rendered HTML, no front-end build. Every value shown comes from the
store (snapshots and run results), written as it appears on the competitor's page.

POST /check is the Check now button: anyone may press it, but it starts at most one run
every 30 minutes (D29). POST /run starts a live run for scripts, such as GitHub's backup
schedule, and needs RUN_TOKEN as "Authorization: Bearer ..."; without RUN_TOKEN set,
runs are switched off and the app only shows what's stored.

The app schedules its own runs: with SCHEDULE_EVERY_HOURS set (6 on Render), a
background thread starts a run whenever the last one is that old, checking
every few minutes. It's reliable because the app is always awake (D22). GitHub's
hourly workflow stays as a backup; it dropped most of its triggers on the first
night (3 of 13 fired), which is why the app now keeps time itself.

/api/changes, /api/pricing and /api/runs give the same data as JSON, read-only,
for a front end hosted elsewhere (the Base44 app). Any site may read them: they
show only what the HTML pages already show.
"""

import base64
import hmac
import html
import json
import os
import re
import threading
from collections import Counter
from urllib.parse import quote
from contextlib import asynccontextmanager
import time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Form, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .core import process
from .core.text import hides_text
from .live import run_live
from .sources.fetch import label
from .store import Store

@asynccontextmanager
async def lifespan(app):
    every = os.environ.get("SCHEDULE_EVERY_HOURS")
    if every:
        threading.Thread(target=_schedule, args=(float(every),), daemon=True).start()
    yield


app = FastAPI(title="Brightloop Pricing Watch", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"])
_store = None
_running = threading.Lock()
CHECK_EVERY_S = 300


_current = None  # the run going now: {"started_at", "trigger"}, for GET /api/check


def run_now(trigger):
    """Start a live run (the caller holds _running) and note it, so the front end can show it in progress."""
    global _current
    _current = {"started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "trigger": trigger}
    try:
        return run_live(store(), trigger=trigger)
    finally:
        _current = None


def store():
    global _store
    if _store is None:
        _store = Store()
    return _store


def esc(value):
    """Escape for HTML, showing the page's ~~struck~~ prices as struck."""
    return re.sub(r"~~(.+?)~~", r"<s>\1</s>", html.escape(str(value if value is not None else "")))


def link(url):
    url = str(url or "")
    full = url if url.startswith(("http://", "https://")) else f"https://{url}"
    if not re.fullmatch(r"https?://[\w.-]+(/[\w./%-]*)?", full):
        return esc(url)
    return f'<a href="{html.escape(full)}">{esc(url)}</a>'


STYLE = """
body{font-family:system-ui,sans-serif;max-width:960px;margin:0 auto;padding:16px;color:#1a1a1a;background:#fff;line-height:1.45}
nav a{margin-right:16px} .brand{margin-right:24px} h1{font-size:1.4rem} .item{border-top:1px solid #ddd;padding:12px 0}
.meta{color:#555;font-size:.9rem} .badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.8rem;background:#eee}
.unverified{background:#fde2b8} .item h3{font-size:1.05rem;margin:6px 0} .why{color:#333} .sources{font-size:.9rem;color:#333;margin-bottom:8px} .label{font-weight:600;margin:8px 0 2px} .failed{color:#a00} .strip{margin:10px 0} .fresh{float:right;font-size:.88rem;color:#555} .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:#16a34a} .dot.old{background:#d97706} .tiles{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin-bottom:8px} .tile{display:flex;flex-direction:column;border:1px solid #d5d8e0;border-radius:8px;background:#fff;text-decoration:none;color:#223} .tile.big{padding:10px 14px;min-width:130px} .tile.big .n{font-size:1.6rem;font-weight:700;line-height:1.1} .tile .t{font-size:.85rem;color:#555} .tile:hover{border-color:#8a90c8} .tile.on{border-color:#4f46e5;background:#eef0ff} .filters{margin:8px 0} .filters select{margin-right:6px} .details td{border-bottom:2px solid #ccc;padding-top:0} summary{cursor:pointer;color:#0645ad} .how{background:#f4f6f8;border-radius:6px;padding:10px 12px;margin-bottom:12px;font-size:.92rem} table{border-collapse:collapse;width:100%;margin-bottom:24px}
td:first-child{white-space:nowrap} td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left;vertical-align:top;font-size:.92rem} ul{margin:0;padding-left:18px}
"""


FRESH_HOURS = 7  # the schedule runs every 6 hours, plus some slack


def freshness(now=None):
    """'Last checked 2h ago' for the top bar: green when recent, amber when a scheduled run looks missed."""
    try:
        last = store().runs(1)
    except Exception:  # the page still renders if the store can't be read
        return ""
    if not last:
        return '<span class="fresh">No checks yet</span>'
    started = datetime.strptime(last[0]["run"]["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    minutes = max(0, int(((now or datetime.now(timezone.utc)) - started).total_seconds() // 60))
    ago = f"{minutes} min ago" if minutes < 60 else f"{minutes // 60}h ago" if minutes < 48 * 60 else f"{minutes // 1440} days ago"
    old = minutes >= FRESH_HOURS * 60
    return (f'<span class="fresh" title="{esc(last[0]["run"]["started_at"])}"><span class="dot{" old" if old else ""}"></span>'
            f'Last checked {ago}{" · may be out of date" if old else ""}</span>')


def page(title, body):
    nav = f'<nav>{freshness()}<b class="brand">Brightloop Pricing Watch</b><a href="/">Changes</a><a href="/pricing">Current pricing</a><a href="/runs">Run log</a><a href="/test">Test upload</a></nav>'
    return HTMLResponse(
        f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)} · Brightloop Pricing Watch</title><style>{STYLE}</style></head><body>{nav}<h1>{esc(title)}</h1>{body}</body></html>"
    )


def render_item(item):
    badge = '<span class="badge unverified">unverified</span> ' if item.get("unverified") else ""
    sources = "".join(f"<li>{link(s['url'])}: &ldquo;{esc(s['quote'])}&rdquo;</li>" for s in item["sources"])
    # What changed (the quote, with its link) comes first, then why it matters, then what to do.
    changed = "What's claimed" if item.get("unverified") else "What changed"
    return (
        f'<div class="item"><div class="meta">{esc(item.get("competitor"))} · seen {esc(item.get("seen_at"))} · '
        f'{badge}confidence {item["confidence"]}</div><h3>{esc(item.get("headline"))}</h3>'
        f"<p class='label'>{changed}</p><ul class='sources'>{sources}</ul>"
        f'<p class="why"><b>Why it matters:</b> {esc(item["why"])}</p>'
        f"<p class='label'>Recommended next steps</p><ul class='steps'>"
        + "".join(f"<li>{esc(step)}</li>" for step in item.get("steps") or [item["action"]]) + "</ul></div>"
    )


def recent_items(runs):
    return sorted((item for run in runs for item in run["items"]), key=lambda i: i.get("seen_at") or "", reverse=True)


# Filters, shared by the pages and the API so every front end filters the same way.
RANGES = {"7": "Last 7 days", "30": "Last 30 days", "all": "All time"}


def changes_in(runs, days="7", competitor=None, now=None):
    """Items from runs started in the last `days` days ("all" for every run), for one competitor or all."""
    days = days if days in RANGES else "7"
    if days != "all":
        since = ((now or datetime.now(timezone.utc)) - timedelta(days=int(days))).strftime("%Y-%m-%dT%H:%M:%SZ")
        runs = [r for r in runs if r["run"]["started_at"] >= since]
    items = recent_items(runs)
    return [i for i in items if i.get("competitor") == competitor] if competitor else items


# How each kind of change is counted in the summary strip.
CHANGE_LABELS = {"price_up": "price up", "price_down": "price down", "price": "price changed", "details": "plan contents",
                 "limits": "limits", "added": "plan added", "removed": "plan removed", "options": "new price options",
                 "opens": "billing view", "view": "billing view"}


def summary_of(items):
    """Counts of the cards in the current filter: rules, not AI (D30). Each count is a filter of
    those same cards, so every number shown traces back to cards and their sources."""
    count = lambda pairs: sorted(Counter(pairs).items(), key=lambda kv: (-kv[1], str(kv[0]).lower()))  # noqa: E731
    return {
        "total": len(items),
        "verified": sum(1 for i in items if not i.get("unverified")),
        "unverified": sum(1 for i in items if i.get("unverified")),
        "by_competitor": [{"competitor": c, "count": n} for c, n in count(i.get("competitor") for i in items)],
        "by_change": [{"change": c, "count": n} for c, n in count(CHANGE_LABELS.get(i.get("change"), "other")
                                                                   for i in items if not i.get("unverified"))],
    }


def focused(items, focus=None):
    """The cards behind one counter: "verified", "unverified", or a kind of change ("price up")."""
    if focus == "verified":
        return [i for i in items if not i.get("unverified")]
    if focus == "unverified":
        return [i for i in items if i.get("unverified")]
    if focus in set(CHANGE_LABELS.values()) | {"other"}:
        return [i for i in items if not i.get("unverified") and CHANGE_LABELS.get(i.get("change"), "other") == focus]
    return items


def summary_strip(summary, days, competitor, focus):
    """The counters above the feed, as stat tiles; each one is a link that shows the cards it counts."""
    def tile(text, n, key=None, value=None):
        query = {"days": days, "competitor": competitor or "", "focus": ""}
        if key:
            query[key] = value
        on = not focus if key is None else (focus if key == "focus" else competitor) == value
        href = "/?" + "&".join(f"{k}={quote(str(v))}" for k, v in query.items() if v)
        return (f"<a class='tile big{' on' if on else ''}' href='{esc(href)}'>"
                f"<span class='n'>{n}</span><span class='t'>{esc(text)}</span></a>")
    main = [tile("All changes", summary["total"]), tile("Verified", summary["verified"], "focus", "verified"),
            tile("Unverified rumors", summary["unverified"], "focus", "unverified")]
    return f"<div class='strip'><div class='tiles'>{''.join(main)}</div></div>"


def competitors_in(runs, snapshot):
    names = {i.get("competitor") for r in runs for i in r["items"]} | {p["competitor"] for p in (snapshot or {}).get("pages", [])}
    return sorted((n for n in names if n), key=str.lower)


def filter_form(action, competitors, competitor, days=None):
    """A plain GET form: a company dropdown, and on Changes a time range (default last 7 days)."""
    option = lambda value, text, chosen: f"<option value='{esc(value)}'{' selected' if chosen else ''}>{esc(text)}</option>"  # noqa: E731
    names = option("", "All companies", not competitor) + "".join(option(n, n, n == competitor) for n in competitors)
    period = ("<select name='days'>" + "".join(option(k, v, k == days) for k, v in RANGES.items()) + "</select> ") if days else ""
    return f"<form class='filters' method='get' action='{action}'>{period}<select name='competitor'>{names}</select> <button>Show</button></form>"


PAGE_FIELDS = ("competitor", "view", "url", "fetched_at", "ok", "error", "opens_on", "plans", "tables")


def run_if_due(every_hours, now=None):
    """Start a live run if the last one started at least every_hours ago (or there's none).

    Returns what happened: "ran", "not due" or "busy" (a run is already going).
    A run that crashes is logged and the next check tries again.
    """
    now = now or datetime.now(timezone.utc)
    last = store().runs(1)
    due = (now - timedelta(hours=every_hours, minutes=-5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if last and last[0]["run"]["started_at"] > due:
        return "not due"
    if not _running.acquire(blocking=False):
        return "busy"
    try:
        run_now(trigger="schedule")
    except Exception as exc:  # never kill the scheduler; the run log shows the gap
        print(f"scheduled run failed: {exc.__class__.__name__}: {exc}", flush=True)
    finally:
        _running.release()
    return "ran"


def _schedule(every_hours):
    while True:
        run_if_due(every_hours)
        time.sleep(CHECK_EVERY_S)


@app.get("/", response_class=HTMLResponse)
def changes(days: str = "7", competitor: str = None, focus: str = None):
    days = days if days in RANGES else "7"
    runs = store().runs()
    if not runs:
        return page("What changed in competitors' pricing", "<p>No runs yet.</p>")
    in_filter = changes_in(runs, days, competitor)
    items = focused(in_filter, focus)
    last = runs[0]["run"]
    failed = [label(p) for p in last.get("pages", []) if not p["ok"]]
    status = f'<span class="failed">couldn\'t read: {esc(", ".join(failed))}</span> · ' if failed else ""
    shown = f"{len(items)} change{'s' if len(items) != 1 else ''} · {RANGES[days].lower()} · {esc(competitor or 'all companies')}"
    empty = "<p>No pricing changes for this filter. Try a longer time range.</p>"
    body = (HOW_CHANGES + filter_form("/", competitors_in(runs, (store().snapshots(1) or [None])[0]), competitor, days)
            + summary_strip(summary_of(in_filter), days, competitor, focus)
            + f'<p class="meta">{status}{shown}</p>' + ("".join(map(render_item, items)) or empty))
    return page("What changed in competitors' pricing", body)


@app.get("/pricing", response_class=HTMLResponse)
def pricing(competitor: str = None):
    latest = store().snapshots(1)
    if not latest:
        return page("Current pricing", "<p>No runs yet.</p>")
    parts = [filter_form("/pricing", competitors_in([], latest[0]), competitor)]
    for p in latest[0]["pages"]:
        if competitor and p["competitor"] != competitor:
            continue
        opens = f" · the page opens on this view" if p.get("view") and p.get("opens_on") == p["view"] else ""
        head = f"<h2>{esc(label(p))}</h2><p class='meta'>{link(p['url'])} · checked {esc(p['fetched_at'])}{opens}</p>"
        if not p["ok"]:
            parts.append(head + f'<p class="failed">Couldn\'t read this page at {esc(p["fetched_at"])}: {esc(p["error"])}. '
                         "Older prices aren't shown as current.</p>")
            continue
        rows = "".join(
            f"<tr><td>{esc(plan['name'])}</td><td>{esc(plan['price'])}"
            + (f" <s>{esc(plan['list_price'])}</s>" if plan.get("list_price") else "")
            + f"</td><td>{esc(plan.get('billing'))}</td><td><ul>{''.join(f'<li>{esc(line)}</li>' for line in plan['includes'])}</ul>"
            + (f"<details><summary>{len(plan['options'])} options in the page's dropdown</summary><ul>"
               + "".join(f"<li>{esc(option)}</li>" for option in plan["options"]) + "</ul></details>" if plan.get("options") else "")
            + "</td></tr>"
            for plan in p["plans"]
        )
        parts.append(head + f"<table><tr><th>Plan</th><th>Price</th><th>Billing</th><th>Includes</th></tr>{rows}</table>")
        for table in p.get("tables") or []:
            header = "".join(f"<th>{esc(column)}</th>" for column in table["columns"])
            body = "".join(f"<tr><td>{esc(row['label'])}</td>" + "".join(f"<td>{esc(v)}</td>" for v in row["values"]) + "</tr>"
                           for row in table["rows"])
            parts.append(f"<h3>{esc(p['competitor'])}: {esc(table['title'])}</h3><table><tr><th></th>{header}</tr>{body}</table>")
    note = "<p class='meta'>As written on each competitor's page; no conversion between their units.</p>"
    return page("Current pricing", note + "".join(parts))


READERS = {"ai": "read with AI, every price checked against the page text", "plain": "read with the plain reader"}


def run_summary(result):
    """What a run read, found and decided, as data: the run log's Details and /api/runs share it.
    Everything comes from the saved run; the reasons are the rules in core/trust.py, in words."""
    run, items = result["run"], result["items"]
    rumors = sum(1 for i in items if i.get("unverified"))
    return {
        "read": [f"{label(p)}: couldn't read (see errors); not compared." if not p["ok"] else
                 f"{label(p)}: {p.get('plans', 0)} plans, {p.get('tables', 0)} tables, {READERS.get(p.get('reader'), 'read')}."
                 for p in run.get("pages", [])],
        "compared": "Each page was compared with its last good reading.",
        "notes": run.get("notes", []),
        "found": (f"{len(items) - rumors} change{'s' if len(items) - rumors != 1 else ''} on the pricing pages and "
                  f"{rumors} pricing rumor{'s' if rumors != 1 else ''} elsewhere."),
        "decided": [{"headline": i.get("headline"), "competitor": i.get("competitor"), "confidence": i["confidence"],
                     "unverified": bool(i.get("unverified")),
                     "rule": SOURCE_RULES.get(i.get("source_kind"), "").format(c=i.get("competitor")),
                     "next_step": (i.get("steps") or [i["action"]])[0]} for i in items],
        "skipped": [f"{s['id']}: {s['reason']}" for s in result.get("skipped", [])],
        "errors": run["errors"],
    }


def run_details(result):
    """The run's summary, collapsed under its row in the run log."""
    s = run_summary(result)
    li = lambda lines: "".join(f"<li>{esc(line)}</li>" for line in lines)  # noqa: E731
    decisions = "".join(f"<li><b>{esc(d['headline'])}</b><br><span class='meta'>{esc(d['rule'])} Next step: {esc(d['next_step'])}</span></li>"
                        for d in s["decided"])
    parts = [
        f"<p><b>Read.</b></p><ul>{li(s['read']) or '<li>No pages recorded for this run.</li>'}</ul>",
        f"<p><b>Compared.</b> {esc(s['compared'])}</p>" + (f"<ul>{li(s['notes'])}</ul>" if s["notes"] else ""),
        f"<p><b>Found</b> {esc(s['found'])}</p>",
        f"<p><b>Decided.</b></p><ul>{decisions}</ul>" if decisions else "",
        f"<p><b>Skipped.</b></p><ul>{li(s['skipped'])}</ul>" if s["skipped"] else "",
        f"<p><b>Errors.</b></p><ul>{li(s['errors'])}</ul>" if s["errors"] else "",
    ]
    return f"<details><summary>Details</summary><div class='how'>{''.join(parts)}</div></details>"


@app.get("/runs", response_class=HTMLResponse)
def runs():
    rows = ""
    for result in store().runs(100):
        run = result["run"]
        pages = ", ".join(f"{label(p)} {'ok' if p['ok'] else 'FAILED'}" for p in run.get("pages", []))
        errors = "".join(f"<li>{esc(e)}</li>" for e in run["errors"])
        rows += (f"<tr><td>{esc(run['started_at'])}</td><td>{esc(run.get('trigger') or '—')}</td><td>{esc(pages)}</td><td>{len(result['items'])}</td>"
                 f"<td>${run['cost_usd']:.4f}</td><td><ul>{errors}</ul></td></tr>"
                 f"<tr class='details'><td colspan='6'>{run_details(result)}</td></tr>")
    form = ("<form method='post' action='/check' onsubmit=\"this.querySelector('button').textContent='Checking… about two minutes'\">"
            f"<button>Check now</button> <span class='meta'>Anyone can start a check, at most once every {CHECK_NOW_EVERY_MIN} minutes.</span></form>")
    table = f"<table><tr><th>Started</th><th>Started by</th><th>Pages</th><th>Changes</th><th>Cost</th><th>Errors</th></tr>{rows}</table>"
    return page("Run log", form + (table if rows else "<p>No runs yet.</p>"))


CHECK_NOW_EVERY_MIN = 30


def check(background=False):
    """Check now, for the page and the API: no token, so reviewers can try it, but at most one run every
    CHECK_NOW_EVERY_MIN minutes (whatever started the last one), which caps the cost (D29).

    Returns (status, last check's started_at): "off", "busy", "too soon", "started" (background) or "done".
    """
    if not os.environ.get("RUN_TOKEN"):
        return "off", None
    if not _running.acquire(blocking=False):
        return "busy", None
    try:
        last = store().runs(1)
        recent = (datetime.now(timezone.utc) - timedelta(minutes=CHECK_NOW_EVERY_MIN)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if last and last[0]["run"]["started_at"] > recent:
            _running.release()
            return "too soon", last[0]["run"]["started_at"]
    except Exception:
        _running.release()
        raise
    if background:  # answer the API at once; the run takes about two minutes
        threading.Thread(target=_check_in_background, daemon=True).start()
        return "started", None
    try:
        run_now(trigger="manual")
    finally:
        _running.release()
    return "done", None


def _check_in_background():
    try:
        run_now(trigger="manual")
    except Exception as exc:  # the run log shows the gap
        print(f"check now failed: {exc.__class__.__name__}: {exc}", flush=True)
    finally:
        _running.release()


@app.post("/check", response_class=HTMLResponse)
def check_now():
    status, last = check()
    if status == "off":
        return page("Check now", "<p>Runs are switched off on this server.</p>")
    if status == "busy":
        return page("Check now", "<p>A check is already running. It takes about two minutes; then see <a href='/'>Changes</a>.</p>")
    if status == "too soon":
        return page("Check now", f"<p>The last check started at {esc(last)}. Check now works at most once "
                    f"every {CHECK_NOW_EVERY_MIN} minutes; its results are on <a href='/'>Changes</a>.</p>")
    return RedirectResponse("/", status_code=303)


CHECK_ANSWERS = {
    "started": (202, "Checking the four pricing pages. It takes about two minutes; the new run then appears in /api/runs."),
    "busy": (409, "A check is already running. It takes about two minutes."),
    "too soon": (429, f"Check now works at most once every {CHECK_NOW_EVERY_MIN} minutes."),
    "off": (503, "Runs are switched off on this server."),
}


@app.get("/api/check")
def api_check_status():
    """Whether a run is going now (from any trigger), so the run log can show it in progress."""
    current = _current
    return {"running": current is not None, "started_at": current and current["started_at"],
            "trigger": current and current["trigger"]}


@app.post("/api/check")
def api_check():
    """Check now for the Base44 front end: starts a run and answers at once."""
    status, last = check(background=True)
    code, message = CHECK_ANSWERS[status]
    answer = {"status": status, "message": message, "last_check": last}
    if last:
        answer["next_allowed_at"] = (datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ")
                                     + timedelta(minutes=CHECK_NOW_EVERY_MIN)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return JSONResponse(answer, status_code=code)


@app.post("/run")
def run(token: str = Form(None), authorization: str = Header(None), unless_ran_within_hours: float = None):
    expected = os.environ.get("RUN_TOKEN")
    given = token or (authorization or "").removeprefix("Bearer ").strip()
    if not expected or not given or not hmac.compare_digest(given, expected):
        return JSONResponse({"error": "a valid run token is needed"}, status_code=403)
    if unless_ran_within_hours is not None:
        last = store().runs(1)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=unless_ran_within_hours)
        if last and last[0]["run"]["started_at"] > cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"):
            return JSONResponse({"skipped": f"last run started at {last[0]['run']['started_at']}"})
    if not _running.acquire(blocking=False):
        return JSONResponse({"error": "a run is already in progress"}, status_code=409)
    try:
        # The Check now form sends the token as a field; GitHub's backup workflow asks to skip a recent run.
        trigger = "manual" if token else "backup schedule" if unless_ran_within_hours is not None else "API"
        result = run_now(trigger=trigger)
    finally:
        _running.release()
    if token:  # the Check now form
        return RedirectResponse("/", status_code=303)
    summary = {"started_at": result["run"]["started_at"], "items": len(result["items"]),
               "errors": result["run"]["errors"], "cost_usd": result["run"]["cost_usd"]}
    return JSONResponse(summary)


# How confidence is set, the same for live runs and test uploads (core/trust.py).
CONFIDENCE = ("<li><b>Confidence comes only from where a claim was seen</b>, never from guessing whether it's true: "
              "the competitor's own pricing page 0.9; another page on their site 0.6; a third party 0.4, unverified; "
              "a sponsored, ad, forum or anonymous source 0.2, unverified.</li>")

HOW_CHANGES = ("<details class='how'><summary><b>How this works</b></summary><ul>"
               "<li>Every 6 hours the app reads each competitor's pricing page and compares it with the last check. "
               "Each difference becomes a card, quoted from the page.</li>"
               "<li>It also looks for pricing rumors on Hacker News. Those cards are unverified and show what the "
               "pricing page said at the same check.</li>" + CONFIDENCE + "</ul></details>")

TEST_INTRO = ("<details class='how'><summary><b>How this works</b></summary><ul>"
              "<li>A test runs a file of signals (like the brief's cases.json) through the same rules as the live watch.</li>"
              "<li>Each signal is a claim someone saw, already saying what changed. So the test doesn't compare with the "
              "current pricing pages, and the same file always gives the same result.</li>" + CONFIDENCE +
              "<li>Pricing signals become cards; ads and launches are skipped with a reason.</li>"
              "<li>Nothing is saved: the other tabs don't change.</li></ul></details>"
              "<form method='post' action='/test' enctype='multipart/form-data'><input type='file' name='cases' required> "
              "<button>Run</button></form>")


@app.get("/test", response_class=HTMLResponse)
def test_form():
    return page("Test upload", TEST_INTRO)


async def run_upload(cases):
    """Run an uploaded cases file through the core, as ./run does. Returns (input, result)."""
    try:
        data = json.loads(await cases.read())
        error = None
    except ValueError as exc:
        data, error = {}, f"Couldn't read the upload: {exc.__class__.__name__}"
    result = process(data)
    if error:
        result["run"]["errors"].insert(0, error)
    return data, result


@app.post("/test")
async def test_upload(cases: UploadFile, format: str = None):
    data, result = await run_upload(cases)
    body = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if format == "json":
        return Response(body, media_type="application/json", headers={"Content-Disposition": "attachment; filename=result.json"})
    return test_results(data, result, body)


# Why a source got its confidence: the rule in core/trust.py, in words.
SOURCE_RULES = {
    "own_pricing_page": "From {c}'s own pricing page, so confidence 0.9.",
    "own_site_other_page": "From {c}'s own site but not its pricing page, so confidence 0.6 and \"confirm on the pricing page\".",
    "third_party": "From a third party, not {c}'s own site, so confidence 0.4 and labelled unverified.",
    "sponsored_or_anonymous": "From a sponsored, ad, forum or anonymous source, so confidence 0.2 and labelled unverified.",
}


def test_rows(data, result):
    """One row per input id: what it led to (an item or a skip) and why, by the rules."""
    signals = data.get("signals") if isinstance(data, dict) and isinstance(data.get("signals"), list) else []
    item_of = {sid: item for item in result["items"] for sid in item["source_ids"]}
    skip_of = {s["id"]: s["reason"] for s in result["skipped"]}
    rows, seen = [], set()
    for signal in signals:
        sid = signal.get("id") if isinstance(signal, dict) else None
        if sid is None or sid in seen:
            continue  # listed under errors
        seen.add(sid)
        item = item_of.get(sid)
        if item:
            row = {"result": "item", "unverified": bool(item.get("unverified")), "headline": item.get("headline"),
                   "why": [SOURCE_RULES.get(item.get("source_kind"), "").format(c=item.get("competitor"))]}
        else:
            row = {"result": "skipped", "unverified": False, "headline": None, "why": [skip_of.get(sid, "")]}
        if hides_text(signal.get("text")):
            row["why"].append("Its text has a hidden part; it was dropped from the quote and not followed (signal text is data).")
        mentions = re.compile(rf"(?<![\w-]){re.escape(str(sid))}(?![\w])|item-{re.escape(str(sid))}\b")
        row["why"] = [w for w in row["why"] + [e for e in result["run"]["errors"] if mentions.search(e)] if w]
        rows.append({"id": sid, "competitor": signal.get("competitor"), "type": signal.get("type"), **row})
    summary = {"signals": len(signals), "items": len(result["items"]), "skipped": len(result["skipped"]),
               "errors": len(result["run"]["errors"])}
    return summary, rows


def test_results(data, result, body):
    """The test result under the upload form: a summary, then one row per input id saying what it
    led to and the rule behind it, then the run's errors and the items as cards, as on Changes."""
    counts, table = test_rows(data, result)
    errors = result["run"]["errors"]
    rows = ""
    for r in table:
        badge = ' <span class="badge unverified">unverified</span>' if r["unverified"] else ""
        outcome = f"<b>Item</b>{badge}<br>{esc(r['headline'])}" if r["result"] == "item" else "<b>Skipped</b>"
        rows += (f"<tr><td>{esc(r['id'])}</td><td>{esc(r['competitor'])}<br><span class='meta'>{esc(r['type'])}</span></td>"
                 f"<td>{outcome}</td><td>{'<br>'.join(esc(w) for w in r['why'])}</td></tr>")
    summary = (f"<p><b>{counts['signals']} signals in the file → {counts['items']} items, {counts['skipped']} skipped, "
               f"{counts['errors']} errors.</b> Every id with a signal appears once: in an item or skipped.</p>")
    download = (f"<p><a download='result.json' href='data:application/json;base64,"
                f"{base64.b64encode(body.encode()).decode()}'>Download result.json</a></p>")
    parts = [TEST_INTRO, "<h2>Result</h2>", summary, download, "<h3>What each input led to, and why</h3>"]
    parts.append(f"<table><tr><th>Id</th><th>Competitor</th><th>Result</th><th>Why</th></tr>{rows}</table>" if rows else "<p>No signals with an id.</p>")
    if errors:
        parts.append("<h3>Errors in the file</h3><ul>" + "".join(f"<li>{esc(e)}</li>" for e in errors) + "</ul>")
    parts.append("<h3>Items, as Maya would see them</h3>" + ("".join(map(render_item, result["items"])) or "<p>No items.</p>"))
    return page("Test upload", "".join(parts))


@app.post("/api/test")
async def api_test(cases: UploadFile):
    """Test upload for the Base44 front end: the same core and rows as the Test upload page. Saves nothing.
    `result` is exactly what ./run writes for this file."""
    data, result = await run_upload(cases)
    summary, rows = test_rows(data, result)
    return {"summary": summary, "rows": rows, "result": result}


@app.get("/api/changes")
def api_changes(days: str = "7", competitor: str = None, focus: str = None):
    """?days=7|30|all (default 7), ?competitor=Lovable and ?focus=verified|unverified|<kind of change>,
    as on the Changes page. `summary` counts the cards in the time range and company, before focus."""
    runs = store().runs()
    last = runs[0]["run"] if runs else None
    return {
        "last_check": last["started_at"] if last else None,
        "failed_pages": [label(p) for p in last.get("pages", []) if not p["ok"]] if last else [],
        "competitors": competitors_in(runs, (store().snapshots(1) or [None])[0]),
        "summary": summary_of(changes_in(runs, days, competitor)),
        "items": focused(changes_in(runs, days, competitor), focus),
    }


@app.get("/api/pricing")
def api_pricing(competitor: str = None):
    latest = store().snapshots(1)
    pages = [p for p in (latest[0]["pages"] if latest else []) if not competitor or p["competitor"] == competitor]
    return {
        "taken_at": latest[0].get("taken_at") if latest else None,
        "pages": [dict({key: p.get(key) for key in PAGE_FIELDS}, label=label(p)) for p in pages],
    }


@app.get("/api/runs")
def api_runs():
    return [
        {"started_at": r["run"]["started_at"], "trigger": r["run"].get("trigger"), "changes": len(r["items"]), "cost_usd": r["run"]["cost_usd"],
         "errors": r["run"]["errors"], "pages": [{"label": label(p), "ok": p["ok"]} for p in r["run"].get("pages", [])],
         "details": run_summary(r)}
        for r in store().runs(100)
    ]


@app.get("/health")
def health():
    return {"ok": True}
