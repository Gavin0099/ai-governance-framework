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
