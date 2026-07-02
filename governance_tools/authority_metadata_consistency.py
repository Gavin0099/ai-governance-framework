#!/usr/bin/env python3
"""Report drift between AUTHORITY.md table rows and governance doc frontmatter.

This checker is diagnostic-only. It reads the human-facing AUTHORITY table and
the live authority metadata parsed from governance/*.md frontmatter, then reports
missing rows, missing frontmatter, and semantic field mismatches.

It does not mutate files and does not enforce hook/CI/pre-push behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from governance_tools.authority_loader import parse_frontmatter


SEMANTIC_FIELDS = (
    "audience",
    "authority",
    "can_override",
    "overridden_by",
    "default_load",
)

STRUCTURAL_EXCLUDED_GOVERNANCE_DOCS = frozenset({
    "AUTHORITY.md",
    "copilot-instructions-template.md",
})


def normalize_document_reference(document: str) -> str:
    """Normalize a table document cell into a slash-separated repo reference."""
    return document.strip().strip("`").replace("\\", "/")


def _table_value(value: str) -> Any:
    value = value.strip()
    if value in ("~", "null", "None", ""):
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def _frontmatter_value(meta: dict[str, Any], field: str) -> Any:
    if field == "audience":
        return meta.get("audience", "agent-on-demand")
    if field == "authority":
        return meta.get("authority", "reference")
    if field == "can_override":
        return meta.get("can_override", False)
    if field == "overridden_by":
        return meta.get("overridden_by")
    if field == "default_load":
        return meta.get("default_load", "on-demand")
    raise KeyError(field)


def is_glob_like(document: str) -> bool:
    return any(marker in document for marker in ("*", "?", "[", "]"))


def is_repo_local_governance_doc(document: str) -> bool:
    return document.startswith("governance/") and not is_glob_like(document)


def parse_authority_table(authority_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    """Parse repo-local governance rows from AUTHORITY.md.

    Returns:
        (rows_by_document, skipped_rows)
    """
    rows: dict[str, dict[str, Any]] = {}
    skipped: list[dict[str, str]] = []
    in_table = False

    try:
        lines = authority_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {}, [{"document": str(authority_path), "reason": f"authority_read_error:{exc}"}]

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == "## Authority Table":
            in_table = True
            continue
        if in_table and stripped == "---":
            break
        if not in_table:
            continue
        if not stripped.startswith("|"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6:
            continue
        if cells[0] in ("document", "----------"):
            continue
        if not cells[0].startswith("`"):
            continue

        document = normalize_document_reference(cells[0].split("`", maxsplit=2)[1])
        if is_glob_like(document):
            skipped.append({"document": document, "reason": "glob_or_pattern_row", "line": str(line_no)})
            continue
        if not document.startswith("governance/"):
            skipped.append({"document": document, "reason": "non_governance_row", "line": str(line_no)})
            continue

        rows[document] = {
            "document": document,
            "line": line_no,
            "audience": _table_value(cells[1]),
            "authority": _table_value(cells[2]),
            "can_override": _table_value(cells[3]),
            "overridden_by": _table_value(cells[4]),
            "default_load": _table_value(cells[5]),
        }

    return rows, skipped


def load_frontmatter_rows(governance_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not governance_dir.is_dir():
        return rows

    for md_file in sorted(governance_dir.glob("*.md")):
        meta = parse_frontmatter(md_file)
        if not meta:
            continue
        document = f"governance/{md_file.name}"
        rows[document] = {
            "document": document,
            "path": str(md_file),
            **{field: _frontmatter_value(meta, field) for field in SEMANTIC_FIELDS},
        }
    return rows


def load_unregistered_documents(
    *,
    governance_dir: Path,
    table_rows: dict[str, dict[str, Any]],
    frontmatter_rows: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Report governance docs invisible to both AUTHORITY.md and frontmatter.

    This is a warning surface only. Some markdown files under governance/ are
    structural artifacts rather than authority documents; those are excluded by
    filename rather than by a second hand-maintained authority registry.
    """
    if not governance_dir.is_dir():
        return []

    registered = set(table_rows) | set(frontmatter_rows)
    unregistered: list[dict[str, str]] = []
    for md_file in sorted(governance_dir.glob("*.md")):
        if md_file.name in STRUCTURAL_EXCLUDED_GOVERNANCE_DOCS:
            continue
        document = f"governance/{md_file.name}"
        if document in registered:
            continue
        unregistered.append({
            "document": document,
            "reason": "governance_doc_without_frontmatter_or_authority_row",
        })
    return unregistered


def compare_authority_metadata(
    *,
    authority_path: Path,
    governance_dir: Path,
) -> dict[str, Any]:
    table_rows, skipped_rows = parse_authority_table(authority_path)
    frontmatter_rows = load_frontmatter_rows(governance_dir)
    unregistered_documents = load_unregistered_documents(
        governance_dir=governance_dir,
        table_rows=table_rows,
        frontmatter_rows=frontmatter_rows,
    )

    missing_table_rows = [
        {"document": document, "reason": "frontmatter_present_but_table_row_missing"}
        for document in sorted(set(frontmatter_rows) - set(table_rows))
    ]
    missing_frontmatter = [
        {"document": document, "reason": "table_row_present_but_frontmatter_missing", "line": row["line"]}
        for document, row in sorted(table_rows.items())
        if document not in frontmatter_rows
    ]

    field_mismatches: list[dict[str, Any]] = []
    for document in sorted(set(table_rows) & set(frontmatter_rows)):
        table_row = table_rows[document]
        frontmatter_row = frontmatter_rows[document]
        for field in SEMANTIC_FIELDS:
            table_value = table_row.get(field)
            frontmatter_value = frontmatter_row.get(field)
            if table_value != frontmatter_value:
                field_mismatches.append({
                    "document": document,
                    "field": field,
                    "table": table_value,
                    "frontmatter": frontmatter_value,
                    "line": table_row["line"],
                })

    ok = not missing_table_rows and not missing_frontmatter and not field_mismatches
    return {
        "ok": ok,
        "mode": "report_only",
        "authority_path": str(authority_path),
        "governance_dir": str(governance_dir),
        "summary": {
            "table_repo_local_rows": len(table_rows),
            "frontmatter_rows": len(frontmatter_rows),
            "missing_table_rows": len(missing_table_rows),
            "missing_frontmatter": len(missing_frontmatter),
            "field_mismatches": len(field_mismatches),
            "unregistered_documents": len(unregistered_documents),
            "skipped_rows": len(skipped_rows),
        },
        "missing_table_rows": missing_table_rows,
        "missing_frontmatter": missing_frontmatter,
        "field_mismatches": field_mismatches,
        "unregistered_documents": unregistered_documents,
        "warning_codes": (
            ["unregistered_governance_documents"]
            if unregistered_documents
            else []
        ),
        "skipped_rows": skipped_rows,
        "claim_ceiling_not_supported": [
            "does_not_change_authority_metadata",
            "does_not_change_session_start_behavior",
            "does_not_install_hook_or_ci_enforcement",
            "does_not_prove_prompt_text_injection",
            "does_not_repair_governance_document_freshness",
            "does_not_make_unregistered_document_warnings_blocking",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report AUTHORITY.md table versus governance/*.md frontmatter drift."
    )
    parser.add_argument("--authority", default="governance/AUTHORITY.md")
    parser.add_argument("--governance-dir", default="governance")
    parser.add_argument("--format", choices=["json"], default="json")
    args = parser.parse_args()

    result = compare_authority_metadata(
        authority_path=Path(args.authority),
        governance_dir=Path(args.governance_dir),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
