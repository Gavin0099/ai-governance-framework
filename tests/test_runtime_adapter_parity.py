"""Cross-harness adapter parity guard.

The runtime governance layer is harness-agnostic (runtime_hooks/ADAPTER_CONTRACT.md):
adapters may only reshape payloads, never embed governance policy. Today that
holds structurally — the four adapter families are identical wrappers and
shared_normalizer.normalize_payload uses the harness only to stamp
metadata.harness. This test pins that invariant so a future per-harness branch
or per-adapter override cannot silently create a weaker path.
"""

from __future__ import annotations

import copy

import pytest

from runtime_hooks.adapters.claude_code.normalize_event import (
    normalize_event as claude_code_normalize,
)
from runtime_hooks.adapters.codex.normalize_event import (
    normalize_event as codex_normalize,
)
from runtime_hooks.adapters.gemini.normalize_event import (
    normalize_event as gemini_normalize,
)
from runtime_hooks.adapters.hermes.normalize_event import (
    normalize_event as hermes_normalize,
)

HARNESS_NORMALIZERS = {
    "claude_code": claude_code_normalize,
    "codex": codex_normalize,
    "gemini": gemini_normalize,
    "hermes": hermes_normalize,
}

EVENT_TYPES = ("session_start", "pre_task", "post_task")

# A rich payload exercising task aliasing, rules, risk/oversight/memory,
# response/checks/contract, impact sets, snapshot, and metadata sources.
RICH_PAYLOAD = {
    "task": "Refactor the retry path",
    "project_root": "/repo",
    "plan": "PLAN.md",
    "rules": ["common", "python"],
    "risk": "high",
    "oversight": "review-required",
    "memory_mode": "candidate",
    "response_file": "/repo/out.md",
    "checks_file": "/repo/checks.json",
    "contract": "/repo/contract.yaml",
    "impact_before": ["a.py", "b.py"],
    "impact_after": ["a.py", "b.py", "c.py"],
    "snapshot": True,
    "summary": "did the thing",
    "session_id": "sess-123",
    "hook_event_name": "PreToolUse",
}


def _strip_harness(normalized: dict) -> dict:
    out = copy.deepcopy(normalized)
    if isinstance(out.get("metadata"), dict):
        out["metadata"].pop("harness", None)
    return out


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_all_harnesses_normalize_identically_except_harness_stamp(event_type: str) -> None:
    results = {
        harness: normalize(copy.deepcopy(RICH_PAYLOAD), event_type)
        for harness, normalize in HARNESS_NORMALIZERS.items()
    }

    # The harness only stamps metadata.harness; every other field must match.
    reference = _strip_harness(results["claude_code"])
    for harness, normalized in results.items():
        assert _strip_harness(normalized) == reference, (
            f"{harness} diverges from claude_code for event_type={event_type}"
        )
        assert normalized["metadata"]["harness"] == harness


def test_harness_only_affects_metadata_harness_field() -> None:
    # Same payload/event through two harnesses must differ in exactly one place:
    # metadata.harness. Any other divergence means a per-harness code path exists.
    a = claude_code_normalize(copy.deepcopy(RICH_PAYLOAD), "pre_task")
    b = gemini_normalize(copy.deepcopy(RICH_PAYLOAD), "pre_task")

    assert a["metadata"]["harness"] == "claude_code"
    assert b["metadata"]["harness"] == "gemini"
    assert _strip_harness(a) == _strip_harness(b)
