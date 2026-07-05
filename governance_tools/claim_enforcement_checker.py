#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path


DISALLOWED_PHRASES = (
    "proven",
    "production-ready",
)

# Lexical strength markers used ONLY to detect a mismatch between a
# self-declared restrained claim_level (bounded/parity) and claim text that
# asserts absolute/universal strength. This is a STRUCTURAL PROXY, not semantic
# verification: it cannot detect a strong claim phrased without these markers
# (false negative), and it may flag restrained text that quotes strong language
# (false positive). See:
# docs/governance/self-governance-claim-label-drift-mutation-contract-2026-07-04.md
CLAIM_STRENGTH_MARKERS = (
    "guarantee",
    "completely safe",
    "completely correct",
    "completely secure",
    "fully safe",
    "fully correct",
    "fully secure",
    "all inputs",
    "all cases",
    "every input",
    "every case",
    "any input",
    "always correct",
    "always safe",
    "never fails",
    "cannot fail",
    "100%",
)

# claim_level values that assert restraint; strength markers in the text
# contradict these labels.
_RESTRAINED_CLAIM_LEVELS = ("bounded", "parity")

_PUBLIC_SUPPORT_SCOPES = ("public", "external")

CLAIM_SEMANTIC_ATTESTATION_SCHEMA = "claim_semantic_attestation.v0.1"
CLAIM_SEMANTIC_ATTESTATION_MISSING = "claim_semantic_attestation_missing"
CLAIM_SEMANTIC_ATTESTATION_INVALID = "claim_semantic_attestation_invalid"
CLAIM_SEMANTIC_ATTESTATION_OVERSTATED = "claim_semantic_attestation_overstated"
CLAIM_SEMANTIC_ATTESTATION_UNCLEAR = "claim_semantic_attestation_unclear"

_ATTESTATION_RESULTS = ("aligned", "overstated", "unclear")
_HEX_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")

POSTURE_ORDER = {
    "none": 0,
    "bounded_support": 1,
    "partial_falsification": 2,
}

CLAIM_LEVEL_ORDER = {
    "bounded": 0,
    "parity": 1,
    "strong": 2,
    "unbounded": 3,
}

# Backward compatibility mapping for older artifacts.
LEGACY_CLAIM_LEVEL_MAP = {
    "bounded_support": "bounded",
    "stronger_than_allowed": "strong",
}


def _load_input(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_posture_stronger(current: str, previous: str) -> bool:
    return POSTURE_ORDER.get(current, -1) > POSTURE_ORDER.get(previous, -1)


def _normalize_claim_level(value: str) -> str:
    raw = (value or "").strip()
    mapped = LEGACY_CLAIM_LEVEL_MAP.get(raw, raw)
    return mapped if mapped in CLAIM_LEVEL_ORDER else "bounded"


def _has_strength_marker(final_claim: str) -> bool:
    lowered = final_claim.lower()
    return any(marker in lowered for marker in CLAIM_STRENGTH_MARKERS)


def _claim_support_report_only_reasons(
    *,
    payload: dict,
    final_claim: str,
    claim_level: str,
    publication_scope: str,
) -> list[str]:
    claim_support = payload.get("claim_support")
    public_scope = publication_scope in _PUBLIC_SUPPORT_SCOPES
    strong_declared_or_marked = claim_level in ("strong", "unbounded") or _has_strength_marker(
        final_claim
    )

    if claim_support is None:
        if public_scope and strong_declared_or_marked:
            return ["claim_support_missing_for_public_strong_claim"]
        return []

    if not isinstance(claim_support, dict):
        return ["claim_support_invalid_shape"]

    reasons: list[str] = []
    supported_claim_level_raw = claim_support.get("supported_claim_level")
    if supported_claim_level_raw is None:
        supported_claim_level = "bounded"
        reasons.append("claim_support_missing_supported_claim_level")
    else:
        raw_supported_level = str(supported_claim_level_raw).strip()
        mapped_supported_level = LEGACY_CLAIM_LEVEL_MAP.get(raw_supported_level, raw_supported_level)
        if mapped_supported_level not in CLAIM_LEVEL_ORDER:
            reasons.append("claim_support_invalid_supported_claim_level")
            supported_claim_level = "bounded"
        else:
            supported_claim_level = mapped_supported_level

    if CLAIM_LEVEL_ORDER[claim_level] > CLAIM_LEVEL_ORDER[supported_claim_level]:
        reasons.append("claim_level_exceeds_structured_support")

    evidence_refs = claim_support.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        reasons.append("claim_support_missing_evidence_refs")

    return reasons


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_empty_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        _is_non_empty_string(item) for item in value
    )


def _git_commit_exists(project_root: object, commit_hash: str) -> bool:
    if not _is_non_empty_string(project_root):
        return True
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "cat-file", "-e", f"{commit_hash}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return True
    return result.returncode == 0


