from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PROBE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROBE_ROOT))

from gate3_arm_d_validator_probe import (  # noqa: E402
    CommandResult,
    LEAKAGE_REVIEW_REQUIRED,
    ChangedRange,
    ProbeFailure,
    audit_forbidden_markers,
    build_stryker_config,
    classify_execution,
    derive_changed_production_ranges,
    materialize_synthetic_repository,
    merkle_root,
    parse_changed_production_ranges,
    remove_owned_workspace,
    summarize_mutation_report,
    validate_output_policy,
    _read_json,
    _require_mapping,
    _verify_package_lock,
)


def _contract() -> dict[str, object]:
    return _require_mapping(_read_json(PROBE_ROOT / "probe-contract.json"), label="contract")


def _output_policy() -> dict[str, object]:
    return _require_mapping(
        _read_json(PROBE_ROOT / "output-policy.json"),
        label="output policy",
    )


def test_package_lock_matches_all_exact_contract_pins() -> None:
    contract = _contract()
    package_lock = _require_mapping(
        _read_json(PROBE_ROOT / "synthetic-consumer" / "package-lock.json"),
        label="package lock",
    )

    _verify_package_lock(
        package_lock,
        _require_mapping(contract["packages"], label="packages"),
    )


def test_zero_context_diff_selects_only_changed_production_ranges() -> None:
    diff = """diff --git a/src/classify.ts b/src/classify.ts
--- a/src/classify.ts
+++ b/src/classify.ts
@@ -1,0 +2,2 @@
+first
+second
diff --git a/test/classify.test.ts b/test/classify.test.ts
--- a/test/classify.test.ts
+++ b/test/classify.test.ts
@@ -1,0 +2,3 @@
+test one
+test two
+test three
diff --git a/src/generated/value.ts b/src/generated/value.ts
--- a/src/generated/value.ts
+++ b/src/generated/value.ts
@@ -1,0 +2 @@
+generated
"""
    policy = _require_mapping(_contract()["scope_policy"], label="scope")

    assert parse_changed_production_ranges(diff, policy=policy) == (
        ChangedRange("src/classify.ts", 2, 3),
    )


def test_empty_or_nonproduction_diff_fails_closed() -> None:
    policy = _require_mapping(_contract()["scope_policy"], label="scope")

    with pytest.raises(ProbeFailure, match="no production mutation range"):
        parse_changed_production_ranges(
            "+++ b/test/only.test.ts\n@@ -0,0 +1 @@\n+test\n",
            policy=policy,
        )


