#!/usr/bin/env python3
"""Machine-readable adoption truth: what each guard surface actually does.

Why this tool exists
--------------------
"Governance is fully adopted" was being claimed on the strength of files being
present and a tool running when invoked by hand. Those are two of six distinct
states, and the gap between them is where enforcement silently disappears:

  1. present              the tool exists in this checkout
  2. configured           something actually wires it into a runtime path
  3. invoked              it has really run, recently, leaving evidence
  4. covered              it provably examined the scope it claims to cover
  5. verdict_influencing  its findings are recorded into a verdict payload
  6. blocking             its findings can set a verdict to blocked

A surface at level 1 or 2 detects nothing in practice. Level 4 exists because a
guard pointed at an empty directory runs perfectly and sees nothing: executing
is not examining. This census reports the highest level each surface has
*evidence* for, names the first missing link, and refuses to emit any aggregate
"adopted" verdict.

Reported alongside, not as a rung: ``version_alignment``. A drifted checkout can
be fully wired and still enforce an older contract than the repo pinned, so it
caps what the census may be quoted for rather than lowering a level.

Claim ceiling
-------------
Reported levels are evidence of wiring, not of correctness. ``blocking`` means
a code is enabled in the blocking policy — not that the guard is right, that
its findings are useful, or that a bypass is impossible. Absence of evidence is
reported as absence of evidence, never as a passing state.

Read-only. Writes nothing, changes no policy, opens no gate.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # pragma: no cover - direct-script fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.memory_authority_guard import load_blocking_policy

CENSUS_VERSION = "0.1"
REGISTRY_RELPATH = "governance/guard_surface_registry.json"
REGISTRY_SCHEMA = "guard_surface_registry.v0.1"

LEVELS = (
    "present",
    "configured",
    "invoked",
    "covered",
    "verdict_influencing",
    "blocking",
)
LEVEL_NONE = "absent"

DEFAULT_MAX_AGE_DAYS = 30

# Coverage modes a surface may declare.
#   full_scan     — the surface reads an entire declared root every run, so
#                   coverage follows from invocation plus the root existing.
#   changed_paths — the surface only looks at what it was handed, so coverage
#                   can only be claimed if the run recorded the scope it saw.
COVERAGE_FULL_SCAN = "full_scan"
COVERAGE_CHANGED_PATHS = "changed_paths"

# What a repo may honestly say once the census has run. Deliberately has no
# "adopted" value: adoption is not a state this tool can certify.
_LEVEL_MEANING = {
    LEVEL_NONE: "surface file not found in this checkout",
    "present": "file exists; nothing is known to call it",
    "configured": "wired into a runtime path; no evidence it has run",
    "invoked": "has run and left evidence; what it examined is unproven",
    "covered": "provably examined its declared scope; findings reach no verdict",
    "verdict_influencing": "findings are recorded in verdicts; they block nothing",
    "blocking": "at least one finding code can set a verdict to blocked",
}


@dataclass
class LevelCheck:
    value: bool
    evidence: list[str] = field(default_factory=list)
    reason: str | None = None
    source_path: Path | None = None
    source_payload: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"value": self.value, "evidence": self.evidence, "reason": self.reason}


# ── registry ──────────────────────────────────────────────────────────────────

def load_registry(project_root: Path, registry_path: Path | None = None) -> dict[str, Any]:
    path = registry_path or (project_root / REGISTRY_RELPATH)
    if not path.is_file():
        return {"error": f"registry_not_found: {path}", "surfaces": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": f"registry_unreadable: {exc}", "surfaces": []}
    if not isinstance(payload, dict):
        return {"error": "registry_not_an_object", "surfaces": []}
    if payload.get("registry_schema") != REGISTRY_SCHEMA:
        return {"error": "registry_schema_mismatch", "surfaces": []}
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        return {"error": "registry_surfaces_invalid", "surfaces": []}
    return {"error": None, "surfaces": surfaces, "path": str(path)}


# ── level checks ──────────────────────────────────────────────────────────────

def _check_present(project_root: Path, surface: dict[str, Any]) -> LevelCheck:
    module = str(surface.get("module") or "").strip()
    if not module:
        return LevelCheck(False, reason="no_module_declared")
    path = project_root / module
    if path.is_file():
        return LevelCheck(True, evidence=[module])
    return LevelCheck(False, reason=f"module_missing:{module}")


def _check_configured(project_root: Path, surface: dict[str, Any]) -> LevelCheck:
    """A surface is configured when a declared wiring site really references it.

    The marker is searched in file text rather than imported, so a wiring site
    that is itself dead code still counts as configured — that gap is what the
    `invoked` level is for.
    """
    sites = surface.get("wiring_sites") or []
    if not sites:
        return LevelCheck(False, reason="no_wiring_sites_declared")
    evidence: list[str] = []
    missing: list[str] = []
    for site in sites:
        rel = str(site.get("path") or "").strip()
        marker = str(site.get("marker") or "").strip()
        if not rel or not marker:
            continue
        path = project_root / rel
        if not path.is_file():
            missing.append(f"{rel}:file_missing")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            missing.append(f"{rel}:unreadable:{exc}")
            continue
        if marker in text:
            evidence.append(f"{rel}:{marker}")
        else:
            missing.append(f"{rel}:marker_absent")
    if evidence:
        return LevelCheck(True, evidence=evidence)
    return LevelCheck(False, reason="; ".join(missing) or "no_wiring_site_matched")


def _iter_glob(project_root: Path, pattern: str) -> list[Path]:
    try:
        return sorted(
            path for path in project_root.glob(pattern) if path.is_file()
        )
    except (OSError, ValueError):
        return []


def _newest_matching(
    project_root: Path, spec: dict[str, Any], limit: int = 400
) -> tuple[Path, float, dict[str, Any] | None] | None:
    """Newest invocation satisfying one evidence spec.

    Parsed payload is retained so later levels stay bound to this exact
    invocation rather than finding a convenient field in stale evidence.
    """
    pattern = str(spec.get("glob") or "").strip()
    if not pattern:
        return None
    candidates = _iter_glob(project_root, pattern)
    if not candidates:
        return None
    # Newest first so a repo with thousands of receipts stops after a few reads.
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    json_key = spec.get("json_key")
    expect_true = bool(spec.get("expect_true"))
    is_ndjson = bool(spec.get("ndjson"))

    for path in candidates[:limit]:
        if not json_key and not is_ndjson:
            return path, path.stat().st_mtime, None
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if is_ndjson:
            for line in reversed(text.splitlines()):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                if isinstance(payload, dict):
                    return path, path.stat().st_mtime, payload
            continue
        try:
            payload = json.loads(text)
        except Exception:
            continue
        if not isinstance(payload, dict) or json_key not in payload:
            continue
        if expect_true and not payload.get(json_key):
            continue
        return path, path.stat().st_mtime, payload
    return None


def _check_invoked(
    project_root: Path, surface: dict[str, Any], *, max_age_days: int, now: float
) -> LevelCheck:
    specs = surface.get("invocation_evidence") or []
    if not specs:
        return LevelCheck(False, reason="no_invocation_evidence_declared")

    best: tuple[Path, float, dict[str, Any] | None] | None = None
    for spec in specs:
        found = _newest_matching(project_root, spec)
        if found and (best is None or found[1] > best[1]):
            best = found
    if best is None:
        return LevelCheck(False, reason="no_invocation_evidence_found")

    path, mtime, payload = best
    age_days = max(0.0, (now - mtime) / 86400.0)
    rel = path.relative_to(project_root).as_posix()
    evidence = [f"{rel} (age {age_days:.1f}d)"]
    if max_age_days > 0 and age_days > max_age_days:
        # Stale evidence proves it ran once, not that it runs now. Reporting it
        # as invoked is how a dead guard keeps looking alive.
        return LevelCheck(
            False,
            evidence=evidence,
            reason=f"invocation_evidence_stale:{age_days:.1f}d>{max_age_days}d",
        )
    return LevelCheck(
        True,
        evidence=evidence,
        source_path=path,
        source_payload=payload,
    )


def _check_covered(
    project_root: Path, surface: dict[str, Any], invoked: LevelCheck
) -> LevelCheck:
    """Did the run actually examine the scope this surface claims to cover?

    Invocation says the code executed. It says nothing about what the code
    looked at — a guard pointed at an empty directory runs perfectly and sees
    nothing. Only a declared coverage mode closes that gap.
    """
    if not invoked.value:
        return LevelCheck(False, reason="not_invoked")

    mode = str(surface.get("coverage_mode") or "").strip()
    if not mode:
        return LevelCheck(False, reason="no_coverage_mode_declared")

    if mode == COVERAGE_FULL_SCAN:
        roots = [str(item) for item in (surface.get("coverage_roots") or [])]
        if not roots:
            return LevelCheck(False, reason="full_scan_declared_without_coverage_roots")
        missing = [root for root in roots if not (project_root / root).exists()]
        if missing:
            return LevelCheck(
                False, reason=f"coverage_root_missing:{','.join(missing)}"
            )
        return LevelCheck(True, evidence=[f"full_scan:{','.join(roots)}"])

    if mode == COVERAGE_CHANGED_PATHS:
        key = str(surface.get("coverage_scope_key") or "").strip()
        if not key:
            return LevelCheck(
                False, reason="changed_paths_declared_without_coverage_scope_key"
            )
        payload = invoked.source_payload
        if payload is None:
            return LevelCheck(False, reason="invocation_payload_not_structured")
        if key not in payload:
            return LevelCheck(False, reason=f"examined_scope_not_recorded:{key}")
        scope = payload.get(key)
        if not isinstance(scope, list):
            return LevelCheck(False, reason=f"examined_scope_invalid_type:{key}")
        examined = [
            item.strip() for item in scope if isinstance(item, str) and item.strip()
        ]
        if len(examined) != len(scope) or not examined:
            return LevelCheck(False, reason=f"examined_scope_empty_or_invalid:{key}")
        if invoked.source_path is None:
            return LevelCheck(False, reason="invocation_source_path_missing")
        rel = invoked.source_path.relative_to(project_root).as_posix()
        return LevelCheck(True, evidence=[f"{rel}:{key}:{len(examined)}"])

    return LevelCheck(False, reason=f"unknown_coverage_mode:{mode}")


def _check_verdict_influencing(
    project_root: Path, surface: dict[str, Any], invoked: LevelCheck
) -> LevelCheck:
    """Do this surface's findings actually land in a verdict payload?

    Requires real invocation evidence containing the declared verdict fields.
    A surface can run and log to stdout without any of it reaching a verdict —
    that is the state this level exists to expose.
    """
    fields = surface.get("verdict_fields") or []
    if not fields:
        return LevelCheck(False, reason="no_verdict_fields_declared")
    if not invoked.value:
        return LevelCheck(False, reason="not_invoked")

    payload = invoked.source_payload
    if payload is None:
        return LevelCheck(False, reason="invocation_payload_not_structured")
    present = [name for name in fields if name in payload]
    if len(present) == len(fields) and invoked.source_path is not None:
        rel = invoked.source_path.relative_to(project_root).as_posix()
        return LevelCheck(True, evidence=[f"{rel}:{','.join(present)}"])
    return LevelCheck(False, reason="verdict_fields_absent_from_invocation_evidence")


def check_version_alignment(project_root: Path) -> dict[str, Any]:
    """Is the framework being executed the one the repo pinned?

    Version drift is orthogonal to the ladder: a drifted checkout can still be
    wired, invoked and blocking — it is simply enforcing an older contract than
    the repo believes. Reporting it as a lower rung would be a different lie,
    so it is reported alongside and caps what the census may be quoted for.

    This is the machine answer to "the submodule is N commits behind": it
    compares the pinned release and commit with the framework actually present,
    instead of inferring staleness from a commit count.
    """
    lock_path = project_root / "governance" / "framework.lock.json"
    if not lock_path.is_file():
        return {
            "status": "unknown",
            "reason": "framework_lock_absent",
            "lock_path": str(lock_path),
        }
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "unknown", "reason": f"framework_lock_unreadable: {exc}"}

    pinned_release = str(lock.get("adopted_release") or "").strip()
    pinned_commit = str(lock.get("adopted_commit") or "").strip().lower()

    try:
        from governance_tools.framework_versioning import current_framework_release

        actual_release = current_framework_release(project_root)
    except Exception as exc:  # pragma: no cover - defensive
        actual_release = None
        release_error = str(exc)
    else:
        release_error = None

    actual_commit = _git_head_commit(project_root)

    mismatches: list[str] = []
    direction = None
    if pinned_release and actual_release and pinned_release != actual_release:
        mismatches.append(f"release pinned={pinned_release} actual={actual_release}")
    if pinned_commit and actual_commit and not (
        actual_commit.startswith(pinned_commit) or pinned_commit.startswith(actual_commit)
    ):
        # Direction is what makes this actionable. A checkout *behind* its pin
        # is running governance the repo already decided to replace — the
        # "submodule is N commits behind" case, now provable rather than
        # inferred from a commit count. A checkout *ahead* is usually a lock
        # that was not refreshed, which is a bookkeeping problem, not a
        # governance one.
        direction = _pin_direction(project_root, pinned_commit, actual_commit)
        mismatches.append(
            f"commit pinned={pinned_commit[:12]} actual={actual_commit[:12]}"
            f" ({direction})"
        )

    # A pin that cannot be checked must never read as aligned. Reporting
    # "aligned" for an unverifiable pin is the same false assurance as
    # reporting a guard nobody runs as blocking.
    unverifiable: list[str] = []
    if pinned_release and not actual_release:
        unverifiable.append("executing_release_undetermined")
    if pinned_commit and not actual_commit:
        unverifiable.append("executing_commit_undetermined")
    if not pinned_release and not pinned_commit:
        unverifiable.append("lock_records_no_release_or_commit")

    if release_error or unverifiable:
        return {
            "status": "unknown",
            "reason": release_error or ",".join(unverifiable),
            "pinned_release": pinned_release,
            "pinned_commit": pinned_commit,
            "actual_release": actual_release,
            "actual_commit": actual_commit,
        }

    return {
        "status": "drifted" if mismatches else "aligned",
        "direction": direction,
        "pinned_release": pinned_release,
        "pinned_commit": pinned_commit,
        "actual_release": actual_release,
        "actual_commit": actual_commit,
        "mismatches": mismatches,
    }


def _pin_direction(project_root: Path, pinned: str, actual: str) -> str:
    """behind_pin / ahead_of_pin / diverged / unknown."""
    def is_ancestor(older: str, newer: str) -> bool | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(project_root), "merge-base", "--is-ancestor",
                 older, newer],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except Exception:
            return None
        if completed.returncode == 0:
            return True
        if completed.returncode == 1:
            return False
        return None  # unknown commit, shallow clone, not a repo

    pinned_is_ancestor = is_ancestor(pinned, actual)
    if pinned_is_ancestor is None:
        return "unknown"
    if pinned_is_ancestor:
        return "ahead_of_pin"
    return "behind_pin" if is_ancestor(actual, pinned) else "diverged"


def _git_head_commit(project_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or "").strip().lower() or None


def _check_blocking(surface: dict[str, Any], enabled_codes: list[str]) -> LevelCheck:
    codes = [str(code) for code in (surface.get("emitted_codes") or [])]
    if not codes:
        return LevelCheck(False, reason="no_emitted_codes_declared")
    enabled = sorted(set(codes) & set(enabled_codes))
    if enabled:
        return LevelCheck(True, evidence=enabled)
    return LevelCheck(False, reason="no_emitted_code_enabled_in_blocking_policy")


# ── assembly ──────────────────────────────────────────────────────────────────

def assess_surface(
    project_root: Path,
    surface: dict[str, Any],
    *,
    enabled_codes: list[str],
    max_age_days: int,
    now: float,
) -> dict[str, Any]:
    present = _check_present(project_root, surface)
    configured = _check_configured(project_root, surface) if present.value else LevelCheck(
        False, reason="not_present"
    )
    invoked = (
        _check_invoked(project_root, surface, max_age_days=max_age_days, now=now)
        if configured.value
        else LevelCheck(False, reason="not_configured")
    )
    covered = _check_covered(project_root, surface, invoked)
    verdict = _check_verdict_influencing(project_root, surface, invoked)
    blocking = _check_blocking(surface, enabled_codes)

    checks = {
        "present": present,
        "configured": configured,
        "invoked": invoked,
        "covered": covered,
        "verdict_influencing": verdict,
        "blocking": blocking,
    }

    # The level is the longest unbroken prefix that holds. A surface whose codes
    # are policy-enabled but which nothing invokes is NOT blocking anything, and
    # reporting it as such would recreate the exact illusion this tool exists to
    # remove.
    level = LEVEL_NONE
    for name in LEVELS:
        if not checks[name].value:
            break
        level = name

    first_gap = next((name for name in LEVELS if not checks[name].value), None)

    return {
        "id": surface.get("id"),
        "title": surface.get("title"),
        "module": surface.get("module"),
        "level": level,
        "level_meaning": _LEVEL_MEANING[level],
        "first_gap": first_gap,
        "first_gap_reason": checks[first_gap].reason if first_gap else None,
        "checks": {name: check.as_dict() for name, check in checks.items()},
    }


def run_census(
    project_root: Path,
    *,
    registry_path: Path | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    now: float | None = None,
) -> dict[str, Any]:
    registry = load_registry(project_root, registry_path)
    policy = load_blocking_policy(project_root)
    enabled_codes = [str(code) for code in policy.get("enabled_codes", [])]
    timestamp = now if now is not None else datetime.now(timezone.utc).timestamp()

    surfaces = [
        assess_surface(
            project_root,
            surface,
            enabled_codes=enabled_codes,
            max_age_days=max_age_days,
            now=timestamp,
        )
        for surface in registry.get("surfaces", [])
    ]

    by_level: dict[str, int] = {name: 0 for name in (LEVEL_NONE, *LEVELS)}
    for entry in surfaces:
        by_level[entry["level"]] += 1

    version_alignment = check_version_alignment(project_root)

    return {
        "tool": "guard_enforcement_census",
        "version": CENSUS_VERSION,
        "generated_at": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
        "project_root": str(project_root),
        "registry_path": registry.get("path"),
        "registry_error": registry.get("error"),
        "max_age_days": max_age_days,
        "blocking_policy": {
            "source": policy.get("source"),
            "enabled_codes": enabled_codes,
            "error": policy.get("error"),
        },
        "surface_count": len(surfaces),
        "surfaces_by_level": by_level,
        "surfaces": surfaces,
        # Orthogonal to the ladder: a drifted checkout can be fully wired and
        # still be enforcing an older contract than the repo believes.
        "version_alignment": version_alignment,
        "claim_ceiling": [
            "levels report wiring evidence, not guard correctness",
            "a surface below 'blocking' cannot stop any commit, push, or closeout",
            "this tool never certifies that governance is adopted",
        ]
        + (
            [
                "version drift detected: reported levels describe the framework "
                "actually present, not the one this repo pinned"
            ]
            if version_alignment.get("status") == "drifted"
            else []
        ),
        "not_claimed": [
            "guard findings are correct",
            "guard coverage is sufficient",
            "enforcement cannot be bypassed",
        ],
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _human(result: dict[str, Any]) -> str:
    lines = [
        f"[guard_enforcement_census] v{result['version']} "
        f"surfaces={result['surface_count']}",
    ]
    if result.get("registry_error"):
        lines.append(f"  registry_error: {result['registry_error']}")
    for entry in result["surfaces"]:
        lines.append(f"  {entry['id']}: {entry['level']} — {entry['level_meaning']}")
        if entry["first_gap"]:
            lines.append(
                f"      first gap: {entry['first_gap']} ({entry['first_gap_reason']})"
            )
    counts = ", ".join(
        f"{name}={count}" for name, count in result["surfaces_by_level"].items() if count
    )
    lines.append(f"  distribution: {counts}")
    alignment = result.get("version_alignment") or {}
    detail = "; ".join(alignment.get("mismatches") or []) or alignment.get("reason") or ""
    lines.append(
        f"  version_alignment: {alignment.get('status')}"
        + (f" ({detail})" if detail else "")
    )
    lines.append("  claim ceiling: " + result["claim_ceiling"][2])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report the adoption level of each registered guard surface."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--registry")
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help="Invocation evidence older than this counts as stale (0 disables).",
    )
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument(
        "--require-level",
        choices=LEVELS,
        help=(
            "Exit non-zero when any registered surface is below this level. "
            "Off by default: the census is a report, not a gate."
        ),
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    result = run_census(
        project_root,
        registry_path=Path(args.registry).resolve() if args.registry else None,
        max_age_days=args.max_age_days,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_human(result))

    if args.require_level:
        threshold = LEVELS.index(args.require_level)
        below = [
            entry["id"]
            for entry in result["surfaces"]
            if entry["level"] == LEVEL_NONE
            or LEVELS.index(entry["level"]) < threshold
        ]
        if below:
            print(
                f"below_required_level({args.require_level}): {', '.join(below)}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
