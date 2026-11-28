"""Protect the inclusive raw-byte boundary and the framework's own headroom."""

from datetime import date
from pathlib import Path
import json
import re
import sys

import pytest

from governance_tools.instruction_context_budget import (
    OBSERVED_ANTIGRAVITY_SESSION_TRUNCATION_BYTES,
    antigravity_truncation_advisories,
    measure_codex_project_doc,
)
from governance_tools import governance_drift_checker as drift
from governance_tools.hook_installer import _codex_project_doc_budget


@pytest.fixture
def budget_repo(tmp_path, monkeypatch):
    """Keep other drift inputs valid so budget severity and CLI exits stand alone."""
    monkeypatch.setattr(
        "governance_tools.expansion_boundary_checker.check_transitional_key_staleness",
        lambda max_days=90: [],
    )
    today = date.today().isoformat()
    (tmp_path / ".governance").mkdir()
    (tmp_path / ".governance/baseline.yaml").write_text(
        f"baseline_version: 1.0.0\nsource_commit: {'a' * 40}\n"
        f"initialized_at: {today}T00:00:00Z\n", encoding="utf-8",
    )
    (tmp_path / "AGENTS.base.md").write_text(
        "<!-- governance-baseline: protected -->\n", encoding="utf-8",
    )
    (tmp_path / "contract.yaml").write_text(
        "name: budget-test\nframework_interface_version: 1\n"
        "framework_compatible: '>=1.0.0,<2.0.0'\ndomain: test\n"
        "documents:\n  - AGENTS.base.md\n", encoding="utf-8",
    )
    (tmp_path / "PLAN.md").write_text(
        f"# Plan\n\n> **最後更新**: {today}\n> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )
    memory = tmp_path / "memory"
    memory.mkdir()
    for name in ("01_active_task.md", "02_tech_stack.md", "03_knowledge_base.md", "04_review_log.md"):
        (memory / name).write_text("# Fixture\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"], ids=["no-bom", "bom"])
@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n"], ids=["no-newline", "lf", "crlf"])
@pytest.mark.parametrize(
    "size, overflow, lf_crlf_size, crlf_overflow",
    [(32767, 0, 32768, 0), (32768, 0, 32769, 1), (32769, 1, 32770, 2)],
)
def test_raw_budget_boundary_counts_bom_and_line_endings(
    bom, ending, size, overflow, lf_crlf_size, crlf_overflow,
):
    # Multibyte text makes decoding or character-counting the wrong measure.
    prefix = bom + "規則".encode("utf-8")
    payload = prefix + b"x" * (size - len(prefix) - len(ending)) + ending

    report = measure_codex_project_doc(payload)

    assert report == {
        "budget_bytes": 32768,
        "budget_source": "codex_default_project_doc_max_bytes",
        "on_disk_bytes": size,
        "crlf_worst_case_bytes": lf_crlf_size if ending == b"\n" else size,
        "overflow_bytes": overflow,
        "crlf_worst_case_overflow_bytes": crlf_overflow if ending == b"\n" else overflow,
        "over_budget": bool(overflow),
        "over_budget_with_crlf": bool(crlf_overflow if ending == b"\n" else overflow),
    }


def test_mixed_line_endings_do_not_double_count_existing_cr():
    assert measure_codex_project_doc(b"a\r\nb\nc\r")["crlf_worst_case_bytes"] == 8


def test_framework_root_agents_fits_on_disk_and_with_crlf():
    root_agents = Path(__file__).resolve().parents[1] / "AGENTS.md"
    report = measure_codex_project_doc(root_agents.read_bytes())

    assert report["over_budget"] is False, report
    assert report["over_budget_with_crlf"] is False, report


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"], ids=["no-bom", "bom"])
@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n"], ids=["no-newline", "lf", "crlf"])
@pytest.mark.parametrize("size", [23876, 23877, 23878])
def test_antigravity_observed_boundary_counts_raw_bytes(bom, ending, size):
    prefix = bom + "規則".encode("utf-8")
    payload = prefix + b"x" * (size - len(prefix) - len(ending)) + ending

    advisories = antigravity_truncation_advisories(payload)

    assert OBSERVED_ANTIGRAVITY_SESSION_TRUNCATION_BYTES == 23877
    if size == 23878:
        assert advisories == [
            "Instruction payload is 23878 bytes on disk, exceeding the observed "
            "Antigravity session truncation threshold of 23877 bytes; tail instructions "
            "may be omitted. This is an observed session threshold, not a universal "
            "Antigravity specification. Advisory only; Codex's 32768-byte budget "
            "and pass/fail results are unchanged."
        ]
    else:
        assert advisories == []


@pytest.mark.parametrize(
    "size, over_budget, overflow",
    [(23878, False, 0), (32768, False, 0), (32769, True, 1)],
)
def test_antigravity_advisory_does_not_change_codex_budget(size, over_budget, overflow):
    payload = b"x" * size

    assert antigravity_truncation_advisories(payload)
    assert measure_codex_project_doc(payload) == {
        "budget_bytes": 32768,
        "budget_source": "codex_default_project_doc_max_bytes",
        "on_disk_bytes": size,
        "crlf_worst_case_bytes": size,
        "overflow_bytes": overflow,
        "crlf_worst_case_overflow_bytes": overflow,
        "over_budget": over_budget,
        "over_budget_with_crlf": over_budget,
    }


