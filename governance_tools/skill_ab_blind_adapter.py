#!/usr/bin/env python3
"""
Blind adapter for codex-review-fast A/B scoring.

This adapter keeps condition labels outside the frozen scorer input. It maps
neutral run IDs to hidden conditions after each run is scored by the frozen
deterministic scorer, then emits a corrected aggregate result artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools.skill_ab_scorer import ScoreResult, score_findings


REPORT_VERSION = "skill_ab_blind_adapter.v0.1"


@dataclass(frozen=True)
class ConditionEntry:
    run_id: str
    condition: str
    source_run_id: str | None = None


def _repo_path(repo_root: Path, rel_path: str | Path) -> Path:
    path = Path(rel_path)
    if path.is_absolute():
        return path
    return repo_root / path


def _display_path(repo_root: Path, path: str | Path) -> str:
    resolved = _repo_path(repo_root, path).resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return str(resolved)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_condition_map(path: Path) -> tuple[dict[str, ConditionEntry], list[str]]:
    payload = _load_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        raise ValueError("condition map must be an object with a runs list")

    mapping: dict[str, ConditionEntry] = {}
    for item in payload["runs"]:
        if not isinstance(item, dict):
            raise ValueError("condition map run entries must be objects")
        run_id = str(item.get("run_id") or "")
        condition = str(item.get("condition") or "").upper()
        source_run_id = item.get("source_run_id")
        if not run_id or condition not in {"A", "B"}:
            raise ValueError("condition map entries require run_id and condition A or B")
        if run_id in mapping:
            raise ValueError(f"duplicate run_id in condition map: {run_id}")
        mapping[run_id] = ConditionEntry(
            run_id=run_id,
            condition=condition,
            source_run_id=str(source_run_id) if source_run_id is not None else None,
        )

    shuffle_order = payload.get("shuffle_order")
    if shuffle_order is None:
        shuffle_order = [entry.run_id for entry in mapping.values()]
    if not isinstance(shuffle_order, list) or not all(isinstance(item, str) for item in shuffle_order):
        raise ValueError("condition map shuffle_order must be a list of run IDs")
    return mapping, list(shuffle_order)


def _load_blind_run_id(path: Path) -> str:
    payload = _load_json(path)
    if isinstance(payload, list):
        return path.stem
    if not isinstance(payload, dict):
        raise ValueError("findings file must be a JSON list or object with findings")
    if "condition" in payload:
        raise ValueError("blind findings files must not contain condition labels")
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        raise ValueError("findings must be a list")
    return str(payload.get("run_id") or path.stem)


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot compute mean for an empty condition group")
    return sum(values) / len(values)


def _precision_mean(runs: list[ScoreResult]) -> float | None:
    values = [run.precision for run in runs if run.precision is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _decision_effect(delta_recall: float, delta_precision: float | None) -> str:
    if delta_precision is None:
        return "none"
    if delta_recall >= 0.15 and delta_precision >= -0.10:
        return "positive"
    if delta_recall < 0.15 and delta_precision < -0.10:
        return "negative"
    return "none"


def _json_number(value: float | None) -> float | str:
    return "n/a" if value is None else value


def _conditions_are_shuffled(conditions: list[str]) -> bool:
    if len(set(conditions)) < 2:
        return False
    return conditions != sorted(conditions)


def _compare_aggregates(
    aggregates: dict[str, Any],
    reference_result_path: Path | None,
    repo_root: Path,
) -> dict[str, Any]:
    if reference_result_path is None:
        return {
            "reference_result": None,
            "decision_effect_matches_reference": "not_checked",
            "aggregate_values_match_reference": "not_checked",
        }

    reference = _load_json(reference_result_path)
    reference_aggregates = reference.get("aggregates", {})
    keys = [
        "mean_recall_A",
        "mean_recall_B",
        "mean_precision_A",
        "mean_precision_B",
        "delta_recall",
        "delta_precision",
        "decision_effect",
    ]
    matches = {key: aggregates.get(key) == reference_aggregates.get(key) for key in keys}
    return {
        "reference_result": _display_path(repo_root, reference_result_path),
        "decision_effect_matches_reference": matches["decision_effect"],
        "aggregate_values_match_reference": all(matches.values()),
        "matched_fields": matches,
    }


def score_blind_experiment(
    frozen_path: str | Path,
    findings_paths: list[str | Path],
    condition_map_path: str | Path,
    repo_root: str | Path = ".",
    reference_result_path: str | Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    frozen_file = _repo_path(repo, frozen_path)
    condition_map_file = _repo_path(repo, condition_map_path)
    reference_file = (
        _repo_path(repo, reference_result_path)
        if reference_result_path is not None
        else None
    )

    if len(findings_paths) < 2:
        raise ValueError("blind aggregate scoring requires at least one A and one B findings file")

    mapping, shuffle_order = _load_condition_map(condition_map_file)
    grouped: dict[str, list[ScoreResult]] = {"A": [], "B": []}
    run_rows: list[dict[str, Any]] = []
    scored_runs: list[ScoreResult] = []
    scoring_order: list[str] = []
    conditions_in_order: list[str] = []

    for path in findings_paths:
        findings_file = _repo_path(repo, path)
        run_id = _load_blind_run_id(findings_file)
        if run_id not in mapping:
            raise ValueError(f"condition map missing run_id: {run_id}")
        condition_entry = mapping[run_id]
        score = score_findings(frozen_file, findings_file, repo)
        grouped[condition_entry.condition].append(score)
        scored_runs.append(score)
        scoring_order.append(run_id)
        conditions_in_order.append(condition_entry.condition)
        run_rows.append(
            {
                "run_id": run_id,
                "condition": condition_entry.condition,
                "source_run_id": condition_entry.source_run_id,
                "TP": score.TP,
                "FN": score.FN,
                "FP": score.FP,
                "recall": score.recall,
                "precision": _json_number(score.precision),
                "matched_defects": score.matched_defects,
            }
        )

    if not grouped["A"] or not grouped["B"]:
        raise ValueError("blind aggregate scoring requires both condition A and condition B")
    if set(scoring_order) != set(mapping):
        missing = sorted(set(mapping) - set(scoring_order))
        extra = sorted(set(scoring_order) - set(mapping))
        raise ValueError(f"findings/map run_id mismatch; missing={missing}, extra={extra}")
    if sorted(scoring_order) != sorted(shuffle_order):
        raise ValueError("findings paths must match condition map shuffle_order run IDs")

    mean_recall_a = _mean([run.recall for run in grouped["A"]])
    mean_recall_b = _mean([run.recall for run in grouped["B"]])
    mean_precision_a = _precision_mean(grouped["A"])
    mean_precision_b = _precision_mean(grouped["B"])
    delta_recall = mean_recall_b - mean_recall_a
    delta_precision = (
        None
        if mean_precision_a is None or mean_precision_b is None
        else mean_precision_b - mean_precision_a
    )
    aggregates = {
        "mean_recall_A": mean_recall_a,
        "mean_recall_B": mean_recall_b,
        "mean_precision_A": _json_number(mean_precision_a),
        "mean_precision_B": _json_number(mean_precision_b),
        "delta_recall": delta_recall,
        "delta_precision": _json_number(delta_precision),
        "decision_effect": _decision_effect(delta_recall, delta_precision),
    }

    scorer_hash = _sha256(repo / "governance_tools" / "skill_ab_scorer.py")
    return {
        "schema_version": "skill_ab_blind_result.v0.1",
        "report_version": REPORT_VERSION,
        "subject": "codex-review-fast",
        "run_date": date.today().isoformat(),
        "frozen_bundle": _display_path(repo, frozen_file),
        "scorer": "governance_tools/skill_ab_scorer.py",
        "scorer_sha256": scorer_hash,
        "adapter": "governance_tools/skill_ab_blind_adapter.py",
        "blind_findings": [_display_path(repo, path) for path in findings_paths],
        "hidden_condition_map": _display_path(repo, condition_map_file),
        "controls": {
            "condition_labels_stripped_before_scoring": True,
            "order_shuffled_before_scoring": _conditions_are_shuffled(conditions_in_order),
            "hidden_condition_map_kept_out_of_scorer_input": True,
            "frozen_scorer_input_changed": False,
            "ledger_decision_effect_updated": False,
            "skill_changed": False,
            "hook_ci_gate_or_enforcement_changed": False,
        },
        "scoring_order": scoring_order,
        "condition_order_after_hidden_mapping": conditions_in_order,
        "run_table": run_rows,
        "aggregates": aggregates,
        "reproduction": _compare_aggregates(aggregates, reference_file, repo),
        "claim_boundary": (
            "This artifact corrects the scorer-input blinding protocol for one "
            "constructed seeded A/B run. It does not prove broad review quality, "
            "runtime adoption, or enforcement."
        ),
        "cannot_claim": [
            "codex-review-fast is broadly ineffective",
            "codex-review-fast improves real PR review quality",
            "results transfer to other harnesses or models",
            "ledger decision_effect has been updated",
            "hook, CI, gate, or enforcement behavior changed",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Blind adapter for frozen skill A/B scoring.")
    parser.add_argument("--frozen", required=True, help="Frozen bundle JSON path.")
    parser.add_argument("--condition-map", required=True, help="Hidden run_id -> condition map.")
    parser.add_argument("--findings", required=True, nargs="+", help="Label-stripped findings JSON files.")
    parser.add_argument("--repo", default=".", help="Repository root.")
    parser.add_argument("--reference-result", help="Optional prior result artifact to compare aggregates.")
    parser.add_argument("--output", help="Optional JSON artifact output path.")
    args = parser.parse_args(argv)

    try:
        result = score_blind_experiment(
            frozen_path=args.frozen,
            findings_paths=args.findings,
            condition_map_path=args.condition_map,
            repo_root=args.repo,
            reference_result_path=args.reference_result,
        )
    except Exception as exc:
        payload = {
            "report_version": REPORT_VERSION,
            "valid": False,
            "error": str(exc),
            "claim_boundary": "Blind scoring aborted before a corrected aggregate could be emitted.",
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2

    if args.output:
        _write_json(_repo_path(Path(args.repo).resolve(), args.output), result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
