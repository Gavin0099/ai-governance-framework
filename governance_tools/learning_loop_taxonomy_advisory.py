#!/usr/bin/env python3
"""Advisory-only taxonomy shape checks for learning-loop seed fixtures.

This module is taxonomy-alignment prep. It does not bank reviewer findings,
does not replay evals, does not block CI, and does not affect completion
claims. It only reports whether a seed fixture follows the ratified layered
taxonomy shape:

- semantic_failure: primary reviewer-finding taxonomy (SF-code)
- scenario_type: replay-shape axis
- result_disposition: post-run result axis; null before an eval run
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from governance_tools.failure_disposition import FAILURE_KINDS


DEFAULT_MATRIX = Path("governance/learning_loop_seed_matrix.v0.1.json")
DEFAULT_SEMANTIC_TAXONOMY = Path("governance/SEMANTIC_FAILURE_TAXONOMY.md")


@dataclass
class AdvisoryResult:
    ok: bool
    warning_count: int
    warnings: list[str]
    checked_seeds: int
    claim_ceiling: str = (
        "advisory-only taxonomy shape check; no banking, replay, CI blocker, "
        "completion gate, enforcement, or Gate 3 opening is claimed"
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_semantic_failure_ids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8-sig")
    return set(re.findall(r"^### (SF-\d{2})\b", text, flags=re.MULTILINE))


def validate_payload(payload: dict[str, Any], *, semantic_failure_ids: set[str]) -> AdvisoryResult:
    warnings: list[str] = []
    seeds = payload.get("seeds")
    if not isinstance(seeds, list):
        return AdvisoryResult(
            ok=True,
            warning_count=1,
            warnings=["matrix.seeds must be a list"],
            checked_seeds=0,
        )

    for index, seed in enumerate(seeds):
        prefix = f"seeds[{index}]"
        if not isinstance(seed, dict):
            warnings.append(f"{prefix} must be an object")
            continue

        seed_id = seed.get("id", f"index:{index}")
        semantic_failure = seed.get("semantic_failure")
        scenario_type = seed.get("scenario_type")
        result_disposition = seed.get("result_disposition")

        if not isinstance(semantic_failure, str):
            warnings.append(f"{seed_id}: semantic_failure must be an SF-code string")
        elif semantic_failure not in semantic_failure_ids:
            warnings.append(f"{seed_id}: unknown semantic_failure {semantic_failure}")

        if not isinstance(scenario_type, str) or not scenario_type:
            warnings.append(f"{seed_id}: scenario_type must be a non-empty replay-shape string")
        elif scenario_type in semantic_failure_ids:
            warnings.append(f"{seed_id}: scenario_type must not alias semantic_failure {scenario_type}")
        elif scenario_type in FAILURE_KINDS:
            warnings.append(f"{seed_id}: scenario_type must not use result_disposition value {scenario_type}")

        if result_disposition is not None:
            if result_disposition not in FAILURE_KINDS:
                warnings.append(
                    f"{seed_id}: result_disposition must be null before a run or one of FAILURE_KINDS"
                )
            else:
                warnings.append(
                    f"{seed_id}: result_disposition is prefilled; pre-run seeds should leave it null"
                )

        legacy_category = seed.get("category")
        if legacy_category is not None:
            warnings.append(f"{seed_id}: legacy category field is not allowed in layered seed schema")

    return AdvisoryResult(
        ok=True,
        warning_count=len(warnings),
        warnings=warnings,
        checked_seeds=len(seeds),
    )


def _load_json_advisory(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), []
    except FileNotFoundError:
        return None, [f"matrix file not found: {path}"]
    except JSONDecodeError as exc:
        return None, [f"matrix JSON is invalid: {path}: {exc.msg} at line {exc.lineno} column {exc.colno}"]
    except UnicodeDecodeError as exc:
        return None, [f"matrix file is not valid UTF-8: {path}: {exc}"]


def _load_semantic_ids_advisory(path: Path) -> tuple[set[str], list[str]]:
    try:
        return load_semantic_failure_ids(path), []
    except FileNotFoundError:
        return set(), [f"semantic taxonomy file not found: {path}"]
    except UnicodeDecodeError as exc:
        return set(), [f"semantic taxonomy file is not valid UTF-8: {path}: {exc}"]


def validate_file(matrix_path: Path, *, semantic_taxonomy_path: Path = DEFAULT_SEMANTIC_TAXONOMY) -> AdvisoryResult:
    payload, matrix_warnings = _load_json_advisory(matrix_path)
    semantic_failure_ids, taxonomy_warnings = _load_semantic_ids_advisory(semantic_taxonomy_path)
    warnings = matrix_warnings + taxonomy_warnings
    if payload is None:
        return AdvisoryResult(
            ok=True,
            warning_count=len(warnings),
            warnings=warnings,
            checked_seeds=0,
        )

    result = validate_payload(payload, semantic_failure_ids=semantic_failure_ids)
    if warnings:
        result.warnings[:0] = warnings
        result.warning_count = len(result.warnings)
    return result


def _emit_result(result: AdvisoryResult, *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return

    print("[learning_loop_taxonomy_advisory]")
    print(f"ok={result.ok}")
    print(f"checked_seeds={result.checked_seeds}")
    print(f"warning_count={result.warning_count}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    print(f"claim_ceiling={result.claim_ceiling}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--semantic-taxonomy", type=Path, default=DEFAULT_SEMANTIC_TAXONOMY)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    result = validate_file(args.matrix, semantic_taxonomy_path=args.semantic_taxonomy)
    _emit_result(result, output_format=args.format)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
