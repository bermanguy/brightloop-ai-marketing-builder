"""Live fetch, tested offline: the network calls are replaced, so CI needs no browser or internet."""

import json

import pytest

from pricewatch.sources import fetch

PRICING_HTML = """<html><head><title>x</title><style>.a{}</style></head><body>
<script>var price = "$999";</script>
<h2>Plus</h2><p><span>$30</span><del>$90</del>/user/month</p>
<ul><li>10M tokens/month</li><li>Custom&nbsp;domains</li></ul>
<template><p>$1 hidden</p></template>
</body></html>"""


def test_visible_text_drops_scripts_and_keeps_blocks():
    text = fetch.visible_text(PRICING_HTML)
    assert "$999" not in text and "$1 hidden" not in text and "x" not in text.split("\n")
    assert text.split("\n") == ["Plus", "$30 ~~$90~~ /user/month", "10M tokens/month", "Custom domains"]


@pytest.mark.parametrize(
    "status, text, problem",
    [
        (200, "Pro $25 / month", None),
        (403, "Pro $25 / month", "HTTP 403"),
        (200, "Sorry, you have been blocked. $5", "blocked or challenge page"),
        (200, "Just a moment...", "blocked or challenge page"),
        (200, "Plans\nPro\nGet started", "no prices found on the page (layout change, or plans not rendered)"),
    ],
)
def test_check_page(status, text, problem):
    assert fetch.check_page(status, text) == problem


def test_every_competitor_uses_its_agreed_method():
    # D14: Lovable needs a browser; Replit blocks headless browsers, so HTTP only.
    assert {name: page["method"] for name, page in fetch.PAGES.items()} == {
        "Lovable": "browser", "Bolt": "http", "Replit": "http", "v0": "http",
    }


def test_good_page(monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_http", lambda url: (200, PRICING_HTML))
    page = fetch.fetch_page("Bolt")
    assert page["ok"] and page["error"] is None and page["status"] == 200
    assert page["url"] == "https://bolt.new/pricing" and page["fetched_at"].endswith("Z")
    assert "$30" in page["text"]


def test_a_failing_page_is_reported_and_does_not_stop_the_others(monkeypatch):
    def flaky(url):
        if "replit" in url:
            raise TimeoutError("timed out")
        return 200, PRICING_HTML

    monkeypatch.setattr(fetch, "_fetch_http", flaky)
    monkeypatch.setattr(fetch, "_fetch_browser", lambda url: (200, PRICING_HTML))
    pages = {page["competitor"]: page for page in fetch.fetch_all()}
    assert set(pages) == {"Lovable", "Bolt", "Replit", "v0"}
    assert pages["Replit"]["ok"] is False and pages["Replit"]["error"] == "TimeoutError: timed out"
    assert pages["Replit"]["text"] == ""  # never older data in its place (D12)
    assert all(pages[name]["ok"] for name in ("Lovable", "Bolt", "v0"))


def test_blocked_page_is_a_failure(monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_http", lambda url: (200, "<p>Sorry, you have been blocked</p>"))
    page = fetch.fetch_page("Replit")
    assert page["ok"] is False and page["error"] == "blocked or challenge page"


def test_save_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_http", lambda url: (200, PRICING_HTML))
    fetch.save_pages([fetch.fetch_page("v0")], tmp_path)
    assert (tmp_path / "v0.html").read_text() == PRICING_HTML
    meta = json.loads((tmp_path / "v0.json").read_text())
    assert "html" not in meta and meta["ok"] and "$30" in meta["text"]


def test_css_line_through_counts_as_struck():
    html = '<p><span class="opacity-75 line-through">$20</span> $18 / month</p><p><del><span>$9</span>0</del></p>'
    assert fetch.visible_text(html).split("\n") == ["~~$20~~ $18 / month", "~~$90~~"]
