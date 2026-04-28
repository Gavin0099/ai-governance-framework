#!/usr/bin/env python3
"""
Classification governance smoke test.

This smoke validates the bounded classification-governance slice without
polluting the repo's real artifacts/runtime/summaries directory.

Usage:
    python _classification_governance_smoke.py [--project-root .]
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


def _write_summary(summaries_dir: Path, session_id: str, decision_context: dict) -> None:
    payload = {
        "session_id": session_id,
        "closed_at": "2026-04-07T00:00:00+00:00",
        "decision_context": decision_context,
    }
    (summaries_dir / f"{session_id}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    sys.path.insert(0, str(root))

    from governance_tools.classification_session_summary import (
        build_classification_session_summary,
        format_human_result,
    )

    smoke_root = root / "tests" / "_tmp_classification_governance_smoke"
    if smoke_root.exists():
        shutil.rmtree(smoke_root, ignore_errors=True)
    smoke_root.mkdir(parents=True, exist_ok=True)
    try:
        summaries_dir = smoke_root / "artifacts" / "runtime" / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)

        scenarios = [
            (
                "smoke-ok-001",
                {
                    "initial_agent_class": "instruction_capable",
                    "effective_agent_class": "instruction_capable",
                    "classification_changed": False,
                    "reclassification_reason": None,
                },
            ),
            (
                "smoke-ok-002",
                {
                    "initial_agent_class": "instruction_capable",
                    "effective_agent_class": "instruction_capable",
                    "classification_changed": False,
                    "reclassification_reason": None,
                },
            ),
            (
                "smoke-downgrade-001",
                {
                    "initial_agent_class": "instruction_capable",
                    "effective_agent_class": "instruction_limited",
                    "classification_changed": True,
                    "reclassification_reason": "context_degraded",
                },
            ),
        ]

        for session_id, decision_context in scenarios:
            _write_summary(summaries_dir, session_id, decision_context)

        result = build_classification_session_summary(smoke_root)
        print(format_human_result(result))
        print()

        failed = []
        if result["session_count"] != 3:
            failed.append(f"session_count expected 3, got {result['session_count']}")
        if result["classification_changed_count"] != 1:
            failed.append(
                "classification_changed_count expected 1, "
                f"got {result['classification_changed_count']}"
            )
        if result["downgrade_count"] != 1:
            failed.append(f"downgrade_count expected 1, got {result['downgrade_count']}")
        if result["anomaly_count"] != 0:
            failed.append(f"anomaly_count expected 0, got {result['anomaly_count']}")
        if result["policy_flags"]["anomaly_alert"] is not False:
            failed.append("anomaly_alert should be False")
        if result["policy_flags"]["classifier_review"] is not False:
            failed.append("classifier_review should be False")
        if result["policy_flags"]["taxonomy_breach"] is not False:
            failed.append("taxonomy_breach should be False")
        if result["policy_ok"] is not True:
            failed.append("policy_ok should be True")

        if failed:
            print("FAIL:")
            for item in failed:
                print(f"  - {item}")
            return 1

        print("SMOKE TEST PASS")
        return 0
    finally:
        shutil.rmtree(smoke_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
