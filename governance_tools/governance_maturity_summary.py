#!/usr/bin/env python3
"""
Derived report-only presentation for AI Governance adoption maturity.

This helper combines existing local diagnostics into a single summary for
operator-facing output. It does not install, update, fetch, repair, stage,
rewrite, gate, or enforce anything.
"""

from __future__ import annotations

import json
import subprocess
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
    lock_consistency: SummaryValue
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


def _git_stdout(repo_root: Path, args: list[str]) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _git_success(repo_root: Path, args: list[str]) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode == 0


def _lock_file_dirty(repo_root: Path, lock_path: Path) -> bool | None:
    try:
        rel = lock_path.relative_to(repo_root)
    except ValueError:
        rel = lock_path
    status = _git_stdout(repo_root, ["status", "--porcelain", "--", str(rel)])
    if status is None:
        return None
    return bool(status.strip())


def _load_lock_adopted_commit(lock_path: Path) -> tuple[str | None, str | None]:
    if not lock_path.is_file():
        return None, "governance/framework.lock.json not found"
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"framework lock unreadable: {type(exc).__name__}: {exc}"
    adopted = str(payload.get("adopted_commit", "")).strip()
    if not adopted:
        return None, "framework lock adopted_commit missing"
    return adopted, None


def _is_self_hosting_framework_lock(repo_root: Path, framework_root: Path, lock_path: Path) -> bool:
    if repo_root.resolve() != framework_root.resolve():
        return False
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    note = str(payload.get("_self_reference_note", "")).strip()
    return bool(note)


def _resolve_lock_framework_root(repo_root: Path, framework_root: Path | None) -> Path | None:
    if framework_root is not None:
        return framework_root
    for rel in (
        "additional/ai-governance-framework",
        ".ai-governance-framework",
        "ai-governance-framework",
    ):
        candidate = repo_root / rel
        if candidate.exists():
            return candidate
    return None


def _derive_lock_consistency(repo_root: Path, framework_root: Path | None) -> SummaryValue:
    lock_path = repo_root / "governance" / "framework.lock.json"
    resolved_framework = _resolve_lock_framework_root(repo_root, framework_root)
    if not lock_path.exists():
        return _summary_value(
            "not_applicable",
            "governance_maturity_summary.lock_consistency",
            ["governance/framework.lock.json not found"],
        )
    if resolved_framework is None:
        return _summary_value(
            "unknown",
            "governance_maturity_summary.lock_consistency",
            ["framework checkout root could not be resolved"],
        )
    if _is_self_hosting_framework_lock(repo_root, resolved_framework, lock_path):
        return _summary_value(
            "not_applicable",
            "governance_maturity_summary.lock_consistency",
            [
                "framework root resolves to the target repo itself",
                "governance/framework.lock.json carries _self_reference_note and is a self-assessment baseline",
                "consumer lock-vs-checkout consistency does not apply to the framework repo itself",
            ],
        )

    adopted_commit, lock_error = _load_lock_adopted_commit(lock_path)
    dirty = _lock_file_dirty(repo_root, lock_path)
    dirty_reason = "lock_file_dirty=unknown" if dirty is None else f"lock_file_dirty={str(dirty).lower()}"
    if adopted_commit is None:
        return _summary_value(
            "unknown",
            "governance_maturity_summary.lock_consistency",
            [dirty_reason, lock_error or "framework lock adopted_commit unavailable"],
        )

    framework_head = _git_stdout(resolved_framework, ["rev-parse", "HEAD"])
    if not framework_head:
        return _summary_value(
            "unknown",
            "governance_maturity_summary.lock_consistency",
            [dirty_reason, "framework checkout HEAD could not be read"],
        )

    reasons = [
        dirty_reason,
        f"lock_adopted_commit={adopted_commit}",
        f"framework_head={framework_head}",
        "no fetch was performed; this is a local lock-vs-checkout comparison",
    ]

    if dirty:
        if adopted_commit == framework_head:
            reasons.append("working-tree lock matches checkout HEAD but is not committed")
        elif not _git_success(resolved_framework, ["cat-file", "-e", f"{adopted_commit}^{{commit}}"]):
            reasons.append("working-tree lock commit was not found in the local framework checkout")
        return _summary_value("inconsistent", "governance_maturity_summary.lock_consistency", reasons)

    if adopted_commit == framework_head:
        return _summary_value("consistent", "governance_maturity_summary.lock_consistency", reasons)

    if not _git_success(resolved_framework, ["cat-file", "-e", f"{adopted_commit}^{{commit}}"]):
        reasons.append("lock adopted_commit was not found in the local framework checkout")
        return _summary_value(
            "lock_commit_not_found_locally",
            "governance_maturity_summary.lock_consistency",
            reasons,
        )

    if _git_success(resolved_framework, ["merge-base", "--is-ancestor", adopted_commit, framework_head]):
        reasons.append("direction=lock_behind_checkout")
    elif _git_success(resolved_framework, ["merge-base", "--is-ancestor", framework_head, adopted_commit]):
        reasons.append("direction=lock_ahead_of_checkout")
    else:
        reasons.append("direction=mismatch")
    return _summary_value("inconsistent", "governance_maturity_summary.lock_consistency", reasons)


