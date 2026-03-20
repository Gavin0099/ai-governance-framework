import json
from pathlib import Path

from governance_tools.decision_model_loader import (
    DECISION_MODEL_PATH,
    build_runtime_policy_ref,
    decision_model_version,
    required_evidence_kinds,
    violation_verdict_impact,
)


def test_decision_model_loader_reads_model_version_and_policy_ref():
    payload = json.loads(DECISION_MODEL_PATH.read_text(encoding="utf-8"))

    assert decision_model_version() == payload["version"]
    assert build_runtime_policy_ref() == {
        "governance_runtime_decision_model": payload["version"],
        "artifact_schema_version": "1.0",
        "runtime_version": f"v{payload['version']}-{payload['status']}-runtime",
    }


def test_decision_model_loader_reads_required_evidence_and_violation_impacts():
    assert {"sdv-text", "public-api-diff", "domain-validator-result"} <= required_evidence_kinds()
    assert violation_verdict_impact("missing_required_evidence", "record-only") == "escalate"
    assert violation_verdict_impact("invalid_evidence_schema", "record-only") == "stop"
