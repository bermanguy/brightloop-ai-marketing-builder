"""The web app: what changed, current pricing, the run log, "Check now", and the test upload.

    uvicorn pricewatch.web:app

Plain server-rendered HTML, no front-end build. Every value shown comes from the
store (snapshots and run results), written as it appears on the competitor's page.

POST /run starts a live run. It needs RUN_TOKEN (as "Authorization: Bearer ..."
from the schedule, or typed into the Check now form); without RUN_TOKEN set,
runs are switched off and the app only shows what's stored.

GitHub delays and sometimes drops scheduled workflows, so the schedule calls
every hour with ?unless_ran_within_hours=5.5 and the app keeps the 6-hour pace:
a dropped call costs an hour, not six.
"""

import hmac
import html
import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Form, Header, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .core import process
from .live import run_live
from .sources.fetch import label
from .store import Store

app = FastAPI(title="Brightloop pricing watch", docs_url=None, redoc_url=None)
_store = None
_running = threading.Lock()
RECENT_RUNS = 30


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
.unverified{background:#fde2b8} .failed{color:#a00} table{border-collapse:collapse;width:100%;margin-bottom:24px}
td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left;vertical-align:top;font-size:.92rem} ul{margin:0;padding-left:18px}
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
    return (
        f'<div class="item"><div class="meta">{esc(item.get("competitor"))} · seen {esc(item.get("seen_at"))} · '
        f'{badge}confidence {item["confidence"]}</div><p><b>{esc(item["action"])}</b></p><p>{esc(item["why"])}</p>'
        f"<ul>{sources}</ul></div>"
    )


@app.get("/", response_class=HTMLResponse)
def changes():
    runs = store().runs(RECENT_RUNS)
    items = sorted((item for run in runs for item in run["items"]), key=lambda i: i.get("seen_at") or "", reverse=True)
    if not runs:
        body = "<p>No runs yet.</p>"
    else:
        last = runs[0]["run"]
        failed = [label(p) for p in last.get("pages", []) if not p["ok"]]
        status = f"Last check {esc(last['started_at'])}" + (f' · <span class="failed">couldn\'t read: {esc(", ".join(failed))}</span>' if failed else "")
        body = f'<p class="meta">{status}</p>' + ("".join(map(render_item, items)) or "<p>No pricing changes found yet.</p>")
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


@app.get("/test", response_class=HTMLResponse)
def test_form():
    return page("Test upload", "<p>Upload a cases.json; you get result.json back, from the same core as <code>./run</code>.</p>"
                "<form method='post' action='/test' enctype='multipart/form-data'><input type='file' name='cases' required> "
                "<button>Run</button></form>")


@app.post("/test")
async def test_upload(cases: UploadFile):
    try:
        data = json.loads(await cases.read())
        error = None
    except ValueError as exc:
        data, error = {}, f"Couldn't read the upload: {exc.__class__.__name__}"
    result = process(data)
    if error:
        result["run"]["errors"].insert(0, error)
    body = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    return Response(body, media_type="application/json", headers={"Content-Disposition": "attachment; filename=result.json"})


@app.get("/health")
def health():
    return {"ok": True}
