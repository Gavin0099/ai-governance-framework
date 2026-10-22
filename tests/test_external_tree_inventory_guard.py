from __future__ import annotations

import codecs
import io
import json
import subprocess
from pathlib import Path

import pytest

from governance_tools.external_tree_inventory_guard import (
    STATUS_BLOCKED,
    STATUS_PASS,
    STATUS_UNATTRIBUTED_BULK_INVENTORY,
    STATUS_UNREADABLE,
    IdentityConfigError,
    PrePushScanError,
    PrePushUpdate,
    assess_bytes,
    assess_document,
    assess_path,
    load_repository_identities,
    main,
    parse_pre_push_updates,
    scan_pre_push_updates,
)


EXPECTED_REPOSITORY = "example/framework"
ZERO_OID = "0" * 40


def _entries(count: int, *, duplicate: bool = False) -> list[dict[str, object]]:
    return [
        {
            "path": "src/repeated.py" if duplicate else f"src/file-{index:04d}.py",
            "oid": "a" * 40 if duplicate else f"{index:040x}",
            "mode": "100644",
        }
        for index in range(count)
    ]


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.decode("utf-8", errors="replace").strip()


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _commit_bytes(repo: Path, relative_path: str, raw: bytes, message: str) -> str:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    _git(repo, "add", relative_path)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _inventory_bytes(repository: str = "outside/private-consumer") -> bytes:
    return json.dumps({"repository": repository, "entries": _entries(120)}).encode("utf-8")


def _scan(repo: Path, old_oid: str, new_oid: str):
    return scan_pre_push_updates(
        repo,
        (PrePushUpdate("refs/heads/main", new_oid, "refs/heads/main", old_oid),),
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )


