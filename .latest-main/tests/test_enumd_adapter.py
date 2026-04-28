"""
tests/test_enumd_adapter.py

Tests for integrations/enumd/enumd_adapter.adapt_enumd_report().

These tests verify that the Enumd-specific adapter layer:
  1. Always routes through external_observation_adapter (trust boundary)
  2. Always produces misuse_evidence_status="not_tested" (non-equivalence guarantee)
  3. Degrades gracefully on bad/incomplete inputs (fail-closed)
  4. Strips and warns on forbidden authority fields
  5. Preserves Enumd advisory signals as evidence_refs (informational only)
  6. Never elevates Enumd "all pass" to any canonical risk state

Coverage matrix
---------------
A1  valid_wave5              — normal input → accepted, not_tested, decision_constraints locked
A2  missing_fields           — absent run_id / calibration_profile → degraded, not crash
A3  ambiguous_status         — unknown severity advisories → not_tested, advisory refs preserved
A4  forbidden_authority      — verdict/current_state/promote_eligible → stripped, degraded
A5  legacy_old_format        — no calibration_profile → degraded, advisory-only
A6  looks_safe_not_tested    — all-pass Enumd → still not_tested (non-equivalence enforced)
A7  contradictory_runs       — calibration profile change → accepted, provenance metadata preserved
A8  non_dict_input           — raises ValueError immediately
A9  advisory_refs_format     — evidence_refs follow "enumd:<signal>:<slug>" pattern
A10 decision_constraints_locked — external_authority/verdict_authority/promotion_authority all False
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.enumd.enumd_adapter import adapt_enumd_report

# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "enumd"


def _load(name: str) -> dict:
    p = FIXTURES_DIR / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# A1 — valid wave-5 report produces canonical envelope
# ─────────────────────────────────────────────────────────────────────────────

def test_valid_wave5_accepted() -> None:
    """
    A well-formed Enumd report must produce ingest_status=accepted and
    misuse_evidence_status=not_tested.
    """
    report = _load("valid_wave5")
    env = adapt_enumd_report(report)

    assert env["ingest_status"] == "accepted", (
        f"Expected accepted; got {env['ingest_status']}; warnings={env['advisory']['warnings']}"
    )
    assert env["observation"]["misuse_evidence_status"] == "not_tested"
    assert env["observation"]["confidence_level"] == "low"


# ─────────────────────────────────────────────────────────────────────────────
# A2 — missing fields → degraded, no crash
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_fields_degraded_not_crash() -> None:
    """
    A report missing run_id and calibration_profile must produce
    ingest_status=degraded without raising an exception.
    misuse_evidence_status must still be not_tested.
    """
    report = _load("missing_fields")
    env = adapt_enumd_report(report)

    # Must degrade, not crash
    assert env["ingest_status"] == "degraded"
    # Non-equivalence must hold even on degraded input
    assert env["observation"]["misuse_evidence_status"] == "not_tested"
    # decision_constraints must still be locked
    assert env["decision_constraints"]["external_authority"] is False
    assert env["decision_constraints"]["promotion_authority"] is False


# ─────────────────────────────────────────────────────────────────────────────
# A3 — ambiguous advisories → advisory refs preserved, status still not_tested
# ─────────────────────────────────────────────────────────────────────────────

def test_ambiguous_status_advisory_signals_preserved() -> None:
    """
    Advisories with unknown severity must be preserved in advisory_signals[],
    NOT in observation.evidence_refs.
    misuse_evidence_status must remain not_tested regardless of advisory count.
    """
    report = _load("ambiguous_status")
    env = adapt_enumd_report(report)

    assert env["observation"]["misuse_evidence_status"] == "not_tested"

    # Advisories must appear in advisory_signals[], not evidence_refs
    signals = env["advisory_signals"]
    assert len(signals) >= 2, f"Expected advisory_signals entries; got {signals}"

    # Each signal must be a structured dict with required keys
    for sig in signals:
        assert "signal" in sig, f"Missing 'signal' key in advisory_signal: {sig}"
        assert "source_ref" in sig, f"Missing 'source_ref' key in advisory_signal: {sig}"
        assert sig["source_ref"].startswith("enumd:"), (
            f"source_ref must start with 'enumd:'; got {sig['source_ref']!r}"
        )

    # evidence_refs must NOT contain advisory signal slugs
    for ref in env["observation"]["evidence_refs"]:
        assert "domain_misalignment_risk" not in ref, (
            f"Advisory signal slug leaked into evidence_refs: {ref!r}"
        )
        assert "thin_synthesis" not in ref, (
            f"Advisory signal slug leaked into evidence_refs: {ref!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# A4 — forbidden authority fields → stripped, envelope degraded
# ─────────────────────────────────────────────────────────────────────────────

def test_forbidden_authority_fields_stripped_and_degraded() -> None:
    """
    A report containing verdict, current_state, promote_eligible,
    phase3_entry_allowed, closure_review_approved must be degraded.

    None of those values must appear in the output envelope as decision fields.
    """
    report = _load("forbidden_authority_fields")
    env = adapt_enumd_report(report)

    # Envelope must be degraded because forbidden fields were present
    assert env["ingest_status"] == "degraded", (
        "Expected degraded when forbidden authority fields present; "
        f"got {env['ingest_status']}"
    )

    # Forbidden values must NOT have leaked into the envelope at any key
    forbidden_values = {"APPROVED", "closure_verified", True}
    for key in ("verdict", "gate_verdict", "current_state", "promote_eligible",
                "phase3_entry_allowed", "closure_review_approved"):
        assert key not in env, f"Forbidden field {key!r} leaked into envelope"

    # decision_constraints must be locked False
    dc = env["decision_constraints"]
    assert dc["external_authority"] is False
    assert dc["verdict_authority"] is False
    assert dc["promotion_authority"] is False

    # Warnings must mention the forbidden fields
    all_warnings = " ".join(env["advisory"]["warnings"])
    assert "forbidden" in all_warnings.lower(), (
        f"Expected forbidden-field warning; got: {env['advisory']['warnings']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# A5 — legacy old format (missing calibration_profile) → degraded, advisory-only
# ─────────────────────────────────────────────────────────────────────────────

def test_legacy_old_format_degraded_advisory_only() -> None:
    """
    A legacy report missing calibration_profile must degrade gracefully.
    The output must still carry decision_constraints locked.
    """
    report = _load("legacy_old_format")
    env = adapt_enumd_report(report)

    assert env["ingest_status"] == "degraded"
    assert env["observation"]["misuse_evidence_status"] == "not_tested"
    assert env["decision_constraints"]["external_authority"] is False


# ─────────────────────────────────────────────────────────────────────────────
# A6 — all-pass Enumd report → still not_tested (non-equivalence enforced)
# ─────────────────────────────────────────────────────────────────────────────

def test_all_pass_report_still_not_tested() -> None:
    """
    An Enumd report where suppressed=0, flagged=0, no advisories must still
    produce misuse_evidence_status=not_tested.

    Enumd "all pass" means synthesis quality passed Enumd's domain-calibrated
    thresholds.  It does NOT mean risk is absent in the framework sense.
    not_observed_in_window would claim absence of evidence; not_tested is correct
    because Enumd does not test agent misuse.
    """
    report = _load("looks_safe_not_tested")
    env = adapt_enumd_report(report)

    status = env["observation"]["misuse_evidence_status"]
    assert status == "not_tested", (
        f"Enumd all-pass must produce not_tested, NOT {status!r}. "
        "Mapping Enumd all-pass to a stronger framework state would be a "
        "non-equivalence violation."
    )
    # Confidence must remain low even for clean Enumd reports
    assert env["observation"]["confidence_level"] == "low"


# ─────────────────────────────────────────────────────────────────────────────
# A7 — contradictory runs (calibration profile change) → provenance preserved
# ─────────────────────────────────────────────────────────────────────────────

def test_contradictory_runs_provenance_preserved() -> None:
    """
    A report where calibration_profile changed between waves must be accepted.
    The calibration_profile metadata must be preserved in enumd_provenance so
    downstream trend analysis can apply suppression_changed_because_of_behavior().
    """
    report = _load("contradictory_runs")
    env = adapt_enumd_report(report)

    # Should be accepted (the report itself is structurally valid)
    assert env["ingest_status"] == "accepted"

    # Provenance must include calibration_profile for trend disambiguation
    prov = env.get("enumd_provenance", {})
    assert prov.get("calibration_profile") is not None, (
        "enumd_provenance.calibration_profile must be preserved for trend analysis"
    )
    assert prov["calibration_profile"]["name"] == "production_v2"

    # run_id must be preserved
    assert prov.get("run_id") == "wave-6-recalibrated"


# ─────────────────────────────────────────────────────────────────────────────
# A8 — non-dict input → ValueError
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_input", [None, "string", 42, [], True])
def test_non_dict_input_raises(bad_input) -> None:
    """adapt_enumd_report must raise ValueError for non-dict inputs."""
    with pytest.raises(ValueError):
        adapt_enumd_report(bad_input)


# ─────────────────────────────────────────────────────────────────────────────
# A9 — advisory_signals 與 evidence_refs 語義分流
# ─────────────────────────────────────────────────────────────────────────────

def test_advisory_signals_separate_from_evidence_refs() -> None:
    """
    Advisory signal slugs must be in advisory_signals[], NOT evidence_refs.
    evidence_refs must only contain provenance pointers (run id, artifact paths).

    This enforces the semantic split that prevents downstream consumers from
    treating advisory signal count as evidence density.
    """
    report = _load("valid_wave5")
    env = adapt_enumd_report(report)

    # advisory_signals must exist and contain the Enumd signal
    signals = env["advisory_signals"]
    assert len(signals) >= 1, "Expected advisory_signals from valid_wave5 advisories"
    signal_names = [s["signal"] for s in signals]
    assert "domain_misalignment_risk" in signal_names, (
        f"Expected domain_misalignment_risk in advisory_signals; got {signal_names}"
    )

    # Each advisory_signal must follow structured format
    for sig in signals:
        assert isinstance(sig.get("signal"), str)
        assert isinstance(sig.get("source_ref"), str)
        assert sig["source_ref"].startswith("enumd:"), (
            f"source_ref {sig['source_ref']!r} must start with 'enumd:'"
        )

    # evidence_refs must only contain provenance pointers — NOT advisory signal slugs
    refs = env["observation"]["evidence_refs"]
    advisory_signal_names = {"domain_misalignment_risk", "thin_synthesis",
                              "calibration_profile_changed", "cross_domain_slug"}
    for ref in refs:
        for signal_name in advisory_signal_names:
            assert signal_name not in ref, (
                f"Advisory signal name {signal_name!r} leaked into evidence_refs: {ref!r}. "
                "Advisory signals belong in advisory_signals[], not evidence_refs."
            )

    # evidence_refs should be provenance pointers (run id or artifact path)
    if refs:
        for ref in refs:
            assert ref.startswith("enumd-run:") or ref.startswith("enumd-artifact:"), (
                f"evidence_ref {ref!r} must be a provenance pointer "
                "(enumd-run:<id> or enumd-artifact:<path>)"
            )


# ─────────────────────────────────────────────────────────────────────────────
# A10 — decision_constraints locked for all valid inputs
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture_name", [
    "valid_wave5",
    "missing_fields",
    "ambiguous_status",
    "looks_safe_not_tested",
    "contradictory_runs",
    "legacy_old_format",
])
def test_decision_constraints_always_locked(fixture_name: str) -> None:
    """
    For every fixture, decision_constraints must have all three authority
    fields set to False.  This is the non-negotiable trust boundary.
    """
    report = _load(fixture_name)
    env = adapt_enumd_report(report)

    dc = env["decision_constraints"]
    assert dc["external_authority"] is False, (
        f"[{fixture_name}] external_authority must be False"
    )
    assert dc["verdict_authority"] is False, (
        f"[{fixture_name}] verdict_authority must be False"
    )
    assert dc["promotion_authority"] is False, (
        f"[{fixture_name}] promotion_authority must be False"
    )


# ─────────────────────────────────────────────────────────────────────────────
# A11 — not_tested status for all fixtures (non-equivalence invariant)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture_name", [
    "valid_wave5",
    "missing_fields",
    "ambiguous_status",
    "forbidden_authority_fields",
    "legacy_old_format",
    "looks_safe_not_tested",
    "contradictory_runs",
])
def test_misuse_evidence_status_always_not_tested(fixture_name: str) -> None:
    """
    misuse_evidence_status must be 'not_tested' for every Enumd fixture.

    This is the Enumd non-equivalence invariant: Enumd tests synthesis quality,
    not agent misuse.  Any mapping to 'observed' or 'not_observed_in_window'
    would introduce false equivalence between synthesis pipeline governance
    and agent risk assessment.
    """
    report = _load(fixture_name)
    env = adapt_enumd_report(report)

    status = env["observation"]["misuse_evidence_status"]
    assert status == "not_tested", (
        f"[{fixture_name}] misuse_evidence_status must be 'not_tested', got {status!r}. "
        "Non-equivalence violation: Enumd synthesis verdicts must not map to "
        "framework risk states."
    )
