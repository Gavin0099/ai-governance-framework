"""Own execution is a statement, not a tool-name occurrence (CLOSEOUT-02)."""
import ast
import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

from governance_tools.session_end_hook import (
    _check_content, _check_evidence, CONTENT_SUFFICIENT, CONTENT_INSUFFICIENT,
    EVIDENCE_CONSISTENT, EVIDENCE_INCONSISTENT, EVIDENCE_UNCHECKED,
    classify_closeout,
)


@pytest.fixture(autouse=True)
def synthetic_repo(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)


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
    "The supplied report says, I ran pytest -q.",
    'The report states "I ran pytest -q, session_end_hook".',
    'The report states \'session_end_hook, "C:\\Program Files\\Python313\\python.exe" -m pytest -q\'.',
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
    "After CI failed, I ran pytest -q.",
    "Using supplied fixtures, I ran pytest -q.",
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


def test_denial_without_any_referenced_evidence_is_consistent(tmp_path):
    status, problems, refs = _check_evidence({
        "FILES_TOUCHED": "NONE", "CHECKS_RUN": "supplied pytest evidence was not run by me",
    }, tmp_path)
    assert status == EVIDENCE_CONSISTENT
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


@pytest.mark.parametrize("checks", [
    "pytest -q, session_end_hook",
    "python -m pytest -q, session_end_hook",
    "pytest, session_end_hook",
])
def test_comma_separated_commands_each_require_their_own_footprint(tmp_path, checks):
    (tmp_path / ".pytest_cache").mkdir()
    status, problems, refs = evidence(tmp_path, checks)
    assert status == EVIDENCE_INCONSISTENT
    assert any("'session_end_hook' claimed" in p for p in problems)
    (tmp_path / "artifacts/runtime/verdicts").mkdir(parents=True)
    status, problems, refs = evidence(tmp_path, checks)
    assert status == EVIDENCE_CONSISTENT and not problems
    assert {r["tool"] for r in refs if "tool" in r} >= {"pytest", "session_end_hook"}


@pytest.mark.parametrize("executable", [
    r'"C:\Program Files\Python313\python.exe"',
    r'"C:\Tools, Python\python.exe"',
])
@pytest.mark.parametrize("module_first", [False, True])
def test_command_list_preserves_quoted_module_executable(tmp_path, executable, module_first):
    module = executable + " -m pytest -q"
    checks = module + ", session_end_hook" if module_first else "session_end_hook, " + module
    (tmp_path / "artifacts/runtime/verdicts").mkdir(parents=True)
    status, problems, refs = evidence(tmp_path, checks)
    assert status == EVIDENCE_INCONSISTENT
    assert any("'pytest' claimed" in p for p in problems)
    (tmp_path / ".pytest_cache").mkdir()
    status, problems, refs = evidence(tmp_path, checks)
    assert status == EVIDENCE_CONSISTENT and not problems
    assert {r["tool"] for r in refs if "tool" in r} >= {"pytest", "session_end_hook"}


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
    assert bool(problems) is (not artifact_exists)
    assert any(r.get("claimed") == "supplied-junit.xml" and r["found"] is artifact_exists for r in refs)
    assert not any(r.get("tool") == "pytest" for r in refs)


@pytest.mark.parametrize("statement", [
    "I didn't run pytest.",
    "pytest was not executed by me.",
    "pytest: NOT RUN",
    "Read pytest documentation.",
    "pytest documentation was reviewed.",
    "pytest was mentioned in review.md.",
    "pytest output from CI was supplied.",
    "pytest evidence supplied by the reviewer.",
    "pytest 在報告中被提及。",
    "pytest: supplied results show 38 passed.",
    "pytest was run by CI.",
    "I reviewed pytest output.",
    "CI 執行 pytest -q。",
    "外部報告顯示 pytest: 38 passed。",
    "我並未在本機執行 pytest。",
    "我没有执行 pytest。",
    '"I ran pytest -q"',
    "'I ran pytest -q'",
    "`I ran pytest -q`",
    "「我有執行 pytest」",
])
def test_mentions_and_quoted_assertions_are_not_self_execution(tmp_path, statement):
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_CONSISTENT
    assert not problems
    assert not any(ref.get("tool") == "pytest" for ref in refs)


