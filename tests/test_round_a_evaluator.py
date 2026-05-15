from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from governance_tools.round_a_evaluator import evaluate_round_a


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_round_a_evaluator" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _base_ledger(summary_count: str = "1", summary_ratio: str = "1/1") -> str:
    return f'''# AB v1.2 Run Ledger

## Quick Log Table

| run_id | arm | task_id | closeout_status | hard_failure | anchoring_fail | disposition | accepted_change_count | runtime_gov_ratio |
|---|---|---|---|---|---|---|---:|---:|
| 2026-05-11-docs-fix | single-arm | docs-fix | valid | false | false | merge | 1 | 0 |

## Run Type Normalization

### Semantic Slice Summary (current)

| run_id | run_source | commit_hash | closeout_covered |
|---|---|---|---|
| 2026-05-11-docs-fix | semantic_slice_commit | abc1234 | yes |
- engineering_run_count = {summary_count}
- closeout_covered_runs = {summary_ratio} (semantic slices are continuing to be linked to session closeout ids in the same repo and same working session)

## Run Entries

```yaml
run_id: "2026-05-11-docs-fix"
date_utc: "2026-05-11T10:00:00Z"
arm: "single-arm"
task_id: "docs-fix"
task_type: "cross-file-consistency"
baseline_commit: "base-001"
spec_version: "v1.2"
new_session_confirmed: true
run_source: "semantic_slice_commit"
commit_hash: "abc1234"
session_id: "session-001"
closeout_status: "valid"
closeout_covered: "yes"
mapping_confidence: "high"

metrics:
  revert_needed_after_fix: false
  reviewer_edit_effort: 1

failure_flags:
  hard_failure: false
```
'''


def test_round_a_evaluator_passes_when_summary_and_mapping_are_consistent():
    root = _tmp_dir("pass")
    _write(root / "docs" / "ab-v1.2-run-ledger.md", _base_ledger())
    _write(
        root / "artifacts" / "session-index.ndjson",
        json.dumps(
            {
                "session_id": "session-001",
                "closed_at": "2026-05-11T10:01:00+00:00",
                "closeout_status": "valid",
                "task_intent": "docs-fix",
                "has_open_risks": False,
            }
        )
        + "\n",
    )

    result = evaluate_round_a(
        root,
        commit_timestamp_resolver=lambda _root, _commit: datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
    )

    assert result.ok is True
    assert result.data_consistency["summary_count_match"] is True
    assert result.data_consistency["summary_detail_entry_match"] is True
    assert result.closeout_quality["completion_contract_pass_rate"] == 1.0
    assert result.rollout_gate["expand_ready"] is True


def test_round_a_evaluator_fails_on_summary_detail_mismatch():
    root = _tmp_dir("mismatch")
    ledger = _base_ledger(summary_count="2", summary_ratio="1/2")
    _write(root / "docs" / "ab-v1.2-run-ledger.md", ledger)
    _write(
        root / "artifacts" / "session-index.ndjson",
        json.dumps(
            {
                "session_id": "session-001",
                "closed_at": "2026-05-11T10:01:00+00:00",
                "closeout_status": "valid",
                "task_intent": "docs-fix",
                "has_open_risks": False,
            }
        )
        + "\n",
    )

    result = evaluate_round_a(
        root,
        commit_timestamp_resolver=lambda _root, _commit: datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
    )

    assert result.ok is False
    assert result.data_consistency["summary_count_match"] is False
    assert result.data_consistency["summary_ratio_match"] is False
    assert "data_consistency_check_failed" in result.rollout_gate["pause_reasons"]


def test_round_a_evaluator_fails_when_high_mapping_cannot_be_reproduced():
    root = _tmp_dir("bad_high_mapping")
    _write(root / "docs" / "ab-v1.2-run-ledger.md", _base_ledger())
    _write(
        root / "artifacts" / "session-index.ndjson",
        json.dumps(
            {
                "session_id": "session-001",
                "closed_at": "2026-05-11T09:59:00+00:00",
                "closeout_status": "valid",
                "task_intent": "docs-fix",
                "has_open_risks": False,
            }
        )
        + "\n",
    )

    result = evaluate_round_a(
        root,
        commit_timestamp_resolver=lambda _root, _commit: datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
    )

    assert result.ok is False
    assert result.data_consistency["mapping_confidence_reproducible"] is False
    assert result.data_consistency["inconsistent_high_mappings"] == ["2026-05-11-docs-fix"]


def test_round_a_evaluator_accepts_legacy_semantic_blocks_without_explicit_run_source():
    root = _tmp_dir("legacy_semantic_block")
    ledger = '''# AB v1.2 Run Ledger

## Quick Log Table

| run_id | arm | task_id | closeout_status | hard_failure | anchoring_fail | disposition | accepted_change_count | runtime_gov_ratio |
|---|---|---|---|---|---|---|---:|---:|
| 2026-05-11-docs-fix | single-arm | docs-fix | valid | false | false | merge | 1 | 0 |

## Run Type Normalization

### Semantic Slice Summary (current)

| run_id | run_source | commit_hash | closeout_covered |
|---|---|---|---|
| 2026-05-11-docs-fix | semantic_slice_commit | abc1234 | yes |
- engineering_run_count = 1
- closeout_covered_runs = 1/1 (semantic slices are continuing to be linked to session closeout ids in the same repo and same working session)

## Run Entries

```yaml
run_id: "2026-05-11-docs-fix"
date_utc: "2026-05-11T10:00:00Z"
arm: "single-arm"
task_id: "docs-fix"
task_type: "cross-file-consistency"
baseline_commit: "base-001"
spec_version: "v1.2"
new_session_confirmed: true
session_id: "session-001"
closeout_status: "valid"
closeout_covered: "yes"
mapping_confidence: "high"

metrics:
  revert_needed_after_fix: false
  reviewer_edit_effort: 1

failure_flags:
  hard_failure: false
```
'''
    _write(root / "docs" / "ab-v1.2-run-ledger.md", ledger)
    _write(
        root / "artifacts" / "session-index.ndjson",
        json.dumps(
            {
                "session_id": "session-001",
                "closed_at": "2026-05-11T10:01:00+00:00",
                "closeout_status": "valid",
                "task_intent": "docs-fix",
                "has_open_risks": False,
            }
        )
        + "\n",
    )

    result = evaluate_round_a(
        root,
        commit_timestamp_resolver=lambda _root, _commit: datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
    )

    assert result.ok is True
    assert result.data_consistency["summary_detail_entry_match"] is True
    assert result.closeout_quality["completion_contract_pass_rate"] == 1.0