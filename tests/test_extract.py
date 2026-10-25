"""The plain-code plan reader, on the real pages saved on 2026-10-25 (fixtures/pages/2026-10-25)."""

import json
from pathlib import Path

import pytest

from pricewatch.sources.extract import extract_plans, read_page, unquoted

PAGES = Path(__file__).resolve().parent.parent / "fixtures" / "pages" / "2026-10-25"


def saved(competitor):
    return json.loads((PAGES / f"{competitor}.json").read_text())


def summary(competitor):
    return [(p["name"], p["price"], p["list_price"], p["billing"]) for p in read_page(saved(competitor))["plans"]]


# Read by hand from each page on 2026-10-25 (docs/pricing-pages.md), default view only (D14).
EXPECTED = {
    "lovable": [
        ("Free", "$0", None, None),
        ("Pro", "$25", None, "/ month"),
        ("Business", "$50", None, "/ month"),
        ("Enterprise", "Platform fee", None, None),
    ],
    "bolt": [
        ("Free", "$0", None, "/month"),
        ("Pro", "$18", None, "/month; Total of $216 ~~$300~~ / year; Billed annually"),
        ("Teams", "$27", None, "/month; Total of $324 ~~$360~~ / year; Per member, billed annually"),
        ("Enterprise", "Custom", None, None),
    ],
    "replit": [
        ("Core", "$18", "$20", "/ month, billed annually"),
        ("Pro", "$90", "$100", "/ month, billed annually"),
        ("Enterprise", "Custom", None, None),
    ],
    "v0": [
        ("Free", "$0", None, "/month"),
        ("Plus", "$30", "$90", "/user/month"),
        ("Business", "$100", None, "/user/month"),
        ("Enterprise", "Custom", None, None),
    ],
}


@pytest.mark.parametrize("competitor", EXPECTED)
def test_reads_every_plan_on_the_real_pages(competitor):
    assert summary(competitor) == EXPECTED[competitor]


@pytest.mark.parametrize("competitor", EXPECTED)
def test_every_value_is_quoted_word_for_word(competitor):
    page = saved(competitor)
    for plan in read_page(page)["plans"]:
        assert unquoted(plan, page["text"]) == []
        assert all(quote in page["text"] for quote in plan["quotes"])


def test_includes_what_the_plan_contains():
    pro = next(p for p in read_page(saved("lovable"))["plans"] if p["name"] == "Pro")
    assert "100 monthly credits" in pro["includes"]
    assert "Custom domains" in pro["includes"]
    assert "Get started" not in pro["includes"]  # buttons aren't plan contents


def test_comparison_tables_and_faqs_are_not_plans():
    names = [p["name"] for p in read_page(saved("bolt"))["plans"]]
    assert names == ["Free", "Pro", "Teams", "Enterprise"]
    enterprise = read_page(saved("lovable"))["plans"][-1]
    assert not any("Frequently asked" in line or "student" in line for line in enterprise["includes"])


def test_struck_price_is_never_the_price():
    plans = extract_plans("Plus\n$30 ~~$90~~ /user/month\nGet started\nPro\n~~$20~~ $18 / month, billed annually")
    assert [(p["price"], p["list_price"]) for p in plans] == [("$30", "$90"), ("$18", "$20")]


def test_feature_lines_starting_with_a_price_are_not_plans():
    plans = extract_plans("Core\n$18 / month\n$20 towards more powerful models\nPlan mode")
    assert [p["name"] for p in plans] == ["Core"]
    assert plans[0]["includes"] == ["$20 towards more powerful models", "Plan mode"]


def test_badges_are_not_plan_names():
    plans = extract_plans("MOST POPULARPro\n$18*/month\nTeams\nPopular\n$27*/month")
    assert [p["name"] for p in plans] == ["Pro", "Teams"]


def test_page_with_no_plans_is_failed_not_guessed():
    page = {"competitor": "Bolt", "ok": True, "error": None, "text": "Pricing\nCustom apps, no $100K project.\nSign in"}
    result = read_page(page)
    assert result["ok"] is False and result["plans"] == [] and "no plans" in result["error"]


def test_failed_fetch_stays_failed():
    result = read_page({"competitor": "Replit", "ok": False, "error": "blocked or challenge page", "text": "", "html": "x"})
    assert result["ok"] is False and result["error"] == "blocked or challenge page"
    assert "html" not in result


def test_a_plan_with_an_invented_value_is_rejected():
    # The guard the AI reader will also go through: a price not on the page is caught.
    text = "Pro\n$25 / month"
    invented = {"name": "Pro", "price": "$20", "list_price": None, "billing": "/ month", "includes": [], "quotes": ["Pro", "$25 / month"]}
    assert unquoted(invented, text) == ["$20"]
    misquoted = dict(invented, price="$25", quotes=["Pro", "$25 per month"])
    assert unquoted(misquoted, text) == ["$25 per month"]
