from __future__ import annotations

import json
from pathlib import Path

from governance_tools.reason_code_verifier import verify_gate_consumed_reason_fields


def _write_registry(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "| code | type | short meaning | current usage location |",
                "|---|---|---|---|",
                "| `production_fix_required` | reason_code | x | y |",
                "| `block_if_count_exceeds` | policy_mode_code | x | y |",
                "| `test_result_artifact_absent` | reason_code | x | y |",
            ]
        ),
        encoding="utf-8",
    )


def test_reason_code_verifier_passes_for_registered_codes(tmp_path: Path) -> None:
    registry = tmp_path / "reason-code-registry.md"
    gate_policy = tmp_path / "gate_policy.yaml"
    audit_log = tmp_path / "canonical-audit-log.jsonl"

    _write_registry(registry)
    gate_policy.write_text(
        "\n".join(
            [
                "blocking_actions:",
                "  - production_fix_required",
                "unknown_treatment:",
                "  mode: block_if_count_exceeds",
            ]
        ),
        encoding="utf-8",
    )
    audit_log.write_text(
        json.dumps({"signals": ["test_result_artifact_absent"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = verify_gate_consumed_reason_fields(registry, gate_policy, audit_log)
    assert result.ok
    assert result.violations == []


def test_reason_code_verifier_rejects_free_text_reason(tmp_path: Path) -> None:
    registry = tmp_path / "reason-code-registry.md"
    gate_policy = tmp_path / "gate_policy.yaml"
    audit_log = tmp_path / "canonical-audit-log.jsonl"

    _write_registry(registry)
    gate_policy.write_text(
        "\n".join(
            [
                "blocking_actions:",
                "  - this is free text reason",  # intentionally invalid
                "unknown_treatment:",
                "  mode: block_if_count_exceeds",
            ]
        ),
        encoding="utf-8",
    )
    audit_log.write_text(
        json.dumps({"signals": ["test_result_artifact_absent"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = verify_gate_consumed_reason_fields(registry, gate_policy, audit_log)
    assert not result.ok
    assert any("non-registered code" in item for item in result.violations)


def test_reason_code_verifier_rejects_free_text_in_realistic_gate_policy_shape(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "reason-code-registry.md"
    gate_policy = tmp_path / "gate_policy.yaml"
    audit_log = tmp_path / "canonical-audit-log.jsonl"

    _write_registry(registry)
    gate_policy.write_text(
        "\n".join(
            [
                'version: "1"',
                "fail_mode: strict",
                "blocking_actions:",
                "  - production_fix_required",
                "unknown_treatment:",
                "  mode: this mode is human prose and must fail",  # intentionally invalid
                "  threshold: 3",
                "artifact_stale_seconds: 86400",
            ]
        ),
        encoding="utf-8",
    )
    audit_log.write_text(
        json.dumps({"signals": ["test_result_artifact_absent"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = verify_gate_consumed_reason_fields(registry, gate_policy, audit_log)
    assert not result.ok
    assert any("unknown_treatment.mode" in item for item in result.violations)
