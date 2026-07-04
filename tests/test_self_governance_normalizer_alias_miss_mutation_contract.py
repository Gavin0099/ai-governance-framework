from __future__ import annotations

from runtime_hooks.adapters.shared_normalizer import (
    detect_unmapped_gate_keys,
    normalize_payload,
)


def test_unmapped_gate_relevant_keys_are_surfaced() -> None:
    # S1 (remediated, advisory): gate-relevant content under unrecognized names
    # is silently dropped from the mapped fields but is now surfaced.
    payload = {
        "task": "do the thing",
        "project_root": "/repo",
        "evidence": "these tests passed",
        "proof_file": "/repo/proof.json",
        "risk_score": "high",
    }

    unmapped = detect_unmapped_gate_keys(payload)

    assert "evidence" in unmapped
    assert "proof_file" in unmapped
    assert "risk_score" in unmapped


def test_normalize_payload_exposes_unmapped_keys_without_changing_mapped_fields() -> None:
    payload = {
        "task": "do the thing",
        "project_root": "/repo",
        "risk": "high",
        "evidence": "unmapped evidence blob",
    }

    normalized = normalize_payload(payload, harness="codex", event_type="post_task")

    # Mapped fields and gating inputs are unchanged.
    assert normalized["task"] == "do the thing"
    assert normalized["risk"] == "high"
    assert "evidence" not in normalized  # still silently dropped from mapped shape
    # But the drop is now visible.
    assert normalized["metadata"]["unmapped_gate_relevant_keys"] == ["evidence"]


def test_properly_aliased_payload_surfaces_nothing() -> None:
    # Regression: a payload using recognized aliases must not be flagged.
    payload = {
        "task": "do the thing",
        "project_root": "/repo",
        "evidence_file": "/repo/checks.json",  # recognized alias for checks_file
        "risk_level": "high",  # recognized alias for risk
        "response_file": "/repo/out.md",
    }

    normalized = normalize_payload(payload, harness="claude_code", event_type="post_task")

    assert normalized["metadata"]["unmapped_gate_relevant_keys"] == []
    assert normalized["checks_file"] == "/repo/checks.json"
    assert normalized["risk"] == "high"


def test_obscure_key_name_without_token_stays_vulnerable_baseline() -> None:
    # S2 (VULNERABLE baseline): a gate-relevant value under a name that contains
    # none of the gate-relevant tokens is neither mapped nor surfaced. Pinned:
    # if a strict unknown-key schema is adopted later, this should fail and force
    # a contract/catalog update.
    payload = {
        "task": "do the thing",
        "project_root": "/repo",
        "xyz": "actually the real test evidence, hidden under an opaque key",
    }

    unmapped = detect_unmapped_gate_keys(payload)
    normalized = normalize_payload(payload, harness="gemini", event_type="post_task")

    assert "xyz" not in unmapped
    assert normalized["metadata"]["unmapped_gate_relevant_keys"] == []


def test_harness_agnostic_detection_is_identical_across_harnesses() -> None:
    # The advisory field must be harness-agnostic (no per-harness path).
    payload = {"task": "t", "project_root": "/r", "attestation_blob": "x"}
    a = normalize_payload(payload, harness="claude_code", event_type="pre_task")
    b = normalize_payload(payload, harness="hermes", event_type="pre_task")
    assert (
        a["metadata"]["unmapped_gate_relevant_keys"]
        == b["metadata"]["unmapped_gate_relevant_keys"]
        == ["attestation_blob"]
    )
