"""Live source, rumors: pricing claims about the competitors on Hacker News.

Maya's incident was a false number taken as fact ("an AI summary said a
competitor had cut prices 30%"). Claims like that circulate before anyone checks
the pricing page, so the watch shows them, labelled unverified with low
confidence and a "don't act yet" action (D10). The core sets that by rule from
the source: a Hacker News link is a forum (core/trust.py).

A claim is one sentence of a story or comment, quoted as written, that names
the competitor and states an amount or a percentage next to a pricing word
("Lovable's Pro is $30 now"). Rules, not AI: no key needed, and nothing is
paraphrased, so every number Maya sees is in the quote (R4).

Hacker News search is Algolia's public API: no account, no key.
Each comment is reported once; ids already reported are kept in the snapshots.
"""

import re
from datetime import datetime, timedelta, timezone

from .fetch import USER_AGENT, visible_text

SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
ITEM = "https://news.ycombinator.com/item?id={}"
WINDOW_DAYS = 7
TIMEOUT_S = 20

# What to search for, and how the competitor is named in a sentence.
COMPETITORS = {
    "Lovable": {"query": "lovable", "name": r"\blovable\b"},
    "Bolt": {"query": "bolt.new", "name": r"\bbolt(?:\.new)?\b"},
    "Replit": {"query": "replit", "name": r"\breplit\b"},
    "v0": {"query": "v0", "name": r"\bv0(?:\.dev|\.app)?\b"},
}

AMOUNT = re.compile(r"\$\s?\d|\d\s?%|\d+\s?(?:usd|dollars|bucks)\b", re.I)
PRICING = re.compile(r"\b(?:pric\w*|plans?|tiers?|pro|plus|teams|business|core|enterprise|subscriptions?|credits?|per month|/mo\b|/month|monthly|yearly|annual\w*|"
                     r"free tier|paywall|charg\w*|cost\w*|discount\w*|cheaper|expensive)", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
MAX_QUOTE = 300


def claims_in(text, competitor):
    """The sentences of a post that make a pricing claim about the competitor, as written."""
    name = re.compile(COMPETITORS[competitor]["name"], re.I)
    found = []
    for sentence in SENTENCE.split(text or ""):
        sentence = sentence.strip()
        if name.search(sentence) and AMOUNT.search(sentence) and PRICING.search(sentence) and len(sentence) <= MAX_QUOTE:
            found.append(sentence)
    return found


def _search(query, since):
    import httpx

    # typoTolerance off: otherwise "lovable" also matches "love" and fills the page with noise.
    params = {"query": query, "tags": "(story,comment)", "typoTolerance": "false", "numericFilters": f"created_at_i>{int(since.timestamp())}",
              "hitsPerPage": 100}
    response = httpx.get(SEARCH, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
    response.raise_for_status()
    return response.json()["hits"]


def find(seen=(), now=None):
    """Return (signals, errors). Signals have the shape of cases.json pricing signals.

    seen: Hacker News ids reported by earlier runs; they're skipped.
    """
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=WINDOW_DAYS)
    signals, errors = [], []
    for competitor, spec in COMPETITORS.items():
        try:
            hits = _search(spec["query"], since)
        except Exception as exc:  # network errors, rate limits, a changed API
            errors.append(f"Hacker News ({competitor}): couldn't search ({exc.__class__.__name__}: {str(exc)[:120]}).")
            continue
        for hit in hits:
            hn_id = str(hit.get("objectID") or "")
            if not hn_id or hn_id in seen:
                continue
            text = visible_text("\n".join(filter(None, [hit.get("title"), hit.get("story_text"), hit.get("comment_text")])))
            for number, quote in enumerate(claims_in(text, competitor), 1):
                signals.append({
                    "id": f"hn-{hn_id}-{competitor.lower()}-{number}",
                    "hn_id": hn_id,
                    "type": "pricing",
                    "competitor": competitor,
                    "source": ITEM.format(hn_id),
                    "ts": hit.get("created_at"),
                    "text": quote,
                })
    return signals, errors
