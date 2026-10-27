"""The web app: what changed, current pricing, the run log, "Check now", and the test upload.

    uvicorn pricewatch.web:app

Plain server-rendered HTML, no front-end build. Every value shown comes from the
store (snapshots and run results), written as it appears on the competitor's page.

POST /run starts a live run. It needs RUN_TOKEN (as "Authorization: Bearer ..."
from the schedule, or typed into the Check now form); without RUN_TOKEN set,
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
from contextlib import asynccontextmanager
import time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Form, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .core import process
from .live import run_live
from .sources.fetch import label
from .store import Store

@asynccontextmanager
async def lifespan(app):
    every = os.environ.get("SCHEDULE_EVERY_HOURS")
    if every:
        threading.Thread(target=_schedule, args=(float(every),), daemon=True).start()
    yield


app = FastAPI(title="Brightloop pricing watch", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
_store = None
_running = threading.Lock()
RECENT_RUNS = 30
CHECK_EVERY_S = 300


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
nav a{margin-right:16px} h1{font-size:1.4rem} .item{border-top:1px solid #ddd;padding:12px 0}
.meta{color:#555;font-size:.9rem} .badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.8rem;background:#eee}
.unverified{background:#fde2b8} .item h3{font-size:1.05rem;margin:6px 0} .why{color:#333} .sources{font-size:.9rem;color:#333;margin-bottom:8px} .label{font-weight:600;margin:8px 0 2px} .failed{color:#a00} .how{background:#f4f6f8;border-radius:6px;padding:10px 12px;margin-bottom:12px;font-size:.92rem} table{border-collapse:collapse;width:100%;margin-bottom:24px}
td:first-child{white-space:nowrap} td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left;vertical-align:top;font-size:.92rem} ul{margin:0;padding-left:18px}
"""


def page(title, body):
    nav = '<nav><a href="/">Changes</a><a href="/pricing">Current pricing</a><a href="/runs">Run log</a><a href="/test">Test upload</a></nav>'
    return HTMLResponse(
        f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)} · Pricing watch</title><style>{STYLE}</style></head><body>{nav}<h1>{esc(title)}</h1>{body}</body></html>"
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
        run_live(store())
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
def changes():
    runs = store().runs(RECENT_RUNS)
    items = recent_items(runs)
    if not runs:
        body = "<p>No runs yet.</p>"
    else:
        last = runs[0]["run"]
        failed = [label(p) for p in last.get("pages", []) if not p["ok"]]
        status = f"Last check {esc(last['started_at'])}" + (f' · <span class="failed">couldn\'t read: {esc(", ".join(failed))}</span>' if failed else "")
        body = HOW_CHANGES + f'<p class="meta">{status}</p>' + ("".join(map(render_item, items)) or "<p>No pricing changes found yet.</p>")
    return page("What changed in competitors' pricing", body)


@app.get("/pricing", response_class=HTMLResponse)
def pricing():
    latest = store().snapshots(1)
    if not latest:
        return page("Current pricing", "<p>No runs yet.</p>")
    parts = []
    for p in latest[0]["pages"]:
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


@app.get("/runs", response_class=HTMLResponse)
def runs():
    rows = ""
    for result in store().runs(100):
        run = result["run"]
        pages = ", ".join(f"{label(p)} {'ok' if p['ok'] else 'FAILED'}" for p in run.get("pages", []))
        errors = "".join(f"<li>{esc(e)}</li>" for e in run["errors"])
        rows += (f"<tr><td>{esc(run['started_at'])}</td><td>{esc(pages)}</td><td>{len(result['items'])}</td>"
                 f"<td>${run['cost_usd']:.4f}</td><td><ul>{errors}</ul></td></tr>")
    form = ("<form method='post' action='/run' onsubmit=\"this.querySelector('button').textContent='Checking… about two minutes'\">"
            "<input type='password' name='token' placeholder='Run token' required> <button>Check now</button></form>")
    table = f"<table><tr><th>Started</th><th>Pages</th><th>Changes</th><th>Cost</th><th>Errors</th></tr>{rows}</table>"
    return page("Run log", form + (table if rows else "<p>No runs yet.</p>"))


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
        result = run_live(store())
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

HOW_CHANGES = ("<div class='how'><b>How this works</b><ul>"
               "<li>Every 6 hours the app reads each competitor's pricing page and compares it with the last check. "
               "Each difference becomes a card, quoted from the page.</li>"
               "<li>It also looks for pricing rumors on Hacker News. Those cards are unverified and show what the "
               "pricing page said at the same check.</li>" + CONFIDENCE + "</ul></div>")

