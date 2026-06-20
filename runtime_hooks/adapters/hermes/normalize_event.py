#!/usr/bin/env python3
"""
Normalize Hermes hook payloads into the shared runtime event contract.

NOTE: "hermes" here is an accepted-input adapter target, NOT a verified
description of any external Hermes runtime's native event API. The fixtures in
runtime_hooks/examples/hermes/ are the accepted-input contract; if a real Hermes
payload uses field names outside the shared aliases (see
runtime_hooks/adapters/shared_normalizer.py), extend the mapping here. Governance
policy stays in runtime_hooks/core/* — this adapter only reshapes payloads.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime_hooks.adapters.shared_normalizer import cli_main, normalize_payload as _normalize_payload


def normalize_event(payload: dict, event_type: str) -> dict:
    return _normalize_payload(payload, harness="hermes", event_type=event_type)


if __name__ == "__main__":
    cli_main("hermes")
