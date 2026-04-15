"""
tests/test_plan_context_provenance.py

Tests for the compression provenance layer (Phase 1: plan context only).

Verifies:
  1. plan_summary.py JSON output carries plan_context_provenance
  2. plan_summary.py human output has parseable marker at line 1
  3. session_start._detect_plan_context_provenance detects summarized marker
  4. session_start._detect_plan_context_provenance returns full for plain PLAN.md
  5. _append_canonical_audit_log carries plan_context_provenance in entry
  6. _read_plan_context_provenance reads sidecar correctly
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# ── plan_summary imports ───────────────────────────────────────────────────
from scripts.plan_summary import (
    _PLAN_CONTEXT_PROVENANCE,
    _PROVENANCE_MARKER,
    _PROVENANCE_SIDECAR_PATH,
    build_plan_summary,
    format_human,
)

# ── session_start imports ──────────────────────────────────────────────────
from runtime_hooks.core.session_start import _detect_plan_context_provenance

# ── session_end_hook imports ───────────────────────────────────────────────
from governance_tools.session_end_hook import (
    _append_canonical_audit_log,
    _read_plan_context_provenance,
)


# ── fixtures ───────────────────────────────────────────────────────────────

MINIMAL_PLAN = """\
# PLAN.md - Test Repo

> **最後更新**: 2026-04-15
> **Owner**: Test

## 階段總覽

- [x] Phase A : done
- [>] Phase E : in_progress

## Current Sprint

- [x] Task one done
- [ ] Task two pending

## Backlog

### P0
- [ ] P0 item

## 決策紀錄

| 日期 | 決策 | 說明 |
|---|---|---|
| 2026-04-15 | test decision | test note |
"""


@pytest.fixture()
def tmp_plan(tmp_path: Path) -> Path:
    p = tmp_path / "PLAN.md"
    p.write_text(MINIMAL_PLAN, encoding="utf-8")
    return p


# ── Test 1: JSON output carries plan_context_provenance ───────────────────

def test_plan_summary_json_has_provenance_key(tmp_plan: Path) -> None:
    summary = build_plan_summary(tmp_plan, tmp_plan.parent)
    assert "plan_context_provenance" in summary
    prov = summary["plan_context_provenance"]
    assert prov["fidelity"] == "summarized"
    assert prov["origin"] == "plan_summary.py"
    assert prov["summary_kind"] == "deterministic_extract"


# ── Test 2: Human output has marker at line 1 ─────────────────────────────

def test_plan_summary_human_has_marker_at_line_1(tmp_plan: Path) -> None:
    summary = build_plan_summary(tmp_plan, tmp_plan.parent)
    human = format_human(summary)
    first_line = human.splitlines()[0]
    assert first_line == _PROVENANCE_MARKER
    assert first_line.startswith("<!-- plan_context_provenance ")


# ── Test 3: _detect detects summarized when marker present ────────────────

def test_detect_plan_context_provenance_summarized(tmp_path: Path) -> None:
    # Write a file that starts with the provenance marker (as plan_summary.py would)
    plan = tmp_path / "plan-summary.md"
    plan.write_text(
        _PROVENANCE_MARKER + "\n# PLAN.md Compressed View\n...\n",
        encoding="utf-8",
    )
    prov = _detect_plan_context_provenance(plan)
    assert prov["fidelity"] == "summarized"
    assert prov["origin"] == "plan_summary.py"
    assert prov["summary_kind"] == "deterministic_extract"


# ── Test 4: _detect returns full for normal PLAN.md ───────────────────────

def test_detect_plan_context_provenance_full(tmp_plan: Path) -> None:
    prov = _detect_plan_context_provenance(tmp_plan)
    assert prov["fidelity"] == "full"
    assert prov["origin"] == "PLAN.md"
    assert prov["summary_kind"] is None


# ── Test 5: audit log entry carries plan_context_provenance ───────────────

def test_canonical_audit_log_carries_provenance(tmp_path: Path) -> None:
    provenance = {"fidelity": "summarized", "origin": "plan_summary.py", "summary_kind": "deterministic_extract"}
    dummy_canonical = {
        "signals": [],
        "audit_note": "test",
        "artifact_present": True,
        "failure_disposition_key_present": True,
        "failure_disposition_present": True,
    }
    _append_canonical_audit_log(
        project_root=tmp_path,
        session_id="session-test-prov",
        artifact_state="ok",
        canonical_path_audit=dummy_canonical,
        gate_blocked=False,
        policy_source="repo_local",
        policy_path="governance/gate_policy.yaml",
        fallback_used=False,
        repo_policy_present=True,
        skip_type=None,
        plan_context_provenance=provenance,
    )
    log_path = tmp_path / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "plan_context_provenance" in entry
    assert entry["plan_context_provenance"]["fidelity"] == "summarized"


def test_canonical_audit_log_no_provenance_key_when_none(tmp_path: Path) -> None:
    dummy_canonical = {"signals": [], "audit_note": "", "artifact_present": True,
                       "failure_disposition_key_present": True, "failure_disposition_present": True}
    _append_canonical_audit_log(
        project_root=tmp_path,
        session_id="session-test-none",
        artifact_state="ok",
        canonical_path_audit=dummy_canonical,
        gate_blocked=False,
        policy_source="builtin_default",
        policy_path="",
        fallback_used=True,
        repo_policy_present=False,
        plan_context_provenance=None,
    )
    log_path = tmp_path / "artifacts" / "runtime" / "canonical-audit-log.jsonl"
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "plan_context_provenance" not in entry


# ── Test 6: _read_plan_context_provenance reads sidecar ───────────────────

def test_read_plan_context_provenance_reads_sidecar(tmp_path: Path) -> None:
    sidecar = tmp_path / _PROVENANCE_SIDECAR_PATH
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        json.dumps({"fidelity": "summarized", "origin": "plan_summary.py", "summary_kind": "deterministic_extract"}),
        encoding="utf-8",
    )
    result = _read_plan_context_provenance(tmp_path)
    assert result is not None
    assert result["fidelity"] == "summarized"


def test_read_plan_context_provenance_returns_none_when_absent(tmp_path: Path) -> None:
    result = _read_plan_context_provenance(tmp_path)
    assert result is None
