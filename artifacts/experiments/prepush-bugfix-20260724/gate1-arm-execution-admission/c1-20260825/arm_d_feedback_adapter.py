"""Pure validation boundary for frozen Arm D transient feedback."""
from __future__ import annotations

import re
from typing import Any


class ArmDFeedbackError(ValueError):
    pass


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def validate_policy(policy: dict[str, Any]) -> None:
    visibility = policy.get("treatment_visibility")
    transient = policy.get("transient_feedback")
    retained = policy.get("retained_evidence")
    if (
        policy.get("schema") != "c1-arm-d-stryker-feedback-policy.v1"
        or not isinstance(visibility, dict)
        or visibility.get("arms_allowed") != ["D"]
        or visibility.get("arms_denied") != ["A", "B", "C"]
        or visibility.get("delivery_count") != 1
        or visibility.get("adaptive_retry_allowed") is not False
        or not isinstance(transient, dict)
        or transient.get("persistence") != "owned_private_scratch_only"
        or transient.get("remove_before_output_seal") is not True
        or not isinstance(retained, dict)
        or retained.get("aggregate_only") is not True
        or retained.get("raw_output_retained") is not False
        or retained.get("bulk_path_listing_retained") is not False
    ):
        raise ArmDFeedbackError("Arm D feedback policy is not fail-closed")


def validate_transient_feedback(
    entries: list[dict[str, Any]], policy: dict[str, Any], *, arm: str
) -> None:
    validate_policy(policy)
    transient = policy["transient_feedback"]
    if arm != "D":
        raise ArmDFeedbackError("transient validator feedback is Arm D only")
    if len(entries) > transient["maximum_entries"]:
        raise ArmDFeedbackError("transient feedback exceeds the entry cap")
    allowed = set(transient["allowed_fields"])
    forbidden = set(transient["forbidden_fields"])
    for entry in entries:
        keys = set(entry)
        if keys - allowed or keys & forbidden:
            raise ArmDFeedbackError("transient feedback contains forbidden fields")
        relative = entry.get("relative_path")
        if not isinstance(relative, str) or not relative or relative.startswith(("/", "\\")):
            raise ArmDFeedbackError("transient feedback path is not relative")
        if ":" in relative.split("/", 1)[0] or ".." in relative.replace("\\", "/").split("/"):
            raise ArmDFeedbackError("transient feedback path escapes the scratch tree")
        for value in entry.values():
            if isinstance(value, str) and len(value) > transient["maximum_characters_per_entry"]:
                raise ArmDFeedbackError("transient feedback exceeds the character cap")


def validate_retained_evidence(
    evidence: dict[str, Any], policy: dict[str, Any]
) -> None:
    validate_policy(policy)
    retained = policy["retained_evidence"]
    allowed = set(retained["allowed_fields"])
    forbidden = set(retained["forbidden_fields"])
    keys = set(evidence)
    if keys - allowed or keys & forbidden:
        raise ArmDFeedbackError("retained evidence contains non-aggregate fields")
    if evidence.get("cleanup_confirmed") is not True:
        raise ArmDFeedbackError("Arm D cleanup is not confirmed")
    for digest_field in ("target_rule_sha256", "raw_report_sha256"):
        if not _HEX64.fullmatch(str(evidence.get(digest_field, ""))):
            raise ArmDFeedbackError(f"{digest_field} is invalid")
    for aggregate_field in ("operator_counts", "status_counts"):
        value = evidence.get(aggregate_field)
        if not isinstance(value, dict) or any(
            not isinstance(key, str)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
            for key, count in value.items()
        ):
            raise ArmDFeedbackError(f"{aggregate_field} is invalid")
