"""Live source, step 2 (plain-code version): read plans and prices from a fetched page's text.

This is the keyless reader. It relies on the shape all four pricing pages
share today: a short plan name, then a line that starts with the price, then
the plan's details until the next plan. Every value it returns is a line of
the page, so each one is its own word-for-word quote (R4).

A page whose plans can't be read comes back failed, never guessed (D12).
"""

import re

# A price line starts with the amount: "$25", "$18*/month", "~~$20~~ $18 / month, billed annually".
PRICE_LINE = re.compile(r"^(?:~~\$[\d.,]+~~\s*)?\$\d")
# Plans with no number.
NO_NUMBER_PRICES = {"custom", "platform fee"}
AMOUNT = re.compile(r"(~~)?\$(\d[\d,]*(?:\.\d+)?)(?:~~)?")
# "/ month" after a price, not "tokens/month" inside a feature.
PERIOD = re.compile(r"(?:^|[\s\d*])/\s*(?:user\s*/\s*)?(?:month|mo|year|yr)\b|billed (?:annually|monthly|yearly)|per (?:month|year)", re.I)
BADGES = re.compile(r"^(?:most popular|popular|recommended|best value|new)\s*", re.I)
CTA = re.compile(r"^(?:get|start|try|upgrade|book|contact|select|sign up|buy|choose)\b", re.I)
# Where the plan cards end: footnotes, comparison tables, FAQs, other sections.
END_OF_PLANS = re.compile(
    r"^(?:\*|frequently asked|trusted by|compare\b|.*plan comparison|security and compliance|model pricing|"
    r"all prices shown|lovable for )",
    re.I,
)
MAX_PLAN_LINES = 30


def _is_price_line(line):
    """A line that is a price, not a feature that starts with one ("$20 towards more powerful models")."""
    if line.strip().lower() in NO_NUMBER_PRICES:
        return True
    if not PRICE_LINE.match(line):
        return False
    remainder = AMOUNT.sub("", line).strip(" *")
    return not remainder or bool(PERIOD.match(remainder) or re.match(r",?\s*billed\b", remainder, re.I))


def _plan_name(lines, price_index, floor):
    """The plan's name: the nearest short line above its price, skipping taglines and badges."""
    for index in range(price_index - 1, max(floor, price_index - 4) - 1, -1):
        name = BADGES.sub("", lines[index]).strip()
        if name and len(name) <= 25 and len(name.split()) <= 3 and not CTA.match(name):
            return name, index
    return None, None


def _price(line):
    """(price, list_price) from a price line. A struck-through amount is the list price, never the price."""
    if line.strip().lower() in NO_NUMBER_PRICES:
        return line.strip(), None
    price = list_price = None
    for struck, amount in AMOUNT.findall(line):
        if struck and list_price is None:
            list_price = f"${amount}"
        elif not struck and price is None:
            price = f"${amount}"
    return price, list_price


def extract_plans(text):
    """Return the plans found in a page's visible text (see fetch.visible_text)."""
    lines = [line for line in (text or "").split("\n") if line.strip()]
    starts = []  # (name, name_index, price_index)
    floor = 0
    for index, line in enumerate(lines):
        if starts and END_OF_PLANS.match(line):
            end = index
            break
        if _is_price_line(line):
            name, name_index = _plan_name(lines, index, floor)
            if name:
                starts.append((name, name_index, index))
                floor = index + 1
    else:
        end = len(lines)

    plans = []
    for number, (name, name_index, price_index) in enumerate(starts):
        stop = starts[number + 1][1] if number + 1 < len(starts) else end
        stop = min(stop, price_index + MAX_PLAN_LINES)
        price_line = lines[price_index]
        details = lines[price_index + 1 : stop]
        price, list_price = _price(price_line)
        remainder = AMOUNT.sub("", price_line).strip(" *")
        billing = ([remainder] if PERIOD.search(remainder) else []) + [d for d in details if PERIOD.search(d)]
        includes = [d for d in details if not PERIOD.search(d) and not CTA.match(d)]
        plans.append(
            {
                "name": name,
                "price": price,
                "list_price": list_price,
                "billing": "; ".join(billing) or None,
                "includes": includes,
                "quotes": [lines[name_index], price_line] + details,
            }
        )
    return plans


def unquoted(plan, text):
    """Quotes of a plan that aren't word for word in the page text. Empty means the plan checks out.

    Every value (name, prices, billing, what's included) must sit inside the
    plan's quotes. The plain reader passes by construction; this is the guard
    the AI reader must pass too.
    """
    missing = [quote for quote in plan["quotes"] if quote not in text]
    quoted = "\n".join(plan["quotes"])
    values = [plan["name"], plan["price"], plan["list_price"], *plan["includes"]]
    values += (plan["billing"] or "").split("; ")
    for value in values:
        if value and value not in quoted:
            missing.append(value)
    return missing


def read_page(page):
    """Add plans to a fetched page (fetch.fetch_page). A page with no readable plans is marked failed."""
    result = {key: value for key, value in page.items() if key != "html"}
    result["plans"] = []
    if not page.get("ok"):
        return result
    plans = [plan for plan in extract_plans(page["text"]) if not unquoted(plan, page["text"])]
    if not plans:
        result["ok"] = False
        result["error"] = "no plans could be read from the page (layout change?)"
    result["plans"] = plans
    return result
