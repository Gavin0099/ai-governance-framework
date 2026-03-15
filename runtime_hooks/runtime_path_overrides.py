#!/usr/bin/env python3
"""
Shared path-override helpers for runtime entrypoints.
"""

from __future__ import annotations

from pathlib import Path


def apply_runtime_path_overrides(
    payload: dict,
    *,
    project_root: Path | None = None,
    plan_path: Path | None = None,
    contract_file: Path | None = None,
) -> dict:
    updated = dict(payload)

    effective_contract = contract_file.resolve() if contract_file else None
    effective_project_root = project_root.resolve() if project_root else None
    effective_plan_path = plan_path.resolve() if plan_path else None

    if effective_project_root is None and effective_contract is not None:
        contract_project_root = effective_contract.parent
        contract_plan_path = contract_project_root / "PLAN.md"
        if contract_plan_path.exists():
            effective_project_root = contract_project_root

    if effective_plan_path is None and effective_project_root is not None:
        effective_plan_path = effective_project_root / "PLAN.md"

    if effective_project_root is not None:
        updated["project_root"] = str(effective_project_root)
    if effective_plan_path is not None:
        updated["plan_path"] = str(effective_plan_path)
    if effective_contract is not None:
        updated["contract"] = str(effective_contract)

    return updated
