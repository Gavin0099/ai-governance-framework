"""
Tests for governance_tools/authority_loader.py

Coverage:
- parse_frontmatter: valid, missing, malformed
- load_authority_table: real governance/ dir, empty dir, no-frontmatter files
- filter_for_session: L0 (always only), L1/L2 (always + on-demand), human-only exclusion
- get_human_only_files: correct extraction
- resolve_conflict: authority priority (canonical > reference > derived)
- validate_session_payload: ok + violation cases
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from governance_tools.authority_loader import (
    filter_for_session,
    get_human_only_files,
    load_authority_table,
    parse_frontmatter,
    resolve_conflict,
    validate_session_payload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


def _make_entry(
    filename: str = "test.md",
    audience: str = "agent-runtime",
    authority: str = "canonical",
    default_load: str = "always",
) -> dict:
    return {
        "file": f"governance/{filename}",
        "filename": filename,
        "audience": audience,
        "authority": authority,
        "can_override": False,
        "overridden_by": None,
        "default_load": default_load,
    }


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        f = _write(tmp_path, "doc.md", """\
            ---
            audience: agent-runtime
            authority: canonical
            can_override: false
            overridden_by: ~
            default_load: always
            ---
            # Title
        """)
        meta = parse_frontmatter(f)
        assert meta["audience"] == "agent-runtime"
        assert meta["authority"] == "canonical"
        assert meta["can_override"] is False
        assert meta["overridden_by"] is None
        assert meta["default_load"] == "always"

    def test_no_frontmatter(self, tmp_path):
        f = _write(tmp_path, "doc.md", "# Just a title\nNo frontmatter here.\n")
        assert parse_frontmatter(f) == {}

    def test_missing_closing_marker(self, tmp_path):
        f = _write(tmp_path, "doc.md", "---\naudience: agent-runtime\n# no closing marker")
        assert parse_frontmatter(f) == {}

    def test_overridden_by_tilde_is_none(self, tmp_path):
        f = _write(tmp_path, "doc.md", "---\noverridden_by: ~\n---\n# Title\n")
        meta = parse_frontmatter(f)
        assert meta["overridden_by"] is None

    def test_boolean_false(self, tmp_path):
        f = _write(tmp_path, "doc.md", "---\ncan_override: false\n---\n")
        meta = parse_frontmatter(f)
        assert meta["can_override"] is False

    def test_boolean_true(self, tmp_path):
        f = _write(tmp_path, "doc.md", "---\ncan_override: true\n---\n")
        meta = parse_frontmatter(f)
        assert meta["can_override"] is True

    def test_nonexistent_file(self, tmp_path):
        result = parse_frontmatter(tmp_path / "missing.md")
        assert result == {}


# ---------------------------------------------------------------------------
# load_authority_table
# ---------------------------------------------------------------------------

class TestLoadAuthorityTable:
    def test_loads_real_governance_dir(self):
        """Integration: real governance/ should have at least 8 files with frontmatter."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        # 8 governance docs + AUTHORITY.md (9 total)
        assert len(table) >= 8, f"Expected ≥8 entries, got {len(table)}: {[e['filename'] for e in table]}"

    def test_skips_files_without_frontmatter(self, tmp_path):
        _write(tmp_path, "with_fm.md", "---\naudience: agent-runtime\nauthority: canonical\ndefault_load: always\n---\n# Doc\n")
        _write(tmp_path, "no_fm.md", "# No frontmatter\n")
        table = load_authority_table(tmp_path)
        names = [e["filename"] for e in table]
        assert "with_fm.md" in names
        assert "no_fm.md" not in names

    def test_empty_directory(self, tmp_path):
        assert load_authority_table(tmp_path) == []

    def test_nonexistent_directory(self, tmp_path):
        assert load_authority_table(tmp_path / "does_not_exist") == []

    def test_entry_has_required_keys(self, tmp_path):
        _write(tmp_path, "doc.md", "---\naudience: agent-runtime\nauthority: canonical\ndefault_load: always\n---\n")
        table = load_authority_table(tmp_path)
        assert len(table) == 1
        entry = table[0]
        for key in ("file", "filename", "audience", "authority", "can_override", "overridden_by", "default_load"):
            assert key in entry, f"Missing key: {key}"

    def test_real_human_only_files_present(self):
        """HUMAN-OVERSIGHT.md and REVIEW_CRITERIA.md must be human-only."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        human_only_names = {e["filename"] for e in table if e["audience"] == "human-only"}
        assert "HUMAN-OVERSIGHT.md" in human_only_names
        assert "REVIEW_CRITERIA.md" in human_only_names

    def test_real_canonical_files_present(self):
        """SYSTEM_PROMPT.md, AGENT.md, PLAN.md must be canonical."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        canonical_names = {e["filename"] for e in table if e["authority"] == "canonical"}
        assert "SYSTEM_PROMPT.md" in canonical_names
        assert "AGENT.md" in canonical_names
        assert "PLAN.md" in canonical_names


