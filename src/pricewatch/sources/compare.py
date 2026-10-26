"""Live source, step 3: compare two readings of the pricing pages and turn each difference into a signal.

A signal here has the same shape as a cases.json `pricing` signal, so the core
treats it exactly like one: its source is the competitor's pricing page, its
text quotes the page as written, before and after.

Rules, not AI (D13):
- A changed price or list price is one signal per plan (R1).
- Any other change to the plan's lines on the page (billing wording, what it
  includes) is one signal per plan, even when the price is the same (R2).
- A plan whose price changes as its card switches between "billed monthly"
  and "billed annually" is one signal saying the page now opens on the other
  billing period, not that the price changed: the page's Monthly/Yearly toggle
  has a new default, and we only read the default view (D14). Seen on Bolt,
  2026-10-26. (The same price with the other period is a real change in terms,
  so it stays a details change.)
- Each plan gives at most one signal per run, so one change isn't shown twice.
- A plan that appears or disappears is one signal.
- A page with a billing toggle is compared view by view (Monthly with Monthly,
  Yearly with Yearly). If it now opens on the other view, that's one signal.
- A change seen the same way in every billing view (Lovable raising Pro on
  both its Monthly and Yearly prices) is one signal quoting each view.
- A table of limits or prices (e.g. Bolt's plan comparison, v0's model rates)
  gives one signal per table, listing the rows whose values changed.
- Only pages read successfully in both snapshots are compared. A failed page
  never reads as "every plan removed" (D12); the caller reports it instead.

Each signal also says, as fields, what kind of change it is ("change"), which
plan or table ("plan"), and its value before and after ("was", "now") as the
page shows them. The core writes Maya's headline and action from those; every
figure in them is in the quoted text. A price is "price_up" or "price_down" only
when both prices are plain amounts ("$25") billed the same way; anything else
("Custom", a new billing period) is "price".

"The plan's lines" are its quotes, the page lines the reader says the plan's
values came from, plus its dropdown options (Lovable's credit ladder). They're compared instead of the reader's billing/includes
fields because the AI files the same line under either field from one run to
the next (seen on Lovable's "Volume based pricingUnlimited users"), while the
lines themselves only change when the page does.
"""

import re

PRICE_FIELDS = ("price", "list_price")
AMOUNT = re.compile(r"\$\s?(\d+(?:\.\d+)?)\*?")
PERIOD = re.compile(r"billed (monthly|annually|yearly)", re.IGNORECASE)
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


def _period(plan):
    """"monthly" or "yearly" when the plan's lines say how it's billed (one way only), else None."""
    found = {"monthly" if m.lower() == "monthly" else "yearly" for m in PERIOD.findall(" ".join(plan["quotes"]))}
    return found.pop() if len(found) == 1 else None


def _plan(page, name):
    """"Pro plan", or "Pro plan (Yearly view)" on a page with a billing toggle."""
    return f"{name} plan ({page['view']} view)" if page.get("view") else f"{name} plan"


def _direction(was, plan):
    """"price_up", "price_down", or "price" when the two prices can't be put side by side."""
    old, new = AMOUNT.fullmatch(was["price"] or ""), AMOUNT.fullmatch(plan["price"] or "")
    if not (old and new) or was.get("billing") != plan.get("billing"):
        return "price"
    old, new = float(old.group(1)), float(new.group(1))
    return "price_up" if new > old else "price_down" if new < old else "price"


def _row(columns, values):
    return "; ".join(f"{column}: {value}" for column, value in zip(columns, values))


def _signal(page, subject, kind, text, change=None, plan=None, was=None, now=None, billing=None):
    stamp = re.sub(r"[^0-9]", "", page["fetched_at"] or "")
    view = f"{_slug(page['view'])}-" if page.get("view") else ""
    return {
        "id": f"live-{_slug(page['competitor'])}-{view}{_slug(subject)}-{kind}-{stamp}",
        "type": "pricing",
        "competitor": page["competitor"],
        "source": page["url"],
        "ts": page["fetched_at"],
        "text": text,
        "change": change or kind,
        "plan": plan,
        "was": was,
        "now": now,
        "billing": billing,
        "name": subject,
        "view": page.get("view"),
    }


