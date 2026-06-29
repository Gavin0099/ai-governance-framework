#!/usr/bin/env python3
"""Generate a read-only AUTHORITY_MANIFEST candidate from baseline truth.

This module is detection/accountability only. It does not implement prompt
cache behavior, runtime enforcement, CI wiring, hooks, or baseline mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.governance_drift_checker import (
    BASELINE_YAML_RELPATH,
    check_governance_drift,
    _read_baseline_yaml,
)


MANIFEST_SCHEMA = "AUTHORITY_MANIFEST v1"
GENERATOR = "governance_tools.authority_manifest"


@dataclass(frozen=True)
class AuthorityFile:
    path: str
    baseline_hash: str
    baseline_hash_source: str
    current_hash: str | None
    current_hash_source: str
    base_hash: str | None
    base_hash_source: str
    head_hash: str | None
    head_hash_source: str
    changed_between_refs: bool | None
    overridable: str
    loaded_as: str
    invalidates_cache_on_change: bool


@dataclass(frozen=True)
class AuthorityManifest:
    schema: str
    status: str
    repo: str
    base_ref: str
    head_ref: str
    generated_at: str
    generated_by: str
    baseline_source: dict[str, Any]
    authority_files: list[AuthorityFile]
    checks: dict[str, Any]
    invalidation: dict[str, Any]
    manifest_hash: str
    harness_dependent: bool
    repo_enforces_prompt_cache: bool
    claim_ceiling: str
    non_claims: list[str] = field(default_factory=list)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return _sha256_bytes(path.read_bytes())


def _git_show(repo_root: Path, ref: str, relpath: str) -> bytes | None:
    command = ["git", "-C", str(repo_root), "show", f"{ref}:{relpath}"]
    proc = subprocess.run(command, capture_output=True, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout


def _git_blob_hash(repo_root: Path, ref: str, relpath: str) -> str | None:
    data = _git_show(repo_root, ref, relpath)
    if data is None:
        return None
    return _sha256_bytes(data)


def _authority_paths_from_baseline(baseline: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in baseline:
        if key.startswith("sha256."):
            paths.append(key.removeprefix("sha256."))
    return sorted(paths)


def _loaded_as(overridable: str) -> str:
    if overridable == "protected":
        return "protected_authority"
    return "overridable_authority"


def _stable_manifest_hash(payload: dict[str, Any]) -> str:
    stable_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "manifest_hash"}
    }
    encoded = json.dumps(stable_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_authority_manifest(
    project_root: Path,
    *,
    base_ref: str,
    head_ref: str,
    framework_root: Path | None = None,
) -> AuthorityManifest:
    repo_root = project_root.resolve()
    baseline = _read_baseline_yaml(repo_root)
    if baseline is None:
        raise ValueError(f"missing or unreadable {BASELINE_YAML_RELPATH}")

    authority_files: list[AuthorityFile] = []
    changed_paths: list[str] = []
    missing_at_base: list[str] = []
    missing_at_head: list[str] = []

    for relpath in _authority_paths_from_baseline(baseline):
        baseline_hash = str(baseline.get(f"sha256.{relpath}", ""))
        current_hash = _sha256_file(repo_root / relpath)
        base_hash = _git_blob_hash(repo_root, base_ref, relpath)
        head_hash = _git_blob_hash(repo_root, head_ref, relpath)
        changed_between_refs = None
        if base_hash is None:
            missing_at_base.append(relpath)
        if head_hash is None:
            missing_at_head.append(relpath)
        if base_hash is not None and head_hash is not None:
            changed_between_refs = base_hash != head_hash
            if changed_between_refs:
                changed_paths.append(relpath)

        overridable = str(baseline.get(f"overridable.{relpath}", "unknown"))
        authority_files.append(
            AuthorityFile(
                path=relpath,
                baseline_hash=baseline_hash,
                baseline_hash_source=f"{BASELINE_YAML_RELPATH}:sha256.{relpath}",
                current_hash=current_hash,
                current_hash_source="working_tree_bytes",
                base_hash=base_hash,
                base_hash_source=f"git_blob:{base_ref}:{relpath}",
                head_hash=head_hash,
                head_hash_source=f"git_blob:{head_ref}:{relpath}",
                changed_between_refs=changed_between_refs,
                overridable=overridable,
                loaded_as=_loaded_as(overridable),
                invalidates_cache_on_change=True,
            )
        )

    drift = check_governance_drift(repo_root=repo_root, framework_root=framework_root)
    drift_summary = {
        "severity": drift.severity,
        "ok": drift.ok,
        "checks": drift.checks,
        "warnings": drift.warnings,
        "errors": drift.errors,
    }
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    manifest_without_hash = {
        "schema": MANIFEST_SCHEMA,
        "status": "candidate",
        "repo": str(repo_root),
        "base_ref": base_ref,
        "head_ref": head_ref,
        "generated_at": generated_at,
        "generated_by": GENERATOR,
        "baseline_source": {
            "path": BASELINE_YAML_RELPATH,
            "source_commit": baseline.get("source_commit"),
            "baseline_version": baseline.get("baseline_version"),
            "initialized_at": baseline.get("initialized_at"),
            "initialized_by": baseline.get("initialized_by"),
            "authority_paths_source": "sha256.* keys from .governance/baseline.yaml",
        },
        "authority_files": [asdict(item) for item in authority_files],
        "checks": {"governance_drift_checker": drift_summary},
        "invalidation": {
            "authority_changed_between_refs": bool(changed_paths or missing_at_base or missing_at_head),
            "changed_paths": changed_paths,
            "missing_at_base": missing_at_base,
            "missing_at_head": missing_at_head,
            "signal": "authority_change_invalidation_signal",
            "effect": "detection_accountability_only",
        },
        "harness_dependent": True,
        "repo_enforces_prompt_cache": False,
        "claim_ceiling": "candidate authority manifest; detection/accountability only; not prompt-cache enforcement",
        "non_claims": [
            "prompt cache implementation",
            "cache hit/miss monitoring",
            "runtime enforcement",
            "CI/pre-push/gate enforcement",
            "baseline rewrite",
            "memory behavior change",
            "cross-repo write authorization",
        ],
    }
    manifest_hash = _stable_manifest_hash(manifest_without_hash)

    return AuthorityManifest(
        schema=MANIFEST_SCHEMA,
        status="candidate",
        repo=str(repo_root),
        base_ref=base_ref,
        head_ref=head_ref,
        generated_at=generated_at,
        generated_by=GENERATOR,
        baseline_source=manifest_without_hash["baseline_source"],
        authority_files=authority_files,
        checks=manifest_without_hash["checks"],
        invalidation=manifest_without_hash["invalidation"],
        manifest_hash=manifest_hash,
        harness_dependent=True,
        repo_enforces_prompt_cache=False,
        claim_ceiling=manifest_without_hash["claim_ceiling"],
        non_claims=manifest_without_hash["non_claims"],
    )


def manifest_to_dict(manifest: AuthorityManifest) -> dict[str, Any]:
    return asdict(manifest)


def format_json(manifest: AuthorityManifest) -> str:
    return json.dumps(manifest_to_dict(manifest), ensure_ascii=False, indent=2)


def format_human(manifest: AuthorityManifest) -> str:
    lines = [
        "[authority_manifest]",
        f"schema={manifest.schema}",
        f"status={manifest.status}",
        f"repo={manifest.repo}",
        f"base_ref={manifest.base_ref}",
        f"head_ref={manifest.head_ref}",
        f"baseline_source={manifest.baseline_source['path']}",
        f"authority_changed_between_refs={manifest.invalidation['authority_changed_between_refs']}",
        f"changed_paths={', '.join(manifest.invalidation['changed_paths']) or '<none>'}",
        f"governance_drift_checker.severity={manifest.checks['governance_drift_checker']['severity']}",
        f"repo_enforces_prompt_cache={manifest.repo_enforces_prompt_cache}",
        f"claim_ceiling={manifest.claim_ceiling}",
        f"manifest_hash={manifest.manifest_hash}",
        "",
        "authority_files:",
    ]
    for item in manifest.authority_files:
        marker = "changed" if item.changed_between_refs else "unchanged"
        if item.changed_between_refs is None:
            marker = "unavailable"
        lines.append(
            f"- {item.path}: baseline={item.baseline_hash} "
            f"base={item.base_hash or '<missing>'} head={item.head_hash or '<missing>'} "
            f"{marker} loaded_as={item.loaded_as} "
            f"hash_sources=baseline_yaml/working_tree/git_blob"
        )
    lines.append("")
    lines.append("non_claims:")
    for claim in manifest.non_claims:
        lines.append(f"- {claim}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a read-only AUTHORITY_MANIFEST candidate from baseline truth."
    )
    parser.add_argument("--project-root", default=".", help="Repository root (default: .)")
    parser.add_argument("--base-ref", required=True, help="Base git ref for authority comparison")
    parser.add_argument("--head-ref", required=True, help="Head git ref for authority comparison")
    parser.add_argument("--framework-root", help="Explicit framework root for drift checker")
    parser.add_argument("--format", choices=("json", "human"), default="human")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = build_authority_manifest(
            Path(args.project_root),
            base_ref=args.base_ref,
            head_ref=args.head_ref,
            framework_root=Path(args.framework_root) if args.framework_root else None,
        )
    except ValueError as exc:
        print(f"authority_manifest: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(format_json(manifest))
    else:
        print(format_human(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
