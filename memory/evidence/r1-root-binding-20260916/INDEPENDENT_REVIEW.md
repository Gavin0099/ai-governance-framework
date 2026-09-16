# R1 independent code review — 2026-09-16

Verdict: CHANGES_REQUESTED / NOT COMMIT_READY.
Independent reviewer: /root/r1_independent_review (AI code review, not human or external certification).
Subject: uncommitted candidate on base e5d819b47be58384eeda1a2d7672f9de16e1b63b.
Exact four-file hashes: source-snapshot.json; rechecked unchanged after review.

No P0/P1 identified. Two P2 findings violate the owner's frozen acceptance and block commit readiness. No production changes or remediation were made during this review.

## P2-1 — Legacy writer overwrites an existing root-bound envelope

Location: runtime_hooks/core/_canonical_closeout.py:176.
Real legacy caller: runtime_hooks/core/session_start.py:263.

The existing-envelope and completion checks are confined to the branch with bound_consumer_root. A caller without that argument writes directly to the final envelope path. After qualified Codex startup creates v1.1, a legacy invocation can downgrade it to v1.0, remove repo_binding and change original envelope bytes/started_at. Subsequent Codex startup accepts that v1.0 as legacy state.

Minimal sequence, reproduced in a disposable Git repository (root):

```python
run({"hook_event_name": "SessionStart", "source": "startup",
     "session_id": "s1", "cwd": str(root)}, root)
before = envelope_path.read_bytes()
write_session_envelope("s1", root, provider="codex")
after = read_session_envelope("s1", root)
```

Observed: `{"bytes_unchanged": false, "schema_after": "1.0", "binding_after": null}`.

This violates persistent root authority and no-rewrite semantics through an existing production helper. It does not require malicious filesystem access. Preserve genuine legacy v1.0 behavior while preventing an unqualified caller from overwriting existing v1.1. Add a sequence test requiring byte preservation or rejection before mutation.

## P2-2 — Completion-only inconsistency is rejected after mutation

Location: runtime_hooks/adapters/codex/session_start.py:62.
The session directory is created at line 62 and lock opened at line 66; the completion-only check is at line 76.

Minimal reproduction in a disposable Git repository:

1. Create artifacts/runtime/closeout-completions/s1.json without an envelope.
2. Invoke Codex startup for s1.
3. Observe Path.open with a spy for the session lock and inspect the session directory.

Observed: `{"error": "Completion marker exists without envelope", "lock_opened": true, "session_dir_created": true}`.

This is an exposed/pre-existing ordering problem that the new preflight does not cover. It creates no new envelope and no data loss was observed, but it violates the explicit rejection-before-lock/mutation acceptance. Add a preflight for the known inconsistency, retaining the check under the lock for races.

This finding does NOT concern normal resume of an existing valid consumed envelope. The accepted design permits refreshing its convenience marker while preserving envelope/completion bytes and never rebinding or resetting consumption. A ban on that refresh would be a separate contract change.

## Other invariants and evidence limits

- Legacy callers still default to v1.0; no accidental production of v1.1 by an unbound caller was found. Existing adapter repeat events preserve v1.0 bytes.
- Qualified publication uses a sibling temporary file and replace. No accepted half-envelope path was found. Direct writer concurrency was not qualified; formal adapter uses its same-ID lock.
- Same-checkout adapter/writer/shared-reader compatibility is supported by code and author tests. Mixed-version deployed routes remain NOT QUALIFIED.
- Author qualification remains 117 passed in tests.xml. The independent reviewer did not rerun that suite; independent evidence consists of scoped code review and the two disposable reproductions above.
- No consumer, native host, R2, preparation helper, promotion or full Memory E2E qualification is claimed.

## Delivery condition

Merging R1 framework code does NOT authorize installing or enabling the v1.1-producing SessionStart path in any consumer whose bound framework reader compatibility has not been verified.

Already-installed hooks may point at an in-place checkout; advancing that checkout can change the next writer output without reinstalling. Verify actual command bindings and paired readers before such activation/update. Separate installers do not prove universal deployment isolation.

## Disposition

Fix only the two findings in a separately authorized remediation slice, add focused regression cases, rerun affected tests and review the resulting exact diff. No commit, push, PR, merge or consumer activation occurred in this review. R2 remains open.

## Machine response envelope

```json
{
  "mode": "expanded",
  "mode_source": "failed_or_partial",
  "task_authority": "Owner requested independent review of five frozen R1 invariants",
  "scope": "R1 independent code review and review evidence only",
  "done": "Independent review complete; implementation commit readiness blocked",
  "claim_ceiling": "AI scoped review and two disposable reproductions on unchanged uncommitted candidate",
  "not_claimed": ["remediation", "commit readiness", "commit", "PR", "merge", "consumer activation", "mixed-version deployment compatibility", "R2", "Memory E2E"],
  "evidence_refs": ["source-snapshot.json", "INDEPENDENT_REVIEW.md", "REVIEW_PACKET.md", "tests.xml"],
  "risk": "Two invariant-breaking P2 findings; scoped changes remain uncommitted; unrelated workspace state excluded",
  "next_action": "Bounded remediation of the two findings followed by focused regression and re-review"
}
```
