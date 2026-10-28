"""Snapshots and the run log, in Postgres (Neon) when DATABASE_URL is set, else SQLite.

Four tables, each row one JSON document:
- snapshots: every page's plans from one run, or why a page couldn't be read
- runs: the result of one run (items, skipped, run log), exactly as ./run writes it
- alerts: every alert sent (or held back by the settings), for the alert log
- settings: the alert settings changed in the app; the newest row is the one in use

SQLite needs nothing installed, so tests, ./proof and local runs use it.
"""

import json
import os
import sqlite3
from pathlib import Path

DEFAULT_SQLITE = Path("data") / "pricewatch.db"
PAGE_FIELDS = ("competitor", "view", "view_index", "opens_on", "url", "method", "fetched_at", "ok", "status", "error",
               "reader", "ai_error", "cost_usd", "plans", "tables")


class Store:
    def __init__(self, url=None):
        self.url = url or os.environ.get("DATABASE_URL") or str(DEFAULT_SQLITE)
        self.postgres = self.url.startswith(("postgres://", "postgresql://"))
        if self.postgres:
            key = "BIGSERIAL PRIMARY KEY"
        else:
            Path(self.url).parent.mkdir(parents=True, exist_ok=True)
            self.sqlite = sqlite3.connect(self.url, check_same_thread=False, isolation_level=None)
            key = "INTEGER PRIMARY KEY AUTOINCREMENT"
        for table in ("snapshots", "runs", "alerts", "settings"):
            self._sql(f"CREATE TABLE IF NOT EXISTS {table} (id {key}, at TEXT NOT NULL, doc TEXT NOT NULL)")

    def _sql(self, query, args=()):
        """Run one statement; return its rows. Postgres gets a fresh connection each time,
        because Neon closes idle connections when it scales to zero."""
        if not self.postgres:
            cursor = self.sqlite.execute(query, args)
            return cursor.fetchall() if cursor.description else []
        import psycopg

        with psycopg.connect(self.url, autocommit=True) as db:
            cursor = db.execute(query.replace("?", "%s"), args)
            return cursor.fetchall() if cursor.description else []

    def _add(self, table, at, doc):
        self._sql(f"INSERT INTO {table} (at, doc) VALUES (?, ?)", (at, json.dumps(doc, ensure_ascii=False)))

    def _newest(self, table, limit=None):
        query = f"SELECT doc FROM {table} ORDER BY at DESC, id DESC" + (f" LIMIT {int(limit)}" if limit else "")
        return [json.loads(row[0]) for row in self._sql(query)]

    # Snapshots

    def save_snapshot(self, taken_at, pages, rumors=()):
        """rumors: the Hacker News ids reported in this run, so later runs don't report them again."""
        self._add("snapshots", taken_at, {"taken_at": taken_at, "pages": [{k: p.get(k) for k in PAGE_FIELDS} for p in pages],
                                          "rumors": sorted(set(rumors))})

    def snapshots(self, limit=None):
        return self._newest("snapshots", limit)

    def last_good_pages(self):
        """{(competitor, view, reader): page} from the newest snapshot in which each page (or view) was read by that reader."""
        found = {}
        for snapshot in self.snapshots():
            for page in snapshot["pages"]:
                key = (page["competitor"], page.get("view"), page["reader"])
                if page.get("ok") and key not in found:
                    found[key] = page
        return found

    def seen_rumors(self):
        return {hn_id for snapshot in self.snapshots() for hn_id in snapshot.get("rumors") or []}

    # Run log

    def save_run(self, result):
        self._add("runs", result["run"]["started_at"], result)

    def runs(self, limit=None):
        return self._newest("runs", limit)

    # Alerts

    def save_alert(self, entry):
        self._add("alerts", entry["at"], entry)

    def alerts(self, limit=None):
        return self._newest("alerts", limit)

    def save_alert_settings(self, at, settings):
        self._add("settings", at, settings)

    def alert_settings(self):
        """The newest saved alert settings, or {} when none were saved (the environment's then)."""
        newest = self._newest("settings", 1)
        return newest[0] if newest else {}
