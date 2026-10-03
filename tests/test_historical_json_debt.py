"""Exact-blob operator acknowledgements never exclude inventory history."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from governance_tools.external_tree_inventory_guard import (
    HISTORICAL_DEBT_FILENAME, HISTORICAL_DEBT_SCHEMA,
    HistoricalJsonDebt, PrePushScanError, PrePushUpdate,
    load_historical_json_debt, main, scan_pre_push_updates,
)
from tests.test_external_tree_inventory_guard import (
    EXPECTED_REPOSITORY, ZERO_OID, _commit_bytes, _git, _inventory_bytes, _repository,
)


def _policy(repo: Path, baseline: str, oid: str, path: str = "old.json") -> Path:
    target = repo / ".git" / "hooks" / HISTORICAL_DEBT_FILENAME
    target.write_text(json.dumps({
        "schema": HISTORICAL_DEBT_SCHEMA, "repository_id": EXPECTED_REPOSITORY,
        "baseline_commit": baseline, "review_reference": "independent-review:fixture-policy",
        "blobs": [{"oid": oid, "path": path}],
    }), encoding="utf-8")
    return target


def _fixture(tmp_path: Path):
    repo = _repository(tmp_path)
    _commit_bytes(repo, "old.json", b'{"title":\n<<<<<<< HEAD\n', "historical conflict")
    baseline = _git(repo, "rev-parse", "HEAD")
    oid = _git(repo, "rev-parse", "HEAD:old.json")
    _commit_bytes(repo, "old.json", b'{"title":"repaired"}\n', "repair current projection")
    tip = _git(repo, "rev-parse", "HEAD")
    return repo, baseline, oid, tip


def _scan(repo: Path, tip: str, policy: Path | None):
    debt = load_historical_json_debt(policy, repository_root=repo,
        expected_repository_identities=[EXPECTED_REPOSITORY]) if policy else None
    return scan_pre_push_updates(repo, (PrePushUpdate("refs/heads/new", tip, "refs/heads/new", ZERO_OID),),
        expected_repository_identities=[EXPECTED_REPOSITORY], historical_debt=debt)


def test_full_history_stays_strict_without_installed_policy(tmp_path: Path):
    repo, _baseline, _oid, tip = _fixture(tmp_path)
    assert {a.result.status for a in _scan(repo, tip, None).assessments} == {"UNREADABLE", "PASS"}


def test_only_exact_historical_parse_failure_is_acknowledged(tmp_path: Path):
    repo, baseline, oid, tip = _fixture(tmp_path)
    scan = _scan(repo, tip, _policy(repo, baseline, oid))
    assert scan.json_blob_count == 2
    assert [(a.oid, a.result.status) for a in scan.assessments if a.oid == oid] == [(oid, "ACKNOWLEDGED_UNREADABLE")]


@pytest.mark.parametrize("raw,expected", [(b'{"new": invalid}', "UNREADABLE"),
    (_inventory_bytes(), "BLOCKED"),
    (json.dumps({"entries": [{"path": f"x/{i}", "oid": f"{i:040x}"} for i in range(120)]}).encode(), "UNATTRIBUTED_BULK_INVENTORY")])
def test_new_bad_blob_still_blocks_when_deleted_before_tip(tmp_path: Path, raw: bytes, expected: str):
    repo, baseline, oid, _tip = _fixture(tmp_path)
    policy = _policy(repo, baseline, oid)
    _commit_bytes(repo, "new.json", raw, "new failure")
    (repo / "new.json").unlink()
    _git(repo, "add", "-u")
    _git(repo, "commit", "-m", "remove new failure")
    scan = _scan(repo, _git(repo, "rev-parse", "HEAD"), policy)
    assert expected in {a.result.status for a in scan.assessments}


@pytest.mark.parametrize("case", ["identity", "oid", "path", "missing_baseline", "nonancestor", "blob_baseline", "tag_baseline", "empty_review", "duplicate", "malformed"])
def test_invalid_policy_fails_closed(tmp_path: Path, case: str):
    repo, baseline, oid, tip = _fixture(tmp_path)
    policy = _policy(repo, baseline, oid)
    document = json.loads(policy.read_text())
    if case == "identity": document["repository_id"] = "another/repo"
    if case == "oid": document["blobs"][0]["oid"] = "f" * 40
    if case == "path": document["blobs"][0]["path"] = "other.json"
    if case == "missing_baseline": document["baseline_commit"] = "e" * 40
    if case == "blob_baseline": document["baseline_commit"] = oid
    if case == "tag_baseline":
        _git(repo, "tag", "-a", "baseline", baseline, "-m", "tagged baseline")
        document["baseline_commit"] = _git(repo, "rev-parse", "refs/tags/baseline")
    if case == "nonancestor":
        later = _commit_bytes(repo, "later.txt", b"later", "later")
        document["baseline_commit"] = later
    if case == "empty_review": document["review_reference"] = ""
    if case == "duplicate": document["blobs"] *= 2
    policy.write_text("{invalid" if case == "malformed" else json.dumps(document), encoding="utf-8")
    with pytest.raises(PrePushScanError): _scan(repo, tip, policy)


@pytest.mark.parametrize("raw", [b'{"safe":true}', _inventory_bytes(),
    json.dumps({"entries": [{"path": f"x/{i}", "oid": f"{i:040x}"} for i in range(120)]}).encode()])
def test_valid_json_cannot_be_registered_as_unreadable_debt(tmp_path: Path, raw: bytes):
    repo = _repository(tmp_path)
    baseline = _commit_bytes(repo, "old.json", raw, "valid JSON")
    oid = _git(repo, "rev-parse", "HEAD:old.json")
    with pytest.raises(PrePushScanError, match="not UNREADABLE"):
        _scan(repo, baseline, _policy(repo, baseline, oid))


def test_worktree_policy_is_rejected_and_does_not_supply_allowance(tmp_path: Path):
    repo, baseline, oid, tip = _fixture(tmp_path)
    installed = _policy(repo, baseline, oid)
    worktree = repo / HISTORICAL_DEBT_FILENAME
    worktree.write_bytes(installed.read_bytes())
    installed.unlink()
    with pytest.raises(PrePushScanError, match="fixed private hook file"):
        _scan(repo, tip, worktree)
    assert "UNREADABLE" in {a.result.status for a in _scan(repo, tip, None).assessments}


def test_cli_reports_acknowledged_debt_and_keeps_blocker(tmp_path: Path, monkeypatch, capsys):
    repo, baseline, oid, tip = _fixture(tmp_path)
    policy = _policy(repo, baseline, oid)
    monkeypatch.setattr("sys.stdin", io.StringIO(f"refs/heads/new {tip} refs/heads/new {ZERO_OID}\n"))
    args = ["--pre-push-updates", "--repo-root", str(repo), "--repository-id", EXPECTED_REPOSITORY,
            "--historical-json-debt-policy", str(policy)]
    assert main(args) == 0
    output = capsys.readouterr().out
    assert oid in output and "ACKNOWLEDGED_UNREADABLE" in output and "json_blobs=2" in output
    tip = _commit_bytes(repo, "new.json", b"{invalid", "new bad JSON")
    monkeypatch.setattr("sys.stdin", io.StringIO(f"refs/heads/new {tip} refs/heads/new {ZERO_OID}\n"))
    assert main(args) == 2
    output = capsys.readouterr().out
    assert "ACKNOWLEDGED_UNREADABLE" in output and "status: UNREADABLE" in output


def test_git_selectors_and_replace_objects_cannot_hide_bad_blob(tmp_path: Path, monkeypatch):
    repo, baseline, oid, tip = _fixture(tmp_path)
    policy = _policy(repo, baseline, oid)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other = _repository(other_dir)
    replacement = _commit_bytes(repo, "new.json", b"{invalid", "new bad JSON")
    new_oid = _git(repo, "rev-parse", "HEAD:new.json")
    safe_oid = _git(repo, "hash-object", "-w", "old.json")
    _git(repo, "replace", new_oid, safe_oid)
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    scan = _scan(repo, replacement, policy)
    assert [(a.oid, a.result.status) for a in scan.assessments if a.oid == new_oid] == [(new_oid, "UNREADABLE")]


def test_policy_applies_to_linked_worktree_using_common_hooks(tmp_path: Path):
    repo, baseline, oid, tip = _fixture(tmp_path)
    policy = _policy(repo, baseline, oid)
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", "--detach", str(linked), tip)
    assert "ACKNOWLEDGED_UNREADABLE" in {a.result.status for a in _scan(linked, tip, policy).assessments}


def test_multi_ref_force_push_and_deletion_preserve_policy_boundary(tmp_path: Path):
    repo, baseline, oid, tip = _fixture(tmp_path)
    debt = load_historical_json_debt(_policy(repo, baseline, oid), repository_root=repo,
        expected_repository_identities=[EXPECTED_REPOSITORY])
    updates = (
        PrePushUpdate("refs/heads/a", tip, "refs/heads/a", baseline),
        PrePushUpdate("refs/heads/b", tip, "refs/heads/b", ZERO_OID),
        PrePushUpdate("(delete)", ZERO_OID, "refs/heads/c", tip),
    )
    scan = scan_pre_push_updates(repo, updates, expected_repository_identities=[EXPECTED_REPOSITORY], historical_debt=debt)
    assert scan.update_count == 3 and scan.json_blob_count == 2
    assert sum(a.result.status == "ACKNOWLEDGED_UNREADABLE" for a in scan.assessments) == 1
    unrelated_tip = _git(repo, "rev-parse", f"{baseline}^")
    with pytest.raises(PrePushScanError, match="ancestor of every pushed tip"):
        scan_pre_push_updates(repo, updates + (PrePushUpdate("refs/heads/d", unrelated_tip, "refs/heads/d", tip),),
            expected_repository_identities=[EXPECTED_REPOSITORY], historical_debt=debt)