def test_materialized_synthetic_history_derives_only_the_added_source_line(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "consumer"
    baseline = materialize_synthetic_repository(
        repository,
        package_root=PROBE_ROOT / "synthetic-consumer",
    )
    policy = _require_mapping(_contract()["scope_policy"], label="scope")

    ranges = derive_changed_production_ranges(
        repository,
        baseline_commit=baseline,
        policy=policy,
    )

    assert ranges == (ChangedRange("src/classify.ts", 2, 2),)
    assert all("test" not in item.path for item in ranges)


def test_owned_workspace_cleanup_handles_readonly_git_objects(tmp_path: Path) -> None:
    workspace = tmp_path / "owned"
    marker = workspace / ".gate3-arm-d-validator-probe-owned"
    readonly = workspace / ".git" / "objects" / "aa" / "synthetic"
    readonly.parent.mkdir(parents=True)
    marker.write_text("owned\n", encoding="utf-8")
    readonly.write_text("synthetic\n", encoding="utf-8")
    readonly.chmod(0o444)

    remove_owned_workspace(workspace)

    assert not workspace.exists()


def test_cleanup_refuses_workspace_without_ownership_marker(tmp_path: Path) -> None:
    workspace = tmp_path / "unowned"
    workspace.mkdir()

    with pytest.raises(ProbeFailure, match="unowned"):
        remove_owned_workspace(workspace)

    assert workspace.exists()


def test_generated_config_contains_only_diff_derived_targets() -> None:
    template = _require_mapping(
        _read_json(PROBE_ROOT / "stryker.config.template.json"),
        label="template",
    )
    config = json.loads(
        build_stryker_config(
            template,
            (ChangedRange("src/classify.ts", 2, 2),),
        )
    )

    assert config["mutate"] == ["src/classify.ts:2-2"]
    assert not any("test" in target for target in config["mutate"])


@pytest.mark.parametrize(
    ("result", "report_exists", "expected"),
    (
        (CommandResult(0, b"", b"", 1), True, "COMPLETE"),
        (CommandResult(0, b"", b"", 1), False, "PARTIAL"),
        (CommandResult(7, b"", b"", 1), False, "ERROR"),
        (CommandResult(-1, b"", b"", 1, timed_out=True), False, "TIMEOUT"),
    ),
)
def test_execution_classification_fails_closed(
    result: CommandResult,
    report_exists: bool,
    expected: str,
) -> None:
    assert classify_execution(result, report_exists=report_exists) == expected


def test_mutation_report_is_reduced_to_aggregate_feedback() -> None:
    report = {
        "files": {
            "src/synthetic.ts": {
                "mutants": [
                    {
                        "id": "0",
                        "status": "Killed",
                        "mutatorName": "EqualityOperator",
                        "location": {"start": {"line": 2, "column": 3}},
                        "replacement": "synthetic detail",
                    },
                    {
                        "id": "1",
                        "status": "Survived",
                        "mutatorName": "StringLiteral",
                        "location": {"start": {"line": 2, "column": 9}},
                        "replacement": "synthetic detail",
                    },
                ]
            }
        }
    }

    summary = summarize_mutation_report(report)

    assert summary == {
        "file_count": 1,
        "mutant_count": 2,
        "status_counts": {"Killed": 1, "Survived": 1},
        "mutator_counts": {"EqualityOperator": 1, "StringLiteral": 1},
        "surviving_feedback_observed": True,
    }
    serialized = json.dumps(summary, sort_keys=True)
    assert "src/synthetic.ts" not in serialized
    assert "location" not in serialized
    assert "replacement" not in serialized


def test_output_policy_rejects_nested_mutant_details() -> None:
    result = {
        "schema_version": "synthetic",
        "status": "synthetic",
        "runtime": {},
        "scope": {},
        "mutation": {"mutants": []},
        "failure_probes": {},
        "digests": {},
        "merkle_root": "0" * 64,
        "diagnostics": [],
        "claim_ceiling": "synthetic",
    }

    with pytest.raises(ProbeFailure) as exc_info:
        validate_output_policy(result, _output_policy())

    assert exc_info.value.status == LEAKAGE_REVIEW_REQUIRED


def test_forbidden_marker_audit_is_case_insensitive() -> None:
    assert audit_forbidden_markers(
        (b"safe synthetic output", b"UNEXPECTED-SENTINEL"),
        markers=("unexpected-sentinel", "absent-sentinel"),
    ) == ("unexpected-sentinel",)


def test_merkle_root_is_order_independent_and_content_sensitive() -> None:
    first = merkle_root({"b": "2" * 64, "a": "1" * 64})
    reordered = merkle_root({"a": "1" * 64, "b": "2" * 64})
    changed = merkle_root({"a": "1" * 64, "b": "3" * 64})

    assert first == reordered
    assert first != changed


def test_probe_directory_contains_no_real_consumer_fixture_tree() -> None:
    tracked_fixture_files = sorted(
        path.relative_to(PROBE_ROOT).as_posix()
        for path in PROBE_ROOT.rglob("*")
        if path.is_file()
    )

    assert all("node_modules" not in path for path in tracked_fixture_files)
    assert all("reports/" not in path for path in tracked_fixture_files)
    assert tracked_fixture_files.count("synthetic-consumer/package.json") == 1
    assert tracked_fixture_files.count("synthetic-consumer/package-lock.json") == 1