def _claim_semantic_attestation_report_only_reasons(payload: dict) -> list[str]:
    semantic_review_claimed = payload.get("semantic_review_claimed") is True
    attestation = payload.get("claim_semantic_attestation")

    if attestation is None:
        if semantic_review_claimed:
            return [CLAIM_SEMANTIC_ATTESTATION_MISSING]
        return []

    if not isinstance(attestation, dict):
        return [CLAIM_SEMANTIC_ATTESTATION_INVALID]

    invalid = False
    if attestation.get("receipt_schema") != CLAIM_SEMANTIC_ATTESTATION_SCHEMA:
        invalid = True
    if attestation.get("status") != "report_only":
        invalid = True
    if not _is_non_empty_string(attestation.get("reviewed_claim")):
        invalid = True
    if attestation.get("reviewed_claim_level") not in CLAIM_LEVEL_ORDER:
        invalid = True
    if attestation.get("attested_support_level") not in CLAIM_LEVEL_ORDER:
        invalid = True
    attestation_result = attestation.get("attestation_result")
    if attestation_result not in _ATTESTATION_RESULTS:
        invalid = True
    if not _is_non_empty_string_list(attestation.get("evidence_refs")):
        invalid = True
    if not _is_non_empty_string(attestation.get("attested_by")):
        invalid = True
    linked_commit = attestation.get("linked_commit")
    if not _is_non_empty_string(linked_commit) or not _HEX_COMMIT_RE.match(str(linked_commit)):
        invalid = True
    elif not _git_commit_exists(payload.get("project_root"), str(linked_commit)):
        invalid = True
    if not _is_non_empty_string_list(attestation.get("cannot_claim")):
        invalid = True

    if invalid:
        return [CLAIM_SEMANTIC_ATTESTATION_INVALID]
    if attestation_result == "overstated":
        return [CLAIM_SEMANTIC_ATTESTATION_OVERSTATED]
    if attestation_result == "unclear":
        return [CLAIM_SEMANTIC_ATTESTATION_UNCLEAR]
    return []


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
            "checker_status": "pass" if hard_rule_ok else "fail",
            "semantic_drift_risk": False,
            "claim_level": _normalize_claim_level(str(payload.get("claim_level", "bounded"))),
            "enforcement_action": "allow" if hard_rule_ok else "block",
            "reviewer_override_required": False if hard_rule_ok else True,
            "publication_scope": str(payload.get("publication_scope", "public")),
            "reasons": [] if hard_rule_ok else [
                "precondition_failed_contract_violation: expected not_executed + observed=null"
            ],
            "report_only_reasons": [],
        }

    final_claim = str(payload.get("final_claim", ""))
    claim_level = _normalize_claim_level(str(payload.get("claim_level", "bounded")))
    same_evidence = bool(payload.get("same_evidence_as_previous", False))
    posture = str(payload.get("posture", "none"))
    previous_posture = str(payload.get("previous_posture", "none"))
    publication_scope = str(payload.get("publication_scope", "public"))

    semantic_drift_risk = False
    report_only_reasons = _claim_support_report_only_reasons(
        payload=payload,
        final_claim=final_claim,
        claim_level=claim_level,
        publication_scope=publication_scope,
    )
    report_only_reasons.extend(_claim_semantic_attestation_report_only_reasons(payload))

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

    # Local-only scope cannot claim above bounded.
    if publication_scope == "local_only" and claim_level != "bounded":
        semantic_drift_risk = True
        reasons.append("local_only_claim_level_exceeds_bounded")

    # Claim-label drift: a self-declared restrained level (bounded/parity) whose
    # text asserts absolute/universal strength. Advisory-only structural proxy —
    # routes through the existing downgrade path, never a new blocking action.
    if claim_level in _RESTRAINED_CLAIM_LEVELS and any(
        marker in lowered for marker in CLAIM_STRENGTH_MARKERS
    ):
        semantic_drift_risk = True
        reasons.append("claim_label_understates_claim_text")

    if semantic_drift_risk:
        if claim_level in ("strong", "unbounded"):
            enforcement_action = "block"
        else:
            enforcement_action = "downgrade"
    else:
        enforcement_action = "allow"

    result = "fail" if enforcement_action == "block" else "pass"
    return {
        "result": result,
        "checker_status": "fail" if enforcement_action == "block" else "pass",
        "semantic_drift_risk": semantic_drift_risk,
        "claim_level": claim_level,
        "enforcement_action": enforcement_action,
        "reviewer_override_required": enforcement_action in ("downgrade", "block"),
        "publication_scope": publication_scope,
        "reasons": reasons,
        "report_only_reasons": report_only_reasons,
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
