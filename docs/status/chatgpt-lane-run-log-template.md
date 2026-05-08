# ChatGPT Lane Run Log Template

Use one block per run.

---

## Run `N`

- date_utc:
- repo:
- run_id:
- slice_topic:
- primary_targets:
- out_of_scope_targets:

### Completion Contract
- semantic_slice_commit: `pass|fail`
- same_repo_valid_closeout: `pass|fail`
- intent_time_linkage: `pass|fail`
- ledger_yes_high_mapping: `pass|fail`
- overall_completion: `complete|incomplete`

### Mapping Fields
- commit_hash:
- session_id:
- closeout_covered: `yes|no`
- mapping_confidence: `high|low`
- mapping_note:

### Quality Signals
- scope_violation_count:
- claim_overreach_count:
- unintended_change_count:
- reviewer_edit_effort:

### Cost Notes
- engineering_tokens_est:
- governance_tokens_est:
- retry_tokens_est:
- latency_note:

### Validation
- checks_executed:
  - 
- result_summary:

### Follow-up
- gap_type: `none|closeout_missing|mapping_mismatch|intent_mismatch|overclaim_wording|other`
- next_action:

