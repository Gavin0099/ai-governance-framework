from pathlib import Path

from governance_tools.ab_cost_parity_audit import run


LEDGER_SAMPLE = """# AB v1.2 Run Ledger

## Quick Log Table

| run_id | arm | task_id | hard_failure | anchoring_fail | disposition | accepted_change_count | tokens_per_accepted_fix | runtime_gov_ratio |
|---|---|---|---|---|---|---:|---:|---:|
| run-a | A | task-1 | false | false | merge | 4 | TBD | TBD |
| run-b | B | task-1 | false | false | merge | 4 | 3200 | TBD |

---

```yaml
run_id: "run-a"
arm: "A"
task_id: "task-1"

change_scope_metadata:
  accepted_change_count: 4

metrics:
  actionable_fix_latency_sec: "TBD"
  tokens_per_reviewer_accepted_fix: "TBD"
```

```yaml
run_id: "run-b"
arm: "B"
task_id: "task-1"

change_scope_metadata:
  accepted_change_count: 4

metrics:
  actionable_fix_latency_sec: 300
  tokens_per_reviewer_accepted_fix: 3200
```
"""


def test_ab_cost_parity_audit_reports_missing_fields(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.md"
    markdown_out = tmp_path / "out.md"
    json_out = tmp_path / "out.json"
    ledger_path.write_text(LEDGER_SAMPLE, encoding="utf-8")

    exit_code = run(ledger_path=ledger_path, markdown_out=markdown_out, json_out=json_out)
    assert exit_code == 1

    markdown = markdown_out.read_text(encoding="utf-8")
    assert "task-1" in markdown
    assert "run `run-a` (A): missing" in markdown
    assert "quick-log row `run-a` (A): missing `tokens_per_accepted_fix`" in markdown

    report = json_out.read_text(encoding="utf-8")
    assert '"total_missing_items": 3' in report