def _derive_missing_surfaces(
    adoption_report: AdoptionDoctorReport,
    agents_report: AgentsCalibrationMaturity,
    domain_contract_present: SummaryValue,
    validator_surface_present: SummaryValue,
    lock_consistency: SummaryValue,
) -> list[str]:
    missing: list[str] = []
    if adoption_report.adoption_class.value == "copy_based":
        missing.append("runtime_self_contained_governance")
    if adoption_report.self_contained.value != "yes":
        missing.append("static_self_contained_framework")
    if adoption_report.submodule_pin.value in {"behind_local_tracking", "unknown"}:
        missing.append("framework_pin_freshness")
    if lock_consistency.value not in {"consistent", "not_applicable"}:
        missing.append("framework_lock_consistency")
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
        and not missing_surfaces
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


def _derive_cannot_claim(
    adoption_report: AdoptionDoctorReport,
    agents_report: AgentsCalibrationMaturity,
    lock_consistency: SummaryValue,
) -> list[str]:
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
    if lock_consistency.value not in {"consistent", "not_applicable"}:
        cannot.add("framework lock matches the checked-out framework commit")
    if not _repo_specific_rules_present(agents_report.status):
        cannot.add("repo-specific rules are present")
    return sorted(cannot)


def _present_absent(value: object) -> str:
    return "已可用" if value is True else "未導入"


def _plain_status_meaning(status: object) -> str:
    meanings = {
        "not_governed": "沒有偵測到 repo 專屬的 AI Governance 導入表面",
        "minimal": "已有基本治理指引，但還不是完整 framework 導入",
        "partial": "已有部分 AI Governance 功能，但仍缺少至少一個必要表面",
        "full_candidate": "可見的靜態表面已齊備，但 runtime enforcement 仍未被證明",
        "unknown": "訊號不完整或彼此不明確，需要人工判讀",
    }
    return meanings.get(str(status), "需要人工判讀")


def _surface_line(label: str, status: str, explanation: str) -> str:
    return f"- {label}: {status} - {explanation}"


def _capability_status(value: str | bool, *, present_values: set[str] | None = None) -> str:
    if isinstance(value, bool):
        return "已可用" if value else "未導入"
    if value == "not_checked":
        return "未驗證"
    if value in {"unknown", "not_applicable"}:
        return "未知" if value == "unknown" else "不適用"
    diagnostic_statuses = {
        "behind_local_tracking": "已落後",
        "ahead_or_diverged_vs_local_tracking": "不一致",
        "inconsistent": "不一致",
        "lock_commit_not_found_locally": "本地找不到",
    }
    if value in diagnostic_statuses:
        return diagnostic_statuses[value]
    if present_values is not None:
        return "已可用" if value in present_values else "未導入"
    return str(value)


