"""Pure validation helpers for the frozen C1 Gate 1 preregistration.

The module performs no filesystem, Git, network, producer, scorer, or arm I/O.
Filesystem binding verification belongs to the pre-run review tool, not these
decision calculators.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from statistics import median
from typing import Any, Iterable, Mapping, Sequence


class PreregistrationError(ValueError):
    """Raised when frozen preregistration semantics are violated."""


class ProgramTerminal(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    INSUFFICIENT = "INSUFFICIENT"
    INVALID = "INVALID"


EVENT_ORDER = (
    "randomization_committed",
    "first_outcome_sealed",
    "second_outcome_sealed",
    "blind_set_closed",
    "primary_scorer_submitted",
    "second_scorer_submitted",
    "external_chain_head_pinned",
    "mapping_released",
)

QUALIFYING_FIELDS = (
    "completed_under_cap",
    "oracle_acceptance",
    "regression_baseline_fail",
    "regression_passes_after_fix",
    "original_defect_caught",
    "no_new_scoped_regression",
    "critical_residuals_zero",
)


@dataclass(frozen=True)
class PairOutcome:
    a_qualifying: bool
    b_qualifying: bool
    a_completed: bool
    b_completed: bool


@dataclass(frozen=True)
class TaskDecision:
    winner: str
    pairs_used: int
    a_successes: int
    b_successes: int


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def qualifying_success(metrics: Mapping[str, Any]) -> bool:
    missing = [field for field in QUALIFYING_FIELDS if field not in metrics]
    if missing:
        raise PreregistrationError(f"missing qualifying fields: {','.join(missing)}")
    if any(not isinstance(metrics[field], bool) for field in QUALIFYING_FIELDS):
        raise PreregistrationError("qualifying fields must be booleans")
    return all(metrics[field] for field in QUALIFYING_FIELDS)


def third_pair_required(initial_pairs: Sequence[PairOutcome]) -> bool:
    if len(initial_pairs) != 2:
        raise PreregistrationError("exactly two initial pairs are required")
    any_non_completion = any(
        not pair.a_completed or not pair.b_completed for pair in initial_pairs
    )
    a_successes = sum(pair.a_qualifying for pair in initial_pairs)
    b_successes = sum(pair.b_qualifying for pair in initial_pairs)
    return any_non_completion or a_successes == b_successes


def decide_task(pairs: Sequence[PairOutcome]) -> TaskDecision:
    if len(pairs) not in (2, 3):
        raise PreregistrationError("a task decision requires two or three pairs")
    required = third_pair_required(pairs[:2])
    if required and len(pairs) != 3:
        raise PreregistrationError("the frozen third pair is required")
    if not required and len(pairs) != 2:
        raise PreregistrationError("a third pair is forbidden when not triggered")
    a_successes = sum(pair.a_qualifying for pair in pairs)
    b_successes = sum(pair.b_qualifying for pair in pairs)
    winner = "B" if b_successes > a_successes else "A" if a_successes > b_successes else "TIE"
    return TaskDecision(winner, len(pairs), a_successes, b_successes)


def paired_ratios(
    a_values: Sequence[int | float], b_values: Sequence[int | float]
) -> tuple[float, ...]:
    if len(a_values) != len(b_values):
        raise PreregistrationError("paired cost vectors must have equal length")
    if not a_values:
        raise PreregistrationError("at least one paired cost value is required")
    if any(isinstance(value, bool) for value in (*a_values, *b_values)):
        raise PreregistrationError("boolean cost values are invalid")
    if any(value <= 0 for value in (*a_values, *b_values)):
        raise PreregistrationError("cost values must be positive")
    return tuple(float(b) / float(a) for a, b in zip(a_values, b_values, strict=True))


def median_paired_ratio(
    a_values: Sequence[int | float], b_values: Sequence[int | float]
) -> float:
    return float(median(paired_ratios(a_values, b_values)))


def validate_event_order(events: Sequence[str]) -> None:
    if tuple(events) != EVENT_ORDER:
        raise PreregistrationError("evidence-chain event order differs from freeze")


def mapping_commitment(mapping_reveal: Mapping[str, str], nonce_hex: str) -> str:
    if len(nonce_hex) != 64:
        raise PreregistrationError("mapping nonce must contain 64 hex characters")
    try:
        bytes.fromhex(nonce_hex)
    except ValueError as exc:
        raise PreregistrationError("mapping nonce must be hexadecimal") from exc
    payload = {
        "mapping": dict(mapping_reveal),
        "nonce": nonce_hex.lower(),
        "schema": "gate3-mapping-reveal-commitment.v1",
    }
    return sha256_hex(canonical_json_bytes(payload))


def validate_feedback_visibility(arm: str, delivery_count: int) -> None:
    if arm not in {"A", "B", "C", "D"}:
        raise PreregistrationError("unknown arm")
    if arm == "D" and delivery_count != 1:
        raise PreregistrationError("Arm D requires exactly one feedback delivery")
    if arm != "D" and delivery_count != 0:
        raise PreregistrationError("A/B/C must not receive treatment-time feedback")


def validate_retained_feedback(value: Mapping[str, Any]) -> None:
    allowed = {
        "mutant_count",
        "operator_counts",
        "status_counts",
        "surviving_mutant_count",
        "target_rule_sha256",
        "raw_report_sha256",
        "phase_status",
        "duration_ms",
        "cleanup_confirmed",
        "raw_output_retained",
        "bulk_path_listing_retained",
    }
    forbidden = {
        "files",
        "location",
        "mutants",
        "replacement",
        "source",
        "tests",
        "stdout",
        "stderr",
        "path_oid_inventory",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            overlap = forbidden.intersection(str(key) for key in node)
            if overlap:
                raise PreregistrationError(
                    f"retained feedback contains forbidden fields: {','.join(sorted(overlap))}"
                )
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    unknown = set(str(key) for key in value).difference(allowed)
    if unknown:
        raise PreregistrationError(
            f"retained feedback contains unapproved fields: {','.join(sorted(unknown))}"
        )
    walk(value)
    if value.get("raw_output_retained") is not False:
        raise PreregistrationError("raw validator output must not be retained")
    if value.get("bulk_path_listing_retained") is not False:
        raise PreregistrationError("bulk path listings must not be retained")
    if value.get("cleanup_confirmed") is not True:
        raise PreregistrationError("cleanup must be confirmed before retention")


def validate_attempt06_quarantine(value: Mapping[str, Any]) -> None:
    if value.get("role") != "validator_qualification_only":
        raise PreregistrationError("attempt-06 must remain qualification-only")
    forbidden_uses = set(value.get("forbidden_uses", ()))
    required = {
        "producer_input",
        "effectiveness_threshold",
        "task_winner",
        "mutation_score_target",
        "sample_count",
        "arm_output",
    }
    if not required.issubset(forbidden_uses):
        raise PreregistrationError("attempt-06 quarantine is incomplete")


def decide_program_terminal(
    *,
    valid: bool,
    complete_sample: bool,
    diversity_met: bool,
    core_cost_pairs: int,
    b_task_wins: int,
    b_completion_not_lower: bool,
    b_unique_critical_failures: int,
    product_success_difference_wins: int,
    wall_clock_ratio_median: float | None,
    tool_call_ratio_median: float | None,
) -> ProgramTerminal:
    if not valid:
        return ProgramTerminal.INVALID
    if (
        not complete_sample
        or not diversity_met
        or core_cost_pairs < 2
        or wall_clock_ratio_median is None
        or tool_call_ratio_median is None
    ):
        return ProgramTerminal.INSUFFICIENT
    positive = (
        b_task_wins >= 2
        and b_completion_not_lower
        and b_unique_critical_failures == 0
        and product_success_difference_wins >= 1
        and wall_clock_ratio_median <= 1.2
        and tool_call_ratio_median <= 1.2
    )
    return ProgramTerminal.POSITIVE if positive else ProgramTerminal.NEGATIVE


def validate_treatment_lattice(arm_inputs: Mapping[str, Iterable[str]]) -> None:
    normalized = {arm: set(inputs) for arm, inputs in arm_inputs.items()}
    if set(normalized) != {"A", "B", "C", "D"}:
        raise PreregistrationError("the freeze requires exactly A/B/C/D")
    common = {"common_task", "baseline", "permissions", "budget", "harness", "model"}
    expected = {
        "A": common,
        "B": common | {"skill"},
        "C": common | {"skill", "governance"},
        "D": common | {"skill", "governance", "validator_feedback"},
    }
    if normalized != expected:
        raise PreregistrationError("arm treatment lattice differs from D2")
