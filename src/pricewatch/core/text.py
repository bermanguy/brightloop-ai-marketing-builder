"""Item text: cleaning quotes, the plain templates, and the "no link, no number" check (R4)."""

import re

from .trust import pricing_url

MAX_QUOTE = 600

# Numbers as Maya would read them: 20, $25, 1,000, 2.5, 30%. A digit glued to a
# letter ("v0", "W43") is part of a name, not a figure.
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def visible_text(raw):
    """The text a person would see: HTML comments and tags removed, spaces collapsed.

    Comments are where the brief hides instructions (sg-303), and a reader never
    sees them, so they are not part of the claim.
    """
    text = re.sub(r"<!--.*?(-->|$)", " ", str(raw or ""), flags=re.DOTALL)
    text = re.sub(r"<[^>]*>", " ", text)
    text = " ".join(text.split())
    if len(text) > MAX_QUOTE:
        # Cut between words, never inside one, so no figure is shown cut short ("$1,8…").
        text = text[: MAX_QUOTE - 1].rsplit(" ", 1)[0].rstrip() + " …"
    return text


def numbers_in(text):
    return [n.rstrip(",") for n in NUMBER.findall(text or "")]


def unsupported_numbers(item):
    """Numbers in an item's headline, action or why that no source contains.

    A source's link counts: a Hacker News link's item id is part of the link, not a claim.
    """
    quoted = " ".join(source["quote"] + " " + source["url"] for source in item["sources"])
    supported = set(numbers_in(quoted))
    return [n for n in numbers_in(" ".join([item.get("headline", ""), item["action"], item["why"]])) if n not in supported]


# What each kind of change on a competitor's own pricing page means for Brightloop's
# trial starts, and what to do about it (R6). We don't hold Brightloop's own prices,
# so an action never says which product is cheaper or what Brightloop should charge.
# It says what's now out of date (anything Brightloop publishes that quotes the
# competitor: the old figure is exactly the wrong-number risk of Maya's incident),
# and what to decide with whoever owns Brightloop's pricing (D26). Where Brightloop
# quotes competitors (comparison pages, ads, sales material) is an assumption.
PUBLISHED = "Anything we publish that quotes"
DECIDE = "decide with whoever owns our pricing"
CHANGES = {
    "price_up": (
        "{c} raised its {plan} from {was} to {now}{billing}.",
        f"{PUBLISHED} the price of {{c}}'s {{plan}} (comparison pages, ads, sales material) now shows the old "
        f"{{was}}: update it. Then {DECIDE} whether to push our trial while {{c}}'s prospects re-compare.",
        "A price rise sends some of {c}'s prospects comparing alternatives, the moment they decide where to start a trial.",
    ),
    "price_down": (
        "{c} cut its {plan} from {was} to {now}{billing}.",
        f"{PUBLISHED} the price of {{c}}'s {{plan}} (comparison pages, ads, sales material) now shows the old "
        f"{{was}}: update it. Then {DECIDE} whether we need to respond. Don't claim we're cheaper until that's checked.",
        "A lower price makes {c} the easier pick for prospects comparing on price, which can cost us trial starts.",
    ),
    "price": (
        "{c} changed the price of its {plan}: it now shows {now}; it showed {was}.",
        f"{PUBLISHED} the price of {{c}}'s {{plan}} (comparison pages, ads, sales material) is now out of date: "
        "update it.",
        "Prospects compare prices before they start a trial.",
    ),
    "details": (
        "{c} changed what its {plan} includes, at the same price.",
        f"{PUBLISHED} what {{c}}'s {{plan}} includes is now out of date: read the change below and update it. If {{c}} "
        f"now gives less for the same price, {DECIDE} whether to point that out in this week's trial-start campaign.",
        "Prospects compare what each plan includes, not only the price.",
    ),
    "limits": (
        "{c} changed limits in its {plan}.",
        f"{PUBLISHED} {{c}}'s limits is now out of date: read the change below and update it. If {{c}} now gives "
        f"less, {DECIDE} whether to point that out in this week's trial-start campaign.",
        "Limits like tokens and requests are what prospects hit first on a trial, so they compare them.",
    ),
    "added": (
        "{c} added a {plan}, at {now}.",
        f"Add it wherever we compare ourselves with {{c}} (comparison pages, sales material), and {DECIDE} which "
        "of our plans it competes with.",
        "A new plan, especially a cheaper way in, gives prospects a new reason to start a trial at {c}.",
    ),
    "removed": (
        "{c} removed its {plan}. It was {was}.",
        f"Take it out wherever we compare ourselves with {{c}}. Prospects who wanted that plan need another option: "
        f"{DECIDE} whether to point this week's trial-start campaign at them.",
        "People who wanted the plan that's gone are looking for a replacement.",
    ),
    "opens": (
        "{c}'s pricing page now shows its {now} prices first, not {was}.",
        "No price changed. Wherever we quote {c}'s price, say which billing period it is, so we never set our "
        "monthly price against their yearly one.",
        "Yearly prices look lower per month, so the same plan can look cheaper or dearer depending on which view "
        "prospects see first.",
    ),
    "view": (
        "{c}'s pricing page now opens on {now} billing, not {was}, for its {plan}.",
        "No price changed. Wherever we quote {c}'s price, say which billing period it is, so we never set our "
        "monthly price against their yearly one.",
        "Yearly prices look lower per month, so the same plan can look cheaper or dearer depending on which view "
        "prospects see first.",
    ),
}