@pytest.mark.parametrize("statement", [
    "我有執行pytest",
    "我执行了pytest",
    "我剛剛跑了 pytest",
    "I have executed pytest.",
    "I have run pytest.",
    "I also ran pytest -q.",
    "pytest：38 passed",
    "pytest:38 passed",
    "pytest docs.py",
])
def test_punctuation_and_chinese_claims_require_local_signals(tmp_path, statement):
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_INCONSISTENT
    assert any("'pytest' claimed" in problem for problem in problems)
    assert any(ref.get("tool") == "pytest" and not ref["artifact_found"] for ref in refs)
    (tmp_path / ".pytest_cache").mkdir()
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_CONSISTENT
    assert not problems
    assert any(ref.get("tool") == "pytest" and ref["artifact_found"] for ref in refs)


@pytest.mark.parametrize("statement,claimed", [
    ("I ran pytest; I only read session_end_hook documentation.", {"pytest"}),
    ("I ran pytest, but I did not execute session_end_hook.", {"pytest"}),
    ("CI ran pytest, and I ran quickstart_smoke.", {"quickstart_smoke"}),
    ("未執行 pytest；我有執行 session_end_hook。", {"session_end_hook"}),
    ("I did not run pytest, but I later ran pytest -q.", {"pytest"}),
    ("I ran pytest and session_end_hook.", {"pytest", "session_end_hook"}),
])
def test_each_clause_retains_its_own_execution_scope(tmp_path, statement, claimed):
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_INCONSISTENT
    assert problems
    assert {ref["tool"] for ref in refs if ref["type"] == "tool_artifact_signal"} == claimed


@pytest.mark.parametrize("statement", [
    "I ran pytest and got 'not run' from an unrelated report.",
    "I ran pytest and got 'session_end_hook was not run' in a report.",
])
def test_quoted_denial_does_not_override_actual_execution(tmp_path, statement):
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_INCONSISTENT
    assert {ref["tool"] for ref in refs if "tool" in ref} == {"pytest"}
    (tmp_path / ".pytest_cache").mkdir()
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_CONSISTENT
    assert not problems


def test_unconfigured_local_tool_keeps_existing_evidence_status(tmp_path):
    # Characterization: an unmapped tool has no configured artifact requirement.
    status, problems, refs = _check_evidence({
        "FILES_TOUCHED": "NONE", "CHECKS_RUN": "I ran custom_check.py",
    }, tmp_path)
    assert status == EVIDENCE_CONSISTENT
    assert not problems and not refs


@pytest.mark.parametrize("statement,requires_runner,expected", [
    ("", False, EVIDENCE_UNCHECKED),
    ('The report states "I ran pytest -q', False, EVIDENCE_CONSISTENT),
    ('"I ran pytest -q', False, EVIDENCE_CONSISTENT),
    ("I ran `pytest -q", True, EVIDENCE_INCONSISTENT),
])
def test_empty_and_unclosed_quotes_keep_an_explicit_result(tmp_path, statement, requires_runner, expected):
    status, problems, refs = _check_evidence({
        "FILES_TOUCHED": "NONE", "CHECKS_RUN": statement,
    }, tmp_path)
    assert status == expected
    assert bool(problems) is requires_runner
    assert any(ref.get("tool") == "pytest" for ref in refs) is requires_runner


@pytest.mark.parametrize("statement", ["pytest_cov documentation", "pytest.py", "notpytest"])
def test_partial_tool_names_are_not_runner_claims(tmp_path, statement):
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_CONSISTENT
    assert not problems
    assert not any(ref.get("tool") == "pytest" for ref in refs)