def _capability_row(name: str, status: str, explanation: str) -> str:
    return f"| {name} | {status} | {explanation} |"


def _derive_human_readable_adoption_summary(
    *,
    user_facing_status: SummaryValue,
    framework_topology: SummaryValue,
    static_self_contained: SummaryValue,
    runtime_capable: SummaryValue,
    hook_config_framework_root: SummaryValue,
    framework_pin_freshness: SummaryValue,
    lock_consistency: SummaryValue,
    repo_specific_rules_present: SummaryValue,
    domain_contract_present: SummaryValue,
    validator_surface_present: SummaryValue,
    memory_workflow_surface: SummaryValue,
    missing_surfaces: list[str],
    cannot_claim: list[str],
) -> list[str]:
    lines = [
        "[human_readable_adoption_summary]",
        "用途：這段用人類可讀的方式說明 AI Governance 更新後，目前哪些功能已導入、哪些尚未導入或尚未驗證。",
        (
            f"整體導入狀態：{user_facing_status.value} - "
            f"{_plain_status_meaning(user_facing_status.value)}."
        ),
        "AI Governance 功能導入狀態：",
        "| 功能 | 狀態 | 這個功能是做什麼 |",
        "| --- | --- | --- |",
    ]

    lines.append(
        _capability_row(
            "版本帳實一致性（Lock vs checkout consistency）",
            _capability_status(
                lock_consistency.value,
                present_values={"consistent", "not_applicable"},
            ),
            (
                "比對 governance/framework.lock.json 的 adopted_commit 與本地 framework checkout HEAD；"
                "不做 fetch，也不宣稱真實遠端最新版。"
            ),
        )
    )

    framework_status = "present" if framework_topology.value in {
        "repo_owned_framework_path",
        "submodule_consumer",
    } else "not full-framework-owned"
    lines.extend(
        [
            _capability_row(
                "框架本體（Framework checkout）",
                "已可用" if framework_status == "present" else "未導入",
                f"提供 AI Governance 工具與規則來源；目前偵測到的導入型態是 {framework_topology.value}。",
            ),
            _capability_row(
                "版本新鮮度（Framework version freshness）",
                _capability_status(
                    framework_pin_freshness.value,
                    present_values={"current_vs_local_tracking"},
                ),
                (
                    "檢查本地 framework 是否追上本地已知 tracking ref；真正遠端最新證據由 updater 另外回報。"
                ),
            ),
            _capability_row(
                "本 repo 規則（Repo governance instructions）",
                _capability_status(repo_specific_rules_present.value),
                "讓 agent 進入這個 repo 時知道本 repo 的風險、測試與操作規則。",
            ),
            _capability_row(
                "靜態治理檔案（Static framework files）",
                _capability_status(
                    static_self_contained.value,
                    present_values={"yes"},
                ),
                "提供不跑 runtime 也能讀到的治理文件、規則與導入狀態。",
            ),
            _capability_row(
                "runtime 治理能力（Runtime-capable governance）",
                _capability_status(
                    runtime_capable.value,
                    present_values={"yes"},
                ),
                "代表 repo 是否具備可執行的 runtime governance；只有明確回報已可用時才算導入。",
            ),
            _capability_row(
                "本機 commit/push 檢查（Git hooks）",
                _capability_status(
                    hook_config_framework_root.value,
                    present_values={"inside_repo"},
                ),
                "在本機 commit 或 push 前提示/檢查治理狀態；這不等於所有機器都已強制執行。",
            ),
            _capability_row(
                "領域合約（Domain contract）",
                _capability_status(domain_contract_present.value),
                "用 contract.yaml 宣告這個 repo 自己的治理需求與驗證入口。",
            ),
            _capability_row(
                "自動驗證層（Validator surface）",
                _capability_status(validator_surface_present.value),
                "列出 repo 專屬 validator，讓更新後能知道是否接上自動檢查。",
            ),
            _capability_row(
                "記憶工作流（Memory workflow）",
                _capability_status(
                    memory_workflow_surface.value,
                    present_values={"verified", "present", "available"},
                ),
                "顯示 memory 寫入/檢查流程是否有被觀測；不代表記憶內容已完整同步。",
            ),
        ]
    )

    lines.append("技術細項：")
    lines.append(
        _surface_line(
            "AI Governance framework checkout",
            framework_status,
            f"偵測到的導入型態是 {framework_topology.value}",
        )
    )
    lines.append(
        _surface_line(
            "Framework version freshness",
            str(framework_pin_freshness.value),
            "比較本地 framework 與本地已知 tracking ref；這不是遠端最新 head 的證明",
        )
    )
    lines.append(
        _surface_line(
            "Repo governance instructions",
            _present_absent(repo_specific_rules_present.value),
            "AGENTS.md 包含 agent 應遵守的 repo 專屬治理規則",
        )
    )
    lines.append(
        _surface_line(
            "Static framework files",
            str(static_self_contained.value),
            "檢查可見 framework 檔案是否足以提供靜態治理指引",
        )
    )
    lines.append(
        _surface_line(
            "Runtime-capable governance",
            str(runtime_capable.value),
            "這份 summary 不證明 runtime execution 已可用",
        )
    )
    lines.append(
        _surface_line(
            "Git hook framework root",
            str(hook_config_framework_root.value),
            "顯示本機 pre-commit/pre-push hooks 指向哪裡；hook 是本機狀態，不代表所有環境都強制執行",
        )
    )
    lines.append(
        _surface_line(
            "Domain contract",
            _present_absent(domain_contract_present.value),
            "contract.yaml 宣告 repo 專屬治理合約",
        )
    )
    lines.append(
        _surface_line(
            "Validator surface",
            _present_absent(validator_surface_present.value),
            "validator 是 contract 宣告的 repo 專屬自動檢查",
        )
    )
    lines.append(
        _surface_line(
            "Memory workflow surface",
            str(memory_workflow_surface.value),
            "這份 summary 不推論 memory 是否完整同步",
        )
    )

    if missing_surfaces:
        lines.append("尚未導入或尚未被證明：")
        lines.extend(f"- {surface}: 需要後續處理，不能因此宣稱 full adoption" for surface in missing_surfaces)
    else:
        lines.append("尚未導入或尚未被證明：這份 report-only summary 沒有偵測到缺口。")

    lines.append("白話結論：")
    if user_facing_status.value == "full_candidate":
        lines.append(
            "- AI Governance 在可見的靜態表面上看起來已齊備，但 runtime enforcement 仍未被證明。"
        )
    elif user_facing_status.value == "partial":
        lines.append(
            "- AI Governance 是部分導入：核心表面已存在，但這個 repo 還不能宣稱完整導入。"
        )
    elif user_facing_status.value == "minimal":
        lines.append(
            "- AI Governance 指引已存在，但這個 repo 尚未導入完整 framework 表面。"
        )
    elif user_facing_status.value == "not_governed":
        lines.append("- 這個 repo 目前看起來尚未由 AI Governance 管理。")
    else:
        lines.append("- 導入狀態不明確，需要人工判讀。")

    if cannot_claim:
        lines.append("不能從這份 summary 宣稱：")
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
    lock_consistency = _derive_lock_consistency(repo, framework)
    missing_surfaces = _derive_missing_surfaces(
        adoption_report,
        agents_report,
        domain_contract_present,
        validator_surface_present,
        lock_consistency,
    )
    signal_conflicts = _derive_conflicts(adoption_report)
    claim_ceiling = _derive_claim_ceiling(adoption_report, repo_specific_present)
    cannot_claim = _derive_cannot_claim(adoption_report, agents_report, lock_consistency)
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
        lock_consistency=lock_consistency,
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
        lock_consistency=lock_consistency,
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
        f"lock_consistency         = {summary.lock_consistency.value}",
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
