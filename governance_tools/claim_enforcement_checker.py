#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


DISALLOWED_PHRASES = (
    "proven",
    "production-ready",
)

POSTURE_ORDER = {
    "none": 0,
    "bounded_support": 1,
    "partial_falsification": 2,
}


def _load_input(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_posture_stronger(current: str, previous: str) -> bool:
    return POSTURE_ORDER.get(current, -1) > POSTURE_ORDER.get(previous, -1)


def evaluate(payload: dict) -> dict:
    reasons = []
    preconditions = payload.get("preconditions", True)
    scenario_result = payload.get("scenario_result")
    observed = payload.get("observed", "__missing__")

    # Hard rule: precondition failed flow must be not_executed + observed=null
    if preconditions is False:
        hard_rule_ok = scenario_result == "not_executed" and observed is None
        return {
            "result": "pass" if hard_rule_ok else "fail",
            "semantic_drift_risk": False,
            "reasons": [] if hard_rule_ok else [
                "precondition_failed_contract_violation: expected not_executed + observed=null"
            ],
        }

    final_claim = str(payload.get("final_claim", ""))
    claim_level = str(payload.get("claim_level", ""))
    same_evidence = bool(payload.get("same_evidence_as_previous", False))
    posture = str(payload.get("posture", "none"))
    previous_posture = str(payload.get("previous_posture", "none"))

    semantic_drift_risk = False

    if claim_level != "bounded_support":
        semantic_drift_risk = True
        reasons.append("claim_level_stronger_than_allowed")

    lowered = final_claim.lower()
    if any(p in lowered for p in DISALLOWED_PHRASES):
        semantic_drift_risk = True
        reasons.append("disallowed_strong_claim_phrase")

    if same_evidence and _is_posture_stronger(posture, previous_posture):
        semantic_drift_risk = True
        reasons.append("same_evidence_strengthening")

    expected_flag = payload.get("semantic_drift_risk")
    if expected_flag is not None and bool(expected_flag) != semantic_drift_risk:
        reasons.append("input_semantic_drift_risk_mismatch")

    result = "fail" if semantic_drift_risk else "pass"
    return {
        "result": result,
        "semantic_drift_risk": semantic_drift_risk,
        "reasons": reasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args()

    payload = _load_input(Path(args.input))
    out = evaluate(payload)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
