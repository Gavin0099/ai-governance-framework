from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.external_tree_inventory_guard import (
    STATUS_BLOCKED,
    STATUS_PASS,
    STATUS_UNKNOWN,
    assess_document,
    main,
)


EXPECTED_REPOSITORY = "example/framework"


def _entries(count: int, *, duplicate: bool = False) -> list[dict[str, object]]:
    return [
        {
            "path": "src/repeated.py" if duplicate else f"src/file-{index:04d}.py",
            "oid": "a" * 40 if duplicate else f"{index:040x}",
            "mode": "100644",
        }
        for index in range(count)
    ]


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


def test_bulk_inventory_without_repository_identity_is_unknown() -> None:
    result = assess_document(
        {"entries": _entries(120)},
        expected_repository_identities=[EXPECTED_REPOSITORY],
    )

    assert result.status == STATUS_UNKNOWN
    assert result.reason == "bulk_tree_inventory_source_identity_unknown"
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


def test_cli_returns_unknown_for_unreadable_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_text("{not-json", encoding="utf-8")

    exit_code = main([str(candidate), "--repository-id", EXPECTED_REPOSITORY, "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output[0]["status"] == STATUS_UNKNOWN
    assert output[0]["reason"] == "json_unreadable:JSONDecodeError"


def test_entry_threshold_must_be_positive() -> None:
    with pytest.raises(ValueError, match="entry_threshold must be at least 1"):
        assess_document(
            {"entries": []},
            expected_repository_identities=[EXPECTED_REPOSITORY],
            entry_threshold=0,
        )
