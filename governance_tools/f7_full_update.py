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
from pathlib import Path
from typing import Any, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.agents_calibration_maturity import assess_agents_calibration_maturity
from governance_tools.external_governance_submodule_updater import update_governance_submodule
from governance_tools.external_repo_readiness import assess_external_repo
from governance_tools.hook_installer import install_governance_hooks


COMPLETED = "completed"
PARTIALLY_UPDATED = "partially_updated"
ALREADY_CURRENT = "already_current"
BLOCKED = "blocked"
NOT_APPLICABLE = "not_applicable"
NOT_VERIFIED = "not_verified"


@dataclass
class F7Result:
    ok: bool
    mode: str
    repo_root: str
    repo_role: str
    f7_final_status: str
    stages: dict[str, str] = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def _git(repo: Path, args: Sequence[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
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
    return result[0] == 0 and bool(result[1])


def _has_staged_changes(repo: Path) -> bool:
    code, stdout, _stderr = _git(repo, ["diff", "--cached", "--name-only"])
    return code != 0 or bool(stdout)


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
    payload = source.read_text(encoding="utf-8-sig")
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
    if maturity.status not in {"scaffold_only", "generic_filled"}:
        return "verified", [], []

    insert = (
        "\n\n"
        "<!-- governance:key=f7_update_boundary -->\n"
        "- F-7 updates must preserve existing repo-specific AGENTS.md rules.\n"
        "- Validate F-7 state with `python -X utf8 -m governance_tools.f7_full_update --repo . --format json` from the framework environment.\n"
        "- Required external contract surfaces: contract.yaml, governance/framework.lock.json, .git/hooks/pre-commit, .git/hooks/pre-push, .github/copilot-instructions.md.\n"
    )
    after = before.rstrip() + insert + "\n"
    if after == before:
        return ALREADY_CURRENT, [], []
    agents_path.write_text(after, encoding="utf-8")
    return "updated", [str(agents_path)], []


def _external_f7_completed(readiness: Any) -> bool:
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
        ]
    )


def _status_from_external_readiness(readiness: Any) -> str:
    if readiness.errors:
        return BLOCKED
    return COMPLETED if _external_f7_completed(readiness) else PARTIALLY_UPDATED


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
        "agents_calibration": (before.agents_calibration or {}).get("status", NOT_VERIFIED),
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
    final_status = _status_from_external_readiness(after)
    if errors:
        final_status = BLOCKED

    return F7Result(
        ok=final_status in {COMPLETED, ALREADY_CURRENT, PARTIALLY_UPDATED},
        mode="apply" if apply else "dry_run",
        repo_root=str(repo_root.resolve()),
        repo_role="external_contract_repo",
        f7_final_status=final_status,
        stages=stages,
        changed_files=sorted(set(changed)),
        errors=errors,
        warnings=after.warnings,
        details={
            "readiness_ready": after.ready,
            "strict_external_f7_completed": _external_f7_completed(after),
            "checks": after.checks,
            "agents_calibration": after.agents_calibration,
            "hooks": after.hooks,
            "framework_version": after.framework_version,
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
        return F7Result(
            ok=result.ok,
            mode=result.mode,
            repo_root=str(repo_root),
            repo_role=role,
            f7_final_status=result.full_update_stage_report.get("final_status", NOT_VERIFIED),
            stages=result.full_update_stage_report,
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
        stages={"framework_pointer": NOT_APPLICABLE},
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
    ]
    if result.stages:
        lines.append("[stages]")
        for key in sorted(result.stages):
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
