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
    # Lovable needs a browser, and Lovable and Bolt hide a billing period behind a toggle the
    # browser clicks; Replit blocks headless browsers, so HTTP only (docs/pricing-pages.md).
    assert {name: page["method"] for name, page in fetch.PAGES.items()} == {
        "Lovable": "browser", "Bolt": "browser", "Replit": "http", "v0": "http",
    }
    assert [v[0] for v in fetch.PAGES["Bolt"]["views"]] == ["Monthly", "Yearly"]


def http(html, status=200):
    return lambda spec: {"status": status, "opens_on": None, "views": [{"view": None, "html": html, "dropdowns": []}]}


def browser(html, opens_on="Monthly"):
    views = [{"view": name, "html": html.replace("$30", price), "dropdowns": []} for name, price in (("Monthly", "$30"), ("Yearly", "$25"))]
    return lambda spec: {"status": 200, "opens_on": opens_on, "views": views}


def test_good_page(monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_http", http(PRICING_HTML))
    [page] = fetch.fetch_page("v0")
    assert page["ok"] and page["error"] is None and page["status"] == 200 and page["view"] is None
    assert page["url"] == "https://v0.app/pricing" and page["fetched_at"].endswith("Z")
    assert "$30" in page["text"] and fetch.label(page) == "v0"


def test_a_page_with_a_billing_toggle_gives_one_record_per_view(monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_browser", browser(PRICING_HTML))
    monthly, yearly = fetch.fetch_page("Bolt")
    assert (monthly["view"], yearly["view"]) == ("Monthly", "Yearly") and (monthly["view_index"], yearly["view_index"]) == (0, 1)
    assert "$30" in monthly["text"] and "$25" in yearly["text"]
    assert monthly["opens_on"] == yearly["opens_on"] == "Monthly"
    assert fetch.label(yearly) == "Bolt (Yearly)"


def test_a_failing_page_is_reported_and_does_not_stop_the_others(monkeypatch):
    def flaky(spec):
        if "replit" in spec["url"]:
            raise TimeoutError("timed out")
        return http(PRICING_HTML)(spec)

    def broken(spec):
        raise TimeoutError("Locator.click: Timeout 30000ms exceeded.")  # e.g. the toggle is gone

    monkeypatch.setattr(fetch, "_fetch_http", flaky)
    monkeypatch.setattr(fetch, "_fetch_browser", broken)
    pages = {fetch.label(page): page for page in fetch.fetch_all()}
    assert set(pages) == {"Lovable (Monthly)", "Lovable (Yearly)", "Bolt (Monthly)", "Bolt (Yearly)", "Replit", "v0"}
    assert pages["Replit"]["ok"] is False and pages["Replit"]["error"] == "TimeoutError: timed out"
    assert pages["Replit"]["text"] == ""  # never older data in its place (D12)
    assert pages["Bolt (Yearly)"]["ok"] is False and "Timeout" in pages["Bolt (Yearly)"]["error"]
    assert pages["v0"]["ok"]


def test_blocked_page_is_a_failure(monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_http", http("<p>Sorry, you have been blocked</p>"))
    [page] = fetch.fetch_page("Replit")
    assert page["ok"] is False and page["error"] == "blocked or challenge page"


def test_save_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_http", http(PRICING_HTML))
    monkeypatch.setattr(fetch, "_fetch_browser", browser(PRICING_HTML))
    fetch.save_pages(fetch.fetch_page("v0") + fetch.fetch_page("Bolt"), tmp_path)
    assert (tmp_path / "v0.html").read_text() == PRICING_HTML
    meta = json.loads((tmp_path / "v0.json").read_text())
    assert "html" not in meta and meta["ok"] and "$30" in meta["text"]
    assert "$25" in json.loads((tmp_path / "bolt-yearly.json").read_text())["text"]


def test_a_struck_price_split_over_lines_is_closed_on_its_own_line():
    # Lovable's yearly view: <span class="line-through">$25<br></span>
    assert fetch.visible_text('<p><span class="line-through">$25<br></span></p><p>$21</p>') == "~~$25~~\n$21"


def test_css_line_through_counts_as_struck():
    html = '<p><span class="opacity-75 line-through">$20</span> $18 / month</p><p><del><span>$9</span>0</del></p>'
    assert fetch.visible_text(html).split("\n") == ["~~$20~~ $18 / month", "~~$90~~"]