@pytest.mark.parametrize("tool,artifact", [
    ("governance_drift_checker", ".governance-state.yaml"),
    ("codeburn_codex_smoke", "codeburn/phase2/examples/codex_smoke_fixture.jsonl"),
    ("codeburn_copilot_smoke", "codeburn/phase2/examples/copilot_smoke_fixture.csv"),
    ("test_codeburn_copilot_smoke.py", "tests/test_codeburn_copilot_smoke.py"),
])
def test_other_existing_artifact_signals_still_apply(tmp_path, tool, artifact):
    statement = "I ran " + tool
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_INCONSISTENT
    assert any(ref.get("tool") == tool and not ref["artifact_found"] for ref in refs)
    path = tmp_path / artifact
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Synthetic artifact signal.\n", encoding="utf-8")
    status, problems, refs = evidence(tmp_path, statement)
    assert status == EVIDENCE_CONSISTENT
    assert not problems
    assert any(ref.get("tool") == tool and ref["artifact_found"] for ref in refs)


@pytest.mark.parametrize("checks,requires_runner", [
    ("supplied pytest evidence was not run by me", False),
    ("I used the supplied pytest report.", False),
    ("We used provided pytest results.", False),
    ("I used the supplied pytest report to run pytest -q.", True),
    ("I used the supplied pytest report, then ran pytest -q.", True),
    ("I used the supplied pytest report, then reran the same command.", True),
    ("I used the supplied pytest report and reran the tests.", True),
    ("我有執行 pytest", True),
    ("pytest: 38 passed", True),
    ("pytest：38 passed", True),
    ('The report states "I ran pytest -q".', False),
    ("Tests: pytest", True),
    ("Verified with pytest", True),
    ("用 pytest 驗證過", True),
])
def test_current_closeout_classifier_uses_claims_without_changing_statuses(tmp_path, checks, requires_runner):
    (tmp_path / "review.md").write_text("Synthetic input review.\n", encoding="utf-8")
    path = tmp_path / "artifacts/session-closeout.txt"
    path.parent.mkdir()
    path.write_text(
        "TASK_INTENT: Review the synthetic input\n"
        "WORK_COMPLETED: Reviewed review.md\n"
        "FILES_TOUCHED: review.md\n"
        f"CHECKS_RUN: {checks}\n"
        "OPEN_RISKS: NONE\nNOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n",
        encoding="utf-8",
    )
    result = classify_closeout(path, tmp_path)
    assert result["schema_validity"] == "valid"
    assert result["content_sufficiency"] == CONTENT_SUFFICIENT
    assert result["evidence_consistency"] == (
        EVIDENCE_INCONSISTENT if requires_runner else EVIDENCE_CONSISTENT
    )
    assert result["closeout_status"] == ("evidence_inconsistent" if requires_runner else "valid")
    (tmp_path / ".pytest_cache").mkdir()
    result = classify_closeout(path, tmp_path)
    assert result["closeout_status"] == "valid"


@pytest.mark.parametrize("checks,requires_runner", [
    ("Tests: pytest", True),
    ("Verified with pytest", True),
    ("用 pytest 驗證過", True),
    ("Validation relied on pytest", True),
    ("Checks completed via pytest", True),
    ("Successfully validated with pytest", True),
    ("透過 pytest 完成檢查", True),
    ("以 pytest 核對結果", True),
    ("驗證工具：pytest", True),
    ("supplied pytest evidence was not run by me", False),
    ("我有執行 pytest", True),
    ("pytest: 38 passed", True),
])
def test_probe_phrasings_default_to_claim_unless_excluded(tmp_path, checks, requires_runner):
    fields = {"FILES_TOUCHED": "NONE", "CHECKS_RUN": checks}
    status, problems, refs = _check_evidence(fields, tmp_path)
    assert status == (EVIDENCE_INCONSISTENT if requires_runner else EVIDENCE_CONSISTENT)
    runner_refs = [ref for ref in refs if ref.get("tool") == "pytest"]
    assert len(runner_refs) == int(requires_runner)
    assert bool(problems) is requires_runner
    if requires_runner:
        assert runner_refs[0]["artifact_found"] is False
    (tmp_path / ".pytest_cache").mkdir()
    status, problems, refs = _check_evidence(fields, tmp_path)
    assert status == EVIDENCE_CONSISTENT
    assert not problems
    assert any(ref.get("tool") == "pytest" and ref["artifact_found"] for ref in refs) is requires_runner


