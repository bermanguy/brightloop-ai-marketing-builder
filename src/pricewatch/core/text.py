"""Item text: cleaning quotes, the plain templates, and the "no link, no number" check (R4)."""

import re

from .trust import pricing_url

MAX_QUOTE = 300

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
        text = text[: MAX_QUOTE - 1].rstrip() + "…"
    return text


def numbers_in(text):
    return [n.rstrip(",") for n in NUMBER.findall(text or "")]


def unsupported_numbers(item):
    """Numbers in an item's action or why that no source quote contains."""
    quoted = " ".join(source["quote"] for source in item["sources"])
    supported = set(numbers_in(quoted))
    return [n for n in numbers_in(item["action"] + " " + item["why"]) if n not in supported]


def verified_text(competitor, url, quote, own_pricing_page):
    where = f"{competitor}'s own pricing page" if own_pricing_page else f"{competitor}'s own website"
    why = (
        f'{where} ({url}) says: "{quote}" '
        "Prospects compare plans before they start a trial, so this can move our trial starts."
    )
    if own_pricing_page:
        action = (
            f"Check {competitor}'s new pricing against ours this week. Update our comparison "
            "page, and if we now compare better, say so in this week's trial-start campaign."
        )
        cta = "Update the comparison page"
    else:
        pricing = pricing_page_name(competitor)
        action = (
            f"Confirm this on {pricing} before acting. If it's there, update our comparison "
            "page and this week's trial-start campaign."
        )
        cta = "Confirm on the pricing page"
    return action, why, cta


def unverified_text(competitor, source, quote, kind):
    pricing = pricing_page_name(competitor)
    described = "a sponsored, ad, forum or anonymous source" if kind == "sponsored_or_anonymous" else "a third party"
    action = (
        f"Don't act yet: this isn't on {competitor}'s own pricing page. Check {pricing} "
        "before changing campaigns or the comparison page, or repeating it to leadership."
    )
    why = f'Unverified. The claim comes from {described} ({source}), not {competitor}\'s own website: "{quote}"'
    cta = "Don't act yet"
    return action, why, cta


def pricing_page_name(competitor):
    return pricing_url(competitor) or f"{competitor}'s own pricing page"
