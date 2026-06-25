from __future__ import annotations

import textwrap
from pathlib import Path

from governance_tools.authority_metadata_consistency import (
    compare_authority_metadata,
    normalize_document_reference,
    parse_authority_table,
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def _authority(path: Path, rows: str) -> Path:
    return _write(path, f"""\
        # Governance Authority Table

        ## Authority Table

        | document | audience | authority | can_override | overridden_by | default_load |
        |----------|----------|-----------|--------------|---------------|--------------|
        {rows}

        ---
    """)


def _governance_doc(governance_dir: Path, name: str, frontmatter: str) -> Path:
    return _write(governance_dir / name, f"""\
        ---
        {frontmatter}
        ---

        # {name}
    """)


def test_normalize_document_reference_converts_backslashes() -> None:
    assert normalize_document_reference("`governance\\PLAN.md`") == "governance/PLAN.md"


def test_parse_authority_table_returns_repo_local_rows_and_skips_abstract_rows(tmp_path: Path) -> None:
    authority = _authority(tmp_path / "AUTHORITY.md", """\
        | `governance/PLAN.md` | agent-on-demand | reference | false | ../PLAN.md | on-demand |
        | `AGENTS.md` (workspace) | agent-runtime | derived | false | AGENT.md | always |
        | `governance/rules/*.md` | agent-on-demand | reference | false | ~ | on-demand |
        | `domain contract (full)` | agent-on-demand | canonical | false | ~ | on-demand |
    """)

    rows, skipped = parse_authority_table(authority)

    assert set(rows) == {"governance/PLAN.md"}
    assert rows["governance/PLAN.md"]["default_load"] == "on-demand"
    assert rows["governance/PLAN.md"]["overridden_by"] == "../PLAN.md"
    assert {item["reason"] for item in skipped} == {"non_governance_row", "glob_or_pattern_row"}


def test_compare_reports_field_mismatches(tmp_path: Path) -> None:
    governance_dir = tmp_path / "governance"
    authority = _authority(governance_dir / "AUTHORITY.md", """\
        | `governance/PLAN.md` | agent-runtime | canonical | false | ~ | always |
    """)
    _governance_doc(governance_dir, "PLAN.md", """\
        audience: agent-on-demand
        authority: reference
        can_override: false
        overridden_by: ../PLAN.md
        default_load: on-demand
    """)

    result = compare_authority_metadata(authority_path=authority, governance_dir=governance_dir)

    mismatches = {(item["field"], item["table"], item["frontmatter"]) for item in result["field_mismatches"]}
    assert ("audience", "agent-runtime", "agent-on-demand") in mismatches
    assert ("authority", "canonical", "reference") in mismatches
    assert ("overridden_by", None, "../PLAN.md") in mismatches
    assert ("default_load", "always", "on-demand") in mismatches
    assert result["ok"] is False


def test_compare_reports_missing_table_row(tmp_path: Path) -> None:
    governance_dir = tmp_path / "governance"
    authority = _authority(governance_dir / "AUTHORITY.md", "")
    _governance_doc(governance_dir, "AGENT.md", """\
        audience: agent-runtime
        authority: canonical
        can_override: false
        overridden_by: ~
        default_load: always
    """)

    result = compare_authority_metadata(authority_path=authority, governance_dir=governance_dir)

    assert result["missing_table_rows"] == [
        {"document": "governance/AGENT.md", "reason": "frontmatter_present_but_table_row_missing"}
    ]
    assert result["ok"] is False


def test_compare_reports_missing_frontmatter(tmp_path: Path) -> None:
    governance_dir = tmp_path / "governance"
    authority = _authority(governance_dir / "AUTHORITY.md", """\
        | `governance/MEMORY_PROTOCOL.md` | agent-runtime | canonical | false | AGENT.md | on-demand |
    """)
    _write(governance_dir / "MEMORY_PROTOCOL.md", "# no frontmatter\n")

    result = compare_authority_metadata(authority_path=authority, governance_dir=governance_dir)

    assert result["missing_frontmatter"] == [
        {
                "document": "governance/MEMORY_PROTOCOL.md",
                "reason": "table_row_present_but_frontmatter_missing",
                "line": 7,
            }
        ]
    assert result["ok"] is False


def test_compare_ok_when_table_matches_frontmatter(tmp_path: Path) -> None:
    governance_dir = tmp_path / "governance"
    authority = _authority(governance_dir / "AUTHORITY.md", """\
        | `governance/PLAN.md` | agent-on-demand | reference | false | ../PLAN.md | on-demand |
    """)
    _governance_doc(governance_dir, "PLAN.md", """\
        audience: agent-on-demand
        authority: reference
        can_override: false
        overridden_by: ../PLAN.md
        default_load: on-demand
    """)

    result = compare_authority_metadata(authority_path=authority, governance_dir=governance_dir)

    assert result["ok"] is True
    assert result["summary"]["field_mismatches"] == 0
    assert result["summary"]["missing_table_rows"] == 0
    assert result["summary"]["missing_frontmatter"] == 0
