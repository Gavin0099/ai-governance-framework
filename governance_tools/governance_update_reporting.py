from __future__ import annotations

import sys
from typing import Any


def console_safe_text(text: str, encoding: str | None = None) -> str:
    target = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(target, errors="replace").decode(target, errors="replace")


def print_console_safe(text: str) -> None:
    sys.stdout.write(console_safe_text(text))
    sys.stdout.write("\n")


def format_governance_maturity_stage(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return [f"governance_maturity_summary={payload}"]
    if payload.get("status") in {"not_available", "not_run"}:
        return [
            "[governance_maturity_summary]",
            "report_only=true",
            f"status={payload.get('status')}",
            f"reason={payload.get('reason')}",
            f"claim_boundary={payload.get('claim_boundary')}",
        ]

    compact = {
        "report_only": payload.get("report_only"),
        "framework_topology": (payload.get("framework_topology") or {}).get("value"),
        "static_self_contained": (payload.get("static_self_contained") or {}).get("value"),
        "runtime_capable": (payload.get("runtime_capable") or {}).get("value"),
        "hook_config_framework_root": (payload.get("hook_config_framework_root") or {}).get("value"),
        "framework_pin_freshness": (payload.get("framework_pin_freshness") or {}).get("value"),
        "lock_consistency": (payload.get("lock_consistency") or {}).get("value"),
        "agents_calibration": (payload.get("agents_calibration") or {}).get("value"),
        "repo_specific_rules": (payload.get("repo_specific_rules_present") or {}).get("value"),
        "domain_contract_present": (payload.get("domain_contract_present") or {}).get("value"),
        "validator_surface": (payload.get("validator_surface_present") or {}).get("value"),
        "memory_workflow_surface": (payload.get("memory_workflow_surface") or {}).get("value"),
        "claim_ceiling": (payload.get("claim_ceiling") or {}).get("value"),
        "missing_surfaces": payload.get("missing_surfaces"),
        "signal_conflicts": len(payload.get("signal_conflicts") or []),
    }
    lines = ["[governance_maturity_summary]"]
    lines.extend(f"{key}={value}" for key, value in compact.items())
    human_summary = payload.get("human_readable_adoption_summary") or []
    if human_summary:
        lines.extend(str(item) for item in human_summary)
    cannot_claim = payload.get("cannot_claim") or []
    if cannot_claim:
        lines.append("cannot_claim=" + "; ".join(str(item) for item in cannot_claim))
    return lines


def build_final_report_requirement(payload: object) -> dict[str, Any]:
    instruction = (
        "Final AI Governance update reports must relay "
        "[human_readable_adoption_summary] table rows as a table, not a prose "
        "summary. Reporting only machine-readable fields, build/test results, "
        "adoption_doctor findings, or a framework pointer update is incomplete."
    )
    requirement: dict[str, Any] = {
        "status": "not_available",
        "instruction": instruction,
        "required_marker": "[human_readable_adoption_summary]",
        "human_readable_adoption_summary": [],
        "not_substitutes": [
            "adoption_doctor: findings 0",
            "governance_version_check: compatible",
            "clean build/test results",
            "framework pointer or lock update",
            "machine-readable governance_maturity_summary fields only",
        ],
        "claim_boundary": (
            "This is a reporting requirement only; it does not prove full "
            "governance adoption, runtime enforcement, CI/fleet enforcement, "
            "memory completeness, domain correctness, or release readiness."
        ),
    }
    if not isinstance(payload, dict):
        requirement["reason"] = "governance_maturity_summary is not a structured object"
        return requirement
    human_summary = [str(item) for item in payload.get("human_readable_adoption_summary") or []]
    if human_summary:
        requirement["status"] = "required"
        requirement["human_readable_adoption_summary"] = human_summary
        requirement["required_header"] = (
            human_summary[1] if len(human_summary) > 1 else "table header not reported"
        )
        return requirement
    requirement["reason"] = (
        payload.get("reason")
        or f"governance_maturity_summary status={payload.get('status', 'unknown')}"
    )
    return requirement


def build_final_report_table_required(requirement: object) -> dict[str, Any]:
    instruction = (
        "Copy these [human_readable_adoption_summary] rows into the final report "
        "as a table. Do not replace them with prose or only machine-readable fields."
    )
    table: dict[str, Any] = {
        "status": "not_available",
        "required_marker": "[human_readable_adoption_summary]",
        "instruction": instruction,
        "table_rows": [],
        "must_relay_as": "table_rows_verbatim",
        "claim_boundary": (
            "Reporting aid only; table relay does not prove full governance adoption, "
            "runtime enforcement, CI/fleet enforcement, memory completeness, domain "
            "correctness, or release readiness."
        ),
    }
    if not isinstance(requirement, dict):
        table["reason"] = "final_report_requirement is not a structured object"
        return table
    rows = [str(item) for item in requirement.get("human_readable_adoption_summary") or []]
    if rows:
        table["status"] = "required"
        table["table_rows"] = rows
        table["row_count"] = len(rows)
        return table
    table["reason"] = requirement.get("reason") or "human_readable_adoption_summary unavailable"
    return table


def _summary_value(payload: object, key: str, default: str = "not_reported") -> str:
    if not isinstance(payload, dict):
        return default
    value = payload.get(key)
    if isinstance(value, dict):
        raw = value.get("value")
        return str(raw) if raw is not None else default
    return str(value) if value is not None else default


def _governance_maturity_presence(payload: object) -> tuple[str, str | None]:
    if not isinstance(payload, dict):
        return "not_available", "governance_maturity_summary is not a structured object"
    status = payload.get("status")
    if status in {"not_available", "not_run"}:
        return str(status), str(payload.get("reason") or f"status={status}")
    return "present", None


def _human_summary_presence(payload: object) -> tuple[str, str | None]:
    if not isinstance(payload, dict):
        return "not_reported", "governance_maturity_summary is not a structured object"
    rows = payload.get("human_readable_adoption_summary") or []
    if rows:
        return "reported", None
    return "not_reported", str(
        payload.get("reason") or "human_readable_adoption_summary unavailable"
    )


def _final_report_requirement_presence(requirement: object) -> tuple[str, str | None]:
    if not isinstance(requirement, dict):
        return "not_available", "final_report_requirement is not a structured object"
    return "present", None


def build_ai_governance_update_result(
    *,
    framework_update_status: str,
    framework_update_source: str,
    governance_maturity_summary: object,
    final_report_requirement: object,
    evidence_refs: list[dict[str, Any]] | None = None,
    cannot_claim: list[str] | None = None,
) -> dict[str, Any]:
    """Build the report-only unified AI Governance update status envelope."""
    maturity_value, maturity_reason = _governance_maturity_presence(
        governance_maturity_summary
    )
    human_value, human_reason = _human_summary_presence(governance_maturity_summary)
    final_report_value, final_report_reason = _final_report_requirement_presence(
        final_report_requirement
    )
    adoption_status = _summary_value(
        governance_maturity_summary,
        "user_facing_status",
        default="not_reported",
    )
    adoption_source = (
        "governance_maturity_summary.user_facing_status"
        if adoption_status != "not_reported"
        else "not_reported"
    )
    lock_consistency = _summary_value(
        governance_maturity_summary,
        "lock_consistency",
        default="unknown",
    )
    if lock_consistency == "not_reported":
        lock_consistency = "unknown"

    inherited_cannot = []
    if isinstance(governance_maturity_summary, dict):
        inherited_cannot = [
            str(item) for item in governance_maturity_summary.get("cannot_claim") or []
        ]
    base_cannot = [
        "full governance adoption",
        "runtime enforcement",
        "CI/fleet enforcement",
        "memory completeness",
        "domain correctness",
        "release readiness",
    ]
    merged_cannot = sorted(
        {*(cannot_claim or []), *inherited_cannot, *base_cannot}
    )

    envelope: dict[str, Any] = {
        "report_only": True,
        "framework_update_status": {
            "value": framework_update_status,
            "source": framework_update_source,
        },
        "adoption_status": {
            "value": adoption_status,
            "source": adoption_source,
        },
        "lock_consistency": {
            "value": lock_consistency,
            "source": "governance_maturity_summary.lock_consistency",
        },
        "governance_maturity_summary": {
            "value": maturity_value,
        },
        "human_readable_adoption_summary": {
            "value": human_value,
        },
        "final_report_requirement": {
            "value": final_report_value,
            "source": framework_update_source,
        },
        "cannot_claim": merged_cannot,
        "evidence_refs": evidence_refs or [],
    }
    if maturity_reason:
        envelope["governance_maturity_summary"]["reason"] = maturity_reason
    if human_reason:
        envelope["human_readable_adoption_summary"]["reason"] = human_reason
    if final_report_reason:
        envelope["final_report_requirement"]["reason"] = final_report_reason
    return envelope


def format_ai_governance_update_result(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return [f"ai_governance_update_result={payload}"]
    framework = payload.get("framework_update_status") or {}
    adoption = payload.get("adoption_status") or {}
    lock = payload.get("lock_consistency") or {}
    maturity = payload.get("governance_maturity_summary") or {}
    human = payload.get("human_readable_adoption_summary") or {}
    final_report = payload.get("final_report_requirement") or {}

    lines = [
        "[ai_governance_update_result]",
        f"report_only={str(payload.get('report_only')).lower()}",
        f"framework_update_status={framework.get('value')}",
        f"framework_update_status_source={framework.get('source')}",
        f"adoption_status={adoption.get('value')}",
        f"adoption_status_source={adoption.get('source')}",
        f"lock_consistency={lock.get('value')}",
        f"lock_consistency_source={lock.get('source')}",
        f"governance_maturity_summary={maturity.get('value')}",
        f"human_readable_adoption_summary={human.get('value')}",
        f"final_report_requirement={final_report.get('value')}",
        f"final_report_requirement_source={final_report.get('source')}",
    ]
    for section, prefix in (
        (maturity, "governance_maturity_summary_reason"),
        (human, "human_readable_adoption_summary_reason"),
        (final_report, "final_report_requirement_reason"),
    ):
        reason = section.get("reason") if isinstance(section, dict) else None
        if reason:
            lines.append(f"{prefix}={reason}")

    cannot_claim = payload.get("cannot_claim") or []
    if cannot_claim:
        lines.append("cannot_claim=" + "; ".join(str(item) for item in cannot_claim))
    evidence_refs = payload.get("evidence_refs") or []
    if evidence_refs:
        lines.append("evidence_refs:")
        for item in evidence_refs:
            if isinstance(item, dict):
                lines.append(
                    "- "
                    + ", ".join(f"{key}={value}" for key, value in sorted(item.items()))
                )
            else:
                lines.append(f"- {item}")
    return lines


def format_final_report_requirement(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return [f"final_report_requirement={payload}"]
    lines = [
        "[final_report_requirement]",
        f"status={payload.get('status')}",
        f"instruction={payload.get('instruction')}",
        f"claim_boundary={payload.get('claim_boundary')}",
    ]
    reason = payload.get("reason")
    if reason:
        lines.append(f"reason={reason}")
    human_summary = payload.get("human_readable_adoption_summary") or []
    if human_summary:
        lines.extend(str(item) for item in human_summary)
    return lines
