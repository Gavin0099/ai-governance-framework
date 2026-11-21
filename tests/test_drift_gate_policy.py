import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.drift_gate_policy import is_time_based_advisory

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "governance_tools" / "drift_gate_policy.py"

STALE_KEY = {"check": "expansion_boundary", "severity": "warning",
             "detail": "transitional_key_stale: key='k' admitted=2026-07-29 age=91d (max=90d) "
                       "expected=core — promote to core or remove"}
STALE_BASELINE = {"check": "baseline_yaml_freshness", "severity": "warning",
                  "detail": "baseline.yaml is 95 days old (threshold: 90d) — re-run drift check"}


def _run(payload):
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, str(POLICY)], input=stdin, text=True,
                          capture_output=True, encoding="utf-8")


@pytest.mark.parametrize("finding", [STALE_KEY, STALE_BASELINE])
def test_time_based_warnings_are_advisory(finding):
    assert is_time_based_advisory(finding)


@pytest.mark.parametrize("finding", [
    {"check": "protected_files_unmodified", "severity": "warning",
     "detail": "no recorded hash for AGENTS.base.md — re-run init to record hash"},
    {"check": "source_commit_recorded", "severity": "warning", "detail": "source_commit missing"},
    {"check": "baseline_yaml_freshness", "severity": "warning",
     "detail": "cannot parse initialized_at: not-a-date"},
    {"check": "expansion_boundary", "severity": "warning",
     "detail": "new_return_key: unrecognized key(s) in return dict: ['x']"},
    {**STALE_KEY, "severity": "critical"},
    {"check": "expansion_boundary", "severity": "warning"},
    "transitional_key_stale: not a dict",
])
def test_everything_else_blocks(finding):
    assert not is_time_based_advisory(finding)


def test_advisory_only_result_passes_and_stays_visible():
    completed = _run({"findings": [STALE_KEY, STALE_BASELINE]})
    assert completed.returncode == 0
    assert completed.stdout.count("ADVISORY") == 2
    assert "transitional_key_stale" in completed.stdout


def test_one_bookkeeping_warning_blocks_the_whole_result():
    bookkeeping = {"check": "source_commit_recorded", "severity": "warning", "detail": "missing"}
    completed = _run({"findings": [STALE_KEY, bookkeeping]})
    assert completed.returncode == 1
    assert "BLOCK source_commit_recorded" in completed.stdout


@pytest.mark.parametrize("payload", ["", "{not json", {"no_findings": []}, {"findings": "x"},
                                     {"findings": []}])
def test_unreadable_or_empty_result_blocks(payload):
    completed = _run(payload)
    assert completed.returncode == 1
    assert "BLOCK" in completed.stdout


def test_gate_2b_consults_policy_only_for_warning_exit():
    script = (ROOT / "scripts" / "verify_phase_gates.sh").read_text(encoding="utf-8")
    gate = script[script.index("Gate 2b"):script.index("Gate 3")]
    assert '--format human || DRIFT_RC=$?' in gate
    assert 'if [ "$DRIFT_RC" -eq 1 ]; then' in gate
    assert "governance_tools/drift_gate_policy.py" in gate
    assert 'if [ "$DRIFT_RC" -eq 0 ]; then' in gate
    assert 'elif [ "$DRIFT_ADVISORY_ONLY" = true ]; then' in gate
    assert "bookkeeping consistency, not owner authorization" in gate
