# Expired test exclusions: revalidation and retirement — 2026-10-03

PR204 head 6675932 failed Full Test Suite and Phase Gate Verification at
`test_real_registry_audit_passes`: EX-001..009 expired on 2026-10-01.
The CI suite otherwise reported 6469 passed, 44 skipped, 33 deselected.
This was a failed suite, not a successful delivery gate.
Local failure-first replay on 2026-10-03 reproduced all nine expired IDs.

Disposition: set all nine entries inactive. Keep original owner, expiry,
justification and revalidation trigger as historical metadata; no renewed
exemption, changed date semantics or relaxed audit. Retired names produce
no `-k` restriction in the canonical filtered-suite command.

Independent readonly reviewer executed from this framework worktree:

```text
python -X utf8 -m pytest tests/test_trust_signal_overview.py tests/test_trust_signal_snapshot.py tests/test_trust_signal_publication_reader.py tests/test_reviewer_handoff_summary.py tests/test_reviewer_handoff_snapshot.py tests/test_reviewer_handoff_reader.py tests/test_reviewer_handoff_publication_reader.py tests/test_release_package_publication_reader.py tests/test_external_repo_version_audit.py tests/test_governance_auditor.py tests/test_runtime_session_start.py -q
59 passed, 20 deselected in 163.30s
```

The command used the reviewer's existing Python environment, not the later
isolated requirements environment. Counts are self-reported execution evidence.

| Entry | Executed local fixture basis | Remaining dependency / boundary |
| --- | --- | --- |
| EX-001 trust_signal | Local contracts, onboarding JSON, temporary publication bundles | Real-repo integration checks remain deselected |
| EX-002 reviewer_handoff_summary | Locally generated release snapshots/bundles, failure fixtures | Real-repo integration checks remain deselected |
| EX-003 reviewer_handoff_reader | Temporary manifests, format/missing-file cases | Real-repo integration checks remain deselected |
| EX-004 reviewer_handoff_snapshot | Local payloads and fixture directories | No shared artifact store in executed default cases; integration remains deselected |
| EX-005 session_start_can_load_domain_contract | Test creates contract, rules and validator | No external sibling checkout |
| EX-006 session_start_can_auto_discover | Test creates discoverable contract | No external sibling checkout |
| EX-007 version_audit | Local repositories/version manifests, current/outdated/missing cases | Uses framework version metadata; no live external HEAD lookup |
| EX-008 governance_auditor | Minimal local projects, missing/drift cases, current framework static checks | Some checkout-dependent checks; release-aware integration remains deselected |
| EX-009 publication_reader | Local manifests, tracked example contract, generated temporary bundles | Real-repo integration checks remain deselected |

`pytest.ini` retains its existing integration marker policy. Neither the
normal full-suite workflow nor Phase Gate uses the name-filter runner.
Retirement restores coverage for callers of that runner and repairs the
expiry audit without weakening the existing ordinary CI suite.

Registry/runner regressions: 35 passed in 1.73s, including synthetic active,
inactive and expired fixtures, preserved retirement history, and observable
dry-run commands without `-k`. No integration success is claimed.
