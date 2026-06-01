#!/usr/bin/env python3
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GuardFinding:
    file: str
    code: str
    detail: str


def _parse_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imported = f"{module}.{alias.name}" if module else alias.name
                imports.add(imported)
    return imports


def _is_consumer_module(path: Path) -> bool:
    return path.name.startswith("copilot_billing_") and path.name.endswith(("_summary.py", "_dashboard.py", "_ui.py"))


def run_consumer_bypass_guard(phase2_dir: Path) -> list[GuardFinding]:
    findings: list[GuardFinding] = []
    for file in sorted(phase2_dir.glob("copilot_billing_*.py")):
        if not _is_consumer_module(file):
            continue
        imports = _parse_imports(file)

        # summary/ui/dashboard consumers must not import ingestor directly.
        if (
            "codeburn.phase2.copilot_billing_ingestor" in imports
            or "codeburn.phase2.copilot_billing_ingestor.ingest_copilot_csv" in imports
            or "_ensure_db" in imports
        ):
            findings.append(
                GuardFinding(
                    file=str(file),
                    code="CONSUMER_IMPORTS_INGESTOR",
                    detail="consumer imports copilot_billing_ingestor directly",
                )
            )

        # summary consumer must be contract-bound to report layer.
        if file.name == "copilot_billing_summary.py":
            if "codeburn.phase2.copilot_billing_report.build_copilot_billing_report" not in imports:
                findings.append(
                    GuardFinding(
                        file=str(file),
                        code="SUMMARY_MISSING_REPORT_DEPENDENCY",
                        detail="summary does not import report builder",
                    )
                )

    return findings


def validate_consumer_bypass_guard(phase2_dir: Path) -> dict:
    findings = run_consumer_bypass_guard(phase2_dir)
    return {
        "ok": len(findings) == 0,
        "finding_count": len(findings),
        "findings": [f.__dict__ for f in findings],
    }

