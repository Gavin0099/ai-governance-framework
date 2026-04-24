#!/usr/bin/env python3
"""Machine-readable runtime phase execution policy helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_RUNTIME_PHASE_POLICY_PATH = Path("governance/runtime/runtime_phase_policy.yaml")
PHASE_ORDER = (
    "sync_gate",
    "sync_advisory",
    "async_closeout",
    "async_audit",
    "manual_review_only",
)


def load_runtime_phase_policy(*, framework_root: Path | None = None) -> dict[str, Any]:
    root = framework_root or Path(__file__).resolve().parent.parent
    path = root / DEFAULT_RUNTIME_PHASE_POLICY_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"runtime phase policy must be a mapping: {path}")
    return data


def build_phase_classification(
    *,
    action_ids: list[str],
    hook: str,
    framework_root: Path | None = None,
) -> dict[str, Any]:
    policy = load_runtime_phase_policy(framework_root=framework_root)
    actions = policy.get("actions") or {}
    phase_summary = {phase: [] for phase in PHASE_ORDER}
    unknown_actions: list[str] = []
    entries: list[dict[str, Any]] = []

    for action_id in action_ids:
        action = str(action_id).strip()
        if not action:
            continue
        spec = actions.get(action)
        if not isinstance(spec, dict):
            unknown_actions.append(action)
            continue
        phase = str(spec.get("phase", "")).strip()
        if phase not in phase_summary:
            unknown_actions.append(action)
            continue
        phase_summary[phase].append(action)
        entries.append(
            {
                "action": action,
                "phase": phase,
                "owner": spec.get("owner"),
                "description": spec.get("description"),
            }
        )

    compact_summary = {phase: values for phase, values in phase_summary.items() if values}
    return {
        "schema_version": policy.get("schema_version"),
        "hook": hook,
        "actions": entries,
        "phase_summary": compact_summary,
        "rules": policy.get("rules") or {},
        "unknown_actions": unknown_actions,
    }


def aggregate_phase_classifications(
    *,
    phase_classifications: dict[str, dict[str, Any]],
    framework_root: Path | None = None,
) -> dict[str, Any]:
    policy = load_runtime_phase_policy(framework_root=framework_root)
    aggregated = {phase: [] for phase in PHASE_ORDER}

    for _, payload in phase_classifications.items():
        if not isinstance(payload, dict):
            continue
        for phase, actions in (payload.get("phase_summary") or {}).items():
            if phase not in aggregated:
                continue
            for action in actions:
                if action not in aggregated[phase]:
                    aggregated[phase].append(action)

    return {
        "schema_version": policy.get("schema_version"),
        "phase_classifications": phase_classifications,
        "phase_summary": {phase: values for phase, values in aggregated.items() if values},
        "rules": policy.get("rules") or {},
    }
