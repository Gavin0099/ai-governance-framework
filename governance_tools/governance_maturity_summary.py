#!/usr/bin/env python3
"""
Derived report-only presentation for AI Governance adoption maturity.

This helper combines existing local diagnostics into a single summary for
operator-facing output. It does not install, update, fetch, repair, stage,
rewrite, gate, or enforce anything.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from governance_tools.adoption_doctor import AdoptionDoctorReport, inspect_adoption
from governance_tools.agents_calibration_maturity import (
    AgentsCalibrationMaturity,
    assess_agents_calibration_maturity,
)
from governance_tools.domain_contract_loader import load_domain_contract, resolve_domain_contract


REPORT_VERSION = "0.1"


@dataclass
class SummaryValue:
    value: object
    source: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class SignalConflict:
    field: str
    sources: dict[str, str]
    action: str = "manual_review_required"


@dataclass
class GovernanceMaturitySummary:
    report_version: str
    repo_root: str
    report_only: bool
    user_facing_status: SummaryValue
    framework_topology: SummaryValue
    static_self_contained: SummaryValue
    runtime_capable: SummaryValue
    hook_config_framework_root: SummaryValue
    framework_pin_freshness: SummaryValue
    agents_calibration: SummaryValue
    repo_specific_rules_present: SummaryValue
    domain_contract_present: SummaryValue
    validator_surface_present: SummaryValue
    memory_workflow_surface: SummaryValue
    human_readable_adoption_summary: list[str] = field(default_factory=list)
    missing_surfaces: list[str] = field(default_factory=list)
    signal_conflicts: list[SignalConflict] = field(default_factory=list)
    claim_ceiling: SummaryValue = field(
        default_factory=lambda: SummaryValue(
            "governance_assisted",
            "governance_maturity_summary.derived",
        )
    )
    cannot_claim: list[str] = field(default_factory=list)
    claim_boundary: str = (
        "This summary is report-only. It does not prove full governance adoption, "
        "runtime self-contained execution, hook enforcement, memory completeness, "
        "domain correctness, or release readiness."
    )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _summary_value(value: object, source: str, reasons: list[str] | None = None) -> SummaryValue:
    return SummaryValue(value=value, source=source, reasons=list(reasons or []))


def _repo_specific_rules_present(status: str) -> bool:
    return status in {"repo_specific_minimal", "reviewer_verified"}


def _load_contract_surface(repo_root: Path) -> tuple[SummaryValue, SummaryValue]:
    candidate = repo_root / "contract.yaml"
    if not candidate.is_file():
        return (
            _summary_value(False, "domain_contract_loader.resolve_domain_contract", ["contract.yaml not found"]),
            _summary_value(
                "not_checked",
                "domain_contract_loader.load_domain_contract.validators",
                ["contract.yaml not found"],
            ),
        )

    contract_path = resolve_domain_contract(candidate, project_root=repo_root)
    if contract_path is None:
        return (
            _summary_value(False, "domain_contract_loader.resolve_domain_contract", ["contract.yaml could not be resolved"]),
            _summary_value(
                "not_checked",
                "domain_contract_loader.load_domain_contract.validators",
                ["contract.yaml could not be resolved"],
            ),
        )

    try:
        contract = load_domain_contract(contract_path, skip_document_content=True)
    except (OSError, ValueError) as exc:
        return (
            _summary_value(True, "domain_contract_loader.resolve_domain_contract", [str(contract_path)]),
            _summary_value(
                "not_checked",
                "domain_contract_loader.load_domain_contract.validators",
                [f"contract load failed: {exc}"],
            ),
        )

    validators = (contract or {}).get("validators") or []
    validator_exists = any(bool(item.get("exists")) for item in validators if isinstance(item, dict))
    if validators:
        reason = "at least one validator file exists" if validator_exists else "validators declared but no validator file exists"
        value: object = bool(validator_exists)
    else:
        reason = "no validators declared"
        value = False
    return (
        _summary_value(True, "domain_contract_loader.resolve_domain_contract", [str(contract_path)]),
        _summary_value(value, "domain_contract_loader.load_domain_contract.validators", [reason]),
    )


def _derive_missing_surfaces(
    adoption_report: AdoptionDoctorReport,
    agents_report: AgentsCalibrationMaturity,
    domain_contract_present: SummaryValue,
    validator_surface_present: SummaryValue,
) -> list[str]:
    missing: list[str] = []
    if adoption_report.adoption_class.value == "copy_based":
        missing.append("runtime_self_contained_governance")
    if adoption_report.self_contained.value != "yes":
        missing.append("static_self_contained_framework")
    if adoption_report.submodule_pin.value in {"behind_local_tracking", "unknown"}:
        missing.append("framework_pin_freshness")
    if not _repo_specific_rules_present(agents_report.status):
        missing.append("repo_specific_agents_rules")
    if domain_contract_present.value is False:
        missing.append("domain_contract")
    if validator_surface_present.value is False:
        missing.append("validator_surface")
    if adoption_report.hook_config_framework_root.value == "external" and adoption_report.adoption_class.value in {
        "repo_owned_framework_path",
        "submodule_consumer",
    }:
        missing.append("repo_owned_hook_execution")
    return missing


def _derive_conflicts(adoption_report: AdoptionDoctorReport) -> list[SignalConflict]:
    conflicts: list[SignalConflict] = []
    if adoption_report.hook_config_framework_root.value == "external" and adoption_report.adoption_class.value in {
        "repo_owned_framework_path",
        "submodule_consumer",
    }:
        conflicts.append(
            SignalConflict(
                field="hooks",
                sources={
                    "adoption_doctor.adoption_class": adoption_report.adoption_class.value,
                    "adoption_doctor.hook_config_framework_root": adoption_report.hook_config_framework_root.value,
                },
            )
        )
    return conflicts


def _derive_claim_ceiling(
    adoption_report: AdoptionDoctorReport,
    repo_specific_rules_present: bool,
) -> SummaryValue:
    if adoption_report.adoption_class.value == "copy_based":
        return _summary_value("governance_assisted", "governance_maturity_summary.derived")
    if repo_specific_rules_present:
        return _summary_value("repo_specific_assisted", "governance_maturity_summary.derived")
    if adoption_report.self_contained.value == "yes":
        return _summary_value("static_self_contained_not_runtime_verified", "governance_maturity_summary.derived")
    return _summary_value("partial_governance_surface", "governance_maturity_summary.derived")


def _derive_user_facing_status(
    adoption_report: AdoptionDoctorReport,
    repo_specific_rules_present: bool,
    domain_contract_present: SummaryValue,
    validator_surface_present: SummaryValue,
    missing_surfaces: list[str],
    signal_conflicts: list[SignalConflict],
) -> SummaryValue:
    topology = adoption_report.adoption_class.value
    reasons: list[str] = []

    if topology == "unknown":
        validator_absent = validator_surface_present.value in {False, "not_checked"}
        if (
            not repo_specific_rules_present
            and domain_contract_present.value is False
            and validator_absent
        ):
            return _summary_value(
                "not_governed",
                "governance_maturity_summary.derived",
                ["No repo-specific governance surfaces were detected."],
            )
        return _summary_value(
            "unknown",
            "governance_maturity_summary.derived",
            ["Governance signals are incomplete or ambiguous; manual review is required."],
        )

    if topology == "copy_based":
        return _summary_value(
            "minimal",
            "governance_maturity_summary.derived",
            [
                "Basic governance guidance is present, but the repo does not own a runtime-capable framework checkout.",
                "This is useful for agent guidance, not full governance adoption.",
            ],
        )

    if signal_conflicts:
        reasons.append("Some governance signals conflict and require manual review.")

    if missing_surfaces:
        reasons.append("Missing surfaces: " + ", ".join(missing_surfaces))

    pin_state = adoption_report.submodule_pin.value
    static_complete = adoption_report.self_contained.value == "yes"
    pin_acceptable = pin_state == "current_vs_local_tracking"
    hooks_inside_repo = adoption_report.hook_config_framework_root.value == "inside_repo"
    domain_ready = domain_contract_present.value is True
    validator_ready = validator_surface_present.value is True

    if (
        topology in {"repo_owned_framework_path", "submodule_consumer"}
        and static_complete
        and pin_acceptable
        and hooks_inside_repo
        and repo_specific_rules_present
        and domain_ready
        and validator_ready
        and not signal_conflicts
    ):
        return _summary_value(
            "full_candidate",
            "governance_maturity_summary.derived",
            [
                "Visible static governance surfaces are present.",
                "This is still only a candidate; runtime enforcement and semantic correctness are not proven.",
            ],
        )

    if not reasons:
        reasons.append("Some governance surfaces are present, but the visible evidence is not enough for full_candidate.")
    return _summary_value("partial", "governance_maturity_summary.derived", reasons)


def _derive_cannot_claim(adoption_report: AdoptionDoctorReport, agents_report: AgentsCalibrationMaturity) -> list[str]:
    cannot = {
        "full governance adoption",
        "runtime self-contained governance",
        "hook or CI enforcement",
        "runtime smoke passed",
        "domain correctness",
        "memory consolidation completeness",
        "release readiness",
    }
    if adoption_report.submodule_pin.value != "current_vs_local_tracking":
        cannot.add("framework pin freshness")
    else:
        cannot.add("framework pin matches the true remote head")
    if not _repo_specific_rules_present(agents_report.status):
        cannot.add("repo-specific rules are present")
    return sorted(cannot)


def _present_absent(value: object) -> str:
    return "present" if value is True else "missing"


def _plain_status_meaning(status: object) -> str:
    meanings = {
        "not_governed": "no repo-specific AI Governance surfaces were detected",
        "minimal": "basic guidance exists, but this is not a full framework integration",
        "partial": "some AI Governance surfaces are installed, but at least one required surface is still missing",
        "full_candidate": "visible static surfaces are present; runtime enforcement is still not proven",
        "unknown": "signals are incomplete or ambiguous and need manual review",
    }
    return meanings.get(str(status), "manual review is required")


def _surface_line(label: str, status: str, explanation: str) -> str:
    return f"- {label}: {status} - {explanation}"


def _derive_human_readable_adoption_summary(
    *,
    user_facing_status: SummaryValue,
    framework_topology: SummaryValue,
    static_self_contained: SummaryValue,
    runtime_capable: SummaryValue,
    hook_config_framework_root: SummaryValue,
    framework_pin_freshness: SummaryValue,
    repo_specific_rules_present: SummaryValue,
    domain_contract_present: SummaryValue,
    validator_surface_present: SummaryValue,
    memory_workflow_surface: SummaryValue,
    missing_surfaces: list[str],
    cannot_claim: list[str],
) -> list[str]:
    lines = [
        "[human_readable_adoption_summary]",
        "Purpose: this section explains, in operator-facing language, which AI Governance capabilities appear installed.",
        (
            f"Overall adoption status: {user_facing_status.value} - "
            f"{_plain_status_meaning(user_facing_status.value)}."
        ),
        "What this update/status check confirms:",
    ]

    framework_status = "present" if framework_topology.value in {
        "repo_owned_framework_path",
        "submodule_consumer",
    } else "not full-framework-owned"
    lines.append(
        _surface_line(
            "AI Governance framework checkout",
            framework_status,
            f"detected topology is {framework_topology.value}",
        )
    )
    lines.append(
        _surface_line(
            "Framework version freshness",
            str(framework_pin_freshness.value),
            "compares the local framework checkout with the locally known tracking ref; it is not proof of the true remote head",
        )
    )
    lines.append(
        _surface_line(
            "Repo governance instructions",
            _present_absent(repo_specific_rules_present.value),
            "AGENTS.md contains repo-specific governance rules for agents to follow",
        )
    )
    lines.append(
        _surface_line(
            "Static framework files",
            str(static_self_contained.value),
            "checks whether the visible framework files are self-contained in this repo layout",
        )
    )
    lines.append(
        _surface_line(
            "Runtime-capable governance",
            str(runtime_capable.value),
            "runtime execution is not proven by this summary",
        )
    )
    lines.append(
        _surface_line(
            "Git hook framework root",
            str(hook_config_framework_root.value),
            "shows where local pre-commit/pre-push hooks point; hooks are local machine state, not proof of enforcement everywhere",
        )
    )
    lines.append(
        _surface_line(
            "Domain contract",
            _present_absent(domain_contract_present.value),
            "contract.yaml declares the repo-specific governance contract",
        )
    )
    lines.append(
        _surface_line(
            "Validator surface",
            _present_absent(validator_surface_present.value),
            "validators are the repo-specific automated checks declared by the contract",
        )
    )
    lines.append(
        _surface_line(
            "Memory workflow surface",
            str(memory_workflow_surface.value),
            "memory completeness is not inferred by this summary",
        )
    )

    if missing_surfaces:
        lines.append("Still missing or not fully proven:")
        lines.extend(f"- {surface}: needs follow-up before claiming full adoption" for surface in missing_surfaces)
    else:
        lines.append("Still missing or not fully proven: none detected by this report-only summary.")

    lines.append("Plain-language conclusion:")
    if user_facing_status.value == "full_candidate":
        lines.append(
            "- AI Governance appears fully present at the visible static-surface level, but runtime enforcement is still not proven."
        )
    elif user_facing_status.value == "partial":
        lines.append(
            "- AI Governance is partially adopted: core surfaces are present, but this repo is not ready to claim full adoption."
        )
    elif user_facing_status.value == "minimal":
        lines.append(
            "- AI Governance guidance is present, but the repo has not adopted the full framework surface."
        )
    elif user_facing_status.value == "not_governed":
        lines.append("- This repo does not appear governed by AI Governance yet.")
    else:
        lines.append("- Adoption status is unclear; manual review is required.")

    if cannot_claim:
        lines.append("Do not claim from this summary:")
        lines.extend(f"- {item}" for item in cannot_claim)
    return lines


def _pin_reasons(adoption_report: AdoptionDoctorReport) -> list[str]:
    pin = adoption_report.submodule_pin
    reasons = list(pin.reasons)
    if pin.remote_tracking_ref:
        reasons.append(f"remote_tracking_ref={pin.remote_tracking_ref}")
    reasons.append(f"remote_tracking_freshness={pin.remote_tracking_freshness}")
    if pin.last_fetch:
        reasons.append(f"last_fetch={pin.last_fetch}")
    if pin.value == "current_vs_local_tracking":
        reasons.append("current_vs_local_tracking is not proof of true remote currentness")
    return reasons


def build_governance_maturity_summary(
    repo_root: str | Path,
    *,
    framework_root: str | Path | None = None,
) -> GovernanceMaturitySummary:
    repo = Path(repo_root).resolve()
    framework = Path(framework_root).resolve() if framework_root is not None else None
    adoption_report = inspect_adoption(repo, framework_root=framework)
    agents_report = assess_agents_calibration_maturity(repo)
    domain_contract_present, validator_surface_present = _load_contract_surface(repo)
    repo_specific_present = _repo_specific_rules_present(agents_report.status)
    missing_surfaces = _derive_missing_surfaces(
        adoption_report,
        agents_report,
        domain_contract_present,
        validator_surface_present,
    )
    signal_conflicts = _derive_conflicts(adoption_report)
    claim_ceiling = _derive_claim_ceiling(adoption_report, repo_specific_present)
    cannot_claim = _derive_cannot_claim(adoption_report, agents_report)
    user_facing_status = _derive_user_facing_status(
        adoption_report,
        repo_specific_present,
        domain_contract_present,
        validator_surface_present,
        missing_surfaces,
        signal_conflicts,
    )
    framework_topology = _summary_value(
        adoption_report.adoption_class.value,
        "adoption_doctor.adoption_class",
        adoption_report.adoption_class.reasons,
    )
    static_self_contained = _summary_value(
        adoption_report.self_contained.value,
        "adoption_doctor.self_contained",
        adoption_report.self_contained.reasons,
    )
    runtime_capable = _summary_value(
        adoption_report.runtime_capable.value,
        "adoption_doctor.runtime_capable",
        adoption_report.runtime_capable.reasons,
    )
    hook_config_framework_root = _summary_value(
        adoption_report.hook_config_framework_root.value,
        "adoption_doctor.hook_config_framework_root",
        adoption_report.hook_config_framework_root.reasons,
    )
    framework_pin_freshness = _summary_value(
        adoption_report.submodule_pin.value,
        "adoption_doctor.submodule_pin",
        _pin_reasons(adoption_report),
    )
    agents_calibration = _summary_value(
        agents_report.status,
        "agents_calibration_maturity.status",
        [agents_report.reason],
    )
    repo_specific_rules_present = _summary_value(
        repo_specific_present,
        "agents_calibration_maturity.status",
        [agents_report.reason],
    )
    memory_workflow_surface = _summary_value(
        "not_checked",
        "governance_maturity_summary.memory_workflow_surface",
        ["memory consolidation completeness is not inferred by this summary"],
    )
    human_readable_adoption_summary = _derive_human_readable_adoption_summary(
        user_facing_status=user_facing_status,
        framework_topology=framework_topology,
        static_self_contained=static_self_contained,
        runtime_capable=runtime_capable,
        hook_config_framework_root=hook_config_framework_root,
        framework_pin_freshness=framework_pin_freshness,
        repo_specific_rules_present=repo_specific_rules_present,
        domain_contract_present=domain_contract_present,
        validator_surface_present=validator_surface_present,
        memory_workflow_surface=memory_workflow_surface,
        missing_surfaces=missing_surfaces,
        cannot_claim=cannot_claim,
    )

    return GovernanceMaturitySummary(
        report_version=REPORT_VERSION,
        repo_root=str(repo),
        report_only=True,
        user_facing_status=user_facing_status,
        framework_topology=framework_topology,
        static_self_contained=static_self_contained,
        runtime_capable=runtime_capable,
        hook_config_framework_root=hook_config_framework_root,
        framework_pin_freshness=framework_pin_freshness,
        agents_calibration=agents_calibration,
        repo_specific_rules_present=repo_specific_rules_present,
        domain_contract_present=domain_contract_present,
        validator_surface_present=validator_surface_present,
        memory_workflow_surface=memory_workflow_surface,
        human_readable_adoption_summary=human_readable_adoption_summary,
        missing_surfaces=missing_surfaces,
        signal_conflicts=signal_conflicts,
        claim_ceiling=claim_ceiling,
        cannot_claim=cannot_claim,
    )


def summary_to_dict(summary: GovernanceMaturitySummary) -> dict[str, object]:
    return summary.to_dict()


def format_human(summary: GovernanceMaturitySummary) -> str:
    lines = [
        "[governance_maturity_summary]",
        f"report_only              = {str(summary.report_only).lower()}",
        f"user_facing_status       = {summary.user_facing_status.value}",
        "user_facing_meaning      = " + " ".join(summary.user_facing_status.reasons),
        f"framework_topology       = {summary.framework_topology.value}",
        f"static_self_contained    = {summary.static_self_contained.value}",
        f"runtime_capable          = {summary.runtime_capable.value}",
        f"hook_config_framework_root = {summary.hook_config_framework_root.value}",
        f"framework_pin_freshness  = {summary.framework_pin_freshness.value}",
        f"agents_calibration       = {summary.agents_calibration.value}",
        f"repo_specific_rules      = {str(summary.repo_specific_rules_present.value).lower()}",
        f"domain_contract_present = {str(summary.domain_contract_present.value).lower()}",
        f"validator_surface        = {str(summary.validator_surface_present.value).lower()}",
        f"memory_workflow_surface  = {summary.memory_workflow_surface.value}",
        f"claim_ceiling            = {summary.claim_ceiling.value}",
        f"missing_surfaces         = {', '.join(summary.missing_surfaces) if summary.missing_surfaces else '<none>'}",
        f"signal_conflicts         = {len(summary.signal_conflicts)}",
        "claim_boundary           = "
        "report-only; does not prove full governance adoption, runtime self-contained execution, "
        "hook enforcement, memory completeness, domain correctness, or release readiness",
    ]
    if summary.human_readable_adoption_summary:
        lines.extend(summary.human_readable_adoption_summary)
    if summary.cannot_claim:
        lines.append("[cannot_claim]")
        lines.extend(f"- {item}" for item in summary.cannot_claim)
    if summary.signal_conflicts:
        lines.append("[signal_conflicts]")
        for conflict in summary.signal_conflicts:
            source_text = ", ".join(f"{key}={value}" for key, value in conflict.sources.items())
            lines.append(f"- {conflict.field}: {source_text}; action={conflict.action}")
    return "\n".join(lines)