TEST_INTRO = ("<div class='how'><b>How this works</b><ul>"
              "<li>A test runs a file of signals (like the brief's cases.json) through the same rules as the live watch.</li>"
              "<li>Each signal is a claim someone saw, already saying what changed. So the test doesn't compare with the "
              "current pricing pages, and the same file always gives the same result.</li>" + CONFIDENCE +
              "<li>Pricing signals become cards; ads and launches are skipped with a reason.</li>"
              "<li>Nothing is saved: the other tabs don't change.</li></ul></div>"
              "<form method='post' action='/test' enctype='multipart/form-data'><input type='file' name='cases' required> "
              "<button>Run</button></form>")


@app.get("/test", response_class=HTMLResponse)
def test_form():
    return page("Test upload", TEST_INTRO)


@app.post("/test")
async def test_upload(cases: UploadFile, format: str = None):
    try:
        data = json.loads(await cases.read())
        error = None
    except ValueError as exc:
        data, error = {}, f"Couldn't read the upload: {exc.__class__.__name__}"
    result = process(data)
    if error:
        result["run"]["errors"].insert(0, error)
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


def test_results(data, result, body):
    """The test result under the upload form: a summary, then one row per input id saying what it
    led to and the rule behind it, then the run's errors and the items as cards, as on Changes."""
    signals = data.get("signals") if isinstance(data, dict) and isinstance(data.get("signals"), list) else []
    item_of = {sid: item for item in result["items"] for sid in item["source_ids"]}
    skip_of = {s["id"]: s["reason"] for s in result["skipped"]}
    errors = result["run"]["errors"]
    rows, seen = "", set()
    for signal in signals:
        sid = signal.get("id") if isinstance(signal, dict) else None
        if sid is None or sid in seen:
            continue  # listed under errors
        seen.add(sid)
        item = item_of.get(sid)
        if item:
            badge = ' <span class="badge unverified">unverified</span>' if item.get("unverified") else ""
            outcome = f"<b>Item</b>{badge}<br>{esc(item.get('headline'))}"
            why = [SOURCE_RULES.get(item.get("source_kind"), "").format(c=item.get("competitor"))]
        else:
            outcome, why = "<b>Skipped</b>", [skip_of.get(sid, "")]
        if "<!--" in str(signal.get("text")):
            why.append("Its text has a hidden comment; it was dropped from the quote and not followed (signal text is data).")
        mentions = re.compile(rf"(?<![\w-]){re.escape(str(sid))}(?![\w])|item-{re.escape(str(sid))}\b")
        why += [e for e in errors if mentions.search(e)]
        rows += (f"<tr><td>{esc(sid)}</td><td>{esc(signal.get('competitor'))}<br><span class='meta'>{esc(signal.get('type'))}</span></td>"
                 f"<td>{outcome}</td><td>{'<br>'.join(esc(w) for w in why if w)}</td></tr>")
    summary = (f"<p><b>{len(signals)} signals in the file → {len(result['items'])} items, {len(result['skipped'])} skipped, "
               f"{len(errors)} errors.</b> Every id with a signal appears once: in an item or skipped.</p>")
    download = (f"<p><a download='result.json' href='data:application/json;base64,"
                f"{base64.b64encode(body.encode()).decode()}'>Download result.json</a></p>")
    parts = [TEST_INTRO, "<h2>Result</h2>", summary, download, "<h3>What each input led to, and why</h3>"]
    parts.append(f"<table><tr><th>Id</th><th>Competitor</th><th>Result</th><th>Why</th></tr>{rows}</table>" if rows else "<p>No signals with an id.</p>")
    if errors:
        parts.append("<h3>Errors in the file</h3><ul>" + "".join(f"<li>{esc(e)}</li>" for e in errors) + "</ul>")
    parts.append("<h3>Items, as Maya would see them</h3>" + ("".join(map(render_item, result["items"])) or "<p>No items.</p>"))
    return page("Test upload", "".join(parts))


@app.get("/api/changes")
def api_changes():
    runs = store().runs(RECENT_RUNS)
    last = runs[0]["run"] if runs else None
    return {
        "last_check": last["started_at"] if last else None,
        "failed_pages": [label(p) for p in last.get("pages", []) if not p["ok"]] if last else [],
        "items": recent_items(runs),
    }


@app.get("/api/pricing")
def api_pricing():
    latest = store().snapshots(1)
    pages = latest[0]["pages"] if latest else []
    return {
        "taken_at": latest[0].get("taken_at") if latest else None,
        "pages": [dict({key: p.get(key) for key in PAGE_FIELDS}, label=label(p)) for p in pages],
    }


@app.get("/api/runs")
def api_runs():
    return [
        {"started_at": r["run"]["started_at"], "changes": len(r["items"]), "cost_usd": r["run"]["cost_usd"],
         "errors": r["run"]["errors"], "pages": [{"label": label(p), "ok": p["ok"]} for p in r["run"].get("pages", [])]}
        for r in store().runs(100)
    ]


@app.get("/health")
def health():
    return {"ok": True}