def test_antigravity_empty_payload_has_no_advisory():
    assert antigravity_truncation_advisories(b"") == []


@pytest.mark.parametrize(
    "heading",
    [
        b"## Repo-Specific Forbidden Behaviors",
        b"## Workspace vs Repo Governance",
        b"## Nested Repo / Submodule Rule",
        b"## Memory",
        b"## Safety",
        b"## External vs Internal",
    ],
)
def test_framework_critical_sections_end_before_23000_bytes(heading):
    # The whole section must survive, including nested headings and final rules
    # (self_reference_note, preference precedence and destructive-update inventory).
    payload = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_bytes()
    match = re.search(rb"^" + re.escape(heading) + rb"\r?$", payload, re.MULTILINE)
    assert match is not None, heading
    start = match.start()
    following = re.search(rb"^## ", payload[start + 1:], re.MULTILINE)
    end = start + 1 + following.start() if following else len(payload)

    assert end < 23000, (heading, start, end)


@pytest.mark.parametrize("projection", ["checkpoint-projection", "agent-core-rules", "session-end-closeout"])
def test_framework_canonical_projections_end_before_23000_bytes(projection):
    payload = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_bytes()
    marker = f"<!-- ai-governance:{projection} END -->".encode("ascii")

    assert payload.index(marker) + len(marker) < 23000


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"], ids=["no-bom", "bom"])
@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n"], ids=["no-newline", "lf", "crlf"])
@pytest.mark.parametrize("size", [32767, 32768, 32769])
def test_drift_raw_budget_boundary(budget_repo, bom, ending, size):
    prefix = bom + "規則".encode("utf-8")
    target = budget_repo / "AGENTS.md"
    target.write_bytes(prefix + b"x" * (size - len(prefix) - len(ending)) + ending)

    result = drift.check_governance_drift(budget_repo)
    budget_findings = [f for f in result.findings if f["check"] == "agents_context_budget"]
    report, warnings = _codex_project_doc_budget(budget_repo, [str(target)])

    if size == 32769:
        assert result.ok is False
        assert result.severity == "critical"
        assert result.checks["agents_context_budget"] is False
        detail = budget_findings[0]["detail"]
        for token in ("32769 bytes", "32768", "1 bytes over", "Codex", "silently truncated"):
            assert token in detail
        assert report["over_budget"] is True and len(warnings) == 1
    elif size == 32768 and ending == b"\n":
        # The raw file fits exactly; only a future CRLF checkout would truncate.
        assert result.ok is True
        assert result.severity == "ok"
        assert result.checks["agents_context_budget"] is True
        assert budget_findings == []
        assert result.errors == []
        assert result.warnings == [
            "agents_context_budget: AGENTS.md is 32768 bytes on disk and fits "
            "Codex's default 32768-byte project-doc limit, but its CRLF form "
            "would be 32769 bytes (1 bytes over); a Windows checkout with "
            "autocrlf would have its tail silently truncated."
        ]
        assert report["over_budget"] is False and len(warnings) == 1
    else:
        assert result.ok is True
        assert result.severity == "ok"
        assert result.checks["agents_context_budget"] is True
        assert budget_findings == []
        assert report["over_budget"] is False and warnings == []


def test_missing_root_agents_is_not_applicable(budget_repo):
    # Another instruction surface and a nested file do not spend this check's budget.
    (budget_repo / "CLAUDE.md").write_bytes(b"x" * 40000)
    nested = budget_repo / "nested"
    nested.mkdir()
    (nested / "AGENTS.md").write_bytes(b"x" * 40000)

    result = drift.check_governance_drift(budget_repo)

    assert result.ok is True
    assert result.severity == "ok"
    assert "agents_context_budget" not in result.checks
    assert not any(f["check"] == "agents_context_budget" for f in result.findings)


@pytest.mark.parametrize(
    "payload, exit_code, severity, expected_advisory",
    [(b"x" * 32768, 0, "ok", False), (b"x" * 32769, 2, "critical", False),
     (b"x" * 32767 + b"\n", 0, "ok", True)],
    ids=["exact-limit", "one-byte-over", "lf-crlf-risk"],
)
def test_drift_budget_cli_exit_codes(
    budget_repo, monkeypatch, capsys, payload, exit_code, severity, expected_advisory,
):
    (budget_repo / "AGENTS.md").write_bytes(payload)
    monkeypatch.setattr(sys, "argv", ["governance_drift_checker", "--repo", str(budget_repo), "--format", "json"])

    assert drift.main() == exit_code
    output = json.loads(capsys.readouterr().out)
    assert output["severity"] == severity
    assert output["checks"]["agents_context_budget"] is (exit_code == 0)
    assert bool(output["warnings"]) is expected_advisory
    if expected_advisory:
        assert "CRLF form would be 32769 bytes" in output["warnings"][0]
        assert "silently truncated" in output["warnings"][0]
        assert output["findings"] == []
