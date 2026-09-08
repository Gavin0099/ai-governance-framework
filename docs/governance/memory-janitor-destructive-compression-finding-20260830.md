# Memory janitor destructive-compression finding — 2026-08-30

Status: **CONFIRMED OPERATIONAL SAFETY FINDING / ACTIVE CLEANUP PROHIBITED**

This finding records a bounded, reproduced failure in the current memory-janitor
cleanup path. It is an operational containment authority only. It creates no
Gate 3 validity requirement, changes no experiment criterion, and authorizes no
memory cleanup or replacement compression design.

## Exact observation identities

The observation was made at repository `HEAD`
`d3b28213513589cfec8b95edd4965cd631052449`.

The observed committed janitor implementation was:

```text
path:        governance_tools/memory_janitor.py
blob:        e9c550f0c8f4f9ffdb9fa947095ac774f4fdd966
blob SHA-256: 90d5d6263301bea98051b61bcfc2784125ab6f94178cb5ba1b7e8f2d5c409c9d
blob bytes:   16,409
blob LF / CR: 394 / 0
```

The clean checked-out file had CRLF line endings: SHA-256
`d001f2300755c939f8ed0dbed1f9de7261f0c10d99396401d76df224b81f2fb5`,
16,803 bytes, 394 LF and 394 CR. The blob and worktree identities are stated
separately so line-ending normalization is not mistaken for byte equality.

The observed dirty-worktree active projection was:

```text
path:        memory/01_active_task.md
SHA-256:     38680653be7302482a0736af7d2ab92a282bc3fa311362f7a56db90c04824d78
bytes:       11,447
characters:  11,435
lines / LF:  159 / 159
CR / BOM:    0 / absent
trailing LF: present
```

The file was `CRITICAL` because its character count exceeded the 10,000-character
hard limit even though its 159 lines were below the 200-line hard limit.

## Confirmed destructive active-projection behavior

`execute_cleanup(...)` first writes the full decoded text to an archive file.
It then constructs the replacement active projection from only:

- the opening `min(20, line-before-Next-Steps)` lines; and
- the first existing `## Next Steps` section.

It does not construct and validate a replacement current state, prove semantic
coverage, or verify a byte-exact archive before replacing the active projection.
For the exact active-task identity above, the algorithm retains lines 1–20 and
84–93. It removes lines 21–83 and 95–159 from the active retrieval surface.
It also cuts the multi-line current-focus bullet beginning at line 20 away from
its continuation on lines 21–23.

Decision-relevant content in the discarded active region includes:

- `## Open Risks`, lines 95–109;
- `## Claim Ceiling`, lines 111–135; and
- the current Gate 3 progression at lines 149–159, including the rev9 STOP,
  corrected pin-before-first-authoritative-release basis, PLAN authority audit,
  and committed PLAN authority checkpoint.

The retained `## Next Steps` at lines 84–93 still describes the older M3-b
sequence. Therefore the current algorithm can replace newer Gate 3 state with a
stale continuation while reporting cleanup success.

This is destructive to active retrieval and current-state semantics. This
finding does **not** claim that every archived byte is permanently lost: the
implementation attempts a text-mode full-content archive first. The defect is
that no verified-archive plus validated-replacement cutover exists before the
active projection is replaced.

## Unsafe guidance and actual mutating entrypoint

The current human guidance is internally inconsistent and unsafe:

- `CRITICAL` warning output recommends `python memory_janitor.py --clean`;
- `--clean` is not registered by the current argument parser;
- the human `CRITICAL` plan recommends the actual mutating `--execute` path;
- the JSON `CRITICAL` plan emits `execute_cleanup_now`; and
- `EMERGENCY` warning output requires stopping and forcing cleanup.

Rejecting the unregistered `--clean` option alone is not containment. The
actual mutating `--execute` / `execute_cleanup(dry_run=False)` path must also
fail closed until a separately authorized verified archive and replacement-state
cutover exists.

## Operational prohibition

Until a containment change is committed and verified:

> Do not run `governance_tools/memory_janitor.py --clean`, `--execute`, or call
> `MemoryJanitor.execute_cleanup(dry_run=False)` against the current
> `memory/01_active_task.md`.

CRITICAL or EMERGENCY pressure does not override this prohibition. The safe
response is to preserve the input unchanged and require a separately authorized
workflow that produces a verified archive and a validated replacement state
before cutover. Agents must not retry the legacy destructive command.

## Containment boundary and non-claims

The minimal authorized containment is limited to removing unsafe cleanup
recommendations, making the legacy mutating entrypoint fail closed without
rewriting active memory, and adding focused regression tests.

This finding does not:

- authorize archive creation, active-memory rewrite, compaction, or cleanup;
- design a replacement archive, lifecycle, or cutover subsystem;
- establish a new Gate 3 blocker, validity predicate, or evidence standard;
- modify or reinterpret PLAN, preregistration, rev9, Release-Order authority, or
  any counted experiment result;
- prove that the attempted archive is durable, byte-identical, or irrecoverable;
  or
- authorize provider work, Gate 3 implementation, network activity, push, or
  unrelated dirty-work handling.
