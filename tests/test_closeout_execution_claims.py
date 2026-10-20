"""Own execution is a statement, not a tool-name occurrence (CLOSEOUT-02)."""
from pathlib import Path

import pytest

from governance_tools.session_end_hook import (
    _check_content, _check_evidence, CONTENT_SUFFICIENT, CONTENT_INSUFFICIENT,
    EVIDENCE_CONSISTENT, EVIDENCE_INCONSISTENT, EVIDENCE_UNCHECKED,
)


def evidence(root: Path, checks: str):
    (root / "review.md").write_text("Input boundary review.\n", encoding="utf-8")
    return _check_evidence({"FILES_TOUCHED": "review.md", "CHECKS_RUN": checks}, root)


@pytest.mark.parametrize("statement", [
    "supplied pytest evidence was not run by me",
    "I did not run pytest; supplied JUnit reports 38 passed.",
    "I did not run pytest locally; supplied JUnit reports 38 passed.",
    "NOT RUN: pytest; reviewed supplied results only.",
    "I have not executed pytest myself.",
    "CI ran pytest -q and supplied the JUnit artifact.",
    "The report states 'I ran pytest -q'.",
    'The report states "I ran pytest -q".',
    "The supplied report says I ran pytest -q.",
    "Read pytest documentation in review.md.",
    "未執行 pytest；僅查閱外部 JUnit 結果。",
])
def test_nonexecution_mentions_do_not_require_local_runner_artifacts(tmp_path, statement):
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_CONSISTENT
    assert problems == []
    assert not any(r.get("tool") == "pytest" for r in refs)


@pytest.mark.parametrize("statement", [
    "I ran pytest -q.",
    "We executed pytest tests/test_boundary.py.",
    "Ran pytest tests/test_boundary.py.",
    "I ran `pytest -q` and got 38 passed.",
    "pytest -q",
    "pytest tests/test_boundary.py",
    "python -m pytest -q",
    "python -B -X utf8 -m pytest -q",
    "pytest: 38 passed",
    "pytest",
    "已執行 pytest -q，38 passed。",
    "I did not run pytest earlier; I later ran pytest -q.",
    "Supplied pytest evidence was not run by me; I ran pytest -q afterwards.",
    "I ran pytest using supplied fixtures.",
])
def test_positive_claim_still_requires_existing_local_artifact_signals(tmp_path, statement):
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_INCONSISTENT
    assert any("'pytest' claimed" in p for p in problems)
    assert any(r.get("tool") == "pytest" and r["artifact_found"] is False for r in refs)
    # Existing admissibility signals are unchanged, not replaced by text parsing.
    (tmp_path / ".pytest_cache").mkdir()
    status, problems, _ = evidence(tmp_path, statement)
    assert status == EVIDENCE_CONSISTENT and not problems


def test_external_clause_does_not_hide_another_positive_execution_claim(tmp_path):
    status, problems, refs = evidence(
        tmp_path, "Supplied pytest evidence was not run by me; I ran quickstart_smoke.")
    assert status == EVIDENCE_INCONSISTENT
    assert not any(r.get("tool") == "pytest" for r in refs)
    assert any("quickstart_smoke" in p for p in problems)


def test_external_result_is_still_checked_as_a_referenced_file(tmp_path):
    status, problems, refs = _check_evidence({
        "FILES_TOUCHED": "missing-junit.xml",
        "CHECKS_RUN": "supplied pytest evidence was not run by me",
    }, tmp_path)
    assert status == EVIDENCE_INCONSISTENT
    assert any("missing-junit.xml" in p for p in problems)
    assert not any(r.get("tool") == "pytest" for r in refs)


def test_denial_without_any_referenced_evidence_is_unchecked(tmp_path):
    status, problems, refs = _check_evidence({
        "FILES_TOUCHED": "NONE", "CHECKS_RUN": "supplied pytest evidence was not run by me",
    }, tmp_path)
    assert status == EVIDENCE_UNCHECKED
    assert not problems and not refs


