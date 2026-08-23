from __future__ import annotations

import codecs
import json
from pathlib import Path

import pytest

from governance_tools.external_tree_inventory_guard import (
    STATUS_BLOCKED,
    STATUS_PASS,
    STATUS_UNATTRIBUTED_BULK_INVENTORY,
    STATUS_UNREADABLE,
    assess_document,
    assess_path,
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
