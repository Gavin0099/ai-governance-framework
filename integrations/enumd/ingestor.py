#!/usr/bin/env python3
"""
integrations/enumd/ingestor.py

Adapter that validates and normalises an Enumd governance_report.json into
a framework-canonical external-observation entry.

Responsibilities
----------------
1. Read a governance_report.json produced by Enumd.
2. Validate required provenance fields (producer, schema_version,
   semantic_boundary, calibration_profile).
3. Assert that semantic_boundary.represents_agent_behavior == false so the
   observation is never accidentally routed into lifecycle_class / E1b.
4. Write a canonical external-observation JSON to
   artifacts/external-observations/enumd-{run_id}.json.

What this adapter intentionally does NOT do
-------------------------------------------
- Recompute any Enumd overlap or enforcement scores.
- Re-interpret domain-calibrated thresholds (0.40, 0.30, 0.50) as framework
  policy defaults.
- Derive stronger framework-level meanings from Enumd advisory signals.
- Convert Enumd KEEP/DOWNGRADE/REMOVE decisions to framework lifecycle actions.

See integrations/enumd/mapping.md for the authoritative field correspondence
table.  See integrations/enumd/usage.md for CLI usage and output contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL = [
    "producer",
    "artifact_type",
    "schema_version",
    "observation_class",
    "observation_type",
    "semantic_boundary",
    "calibration_profile",
    "run_id",
]

REQUIRED_SEMANTIC_BOUNDARY = ["represents_agent_behavior", "derivation"]

REQUIRED_CALIBRATION_PROFILE = ["name", "overlap_thresholds"]

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_required_fields(data: dict, fields: list[str], context: str) -> list[str]:
    missing = [f for f in fields if f not in data]
    return [f"[{context}] missing required field: {f!r}" for f in missing]


def validate_report(report: dict) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors: list[str] = []

    errors.extend(_check_required_fields(report, REQUIRED_TOP_LEVEL, "top-level"))
    if errors:
        # Cannot safely proceed with deeper checks
        return errors

    # Schema version
    version = report.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            f"[schema_version] unsupported value {version!r}; "
            f"expected one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    # producer must be "enumd"
    producer = report.get("producer")
    if producer != "enumd":
        errors.append(
            f"[producer] expected 'enumd', got {producer!r}; "
            "this adapter only accepts Enumd artifacts"
        )

    # semantic_boundary
    sb = report.get("semantic_boundary", {})
    errors.extend(_check_required_fields(sb, REQUIRED_SEMANTIC_BOUNDARY, "semantic_boundary"))
    if "represents_agent_behavior" in sb:
        if sb["represents_agent_behavior"] is not False:
            errors.append(
                "[semantic_boundary.represents_agent_behavior] must be false; "
                "Enumd governance reports describe synthesis pipeline output, "
                "not agent runtime behavior. "
                "Routing this observation into lifecycle statistics would be incorrect."
            )

    # calibration_profile
    cp = report.get("calibration_profile", {})
    errors.extend(_check_required_fields(cp, REQUIRED_CALIBRATION_PROFILE, "calibration_profile"))

    return errors


# ---------------------------------------------------------------------------
# Output construction
# ---------------------------------------------------------------------------


def build_canonical_observation(report: dict, source_path: Path) -> dict:
    """
    Wrap the validated report in the framework's canonical external-observation
    envelope.  The envelope adds governance routing metadata without altering
    the Enumd payload.
    """
    return {
        "observation_class": "external_analysis_artifact",
        "observation_type": report.get("observation_type", "synthesis_governance_report"),
        "source": "enumd",
        "run_id": report["run_id"],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source_path),
        # Routing directive preserved verbatim from the producer.
        "semantic_boundary": report["semantic_boundary"],
        # Calibration metadata kept for trend-analysis disambiguation.
        "calibration_profile": report["calibration_profile"],
        # Raw payload embedded as-is — the framework does not reinterpret it.
        "payload": {
            k: v
            for k, v in report.items()
            if k
            not in (
                "semantic_boundary",
                "calibration_profile",
            )
        },
    }


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------


def _output_dir(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "external-observations"


def _output_path(repo_root: Path, run_id: str) -> Path:
    safe_id = run_id.replace("/", "-").replace("\\", "-")
    return _output_dir(repo_root) / f"enumd-{safe_id}.json"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def ingest(report_path: Path, repo_root: Path, dry_run: bool = False) -> dict:
    """
    Read, validate, and normalise a governance_report.json.

    Returns a result dict with keys:
      ok (bool), errors (list[str]), warnings (list[str]),
      output_path (str | None), observation (dict | None)
    """
    result: dict = {
        "ok": False,
        "errors": [],
        "warnings": [],
        "output_path": None,
        "observation": None,
    }

    # --- Load ---
    try:
        raw = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        result["errors"].append(f"[io] cannot read {report_path}: {exc}")
        return result

    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        result["errors"].append(f"[parse] invalid JSON in {report_path}: {exc}")
        return result

    if not isinstance(report, dict):
        result["errors"].append("[parse] top-level JSON value must be an object")
        return result

    # --- Validate ---
    validation_errors = validate_report(report)
    if validation_errors:
        result["errors"].extend(validation_errors)
        return result

    # --- Warn on advisory-only fields ---
    if not report.get("advisories"):
        result["warnings"].append("[advisories] field absent or empty — no advisory signals to observe")

    # --- Build canonical observation ---
    observation = build_canonical_observation(report, report_path)
    result["observation"] = observation

    out_path = _output_path(repo_root, report["run_id"])
    result["output_path"] = str(out_path)

    if not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")

    result["ok"] = True
    return result


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest an Enumd governance_report.json into the framework's external-observations store."
    )
    parser.add_argument("report", type=Path, help="Path to governance_report.json produced by Enumd")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent,
        help="Framework repo root (default: two levels up from this file)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the canonical observation without writing to disk",
    )
    args = parser.parse_args()

    result = ingest(args.report, args.repo_root, dry_run=args.dry_run)

    if result["warnings"]:
        for w in result["warnings"]:
            print(f"WARNING: {w}", file=sys.stderr)

    if not result["ok"]:
        for e in result["errors"]:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(result["observation"], indent=2, ensure_ascii=False))
        print(f"\n[dry-run] would write to: {result['output_path']}", file=sys.stderr)
    else:
        print(f"OK: written to {result['output_path']}")


if __name__ == "__main__":
    _cli()