# ---------------------------------------------------------------------------
# filter_for_session
# ---------------------------------------------------------------------------

class TestFilterForSession:
    def test_l0_excludes_on_demand(self):
        table = [
            _make_entry("AGENT.md", "agent-runtime", "canonical", "always"),
            _make_entry("ARCHITECTURE.md", "agent-on-demand", "reference", "on-demand"),
        ]
        result = filter_for_session(table, include_on_demand=False)
        assert "governance/AGENT.md" in result
        assert "governance/ARCHITECTURE.md" not in result

    def test_l1_includes_on_demand(self):
        table = [
            _make_entry("AGENT.md", "agent-runtime", "canonical", "always"),
            _make_entry("ARCHITECTURE.md", "agent-on-demand", "reference", "on-demand"),
        ]
        result = filter_for_session(table, include_on_demand=True)
        assert "governance/AGENT.md" in result
        assert "governance/ARCHITECTURE.md" in result

    def test_human_only_never_included_regardless_of_mode(self):
        table = [
            _make_entry("REVIEW_CRITERIA.md", "human-only", "reference", "never"),
            _make_entry("HUMAN-OVERSIGHT.md", "human-only", "reference", "never"),
        ]
        for include in (False, True):
            result = filter_for_session(table, include_on_demand=include)
            assert "governance/REVIEW_CRITERIA.md" not in result
            assert "governance/HUMAN-OVERSIGHT.md" not in result

    def test_never_load_excluded(self):
        table = [_make_entry("SECRET.md", "agent-runtime", "canonical", "never")]
        result = filter_for_session(table, include_on_demand=True)
        assert "governance/SECRET.md" not in result

    def test_incremental_not_in_filter_result(self):
        """incremental files are handled by memory pipeline, not session filter."""
        table = [_make_entry("facts.md", "agent-runtime", "canonical", "incremental")]
        result = filter_for_session(table, include_on_demand=True)
        assert "governance/facts.md" not in result

    def test_empty_table(self):
        assert filter_for_session([], include_on_demand=True) == []

    def test_real_l0_excludes_architecture(self):
        """Integration: real governance/ — L0 must not include ARCHITECTURE.md."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        result_l0 = filter_for_session(table, include_on_demand=False)
        filenames = [Path(f).name for f in result_l0]
        assert "ARCHITECTURE.md" not in filenames

    def test_real_l1_includes_architecture(self):
        """Integration: real governance/ — L1 must include ARCHITECTURE.md."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        result_l1 = filter_for_session(table, include_on_demand=True)
        filenames = [Path(f).name for f in result_l1]
        assert "ARCHITECTURE.md" in filenames

    def test_real_canonical_always_present_in_l0(self):
        """Integration: canonical always files must appear in L0."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        result = filter_for_session(table, include_on_demand=False)
        filenames = [Path(f).name for f in result]
        for must_have in ("SYSTEM_PROMPT.md", "AGENT.md", "PLAN.md"):
            assert must_have in filenames, f"{must_have} missing from L0 payload"


# ---------------------------------------------------------------------------
# get_human_only_files
# ---------------------------------------------------------------------------

class TestGetHumanOnlyFiles:
    def test_returns_human_only(self):
        table = [
            _make_entry("AGENT.md", "agent-runtime"),
            _make_entry("REVIEW_CRITERIA.md", "human-only"),
            _make_entry("HUMAN-OVERSIGHT.md", "human-only"),
        ]
        result = get_human_only_files(table)
        assert "governance/REVIEW_CRITERIA.md" in result
        assert "governance/HUMAN-OVERSIGHT.md" in result
        assert "governance/AGENT.md" not in result

    def test_empty_table(self):
        assert get_human_only_files([]) == []

    def test_real_governance_dir(self):
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        human_only = get_human_only_files(table)
        names = [Path(f).name for f in human_only]
        assert "HUMAN-OVERSIGHT.md" in names
        assert "REVIEW_CRITERIA.md" in names
        # canonical files must NOT be in human-only list
        assert "SYSTEM_PROMPT.md" not in names
        assert "AGENT.md" not in names


# ---------------------------------------------------------------------------
# resolve_conflict
# ---------------------------------------------------------------------------

class TestResolveConflict:
    def test_canonical_wins_over_reference(self):
        entries = [
            {"authority": "reference", "value": "ref"},
            {"authority": "canonical", "value": "canon"},
        ]
        winner = resolve_conflict(entries)
        assert winner["authority"] == "canonical"

    def test_canonical_wins_over_derived(self):
        entries = [
            {"authority": "derived", "value": "derived_val"},
            {"authority": "canonical", "value": "canon_val"},
        ]
        winner = resolve_conflict(entries)
        assert winner["authority"] == "canonical"

    def test_reference_wins_over_derived(self):
        entries = [
            {"authority": "derived"},
            {"authority": "reference"},
        ]
        winner = resolve_conflict(entries)
        assert winner["authority"] == "reference"

    def test_all_three_priorities(self):
        entries = [
            {"authority": "derived", "id": 3},
            {"authority": "canonical", "id": 1},
            {"authority": "reference", "id": 2},
        ]
        winner = resolve_conflict(entries)
        assert winner["authority"] == "canonical"
        assert winner["id"] == 1

    def test_single_entry(self):
        entries = [{"authority": "reference", "id": 99}]
        winner = resolve_conflict(entries)
        assert winner["id"] == 99

    def test_empty_returns_none(self):
        assert resolve_conflict([]) is None


# ---------------------------------------------------------------------------
# validate_session_payload
# ---------------------------------------------------------------------------

class TestValidateSessionPayload:
    def test_no_violations(self):
        table = [
            _make_entry("AGENT.md", "agent-runtime"),
            _make_entry("REVIEW_CRITERIA.md", "human-only"),
        ]
        allowed = ["governance/AGENT.md"]
        result = validate_session_payload(allowed, table)
        assert result["ok"] is True
        assert result["violations"] == []

    def test_detects_human_only_violation(self):
        table = [
            _make_entry("REVIEW_CRITERIA.md", "human-only"),
        ]
        # Simulate a bug: human-only file somehow ended up in allowed
        allowed = ["governance/REVIEW_CRITERIA.md"]
        result = validate_session_payload(allowed, table)
        assert result["ok"] is False
        assert "governance/REVIEW_CRITERIA.md" in result["violations"]

    def test_multiple_violations(self):
        table = [
            _make_entry("REVIEW_CRITERIA.md", "human-only"),
            _make_entry("HUMAN-OVERSIGHT.md", "human-only"),
        ]
        allowed = ["governance/REVIEW_CRITERIA.md", "governance/HUMAN-OVERSIGHT.md"]
        result = validate_session_payload(allowed, table)
        assert result["ok"] is False
        assert len(result["violations"]) == 2

    def test_empty_allowed_is_ok(self):
        table = [_make_entry("REVIEW_CRITERIA.md", "human-only")]
        result = validate_session_payload([], table)
        assert result["ok"] is True

    def test_real_governance_l0_is_clean(self):
        """Integration: L0 filter on real governance/ must have no violations."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        allowed = filter_for_session(table, include_on_demand=False)
        result = validate_session_payload(allowed, table)
        assert result["ok"] is True, f"Violations: {result['violations']}"

    def test_real_governance_l1_is_clean(self):
        """Integration: L1 filter on real governance/ must have no violations."""
        gov_dir = Path(__file__).resolve().parents[1] / "governance"
        table = load_authority_table(gov_dir)
        allowed = filter_for_session(table, include_on_demand=True)
        result = validate_session_payload(allowed, table)
        assert result["ok"] is True, f"Violations: {result['violations']}"
