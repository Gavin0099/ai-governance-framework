#!/usr/bin/env python3
"""Simulate a no-write AUTHORITY_MANIFEST preflight consumer.

This module consumes AUTHORITY_MANIFEST evidence and emits a reviewer-facing
receipt. It does not implement prompt cache behavior, provider integration,
runtime hooks, CI wiring, or enforcement.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.authority_manifest import (
    MANIFEST_SCHEMA,
    build_authority_manifest,
    manifest_to_dict,
)


RECEIPT_SCHEMA = "AUTHORITY_MANIFEST_PREFLIGHT_RECEIPT v0.1"
RECEIPT_GENERATOR = "governance_tools.authority_manifest_preflight"
REPO_CACHE_BEHAVIOR_CLAIM = "not_observed"
REPO_RUNTIME_ENFORCEMENT_CLAIM = "not_enforced_by_repo"
NOT_CLAIMED = [
    "prompt cache implementation",
    "cache hit/miss observation",
    "provider cache behavior",
    "runtime enforcement",
    "CI/pre-push/gate enforcement",
    "hook wiring",
    "cross-repo write authorization",
]


@dataclass(frozen=True)
class PreflightReceipt:
    schema: str
    generated_by: str
    repo: str
    base_ref: str
    head_ref: str
    manifest_schema: str
    manifest_status: str
    manifest_hash: str
    authority_changed_between_refs: bool | None
    governance_drift_severity: str
    repo_enforces_prompt_cache: bool | None
    decision: str
    decision_reason: str
    required_action: str
    cache_behavior_claim: str
    runtime_enforcement_claim: str
    evidence_refs: list[str] = field(default_factory=list)
    not_claimed: list[str] = field(default_factory=lambda: list(NOT_CLAIMED))


def _lookup(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _base_receipt(
    *,
    repo: str,
    base_ref: str,
    head_ref: str,
    manifest_schema: str,
    manifest_status: str,
    manifest_hash: str,
    authority_changed_between_refs: bool | None,
    governance_drift_severity: str,
    repo_enforces_prompt_cache: bool | None,
    decision: str,
    decision_reason: str,
    required_action: str,
    evidence_refs: list[str],
) -> PreflightReceipt:
    return PreflightReceipt(
        schema=RECEIPT_SCHEMA,
        generated_by=RECEIPT_GENERATOR,
        repo=repo,
        base_ref=base_ref,
        head_ref=head_ref,
        manifest_schema=manifest_schema,
        manifest_status=manifest_status,
        manifest_hash=manifest_hash,
        authority_changed_between_refs=authority_changed_between_refs,
        governance_drift_severity=governance_drift_severity,
        repo_enforces_prompt_cache=repo_enforces_prompt_cache,
        decision=decision,
        decision_reason=decision_reason,
        required_action=required_action,
        cache_behavior_claim=REPO_CACHE_BEHAVIOR_CLAIM,
        runtime_enforcement_claim=REPO_RUNTIME_ENFORCEMENT_CLAIM,
        evidence_refs=evidence_refs,
    )


def assess_manifest_payload(payload: dict[str, Any]) -> PreflightReceipt:
    manifest_schema = str(payload.get("schema") or "")
    manifest_status = str(payload.get("status") or "")
    manifest_hash = str(payload.get("manifest_hash") or "")
    repo = str(payload.get("repo") or "<unknown>")
    base_ref = str(payload.get("base_ref") or "<unknown>")
    head_ref = str(payload.get("head_ref") or "<unknown>")
    authority_changed = _lookup(payload, "invalidation", "authority_changed_between_refs")
    drift_severity = str(_lookup(payload, "checks", "governance_drift_checker", "severity") or "")
    repo_enforces = payload.get("repo_enforces_prompt_cache")

    evidence_refs = [
        f"manifest_schema={manifest_schema or '<missing>'}",
        f"manifest_status={manifest_status or '<missing>'}",
        f"manifest_hash={manifest_hash or '<missing>'}",
    ]

    if manifest_schema != MANIFEST_SCHEMA:
        return _base_receipt(
            repo=repo,
            base_ref=base_ref,
            head_ref=head_ref,
            manifest_schema=manifest_schema or "<missing>",
            manifest_status=manifest_status or "<missing>",
            manifest_hash=manifest_hash or "<missing>",
            authority_changed_between_refs=None if not isinstance(authority_changed, bool) else authority_changed,
            governance_drift_severity=drift_severity or "<missing>",
            repo_enforces_prompt_cache=(repo_enforces if isinstance(repo_enforces, bool) else None),
            decision="cache_unsafe",
            decision_reason="wrong_or_missing_manifest_schema",
            required_action="manual_review",
            evidence_refs=evidence_refs,
        )

    missing_fields: list[str] = []
    if not manifest_status:
        missing_fields.append("status")
    if not manifest_hash:
        missing_fields.append("manifest_hash")
    if not isinstance(authority_changed, bool):
        missing_fields.append("invalidation.authority_changed_between_refs")
    if not drift_severity:
        missing_fields.append("checks.governance_drift_checker.severity")
    if not isinstance(repo_enforces, bool):
        missing_fields.append("repo_enforces_prompt_cache")

    if missing_fields:
        return _base_receipt(
            repo=repo,
            base_ref=base_ref,
            head_ref=head_ref,
            manifest_schema=manifest_schema,
            manifest_status=manifest_status or "<missing>",
            manifest_hash=manifest_hash or "<missing>",
            authority_changed_between_refs=None if not isinstance(authority_changed, bool) else authority_changed,
            governance_drift_severity=drift_severity or "<missing>",
            repo_enforces_prompt_cache=(repo_enforces if isinstance(repo_enforces, bool) else None),
            decision="not_checked",
            decision_reason=f"missing_required_fields:{','.join(missing_fields)}",
            required_action="manual_review",
            evidence_refs=evidence_refs + [f"missing_fields={','.join(missing_fields)}"],
        )

    if repo_enforces is not False:
        return _base_receipt(
            repo=repo,
            base_ref=base_ref,
            head_ref=head_ref,
            manifest_schema=manifest_schema,
            manifest_status=manifest_status,
            manifest_hash=manifest_hash,
            authority_changed_between_refs=authority_changed,
            governance_drift_severity=drift_severity,
            repo_enforces_prompt_cache=repo_enforces,
            decision="cache_unsafe",
            decision_reason="repo_enforces_prompt_cache_not_false",
            required_action="manual_review",
            evidence_refs=evidence_refs,
        )

    if drift_severity == "critical":
        return _base_receipt(
            repo=repo,
            base_ref=base_ref,
            head_ref=head_ref,
            manifest_schema=manifest_schema,
            manifest_status=manifest_status,
            manifest_hash=manifest_hash,
            authority_changed_between_refs=authority_changed,
            governance_drift_severity=drift_severity,
            repo_enforces_prompt_cache=repo_enforces,
            decision="cache_unsafe",
            decision_reason="critical_governance_drift",
            required_action="manual_review",
            evidence_refs=evidence_refs,
        )

    if authority_changed:
        return _base_receipt(
            repo=repo,
            base_ref=base_ref,
            head_ref=head_ref,
            manifest_schema=manifest_schema,
            manifest_status=manifest_status,
            manifest_hash=manifest_hash,
            authority_changed_between_refs=authority_changed,
            governance_drift_severity=drift_severity,
            repo_enforces_prompt_cache=repo_enforces,
            decision="reload_required",
            decision_reason="authority_changed_between_refs",
            required_action="reload_authority_files",
            evidence_refs=evidence_refs,
        )

    if manifest_status == "candidate" and drift_severity in {"ok", "warning"}:
        return _base_receipt(
            repo=repo,
            base_ref=base_ref,
            head_ref=head_ref,
            manifest_schema=manifest_schema,
            manifest_status=manifest_status,
            manifest_hash=manifest_hash,
            authority_changed_between_refs=authority_changed,
            governance_drift_severity=drift_severity,
            repo_enforces_prompt_cache=repo_enforces,
            decision="reuse_candidate",
            decision_reason="candidate_manifest_with_acceptable_drift_and_unchanged_authority",
            required_action="none",
            evidence_refs=evidence_refs,
        )

    return _base_receipt(
        repo=repo,
        base_ref=base_ref,
        head_ref=head_ref,
        manifest_schema=manifest_schema,
        manifest_status=manifest_status,
        manifest_hash=manifest_hash,
        authority_changed_between_refs=authority_changed,
        governance_drift_severity=drift_severity,
        repo_enforces_prompt_cache=repo_enforces,
        decision="not_checked",
        decision_reason="unsupported_manifest_status_or_drift_state",
        required_action="manual_review",
        evidence_refs=evidence_refs,
    )


def assess_manifest_path(path: Path, *, project_root: Path | None = None) -> PreflightReceipt:
    repo = str(project_root.resolve()) if project_root else "<unknown>"
    if not path.exists():
        return _base_receipt(
            repo=repo,
            base_ref="<unknown>",
            head_ref="<unknown>",
            manifest_schema="<missing>",
            manifest_status="<missing>",
            manifest_hash="<missing>",
            authority_changed_between_refs=None,
            governance_drift_severity="<missing>",
            repo_enforces_prompt_cache=None,
            decision="cache_unsafe",
            decision_reason="manifest_json_missing",
            required_action="manual_review",
            evidence_refs=[f"manifest_json={path}"],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _base_receipt(
            repo=repo,
            base_ref="<unknown>",
            head_ref="<unknown>",
            manifest_schema="<unreadable>",
            manifest_status="<unreadable>",
            manifest_hash="<unreadable>",
            authority_changed_between_refs=None,
            governance_drift_severity="<unreadable>",
            repo_enforces_prompt_cache=None,
            decision="cache_unsafe",
            decision_reason="manifest_json_unreadable",
            required_action="manual_review",
            evidence_refs=[f"manifest_json={path}"],
        )
    receipt = assess_manifest_payload(payload)
    merged_refs = [f"manifest_json={path}", *receipt.evidence_refs]
    return PreflightReceipt(**{**asdict(receipt), "evidence_refs": merged_refs})


def build_generated_receipt(
    project_root: Path,
    *,
    base_ref: str,
    head_ref: str,
    framework_root: Path | None = None,
) -> PreflightReceipt:
    try:
        manifest = build_authority_manifest(
            project_root,
            base_ref=base_ref,
            head_ref=head_ref,
            framework_root=framework_root,
        )
    except ValueError as exc:
        return _base_receipt(
            repo=str(project_root.resolve()),
            base_ref=base_ref,
            head_ref=head_ref,
            manifest_schema="<generation_failed>",
            manifest_status="<generation_failed>",
            manifest_hash="<generation_failed>",
            authority_changed_between_refs=None,
            governance_drift_severity="<generation_failed>",
            repo_enforces_prompt_cache=None,
            decision="cache_unsafe",
            decision_reason=f"authority_manifest_generation_failed:{exc}",
            required_action="manual_review",
            evidence_refs=[f"project_root={project_root.resolve()}"],
        )
    receipt = assess_manifest_payload(manifest_to_dict(manifest))
    merged_refs = [f"generated_manifest_project_root={project_root.resolve()}", *receipt.evidence_refs]
    return PreflightReceipt(**{**asdict(receipt), "evidence_refs": merged_refs})


def receipt_to_dict(receipt: PreflightReceipt) -> dict[str, Any]:
    return asdict(receipt)


def format_json(receipt: PreflightReceipt) -> str:
    return json.dumps(receipt_to_dict(receipt), ensure_ascii=False, indent=2)


def format_human(receipt: PreflightReceipt) -> str:
    lines = [
        "[authority_manifest_preflight]",
        f"schema={receipt.schema}",
        f"generated_by={receipt.generated_by}",
        f"repo={receipt.repo}",
        f"base_ref={receipt.base_ref}",
        f"head_ref={receipt.head_ref}",
        f"manifest_schema={receipt.manifest_schema}",
        f"manifest_status={receipt.manifest_status}",
        f"manifest_hash={receipt.manifest_hash}",
        f"authority_changed_between_refs={receipt.authority_changed_between_refs}",
        f"governance_drift_severity={receipt.governance_drift_severity}",
        f"repo_enforces_prompt_cache={receipt.repo_enforces_prompt_cache}",
        f"decision={receipt.decision}",
        f"decision_reason={receipt.decision_reason}",
        f"required_action={receipt.required_action}",
        f"cache_behavior_claim={receipt.cache_behavior_claim}",
        f"runtime_enforcement_claim={receipt.runtime_enforcement_claim}",
        "",
        "evidence_refs:",
    ]
    lines.extend(f"- {ref}" for ref in receipt.evidence_refs)
    lines.append("")
    lines.append("not_claimed:")
    lines.extend(f"- {item}" for item in receipt.not_claimed)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulate a no-write AUTHORITY_MANIFEST preflight consumer."
    )
    parser.add_argument("--project-root", default=".", help="Repository root (default: .)")
    parser.add_argument("--base-ref", help="Base git ref for generated manifest mode")
    parser.add_argument("--head-ref", help="Head git ref for generated manifest mode")
    parser.add_argument("--manifest-json", help="Existing AUTHORITY_MANIFEST JSON path")
    parser.add_argument("--framework-root", help="Explicit framework root for generated manifest mode")
    parser.add_argument("--format", choices=("json", "human"), default="human")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = Path(args.project_root).resolve()
    if args.manifest_json:
        receipt = assess_manifest_path(Path(args.manifest_json), project_root=project_root)
    else:
        if not args.base_ref or not args.head_ref:
            print("authority_manifest_preflight: --base-ref and --head-ref are required without --manifest-json", file=sys.stderr)
            return 2
        receipt = build_generated_receipt(
            project_root,
            base_ref=args.base_ref,
            head_ref=args.head_ref,
            framework_root=Path(args.framework_root) if args.framework_root else None,
        )

    if args.format == "json":
        print(format_json(receipt))
    else:
        print(format_human(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
