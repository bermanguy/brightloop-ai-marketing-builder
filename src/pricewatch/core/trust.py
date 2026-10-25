"""Confidence and the unverified label, set by rule from where a claim came from (D13).

Only the signal's `source` and `competitor` fields are read here, never its
`text`, so instructions hidden in the text cannot move confidence (D1).
"""

import re

# Each competitor's own website and its pricing page.
COMPETITORS = {
    "lovable": {"domains": ["lovable.dev"], "pricing_url": "lovable.dev/pricing"},
    "bolt": {"domains": ["bolt.new"], "pricing_url": "bolt.new/pricing"},
    "replit": {"domains": ["replit.com"], "pricing_url": "replit.com/pricing"},
    "v0": {"domains": ["v0.app", "v0.dev"], "pricing_url": "v0.app/pricing"},
}

# The confidence table in docs/architecture.md.
OWN_PRICING_PAGE = ("own_pricing_page", 0.9, False)
OWN_SITE_OTHER_PAGE = ("own_site_other_page", 0.6, False)
THIRD_PARTY = ("third_party", 0.4, True)
LOW_TRUST = ("sponsored_or_anonymous", 0.2, True)

# Markers of sponsored, ad, forum or anonymous sources. Checked first, so
# "sponsored post on lovable.dev" is still low trust.
LOW_TRUST_MARKERS = re.compile(
    r"sponsor|\bads?\b|ads\.|advert|promoted|reddit|\bu/|anon|rumou?r|forum|"
    r"ai summary|chatgpt",
    re.IGNORECASE,
)

HOST = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)+)(/[^\s,;]*)?", re.IGNORECASE)


def _key(competitor):
    return re.sub(r"[^a-z0-9]", "", str(competitor or "").lower())


def _own_domains(competitor):
    known = COMPETITORS.get(_key(competitor))
    return known["domains"] if known else []


def pricing_url(competitor):
    """The competitor's pricing page, or None for a competitor we don't track."""
    known = COMPETITORS.get(_key(competitor))
    return known["pricing_url"] if known else None


def _is_own_host(host, competitor):
    host = host.lower()
    for domain in _own_domains(competitor):
        if host == domain or host.endswith("." + domain):
            return True
    # A competitor we don't track: its own site if the domain name is its name,
    # e.g. "cursor.com" for "Cursor".
    parts = host.split(".")
    return len(parts) >= 2 and parts[-2] == _key(competitor) != ""


def classify(source, competitor):
    """Return (kind, confidence, unverified) for a claim's source."""
    source = str(source or "").strip()
    if not source or LOW_TRUST_MARKERS.search(source):
        return LOW_TRUST
    match = HOST.search(source)
    if match and _is_own_host(match.group(1), competitor):
        path = (match.group(2) or "").lower()
        if path.startswith("/pricing"):
            return OWN_PRICING_PAGE
        return OWN_SITE_OTHER_PAGE
    return THIRD_PARTY