def test_external_bulk_tree_inventory_is_blocked() -> None:
    payload = {
        "repository": "outside/private-consumer",
        "entries": _entries(120),
    }

    result = assess_document(
        payload,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_BLOCKED
    assert result.reason == "external_bulk_tree_inventory_detected"
    assert result.findings[0].distinct_entry_count == 120
    assert result.findings[0].source_repository_identities == ("outside/private-consumer",)


def test_same_repository_bulk_inventory_is_not_blocked() -> None:
    payload = {
        "repository": {"owner": "example", "name": "framework"},
        "entries": _entries(120),
    }

    result = assess_document(
        payload,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_PASS
    assert result.reason == "only_expected_repository_bulk_inventories_detected"
    assert result.findings[0].reason == "bulk_tree_inventory_identifies_expected_repository"


def test_small_explicit_blob_binding_set_is_not_blocked() -> None:
    payload = {
        "repository": "outside/private-consumer",
        "authoritative_bindings": _entries(8),
    }

    result = assess_document(
        payload,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_PASS
    assert result.findings == ()
    assert result.reason == "no_bulk_tree_inventory_detected"


def test_nested_reordered_external_inventory_is_still_blocked() -> None:
    entries = [
        {"unrelated": index, "oid": f"{index:040x}", "path": f"nested/{index}.json"}
        for index in range(120)
    ]
    payload = {
        "wrapper": {
            "source_repository": {"url": "https://github.com/outside/private-consumer.git"},
            "nested": {"inventory": entries},
        }
    }

    result = assess_document(
        payload,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_BLOCKED
    assert result.findings[0].json_path == "$.wrapper.nested.inventory"
    assert result.findings[0].source_repository_identities == ("outside/private-consumer",)
    assert result.findings[0].collection_entry_counts[0].distinct_entry_count == 120


def test_split_external_inventory_is_blocked_by_document_aggregate() -> None:
    entries = _entries(20 * 94)
    payload = {
        "repository": "outside/private-consumer",
        "groups": [entries[index : index + 94] for index in range(0, len(entries), 94)],
    }

    result = assess_document(
        payload,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_BLOCKED
    assert result.findings[0].json_path == "$"
    assert result.findings[0].distinct_entry_count == 20 * 94
    assert len(result.findings[0].collection_entry_counts) == 20
    assert {item.distinct_entry_count for item in result.findings[0].collection_entry_counts} == {94}
    assert result.findings[0].collection_entry_counts[0].json_path == "$.groups[0]"
    assert result.findings[0].collection_entry_counts[-1].json_path == "$.groups[19]"


def test_bulk_inventory_without_repository_identity_is_unattributed() -> None:
    result = assess_document(
        {"entries": _entries(120)},
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_UNATTRIBUTED_BULK_INVENTORY
    assert result.reason == "unattributed_bulk_tree_inventory_detected"
    assert result.findings[0].reason == "bulk_tree_inventory_has_no_reliable_repository_identity"


def test_duplicate_path_oid_pairs_do_not_satisfy_distinct_entry_threshold() -> None:
    result = assess_document(
        {
            "repository": "outside/private-consumer",
            "entries": _entries(120, duplicate=True),
        },
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_PASS
    assert result.findings == ()


def test_cli_returns_unreadable_for_unreadable_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_text("{not-json", encoding="utf-8")

    exit_code = main([str(candidate), "--repository-id", EXPECTED_REPOSITORY, "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output[0]["status"] == STATUS_UNREADABLE
    assert output[0]["reason"] == "json_unreadable:JSONDecodeError"


def test_cli_returns_exit_3_for_unattributed_bulk_inventory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    candidate = tmp_path / "unattributed-inventory.json"
    candidate.write_text(json.dumps({"entries": _entries(120)}), encoding="utf-8")

    exit_code = main([str(candidate), "--repository-id", EXPECTED_REPOSITORY, "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert output[0]["status"] == STATUS_UNATTRIBUTED_BULK_INVENTORY
    assert output[0]["reason"] == "unattributed_bulk_tree_inventory_detected"


def test_cli_multi_file_exit_priority(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unreadable = tmp_path / "unreadable.json"
    unattributed = tmp_path / "unattributed.json"
    blocked = tmp_path / "blocked.json"
    unreadable.write_text("{not-json", encoding="utf-8")
    unattributed.write_text(json.dumps({"entries": _entries(120)}), encoding="utf-8")
    blocked.write_text(
        json.dumps({"repository": "outside/private-consumer", "entries": _entries(120)}),
        encoding="utf-8",
    )

    common_args = ["--repository-id", EXPECTED_REPOSITORY, "--format", "json"]
    assert main([str(unreadable), str(unattributed), str(blocked), *common_args]) == 1
    capsys.readouterr()
    assert main([str(unreadable), str(unattributed), *common_args]) == 3
    capsys.readouterr()
    assert main([str(unreadable), *common_args]) == 2


def test_utf8_bom_external_bulk_inventory_is_blocked(tmp_path: Path) -> None:
    candidate = tmp_path / "bom-inventory.json"
    payload = {
        "repository": "outside/private-consumer",
        "entries": _entries(120),
    }
    candidate.write_bytes(json.dumps(payload).encode("utf-8-sig"))

    result = assess_path(
        candidate,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_BLOCKED
    assert result.reason == "external_bulk_tree_inventory_detected"
    assert result.findings[0].distinct_entry_count == 120


@pytest.mark.parametrize(
    ("bom", "encoding"),
    (
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ),
)
def test_utf16_bom_external_bulk_inventory_is_blocked(
    tmp_path: Path,
    bom: bytes,
    encoding: str,
) -> None:
    candidate = tmp_path / f"bom-inventory-{encoding}.json"
    payload = {
        "repository": "outside/private-consumer",
        "entries": _entries(120),
    }
    candidate.write_bytes(bom + json.dumps(payload).encode(encoding))

    result = assess_path(
        candidate,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_BLOCKED
    assert result.reason == "external_bulk_tree_inventory_detected"
    assert result.findings[0].distinct_entry_count == 120


def test_entry_threshold_must_be_positive() -> None:
    with pytest.raises(ValueError, match="entry_threshold must be at least 1"):
        assess_document(
            {"entries": []},
            expected_repository_identities=[EXPECTED_REPOSITORY],
            entry_threshold=0,
        )


@pytest.mark.parametrize(
    "raw",
    [
        codecs.BOM_UTF8 + _inventory_bytes(),
        codecs.BOM_UTF16_LE + _inventory_bytes().decode("utf-8").encode("utf-16-le"),
        codecs.BOM_UTF16_BE + _inventory_bytes().decode("utf-8").encode("utf-16-be"),
    ],
    ids=["utf8-bom", "utf16-le", "utf16-be"],
)
def test_assess_bytes_blocks_supported_encoded_inventory(raw: bytes) -> None:
    result = assess_bytes(raw, expected_repository_identities=[EXPECTED_REPOSITORY])
    assert result.status == STATUS_BLOCKED


def test_assess_bytes_classifies_utf32_as_unreadable() -> None:
    raw = codecs.BOM_UTF32_LE + _inventory_bytes().decode("utf-8").encode("utf-32-le")
    result = assess_bytes(raw, expected_repository_identities=[EXPECTED_REPOSITORY])
    assert result.status == STATUS_UNREADABLE
    assert result.reason == "json_unreadable:UnsupportedEncoding:utf-32"


def test_shared_identity_config_resolves_repository_root_token(tmp_path: Path) -> None:
    config = tmp_path / "identities.json"
    config.write_text(
        json.dumps(
            {
                "schema": "external-tree-inventory-guard-identities.v1",
                "repository_identities": [EXPECTED_REPOSITORY, "@repository-root"],
            }
        ),
        encoding="utf-8",
    )

    identities = load_repository_identities(config, repository_root=tmp_path)

    assert identities == (EXPECTED_REPOSITORY, str(tmp_path.resolve()))


@pytest.mark.parametrize(
    "remote_identity",
    (
        "git@github.com:example/framework.git",
        "git@gitlab.com:example/framework.git",
    ),
)
def test_scp_like_remote_identity_matches_owner_repository(
    remote_identity: str,
) -> None:
    result = assess_document(
        {"repository": "example/framework", "entries": _entries(120)},
        expected_repository_identities=[remote_identity],
    )

    assert result.status == STATUS_PASS
    assert result.reason == "only_expected_repository_bulk_inventories_detected"


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"schema": "wrong", "repository_identities": [EXPECTED_REPOSITORY]},
        {"schema": "external-tree-inventory-guard-identities.v1", "repository_identities": []},
    ],
)
def test_shared_identity_config_fails_closed_when_invalid(
    tmp_path: Path, document: dict[str, object]
) -> None:
    config = tmp_path / "identities.json"
    config.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(IdentityConfigError):
        load_repository_identities(config, repository_root=tmp_path)


def test_pre_push_update_parser_rejects_malformed_input() -> None:
    with pytest.raises(PrePushScanError, match="expected four fields"):
        parse_pre_push_updates(io.StringIO("refs/heads/main only-two\n"))


def test_existing_ref_scans_intermediate_blob_deleted_before_tip(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    baseline = _git(repo, "rev-parse", "HEAD")
    _commit_bytes(repo, "evidence/leak.json", _inventory_bytes(), "add inventory")
    (repo / "evidence" / "leak.json").unlink()
    _git(repo, "add", "-u")
    _git(repo, "commit", "-m", "remove inventory")
    tip = _git(repo, "rev-parse", "HEAD")

    scan = _scan(repo, baseline, tip)

    assert scan.json_blob_count == 1
    assert scan.assessments[0].path == "evidence/leak.json"
    assert scan.assessments[0].result.status == STATUS_BLOCKED


@pytest.mark.parametrize("old_oid", [ZERO_OID, None])
def test_new_and_existing_ref_inventory_are_blocked(tmp_path: Path, old_oid: str | None) -> None:
    repo = _repository(tmp_path)
    baseline = _git(repo, "rev-parse", "HEAD")
    tip = _commit_bytes(repo, "inventory.json", _inventory_bytes(), "inventory")

    scan = _scan(repo, old_oid or baseline, tip)

    assert scan.assessments[-1].result.status == STATUS_BLOCKED


def test_force_push_and_multi_ref_union_deduplicate_json_blob(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    baseline = _git(repo, "rev-parse", "HEAD")
    old = _commit_bytes(repo, "old.json", b'{"old": true}\n', "old branch")
    _git(repo, "reset", "--hard", baseline)
    tip = _commit_bytes(repo, "inventory.json", _inventory_bytes(), "replacement branch")
    updates = (
        PrePushUpdate("refs/heads/a", tip, "refs/heads/a", old),
        PrePushUpdate("refs/heads/b", tip, "refs/heads/b", old),
    )

    scan = scan_pre_push_updates(
        repo,
        updates,
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert scan.update_count == 2
    assert scan.json_blob_count == 1
    assert scan.assessments[0].result.status == STATUS_BLOCKED


def test_rev_list_failure_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    tip = _commit_bytes(repo, "safe.json", b'{"safe": true}\n', "safe")
    original_run = subprocess.run

    def failing_rev_list(command, *args, **kwargs):
        if "rev-list" in command:
            return subprocess.CompletedProcess(command, 9, stdout=b"", stderr=b"broken")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(
        "governance_tools.external_tree_inventory_guard.subprocess.run",
        failing_rev_list,
    )

    with pytest.raises(PrePushScanError, match="git rev-list failed"):
        _scan(repo, old, tip)


def test_cat_file_failure_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    tip = _commit_bytes(repo, "safe.json", b'{"safe": true}\n', "safe")

    class FailedBatch:
        returncode = 9

        def communicate(self, _query: bytes) -> tuple[bytes, bytes]:
            return b"", b"broken"

    original_popen = subprocess.Popen

    def fail_only_batch(command, *args, **kwargs):
        if "--batch" in command:
            return FailedBatch()
        return original_popen(command, *args, **kwargs)

    monkeypatch.setattr(
        "governance_tools.external_tree_inventory_guard.subprocess.Popen",
        fail_only_batch,
    )

    with pytest.raises(PrePushScanError, match="git cat-file --batch failed"):
        _scan(repo, old, tip)


def test_delete_only_update_scans_no_objects(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    scan = _scan(repo, old, ZERO_OID)
    assert scan.json_blob_count == 0
    assert scan.assessments == ()


def test_missing_remote_old_oid_fails_closed_with_fetch_guidance(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    tip = _git(repo, "rev-parse", "HEAD")
    missing = "f" * 40
    with pytest.raises(PrePushScanError, match="run git fetch before pushing"):
        _scan(repo, missing, tip)


def test_non_json_is_ignored_and_safe_json_passes(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    (repo / "inventory.txt").write_bytes(_inventory_bytes())
    (repo / "safe.json").write_text('{"ok": true}\n', encoding="utf-8")
    _git(repo, "add", "inventory.txt", "safe.json")
    _git(repo, "commit", "-m", "safe")
    tip = _git(repo, "rev-parse", "HEAD")

    scan = _scan(repo, old, tip)

    assert scan.json_blob_count == 1
    assert scan.assessments[0].path == "safe.json"
    assert scan.assessments[0].result.status == STATUS_PASS


def test_scanner_reads_committed_blob_not_working_tree(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    tip = _commit_bytes(repo, "inventory.json", _inventory_bytes(), "inventory")
    (repo / "inventory.json").write_text('{"safe": true}\n', encoding="utf-8")

    scan = _scan(repo, old, tip)

    assert scan.assessments[0].result.status == STATUS_BLOCKED


def test_scanner_uses_one_cat_file_batch_and_never_materializes_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    tip = _commit_bytes(repo, "inventory.json", _inventory_bytes(), "inventory")
    original_popen = subprocess.Popen
    calls: list[list[str]] = []

    def recording_popen(command, *args, **kwargs):
        calls.append(list(command))
        return original_popen(command, *args, **kwargs)

    monkeypatch.setattr(
        "governance_tools.external_tree_inventory_guard.subprocess.Popen",
        recording_popen,
    )
    monkeypatch.setattr(Path, "write_bytes", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("materialized")))

    scan = _scan(repo, old, tip)

    assert scan.assessments[0].result.status == STATUS_BLOCKED
    assert [command for command in calls if "--batch" in command] == [
        ["git", "--no-replace-objects", "-C", str(repo), "cat-file", "--batch"]
    ]


def test_json_named_tree_is_rejected_as_unsupported_object(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    (repo / "folder.json").mkdir()
    (repo / "folder.json" / "item.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "folder.json/item.txt")
    _git(repo, "commit", "-m", "json named tree")
    tip = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(PrePushScanError, match="unsupported Git object type tree"):
        _scan(repo, old, tip)


GUARD = "governance_tools.external_tree_inventory_guard"
NEWLINE_JSON = "prefix\nleak.json"


def _force_git_version(monkeypatch: pytest.MonkeyPatch, version: tuple[int, int, int]) -> None:
    monkeypatch.setattr(f"{GUARD}._git_version", lambda: version)


def _mktree(repo: Path, files: dict[bytes, str]) -> str:
    """Build nested trees from {b"dir/name": blob}; one mktree call per directory."""
    here: dict[bytes, str] = {}
    below: dict[bytes, dict[bytes, str]] = {}
    for path, blob in files.items():
        head, slash, rest = path.partition(b"/")
        if slash:
            below.setdefault(head, {})[rest] = blob
        else:
            here[head] = blob
    records = [b"100644 blob " + blob.encode("ascii") + b"\t" + name for name, blob in here.items()]
    records += [b"040000 tree " + _mktree(repo, sub).encode("ascii") + b"\t" + name
                for name, sub in below.items()]
    return _git(repo, "mktree", "-z", input_bytes=b"".join(r + b"\0" for r in records))


def _commit_tree(repo: Path, parent: str, entries: list[tuple[str, str]], message: str) -> str:
    """Commit (path, blob) pairs on top of parent via plumbing.

    ``git mktree -z`` accepts names Git for Windows refuses in the index, such
    as a path containing a newline, so the fixture works on every platform.
    """
    files: dict[bytes, str] = {}
    listing = subprocess.run(["git", "ls-tree", "-r", "-z", parent], cwd=repo,
                             stdout=subprocess.PIPE, check=True).stdout
    for record in listing.split(b"\0"):
        if record:
            meta, _, name = record.partition(b"\t")
            files[name] = meta.split()[2].decode("ascii")
    for path, blob in entries:
        files[path.encode("utf-8")] = blob
    return _git(repo, "commit-tree", _mktree(repo, files), "-p", parent, "-m", message)


def _blob(repo: Path, raw: bytes) -> str:
    return _git(repo, "hash-object", "-w", "--stdin", input_bytes=raw)


def _candidates(repo: Path, old: str, new: str) -> dict[str, set[str]]:
    from governance_tools.external_tree_inventory_guard import _enumerate_json_blob_candidates

    return _enumerate_json_blob_candidates(
        repo, [PrePushUpdate("refs/heads/x", new, "refs/heads/x", old)])


@pytest.fixture
def awkward_paths(tmp_path: Path) -> tuple[Path, str, str, dict[str, str]]:
    """A push range with a newline-named JSON, a spaced JSON, and one blob at two paths."""
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    blobs = {
        NEWLINE_JSON: _blob(repo, b'{"leak": 1}\n'),
        "dir with space/b c.json": _blob(repo, b'{"spaced": 1}\n'),
        "a/b.json": _blob(repo, b'{"shared": 1}\n'),
    }
    first = _commit_tree(repo, old, [(NEWLINE_JSON, blobs[NEWLINE_JSON]),
                                     ("dir with space/b c.json", blobs["dir with space/b c.json"])],
                         "awkward names")
    second = _commit_tree(repo, first, [("a/b.json", blobs["a/b.json"]),
                                        ("copy/b.txt", blobs["a/b.json"])], "same blob twice")
    return repo, old, second, blobs


@pytest.mark.parametrize("version", [(2, 43, 0), (2, 47, 3)])
def test_compat_path_finds_newline_named_json(
    awkward_paths, monkeypatch: pytest.MonkeyPatch, version
) -> None:
    """Review on #228: newline-delimited rev-list output reports this blob as
    'prefix' and the .json is lost; the compat path must still find it."""
    repo, old, new, blobs = awkward_paths
    _force_git_version(monkeypatch, version)
    found = _candidates(repo, old, new)
    assert found[blobs[NEWLINE_JSON]] == {NEWLINE_JSON}
    assert found[blobs["dir with space/b c.json"]] == {"dir with space/b c.json"}
    assert found[blobs["a/b.json"]] == {"a/b.json"}


def test_compat_path_covers_everything_the_nul_path_finds(
    awkward_paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, old, new, _blobs = awkward_paths
    _force_git_version(monkeypatch, (2, 50, 0))
    nul = _candidates(repo, old, new)
    _force_git_version(monkeypatch, (2, 47, 3))
    compat = _candidates(repo, old, new)
    assert nul  # this checkout's git is >= 2.50, so the -z path is real here
    for oid, names in nul.items():
        assert names <= compat.get(oid, set())


def test_newline_named_json_is_scanned_end_to_end_on_compat_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    blob = _blob(repo, _inventory_bytes())
    new = _commit_tree(repo, old, [(NEWLINE_JSON, blob)], "hidden inventory")
    _force_git_version(monkeypatch, (2, 43, 0))
    result = _scan(repo, old, new)
    assert result.json_blob_count == 1
    assert result.assessments[0].path == NEWLINE_JSON
    assert result.assessments[0].result.status == STATUS_BLOCKED


def test_old_git_never_uses_rev_list_z(awkward_paths, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch is by version, not by guessing from the output format."""
    repo, old, new, _blobs = awkward_paths
    _force_git_version(monkeypatch, (2, 43, 0))
    seen: list[list[str]] = []
    original_run = subprocess.run

    def spy(command, *args, **kwargs):
        if isinstance(command, list):
            seen.append([str(part) for part in command])
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(f"{GUARD}.subprocess.run", spy)
    _candidates(repo, old, new)
    rev_lists = [cmd for cmd in seen if "rev-list" in cmd]
    assert rev_lists and all("-z" not in cmd for cmd in rev_lists)


def test_nul_path_refuses_output_without_nul(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A git that claims >= 2.50 but ignores -z must not be parsed any other way."""
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    tip = _commit_bytes(repo, "data/a.json", b'{"safe": true}\n', "safe")
    blob = _git(repo, "rev-parse", f"{tip}:data/a.json")
    _force_git_version(monkeypatch, (2, 50, 0))
    original_run = subprocess.run

    def fake_run(command, *args, **kwargs):
        if isinstance(command, list) and "rev-list" in command:
            return subprocess.CompletedProcess(command, 0, stdout=f"{tip}\n{blob} data/a.json\n".encode(),
                                               stderr=b"")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(f"{GUARD}.subprocess.run", fake_run)
    with pytest.raises(PrePushScanError, match="not NUL-delimited"):
        _candidates(repo, old, tip)


@pytest.mark.parametrize("with_z", [b"zzzz\0", b"path=orphan.json\0", b"\xff\xfe\0"])
def test_malformed_nul_rev_list_output_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_z: bytes
) -> None:
    repo = _repository(tmp_path)
    old = _git(repo, "rev-parse", "HEAD")
    tip = _commit_bytes(repo, "data/a.json", b'{"safe": true}\n', "safe")
    _force_git_version(monkeypatch, (2, 50, 0))
    original_run = subprocess.run

    def fake_run(command, *args, **kwargs):
        if isinstance(command, list) and "rev-list" in command:
            return subprocess.CompletedProcess(command, 0, stdout=with_z, stderr=b"")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(f"{GUARD}.subprocess.run", fake_run)
    with pytest.raises(PrePushScanError, match="git rev-list emitted"):
        _candidates(repo, old, tip)


def test_compat_path_refuses_more_commits_than_its_limit(
    awkward_paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, old, new, _blobs = awkward_paths
    _force_git_version(monkeypatch, (2, 43, 0))
    monkeypatch.setattr(f"{GUARD}._COMPAT_MAX_COMMITS", 1)
    with pytest.raises(PrePushScanError, match="refusing a partial scan"):
        _candidates(repo, old, new)


def test_compat_path_fails_closed_when_a_new_blob_has_no_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ref pointing straight at a blob has no commit tree to name it."""
    repo = _repository(tmp_path)
    blob = _blob(repo, _inventory_bytes())
    _force_git_version(monkeypatch, (2, 43, 0))
    with pytest.raises(PrePushScanError):
        _candidates(repo, ZERO_OID, blob)


def test_git_version_parses_vendor_suffixes(monkeypatch: pytest.MonkeyPatch) -> None:
    from governance_tools.external_tree_inventory_guard import _git_version

    original_run = subprocess.run

    def fake_run(command, *args, **kwargs):
        if command == ["git", "--version"]:
            return subprocess.CompletedProcess(command, 0, stdout=b"git version 2.50.0.windows.1\n",
                                               stderr=b"")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(f"{GUARD}.subprocess.run", fake_run)
    assert _git_version() == (2, 50, 0)


# Review on #228 (P1): remote-tracking refs are not proof of what the push
# destination holds.  New refs are scanned in full, whatever the tracking refs say.

@pytest.mark.parametrize("version", [(2, 43, 0), (2, 50, 0)])
def test_new_ref_scan_ignores_tracking_refs_of_a_different_push_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version
) -> None:
    repo = _repository(tmp_path)
    tip = _commit_bytes(repo, "data/inventory.json", _inventory_bytes(), "inventory")
    # origin fetches from A (whose tracking ref already contains the blob)
    # but pushes to an empty B.
    _git(repo, "remote", "add", "origin", "https://example.invalid/A.git")
    _git(repo, "remote", "set-url", "--push", "origin", "https://example.invalid/B.git")
    _git(repo, "update-ref", "refs/remotes/origin/main", tip)
    _force_git_version(monkeypatch, version)
    result = scan_pre_push_updates(
        repo, (PrePushUpdate("refs/heads/new", tip, "refs/heads/new", ZERO_OID),),
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )
    assert [a.result.status for a in result.assessments] == [STATUS_BLOCKED]


def test_new_ref_scan_ignores_stale_tracking_refs(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    tip = _commit_bytes(repo, "data/inventory.json", _inventory_bytes(), "inventory")
    # A tracking ref left behind after the branch was deleted upstream.
    _git(repo, "remote", "add", "origin", "https://example.invalid/A.git")
    _git(repo, "update-ref", "refs/remotes/origin/deleted-upstream", tip)
    result = scan_pre_push_updates(
        repo, (PrePushUpdate("refs/heads/new", tip, "refs/heads/new", ZERO_OID),),
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )
    assert [a.result.status for a in result.assessments] == [STATUS_BLOCKED]


def test_pre_push_hook_does_not_narrow_scan_by_remote_name() -> None:
    hook = (Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "pre-push").read_text(
        encoding="utf-8")
    assert "--published-remote" not in hook
    assert "--remotes=" not in hook
