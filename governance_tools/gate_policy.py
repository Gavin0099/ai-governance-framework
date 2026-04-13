#!/usr/bin/env python3
"""
gate_policy.py — load and evaluate the test-result gate policy.

The policy authorises (or withholds authorisation for) session closeout
based on the failure_disposition in the test-result artifact.

Policy source: governance/gate_policy.yaml

Three concerns are handled here and nowhere else:

  1. Artifact state classification
       absent    — file does not exist
       malformed — file exists but is not valid JSON or missing expected keys
       stale     — file exists and is valid but its mtime exceeds the
                   artifact_stale_seconds threshold in the policy
       ok        — file is valid and fresh

  2. Gate evaluation
       Given a failure_disposition dict and the loaded policy, decide whether
       to block and produce a list of gate errors / warnings.

  3. Fail-mode enforcement
       strict     — absent/malformed are gate errors; stale is a warning
       permissive — all anomalous states are silently skipped
       audit      — anomalous states become warnings, gate is never triggered
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# ── Constants ─────────────────────────────────────────────────────────────────

FAIL_MODE_STRICT = "strict"
FAIL_MODE_PERMISSIVE = "permissive"
FAIL_MODE_AUDIT = "audit"

ARTIFACT_STATE_ABSENT = "absent"
ARTIFACT_STATE_MALFORMED = "malformed"
ARTIFACT_STATE_STALE = "stale"
ARTIFACT_STATE_OK = "ok"

_DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "governance" / "gate_policy.yaml"
)

_DEFAULTS: dict[str, Any] = {
    "version": "1",
    "fail_mode": FAIL_MODE_STRICT,
    "blocking_actions": ["production_fix_required"],
    "unknown_treatment": {"mode": "block_if_count_exceeds", "threshold": 3},
    "artifact_stale_seconds": 86400,
}


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class GatePolicy:
    fail_mode: str
    blocking_actions: list[str]
    unknown_treatment_mode: str
    unknown_treatment_threshold: int
    artifact_stale_seconds: int
    source: str = "defaults"


@dataclass
class ArtifactResult:
    """Result of reading and classifying the test-result artifact."""
    state: str                              # absent | malformed | stale | ok
    failure_disposition: dict | None = None
    stale_seconds: float | None = None     # age when state=stale
    load_error: str | None = None          # message when state=malformed


@dataclass
class GateDecision:
    """
    The final gate verdict produced by evaluate_gate().

    blocked     — True if the gate decided to block session closeout
    errors      — messages that must surface as result["errors"]
    warnings    — messages that must surface as result["warnings"]
    artifact_state — the classified state of the artifact
    """
    blocked: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    artifact_state: str = ARTIFACT_STATE_ABSENT


# ── Policy loading ────────────────────────────────────────────────────────────

def load_policy(path: Path | None = None) -> GatePolicy:
    """
    Load gate_policy.yaml.  Falls back to hardcoded defaults on any read/parse
    error so the session-end hook can always run.  The source field records
    whether defaults were used.
    """
    target = path or _DEFAULT_POLICY_PATH
    raw: dict[str, Any] = dict(_DEFAULTS)

    if target.exists():
        if not _HAS_YAML:
            # yaml not installed — use defaults, record it
            return _build_policy(raw, source=f"defaults (yaml unavailable, checked {target})")
        try:
            loaded = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
            raw.update({k: v for k, v in loaded.items() if v is not None})
            source = str(target)
        except Exception as exc:
            source = f"defaults (load error: {exc})"
    else:
        source = f"defaults (policy file not found: {target})"

    return _build_policy(raw, source=source)


def _build_policy(raw: dict[str, Any], source: str) -> GatePolicy:
    ut = raw.get("unknown_treatment") or {}
    if isinstance(ut, str):
        # allow shorthand: unknown_treatment: never_block
        ut = {"mode": ut, "threshold": 0}
    return GatePolicy(
        fail_mode=str(raw.get("fail_mode", FAIL_MODE_STRICT)),
        blocking_actions=list(raw.get("blocking_actions", ["production_fix_required"])),
        unknown_treatment_mode=str(ut.get("mode", "block_if_count_exceeds")),
        unknown_treatment_threshold=int(ut.get("threshold", 3)),
        artifact_stale_seconds=int(raw.get("artifact_stale_seconds", 86400)),
        source=source,
    )


# ── Artifact state classification ─────────────────────────────────────────────

def classify_artifact(
    artifact_path: Path,
    policy: GatePolicy,
) -> ArtifactResult:
    """
    Classify the test-result artifact into one of four states.

    absent    — path does not exist
    malformed — path exists but JSON is invalid or failure_disposition key absent
    stale     — JSON is valid but file is older than policy.artifact_stale_seconds
    ok        — valid and fresh
    """
    if not artifact_path.exists():
        return ArtifactResult(state=ARTIFACT_STATE_ABSENT)

    # Load JSON
    try:
        text = artifact_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as exc:
        return ArtifactResult(state=ARTIFACT_STATE_MALFORMED, load_error=str(exc))

    if not isinstance(data, dict):
        return ArtifactResult(
            state=ARTIFACT_STATE_MALFORMED,
            load_error="artifact root is not a JSON object",
        )

    # Stale check (only when stale detection is enabled)
    if policy.artifact_stale_seconds > 0:
        try:
            age = time.time() - artifact_path.stat().st_mtime
            if age > policy.artifact_stale_seconds:
                # Still load disposition so stale-but-valid artifacts can
                # contribute classification data for audit mode.
                return ArtifactResult(
                    state=ARTIFACT_STATE_STALE,
                    failure_disposition=data.get("failure_disposition"),
                    stale_seconds=age,
                )
        except OSError:
            pass  # stat failed — treat as ok, ignore stale check

    return ArtifactResult(
        state=ARTIFACT_STATE_OK,
        failure_disposition=data.get("failure_disposition"),
    )


# ── Gate evaluation ───────────────────────────────────────────────────────────

def evaluate_gate(
    artifact_result: ArtifactResult,
    policy: GatePolicy,
) -> GateDecision:
    """
    Apply the gate policy to an ArtifactResult and return a GateDecision.

    fail_mode determines how non-ok artifact states are handled.
    The gate is only ever triggered (blocked=True) in strict or permissive
    modes with a valid disposition — audit mode never blocks.
    """
    state = artifact_result.state

    # ── Audit mode: never block, only record ──────────────────────────────────
    if policy.fail_mode == FAIL_MODE_AUDIT:
        warnings: list[str] = []
        if state == ARTIFACT_STATE_ABSENT:
            warnings.append(
                "[gate_policy:audit] test-result artifact absent — gate skipped"
            )
        elif state == ARTIFACT_STATE_MALFORMED:
            warnings.append(
                f"[gate_policy:audit] test-result artifact malformed "
                f"({artifact_result.load_error}) — gate skipped"
            )
        elif state == ARTIFACT_STATE_STALE:
            warnings.append(
                f"[gate_policy:audit] test-result artifact stale "
                f"({artifact_result.stale_seconds:.0f}s old) — gate skipped"
            )
        # Even in audit mode, surface disposition advisory warnings
        if artifact_result.failure_disposition:
            _add_advisory_warnings(artifact_result.failure_disposition, policy, warnings)
        return GateDecision(blocked=False, warnings=warnings, artifact_state=state)

    # ── Strict: absent and malformed are errors ───────────────────────────────
    if policy.fail_mode == FAIL_MODE_STRICT:
        if state == ARTIFACT_STATE_ABSENT:
            return GateDecision(
                blocked=True,
                errors=[
                    "[gate_policy:strict] test-result artifact absent — "
                    "run test_result_ingestor --out artifacts/runtime/test-results/latest.json "
                    "before session closeout"
                ],
                artifact_state=state,
            )
        if state == ARTIFACT_STATE_MALFORMED:
            return GateDecision(
                blocked=True,
                errors=[
                    f"[gate_policy:strict] test-result artifact malformed "
                    f"({artifact_result.load_error}) — cannot evaluate gate"
                ],
                artifact_state=state,
            )
        if state == ARTIFACT_STATE_STALE:
            # Stale in strict: warn but still evaluate the gate
            stale_warning = (
                f"[gate_policy:strict] test-result artifact is stale "
                f"({artifact_result.stale_seconds:.0f}s > "
                f"{policy.artifact_stale_seconds}s threshold) — "
                f"gate applied using stale data"
            )
            decision = _evaluate_disposition(artifact_result.failure_disposition, policy, state)
            decision.warnings.insert(0, stale_warning)
            return decision

    # ── Permissive: absent / malformed / stale all skip silently ─────────────
    if policy.fail_mode == FAIL_MODE_PERMISSIVE:
        if state in (ARTIFACT_STATE_ABSENT, ARTIFACT_STATE_MALFORMED, ARTIFACT_STATE_STALE):
            return GateDecision(blocked=False, artifact_state=state)

    # ── ok (or permissive with ok): evaluate disposition ─────────────────────
    return _evaluate_disposition(artifact_result.failure_disposition, policy, state)


def _evaluate_disposition(
    disp: dict | None,
    policy: GatePolicy,
    artifact_state: str,
) -> GateDecision:
    """
    Given a (possibly None) failure_disposition dict and the policy, produce
    a GateDecision based on blocking_actions and unknown_treatment.
    """
    if not disp:
        # No disposition = no failures, or ingestor returned None.
        return GateDecision(blocked=False, artifact_state=artifact_state)

    errors: list[str] = []
    warnings: list[str] = []
    blocked = False

    by_action = disp.get("by_action") or {}

    # Blocking actions
    for action in policy.blocking_actions:
        count = by_action.get(action, 0)
        if count > 0:
            blocked = True
            errors.append(
                f"[GATE:{action}] {count} test failure(s) classified as "
                f"{action} — production code must be fixed before session can close"
            )

    # Unknown treatment
    unknown_count = disp.get("unknown_count", 0)
    mode = policy.unknown_treatment_mode
    threshold = policy.unknown_treatment_threshold

    if mode == "always_block" and unknown_count > 0:
        blocked = True
        errors.append(
            f"[GATE:unknown] {unknown_count} unclassified failure(s) — "
            f"policy=always_block requires resolution before closeout"
        )
    elif mode == "block_if_count_exceeds" and unknown_count > threshold:
        blocked = True
        errors.append(
            f"[GATE:unknown] {unknown_count} unclassified failure(s) exceeds threshold "
            f"({threshold}) — taxonomy must be expanded before closeout"
        )
    elif unknown_count > 0:
        warnings.append(
            f"[gate_policy] {unknown_count} unclassified failure(s) — "
            f"consider expanding taxonomy (unknown_treatment={mode})"
        )

    # Advisory warnings regardless of block status
    _add_advisory_warnings(disp, policy, warnings)

    return GateDecision(blocked=blocked, errors=errors, warnings=warnings, artifact_state=artifact_state)


def _add_advisory_warnings(disp: dict, policy: GatePolicy, warnings: list[str]) -> None:
    """Append non-blocking advisory notices from disposition to warnings list."""
    if disp.get("taxonomy_expansion_signal"):
        uc = disp.get("unknown_count", 0)
        if not any("taxonomy_expansion_signal" in w for w in warnings):
            warnings.append(
                f"[gate_policy:signal] taxonomy_expansion_signal: "
                f"{uc} unknown failures >= escalation threshold"
            )
