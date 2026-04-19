#!/usr/bin/env python3
"""
Semantic isolation layer for Enumd runtime candidate artifacts.

Enumd produces fields that are decision-shaped in representation (directive, numeric, binary)
but carry internal session-level semantics that differ from governance framework semantics.
This tool maps those fields through a non-equivalence registry and produces a probe report
with semantic isolation applied, preventing cross-domain misread.

Batch conclusions:
  observe_only_safe                 — boundary pass, no authority-like fields detected
  observe_only_with_inducement_risk — boundary pass, occasional authority-like fields
  observe_only_with_semantic_collision — boundary pass, systematic authority-like fields
                                         (same field family hits across entire batch)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "enumd-semantic-isolation-probe"

# Non-equivalence registry: Enumd field path → semantic annotation.
# Key format: dot-notation path into the candidate JSON (e.g. "policy.decision").
_NON_EQUIVALENCE_REGISTRY: dict[str, dict[str, Any]] = {
    "policy.decision": {
        "family": "promotion_like",
        "actual_scope": "session_memory_promotion",
        "misread_scope": "repo_integration_decision",
        "decision_shaped": True,
        "reinterpretation_required": True,
        "non_equivalence": "policy.decision != framework verdict.decision",
        "collision_risk": "high",
    },
    "checks.repo_readiness_level": {
        "family": "numeric_threshold",
        "actual_scope": "closeout_completeness_proxy",
        "misread_scope": "integration_readiness_gate",
        "decision_shaped": True,
        "reinterpretation_required": True,
        "non_equivalence": "repo_readiness_level != readiness_gate",
        "collision_risk": "medium",
    },
    "checks.closeout_schema_validity": {
        "family": "binary_verdict",
        "actual_scope": "artifact_file_presence_and_structure",
        "misread_scope": "governance_validity",
        "decision_shaped": True,
        "reinterpretation_required": True,
        "non_equivalence": "closeout_schema_validity != governance_validity",
        "collision_risk": "medium",
    },
    "checks.closeout_content_sufficiency": {
        "family": "binary_verdict",
        "actual_scope": "artifact_file_content_completeness",
        "misread_scope": "governance_content_sufficiency",
        "decision_shaped": True,
        "reinterpretation_required": True,
        "non_equivalence": "closeout_content_sufficiency != governance_content_sufficiency",
        "collision_risk": "low",
    },
    "checks.repo_closeout_activation_state": {
        "family": "state_machine",
        "actual_scope": "session_activation_lifecycle",
        "misread_scope": "integration_activation_status",
        "decision_shaped": True,
        "reinterpretation_required": True,
        "non_equivalence": "repo_closeout_activation_state != integration_activation_status",
        "collision_risk": "low",
    },
}

_HIGH_COLLISION_FIELDS = {k for k, v in _NON_EQUIVALENCE_REGISTRY.items() if v["collision_risk"] == "high"}


def _get_nested(data: dict, dotpath: str) -> tuple[bool, Any]:
    """Return (exists, value) for a dot-notation path."""
    parts = dotpath.split(".")
    cur: Any = data
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _classify_ingestion_valid(candidate: dict) -> bool:
    """A candidate is ingestion-valid only if it has no missing_fields and boundary passes."""
    checks = candidate.get("checks") or {}
    missing = checks.get("closeout_per_layer_results", {}).get("missing_fields", [])
    errors = candidate.get("errors") or []
    return len(missing) == 0 and len(errors) == 0


def _classify_boundary_status(candidate: dict) -> str:
    """Pass unless explicit boundary_fail signal."""
    errors = candidate.get("errors") or []
    for e in errors:
        if isinstance(e, dict) and "boundary_fail" in str(e).lower():
            return "fail"
        if isinstance(e, str) and "boundary_fail" in e.lower():
            return "fail"
    return "pass"


@dataclass
class AuthorityLikeField:
    field: str
    family: str
    actual_scope: str
    misread_scope: str
    reinterpretation_required: bool
    collision_risk: str
    observed_value: Any
    non_equivalence: str

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "family": self.family,
            "actual_scope": self.actual_scope,
            "misread_scope": self.misread_scope,
            "reinterpretation_required": self.reinterpretation_required,
            "collision_risk": self.collision_risk,
            "observed_value": self.observed_value,
            "non_equivalence": self.non_equivalence,
        }


@dataclass
class SampleProbeResult:
    sample_id: str
    source_path: str
    ingestion_valid: bool
    boundary_status: str
    runtime_eligible_result: str
    inducement_risk: str
    misread_risk: str
    authority_like_fields: list[AuthorityLikeField] = field(default_factory=list)
    semantic_isolation_applied: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "sample_id": self.sample_id,
            "source_path": self.source_path,
            "ingestion_valid": self.ingestion_valid,
            "boundary_status": self.boundary_status,
            "runtime_eligible_result": self.runtime_eligible_result,
            "inducement_risk": self.inducement_risk,
            "misread_risk": self.misread_risk,
            "authority_like_fields": [f.to_dict() for f in self.authority_like_fields],
            "semantic_isolation_applied": self.semantic_isolation_applied,
            "notes": self.notes,
        }


def analyze_candidate(candidate: dict, source_path: str) -> SampleProbeResult:
    """Analyze one Enumd candidate file and return a probe result."""
    session_id = candidate.get("session_id", Path(source_path).stem)
    ingestion_valid = _classify_ingestion_valid(candidate)
    boundary_status = _classify_boundary_status(candidate)

    authority_fields: list[AuthorityLikeField] = []
    for dotpath, spec in _NON_EQUIVALENCE_REGISTRY.items():
        exists, value = _get_nested(candidate, dotpath)
        if not exists or value is None:
            continue
        authority_fields.append(AuthorityLikeField(
            field=dotpath,
            family=spec["family"],
            actual_scope=spec["actual_scope"],
            misread_scope=spec["misread_scope"],
            reinterpretation_required=spec["reinterpretation_required"],
            collision_risk=spec["collision_risk"],
            observed_value=value,
            non_equivalence=spec["non_equivalence"],
        ))

    high_risk = any(f.collision_risk == "high" for f in authority_fields)
    any_risk = len(authority_fields) > 0
    inducement_risk = "high" if high_risk else ("medium" if any_risk else "low")
    misread_risk = "high" if high_risk else ("medium" if any_risk else "low")

    notes_parts = []
    if boundary_status == "pass" and not ingestion_valid:
        notes_parts.append("boundary pass despite ingestion failure")
    if any_risk:
        notes_parts.append(f"{len(authority_fields)} authority-like field(s) detected; semantic isolation applied")

    return SampleProbeResult(
        sample_id=session_id,
        source_path=source_path,
        ingestion_valid=ingestion_valid,
        boundary_status=boundary_status,
        runtime_eligible_result="observe_only",
        inducement_risk=inducement_risk,
        misread_risk=misread_risk,
        authority_like_fields=authority_fields,
        semantic_isolation_applied=any_risk,
        notes="; ".join(notes_parts),
    )


def _classify_batch_conclusion(samples: list[SampleProbeResult]) -> str:
    """
    observe_only_with_semantic_collision  — systematic authority-like fields (high-collision
                                            family present in >= 50% of samples)
    observe_only_with_inducement_risk     — occasional authority-like fields
    observe_only_safe                     — no authority-like fields detected
    """
    if not samples:
        return "observe_only_safe"

    high_collision_hits = sum(
        1 for s in samples
        if any(f.field in _HIGH_COLLISION_FIELDS for f in s.authority_like_fields)
    )
    ratio = high_collision_hits / len(samples)
    if ratio >= 0.5:
        return "observe_only_with_semantic_collision"

    any_hit = sum(1 for s in samples if s.authority_like_fields)
    if any_hit > 0:
        return "observe_only_with_inducement_risk"

    return "observe_only_safe"


def run_probe(
    candidates_dir: Path,
    registry_path: Path | None = None,
) -> dict:
    """Read all candidate JSON files in candidates_dir and return a probe report."""
    files = sorted(candidates_dir.glob("*.json"))
    samples: list[SampleProbeResult] = []

    for fp in files:
        try:
            candidate = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as exc:
            samples.append(SampleProbeResult(
                sample_id=fp.stem,
                source_path=str(fp),
                ingestion_valid=False,
                boundary_status="error",
                runtime_eligible_result="error",
                inducement_risk="unknown",
                misread_risk="unknown",
                notes=f"parse error: {exc}",
            ))
            continue
        samples.append(analyze_candidate(candidate, str(fp)))

    batch_conclusion = _classify_batch_conclusion(samples)
    systematic_collision_fields = sorted({
        f.field
        for s in samples
        for f in s.authority_like_fields
        if f.field in _HIGH_COLLISION_FIELDS
    }) if batch_conclusion == "observe_only_with_semantic_collision" else []

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(candidates_dir),
        "registry_path": str(registry_path) if registry_path else "built-in",
        "n": len(samples),
        "batch_conclusion": batch_conclusion,
        "systematic_collision_fields": systematic_collision_fields,
        "boundary_fail_count": sum(1 for s in samples if s.boundary_status == "fail"),
        "ingestion_valid_count": sum(1 for s in samples if s.ingestion_valid),
        "semantic_isolation_applied_count": sum(1 for s in samples if s.semantic_isolation_applied),
        "samples": [s.to_dict() for s in samples],
    }


def format_human(report: dict) -> str:
    lines = [
        f"[enumd_semantic_isolation_probe]",
        f"source_dir={report['source_dir']}",
        f"n={report['n']}",
        f"batch_conclusion={report['batch_conclusion']}",
        f"boundary_fail_count={report['boundary_fail_count']}",
        f"ingestion_valid_count={report['ingestion_valid_count']}",
        f"semantic_isolation_applied_count={report['semantic_isolation_applied_count']}",
    ]
    if report["systematic_collision_fields"]:
        lines.append(f"systematic_collision_fields={','.join(report['systematic_collision_fields'])}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run semantic isolation probe on Enumd runtime candidate artifacts."
    )
    parser.add_argument("--candidates-dir", required=True, help="Directory containing Enumd candidate JSON files")
    parser.add_argument("--registry", help="Path to external non_equivalence_registry.json (optional; built-in used if omitted)")
    parser.add_argument("--output", help="Output path for probe report JSON")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    candidates_dir = Path(args.candidates_dir).resolve()
    registry_path = Path(args.registry).resolve() if args.registry else None

    report = run_probe(candidates_dir, registry_path)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report))
        if args.output:
            print(f"output={args.output}")


if __name__ == "__main__":
    main()