@pytest.mark.parametrize("checks,expected", [
    ("", EVIDENCE_UNCHECKED),
    ("  ", EVIDENCE_UNCHECKED),
    ("NONE", EVIDENCE_UNCHECKED),
    ("none", EVIDENCE_UNCHECKED),
    ("supplied pytest evidence was not run by me", EVIDENCE_CONSISTENT),
    ("CI ran pytest -q", EVIDENCE_CONSISTENT),
    ('The report states "I ran pytest -q".', EVIDENCE_CONSISTENT),
    ("Read pytest documentation", EVIDENCE_CONSISTENT),
    ('"Verified with pytest"', EVIDENCE_CONSISTENT),
    ("pytest documentation was reviewed", EVIDENCE_CONSISTENT),
    ("No known runner names", EVIDENCE_CONSISTENT),
])
def test_checkable_field_presence_restores_main_status(tmp_path, checks, expected):
    assert _check_evidence({"FILES_TOUCHED": "NONE", "CHECKS_RUN": checks}, tmp_path) == (expected, [], [])


def _existing_check_phrasings():
    """Include existing parametrized inputs and literal CHECKS_RUN call sites."""
    phrasings = set()
    for value in list(globals().values()):
        if not callable(value):
            continue
        for mark in getattr(value, "pytestmark", []):
            if mark.name != "parametrize":
                continue
            names, rows = mark.args[:2]
            names = names.split(",") if isinstance(names, str) else names
            names = [name.strip() for name in names]
            for row in rows:
                values = (row,) if len(names) == 1 else row
                for name, item in zip(names, values):
                    if name in {"checks", "statement"}:
                        phrasings.add(item)
                    elif name == "tool":
                        phrasings.add("I ran " + item)
                    elif name == "executable":
                        command = item + " -m pytest -q"
                        phrasings.update((command + ", session_end_hook", "session_end_hook, " + command))
    for node in ast.walk(ast.parse(Path(__file__).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "evidence":
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                phrasings.add(node.args[1].value)
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "CHECKS_RUN"
                        and isinstance(value, ast.Constant)):
                    phrasings.add(value.value)
    return phrasings


# Snapshot all earlier tests before defining the new corpus-based tests.
_PRE_REVIEW_PHRASINGS = _existing_check_phrasings()
_LITERAL_COMMANDS = (
    "python -m pytest -q", "py -m pytest -q", "python3 -m pytest -q",
    "python3.11 -m pytest -q", "uv run pytest -q", "poetry run pytest -q",
    "pipx run pytest -q", "tox -e py -- pytest -q", "npx pytest -q",
    ".venv/bin/python -m pytest -q", r".venv\Scripts\python.exe -m pytest -q",
    r'"C:\Synthetic Tools\python3.exe" -m pytest -q',
)
_QUOTED_COMMAND_CLAIMS = tuple(
    template.format(command=command)
    for command in _LITERAL_COMMANDS
    for template in (
        "I ran `{command}`.", "我有執行 `{command}`。", "`{command}`",
        '"{command}"', "'{command}'",
    )
)
_ENGLISH_NEGATIONS = ("didn't run", "did not run", "never ran", "not run", "didn’t run")
_CHINESE_NEGATIONS = ("沒有執行", "未執行", "没有执行", "並未執行")
_MIXED_EXECUTION_CLAIMS = tuple(
    (statement, positive)
    for positive, negative in (("pytest", "session_end_hook"), ("session_end_hook", "pytest"))
    for negation in _ENGLISH_NEGATIONS
    for statement in (
        f"I ran {positive} and {negation} {negative}.",
        f"I {negation} {negative} and ran {positive}.",
    )
) + tuple(
    (statement, positive)
    for positive, negative in (("pytest", "session_end_hook"), ("session_end_hook", "pytest"))
    for negation in _CHINESE_NEGATIONS
    for coordinator in ("且", "但", "而且", "，")
    for statement in (
        f"我有執行 {positive}{coordinator}我{negation} {negative}。",
        f"我{negation} {negative}{coordinator}我有執行 {positive}。",
    )
) + (
    ("I ran pytest, not session_end_hook.", "pytest"),
    ("Not session_end_hook, I ran pytest.", "pytest"),
    ("I ran pytest and session_end_hook was not run.", "pytest"),
    ("session_end_hook was not run and I ran pytest.", "pytest"),
    ("我有執行 pytest，未 session_end_hook。", "pytest"),
    ("未 session_end_hook，我有執行 pytest。", "pytest"),
    ("I ran pytest not session_end_hook.", "pytest"),
    ("I ran pytest not run session_end_hook.", "pytest"),
    ("我有執行 pytest未執行 session_end_hook。", "pytest"),
)

# Exact inputs only: these are the owner-authorized non-execution contexts.
# No regex or production-derived expected results may extend this allow-list.
_INTENDED_EXCLUSIONS = {
    "supplied pytest evidence was not run by me": "supplied evidence",
    "I did not run pytest locally; supplied JUnit reports 38 passed.": "negation",
    "I have not executed pytest myself.": "negation",
    "CI ran pytest -q and supplied the JUnit artifact.": "CI evidence",
    "The report states 'I ran pytest -q'.": "report attribution",
    'The report states "I ran pytest -q".': "report attribution",
    "The supplied report says I ran pytest -q.": "report attribution",
    "The supplied report says, I ran pytest -q.": "report attribution",
    'The report states "I ran pytest -q, session_end_hook".': "report attribution",
    'The report states \'session_end_hook, "C:\\Program Files\\Python313\\python.exe" -m pytest -q\'.': "report attribution",
    "Read pytest documentation in review.md.": "documentation",
    "我沒有執行 pytest": "negation",
    "pytest 不是我執行的": "negation",
    "pytest was not executed by me.": "negation",
    "Read pytest documentation.": "documentation",
    "pytest documentation was reviewed.": "documentation",
    "pytest was mentioned in review.md.": "documentation",
    "pytest output from CI was supplied.": "CI evidence",
    "pytest evidence supplied by the reviewer.": "supplied evidence",
    "pytest 在報告中被提及。": "report attribution",
    "pytest was run by CI.": "CI evidence",
    "I reviewed pytest output.": "supplied evidence",
    "I used the supplied pytest report.": "supplied evidence",
    "We used provided pytest results.": "supplied evidence",
    "CI 執行 pytest -q。": "CI evidence",
    '"I ran pytest -q"': "quoted assertion",
    "'I ran pytest -q'": "quoted assertion",
    "`I ran pytest -q`": "quoted assertion",
    'The report states "I ran pytest -q': "report attribution",
    '"I ran pytest -q': "quoted assertion",
    "CI ran pytest -q": "CI evidence",
    "Read pytest documentation": "documentation",
    "pytest documentation was reviewed": "documentation",
    "I did not run session_end_hook": "negation",
    "I didn't run session_end_hook": "negation",
    "I never ran session_end_hook": "negation",
    "I did not run pytest": "negation",
    "I didn't run pytest": "negation",
    "I never ran pytest": "negation",
    "not pytest": "negation",
    "not session_end_hook": "negation",
    "沒有執行 pytest": "negation",
    "未執行 pytest": "negation",
    "沒有執行 session_end_hook": "negation",
    "未執行 session_end_hook": "negation",
}
_DIFFERENTIAL_PHRASINGS = sorted(
    _PRE_REVIEW_PHRASINGS | set(_QUOTED_COMMAND_CLAIMS)
    | {statement for statement, _ in _MIXED_EXECUTION_CLAIMS}
    | set(_INTENDED_EXCLUSIONS)
)


@pytest.fixture(scope="module")
def main_check_evidence(tmp_path_factory):
    """Load the actual frozen main implementation, never the new parser."""
    repo = Path(__file__).resolve().parents[1]
    source = subprocess.run(
        ["git", "show", "39d57baf:governance_tools/session_end_hook.py"],
        cwd=repo, check=True, capture_output=True, encoding="utf-8",
        env={name: value for name, value in os.environ.items() if not name.upper().startswith("GIT_")},
    ).stdout
    path = tmp_path_factory.mktemp("main_evidence_module") / "session_end_hook.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("governance_tools._main_evidence_baseline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._check_evidence


@pytest.mark.parametrize("checks", _DIFFERENTIAL_PHRASINGS)
def test_main_evidence_differential_allows_only_explicit_nonexecution(tmp_path, main_check_evidence, checks):
    fields = {"FILES_TOUCHED": "NONE", "CHECKS_RUN": checks}
    old = main_check_evidence(fields, tmp_path)[0]
    new = _check_evidence(fields, tmp_path)[0]
    if old == EVIDENCE_INCONSISTENT and new == EVIDENCE_CONSISTENT:
        assert checks in _INTENDED_EXCLUSIONS, f"Unintended fail-open: {checks!r}: {old} -> {new}"
        print(f"\nINTENDED_FLIP {checks!r} -> {old} -> {new}")
    if checks in _INTENDED_EXCLUSIONS:
        assert (old, new) == (EVIDENCE_INCONSISTENT, EVIDENCE_CONSISTENT)


@pytest.mark.parametrize("checks", _QUOTED_COMMAND_CLAIMS)
def test_quoted_launcher_command_retains_recognized_tool(tmp_path, checks):
    status, problems, refs = _check_evidence({"FILES_TOUCHED": "NONE", "CHECKS_RUN": checks}, tmp_path)
    assert status == EVIDENCE_INCONSISTENT
    assert problems and any(ref.get("tool") == "pytest" for ref in refs)
    (tmp_path / ".pytest_cache").mkdir()
    assert _check_evidence({"FILES_TOUCHED": "NONE", "CHECKS_RUN": checks}, tmp_path)[0] == EVIDENCE_CONSISTENT


@pytest.mark.parametrize("checks,claimed", _MIXED_EXECUTION_CLAIMS)
def test_negation_cannot_discard_another_affirmative_predicate(tmp_path, checks, claimed):
    fields = {"FILES_TOUCHED": "NONE", "CHECKS_RUN": checks}
    status, problems, refs = _check_evidence(fields, tmp_path)
    assert status == EVIDENCE_INCONSISTENT
    assert problems and {ref["tool"] for ref in refs} == {claimed}
    signal = ".pytest_cache" if claimed == "pytest" else "artifacts/runtime/verdicts"
    (tmp_path / signal).mkdir(parents=True)
    status, problems, refs = _check_evidence(fields, tmp_path)
    assert status == EVIDENCE_CONSISTENT and not problems
    assert {ref["tool"] for ref in refs} == {claimed}


@pytest.mark.parametrize("checks", [
    "I ran `python3 -m pytest -q`.",
    "I ran `uv run pytest -q`.",
    "I ran `.venv/bin/python -m pytest -q`.",
    "I ran pytest and didn't run session_end_hook.",
    "I ran pytest and never ran session_end_hook.",
])
def test_reviewer_examples_cannot_qualify_as_valid_without_artifacts(tmp_path, checks):
    path = tmp_path / "session-closeout.txt"
    path.write_text(
        "TASK_INTENT: Review the synthetic input\nWORK_COMPLETED: Reviewed review.md\n"
        "FILES_TOUCHED: NONE\n"
        f"CHECKS_RUN: {checks}\n"
        "OPEN_RISKS: NONE\nNOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n",
        encoding="utf-8",
    )
    result = classify_closeout(path, tmp_path)
    assert result["schema_validity"] == "valid"
    assert result["content_sufficiency"] == CONTENT_SUFFICIENT
    assert result["closeout_status"] == "evidence_inconsistent"
    assert result["memory_tier"] != "verified_state_update"
