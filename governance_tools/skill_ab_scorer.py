#!/usr/bin/env python3
"""
Deterministic scorer for the codex-review-fast A/B measurement.

This is report-only measurement tooling. It does not edit the skill, update the
ledger, enforce a gate, or prove general review quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


REPORT_VERSION = "skill_ab_scorer.v0.1"


class FrozenBundleError(ValueError):
    """Raised when a frozen A/B bundle no longer matches its recorded hashes."""


@dataclass
class Finding:
    file: str
    line: int | None
    defect_type: str
    text: str = ""
    function: str | None = None


@dataclass
class ScoredFinding:
    finding_index: int
    file: str
    line: int | None
    defect_type: str
    disposition: str
    defect_id: str | None = None
    reason: str = ""


@dataclass
class ScoreResult:
    report_version: str
    valid: bool
    run_id: str
    frozen_bundle: str
    TP: int
    FN: int
    FP: int
    recall: float
    precision: float | None
    matched_defects: list[str] = field(default_factory=list)
    missed_defects: list[str] = field(default_factory=list)
    scored_findings: list[ScoredFinding] = field(default_factory=list)
    claim_boundary: str = (
        "This scorer measures matches against one frozen seeded review task. "
        "It does not prove broad review quality, skill effectiveness, runtime "
        "adoption, or enforcement."
    )
    cannot_claim: list[str] = field(
        default_factory=lambda: [
            "codex-review-fast improves real PR review quality",
            "A/B experiment has been run",
            "ledger decision_effect is ready to update",
            "hook, CI, gate, or enforcement behavior changed",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.precision is None:
            payload["precision"] = "n/a"
        return payload


@dataclass
class ExperimentResult:
    report_version: str
    valid: bool
    frozen_bundle: str
    runs: list[ScoreResult]
    mean_recall_A: float
    mean_recall_B: float
    mean_precision_A: float | None
    mean_precision_B: float | None
    delta_recall: float
    delta_precision: float | None
    decision_effect: str
    claim_boundary: str = (
        "This aggregate is a pure function of frozen seeded-task findings. "
        "It does not prove broad review quality, runtime adoption, or enforcement."
    )
    cannot_claim: list[str] = field(
        default_factory=lambda: [
            "codex-review-fast improves real PR review quality",
            "results transfer to other harnesses or models",
            "hook, CI, gate, or enforcement behavior changed",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["runs"] = [run.to_dict() for run in self.runs]
        if self.mean_precision_A is None:
            payload["mean_precision_A"] = "n/a"
        if self.mean_precision_B is None:
            payload["mean_precision_B"] = "n/a"
        if self.delta_precision is None:
            payload["delta_precision"] = "n/a"
        return payload


def _repo_path(repo_root: Path, rel_path: str | Path) -> Path:
    path = Path(rel_path)
    if path.is_absolute():
        return path
    return repo_root / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_type(value: str) -> str:
    return "-".join(part for part in re.split(r"[^a-z0-9]+", value.lower()) if part)


def validate_frozen_bundle(frozen_path: str | Path, repo_root: str | Path = ".") -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    frozen_file = _repo_path(repo, frozen_path)
    frozen = _load_json(frozen_file)
    hashes = frozen.get("hashes", {})
    paths = frozen.get("paths", {})

    required = {
        "ground_truth_sha256": paths.get("ground_truth"),
        "allowlist_sha256": paths.get("allowlist"),
        "target_diff_sha256": paths.get("target_diff"),
        "scorer_sha256": paths.get("scorer"),
    }
    mismatches: list[dict[str, str]] = []
    missing: list[str] = []

    for hash_key, rel_path in required.items():
        expected = hashes.get(hash_key)
        if not rel_path:
            missing.append(hash_key.replace("_sha256", ""))
            continue
        if not expected:
            missing.append(hash_key)
            continue
        actual = _sha256(_repo_path(repo, rel_path))
        if actual != expected:
            mismatches.append({"field": hash_key, "expected": expected, "actual": actual})

    if missing or mismatches:
        raise FrozenBundleError(
            json.dumps(
                {
                    "code": "frozen_bundle_hash_mismatch",
                    "missing": missing,
                    "mismatches": mismatches,
                },
                sort_keys=True,
            )
        )
    return frozen


def _load_findings(path: Path) -> tuple[str, str | None, list[Finding]]:
    payload = _load_json(path)
    run_id = path.stem
    condition: str | None = None
    raw_findings: list[dict[str, Any]]
    if isinstance(payload, list):
        raw_findings = payload
    elif isinstance(payload, dict):
        run_id = str(payload.get("run_id") or run_id)
        condition_value = payload.get("condition")
        condition = str(condition_value).upper() if condition_value is not None else None
        raw_findings = payload.get("findings", [])
    else:
        raise ValueError("findings file must be a JSON list or object with findings")

    findings: list[Finding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            continue
        line_value = raw.get("line")
        line = int(line_value) if line_value is not None else None
        findings.append(
            Finding(
                file=str(raw.get("file") or ""),
                line=line,
                defect_type=str(raw.get("type") or raw.get("defect_type") or ""),
                text=str(raw.get("text") or raw.get("evidence") or raw.get("message") or ""),
                function=str(raw["function"]) if raw.get("function") else None,
            )
        )
    return run_id, condition, findings


def _type_matches(finding_type: str, defect: dict[str, Any], aliases: dict[str, list[str]]) -> bool:
    canonical = _normalize_type(str(defect["type"]))
    observed = _normalize_type(finding_type)
    allowed = {canonical}
    allowed.update(_normalize_type(item) for item in aliases.get(canonical, []))
    return observed in allowed


def _line_matches(finding: Finding, defect: dict[str, Any]) -> bool:
    if finding.file != defect.get("file"):
        return False
    if finding.line is None:
        return False
    return abs(finding.line - int(defect["line"])) <= 1


def _anchor_matches(finding: Finding, defect: dict[str, Any]) -> bool:
    if finding.file != defect.get("file"):
        return False
    expected_function = defect.get("function")
    if expected_function and finding.function and finding.function != expected_function:
        return False
    anchor = str(defect.get("regex_anchor") or "")
    if not anchor:
        return False
    return re.search(anchor, finding.text) is not None


def _allowlisted(finding: Finding, allowlist: dict[str, Any]) -> bool:
    if finding.line is None:
        return False
    for region in allowlist.get("legitimate_regions", []):
        if finding.file != region.get("file"):
            continue
        for line in region.get("lines", []):
            if finding.line == int(line):
                return True
        for start, end in region.get("ranges", []):
            if int(start) <= finding.line <= int(end):
                return True
    return False


def score_findings(
    frozen_path: str | Path,
    findings_path: str | Path,
    repo_root: str | Path = ".",
) -> ScoreResult:
    repo = Path(repo_root).resolve()
    frozen_file = _repo_path(repo, frozen_path)
    frozen = validate_frozen_bundle(frozen_file, repo)
    paths = frozen["paths"]
    ground_truth = _load_json(_repo_path(repo, paths["ground_truth"]))
    allowlist = _load_json(_repo_path(repo, paths["allowlist"]))
    run_id, _condition, findings = _load_findings(_repo_path(repo, findings_path))

    defects = list(ground_truth.get("defects", []))
    aliases = {
        _normalize_type(key): list(value)
        for key, value in ground_truth.get("alias_table", {}).items()
    }
    unmatched = {str(defect["id"]): defect for defect in defects}
    matched: list[str] = []
    scored: list[ScoredFinding] = []
    false_positives = 0

    for index, finding in enumerate(findings):
        matched_id: str | None = None
        matched_reason = ""
        for defect_id, defect in list(unmatched.items()):
            if not _type_matches(finding.defect_type, defect, aliases):
                continue
            if _line_matches(finding, defect):
                matched_id = defect_id
                matched_reason = "line_within_plus_minus_one"
                break
            if _anchor_matches(finding, defect):
                matched_id = defect_id
                matched_reason = "regex_anchor_in_declared_function"
                break
        if matched_id:
            matched.append(matched_id)
            unmatched.pop(matched_id)
            scored.append(
                ScoredFinding(
                    finding_index=index,
                    file=finding.file,
                    line=finding.line,
                    defect_type=_normalize_type(finding.defect_type),
                    disposition="TP",
                    defect_id=matched_id,
                    reason=matched_reason,
                )
            )
        elif _allowlisted(finding, allowlist):
            false_positives += 1
            scored.append(
                ScoredFinding(
                    finding_index=index,
                    file=finding.file,
                    line=finding.line,
                    defect_type=_normalize_type(finding.defect_type),
                    disposition="FP",
                    reason="allowlisted_legitimate_line",
                )
            )
        else:
            scored.append(
                ScoredFinding(
                    finding_index=index,
                    file=finding.file,
                    line=finding.line,
                    defect_type=_normalize_type(finding.defect_type),
                    disposition="unscored",
                    reason="outside_seeded_defects_and_allowlist",
                )
            )

    true_positives = len(matched)
    false_negatives = len(unmatched)
    denominator = true_positives + false_positives
    precision = None if denominator == 0 else true_positives / denominator
    recall = true_positives / len(defects) if defects else 0.0
    return ScoreResult(
        report_version=REPORT_VERSION,
        valid=True,
        run_id=run_id,
        frozen_bundle=str(frozen_file),
        TP=true_positives,
        FN=false_negatives,
        FP=false_positives,
        recall=recall,
        precision=precision,
        matched_defects=matched,
        missed_defects=list(unmatched),
        scored_findings=scored,
    )


def _finding_condition(repo: Path, findings_path: str | Path) -> str:
    _run_id, condition, _findings = _load_findings(_repo_path(repo, findings_path))
    if condition not in {"A", "B"}:
        raise ValueError("aggregate scoring requires each findings file to declare condition A or B")
    return condition


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


def score_experiment(
    frozen_path: str | Path,
    findings_paths: list[str | Path],
    repo_root: str | Path = ".",
) -> ExperimentResult:
    repo = Path(repo_root).resolve()
    if len(findings_paths) < 2:
        raise ValueError("aggregate scoring requires at least one A and one B findings file")

    grouped: dict[str, list[ScoreResult]] = {"A": [], "B": []}
    all_runs: list[ScoreResult] = []
    for path in findings_paths:
        condition = _finding_condition(repo, path)
        run = score_findings(frozen_path, path, repo)
        grouped[condition].append(run)
        all_runs.append(run)

    if not grouped["A"] or not grouped["B"]:
        raise ValueError("aggregate scoring requires both condition A and condition B")

    mean_recall_a = _mean([run.recall for run in grouped["A"]])
    mean_recall_b = _mean([run.recall for run in grouped["B"]])
    mean_precision_a = _precision_mean(grouped["A"])
    mean_precision_b = _precision_mean(grouped["B"])
    delta_recall = mean_recall_b - mean_recall_a
    if mean_precision_a is None or mean_precision_b is None:
        delta_precision = None
    else:
        delta_precision = mean_precision_b - mean_precision_a

    repo = Path(repo_root).resolve()
    return ExperimentResult(
        report_version=REPORT_VERSION,
        valid=True,
        frozen_bundle=str(_repo_path(repo, frozen_path)),
        runs=all_runs,
        mean_recall_A=mean_recall_a,
        mean_recall_B=mean_recall_b,
        mean_precision_A=mean_precision_a,
        mean_precision_B=mean_precision_b,
        delta_recall=delta_recall,
        delta_precision=delta_precision,
        decision_effect=_decision_effect(delta_recall, delta_precision),
    )


def format_human(result: ScoreResult) -> str:
    precision = "n/a" if result.precision is None else f"{result.precision:.3f}"
    lines = [
        "[skill_ab_scorer]",
        f"valid={str(result.valid).lower()}",
        f"run_id={result.run_id}",
        f"TP={result.TP}",
        f"FN={result.FN}",
        f"FP={result.FP}",
        f"recall={result.recall:.3f}",
        f"precision={precision}",
        "matched_defects=" + ",".join(result.matched_defects),
        "missed_defects=" + ",".join(result.missed_defects),
        f"claim_boundary={result.claim_boundary}",
        "cannot_claim:",
    ]
    lines.extend(f"  - {item}" for item in result.cannot_claim)
    return "\n".join(lines)


def format_experiment_human(result: ExperimentResult) -> str:
    precision_a = "n/a" if result.mean_precision_A is None else f"{result.mean_precision_A:.3f}"
    precision_b = "n/a" if result.mean_precision_B is None else f"{result.mean_precision_B:.3f}"
    delta_precision = "n/a" if result.delta_precision is None else f"{result.delta_precision:.3f}"
    lines = [
        "[skill_ab_scorer_experiment]",
        f"valid={str(result.valid).lower()}",
        f"runs={len(result.runs)}",
        f"mean_recall_A={result.mean_recall_A:.3f}",
        f"mean_recall_B={result.mean_recall_B:.3f}",
        f"mean_precision_A={precision_a}",
        f"mean_precision_B={precision_b}",
        f"delta_recall={result.delta_recall:.3f}",
        f"delta_precision={delta_precision}",
        f"decision_effect={result.decision_effect}",
        f"claim_boundary={result.claim_boundary}",
        "cannot_claim:",
    ]
    lines.extend(f"  - {item}" for item in result.cannot_claim)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score codex-review-fast A/B findings against a frozen seed.")
    parser.add_argument("--frozen", required=True, help="Frozen bundle JSON path.")
    parser.add_argument("--findings", required=True, nargs="+", help="Findings JSON path(s). Multiple paths produce an aggregate A/B result.")
    parser.add_argument("--repo", default=".", help="Repository root.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    try:
        if len(args.findings) == 1:
            result = score_findings(args.frozen, args.findings[0], args.repo)
        else:
            result = score_experiment(args.frozen, args.findings, args.repo)
    except FrozenBundleError as exc:
        payload = {
            "report_version": REPORT_VERSION,
            "valid": False,
            "error": json.loads(str(exc)),
            "claim_boundary": "Scoring aborted because the frozen bundle did not match recorded hashes.",
        }
        if args.format == "json":
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("[skill_ab_scorer]")
            print("valid=false")
            print(f"error={payload['error']}")
            print(f"claim_boundary={payload['claim_boundary']}")
        return 2

    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    elif isinstance(result, ExperimentResult):
        print(format_experiment_human(result))
    else:
        print(format_human(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
