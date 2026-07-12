# Payload-Audit Runtime Writer Silence — Findings (2026-07-12)

Status: read-only investigation closing census candidate G. No tool,
hook, gitignore, or census change is made by this document.

## Question

`runtime_hooks/core/payload_audit_logger.py` is called unconditionally
(inside a non-blocking try) by `session_start`'s CLI, yet no tracked JSONL
exists after 2026-03-23. The earlier default-off-gate explanation was
reviewer-rejected because that gate guards only the *governance_tools*
writer. Why is the runtime writer silent?

## Findings (mechanical, re-checkable)

1. **Outputs are gitignored anyway**: `.gitignore:144-145` ignores
   `docs/payload-audit/*.jsonl`. The tracked 2026-03-23 files predate or
   bypassed that rule. So "no tracked JSONL" could never distinguish a
   silent writer from a writing one — tracked evidence was structurally
   impossible after the ignore rule.
2. **Disk truth, this repo**: only the two 2026-03-23 JSONL files exist on
   disk (no untracked newer files). The writer genuinely has not run here
   since the March token-baseline campaign.
3. **Disk truth, consumer**: `D:/meiandraybook/docs/payload-audit/` contains
   `L1-2026-04-24.jsonl` — the writer DID run in a consumer through late
   April (the L1 campaign), then stopped there too.
4. **Root cause — no invoker**: the writer only runs when `session_start`'s
   CLI runs. No current session path invokes it: this repo's
   `.claude/settings.json` has no hooks section at all, and meiandraybook's
   Stop hook calls `session_closeout_entry.py` directly, bypassing
   `session_start`. The only invokers are manual/campaign entrypoints
   (`scripts/run-runtime-governance.sh`, the runtime-smoke skill, tests).

## Conclusion

The runtime writer's silence is fully explained: **its sole caller is not
wired into any current real session**, and even if it ran, its output is
untracked by design. Silence dates match the end of the March (framework)
and April (meiandraybook) token campaigns. This is dormancy of the caller,
not a defect in the writer.

## Implication flagged (outside this slice's scope)

If `session_start` is not invoked by any current session path, the same
applies to the treatment layer it orchestrates (injection, pre-task
advisories) and plausibly to the pre/post-task adapters' "consumer known"
notes, which may be historical. Whether `session_start` *should* be wired
into current sessions is an owner architecture decision, not a defect; a
separate read-only check could establish which census units have a live
invoker today.

## Claim ceiling

- Does not claim the writer or its caller is useless or retirable.
- Does not claim consumer repos other than meiandraybook were checked.
- The census candidate B (rename/merge the two same-named logger modules)
  remains open and separate.
