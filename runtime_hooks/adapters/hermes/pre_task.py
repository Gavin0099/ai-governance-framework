#!/usr/bin/env python3
"""
Hermes adapter for the core pre-task hook.

Expected to normalize native events to runtime_hooks/event_contract.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime_hooks.adapters.hermes.normalize_event import normalize_event
from runtime_hooks.adapters.shared_adapter_runner import adapter_main


if __name__ == "__main__":
    adapter_main("hermes", normalize_event=normalize_event, event_type="pre_task")
