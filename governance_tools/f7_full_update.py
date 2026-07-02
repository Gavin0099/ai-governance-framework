#!/usr/bin/env python3
"""
Repo-role aware F-7 full update orchestrator.

This module separates F-7 completion semantics from the older submodule pointer
backend. The first implemented non-submodule backend is the external contract
repo path exposed by pcie_g5_contract: framework lock, hooks, Copilot
instructions, and repo-specific AGENTS calibration.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.agents_calibration_maturity import assess_agents_calibration_maturity
from governance_tools.external_governance_submodule_updater import update_governance_submodule
from governance_tools.external_repo_readiness import assess_external_repo
from governance_tools.governance_maturity_summary import (
    build_governance_maturity_summary,
    summary_to_dict as governance_maturity_summary_to_dict,
)
from governance_tools.hook_installer import install_governance_hooks


COMPLETED = "completed"
PARTIALLY_UPDATED = "partially_updated"
ALREADY_CURRENT = "already_current"
BLOCKED = "blocked"
NOT_APPLICABLE = "not_applicable"
NOT_VERIFIED = "not_verified"

F7_UPDATE_BOUNDARY_MARKER = "<!-- governance:key=f7_update_boundary -->"
F7_UPDATE_BOUNDARY_BLOCK = (
    f"{F7_UPDATE_BOUNDARY_MARKER}\n"
    "- F-7 updates must preserve existing repo-specific AGENTS.md rules.\n"
    "- Validate F-7 state with `python -X utf8 -m governance_tools.f7_full_update --repo . --format human` from the framework environment.\n"
    "- Final AI Governance update reports must relay `[human_readable_adoption_summary]` table rows as a table, not a prose summary, and include the user-facing adoption status; reporting only machine-readable fields or `F-7 completed` is incomplete.\n"
    "- Required external contract surfaces: contract.yaml, governance/framework.lock.json, .git/hooks/pre-commit, .git/hooks/pre-push, .github/copilot-instructions.md.\n"
)


@dataclass
class F7Result:
    ok: bool
    mode: str
    repo_root: str
    repo_role: str
    f7_final_status: str
    stages: dict[str, Any] = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def _git(repo: Path, args: Sequence[str]) -> tuple[int, str, str]:
    repo = repo.resolve()
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode, (completed.stdout or "").strip(), (completed.stderr or "").strip()


def _is_git_repo(repo: Path) -> bool:
    code, _stdout, _stderr = _git(repo, ["rev-parse", "--is-inside-work-tree"])
    return code == 0


def _has_registered_submodule(repo: Path, submodule_path: str) -> bool:
    result = _git(repo, ["submodule", "status", "--", submodule_path])
    if result[0] == 0 and bool(result[1]):
        return True

    gitmodules = repo / ".gitmodules"
    if not gitmodules.is_file():
        return False
    try:
        text = gitmodules.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    path_pattern = f"path = {submodule_path}"
    quoted_path_pattern = f'path = "{submodule_path}"'
    if path_pattern in text or quoted_path_pattern in text:
        return (repo / submodule_path).exists()

    config_result = _git(
        repo,
        ["config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"],
    )
    if config_result[0] != 0:
        return False
    for line in config_result[1].splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[1].strip() == submodule_path:
            return (repo / submodule_path).exists()
    return False


def _has_staged_changes(repo: Path) -> bool:
    code, stdout, _stderr = _git(repo, ["diff", "--cached", "--name-only"])
    return code != 0 or bool(stdout)


def _governance_maturity_stage(repo_root: Path, framework_root: Path | None) -> dict[str, object]:
    try:
        summary = build_governance_maturity_summary(repo_root, framework_root=framework_root)
    except Exception as exc:
        return {
            "report_only": True,
            "status": "not_available",
            "reason": f"{type(exc).__name__}: {exc}",
            "claim_boundary": "summary unavailable; no maturity claim is supported",
        }
    return governance_maturity_summary_to_dict(summary)


def _format_governance_maturity_stage(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return [f"governance_maturity_summary={payload}"]
    if payload.get("status") == "not_available":
        return [
            "[governance_maturity_summary]",
            "report_only=true",
            "status=not_available",
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


def classify_repo(repo_root: Path, submodule_path: str = "ai-governance-framework") -> str:
    repo_root = repo_root.resolve()
    if not repo_root.exists() or not _is_git_repo(repo_root):
        return "blocked"
    if _has_registered_submodule(repo_root, submodule_path):
        return "submodule_consumer"
    if (repo_root / "contract.yaml").is_file():
        return "external_contract_repo"
    if (repo_root / "governance" / "framework.lock.json").is_file() or (repo_root / "AGENTS.base.md").is_file():
        return "copy_based_consumer"
    return "not_governed"


def _copy_framework_lock(repo_root: Path, framework_root: Path) -> tuple[str, list[str], list[str]]:
    source = framework_root / "governance" / "framework.lock.json"
    target = repo_root / "governance" / "framework.lock.json"
    if not source.is_file():
        return BLOCKED, [], [f"missing framework lock template: {source}"]
    try:
        payload_obj = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return BLOCKED, [], [f"invalid framework lock template JSON: {source}: {exc}"]
    current_head = _framework_head_commit(framework_root)
    if current_head:
        payload_obj["adopted_commit"] = current_head
        payload_obj["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(payload_obj, ensure_ascii=False, indent=2) + "\n"
    if target.exists() and target.read_text(encoding="utf-8-sig") == payload:
        return ALREADY_CURRENT, [], []
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    return "updated", [str(target)], []


def _ensure_agents_keyed_sections(repo_root: Path) -> tuple[str, list[str], list[str]]:
    agents_path = repo_root / "AGENTS.md"
    if not agents_path.is_file():
        return "missing", [], [f"missing AGENTS.md: {agents_path}"]

    before = agents_path.read_text(encoding="utf-8")
    maturity = assess_agents_calibration_maturity(repo_root)
    after = _replace_or_append_managed_bullet_block(
        before,
        marker=F7_UPDATE_BOUNDARY_MARKER,
        block=F7_UPDATE_BOUNDARY_BLOCK,
    )
    after = _remove_legacy_f7_json_validation_guidance(after)
    inserts: list[str] = []
    if "governance:key=memory_workflow" not in before and "memory_workflow" not in before:
        inserts.append(
            "<!-- governance:key=memory_workflow -->\n"
            "- Before claiming completion for any change touching `memory/**`, run `python -m governance_tools.memory_workflow --check --repo .`.\n"
            "- For memory completion claims, run `python -m governance_tools.memory_workflow --check --repo . --run-guard` and report blockers before claiming DONE.\n"
            "- Use the canonical memory writer for session-derived memory; do not edit memory records as ordinary markdown.\n"
        )

    if inserts:
        after = after.rstrip() + "\n\n" + "\n\n".join(inserts) + "\n"

    if after == before:
        return "verified", [], []
    agents_path.write_text(after, encoding="utf-8")
    if maturity.status in {"scaffold_only", "generic_filled"}:
        return "updated", [str(agents_path)], []
    return "updated_preserved_repo_rules", [str(agents_path)], []


def _replace_or_append_managed_bullet_block(text: str, *, marker: str, block: str) -> str:
    lines = text.splitlines()
    block_lines = block.rstrip().splitlines()
    for index, line in enumerate(lines):
        if line.strip() != marker:
            continue
        end = index + 1
        while end < len(lines) and lines[end].startswith("- "):
            end += 1
        updated = lines[:index] + block_lines + lines[end:]
        return "\n".join(updated).rstrip() + "\n"
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def _remove_legacy_f7_json_validation_guidance(text: str) -> str:
    lines = text.splitlines()
    kept = [
        line
        for line in lines
        if not _is_legacy_f7_json_validation_line(line)
    ]
    return "\n".join(kept).rstrip() + "\n"


def _is_legacy_f7_json_validation_line(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("- ")
        and stripped.startswith("- Validate F-7 state with ")
        and "f7_full_update" in stripped
        and "--format json" in stripped
        and "from the framework environment" in stripped
    )


def _framework_head_commit(framework_root: Path) -> str:
    code, stdout, _stderr = _git(framework_root, ["rev-parse", "HEAD"])
    return stdout.strip() if code == 0 else ""


def _adopted_commit(readiness: Any) -> str:
    version = readiness.framework_version or {}
    return str(version.get("adopted_commit", "")).strip()


def _framework_lock_commit_current(readiness: Any, framework_root: Path) -> bool:
    current = _framework_head_commit(framework_root)
    adopted = _adopted_commit(readiness)
    return bool(current) and bool(adopted) and current == adopted


def _framework_version_diagnostics(readiness: Any, framework_root: Path) -> dict[str, Any]:
    version = readiness.framework_version or {}
    current_head = _framework_head_commit(framework_root)
    adopted_commit = str(version.get("adopted_commit", "")).strip()
    return {
        "adopted_release": version.get("adopted_release"),
        "adopted_release_current": readiness.checks.get("framework_version_current") is True,
        "adopted_commit": adopted_commit or None,
        "framework_head_commit": current_head or None,
        "adopted_commit_current": bool(current_head) and bool(adopted_commit) and current_head == adopted_commit,
        "note": "adopted_release_current only means the release is compatible/current; F-7 completion also requires adopted_commit_current.",
    }


def _agents_baseline_diagnostics(repo_root: Path) -> dict[str, Any]:
    agents_path = repo_root / "AGENTS.md"
    if not agents_path.is_file():
        return {
            "baseline_version": None,
            "baseline_version_is_framework_release": False,
            "note": "AGENTS.md is missing; no baseline marker was inspected.",
        }
    text = agents_path.read_text(encoding="utf-8", errors="replace")
    baseline_version: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if "baseline_version:" in stripped:
            baseline_version = stripped.split("baseline_version:", 1)[1].strip()
            baseline_version = baseline_version.strip("-").strip()
            if baseline_version.endswith("-->"):
                baseline_version = baseline_version[:-3].strip()
            break
    return {
        "baseline_version": baseline_version,
        "baseline_version_is_framework_release": False,
        "note": "AGENTS baseline_version describes the AGENTS baseline surface, not the adopted AI Governance Framework release.",
    }


def _uncommitted_governance_surfaces(repo_root: Path) -> list[str]:
    status_args = [
        "status",
        "--short",
        "--",
        "AGENTS.md",
        "AGENTS.base.md",
        "contract.yaml",
        "governance",
        ".github",
        ".governance",
        ".governance-payload-config.yaml",
        "memory",
    ]
    code, stdout, _stderr = _git(repo_root, status_args)
    if code != 0 or not stdout:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]


F7_GOVERNANCE_ALLOWLIST = (
    ".github/copilot-instructions.md",
    ".github/hooks/session-end.json",
    ".github/workflows/governance-drift.yml",
    ".governance-payload-config.yaml",
    ".governance/baseline.yaml",
    ".governance/expected_dirty.json",
    ".governance/version_manifest.yaml",
    "AGENTS.base.md",
    "AGENTS.md",
    "contract.yaml",
    "governance/",
    "memory/01_active_task.md",
    "memory/02_tech_stack.md",
    "memory/03_knowledge_base.md",
    "memory/04_review_log.md",
)


def _status_entries(repo_root: Path) -> list[tuple[str, str]]:
    code, stdout, _stderr = _git(repo_root, ["status", "--porcelain=v1"])
    if code != 0 or not stdout:
        return []
    entries: list[tuple[str, str]] = []
    for raw in stdout.splitlines():
        if not raw.strip():
            continue
        status = raw[:2]
        path = raw[3:] if len(raw) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append((status, path.replace("\\", "/")))
    return entries


def _path_matches_allowlist(path: str) -> bool:
    normalized = path.replace("\\", "/")
    for allowed in F7_GOVERNANCE_ALLOWLIST:
        if allowed.endswith("/"):
            if normalized.startswith(allowed):
                return True
        elif normalized == allowed:
            return True
    return False


def _classify_non_allowlisted_dirty(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized in {"CMakeLists.txt"} or normalized.startswith(("Source/", "SubModule/", "cmake/", "CMakePresets")):
        return "product_build_or_submodule"
    if normalized.startswith(("artifacts/", "winbuild/", ".claude/", ".gemini/", ".tmp", "_pytest_tmp")):
        return "generated_or_local_runtime"
    if normalized.startswith("memory/"):
        return "memory_review_required"
    return "outside_f7_allowlist"


def _f7_remediation_plan(repo_root: Path) -> dict[str, Any]:
    entries = _status_entries(repo_root)
    allowlisted_dirty: list[str] = []
    excluded: dict[str, list[str]] = {
        "product_build_or_submodule": [],
        "generated_or_local_runtime": [],
        "memory_review_required": [],
        "outside_f7_allowlist": [],
    }
    for status, path in entries:
        rendered = f"{status} {path}".strip()
        if _path_matches_allowlist(path):
            allowlisted_dirty.append(rendered)
        else:
            excluded[_classify_non_allowlisted_dirty(path)].append(rendered)

    excluded_non_empty = {key: value for key, value in excluded.items() if value}
    strategy = "direct_apply_possible"
    if excluded_non_empty:
        strategy = "clean_worktree_recommended"
    elif allowlisted_dirty:
        strategy = "review_existing_governance_diff_before_apply"

    return {
        "mode": "read_only_plan",
        "strategy": strategy,
        "governance_allowlist": list(F7_GOVERNANCE_ALLOWLIST),
        "allowlisted_dirty": sorted(allowlisted_dirty),
        "excluded_dirty_scopes": {key: sorted(value) for key, value in excluded_non_empty.items()},
        "non_goals": [
            "do not commit product/build/submodule changes as F-7 adoption",
            "do not delete generated artifacts during F-7 apply",
            "do not claim full_update_completed until repo-role-specific required stages verify",
        ],
        "claim_ceiling": (
            "This plan classifies safe F-7 governance surfaces only; it does not update, "
            "commit, push, or prove fleet adoption."
        ),
    }


def _agents_memory_workflow_router_present(repo_root: Path) -> bool:
    agents_path = repo_root / "AGENTS.md"
    if not agents_path.is_file():
        return False
    text = agents_path.read_text(encoding="utf-8", errors="replace")
    return "memory_workflow" in text and "memory/**" in text


def _resolve_hook_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git / "hooks"
    if dot_git.is_file():
        code, stdout, _stderr = _git(repo_root, ["rev-parse", "--git-common-dir"])
        common_dir = stdout.strip()
        if code == 0 and common_dir:
            common_path = Path(common_dir)
            if not common_path.is_absolute():
                common_path = repo_root / common_path
            return common_path.resolve() / "hooks"
    return dot_git / "hooks"


def _pre_commit_memory_workflow_advisory_present(repo_root: Path) -> bool:
    hook_path = _resolve_hook_dir(repo_root) / "pre-commit"
    if not hook_path.is_file():
        return False
    text = hook_path.read_text(encoding="utf-8", errors="replace")
    return "memory_workflow" in text and "MEMORY_WORKFLOW_TOOL" in text


def _external_f7_completed(readiness: Any, repo_root: Path, framework_root: Path) -> bool:
    checks = readiness.checks
    agents = readiness.agents_calibration or {}
    hooks = readiness.hooks or {}
    hook_checks = hooks.get("checks") or {}
    return all(
        [
            checks.get("hooks_ready") is True,
            checks.get("framework_version_known") is True,
            checks.get("framework_version_current") is True,
            checks.get("framework_source_canonical") is True,
            hook_checks.get("copilot_instructions_governed") is True,
            agents.get("status") not in {"scaffold_only", "generic_filled", None},
            _framework_lock_commit_current(readiness, framework_root),
            _agents_memory_workflow_router_present(repo_root),
            _pre_commit_memory_workflow_advisory_present(repo_root),
        ]
    )


def _status_from_external_readiness(readiness: Any, repo_root: Path, framework_root: Path) -> str:
    if readiness.errors:
        return BLOCKED
    return COMPLETED if _external_f7_completed(readiness, repo_root, framework_root) else PARTIALLY_UPDATED


def _run_external_contract_backend(repo_root: Path, framework_root: Path, apply: bool) -> F7Result:
    before = assess_external_repo(repo_root, framework_root=framework_root)
    changed: list[str] = []
    errors: list[str] = []
    stages: dict[str, str] = {
        "framework_pointer": NOT_APPLICABLE,
        "repo_local_instruction": NOT_VERIFIED,
        "memory_writer_coverage": NOT_VERIFIED,
        "hook_validator_enforcement": "verified" if before.checks.get("hooks_ready") else "missing",
        "existing_memory_normalization": NOT_VERIFIED,
        "framework_lock": "verified" if before.checks.get("framework_version_known") else "missing",
        "framework_lock_commit": "verified" if _framework_lock_commit_current(before, framework_root) else NOT_VERIFIED,
        "agents_calibration": (before.agents_calibration or {}).get("status", NOT_VERIFIED),
        "memory_workflow_router": "verified" if _agents_memory_workflow_router_present(repo_root) else NOT_VERIFIED,
        "memory_workflow_hook_advisory": "verified" if _pre_commit_memory_workflow_advisory_present(repo_root) else NOT_VERIFIED,
    }

    if apply:
        status, lock_changed, lock_errors = _copy_framework_lock(repo_root, framework_root)
        stages["framework_lock"] = status
        changed.extend(lock_changed)
        errors.extend(lock_errors)

        hook_result = install_governance_hooks(repo_root, framework_root)
        stages["hook_validator_enforcement"] = "updated" if hook_result.changed_files else ("verified" if hook_result.ok else BLOCKED)
        changed.extend(hook_result.changed_files)
        errors.extend(hook_result.errors)

        agents_status, agents_changed, agents_errors = _ensure_agents_keyed_sections(repo_root)
        stages["agents_calibration"] = agents_status
        changed.extend(agents_changed)
        errors.extend(agents_errors)

    after = assess_external_repo(repo_root, framework_root=framework_root)
    stages["framework_lock_commit"] = "verified" if _framework_lock_commit_current(after, framework_root) else NOT_VERIFIED
    stages["memory_workflow_router"] = "verified" if _agents_memory_workflow_router_present(repo_root) else NOT_VERIFIED
    stages["memory_workflow_hook_advisory"] = "verified" if _pre_commit_memory_workflow_advisory_present(repo_root) else NOT_VERIFIED
    stages["governance_maturity_summary"] = _governance_maturity_stage(repo_root, framework_root)
    final_status = _status_from_external_readiness(after, repo_root, framework_root)
    if errors:
        final_status = BLOCKED
    diagnostics = _framework_version_diagnostics(after, framework_root)
    governance_surface_status = _uncommitted_governance_surfaces(repo_root)
    remediation_plan = _f7_remediation_plan(repo_root)
    warnings = list(after.warnings)
    if diagnostics["adopted_release_current"] and not diagnostics["adopted_commit_current"]:
        warnings.append(
            "f7-diagnostic: adopted_release is current but adopted_commit does not match framework HEAD; "
            "release-current is not F-7 completion"
        )
    if governance_surface_status:
        warnings.append(
            "f7-diagnostic: uncommitted governance surfaces are present; treat as rollout scope until reviewed/committed"
        )
    if remediation_plan["excluded_dirty_scopes"]:
        warnings.append(
            "f7-diagnostic: non-governance dirty scopes are present; use a clean worktree before F-7 apply/remediation"
        )

    return F7Result(
        ok=final_status in {COMPLETED, ALREADY_CURRENT, PARTIALLY_UPDATED},
        mode="apply" if apply else "dry_run",
        repo_root=str(repo_root.resolve()),
        repo_role="external_contract_repo",
        f7_final_status=final_status,
        stages=stages,
        changed_files=sorted(set(changed)),
        errors=errors,
        warnings=warnings,
        details={
            "readiness_ready": after.ready,
            "strict_external_f7_completed": _external_f7_completed(after, repo_root, framework_root),
            "checks": after.checks,
            "agents_calibration": after.agents_calibration,
            "hooks": after.hooks,
            "framework_version": after.framework_version,
            "framework_version_diagnostics": diagnostics,
            "agents_baseline_diagnostics": _agents_baseline_diagnostics(repo_root),
            "uncommitted_governance_surfaces": governance_surface_status,
            "remediation_plan": remediation_plan,
            "framework_head_commit": _framework_head_commit(framework_root),
            "memory_workflow_router_present": _agents_memory_workflow_router_present(repo_root),
            "memory_workflow_hook_advisory_present": _pre_commit_memory_workflow_advisory_present(repo_root),
        },
    )


def run_f7_full_update(
    *,
    repo_root: Path,
    framework_root: Path,
    apply: bool = False,
    submodule_path: str = "ai-governance-framework",
) -> F7Result:
    repo_root = repo_root.resolve()
    framework_root = framework_root.resolve()
    role = classify_repo(repo_root, submodule_path=submodule_path)

    if role == "blocked":
        return F7Result(
            ok=False,
            mode="apply" if apply else "dry_run",
            repo_root=str(repo_root),
            repo_role=role,
            f7_final_status=BLOCKED,
            errors=[f"not a usable git repo: {repo_root}"],
        )
    if _has_staged_changes(repo_root):
        return F7Result(
            ok=False,
            mode="apply" if apply else "dry_run",
            repo_root=str(repo_root),
            repo_role=role,
            f7_final_status=BLOCKED,
            errors=["repo has pre-existing staged changes; refusing to mix F-7 scope"],
        )
    if role == "submodule_consumer":
        result = update_governance_submodule(
            repo=repo_root,
            submodule_path=submodule_path,
            dry_run=not apply,
            stage=False,
            commit=False,
        )
        stages = dict(result.full_update_stage_report)
        stages["governance_maturity_summary"] = _governance_maturity_stage(repo_root, repo_root / submodule_path)
        return F7Result(
            ok=result.ok,
            mode=result.mode,
            repo_root=str(repo_root),
            repo_role=role,
            f7_final_status=result.full_update_stage_report.get("final_status", NOT_VERIFIED),
            stages=stages,
            changed_files=result.staged_files,
            errors=result.errors,
            details={"submodule_backend": asdict(result)},
        )
    if role == "external_contract_repo":
        return _run_external_contract_backend(repo_root, framework_root, apply=apply)
    return F7Result(
        ok=False,
        mode="apply" if apply else "dry_run",
        repo_root=str(repo_root),
        repo_role=role,
        f7_final_status=NOT_APPLICABLE if role == "not_governed" else NOT_VERIFIED,
        stages={
            "framework_pointer": NOT_APPLICABLE,
            "governance_maturity_summary": _governance_maturity_stage(repo_root, framework_root),
        },
        errors=[f"no F-7 apply backend for repo role: {role}"],
    )


def format_human(result: F7Result) -> str:
    lines = [
        "[f7_full_update]",
        f"ok={result.ok}",
        f"mode={result.mode}",
        f"repo_role={result.repo_role}",
        f"f7_final_status={result.f7_final_status}",
        f"repo_root={result.repo_root}",
        "[human_readable_update_summary]",
        (
            "F-7 full update workflow means the complete AI Governance update flow: "
            "update the framework pointer, refresh repo-local governance instructions, "
            "check memory-writer coverage, check local hook/validator coverage, check "
            "existing memory normalization status, and show the adoption status summary."
        ),
        f"Current result: {result.f7_final_status}.",
        (
            "Changed files reported by this run: "
            + (", ".join(result.changed_files) if result.changed_files else "none")
        ),
        (
            "Important boundary: this report explains visible update/adoption surfaces; "
            "it does not prove runtime enforcement or full governance correctness."
        ),
    ]
    if result.stages:
        lines.append("[stages]")
        for key in sorted(result.stages):
            if key == "governance_maturity_summary":
                lines.extend(_format_governance_maturity_stage(result.stages[key]))
            else:
                lines.append(f"{key}={result.stages[key]}")
    if result.changed_files:
        lines.append("[changed_files]")
        lines.extend(result.changed_files)
    if result.errors:
        lines.append("[errors]")
        lines.extend(result.errors)
    if result.warnings:
        lines.append("[warnings]")
        lines.extend(result.warnings)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run repo-role aware F-7 full update.")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--framework-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--submodule-path", default="ai-governance-framework")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    result = run_f7_full_update(
        repo_root=args.repo,
        framework_root=args.framework_root,
        apply=args.apply,
        submodule_path=args.submodule_path,
    )
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(format_human(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