def compare_page(before, after):
    """Signals for one competitor's page, read at two times. Both pages must be ok."""
    old = {plan["name"]: plan for plan in before["plans"]}
    new = {plan["name"]: plan for plan in after["plans"]}
    since = f"(since {before['fetched_at']})"
    signals = []

    for name, plan in new.items():
        if name not in old:
            where = f" ({after['view']} view)" if after.get("view") else ""
            signals.append(_signal(after, name, "added", f"New plan on the pricing page{where}: {name}, {_price_words(plan)}.",
                                   plan=_plan(after, name), now=_price_words(plan)))
            continue
        was = old[name]
        price_changed = any(was.get(field) != plan.get(field) for field in PRICE_FIELDS)
        before_period, after_period = _period(was), _period(plan)
        if price_changed and before_period and after_period and before_period != after_period:
            signals.append(_signal(after, name, "view", (
                f"The pricing page now opens on {after_period} billing, not {before_period} {since}: "
                f"{_plan(after, name)} now shows {_price_words(plan)}; it showed {_price_words(was)}. "
                "This is a change in which billing period the page shows first, not necessarily a price change."
            ), plan=_plan(after, name), was=before_period, now=after_period))
            continue
        old_lines = was["quotes"] + (was.get("options") or [])
        new_lines = plan["quotes"] + (plan.get("options") or [])
        changes, kind, change = [], "details", "details"
        if price_changed:
            kind, change = "price", _direction(was, plan)
            changes.append(f"now shows {_price_words(plan)}; it showed {_price_words(was)}")
            # The price lines are covered by that, so they aren't listed as changed lines too.
            old_lines = [line for line in old_lines if not (was["price"] and was["price"] in line)]
            new_lines = [line for line in new_lines if not (plan["price"] and plan["price"] in line)]
        added = [line for line in new_lines if line not in old_lines]
        removed = [line for line in old_lines if line not in new_lines]
        if added:
            changes.append(f"now shows {_lines(added)}")
        if removed:
            changes.append(f"no longer shows {_lines(removed)}")
        if changes:
            text = f"{_plan(after, name)} {' and '.join(changes)} {since}."
            if change in ("price_up", "price_down"):  # same billing on both sides: "from $25 to $30 (/ month)"
                signals.append(_signal(after, name, kind, text, change, plan=_plan(after, name), was=was["price"],
                                       now=plan["price"], billing=plan.get("billing")))
            else:
                signals.append(_signal(after, name, kind, text, change, plan=_plan(after, name), was=_price_words(was),
                                       now=_price_words(plan)))

    for name, plan in old.items():
        if name not in new:
            signals.append(
                _signal(after, name, "removed", f"{_plan(after, name)} ({_price_words(plan)}) is no longer on the pricing page {since}.",
                        plan=_plan(after, name), was=_price_words(plan))
            )

    for title, table in {t["title"]: t for t in after.get("tables") or []}.items():
        was = {t["title"]: t for t in before.get("tables") or []}.get(title)
        if not was:
            continue  # a table that wasn't read before: its first reading, nothing to compare
        old_rows = {r["label"]: r["values"] for r in was["rows"]}
        new_rows = {r["label"]: r["values"] for r in table["rows"]}
        changed = [
            f'"{label}" now shows {_row(table["columns"], values)}; it showed {_row(was["columns"], old_rows[label])}'
            for label, values in new_rows.items() if label in old_rows and (values, table["columns"]) != (old_rows[label], was["columns"])
        ]
        changed += [f'new row "{label}": {_row(table["columns"], values)}' for label, values in new_rows.items() if label not in old_rows]
        changed += [f'row "{label}" is gone' for label in old_rows if label not in new_rows]
        if changed:
            more = len(changed) - MAX_LINES
            listed = "; and ".join(changed[:MAX_LINES]) + (f"; and {more} more" if more > 0 else "")
            signals.append(_signal(after, title, "limits", f'The "{title}" table on the pricing page changed {since}: {listed}.',
                                   plan=f'"{title}" table'))

    if after.get("view_index") == 0 and before.get("opens_on") and after.get("opens_on") and before["opens_on"] != after["opens_on"]:
        signals.append(_signal(after, "page", "opens", (
            f"The pricing page now opens on its {after['opens_on']} prices, not {before['opens_on']} {since}. "
            "Both are still on the page; this is a change in which prices visitors see first."
        ), was=before["opens_on"], now=after["opens_on"]))
    return signals


def _unique(values):
    return " and ".join(dict.fromkeys(v for v in values if v))


def merge_views(signals):
    """One signal for a change seen the same way in every billing view.

    Lovable raising Pro shows on its Monthly and its Yearly view: that's one change
    for Maya, so it's one signal quoting both views. The per-view values are kept
    under "views". A plan that changed differently in each view stays two signals.
    """
    groups = {}
    for signal in signals:
        key = (signal["competitor"], signal.get("name"), signal["change"]) if signal.get("view") else id(signal)
        groups.setdefault(key, []).append(signal)
    merged = []
    for group in groups.values():
        if len(group) == 1 or len({s["view"] for s in group}) < len(group):
            merged.extend(group)
            continue
        first = group[0]
        merged.append(dict(
            first,
            id=first["id"].replace(f"-{_slug(first['view'])}-", "-", 1),
            text=" ".join(s["text"] for s in group),
            plan=f"{first['name']} plan" if first["plan"] else None,
            was=_unique(s["was"] for s in group),
            now=_unique(s["now"] for s in group),
            billing=None,
            view=None,
            views=[{key: s[key] for key in ("view", "was", "now", "billing")} for s in group],
        ))
    return merged


def compare(previous, current):
    """Signals for every page (or view) read in both, a change seen in every view once. previous/current: {fetch.label(page): page}."""
    signals = []
    for name, page in current.items():
        before = previous.get(name)
        if page.get("ok") and before and before.get("ok"):
            signals.extend(compare_page(before, page))
    return merge_views(signals)
