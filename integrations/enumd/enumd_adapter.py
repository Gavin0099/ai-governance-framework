#!/usr/bin/env python3
"""
integrations/enumd/enumd_adapter.py

Enumd-specific adapter layer.

Pipeline position:
    Enumd raw report  ->  enumd_adapter  ->  external_observation_adapter
                                              ->  canonical advisory envelope

Responsibilities
----------------
1. Accept a validated Enumd governance_report dict (already passed through
   integrations/enumd/ingestor.validate_report).
2. Map Enumd-specific fields to the generic external observation payload
   format that external_observation_adapter.normalize_external_observation
   expects.
3. Enforce Enumd non-equivalences: certain Enumd concepts MUST NOT map to
   stronger framework states.
4. Delegate all trust-boundary enforcement (forbidden authority fields,
   decision_constraints, advisory envelope) to normalize_external_observation.

Envelope output shape
---------------------
{
  "ingest_status"       : "accepted" | "degraded",
  "source"              : { source_id, source_type, producer_version },
  "observation"         : {
      "misuse_evidence_status" : "not_tested",   # always
      "evidence_refs"          : [...],           # provenance pointers only
      "confidence_level"       : "low",           # always
  },
  "advisory"            : { warnings, notes },
  "advisory_signals"    : [                       # Enumd signal slugs — SEPARATE from evidence_refs
      { "signal", "severity", "decision_distance", "source_ref" },
      ...
  ],
  "decision_constraints": { external_authority: False, ... },
  "enumd_provenance"    : { run_id, calibration_profile, semantic_boundary, ... },
}

Semantic split — evidence_refs vs advisory_signals
---------------------------------------------------
evidence_refs      : Pointers to artifacts that could be verified by a human
                     reviewer (e.g. an Enumd audit JSON path).  These are
                     provenance pointers; they carry no evidential weight on
                     their own.
advisory_signals   : Enumd signal slugs extracted from the advisories[] array.
                     These name synthesis-pipeline observations (domain_misalignment_risk,
                     thin_synthesis, etc.) and are Enumd-vocabulary, not framework
                     vocabulary.  They must NOT be treated as evidence strength
                     indicators; they exist for human-readable traceability only.

Keeping these two lists separate prevents downstream consumers from accidentally
treating advisory signal counts as evidence density.

What this adapter intentionally does NOT do
-------------------------------------------
- Produce aggregation_result.current_state
- Produce promote_eligible
- Participate in closure_review_approved
- Re-interpret Enumd calibration thresholds as framework policy
- Derive misuse_evidence_status from Enumd synthesis verdicts

Non-equivalences enforced (see enumd_non_equivalence.md for full table)
-----------------------------------------------------------------------
Enumd KEEP / DOWNGRADE / REMOVE are synthesis pipeline decisions.
They do NOT map to any canonical framework lifecycle state.
misuse_evidence_status is ALWAYS "not_tested" for Enumd observations
because Enumd tests synthesis quality, not agent misuse.
"""

from __future__ import annotations

from typing import Any

from governance_tools.external_observation_adapter import normalize_external_observation

# Enumd fields that would claim decision authority if they somehow appeared
# at the top level of a raw report.  The generic adapter catches these, but
# we surface a specific warning here so the Enumd-layer violation is auditable.
_ENUMD_FORBIDDEN_AUTHORITY_FIELDS = frozenset({
    "verdict",
    "gate_verdict",
    "current_state",
    "closure_verified",
    "promote_eligible",
    "phase3_entry_allowed",
    "closure_review_approved",
})

_ENUMD_ADVISORY_MAX = 10


def _normalize_instrumentation_version(
    raw: Any,
) -> tuple[dict[str, int] | None, str | None]:
    """
    Normalize instrumentation_version into {"major": int, "minor": int}.

    Returns:
      - normalized object when shape is valid
      - optional warning string when a dict is provided but invalid
    """
    if isinstance(raw, dict):
        major = raw.get("major")
        minor = raw.get("minor")
        if isinstance(major, int) and isinstance(minor, int):
            return {"major": major, "minor": minor}, None
        return None, (
            "enumd_adapter: instrumentation_version dict must include integer "
            "major/minor; treating as advisory metadata only"
        )
    return None, None


def _normalize_node_signals_consumed(raw: Any) -> tuple[bool | None, str | None]:
    """
    Normalize nodeSignals_consumed into bool when explicitly present.

    Returns:
      - bool when valid
      - None when absent
      - warning when present but non-bool
    """
    if raw is None:
        return None, None
    if isinstance(raw, bool):
        return raw, None
    return None, (
        "enumd_adapter: nodeSignals_consumed must be boolean when present; "
        "ignoring malformed value"
    )