def change_text(competitor, signal):
    """(headline, action, why, cta) for a known change on the competitor's own pricing page, else None."""
    template = CHANGES.get(signal.get("change"))
    if not template:
        return None
    values = {key: visible_text(signal.get(key)) for key in ("plan", "was", "now")}
    values["c"] = competitor
    billing = visible_text(signal.get("billing"))
    # "$30 / month", or "$30 (billed annually)" when the billing words don't start with the unit.
    values["billing"] = (f" {billing}" if billing.startswith("/") else f" ({billing})") if billing else ""
    if any(f"{{{key}}}" in part and not values[key] for part in template for key in ("plan", "was", "now")):
        return None
    headline, action, why = (part.format(**values) for part in template)
    views = signal.get("views") if isinstance(signal.get("views"), list) else []
    verb = {"price_up": "raised", "price_down": "cut"}.get(signal.get("change"))
    if verb and views:  # one change seen in each billing view: "Monthly: $25 to $30 / month; Yearly: ..."
        parts = []
        for v in views:
            billing = visible_text(v.get("billing"))
            billing = (f" {billing}" if billing.startswith("/") else f" ({billing})") if billing else ""
            parts.append(f"{visible_text(v.get('view'))}: {visible_text(v.get('was'))} to {visible_text(v.get('now'))}{billing}")
        headline = f"{competitor} {verb} its {values['plan']}. {'; '.join(parts)}."
    return headline, action, why, "Update what quotes them"


def verified_text(competitor, url, quote, own_pricing_page):
    where = f"{competitor}'s own pricing page" if own_pricing_page else f"{competitor}'s own website"
    why = (
        f'{where} ({url}) says: "{quote}" '
        "Prospects compare plans before they start a trial, so this can move our trial starts."
    )
    if own_pricing_page:
        action = (
            f"{PUBLISHED} {competitor}'s pricing (comparison pages, ads, sales material) may now be out of date: "
            f"check it against the page and update it. Then {DECIDE} whether to respond."
        )
        cta = "Update what quotes them"
    else:
        pricing = pricing_page_name(competitor)
        action = (
            f"Confirm this on {pricing} before acting. If it's there, update anything we publish that "
            "quotes their pricing."
        )
        cta = "Confirm on the pricing page"
    return action, why, cta


def unverified_text(competitor, source, quote, kind, page_check=None):
    """page_check: what the competitor's own pricing page showed at the same check, {url, quote, checked_at}."""
    pricing = pricing_page_name(competitor)
    described = "a sponsored, ad, forum or anonymous source" if kind == "sponsored_or_anonymous" else "a third party"
    if page_check:
        action = (
            f"Don't act yet. Compare the claim with what {competitor}'s own pricing page showed at this same check "
            "(below), and act only on what the page shows. Don't repeat the claim in campaigns or to leadership."
        )
    else:
        action = (
            f"Don't act yet: this isn't on {competitor}'s own pricing page. Check {pricing} "
            "before changing anything we publish, or repeating it to leadership."
        )
    why = (
        f"It comes from {described}, not {competitor}'s own website. A claim like this, taken as fact, is how last "
        "quarter's wrong price-cut story reached leadership."
    )
    cta = "Don't act yet"
    return action, why, cta


def headline_text(competitor, source, quote, unverified):
    """A one-line summary for an item no change template covers (e.g. a cases.json signal)."""
    if unverified:
        host = re.sub(r"^(https?://)?(www\.)?", "", source).split("/")[0] or "an unknown source"
        return f"Unverified claim about {competitor}'s pricing, from {host}."
    short = quote if len(quote) <= 140 else quote[:139].rsplit(" ", 1)[0] + " …"
    return f"{competitor}: {short}"


def pricing_page_name(competitor):
    return pricing_url(competitor) or f"{competitor}'s own pricing page"
