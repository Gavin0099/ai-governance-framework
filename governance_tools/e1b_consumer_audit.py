"""
governance_tools/e1b_consumer_audit.py
=======================================
E1b Consumer Audit — Text Scanner.

Scans consumer text (summaries, reports, comments, scripts) for violations
of the semantic limits defined in docs/e1b-classification-semantic-limits.md
and docs/e1b-consumer-audit-checklist.md.

Four forbidden patterns:
  P1  transitioning_active implied as improvement / positive trend
  P2  lifecycle classification count used in numeric risk/score formula
  P3  temporal accumulation implied to improve model classification accuracy
  P4  READY gate verdict equated with classifier validated / safe to promote

Usage
-----
    from governance_tools.e1b_consumer_audit import scan_consumer_text

    violations = scan_consumer_text(text)
    if violations:
        for v in violations:
            print(f"[{v['pattern_id']}] {v['description']}")
            print(f"  matched: {v['excerpt']}")
    else:
        print("no violations found")

Design notes
------------
- scan_consumer_text() is purely detection — it cannot block at runtime.
  It surfaces violations so a human or CI check can act on them.
- False negatives (missed violations) are acceptable; false positives
  (flagging legitimate text) degrade trust and must be minimized.
- Patterns are narrow-band: they require the forbidden combination, not
  individual words in isolation.
- Reference: docs/e1b-consumer-audit-checklist.md
"""
from __future__ import annotations

import re
from typing import Any


# ── Pattern registry ──────────────────────────────────────────────────────────
# Each entry maps to one of the 4 forbidden patterns in the checklist.
# "regexes": list of patterns (any match → violation).
# All patterns are case-insensitive.

_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern_id": "P1",
        "description": (
            "transitioning_active used to imply improvement, progress, or positive trend "
            "(forbidden — the label is semantically neutral, not directional)"
        ),
        "regexes": [
            # "transitioning[...] improv / positive trend / on track / progressing"
            r"(?i)transitioning.{0,80}"
            r"(improv|positive.{0,5}trend|on.{0,3}track|progressing|getting\s+better)",
            # reverse order
            r"(?i)(improv|positive.{0,5}trend|on.{0,3}track|progressing|getting\s+better)"
            r".{0,80}transitioning",
        ],
    },
    {
        "pattern_id": "P2",
        "description": (
            "lifecycle classification count used in numeric risk/score formula "
            "(forbidden — neutral label must not become a risk weight)"
        ),
        "regexes": [
            # transitioning_count ± operator
            r"(?i)transitioning.{0,8}count.{0,40}[\+\-\*\/]",
            # operator ± transitioning_count
            r"(?i)[\+\-\*\/].{0,40}transitioning.{0,8}count",
            # risk_score / risk score + transitioning anywhere nearby
            r"(?i)risk.{0,10}score.{0,60}transitioning",
            r"(?i)transitioning.{0,60}risk.{0,10}score",
        ],
    },
    {
        "pattern_id": "P3",
        "description": (
            "temporal accumulation implied to improve classification accuracy or reliability "
            "(forbidden — time raises reviewer confidence, not model precision)"
        ),
        "regexes": [
            # observed / multiple days / longer → more reliable / more accurate
            r"(?i)(observed?\b|observation|multiple\s+days?|multiple\s+sessions?|longer\s+observ)"
            r".{0,80}(more\s+reliable|more\s+accurate|higher\s+precision|more\s+confident)",
            # reverse
            r"(?i)(more\s+reliable|more\s+accurate|higher\s+precision|more\s+confident)"
            r".{0,80}(observed?\b|observation|multiple\s+days?|multiple\s+sessions?|longer\s+observ)",
            # "classification is more reliable" (with or without temporal context)
            r"(?i)classif\w{0,20}\s+is\s+more\s+reliable",
        ],
    },
    {
        "pattern_id": "P4",
        "description": (
            "READY gate verdict equated with classifier validated, classification proven, "
            "or safe to promote "
            "(forbidden — READY is a policy proxy, not a classification proof)"
        ),
        "regexes": [
            # "likely ready for promotion/promote"
            r"(?i)likely\s+ready\s+for\s+promot",
            # gate passed/ready → promote
            r"(?i)(gate|verdict).{0,30}(passed|ready).{0,80}promot",
            # READY + classifier reliable / classification validated / can promote
            r"(?i)\bREADY\b.{0,80}"
            r"(classifier.{0,10}reliable|classification.{0,10}valid|safe.{0,5}promot|can\s+promot)",
        ],
    },
]


# ── Public API ─────────────────────────────────────────────────────────────────

def scan_consumer_text(text: str) -> list[dict[str, str]]:
    """
    Scan text for E1b consumer anti-patterns.

    Parameters
    ----------
    text : str
        Any text artifact — summary, report, code comment, narrative.

    Returns
    -------
    list[dict]
        Each dict has:
          pattern_id  : "P1" | "P2" | "P3" | "P4"
          description : human-readable rule that was violated
          excerpt     : the matched text (truncated to 120 chars)

        Returns an empty list when no violations are found.

    Design boundary
    ---------------
    Detection scope: the four forbidden patterns from the checklist.
    False negatives (missed violations) are acceptable.
    False positives must be minimized — patterns require the forbidden
    combination, not individual words in isolation.
    """
    violations: list[dict[str, str]] = []
    for entry in _PATTERNS:
        for regex in entry["regexes"]:
            for match in re.finditer(regex, text):
                violations.append({
                    "pattern_id": entry["pattern_id"],
                    "description": entry["description"],
                    "excerpt": match.group(0)[:120],
                })
    return violations


def violation_pattern_ids(text: str) -> set[str]:
    """
    Convenience helper: return only the set of pattern IDs found in text.

    Useful for assertions: ``assert "P1" in violation_pattern_ids(text)``
    """
    return {v["pattern_id"] for v in scan_consumer_text(text)}