def _build_advisory_signals(report: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract Enumd advisory signals into structured signal records.

    These go into advisory_signals[], NOT observation.evidence_refs.
    They are Enumd-vocabulary tags (domain_misalignment_risk, thin_synthesis,
    calibration_profile_changed, …) and must not be treated as evidence
    strength indicators by downstream consumers.

    Each record:
        signal           : Enumd signal name
        severity         : as reported by Enumd ("warning" / "info" / "unknown")
        decision_distance: always "advisory_only" per Enumd contract
        source_ref       : "enumd:<signal>:<node_slug>" or "enumd:<signal>"
    """
    signals: list[dict[str, Any]] = []
    advisories = report.get("advisories")
    if not isinstance(advisories, list):
        return signals
    for adv in advisories[:_ENUMD_ADVISORY_MAX]:
        if not isinstance(adv, dict):
            continue
        signal = adv.get("signal")
        if not isinstance(signal, str) or not signal.strip():
            continue
        signal = signal.strip()
        severity = adv.get("severity", "unknown")
        decision_distance = adv.get("decision_distance", "advisory_only")
        details = adv.get("details") or {}
        node_slug = details.get("node_slug") if isinstance(details, dict) else None
        if isinstance(node_slug, str) and node_slug.strip():
            source_ref = f"enumd:{signal}:{node_slug.strip()}"
        else:
            source_ref = f"enumd:{signal}"
        signals.append({
            "signal": signal,
            "severity": severity if isinstance(severity, str) else "unknown",
            "decision_distance": decision_distance if isinstance(decision_distance, str) else "advisory_only",
            "source_ref": source_ref,
        })
    return signals


def _build_provenance_refs(report: dict[str, Any], run_id: str | None) -> list[str]:
    """
    Build observation.evidence_refs from genuine artifact provenance pointers.

    These are paths or identifiers that a human reviewer could follow to locate
    the original Enumd artifacts.  They are provenance pointers, not evidence
    that implies any risk level.

    Only populated if the report supplies raw_artifacts paths.
    """
    refs: list[str] = []
    if run_id:
        refs.append(f"enumd-run:{run_id}")
    raw_artifacts = report.get("raw_artifacts")
    if isinstance(raw_artifacts, dict):
        audit_path = raw_artifacts.get("audit_json_path")
        if isinstance(audit_path, str) and audit_path.strip():
            refs.append(f"enumd-artifact:{audit_path.strip()}")
    return refs


def _derive_producer_version(report: dict[str, Any]) -> str | None:
    """Combine schema_version and instrumentation_version for provenance."""
    schema_v = report.get("schema_version")
    instr_v = report.get("instrumentation_version")
    instr_obj, _ = _normalize_instrumentation_version(instr_v)
    parts = []
    if isinstance(schema_v, str) and schema_v.strip():
        parts.append(f"schema:{schema_v.strip()}")
    if instr_obj is not None:
        parts.append(f"instr:{instr_obj['major']}.{instr_obj['minor']}")
    elif isinstance(instr_v, str) and instr_v.strip():
        parts.append(f"instr:{instr_v.strip()}")
    return "/".join(parts) if parts else None


def adapt_enumd_report(report: dict[str, Any]) -> dict[str, Any]:
    """
    Map a validated Enumd governance_report dict into a canonical advisory
    envelope by routing it through the generic external_observation_adapter.

    Parameters
    ----------
    report:
        A dict representing one Enumd governance_report.json.  The caller is
        responsible for basic JSON parsing; this function performs Enumd-layer
        semantic mapping.

    Returns
    -------
    dict
        The canonical advisory envelope.  See module docstring for full shape.

    Non-equivalence guarantee
    -------------------------
    misuse_evidence_status is ALWAYS "not_tested".
    Enumd observes synthesis pipeline quality, not agent misuse.
    No Enumd verdict (KEEP / DOWNGRADE / REMOVE / THIN_SYNTHESIS) maps to any
    canonical framework lifecycle state.

    Advisory signals vs evidence refs
    ----------------------------------
    Advisory signal slugs extracted from Enumd advisories[] go into
    advisory_signals[], not observation.evidence_refs.
    evidence_refs contains only provenance pointers (run id, artifact paths).
    """
    if not isinstance(report, dict):
        raise ValueError("Enumd report must be a dict")

    warnings: list[str] = []

    # Detect forbidden authority fields at the Enumd layer before the generic
    # adapter sees them, so the violation is attributed to the Enumd source.
    forbidden_seen = sorted(
        k for k in _ENUMD_FORBIDDEN_AUTHORITY_FIELDS if k in report
    )
    if forbidden_seen:
        warnings.append(
            "enumd_adapter: forbidden authority fields detected in raw report: "
            + ", ".join(forbidden_seen)
        )

    # Build source identity
    run_id = report.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        run_id = None
        warnings.append("enumd_adapter: missing run_id — cannot identify source run")

    instrumentation_obj, instrumentation_warning = _normalize_instrumentation_version(
        report.get("instrumentation_version")
    )
    if instrumentation_warning:
        warnings.append(instrumentation_warning)

    node_signals_consumed, consumed_warning = _normalize_node_signals_consumed(
        report.get("nodeSignals_consumed")
    )
    if consumed_warning:
        warnings.append(consumed_warning)

    source_id = f"enumd:{run_id}" if run_id else "enumd:unknown_run"

    # Calibration profile is required for trend analysis disambiguation.
    # Accepting a report without it would make suppression-delta uninterpretable.
    calibration_profile_raw = report.get("calibration_profile")
    if not isinstance(calibration_profile_raw, dict) or not calibration_profile_raw:
        warnings.append(
            "enumd_adapter: missing calibration_profile — trend analysis impossible; "
            "cannot distinguish behavioral change from threshold change"
        )

    # evidence_refs: provenance pointers only (NOT advisory signal slugs)
    evidence_refs = _build_provenance_refs(report, run_id)

    # advisory_signals: Enumd signal slugs — separate vocabulary, separate field
    advisory_signals = _build_advisory_signals(report)

    # Construct generic external observation payload.
    #
    # NON-EQUIVALENCE: misuse_evidence_status is ALWAYS "not_tested".
    # Enumd reports synthesis quality; it has no opinion on agent misuse.
    # confidence_level is ALWAYS "low": Enumd is an external system with
    # domain-calibrated thresholds that do not generalise to the framework.
    generic_payload: dict[str, Any] = {
        "source": {
            "source_id": source_id,
            "source_type": "enumd_governance_report",
            "producer_version": _derive_producer_version(report),
        },
        "observation": {
            "misuse_evidence_status": "not_tested",
            "confidence_level": "low",
            "evidence_refs": evidence_refs,
        },
    }

    # Inject any forbidden authority fields from the raw report into the
    # generic payload so the generic adapter's own authority-field detector
    # fires and records the degradation in decision_constraints.
    for field in forbidden_seen:
        generic_payload[field] = report[field]

    # Delegate all trust-boundary enforcement to the generic adapter.
    envelope = normalize_external_observation(generic_payload)

    # Merge Enumd-layer warnings into the envelope advisory.
    if warnings:
        envelope["advisory"]["warnings"] = warnings + envelope["advisory"]["warnings"]
        # If the Enumd layer raised its own warnings (missing run_id,
        # missing calibration_profile, forbidden fields), force the envelope
        # to degraded regardless of what the generic adapter decided.
        envelope["ingest_status"] = "degraded"

    # Annotate with Enumd-specific non-equivalence note so downstream
    # consumers understand the intentional status mapping.
    envelope["advisory"]["notes"].append(
        "enumd observation: misuse_evidence_status is not_tested by design "
        "(Enumd tests synthesis quality, not agent misuse)"
    )

    # advisory_signals: Enumd-vocabulary signal slugs, separate from evidence_refs.
    # Consumers must NOT treat advisory_signal count as evidence density.
    envelope["advisory_signals"] = advisory_signals

    # Attach Enumd provenance metadata for trend analysis disambiguation.
    # This is read-only context; it carries no decision authority.
    calibration_profile = report.get("calibration_profile")
    semantic_boundary = report.get("semantic_boundary")
    envelope["enumd_provenance"] = {
        "run_id": run_id if isinstance(run_id, str) else None,
        "calibration_profile": calibration_profile if isinstance(calibration_profile, dict) else None,
        "semantic_boundary": semantic_boundary if isinstance(semantic_boundary, dict) else None,
        "represents_agent_behavior": (
            semantic_boundary.get("represents_agent_behavior")
            if isinstance(semantic_boundary, dict)
            else None
        ),
        "nodeSignals_consumed": node_signals_consumed,
        "instrumentation_version": instrumentation_obj,
    }

    return envelope
