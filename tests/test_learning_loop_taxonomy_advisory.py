import json
from pathlib import Path

from governance_tools.learning_loop_taxonomy_advisory import (
    load_semantic_failure_ids,
    main,
    validate_payload,
)


def test_learning_loop_seed_matrix_uses_layered_taxonomy_shape():
    semantic_ids = load_semantic_failure_ids(Path("governance/SEMANTIC_FAILURE_TAXONOMY.md"))
    payload = json.loads(Path("governance/learning_loop_seed_matrix.v0.1.json").read_text(encoding="utf-8"))

    result = validate_payload(payload, semantic_failure_ids=semantic_ids)

    assert result.ok is True
    assert result.warning_count == 0
    assert result.checked_seeds == 1


def test_advisory_warns_when_failure_kinds_are_used_as_primary_taxonomy():
    payload = {
        "seeds": [
            {
                "id": "bad",
                "semantic_failure": "integration_drift",
                "scenario_type": "stale_assertion",
                "result_disposition": None,
            }
        ]
    }

    result = validate_payload(payload, semantic_failure_ids={"SF-05"})

    assert result.ok is True
    assert result.warning_count == 2
    joined = "\n".join(result.warnings)
    assert "unknown semantic_failure integration_drift" in joined
    assert "scenario_type must not use result_disposition value stale_assertion" in joined


def test_advisory_warns_but_does_not_block_when_result_disposition_prefilled():
    payload = {
        "seeds": [
            {
                "id": "prefilled",
                "semantic_failure": "SF-05",
                "scenario_type": "deterministic_repo_behavior",
                "result_disposition": "stale_assertion",
            }
        ]
    }

    result = validate_payload(payload, semantic_failure_ids={"SF-05"})

    assert result.ok is True
    assert result.warning_count == 1
    assert "result_disposition is prefilled" in result.warnings[0]


def test_advisory_warns_on_legacy_flat_category_field():
    payload = {
        "seeds": [
            {
                "id": "legacy",
                "category": "determinism_replay",
                "semantic_failure": "SF-05",
                "scenario_type": "deterministic_repo_behavior",
                "result_disposition": None,
            }
        ]
    }

    result = validate_payload(payload, semantic_failure_ids={"SF-05"})

    assert result.ok is True
    assert result.warning_count == 1
    assert "legacy category field is not allowed" in result.warnings[0]


def test_advisory_warns_when_seeds_field_is_missing():
    result = validate_payload({}, semantic_failure_ids={"SF-05"})

    assert result.ok is True
    assert result.checked_seeds == 0
    assert result.warning_count == 1
    assert result.warnings == ["matrix.seeds must be a list"]


def test_advisory_warns_when_seeds_field_is_not_a_list():
    result = validate_payload({"seeds": {"id": "not-a-list"}}, semantic_failure_ids={"SF-05"})

    assert result.ok is True
    assert result.checked_seeds == 0
    assert result.warning_count == 1
    assert result.warnings == ["matrix.seeds must be a list"]


def test_advisory_warns_when_seed_entry_is_not_an_object():
    payload = {"seeds": ["not-an-object"]}

    result = validate_payload(payload, semantic_failure_ids={"SF-05"})

    assert result.ok is True
    assert result.checked_seeds == 1
    assert result.warning_count == 1
    assert result.warnings == ["seeds[0] must be an object"]


def test_cli_missing_matrix_is_warning_only(capsys, tmp_path):
    missing = tmp_path / "missing.json"

    exit_code = main(["--matrix", str(missing), "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["ok"] is True
    assert output["checked_seeds"] == 0
    assert output["warning_count"] == 1
    assert "matrix file not found" in output["warnings"][0]


def test_cli_malformed_matrix_is_warning_only(capsys, tmp_path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")

    exit_code = main(["--matrix", str(malformed), "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["ok"] is True
    assert output["checked_seeds"] == 0
    assert output["warning_count"] == 1
    assert "matrix JSON is invalid" in output["warnings"][0]


def test_cli_bom_matrix_is_supported(capsys, tmp_path):
    matrix = tmp_path / "bom.json"
    matrix.write_text(
        json.dumps(
            {
                "seeds": [
                    {
                        "id": "bom",
                        "semantic_failure": "SF-05",
                        "scenario_type": "deterministic_repo_behavior",
                        "result_disposition": None,
                    }
                ]
            }
        ),
        encoding="utf-8-sig",
    )

    exit_code = main(["--matrix", str(matrix), "--format", "json"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["ok"] is True
    assert output["checked_seeds"] == 1
    assert output["warning_count"] == 0
