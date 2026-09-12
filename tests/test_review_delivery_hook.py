"""Review-only native hook wiring; no real GitHub calls or merge execution.

Expected outcomes come from PR81's recorded failure, PR80's positive control,
the accepted S1/S2/S3 contracts, and native deny/ask qualification. Replays
exercise the real primitives; only the external acquisition boundary is fake.
Actual Antigravity dispatch/permission behavior is qualified separately.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from governance_tools import review_delivery_hook as hook
from governance_tools.review_evidence import ACQUISITION_QUERY, snapshot_sha256


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/review_evidence"
SCRIPT = ROOT / "governance_tools/review_delivery_hook.py"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def event(command=None, cwd=ROOT):
    if command is None:
        command = f'"{sys.executable}" pr merge 81 --merge'
    return {"toolCall": {"name": "run_command", "args": {
        "CommandLine": command, "Cwd": str(cwd), "WaitMsBeforeAsync": 5000,
    }}, "stepIdx": 1528}


def config_for(number):
    return {"gh_executable": sys.executable,
            "assessment_path": str(FIXTURES / f"pr{number}_assessment.json")}


def details(result):
    assert set(result) == {"decision", "reason"}
    assert result["decision"] in ("deny", "ask")
    decoded = json.loads(result["reason"])
    assert decoded["MERGE_READY"] in ("NO", "NOT_EVALUATED")
    return decoded


def assert_denied(result, gate="UNKNOWN"):
    decoded = details(result)
    assert result["decision"] == "deny"
    assert decoded["REVIEW_GATE"] == gate
    assert decoded["MERGE_READY"] == "NO"
    return decoded


def test_pr81_original_incomplete_acquisition_cannot_become_zero_findings():
    acquire = Mock(return_value=fixture("pr81_incomplete.json"))
    result = hook.evaluate_tool_call(event(), config_for(81), acquire=acquire)
    decoded = assert_denied(result)
    evidence = decoded["checks"]["REVIEW_IDENTITY"]["REVIEW_EVIDENCE"]
    assert evidence["REVIEW_COMPLETENESS"] == "INSUFFICIENT"
    assert evidence["FINDINGS"] == "UNKNOWN"
    acquire.assert_called_once_with(sys.executable, str(ROOT), 81)


def test_pr81_actual_final_head_rejects_older_review_on_delivery_path():
    result = hook.evaluate_tool_call(
        event(), config_for(81), acquire=Mock(return_value=fixture("pr81_complete.json")))
    identity = assert_denied(result)["checks"]["REVIEW_IDENTITY"]
    assert identity["CURRENT_PR_HEAD"] == "64027f90ef7c1b4255e9b74503e0d97869bcf348"
    assert identity["REVIEWED_HEAD"] == "233430f1b71de34db6fde45916dec41eb150d278"
    assert identity["MATCH"] == "NO"
    assert identity["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "COMPLETE"


def test_pr80_positive_control_passes_only_review_and_never_executes_merge():
    acquire = Mock(return_value=fixture("pr80_complete.json"))
    with patch.object(hook.subprocess, "run", side_effect=AssertionError("must not execute merge")):
        result = hook.evaluate_tool_call(event(f'"{sys.executable}" pr merge 80 --merge'),
                                         config_for(80), acquire=acquire)
    decoded = details(result)
    assert result["decision"] == "ask"
    assert decoded["REVIEW_GATE"] == "PASS"
    assert decoded["MERGE_READY"] == "NOT_EVALUATED"
    assert decoded["checks"]["UNRESOLVED_P0"] == 0
    assert decoded["checks"]["UNRESOLVED_P1"] == 0
    assert decoded["checks"]["REVIEW_IDENTITY"]["REVIEW_EVIDENCE"]["FINDINGS"] == "UNKNOWN"
    assert "CI and owner authorization remain separate" in decoded["reason"]
    acquire.assert_called_once_with(sys.executable, str(ROOT), 80)


def test_synthetic_same_head_pr81_retains_real_p1_and_blocks(tmp_path):
    snapshot = fixture("pr81_complete.json")
    assessment = fixture("pr81_assessment.json")
    pr = snapshot["data"]["repository"]["pullRequest"]
    pr["headRefOid"] = pr["reviews"]["nodes"][0]["commit"]["oid"]
    snapshot["test_scenario"] = "SYNTHETIC same HEAD, not PR81 historical final state"
    assessment["source"] = "Synthetic adapter replay carrying the explicitly assessed PR81 P1"
    assessment["snapshot_sha256"] = snapshot_sha256(snapshot)
    ledger = tmp_path / "explicit-assessment.json"
    ledger.write_text(json.dumps(assessment), encoding="utf-8")
    config = {**config_for(81), "assessment_path": str(ledger)}
    result = hook.evaluate_tool_call(event(), config, acquire=Mock(return_value=snapshot))
    checks = assert_denied(result, "BLOCKED")["checks"]
    assert checks["REVIEW_IDENTITY"]["MATCH"] == "YES"
    assert checks["UNRESOLVED_P1"] == 1
    assert checks["BLOCKING_FINDING_IDS"] == ["github-inline-3994999882"]


def test_live_changed_head_invalidates_previously_matching_pr80_assessment():
    snapshot = fixture("pr80_complete.json")
    snapshot["data"]["repository"]["pullRequest"]["headRefOid"] = "64027f90ef7c1b4255e9b74503e0d97869bcf348"
    result = hook.evaluate_tool_call(event(f'"{sys.executable}" pr merge 80 --merge'), config_for(80),
                                     acquire=Mock(return_value=snapshot))
    assert assert_denied(result)["checks"]["REVIEW_IDENTITY"]["MATCH"] == "NO"


def test_live_changed_body_cannot_reuse_or_repair_assessment_digest():
    snapshot = fixture("pr80_complete.json")
    snapshot["data"]["repository"]["pullRequest"]["reviews"]["nodes"][0]["body"] += "\nNew evidence"
    ledger_path = Path(config_for(80)["assessment_path"])
    before = ledger_path.read_bytes()
    result = hook.evaluate_tool_call(event(f'"{sys.executable}" pr merge 80 --merge'), config_for(80),
                                     acquire=Mock(return_value=snapshot))
    checks = assert_denied(result)["checks"]
    assert checks["REVIEW_IDENTITY"]["MATCH"] == "YES"
    assert checks["UNRESOLVED_P1"] == "UNKNOWN"
    assert ledger_path.read_bytes() == before


@pytest.mark.parametrize("ledger_state", ["absent", "relative", "missing_file", "invalid_json", "wrong_shape"])
def test_missing_or_invalid_ledger_is_unknown_not_a_zero_finding_claim(tmp_path, ledger_state):
    config = config_for(80)
    if ledger_state == "absent":
        del config["assessment_path"]
    elif ledger_state == "relative":
        config["assessment_path"] = "pr80_assessment.json"
    else:
        ledger = tmp_path / "assessment.json"
        config["assessment_path"] = str(ledger)
        if ledger_state != "missing_file":
            ledger.write_text("{" if ledger_state == "invalid_json" else "[]", encoding="utf-8")
    result = hook.evaluate_tool_call(event(f'"{sys.executable}" pr merge 80 --merge'), config,
                                     acquire=Mock(return_value=fixture("pr80_complete.json")))
    checks = assert_denied(result)["checks"]
    assert checks["UNRESOLVED_P0"] == checks["UNRESOLVED_P1"] == "UNKNOWN"


@pytest.mark.parametrize("command", ["git status --short", "gh pr view 81 --comments",
                                    "python deliver.py", 'bash -c "gh pr merge 81 --merge"'])
def test_unrelated_and_out_of_scope_wrappers_do_not_read_ledger_or_acquire(command):
    acquire = Mock(side_effect=AssertionError("unrelated command must not acquire"))
    with patch.object(Path, "read_text", side_effect=AssertionError("must not read ledger")):
        result = hook.evaluate_tool_call(event(command), config_for(81), acquire=acquire)
    decoded = details(result)
    assert result["decision"] == "ask"
    assert decoded["REVIEW_GATE"] == decoded["MERGE_READY"] == "NOT_EVALUATED"
    assert "checks" not in decoded
    acquire.assert_not_called()


def test_other_native_tool_keeps_standard_permissions_without_loading_config():
    result = hook.evaluate_tool_call({"toolCall": {"name": "view_file"}}, None,
                                     acquire=Mock(side_effect=AssertionError("must not acquire")))
    assert result["decision"] == "ask"
    assert details(result)["REVIEW_GATE"] == "NOT_EVALUATED"


@pytest.mark.parametrize("bad_event", [None, [], {}, {"toolCall": []},
    {"toolCall": {"name": "run_command"}},
    {"toolCall": {"name": "run_command", "args": {"CommandLine": None}}}])
def test_invalid_native_event_denies_with_a_valid_native_response(bad_event):
    acquire = Mock()
    assert_denied(hook.evaluate_tool_call(bad_event, config_for(81), acquire=acquire))
    acquire.assert_not_called()


@pytest.mark.parametrize("bad_config", [None, [], {}, {"gh_executable": ""}, {"gh_executable": 123}])
def test_missing_executable_configuration_denies_without_acquisition(bad_config):
    acquire = Mock()
    assert_denied(hook.evaluate_tool_call(event(), bad_config, acquire=acquire))
    acquire.assert_not_called()


@pytest.mark.parametrize("arguments", ["", "feature-branch --merge", "0 --merge",
    "2147483648 --merge", "81 --auto", "81 --merge -R another/repo",
    "81 --merge; echo done"])
def test_configured_executable_with_unsupported_direct_merge_denies_without_acquisition(arguments):
    command = f'"{sys.executable}" pr merge {arguments}'.rstrip()
    acquire = Mock()
    assert_denied(hook.evaluate_tool_call(event(command), config_for(81), acquire=acquire))
    acquire.assert_not_called()


@pytest.mark.parametrize("arguments", ["--squash", "--rebase --delete-branch",
    "--merge --match-head-commit c3eab1c7aafbc56a6fb904dc653733afbfdd0024"])
def test_supported_existing_merge_options_still_consume_review_predicates(arguments):
    command = f'"{sys.executable}" pr merge 80 {arguments}'
    acquire = Mock(return_value=fixture("pr80_complete.json"))
    result = hook.evaluate_tool_call(event(command), config_for(80), acquire=acquire)
    assert details(result)["REVIEW_GATE"] == "PASS"
    assert result["decision"] == "ask"
    acquire.assert_called_once_with(sys.executable, str(ROOT), 80)


@pytest.mark.parametrize("command", [
    "gh pr merge 81 --merge",
    "gh.exe pr merge 81 --merge",
    '& "D:/other/GitHub CLI/gh.exe" pr merge 81 --merge',
    '& "D:/other/gh.exe" pr merge 81 --merge',
])
def test_bare_or_mismatched_gh_executable_denies_without_acquisition(command):
    acquire = Mock(side_effect=AssertionError("unbound executable must not acquire"))
    result = hook.evaluate_tool_call(event(command), config_for(81), acquire=acquire)
    decoded = assert_denied(result)
    assert "configured absolute executable" in decoded["reason"]
    acquire.assert_not_called()


@pytest.mark.parametrize("configured_path,invocation", [
    ("C:/Program Files/GitHub CLI/gh.exe", '& "C:\\Program Files\\GitHub CLI\\gh.exe"'),
    ("C:\\Program Files\\GitHub CLI\\gh.exe", '& "C:/Program Files/GitHub CLI/gh.exe"'),
    ("C:/Program Files/GitHub CLI/gh.exe", '&"C:\\Program Files\\GitHub CLI\\gh.exe"'),
    ("C:\\Program Files\\GitHub CLI\\gh.exe", "&'C:/Program Files/GitHub CLI/gh.exe'"),
])
@pytest.mark.parametrize("number,decision,gate,match", [
    (81, "deny", "UNKNOWN", "NO"),
    (80, "ask", "PASS", "YES"),
])
def test_equivalent_windows_paths_and_powershell_call_operator_cannot_skip_review(
        configured_path, invocation, number, decision, gate, match):
    # These are supported direct invocations, including the valid &"path" form.
    # A separator spelling change must not turn an unqualified review into an
    # unrelated-command response that bypasses acquisition entirely.
    config = {**config_for(number), "gh_executable": configured_path}
    acquire = Mock(return_value=fixture(f"pr{number}_complete.json"))
    result = hook.evaluate_tool_call(event(f"{invocation} pr merge {number} --merge"),
                                     config, acquire=acquire)
    decoded = details(result)
    assert result["decision"] == decision
    assert decoded["REVIEW_GATE"] == gate
    assert decoded["checks"]["REVIEW_IDENTITY"]["MATCH"] == match
    assert decoded["MERGE_READY"] == ("NO" if number == 81 else "NOT_EVALUATED")
    acquire.assert_called_once_with(configured_path, str(ROOT), number)


@pytest.mark.parametrize("failure", [FileNotFoundError("missing gh"), ValueError("bad JSON"),
    subprocess.TimeoutExpired("gh", 20), subprocess.CalledProcessError(1, "gh")])
def test_live_acquisition_failures_deny_instead_of_falling_back_to_cached_evidence(failure):
    result = hook.evaluate_tool_call(event(), config_for(81), acquire=Mock(side_effect=failure))
    checks = assert_denied(result)["checks"]
    assert checks["REVIEW_IDENTITY"]["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "INSUFFICIENT"
    assert checks["UNRESOLVED_P1"] == "UNKNOWN"


def test_acquisition_uses_only_readonly_query_and_the_proposed_command_cwd(tmp_path):
    snapshot = fixture("pr80_complete.json")
    completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(snapshot), stderr="")
    with patch.object(hook.subprocess, "run", return_value=completed) as run:
        result = hook.acquire_snapshot(sys.executable, str(tmp_path), 80)
    assert result == snapshot
    argv = run.call_args.args[0]
    assert argv == [str(Path(sys.executable)), "api", "graphql", "-f", "query=" + ACQUISITION_QUERY,
                    "-F", "owner={owner}", "-F", "name={repo}", "-F", "number=80"]
    options = run.call_args.kwargs
    assert options["cwd"] == str(tmp_path)
    assert options["shell"] is False
    assert options["check"] is True
    assert options["timeout"] == 20
    assert "mutation" not in ACQUISITION_QUERY
    assert "merge" not in argv
    run.assert_called_once()


@pytest.mark.parametrize("stdout", ["{", "not JSON"])
def test_invalid_json_from_actual_acquisition_boundary_reaches_native_deny(stdout, tmp_path):
    completed = subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")
    with patch.object(hook.subprocess, "run", return_value=completed):
        result = hook.evaluate_tool_call(event(cwd=tmp_path), config_for(81))
    assert_denied(result)


@pytest.mark.parametrize("path_kind", ["relative_executable", "missing_executable", "directory_executable",
                                       "relative_cwd", "missing_cwd", "file_cwd"])
def test_invalid_executable_or_cwd_denies_before_spawning(path_kind, tmp_path):
    config = config_for(81)
    native_event = event(cwd=tmp_path)
    if path_kind == "relative_executable":
        config["gh_executable"] = "gh.exe"
    elif path_kind == "missing_executable":
        config["gh_executable"] = str(tmp_path / "missing-gh.exe")
    elif path_kind == "directory_executable":
        config["gh_executable"] = str(tmp_path)
    elif path_kind == "relative_cwd":
        native_event["toolCall"]["args"]["Cwd"] = "."
    elif path_kind == "missing_cwd":
        native_event["toolCall"]["args"]["Cwd"] = str(tmp_path / "missing")
    else:
        native_event["toolCall"]["args"]["Cwd"] = sys.executable
    native_event["toolCall"]["args"]["CommandLine"] = (
        f'"{config["gh_executable"]}" pr merge 81 --merge')
    with patch.object(hook.subprocess, "run", side_effect=AssertionError("must not spawn")) as run:
        result = hook.evaluate_tool_call(native_event, config)
    assert_denied(result)
    run.assert_not_called()


@pytest.mark.parametrize("raw_event,decision,gate", [
    (json.dumps(event("git status --short")), "ask", "NOT_EVALUATED"),
    ("{", "deny", "UNKNOWN"),
    ("null", "deny", "UNKNOWN"),
])
def test_absolute_script_cli_with_isolated_python_works_from_other_cwd(tmp_path, raw_event, decision, gate):
    config_path = tmp_path / "hook-config.json"
    config_path.write_text(json.dumps(config_for(81)), encoding="utf-8")
    # A consumer-local package must not intercept imports under Python -I.
    poison = tmp_path / "governance_tools"
    poison.mkdir()
    (poison / "__init__.py").write_text("raise AssertionError('consumer import used')", encoding="utf-8")
    completed = subprocess.run([sys.executable, "-I", str(SCRIPT), "--config", str(config_path)],
                               input=raw_event, text=True, capture_output=True, encoding="utf-8",
                               cwd=str(tmp_path), timeout=20, check=False)
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["decision"] == decision
    assert details(result)["REVIEW_GATE"] == gate
