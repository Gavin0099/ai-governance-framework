#!/usr/bin/env python3
"""
Report-only diagnostics for AI Governance adoption posture.

This command reads local filesystem and local git metadata only. It does not
install, update, delete, fetch, stage, rewrite, or enforce anything.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


REPORT_VERSION = "0.1"
COMMON_FRAMEWORK_PATHS = (
    "additional/ai-governance-framework",
    ".ai-governance-framework",
    "ai-governance-framework",
)
FRAMEWORK_REQUIRED_SELF_CONTAINED = (
    "governance_tools",
    "runtime_hooks",
    "governance/runtime_injection_snapshot.v0.yaml",
)


@dataclass
class ClassifiedValue:
    value: str
    confidence: str = "medium"
    checked: bool = True
    reasons: list[str] = field(default_factory=list)


@dataclass
class PinStatus:
    value: str
    checked: bool
    remote_tracking_ref: str | None = None
    remote_tracking_freshness: str = "unknown"
    last_fetch: str | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass
class Finding:
    severity: str
    code: str
    message: str


@dataclass
class AdoptionDoctorReport:
    report_version: str
    repo_root: str
    report_only: bool
    adoption_class: ClassifiedValue
    self_contained: ClassifiedValue
    runtime_capable: ClassifiedValue
    root_level_leftover_runtime_hooks: ClassifiedValue
    framework_submodule: ClassifiedValue
    submodule_pin: PinStatus
    external_framework_dependency: ClassifiedValue
    hook_config_framework_root: ClassifiedValue
    findings: list[Finding] = field(default_factory=list)
    claim_boundary: str = (
        "This report does not install, update, delete, fetch, stage, rewrite, "
        "or enforce anything."
    )


def _resolve(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        _resolve(path).relative_to(_resolve(parent))
        return True
    except ValueError:
        return False


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return _resolve(path).relative_to(_resolve(repo_root)).as_posix()
    except ValueError:
        return str(_resolve(path))


def _looks_like_framework_root(path: Path) -> bool:
    path = _resolve(path)
    return (
        (path / "governance_tools").is_dir()
        or (path / "runtime_hooks").is_dir()
        or (path / "governance" / "runtime_injection_snapshot.v0.yaml").is_file()
    )


def _audit_surface_present(repo_root: Path) -> bool:
    return any(
        (repo_root / rel).exists()
        for rel in (
            ".governance/baseline.yaml",
            "contract.yaml",
            "AGENTS.md",
            "AGENTS.base.md",
            "PLAN.md",
            "governance",
        )
    )


def _read_hook_framework_root(repo_root: Path) -> Path | None:
    config = repo_root / ".git" / "hooks" / "ai-governance-framework-root"
    if not config.is_file():
        return None
    raw = config.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return None
    return _resolve(Path(raw))


def _parse_gitmodules_entries(repo_root: Path) -> list[tuple[str, str]]:
    """Declared submodules as (path, url).

    The url matters: a consumer may mount the framework at any path, and when the
    checkout is missing there is no content to inspect. The url is then the only
    remaining evidence of what the path was meant to be.
    """
    gitmodules = repo_root / ".gitmodules"
    if not gitmodules.is_file():
        return []
    entries: list[tuple[str, str]] = []
    current_path: str | None = None
    current_url: str = ""
    for raw_line in gitmodules.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("[submodule "):
            if current_path:
                entries.append((current_path, current_url))
            current_path, current_url = None, ""
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if key == "path" and value:
            current_path = value
        elif key == "url":
            current_url = value
    if current_path:
        entries.append((current_path, current_url))
    return entries


def _parse_gitmodules(repo_root: Path) -> list[str]:
    return [path for path, _url in _parse_gitmodules_entries(repo_root)]


def _framework_candidates(repo_root: Path, explicit_framework_root: Path | None) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    if explicit_framework_root is not None:
        candidates.append(("explicit", explicit_framework_root))

    hook_root = _read_hook_framework_root(repo_root)
    if hook_root is not None:
        candidates.append(("hook_config", hook_root))

    for rel in _parse_gitmodules(repo_root):
        candidates.append(("gitmodules", repo_root / rel))

    for rel in COMMON_FRAMEWORK_PATHS:
        candidates.append(("common_path", repo_root / rel))

    seen: set[str] = set()
    unique: list[tuple[str, Path]] = []
    for source, path in candidates:
        key = str(_resolve(path)).lower()
        if key not in seen:
            seen.add(key)
            unique.append((source, path))
    return unique


def _select_framework_candidate(
    repo_root: Path,
    explicit_framework_root: Path | None,
) -> tuple[str | None, Path | None, bool, list[str]]:
    reasons: list[str] = []
    external_seen = False
    fallback: tuple[str | None, Path | None] = (None, None)
    for source, candidate in _framework_candidates(repo_root, explicit_framework_root):
        if _looks_like_framework_root(candidate):
            if _is_relative_to(candidate, repo_root):
                reasons.append(f"{source} framework root is inside repo: {_repo_relative(repo_root, candidate)}")
                return source, _resolve(candidate), external_seen, reasons
            external_seen = True
            fallback = (source, _resolve(candidate))
            reasons.append(f"{source} framework root is outside repo: {_resolve(candidate)}")
    return fallback[0], fallback[1], external_seen, reasons


_FRAMEWORK_SUBMODULE_NAMES = frozenset(
    rel.rsplit("/", 1)[-1] for rel in COMMON_FRAMEWORK_PATHS
)


@dataclass(frozen=True)
class SubmoduleResolution:
    """Which declared submodule is the framework, decided once.

    Previously three call sites each took `.gitmodules` entry [0]. A consumer
    that declares an unrelated submodule first — CFU declares `Host/DMF` before
    `ai-governance-framework` — had its topology classified from the wrong
    directory, and its framework pin computed from it too. The repo reported
    `framework_topology=unknown` while F-7 was concurrently updating it through
    the `submodule_consumer` path.

    Declaration order carries no meaning, so it is not consulted. Identity comes
    from the explicit framework root when one is given, then from content, then
    from the canonical names. When more than one candidate survives, this fails
    closed rather than picking one.
    """

    path: str | None
    status: str  # "resolved" | "ambiguous" | "no_framework_declared" | "none_declared"
    reasons: list[str] = field(default_factory=list)
    candidates: tuple[str, ...] = ()


def _is_framework_submodule_name(rel: str) -> bool:
    normalized = rel.replace("\\", "/").strip("/")
    return normalized in COMMON_FRAMEWORK_PATHS or normalized.rsplit("/", 1)[-1] in _FRAMEWORK_SUBMODULE_NAMES


def _declares_framework(path: str, url: str) -> bool:
    """Declarative identity, from path or url.

    Matches `manual_update_advisory._is_framework_submodule`. A consumer may
    mount the framework anywhere — `vendor/governance` with the framework's url
    is still the framework — and this is the only signal that survives a missing
    checkout, where there is nothing to inspect.
    """
    return "ai-governance-framework" in f"{path} {url}".lower()


def _resolve_framework_submodule(
    repo_root: Path,
    explicit_framework_root: Path | None = None,
) -> SubmoduleResolution:
    entries = _parse_gitmodules_entries(repo_root)
    declared = [path for path, _url in entries]
    if not declared:
        return SubmoduleResolution(None, "none_declared", [".gitmodules does not declare a submodule"])

    # An explicitly supplied framework root settles it, when it names one of the
    # declared submodules.
    if explicit_framework_root is not None:
        target = str(_resolve(explicit_framework_root)).lower()
        for rel in declared:
            if str(_resolve(repo_root / rel)).lower() == target:
                return SubmoduleResolution(
                    rel,
                    "resolved",
                    [f"explicit framework root matches declared submodule {rel}"],
                    tuple(declared),
                )

    by_content = [rel for rel in declared if _looks_like_framework_root(repo_root / rel)]

    # Declaration first, because it is the stronger signal and the only one that
    # survives a missing checkout. `_looks_like_framework_root` accepts a bare
    # `runtime_hooks/` directory, so an unrelated submodule can collide with a
    # real framework on content alone; asking content first turned that into a
    # spurious `ambiguous` without ever consulting identity.
    by_declaration = [rel for rel, url in entries if _declares_framework(rel, url)]
    if len(by_declaration) == 1:
        return SubmoduleResolution(
            by_declaration[0],
            "resolved",
            [f"declared submodule {by_declaration[0]} is identified as the framework by path or url"],
            tuple(declared),
        )
    if len(by_declaration) > 1:
        # Several declare themselves the framework; prefer the one that is
        # actually checked out, and fail closed when that does not separate them.
        checked_out = [rel for rel in by_declaration if rel in by_content]
        if len(checked_out) == 1:
            return SubmoduleResolution(
                checked_out[0],
                "resolved",
                [
                    f"{len(by_declaration)} declared submodules identify as the framework; "
                    f"only {checked_out[0]} is checked out"
                ],
                tuple(by_declaration),
            )
        return SubmoduleResolution(
            None,
            "ambiguous",
            [f"more than one declared submodule identifies as the framework: {', '.join(by_declaration)}"],
            tuple(by_declaration),
        )

    # No declarative identity: fall back to content, for a framework mounted at
    # an unrecognised path with an unrecognised url.
    if len(by_content) == 1:
        return SubmoduleResolution(
            by_content[0],
            "resolved",
            [f"declared submodule {by_content[0]} contains framework files"],
            tuple(declared),
        )
    if len(by_content) > 1:
        return SubmoduleResolution(
            None,
            "ambiguous",
            [f"more than one declared submodule looks like a framework root: {', '.join(by_content)}"],
            tuple(by_content),
        )

    by_name = [rel for rel in declared if _is_framework_submodule_name(rel)]
    if len(by_name) == 1:
        return SubmoduleResolution(
            by_name[0],
            "resolved",
            [f"declared submodule {by_name[0]} matches a known framework path name"],
            tuple(declared),
        )
    if len(by_name) > 1:
        return SubmoduleResolution(
            None,
            "ambiguous",
            [f"more than one declared submodule matches a framework path name: {', '.join(by_name)}"],
            tuple(by_name),
        )

    return SubmoduleResolution(
        None,
        "no_framework_declared",
        [f".gitmodules declares {len(declared)} submodule(s), none of which is a framework: {', '.join(declared)}"],
        tuple(declared),
    )


def _classify_submodule(repo_root: Path, resolution: SubmoduleResolution) -> ClassifiedValue:
    if resolution.status == "ambiguous":
        # Fail closed: picking one would reinstate the defect this replaced.
        return ClassifiedValue("ambiguous", confidence="high", reasons=resolution.reasons)
    submodule_path = resolution.path
    if not submodule_path:
        return ClassifiedValue("not_applicable", confidence="high", reasons=resolution.reasons)

    abs_path = repo_root / submodule_path
    if not abs_path.exists():
        return ClassifiedValue(
            "declared_missing",
            confidence="high",
            reasons=[f".gitmodules declares {submodule_path}, but the path is missing"],
        )
    if _looks_like_framework_root(abs_path):
        return ClassifiedValue(
            "initialized",
            confidence="high",
            reasons=[f".gitmodules declares initialized framework path {submodule_path}"],
        )
    return ClassifiedValue(
        "partial_or_uninitialized",
        confidence="high",
        reasons=[f".gitmodules declares {submodule_path}, but required framework files are incomplete"],
    )


def _classify_adoption(
    repo_root: Path,
    framework_source: str | None,
    framework_root: Path | None,
    external_seen: bool,
    reasons: list[str],
    submodule: ClassifiedValue,
) -> ClassifiedValue:
    # Passed in rather than recomputed: this used to call _classify_submodule a
    # second time, so the topology shown and the topology used could diverge.
    if submodule.value == "initialized":
        return ClassifiedValue("submodule_consumer", confidence="high", reasons=submodule.reasons)
    if submodule.value == "ambiguous":
        return ClassifiedValue(
            "unknown",
            confidence="medium",
            reasons=submodule.reasons + ["framework submodule could not be uniquely identified"],
        )
    if submodule.value in {"declared_missing", "partial_or_uninitialized"}:
        return ClassifiedValue(
            "unknown",
            confidence="medium",
            reasons=submodule.reasons + ["declared framework submodule evidence is incomplete"],
        )

    if framework_root is not None and _is_relative_to(framework_root, repo_root):
        if framework_source == "gitmodules":
            return ClassifiedValue("unknown", confidence="medium", reasons=submodule.reasons)
        return ClassifiedValue(
            "repo_owned_framework_path",
            confidence="high",
            reasons=reasons or [f"framework root resolves inside repo: {_repo_relative(repo_root, framework_root)}"],
        )

    if _audit_surface_present(repo_root):
        copy_reasons = ["governance audit surface exists, but no repo-owned framework checkout was found"]
        if external_seen or framework_root is not None:
            copy_reasons.append("observed framework dependency resolves outside the target repo")
        return ClassifiedValue("copy_based", confidence="medium", reasons=copy_reasons)

    return ClassifiedValue("unknown", confidence="low", reasons=["insufficient adoption evidence"])


def _classify_self_contained(repo_root: Path, framework_root: Path | None) -> ClassifiedValue:
    if framework_root is None:
        return ClassifiedValue("no", confidence="medium", reasons=["no framework root was found"])
    if not _is_relative_to(framework_root, repo_root):
        return ClassifiedValue("no", confidence="high", reasons=["framework root resolves outside the target repo"])

    missing = [rel for rel in FRAMEWORK_REQUIRED_SELF_CONTAINED if not (framework_root / rel).exists()]
    if missing:
        return ClassifiedValue(
            "no",
            confidence="high",
            reasons=[
                f"framework root is repo-owned, but static runtime surface is incomplete: {', '.join(missing)}",
                "this does not evaluate hooks, pin freshness, runtime smoke, full installer, tests, or enforcement",
            ],
        )
    return ClassifiedValue(
        "yes",
        confidence="high",
        reasons=[
            "framework root is inside the target repo and required static runtime surfaces are present",
            "this does not prove hooks installed, pin fresh, runtime smoke passed, all tests passed, or enforcement",
        ],
    )


def _classify_root_runtime_hooks(repo_root: Path, framework_root: Path | None) -> ClassifiedValue:
    root_hooks = repo_root / "runtime_hooks"
    if not root_hooks.exists():
        return ClassifiedValue("absent", confidence="high", reasons=["root-level runtime_hooks is absent"])
    if framework_root is not None and _resolve(framework_root) == _resolve(repo_root):
        return ClassifiedValue(
            "present_expected_framework_repo",
            confidence="high",
            reasons=["target repo itself appears to be the framework repo"],
        )
    return ClassifiedValue(
        "present",
        confidence="high",
        reasons=["root-level runtime_hooks exists outside the selected framework checkout"],
    )


def _classify_external_dependency(repo_root: Path, framework_root: Path | None) -> ClassifiedValue:
    if framework_root is not None and not _is_relative_to(framework_root, repo_root):
        return ClassifiedValue("observed", confidence="high", reasons=[f"framework root is external: {_resolve(framework_root)}"])
    return ClassifiedValue("not_observed", confidence="medium", reasons=["no external framework root dependency was observed"])


def _classify_hook_config_framework_root(repo_root: Path) -> ClassifiedValue:
    hook_root = _read_hook_framework_root(repo_root)
    if hook_root is None:
        return ClassifiedValue(
            "absent",
            confidence="high",
            reasons=["hook framework-root config is absent"],
        )
    if _is_relative_to(hook_root, repo_root):
        return ClassifiedValue(
            "inside_repo",
            confidence="high",
            reasons=[f"hook framework-root config points inside repo: {_repo_relative(repo_root, hook_root)}"],
        )
    return ClassifiedValue(
        "external",
        confidence="high",
        reasons=[f"hook framework-root config points outside repo: {_resolve(hook_root)}"],
    )


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    resolved_cwd = cwd.resolve()
    return subprocess.run(
        ["git", "-c", f"safe.directory={resolved_cwd.as_posix()}", *args],
        cwd=resolved_cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _git_stdout(args: list[str], cwd: Path) -> str | None:
    completed = _run_git(args, cwd)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _git_dir(cwd: Path) -> Path | None:
    raw = _git_stdout(["rev-parse", "--git-dir"], cwd)
    if not raw:
        return None
    git_dir = Path(raw)
    if not git_dir.is_absolute():
        git_dir = cwd / git_dir
    return _resolve(git_dir)


def _is_git_worktree_root(cwd: Path) -> bool:
    top_level = _git_stdout(["rev-parse", "--show-toplevel"], cwd)
    if not top_level:
        return False
    return _resolve(Path(top_level)) == _resolve(cwd)


def _last_fetch(cwd: Path) -> tuple[str, str | None]:
    git_dir = _git_dir(cwd)
    if git_dir is None:
        return "unknown", None
    fetch_head = git_dir / "FETCH_HEAD"
    if not fetch_head.exists():
        return "unknown", None
    timestamp = datetime.fromtimestamp(fetch_head.stat().st_mtime, timezone.utc).isoformat()
    return "observed", timestamp


def _is_ancestor(cwd: Path, left: str, right: str) -> bool | None:
    completed = _run_git(["merge-base", "--is-ancestor", left, right], cwd)
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    return None


def _pin_subject(repo_root: Path, framework_root: Path) -> str:
    if _is_relative_to(framework_root, repo_root):
        return f"framework root {_repo_relative(repo_root, framework_root)}"
    return f"framework root {_resolve(framework_root)}"


def _classify_git_root_pin(framework_root: Path, subject: str) -> PinStatus:
    if not _is_git_worktree_root(framework_root):
        return PinStatus(
            "not_applicable",
            checked=True,
            reasons=[f"{subject} is not a git repo; no local tracking comparison is available"],
        )

    head = _git_stdout(["rev-parse", "HEAD"], framework_root)
    if not head:
        return PinStatus("unknown", checked=True, reasons=[f"unable to read {subject} HEAD"])

    upstream = _git_stdout(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], framework_root)
    if not upstream:
        for candidate in ("origin/main", "origin/HEAD"):
            resolved = _git_stdout(["rev-parse", "--verify", candidate], framework_root)
            if resolved:
                upstream = candidate
                break
    if not upstream:
        freshness, last_fetch = _last_fetch(framework_root)
        return PinStatus(
            "unknown",
            checked=True,
            remote_tracking_freshness=freshness,
            last_fetch=last_fetch,
            reasons=["no local remote-tracking ref is available; no fetch was attempted"],
        )

    tracking = _git_stdout(["rev-parse", "--verify", upstream], framework_root)
    freshness, last_fetch = _last_fetch(framework_root)
    if not tracking:
        return PinStatus(
            "unknown",
            checked=True,
            remote_tracking_ref=upstream,
            remote_tracking_freshness=freshness,
            last_fetch=last_fetch,
            reasons=["local remote-tracking ref could not be resolved; no fetch was attempted"],
        )

    if head == tracking:
        return PinStatus(
            "current_vs_local_tracking",
            checked=True,
            remote_tracking_ref=upstream,
            remote_tracking_freshness=freshness,
            last_fetch=last_fetch,
            reasons=[
                f"{subject} HEAD matches the local remote-tracking ref",
                "this does not prove the pin matches the true current remote head",
            ],
        )

    head_behind = _is_ancestor(framework_root, head, tracking)
    tracking_behind = _is_ancestor(framework_root, tracking, head)
    if head_behind is True:
        value = "behind_local_tracking"
        reason = f"{subject} HEAD is behind the local remote-tracking ref"
    elif tracking_behind is True:
        value = "ahead_or_diverged_vs_local_tracking"
        reason = f"{subject} HEAD is ahead of the local remote-tracking ref"
    else:
        value = "ahead_or_diverged_vs_local_tracking"
        reason = f"{subject} HEAD has diverged from the local remote-tracking ref"
    return PinStatus(
        value,
        checked=True,
        remote_tracking_ref=upstream,
        remote_tracking_freshness=freshness,
        last_fetch=last_fetch,
        reasons=[reason, "no fetch was attempted"],
    )


def _classify_pin(
    repo_root: Path,
    framework_submodule: ClassifiedValue,
    selected_framework_root: Path | None,
    resolution: SubmoduleResolution,
) -> PinStatus:
    if resolution.status == "ambiguous":
        # Checked before the hook root, not after. A hook root pointing at one of
        # several framework candidates would otherwise let the pin choose a
        # subject while the topology refuses to — `framework_submodule=ambiguous`
        # beside `submodule_pin=current_vs_local_tracking`, which is the
        # cross-surface disagreement this resolution exists to remove.
        return PinStatus("unknown", checked=True, reasons=resolution.reasons)

    hook_root = _read_hook_framework_root(repo_root)
    if hook_root is not None and _looks_like_framework_root(hook_root) and _is_git_worktree_root(hook_root):
        return _classify_git_root_pin(hook_root, _pin_subject(repo_root, hook_root))

    # Same resolution the topology used, so the pin cannot describe a different
    # directory than the one classified.
    submodule_path = resolution.path
    if submodule_path:
        submodule_root = repo_root / submodule_path
        if framework_submodule.value != "initialized":
            return PinStatus("unknown", checked=True, reasons=["framework submodule is not initialized"])
        return _classify_git_root_pin(submodule_root, _pin_subject(repo_root, submodule_root))

    if selected_framework_root is not None and _looks_like_framework_root(selected_framework_root):
        return _classify_git_root_pin(
            selected_framework_root,
            _pin_subject(repo_root, selected_framework_root),
        )

    return PinStatus("not_applicable", checked=True, reasons=["no local framework git root was available"])


def _findings(report: AdoptionDoctorReport) -> list[Finding]:
    findings: list[Finding] = []
    if report.adoption_class.value == "copy_based":
        findings.append(
            Finding(
                "info",
                "copy_based_audit_surface",
                "Copy-based adoption is audit-surface only; it is not runtime self-contained governance.",
            )
        )
    if report.external_framework_dependency.value == "observed":
        findings.append(
            Finding(
                "warning",
                "external_framework_dependency",
                "Framework root resolves outside the target repo; self-contained runtime claims are not supported.",
            )
        )
    if (
        report.hook_config_framework_root.value == "external"
        and report.adoption_class.value in {"repo_owned_framework_path", "submodule_consumer"}
    ):
        findings.append(
            Finding(
                "warning",
                "external_hook_framework_root",
                "Runtime hooks execute from an external framework checkout, not the repo-owned framework path; "
                "static self_contained=yes does not prove runtime self-contained hook execution.",
            )
        )
    if report.root_level_leftover_runtime_hooks.value == "present":
        findings.append(
            Finding(
                "warning",
                "root_level_runtime_hooks",
                "Root-level runtime_hooks exists outside the selected framework checkout.",
            )
        )
    if report.framework_submodule.value in {"declared_missing", "partial_or_uninitialized"}:
        findings.append(
            Finding(
                "warning",
                "submodule_not_initialized",
                "A framework submodule path is declared but is missing or incomplete.",
            )
        )
    if report.submodule_pin.value == "behind_local_tracking":
        findings.append(
            Finding(
                "warning",
                "pin_behind_local_tracking",
                "Framework pin is behind the local remote-tracking ref; this is evidence, not a blocker.",
            )
        )
    if report.submodule_pin.value == "unknown":
        findings.append(
            Finding(
                "unknown",
                "pin_status_unknown",
                "Framework pin status could not be determined from local metadata.",
            )
        )
    return findings


def inspect_adoption(repo_root: Path, framework_root: Path | None = None) -> AdoptionDoctorReport:
    repo_root = _resolve(repo_root)
    explicit_framework_root = _resolve(framework_root) if framework_root is not None else None
    framework_source, selected_framework_root, external_seen, framework_reasons = _select_framework_candidate(
        repo_root,
        explicit_framework_root,
    )
    submodule_resolution = _resolve_framework_submodule(repo_root, explicit_framework_root)
    submodule = _classify_submodule(repo_root, submodule_resolution)
    adoption_class = _classify_adoption(
        repo_root,
        framework_source,
        selected_framework_root,
        external_seen,
        framework_reasons,
        submodule,
    )
    runtime_capable = ClassifiedValue(
        "not_checked",
        confidence="high",
        checked=False,
        reasons=["runtime smoke is out of scope for the static report-only doctor"],
    )
    report = AdoptionDoctorReport(
        report_version=REPORT_VERSION,
        repo_root=str(repo_root),
        report_only=True,
        adoption_class=adoption_class,
        self_contained=_classify_self_contained(repo_root, selected_framework_root),
        runtime_capable=runtime_capable,
        root_level_leftover_runtime_hooks=_classify_root_runtime_hooks(repo_root, selected_framework_root),
        framework_submodule=submodule,
        submodule_pin=_classify_pin(repo_root, submodule, selected_framework_root, submodule_resolution),
        external_framework_dependency=_classify_external_dependency(repo_root, selected_framework_root),
        hook_config_framework_root=_classify_hook_config_framework_root(repo_root),
    )
    report.findings = _findings(report)
    return report


def report_to_dict(report: AdoptionDoctorReport) -> dict[str, object]:
    return asdict(report)


def format_json(report: AdoptionDoctorReport) -> str:
    return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)


def _format_reasons(reasons: list[str]) -> list[str]:
    return [f"  - {reason}" for reason in reasons]


def format_human(report: AdoptionDoctorReport) -> str:
    lines = [
        "Adoption Doctor",
        "",
        f"repo_root          = {report.repo_root}",
        f"adoption_class    = {report.adoption_class.value}",
        f"self_contained    = {report.self_contained.value}",
        f"runtime_capable   = {report.runtime_capable.value}",
        f"report_only       = {str(report.report_only).lower()}",
        "",
        f"Claim boundary: {report.claim_boundary}",
        "",
        "[adoption_class]",
        f"confidence        = {report.adoption_class.confidence}",
        *_format_reasons(report.adoption_class.reasons),
        "",
        "[self_contained]",
        f"checked           = {str(report.self_contained.checked).lower()}",
        f"confidence        = {report.self_contained.confidence}",
        *_format_reasons(report.self_contained.reasons),
        "",
        "[runtime_capable]",
        f"checked           = {str(report.runtime_capable.checked).lower()}",
        *_format_reasons(report.runtime_capable.reasons),
        "",
        "[framework_submodule]",
        f"state             = {report.framework_submodule.value}",
        *_format_reasons(report.framework_submodule.reasons),
        "",
        "[submodule_pin]",
        f"state             = {report.submodule_pin.value}",
        f"remote_tracking   = {report.submodule_pin.remote_tracking_ref or '<none>'}",
        f"tracking_freshness= {report.submodule_pin.remote_tracking_freshness}",
        f"last_fetch        = {report.submodule_pin.last_fetch or '<unknown>'}",
        *_format_reasons(report.submodule_pin.reasons),
        "",
        "[external_framework_dependency]",
        f"state             = {report.external_framework_dependency.value}",
        *_format_reasons(report.external_framework_dependency.reasons),
        "",
        "[hook_config_framework_root]",
        f"state             = {report.hook_config_framework_root.value}",
        *_format_reasons(report.hook_config_framework_root.reasons),
    ]
    if report.findings:
        lines.extend(["", f"findings: {len(report.findings)}"])
        for finding in report.findings:
            lines.append(f"- {finding.severity} {finding.code}: {finding.message}")
    else:
        lines.extend(["", "findings: 0"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report-only AI Governance adoption posture diagnostic.")
    parser.add_argument("--repo", default=".", help="Target repo root to inspect.")
    parser.add_argument("--framework-root", help="Optional explicit framework root.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = _resolve(Path(args.repo))
    if not repo_root.is_dir():
        print(f"error: repo path is not a directory: {repo_root}", file=sys.stderr)
        return 2
    framework_root = Path(args.framework_root) if args.framework_root else None
    report = inspect_adoption(repo_root, framework_root=framework_root)
    if args.format == "json":
        print(format_json(report))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