@pytest.mark.parametrize("checks,expected", [
    ("I did not run pytest; supplied JUnit reports 38 passed.", CONTENT_SUFFICIENT),
    ("supplied pytest evidence was not run by me", CONTENT_SUFFICIENT),
    ("I ran pytest -q.", CONTENT_SUFFICIENT),
    ("ran checks", CONTENT_INSUFFICIENT),
    ("", CONTENT_INSUFFICIENT),
])
def test_content_anchor_is_independent_of_execution_assertion(checks, expected):
    status, issues = _check_content({
        "TASK_INTENT": "Review the documented boundary",
        "WORK_COMPLETED": "Reviewed review.md", "CHECKS_RUN": checks,
    })
    assert status == expected
    assert bool(issues) == (expected == CONTENT_INSUFFICIENT)


def test_content_rejects_missing_completed_work():
    status, issues = _check_content({"TASK_INTENT": "Review", "CHECKS_RUN": "pytest -q"})
    assert status == CONTENT_INSUFFICIENT
    assert any(i["field"] == "WORK_COMPLETED" for i in issues)


def test_compact_multiple_commands_keep_their_evidence_requirements(tmp_path):
    status, problems, refs = evidence(tmp_path, "session_end_hook; npm")
    assert status == EVIDENCE_INCONSISTENT
    assert any("'session_end_hook' claimed" in p for p in problems)
    assert any(r.get("tool") == "npm" for r in refs)


def test_shell_chaining_cannot_hide_a_positive_execution_claim(tmp_path):
    status, problems, _ = evidence(tmp_path, "pytest -q && session_end_hook")
    assert status == EVIDENCE_INCONSISTENT
    assert any("'pytest' claimed" in p for p in problems)
    assert any("'session_end_hook' claimed" in p for p in problems)


@pytest.mark.parametrize(("statement", "requires_runner"), [
    ("I ran pytest", True),
    ("已執行 pytest", True),
    ("我執行了 pytest", True),
    ("我跑了 pytest", True),
    ("我有執行 pytest", True),
    ("我已執行 pytest", True),
    ("我沒有執行 pytest", False),
    ("pytest 不是我執行的", False),
    ("supplied pytest evidence was not run by me", False),
    ("JUnit 顯示 248 passed", False),
])
def test_owner_first_person_execution_claim_matrix(tmp_path, statement, requires_runner):
    status, problems, refs = evidence(tmp_path, statement)
    runner_refs = [r for r in refs if r.get("tool") == "pytest"]
    if requires_runner:
        assert status == EVIDENCE_INCONSISTENT
        assert any("'pytest' claimed" in p for p in problems)
        assert len(runner_refs) == 1 and runner_refs[0]["artifact_found"] is False
        (tmp_path / ".pytest_cache").mkdir()
        status, problems, refs = evidence(tmp_path, statement)
        assert status == EVIDENCE_CONSISTENT and not problems
        assert any(r.get("tool") == "pytest" and r["artifact_found"] for r in refs)
    else:
        assert status == EVIDENCE_CONSISTENT and not problems
        assert not runner_refs


@pytest.mark.parametrize("artifact_exists", [False, True])
def test_supplied_junit_statement_still_requires_its_referenced_artifact(tmp_path, artifact_exists):
    if artifact_exists:
        (tmp_path / "supplied-junit.xml").write_text("<testsuite tests='248'/>", encoding="utf-8")
    status, problems, refs = _check_evidence({
        "FILES_TOUCHED": "supplied-junit.xml",
        "CHECKS_RUN": "JUnit 顯示 248 passed",
    }, tmp_path)
    assert status == (EVIDENCE_CONSISTENT if artifact_exists else EVIDENCE_INCONSISTENT)
    assert bool(problems) is not artifact_exists
    assert any(r.get("claimed") == "supplied-junit.xml" and r["found"] is artifact_exists for r in refs)
    assert not any(r.get("tool") == "pytest" for r in refs)
