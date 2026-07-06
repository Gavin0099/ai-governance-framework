from __future__ import annotations

from pathlib import Path

import pytest

from governance_tools.memory_authority_baseline import (
    BASELINEABLE_CODES,
    bucket_counts,
    build_baseline,
    compare,
    format_human,
    identity_key,
)
from governance_tools.memory_authority_guard import run_guard

REPO_ROOT = Path(__file__).resolve().parents[1]

# Explicit active_from values keep tests hermetic (no dependency on today's date):
#   PAST  -> any 2026 daily file counts as active
#   FUTURE -> nothing counts as active
PAST = "2000-01-01"
FUTURE = "2999-01-01"


def _unbound(file: str = "2026-04-10.md", entry: str = "- memory_type: post-push", reason: str = "no_anchor") -> dict:
    return {"code": "unbound_memory", "severity": "warning", "file": file, "entry": entry, "reason": reason}


def _ncw(file: str = "2026-05-05.md") -> dict:
    return {
        "code": "non_canonical_writer", "severity": "warning", "file": file,
        "entry": "- memory_type: session-derived",
        "reason": "session_derived_entry_not_written_by_memory_record",
    }


def _gr(violations: list[dict]) -> dict:
    return {"violation_count": len(violations), "violations": violations}


def test_identity_key_stable_and_reason_sensitive() -> None:
    a, b = _unbound(reason="no_anchor"), _unbound(reason="no_anchor")
    c = _unbound(reason="read_error: bad byte")  # read_error subtype -> distinct bucket
    assert identity_key(a) == identity_key(b)
    assert identity_key(a) != identity_key(c)


def test_bucket_counts_collapses_same_key_and_excludes_unknown() -> None:
    vs = [
        _unbound(), _unbound(),  # same key -> count 2
        {"code": "missing_canonical_memory", "severity": "warning", "date": "2026-05-23", "reason": "x"},
        {"code": "not_a_baselineable_code", "file": "f"},  # excluded
    ]
    buckets = bucket_counts(vs)
    assert len(buckets) == 2
    assert sum(b["count"] for b in buckets.values()) == 3
    assert all(b["code"] in BASELINEABLE_CODES for b in buckets.values())


def test_build_baseline_refuses_active_si2() -> None:
    # a recent non_canonical_writer is active relative to PAST -> SI-2 refusal
    with pytest.raises(ValueError, match="SI-2"):
        build_baseline(_gr([_ncw("2026-05-05.md")]), active_from=PAST)


def test_compare_count_delta_new_and_suppressed() -> None:
    current = _gr([_unbound() for _ in range(5)])  # 5 in one bucket
    baseline = build_baseline(_gr([_unbound() for _ in range(3)]), active_from=FUTURE)  # frozen at 3
    payload = compare(current, baseline, active_from=FUTURE)
    assert payload["new_since_baseline"] == 2
    assert payload["suppressed_by_baseline"] == 3
    assert payload["active_fresh_findings"] == 0


def test_compare_shrink_hint_when_debt_resolved() -> None:
    baseline = build_baseline(_gr([_unbound() for _ in range(5)]), active_from=FUTURE)
    current = _gr([_unbound() for _ in range(2)])  # debt shrank
    payload = compare(current, baseline, active_from=FUTURE)
    assert payload["new_since_baseline"] == 0
    assert payload["suppressed_by_baseline"] == 2
    assert payload["baseline_shrink_hint"] is True


def test_active_never_suppressed_si1() -> None:
    # baseline contains a bucket that would match the active record's key, but
    # the active record must be reported as active and never suppressed.
    active_rec = _ncw("2026-05-05.md")
    baseline = {
        "summary": {"total": 1},
        "buckets": [{"identity_key": identity_key(active_rec), "code": "non_canonical_writer", "count": 1}],
    }
    payload = compare(_gr([active_rec]), baseline, active_from=PAST)
    assert payload["active_fresh_findings"] == 1
    assert payload["suppressed_by_baseline"] == 0
    assert payload["new_since_baseline"] == 0


def test_shrink_hint_not_masked_by_active_or_new() -> None:
    # Reviewer scenario: baselineable debt shrank (5 -> 2) but active findings
    # inflate current_total. The hint must still fire (based on suppressed debt,
    # not total guard warnings).
    baseline = build_baseline(_gr([_unbound() for _ in range(5)]), active_from=FUTURE)
    current = _gr([_unbound() for _ in range(2)] + [_ncw("2026-05-05.md") for _ in range(10)])
    payload = compare(current, baseline, active_from=PAST)  # the 10 ncw are active
    assert payload["active_fresh_findings"] == 10
    assert payload["new_since_baseline"] == 0
    assert payload["current_total"] > payload["total_historical_debt"]  # would mask old logic
    assert payload["baseline_shrink_hint"] is True


def test_build_baseline_records_source_head() -> None:
    baseline = build_baseline(_gr([_unbound()]), active_from=FUTURE, source_head="abc1234")
    assert baseline["source_head"] == "abc1234"


def test_format_human_oneliner() -> None:
    payload = compare(_gr([_unbound()]), build_baseline(_gr([_unbound()]), active_from=FUTURE), active_from=FUTURE)
    out = format_human(payload)
    assert out.startswith("[memory-authority-baseline]")
    for token in ("new=", "active=", "suppressed=", "current_total=", "baseline="):
        assert token in out


def _tep(file: str = "2026-04-19.md") -> dict:
    return {
        "code": "test_evidence_provenance_not_found", "severity": "warning", "file": file,
        "entry": "- what_changed: hardened reviewer taxonomy",
        "reason": "test_evidence_success_claim_without_artifact",
    }


def test_test_evidence_provenance_is_baselineable() -> None:
    # The 2026-07-06 noisy-warning downgrade banks provenance debt like other codes.
    assert "test_evidence_provenance_not_found" in BASELINEABLE_CODES
    baseline = build_baseline(_gr([_tep(), _tep()]), active_from=FUTURE)
    assert baseline["summary"]["by_code"]["test_evidence_provenance_not_found"] == 2
    payload = compare(_gr([_tep(), _tep(), _tep()]), baseline, active_from=FUTURE)
    assert payload["suppressed_by_baseline"] == 2
    assert payload["new_since_baseline"] == 1
    assert payload["new_buckets"][0]["code"] == "test_evidence_provenance_not_found"


def test_integration_self_baseline_is_zero_new() -> None:
    # Freeze real guard output, compare against itself -> nothing new, all suppressed.
    result = run_guard(REPO_ROOT / "memory", REPO_ROOT, skip_git=True)
    baseline = build_baseline(result, active_from=FUTURE)
    payload = compare(result, baseline, active_from=FUTURE)
    assert payload["new_since_baseline"] == 0
    assert payload["active_fresh_findings"] == 0
    assert payload["suppressed_by_baseline"] == baseline["summary"]["total"]
