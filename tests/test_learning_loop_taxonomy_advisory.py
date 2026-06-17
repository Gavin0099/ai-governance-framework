import json
from pathlib import Path

from governance_tools.learning_loop_taxonomy_advisory import (
    load_semantic_failure_ids,
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
