"""The shared core: signals in, Maya's items out.

Test mode (cases.json) and the live app both call `process`. Everything here
is rules; nothing reads a signal's text to decide what to do with it (D1, D13).
"""

import json
import re
from datetime import datetime, timezone

from . import text, trust
from .timestamps import to_utc

BUILT_FOR = "maya"

SKIP_REASONS = {
    "launch": (
        "Feature launch. Maya acts on pricing and packaging, not launches "
        "(\"Feature launches I mostly ignore; features are product's problem\")."
    ),
    "ad": (
        "Ad. Outside Maya's scope (pricing and packaging). An ad's run length and "
        "predicted_ctr are not evidence that it performs (D4)."
    ),
}

SECRET_KEY_NAMES = re.compile(r"key|token|secret|password|credential", re.IGNORECASE)


def process(cases, started_at=None, cost_usd=0.0):
    """Turn a cases dict (the cases.json shape) into the result dict.

    cost_usd is what the live source spent on AI calls before this (0 in test mode).
    """
    started_at = started_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    errors = []
    items, skipped = [], []

    if not isinstance(cases, dict):
        errors.append("Input is not a JSON object; nothing to process.")
        cases = {}
    signals = cases.get("signals")
    if not isinstance(signals, list):
        errors.append("Input has no 'signals' list; nothing to process.")
        signals = []

    default_tz = cases.get("timezone")
    cta_wanted = bool((cases.get("output") or {}).get("cta_required_per_item"))
    seen = set()

    for index, signal in enumerate(signals):
        if not isinstance(signal, dict) or signal.get("id") in (None, ""):
            errors.append(f"Signal #{index} has no id, so it can't be accounted for.")
            continue
        sid = str(signal["id"])
        if sid in seen:
            errors.append(f"Id {sid} appears more than once in the input; only its first signal is used.")
            continue
        seen.add(sid)

        kind = str(signal.get("type") or "").strip().lower()
        if kind in SKIP_REASONS:
            skipped.append({"id": sid, "reason": SKIP_REASONS[kind]})
        elif kind != "pricing":
            skipped.append({"id": sid, "reason": f"Unknown signal type {kind or '(none)'!r}; only pricing becomes an item."})
        elif not text.visible_text(signal.get("text")):
            skipped.append({"id": sid, "reason": "Pricing signal with no text, so there's no claim to act on."})
        else:
            items.append(_pricing_item(sid, signal, default_tz, cta_wanted, errors))

    # Newest first; signals with no readable time go last.
    items.sort(key=lambda item: item["seen_at"] or "", reverse=True)

    result = {
        "built_for": BUILT_FOR,
        "items": items,
        "skipped": skipped,
        "run": {"started_at": started_at, "cost_usd": cost_usd, "errors": errors},
    }
    return _redact(result, _secret_values(cases))


def _pricing_item(sid, signal, default_tz, cta_wanted, errors):
    competitor = text.visible_text(signal.get("competitor")) or "The competitor"
    source = text.visible_text(signal.get("source")) or "no source given"
    quote = text.visible_text(signal.get("text"))
    kind, confidence, unverified = trust.classify(signal.get("source"), signal.get("competitor"))

    sources = [{"url": source, "quote": quote}]
    # The kind of change (live signals only) is set by our comparison rules, never read from the text (D1).
    known = text.change_text(competitor, signal) if kind == "own_pricing_page" else None
    if known:
        headline, action, why, cta = known
    elif unverified:
        page_check = signal.get("page_check") if isinstance(signal.get("page_check"), dict) else None
        action, why, cta = text.unverified_text(competitor, source, quote, kind, page_check)
        headline = text.headline_text(competitor, source, quote, True)
        if page_check:
            sources.append({"url": text.visible_text(page_check.get("url")), "quote": text.visible_text(page_check.get("quote"))})
    else:
        action, why, cta = text.verified_text(competitor, source, quote, kind == "own_pricing_page")
        headline = text.headline_text(competitor, source, quote, False)

    seen_at = to_utc(signal.get("ts"), default_tz)
    if signal.get("ts") is not None and seen_at is None:
        errors.append(f"Couldn't read the time of {sid}: {str(signal['ts'])[:40]!r}.")

    item = {
        "id": f"item-{sid}",
        "source_ids": [sid],
        "confidence": confidence,
        "headline": headline,
        "action": action,
        "why": why,
        "competitor": competitor,
        "unverified": unverified,
        "source_kind": kind,
        "sources": sources,
        "seen_at": seen_at,
    }
    if cta_wanted:
        item["cta"] = cta

    # No link, no number (R4): the templates add no figures of their own, but
    # check anyway and fall back to text with no figures if one slips in.
    missing = text.unsupported_numbers(item)
    if missing:
        errors.append(f"{item['id']}: numbers {missing} aren't in its sources; text replaced.")
        item["headline"] = f"{competitor}: see the source quote."
        item["why"] = "See the source quote."
    return item


def _secret_values(cases):
    """Credential-like config values (e.g. config.demo_key), never to be echoed."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and SECRET_KEY_NAMES.search(str(key)) and len(value) >= 4:
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(cases)
    return found


def _redact(result, secrets):
    if not secrets:
        return result
    raw = json.dumps(result, ensure_ascii=False)
    for secret in secrets:
        raw = raw.replace(json.dumps(secret, ensure_ascii=False)[1:-1], "[redacted]")
    return json.loads(raw)
