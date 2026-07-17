"""Fail-closed offline import for governance submodules.

Local Git repositories are used only as clone sources and dedicated offline
remotes. Every commit-facing and default-fetch URL remains canonical.
"""

from __future__ import annotations

import argparse
import configparser
import io
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence


DEFAULT_FRAMEWORK_PATH = ".governance/framework"
DEFAULT_DOMAIN_PATH = (
    ".governance/domain-contracts/usb-hub-firmware-architecture-contract"
)
DEFAULT_OFFLINE_REMOTE = "offline-bundle"


class OfflineOnboardingError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubmoduleSpec:
    role: str
    path: str
    source: Path
    expected_head: str
    canonical_url: str


@dataclass
class OfflineOnboardingResult:
    ok: bool
    mode: str
    repo: str
    offline_remote: str
    submodules: list[dict[str, Any]] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)
    message: str = ""
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_submodule_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if not normalized or normalized in {".", ".."}:
        raise OfflineOnboardingError(f"invalid submodule path: {value!r}")
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise OfflineOnboardingError(f"unsafe submodule path: {value!r}")
    return normalized


def _submodule_key(path: str, field_name: str) -> str:
    return f"submodule.{path}.{field_name}"


def _run_git(
    repo: Path,
    args: Sequence[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise OfflineOnboardingError(
            f"git -C {repo} {' '.join(args)} failed: {detail}"
        )
    return completed


def _git_output(repo: Path, args: Sequence[str]) -> str:
    return _run_git(repo, args).stdout.strip()


def _require_repo_root(repo: Path, *, label: str) -> None:
    result = _run_git(repo, ["rev-parse", "--show-toplevel"], check=False)
    if result.returncode != 0:
        raise OfflineOnboardingError(f"{label} is not a Git worktree: {repo}")
    resolved_root = Path(result.stdout.strip()).resolve()
    if resolved_root != repo:
        raise OfflineOnboardingError(
            f"{label} must be the Git worktree root: expected={repo}, actual={resolved_root}"
        )


def _staged_files(repo: Path) -> list[str]:
    output = _run_git(
        repo,
        ["diff", "--cached", "--name-only", "-z"],
    ).stdout
    return sorted(item for item in output.split("\0") if item)


def _require_no_initial_staged_files(repo: Path) -> None:
    staged = _staged_files(repo)
    if staged:
        raise OfflineOnboardingError(
            "target repo has pre-existing staged files; refusing to mix scopes: "
            f"{staged}"
        )


def _require_clean_gitmodules(repo: Path) -> None:
    status = _git_output(repo, ["status", "--porcelain=v1", "--", ".gitmodules"])
    if status:
        raise OfflineOnboardingError(
            "target repo has pre-existing .gitmodules changes; refusing to stage "
            "content outside this onboarding scope"
        )


def _require_remote_url(value: str, *, role: str) -> None:
    stripped = value.strip()
    if not stripped:
        raise OfflineOnboardingError(f"{role} canonical URL is empty")
    if stripped.lower().startswith("file://"):
        raise OfflineOnboardingError(
            f"{role} canonical URL must not use file://: {stripped}"
        )
    if re.match(r"^[A-Za-z]:[\\/]", stripped) or stripped.startswith(
        ("/", "\\", "./", "../", ".\\", "..\\")
    ):
        raise OfflineOnboardingError(
            f"{role} canonical URL must be a remote URL, not a local path: {stripped}"
        )
    if re.match(r"^(ssh|https?|git)://[^\s]+$", stripped):
        return
    if re.match(r"^[^/@\s]+@[^:\s]+:.+$", stripped):
        return
    raise OfflineOnboardingError(
        f"{role} canonical URL is not a supported remote URL: {stripped}"
    )


def _source_info(spec: SubmoduleSpec, *, repo: Path) -> dict[str, Any]:
    source = spec.source.resolve()
    if source == repo or source.is_relative_to(repo):
        raise OfflineOnboardingError(
            f"{spec.role} source must be outside the target repo: {source}"
        )
    _require_repo_root(source, label=f"{spec.role} source")
    dirty = _git_output(source, ["status", "--porcelain=v1"])
    if dirty:
        raise OfflineOnboardingError(
            f"{spec.role} source is dirty; package a clean source before onboarding"
        )
    head = _git_output(source, ["rev-parse", "HEAD"])
    if head != spec.expected_head:
        raise OfflineOnboardingError(
            f"{spec.role} source HEAD mismatch: expected={spec.expected_head}, actual={head}"
        )
    branch = _git_output(source, ["branch", "--show-current"]) or "detached"
    tree = _git_output(source, ["rev-parse", "HEAD^{tree}"])
    return {
        "role": spec.role,
        "path": spec.path,
        "source": str(source),
        "source_head": head,
        "source_tree": tree,
        "source_branch": branch,
        "canonical_url": spec.canonical_url,
    }


def _config_get(
    repo: Path,
    args: Sequence[str],
    *,
    required: bool = True,
) -> str | None:
    result = _run_git(repo, ["config", *args], check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    if required:
        detail = result.stderr.strip() or result.stdout.strip()
        raise OfflineOnboardingError(
            f"git config {' '.join(args)} failed: {detail or 'value not found'}"
        )
    return None


def _registered_url(repo: Path, path: str) -> str | None:
    if not (repo / ".gitmodules").is_file():
        return None
    return _config_get(
        repo,
        ["--file", ".gitmodules", "--get", _submodule_key(path, "url")],
        required=False,
    )


def _parse_staged_gitmodules_url(text: str, path: str) -> str:
    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    try:
        parser.read_file(io.StringIO(text))
    except configparser.Error as exc:
        raise OfflineOnboardingError(f"staged .gitmodules is invalid: {exc}") from exc
    section = f'submodule "{path}"'
    if not parser.has_section(section) or not parser.has_option(section, "url"):
        raise OfflineOnboardingError(
            f"staged .gitmodules is missing URL for submodule path: {path}"
        )
    return parser.get(section, "url").strip()


def _same_local_path(value: str, expected: Path) -> bool:
    try:
        return Path(value).resolve() == expected.resolve()
    except OSError:
        return False


def _assert_equal(*, label: str, actual: str, expected: str) -> None:
    if actual != expected:
        raise OfflineOnboardingError(
            f"{label} assertion failed: expected={expected!r}, actual={actual!r}"
        )


def _staged_gitlink(repo: Path, path: str) -> tuple[str, str]:
    output = _git_output(repo, ["ls-files", "--stage", "--", path])
    if not output or "\t" not in output:
        raise OfflineOnboardingError(f"submodule gitlink is not staged: {path}")
    metadata, staged_path = output.split("\t", 1)
    parts = metadata.split()
    if len(parts) != 3 or staged_path != path:
        raise OfflineOnboardingError(
            f"unexpected staged gitlink record for {path}: {output}"
        )
    mode, head, stage = parts
    if mode != "160000" or stage != "0":
        raise OfflineOnboardingError(
            f"invalid staged gitlink for {path}: mode={mode}, stage={stage}"
        )
    return mode, head


def _apply_spec(repo: Path, spec: SubmoduleSpec, offline_remote: str) -> None:
    _run_git(
        repo,
        [
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(spec.source.resolve()),
            spec.path,
        ],
    )
    nested = (repo / spec.path).resolve()
    key = _submodule_key(spec.path, "url")
    _run_git(
        repo,
        ["config", "--file", ".gitmodules", key, spec.canonical_url],
    )
    _run_git(repo, ["config", key, spec.canonical_url])
    _run_git(nested, ["remote", "set-url", "origin", spec.canonical_url])
    existing = _run_git(
        nested,
        ["remote", "get-url", offline_remote],
        check=False,
    )
    if existing.returncode == 0:
        _run_git(
            nested,
            ["remote", "set-url", offline_remote, str(spec.source.resolve())],
        )
    else:
        _run_git(
            nested,
            ["remote", "add", offline_remote, str(spec.source.resolve())],
        )


def _assert_spec(
    repo: Path,
    spec: SubmoduleSpec,
    *,
    offline_remote: str,
    staged_gitmodules: str,
) -> dict[str, Any]:
    nested = (repo / spec.path).resolve()
    key = _submodule_key(spec.path, "url")
    worktree_url = _config_get(
        repo,
        ["--file", ".gitmodules", "--get", key],
    )
    staged_url = _parse_staged_gitmodules_url(staged_gitmodules, spec.path)
    parent_url = _config_get(repo, ["--get", key])
    nested_origin = _git_output(nested, ["remote", "get-url", "origin"])
    nested_offline = _git_output(nested, ["remote", "get-url", offline_remote])
    nested_head = _git_output(nested, ["rev-parse", "HEAD"])
    _mode, gitlink_head = _staged_gitlink(repo, spec.path)

    _assert_equal(
        label=f"{spec.role} worktree .gitmodules URL",
        actual=worktree_url or "",
        expected=spec.canonical_url,
    )
    _assert_equal(
        label=f"{spec.role} staged .gitmodules URL",
        actual=staged_url,
        expected=spec.canonical_url,
    )
    _assert_equal(
        label=f"{spec.role} parent submodule URL",
        actual=parent_url or "",
        expected=spec.canonical_url,
    )
    _assert_equal(
        label=f"{spec.role} nested origin",
        actual=nested_origin,
        expected=spec.canonical_url,
    )
    if not _same_local_path(nested_offline, spec.source):
        raise OfflineOnboardingError(
            f"{spec.role} nested {offline_remote} assertion failed: "
            f"expected={spec.source.resolve()}, actual={nested_offline}"
        )
    _assert_equal(
        label=f"{spec.role} nested HEAD",
        actual=nested_head,
        expected=spec.expected_head,
    )
    _assert_equal(
        label=f"{spec.role} staged gitlink HEAD",
        actual=gitlink_head,
        expected=spec.expected_head,
    )

    return {
        "role": spec.role,
        "path": spec.path,
        "source": str(spec.source.resolve()),
        "expected_head": spec.expected_head,
        "canonical_url": spec.canonical_url,
        "worktree_gitmodules_url": worktree_url,
        "staged_gitmodules_url": staged_url,
        "parent_submodule_url": parent_url,
        "nested_origin": nested_origin,
        "nested_offline_remote": nested_offline,
        "nested_head": nested_head,
        "staged_gitlink_head": gitlink_head,
        "url_assertions_passed": True,
    }


def onboard_offline_submodules(
    *,
    repo: Path,
    specs: Sequence[SubmoduleSpec],
    offline_remote: str = DEFAULT_OFFLINE_REMOTE,
    apply: bool = False,
) -> OfflineOnboardingResult:
    repo = repo.resolve()
    mode = "apply" if apply else "dry_run"
    if not specs:
        return OfflineOnboardingResult(
            ok=False,
            mode=mode,
            repo=str(repo),
            offline_remote=offline_remote,
            message="no offline submodule specs provided",
            errors=["at least one submodule spec is required"],
        )

    normalized_specs: list[SubmoduleSpec] = []
    try:
        if not offline_remote or offline_remote == "origin":
            raise OfflineOnboardingError(
                "offline remote must be non-empty and must not be named origin"
            )
        _require_repo_root(repo, label="target repo")
        _require_no_initial_staged_files(repo)
        _require_clean_gitmodules(repo)

        seen_paths: set[str] = set()
        source_reports: list[dict[str, Any]] = []
        for raw_spec in specs:
            path = _normalize_submodule_path(raw_spec.path)
            spec = SubmoduleSpec(
                role=raw_spec.role,
                path=path,
                source=raw_spec.source.resolve(),
                expected_head=raw_spec.expected_head,
                canonical_url=raw_spec.canonical_url.strip(),
            )
            if path in seen_paths:
                raise OfflineOnboardingError(f"duplicate submodule path: {path}")
            seen_paths.add(path)
            _require_remote_url(spec.canonical_url, role=spec.role)
            if (repo / path).exists() or _registered_url(repo, path) is not None:
                raise OfflineOnboardingError(
                    f"{spec.role} submodule path is already present or registered: {path}"
                )
            source_reports.append(_source_info(spec, repo=repo))
            normalized_specs.append(spec)

        if not apply:
            return OfflineOnboardingResult(
                ok=True,
                mode=mode,
                repo=str(repo),
                offline_remote=offline_remote,
                submodules=source_reports,
                staged_files=[],
                message="dry run complete; no files modified",
                errors=[],
            )

        for spec in normalized_specs:
            _apply_spec(repo, spec, offline_remote)

        # submodule add stages the original local URLs. Re-stage only after every
        # canonical URL has been written so the index cannot retain local paths.
        _run_git(
            repo,
            ["add", "--", ".gitmodules", *(spec.path for spec in normalized_specs)],
        )
        staged = _staged_files(repo)
        expected_staged = sorted(
            {".gitmodules", *(spec.path for spec in normalized_specs)}
        )
        if staged != expected_staged:
            raise OfflineOnboardingError(
                "staged allowlist assertion failed: "
                f"expected={expected_staged}, actual={staged}"
            )

        staged_gitmodules = _git_output(repo, ["show", ":.gitmodules"])
        assertions = [
            _assert_spec(
                repo,
                spec,
                offline_remote=offline_remote,
                staged_gitmodules=staged_gitmodules,
            )
            for spec in normalized_specs
        ]
        return OfflineOnboardingResult(
            ok=True,
            mode=mode,
            repo=str(repo),
            offline_remote=offline_remote,
            submodules=assertions,
            staged_files=staged,
            message="offline submodules staged with canonical URL assertions passing",
            errors=[],
        )
    except (OfflineOnboardingError, OSError) as exc:
        return OfflineOnboardingResult(
            ok=False,
            mode=mode,
            repo=str(repo),
            offline_remote=offline_remote,
            submodules=[],
            staged_files=_staged_files(repo) if (repo / ".git").exists() else [],
            message="offline submodule onboarding failed; inspect the target repo before retrying",
            errors=[str(exc)],
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage offline governance submodules while keeping canonical URLs in "
            ".gitmodules, parent config, and nested origin."
        )
    )
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--framework-source", required=True, type=Path)
    parser.add_argument("--framework-head", required=True)
    parser.add_argument("--framework-canonical-url", required=True)
    parser.add_argument("--framework-path", default=DEFAULT_FRAMEWORK_PATH)
    parser.add_argument("--domain-source", type=Path)
    parser.add_argument("--domain-head")
    parser.add_argument("--domain-canonical-url")
    parser.add_argument("--domain-path", default=DEFAULT_DOMAIN_PATH)
    parser.add_argument("--offline-remote", default=DEFAULT_OFFLINE_REMOTE)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def _specs_from_args(args: argparse.Namespace) -> list[SubmoduleSpec]:
    specs = [
        SubmoduleSpec(
            role="framework",
            path=args.framework_path,
            source=args.framework_source,
            expected_head=args.framework_head,
            canonical_url=args.framework_canonical_url,
        )
    ]
    domain_values = (
        args.domain_source,
        args.domain_head,
        args.domain_canonical_url,
    )
    if any(value is not None for value in domain_values):
        if not all(value is not None for value in domain_values):
            raise OfflineOnboardingError(
                "--domain-source, --domain-head, and --domain-canonical-url must be provided together"
            )
        specs.append(
            SubmoduleSpec(
                role="domain_contract",
                path=args.domain_path,
                source=args.domain_source,
                expected_head=args.domain_head,
                canonical_url=args.domain_canonical_url,
            )
        )
    return specs


def format_human(result: OfflineOnboardingResult) -> str:
    lines = [
        "offline_submodule_onboarding",
        f"ok={result.ok}",
        f"mode={result.mode}",
        f"repo={result.repo}",
        f"offline_remote={result.offline_remote}",
        f"message={result.message}",
        f"staged_files={','.join(result.staged_files) if result.staged_files else '-'}",
    ]
    for item in result.submodules:
        role = item.get("role", "submodule")
        lines.extend(
            [
                f"[{role}]",
                f"path={item.get('path', '-')}",
                f"source={item.get('source', '-')}",
                f"expected_head={item.get('expected_head', item.get('source_head', '-'))}",
                f"canonical_url={item.get('canonical_url', '-')}",
                f"url_assertions_passed={item.get('url_assertions_passed', 'not_run')}",
            ]
        )
    for error in result.errors:
        lines.append(f"error={error}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        specs = _specs_from_args(args)
        result = onboard_offline_submodules(
            repo=args.repo,
            specs=specs,
            offline_remote=args.offline_remote,
            apply=args.apply,
        )
    except OfflineOnboardingError as exc:
        result = OfflineOnboardingResult(
            ok=False,
            mode="apply" if args.apply else "dry_run",
            repo=str(args.repo.resolve()),
            offline_remote=args.offline_remote,
            message="invalid offline onboarding request",
            errors=[str(exc)],
        )
    if args.format == "json":
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_human(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
