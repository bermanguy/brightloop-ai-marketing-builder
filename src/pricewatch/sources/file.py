"""Test source: signals from a cases.json file."""

import json


def read_cases(path):
    """Return (cases, error). An unreadable file gives ({}, message) so the run still writes a result."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, ValueError) as exc:
        return {}, f"Couldn't read {path}: {exc.__class__.__name__}"
