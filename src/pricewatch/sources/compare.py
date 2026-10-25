"""Live source, step 3: compare two readings of the pricing pages and turn each difference into a signal.

A signal here has the same shape as a cases.json `pricing` signal, so the core
treats it exactly like one: its source is the competitor's pricing page, its
text quotes the page as written, before and after.

Rules, not AI (D13):
- A changed price or list price is one signal per plan (R1).
- Any other change to the plan's lines on the page (billing wording, what it
  includes) is one signal per plan, even when the price is the same (R2).
- A plan that appears or disappears is one signal.
- Only pages read successfully in both snapshots are compared. A failed page
  never reads as "every plan removed" (D12); the caller reports it instead.

"The plan's lines" are its quotes: the page lines the reader says the plan's
values came from. They're compared instead of the reader's billing/includes
fields because the AI files the same line under either field from one run to
the next (seen on Lovable's "Volume based pricingUnlimited users"), while the
lines themselves only change when the page does.
"""

import re

PRICE_FIELDS = ("price", "list_price")
MAX_LINES = 4  # changed lines quoted per signal; the rest are counted


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def _shown(value):
    return f'"{value}"' if value else "nothing"


def _price_words(plan):
    """The plan's price as the page shows it: "$18 (list ~~$20~~) / month, billed annually"."""
    parts = [plan["price"] or "no price"]
    if plan.get("list_price"):
        parts.append(f"(list ~~{plan['list_price']}~~)")
    if plan.get("billing"):
        parts.append(plan["billing"])
    return " ".join(parts)


def _lines(items):
    shown = "; ".join(f'"{line}"' for line in items[:MAX_LINES])
    more = len(items) - MAX_LINES
    return shown + (f" and {more} more" if more > 0 else "")


def _signal(page, plan_name, kind, text):
    stamp = re.sub(r"[^0-9]", "", page["fetched_at"] or "")
    return {
        "id": f"live-{_slug(page['competitor'])}-{_slug(plan_name)}-{kind}-{stamp}",
        "type": "pricing",
        "competitor": page["competitor"],
        "source": page["url"],
        "ts": page["fetched_at"],
        "text": text,
    }


def compare_page(before, after):
    """Signals for one competitor's page, read at two times. Both pages must be ok."""
    old = {plan["name"]: plan for plan in before["plans"]}
    new = {plan["name"]: plan for plan in after["plans"]}
    since = f"(since {before['fetched_at']})"
    signals = []

    for name, plan in new.items():
        if name not in old:
            signals.append(_signal(after, name, "added", f"New plan on the pricing page: {name}, {_price_words(plan)}."))
            continue
        was = old[name]
        old_lines, new_lines = was["quotes"], plan["quotes"]
        if any(was.get(field) != plan.get(field) for field in PRICE_FIELDS):
            signals.append(
                _signal(after, name, "price", f"{name} plan now shows {_price_words(plan)}; it showed {_price_words(was)} {since}.")
            )
            # The price lines are covered by that signal, so they aren't a detail change too.
            old_lines = [line for line in old_lines if not (was["price"] and was["price"] in line)]
            new_lines = [line for line in new_lines if not (plan["price"] and plan["price"] in line)]
        added = [line for line in new_lines if line not in old_lines]
        removed = [line for line in old_lines if line not in new_lines]
        if added or removed:
            changes = []
            if added:
                changes.append(f"now shows {_lines(added)}")
            if removed:
                changes.append(f"no longer shows {_lines(removed)}")
            signals.append(_signal(after, name, "details", f"{name} plan {' and '.join(changes)} {since}."))

    for name, plan in old.items():
        if name not in new:
            signals.append(
                _signal(after, name, "removed", f"{name} plan ({_price_words(plan)}) is no longer on the pricing page {since}.")
            )
    return signals


def compare(previous, current):
    """Signals for every competitor whose page was read in both. previous/current: {competitor: page}."""
    signals = []
    for competitor, page in current.items():
        before = previous.get(competitor)
        if page.get("ok") and before and before.get("ok"):
            signals.extend(compare_page(before, page))
    return signals
