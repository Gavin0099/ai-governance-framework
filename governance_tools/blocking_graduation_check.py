#!/usr/bin/env python3
"""Readiness report for promoting a guard code from advisory to blocking.

Why not "N days with zero findings"
-----------------------------------
A quiet window is ambiguous. Zero findings is equally consistent with a clean
repo, a guard nobody ran, a scope that matches nothing, a broken matcher, and a
baseline that swallowed everything. Promoting on silence promotes whichever of
those is actually true.

So this tool never treats absence of findings as evidence. It asks instead:
did the guard run, over how many sessions, does it still discriminate on known
fixtures, were its false signals reviewed, does it survive a mutation of the
property it protects, are in-window violations actually cleared, and did the
owner approve the profile.

What this tool will not do
--------------------------
It does not enable blocking. Graduation stays a human edit to
``governance/memory_blocking_policy.json``. It cannot satisfy the owner-approval
criterion on the owner's behalf, and an attestation naming an AI identity is
rejected outright.

Read-only.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # pragma: no cover - direct-script fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.guard_enforcement_census import LEVELS, run_census
from governance_tools.memory_authority_guard import (
    _ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM as ACTIVE_WINDOW_FROM,
    _DATE_FILENAME as _DAILY_FILENAME,
    filter_active_non_canonical_writer_violations,
    run_guard,
)

CRITERIA_RELPATH = "governance/blocking_graduation_criteria.json"
CRITERIA_SCHEMA = "blocking_graduation_criteria.v0.1"
ATTESTATION_SCHEMA = "graduation_attestation.v0.1"

MET = "met"
NOT_MET = "not_met"
# Deliberately distinct from not_met: "we could not tell" must never be read as
# "it is fine", and must never be read as a hard failure either.
UNEVALUABLE = "unevaluable"


@dataclass
class CriterionResult:
    id: str
    kind: str
    status: str
    detail: str = ""
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "detail": self.detail,
            "evidence": self.evidence,
        }


# ── criteria file ─────────────────────────────────────────────────────────────

def _criteria_digest(project_root: Path, path: Path | None = None) -> str | None:
    """sha256 of the criteria file, so an approval can be bound to its content."""
    target = path or (project_root / CRITERIA_RELPATH)
    try:
        return hashlib.sha256(target.read_bytes()).hexdigest()
    except OSError:
        return None


def load_criteria(project_root: Path, path: Path | None = None) -> dict[str, Any]:
    target = path or (project_root / CRITERIA_RELPATH)
    if not target.is_file():
        return {"error": "criteria_not_found", "criteria": []}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": f"criteria_unreadable: {exc}", "criteria": []}
    if not isinstance(payload, dict) or payload.get("criteria_schema") != CRITERIA_SCHEMA:
        return {"error": "criteria_schema_mismatch", "criteria": []}
    return {"error": None, **payload}


# ── attestation handling ──────────────────────────────────────────────────────

def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _check_attestation(
    project_root: Path,
    criterion: dict[str, Any],
    *,
    now: datetime,
    max_age_days: int,
    ai_identities: list[str],
    owner_registry: list[str],
    authority_ref_patterns: list[str],
    criteria_digest: str | None,
) -> CriterionResult:
    cid = str(criterion.get("id"))
    rel = str(criterion.get("attestation") or "").strip()
    result = CriterionResult(id=cid, kind="attestation", status=NOT_MET)
    if not rel:
        result.status = UNEVALUABLE
        result.detail = "no_attestation_path_declared"
        return result

    path = project_root / rel
    if not path.is_file():
        result.detail = f"attestation_absent:{rel}"
        return result
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.detail = f"attestation_unreadable:{exc}"
        return result
    if not isinstance(payload, dict):
        result.detail = "attestation_not_an_object"
        return result
    if payload.get("attestation_schema") != ATTESTATION_SCHEMA:
        result.detail = "attestation_schema_mismatch"
        return result

    attested_by = str(payload.get("attested_by") or "").strip()
    if not attested_by:
        result.detail = "attestation_missing_attested_by"
        return result

    # An AI agent cannot sign off on its own enforcement. This is checked for
    # every attestation, not only the owner-approval one, because a mutation or
    # fixture review self-signed by the agent under test is worth nothing.
    lowered = attested_by.lower()
    if any(identity in lowered for identity in ai_identities):
        result.detail = f"attested_by_ai_identity_rejected:{attested_by}"
        return result

    # Naming a human is necessary but nowhere near sufficient: "Gavin" is a
    # name, not an authorisation. The signer must be someone the repo has
    # registered as able to approve enforcement.
    if owner_registry and not any(
        attested_by.strip().lower() == owner.strip().lower() for owner in owner_registry
    ):
        result.detail = f"attested_by_not_in_owner_registry:{attested_by}"
        return result

    authority_ref = str(payload.get("authority_ref") or "").strip()
    if not authority_ref:
        result.detail = "attestation_missing_authority_ref"
        return result
    if not (project_root / authority_ref).exists():
        result.detail = f"authority_ref_missing:{authority_ref}"
        return result
    # Any existing file would otherwise satisfy this; README.md is not an
    # authority document.
    normalized_ref = authority_ref.replace("\\", "/")
    if authority_ref_patterns and not any(
        fnmatch.fnmatch(normalized_ref, pattern) for pattern in authority_ref_patterns
    ):
        result.detail = f"authority_ref_not_an_authority_document:{authority_ref}"
        return result

    # Bind the approval to the exact criteria it approved. Without this the
    # criteria could be weakened after signing and the signature would survive.
    if criteria_digest is not None:
        recorded = str(payload.get("criteria_digest") or "").strip().lower()
        if not recorded:
            result.detail = "attestation_missing_criteria_digest"
            return result
        if recorded != criteria_digest:
            result.detail = (
                f"attestation_criteria_digest_mismatch:signed={recorded[:12]}"
                f"_current={criteria_digest[:12]}"
            )
            return result

    if payload.get("result") is not True:
        result.detail = f"attestation_result_not_true:{payload.get('result')!r}"
        return result

    attested_at = _parse_timestamp(payload.get("attested_at"))
    if attested_at is None:
        result.detail = "attestation_missing_or_invalid_attested_at"
        return result
    age_days = (now - attested_at).total_seconds() / 86400.0
    if max_age_days > 0 and age_days > max_age_days:
        result.detail = f"attestation_stale:{age_days:.0f}d>{max_age_days}d"
        return result

    # Repository JSON proves only that bytes naming this owner exist. This
    # process can create those bytes too, so it cannot authenticate the signer.
    result.status = UNEVALUABLE
    result.detail = (
        f"declared_attestation_valid_but_signer_identity_unverified:"
        f"attested_by={attested_by} age={age_days:.0f}d"
    )
    result.evidence = [rel, authority_ref]
    return result


# ── machine criteria ──────────────────────────────────────────────────────────

def _check_execution_coverage(
    project_root: Path, criterion: dict[str, Any], census: dict[str, Any]
) -> CriterionResult:
    cid = str(criterion.get("id"))
    surface_id = str(criterion.get("surface_id") or "")
    min_level = str(criterion.get("min_level") or "invoked")
    result = CriterionResult(id=cid, kind="machine", status=NOT_MET)

    entry = next(
        (item for item in census.get("surfaces", []) if item.get("id") == surface_id),
        None,
    )
    if entry is None:
        result.status = UNEVALUABLE
        result.detail = f"surface_not_registered:{surface_id}"
        return result

    level = entry.get("level")
    if level not in LEVELS:
        result.detail = f"surface_level={level}"
        return result
    if LEVELS.index(level) >= LEVELS.index(min_level):
        result.status = MET
    result.detail = f"surface_level={level} required={min_level}"
    result.evidence = [f"{surface_id}:{level}"]
    return result


def _check_session_coverage(
    project_root: Path, criterion: dict[str, Any], *, now: datetime, window_days: int
) -> CriterionResult:
    cid = str(criterion.get("id"))
    result = CriterionResult(id=cid, kind="machine", status=NOT_MET)
    pattern = str(criterion.get("evidence_glob") or "").strip()
    ran_key = str(criterion.get("ran_key") or "").strip()
    min_ratio = float(criterion.get("min_ratio", 0.9))
    min_sessions = int(criterion.get("min_sessions", 1))
    if not pattern or not ran_key:
        result.status = UNEVALUABLE
        result.detail = "coverage_criterion_incomplete"
        return result

    cutoff = (now - timedelta(days=window_days)).timestamp()
    total = 0
    ran = 0
    for path in project_root.glob(pattern):
        if not path.is_file() or path.stat().st_mtime < cutoff:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict) or ran_key not in payload:
            continue
        total += 1
        if payload.get(ran_key):
            ran += 1

    if total < min_sessions:
        # Too few sessions is not a pass and not a fail: there is no sample.
        result.status = UNEVALUABLE
        result.detail = (
            f"insufficient_sessions_in_window: {total}<{min_sessions} "
            f"({window_days}d)"
        )
        return result

    ratio = ran / total
    result.detail = f"ran={ran}/{total} ratio={ratio:.2f} required={min_ratio:.2f}"
    result.evidence = [pattern]
    if ratio >= min_ratio:
        result.status = MET
    return result


def _newest_baseline(project_root: Path, pattern: str) -> tuple[Path, float] | None:
    newest: tuple[Path, float] | None = None
    for path in project_root.glob(pattern):
        if not path.is_file():
            continue
        mtime = path.stat().st_mtime
        if newest is None or mtime > newest[1]:
            newest = (path, mtime)
    return newest


def _check_active_violations(
    project_root: Path,
    criterion: dict[str, Any],
    memory_root: Path,
    *,
    now: datetime,
    window_days: int,
    baseline_glob: str | None,
) -> CriterionResult:
    cid = str(criterion.get("id"))
    result = CriterionResult(id=cid, kind="machine", status=NOT_MET)
    if not memory_root.is_dir():
        result.status = UNEVALUABLE
        result.detail = f"memory_root_absent:{memory_root}"
        return result

    # A baseline rebuilt inside the observation window re-freezes current debt
    # as accepted, which can zero out active findings without anything being
    # fixed. That invalidates the window rather than passing it.
    if baseline_glob:
        newest = _newest_baseline(project_root, baseline_glob)
        if newest is not None:
            baseline_path, mtime = newest
            age_days = (now.timestamp() - mtime) / 86400.0
            if age_days < window_days:
                result.status = UNEVALUABLE
                result.detail = (
                    f"baseline_rebuilt_inside_observation_window:{baseline_path.name}"
                    f"_age={age_days:.1f}d<{window_days}d"
                )
                return result
    try:
        guard = run_guard(memory_root, project_root, skip_git=True)
    except Exception as exc:
        result.status = UNEVALUABLE
        result.detail = f"guard_run_failed:{exc}"
        return result

    active = filter_active_non_canonical_writer_violations(guard.get("violations", []))
    total = int(guard.get("violation_count", 0))
    result.detail = (
        f"active_non_canonical_writer={len(active)} "
        f"(historical debt excluded; total findings={total})"
    )
    result.evidence = sorted({str(item.get("file")) for item in active})
    if not active:
        result.status = MET
    return result


def _check_baseline_non_interference(
    project_root: Path, criterion: dict[str, Any], memory_root: Path
) -> CriterionResult:
    """The baseline must be incapable of hiding an in-window finding.

    `memory_authority_baseline` splits active violations out before bucketing
    (SI-1), so this verifies the property holds for the real baseline rather
    than trusting the invariant.
    """
    cid = str(criterion.get("id"))
    result = CriterionResult(id=cid, kind="machine", status=NOT_MET)
    pattern = str(criterion.get("baseline_glob") or "").strip()
    if not pattern:
        result.status = UNEVALUABLE
        result.detail = "no_baseline_glob_declared"
        return result

    newest = _newest_baseline(project_root, pattern)
    if newest is None:
        # No baseline means nothing can be suppressed by one.
        result.status = MET
        result.detail = "no_baseline_present_nothing_can_be_suppressed"
        return result

    path, _mtime = newest
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.status = UNEVALUABLE
        result.detail = f"baseline_unreadable:{exc}"
        return result

    buckets = payload.get("buckets")
    if not isinstance(buckets, list):
        result.status = UNEVALUABLE
        result.detail = f"baseline_shape_unrecognised:{path.name}"
        return result

    # The cutoff comes from the guard, not from the baseline file. A baseline
    # that simply omits the field would otherwise make this check pass
    # vacuously — the exact failure mode it is meant to detect.
    cutoff = f"{ACTIVE_WINDOW_FROM}.md"
    writer_buckets = [
        bucket
        for bucket in buckets
        if isinstance(bucket, dict)
        and bucket.get("code") == "non_canonical_writer"
    ]
    missing_file = [
        bucket
        for bucket in writer_buckets
        if not _DAILY_FILENAME.match(str(bucket.get("file") or ""))
    ]
    if missing_file:
        # Baseline schema v0.2 did not retain the identity fields used to make
        # each bucket key. Treat those legacy bytes as unevaluable: reporting
        # MET would claim non-interference from data that cannot answer it.
        result.status = UNEVALUABLE
        result.detail = (
            f"baseline_missing_machine_readable_file:{path.name} "
            f"affected_buckets={len(missing_file)}"
        )
        result.evidence = [path.name]
        return result

    leaked = [
        bucket
        for bucket in writer_buckets
        if str(bucket.get("file")) >= cutoff
    ]
    result.detail = (
        f"baseline={path.name} buckets={len(buckets)} active_from={ACTIVE_WINDOW_FROM} "
        f"in_window_buckets_frozen={len(leaked)}"
    )
    result.evidence = [path.name] + [str(b.get("file")) for b in leaked[:5]]
    if not leaked:
        result.status = MET
    return result


def _check_rollback_available(
    project_root: Path, criterion: dict[str, Any]
) -> CriterionResult:
    """Enforcement that cannot be turned off is not something to switch on."""
    cid = str(criterion.get("id"))
    result = CriterionResult(id=cid, kind="machine", status=NOT_MET)
    rel = str(criterion.get("policy_path") or "").strip()
    if not rel:
        result.status = UNEVALUABLE
        result.detail = "no_policy_path_declared"
        return result

    path = project_root / rel
    if not path.is_file():
        # No policy file is itself the off state, and creating one is the
        # documented way in. Nothing to roll back from.
        result.status = MET
        result.detail = f"no_policy_file_blocking_is_off:{rel}"
        return result

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.detail = f"policy_unreadable:{exc}"
        return result
    if not isinstance(payload, dict) or "enabled" not in payload:
        result.detail = "policy_has_no_enabled_switch"
        return result
    if not os.access(path, os.W_OK):
        result.detail = f"policy_not_writable:{rel}"
        return result

    documented = any(
        isinstance(value, str) and "kill switch" in value.lower()
        for value in payload.values()
    )
    result.detail = f"enabled_switch_present writable=True documented={documented}"
    result.evidence = [rel]
    if documented:
        result.status = MET
    else:
        result.detail += " (no kill-switch note in policy file)"
    return result


# ── assembly ──────────────────────────────────────────────────────────────────

def evaluate(
    project_root: Path,
    *,
    memory_root: Path | None = None,
    criteria_path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp = now or datetime.now(timezone.utc)
    config = load_criteria(project_root, criteria_path)
    if config.get("error"):
        return {
            "tool": "blocking_graduation_check",
            "error": config["error"],
            "ready_to_propose": False,
            "criteria": [],
        }

    window_days = int(config.get("observation_window_days", 30))
    attestation_max_age = int(config.get("attestation_max_age_days", 90))
    ai_identities = [
        str(item).lower() for item in config.get("ai_identities_may_not_attest", [])
    ]
    owner_registry = [str(item) for item in config.get("owner_registry", [])]
    authority_ref_patterns = [
        str(item) for item in config.get("authority_ref_patterns", [])
    ]
    baseline_glob = config.get("baseline_glob")
    criteria_digest = (
        _criteria_digest(project_root, criteria_path)
        if config.get("require_criteria_digest")
        else None
    )
    census = run_census(project_root)
    resolved_memory_root = memory_root or (project_root / "memory")

    results: list[CriterionResult] = []
    for criterion in config.get("criteria", []):
        cid = str(criterion.get("id"))
        kind = str(criterion.get("kind"))
        if kind == "attestation":
            results.append(
                _check_attestation(
                    project_root,
                    criterion,
                    now=timestamp,
                    max_age_days=attestation_max_age,
                    ai_identities=ai_identities,
                    owner_registry=owner_registry,
                    authority_ref_patterns=authority_ref_patterns,
                    criteria_digest=criteria_digest,
                )
            )
        elif cid == "guard_execution_coverage":
            results.append(_check_execution_coverage(project_root, criterion, census))
        elif cid == "session_coverage":
            results.append(
                _check_session_coverage(
                    project_root, criterion, now=timestamp, window_days=window_days
                )
            )
        elif cid == "active_violations_clear":
            results.append(
                _check_active_violations(
                    project_root,
                    criterion,
                    resolved_memory_root,
                    now=timestamp,
                    window_days=window_days,
                    baseline_glob=str(baseline_glob) if baseline_glob else None,
                )
            )
        elif cid == "baseline_non_interference":
            results.append(
                _check_baseline_non_interference(
                    project_root, criterion, resolved_memory_root
                )
            )
        elif cid == "rollback_available":
            results.append(_check_rollback_available(project_root, criterion))
        else:
            results.append(
                CriterionResult(
                    id=cid, kind=kind, status=UNEVALUABLE, detail="no_checker_for_criterion"
                )
            )

    met = [item for item in results if item.status == MET]
    unevaluable = [item for item in results if item.status == UNEVALUABLE]

    # Only every criterion being MET permits a proposal. An unevaluable
    # criterion blocks the proposal exactly as a failing one does, because the
    # question it answers is still open.
    ready = bool(results) and len(met) == len(results)

    return {
        "tool": "blocking_graduation_check",
        "version": "0.1",
        "generated_at": timestamp.isoformat(),
        "project_root": str(project_root),
        "observation_window_days": window_days,
        "criteria_total": len(results),
        "criteria_met": len(met),
        "criteria_unevaluable": len(unevaluable),
        "ready_to_propose": ready,
        "criteria": [item.as_dict() for item in results],
        "rejected_criterion": config.get("rejected_criterion"),
        "claim_ceiling": [
            "ready_to_propose means the recorded preconditions hold, not that blocking is safe",
            "enabling a code stays a human edit to governance/memory_blocking_policy.json",
            "repository JSON can declare an attestation but cannot authenticate its signer",
            "this tool cannot satisfy owner approval and never enables anything",
        ],
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _human(result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"[blocking_graduation_check] error: {result['error']}"
    lines = [
        "[blocking_graduation_check] "
        f"{result['criteria_met']}/{result['criteria_total']} met, "
        f"{result['criteria_unevaluable']} unevaluable"
    ]
    for item in result["criteria"]:
        lines.append(f"  {item['status']:<11} {item['id']}: {item['detail']}")
    lines.append(f"  ready_to_propose: {result['ready_to_propose']}")
    lines.append("  note: proposing is not enabling; enabling stays a human edit.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report whether a guard code meets the advisory→blocking preconditions."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--memory-root")
    parser.add_argument("--criteria")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    result = evaluate(
        project_root,
        memory_root=Path(args.memory_root).resolve() if args.memory_root else None,
        criteria_path=Path(args.criteria).resolve() if args.criteria else None,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_human(result))
    # Always 0: this is a readiness report, not a gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
