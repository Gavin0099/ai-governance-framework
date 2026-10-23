# Claude formal closeout entry — design candidate 2026-10-23

Status: **DESIGN CANDIDATE / UNREVIEWED**. This document specifies scope. It is
not an implementation authorization, and it does not claim that any tranche
below has been built, reviewed or validated.

Issue: #233. Related: #231 (spec, open, not modified), #232 (Claude session
lifecycle implementation, open, not modified).

Architecture impact preview for `governance_tools/closeout_handoff.py` at
`scope=feature`: `recommended_risk=medium`,
`recommended_oversight=review-required`,
`expected_validators=architecture_drift_checker`,
`required_evidence=architecture-review`. Touched-file set below is provisional.

## Problem

There is no usable explicit formal closeout command for any agent.
`manage_agent_closeout print-manual` emits
`--trigger-mode manual_fallback` for all five adapters (Claude, Copilot, Gemini,
ChatGPT-web, Codex — `manage_agent_closeout.py` lines 435, 658, 784, 854, 1090),
and `session_closeout_entry` rejects that mode unconditionally in two
independent places:

- `session_closeout_entry.py:752` — CLI early exit, `RELEASE_PROOF_INVALID`
- `session_closeout_entry.py:529-530` — library guard,
  `trigger_mode in ALLOWED_TRIGGER_MODES and trigger_mode != "manual_fallback"`

Removing the first guard alone does not reach a working path; it hits the
second. The rejection is deliberate: the receipt writer cannot produce the
release proof R2 requires.

The consequence for Claude is a closed ownership loop:

1. `acquire_owner` admits a *different* session only when
   `owner.state == "RELEASED"` (`shared_closeout_ownership.py:304`), otherwise
   `OWNER_CONFLICT`.
2. Only `finalize_release` sets `RELEASED`, and it requires a receipt
   (`shared_closeout_ownership.py:457-466`).
3. The only receipt-producing CLI rejects `manual_fallback`.

So Claude session B can read session A's summary but cannot take ownership, and
no command can release A.

## Target outcome

One verified scenario, and nothing more:

> Claude session A has saved its summary. The user explicitly asks A to close
> out. The system validates the required evidence and releases A's ownership, so
> Claude session B can acquire ownership and save a new summary.

Two acceptance properties, both of which must hold:

- **No wrongful release.** Ownership is never released without a valid
  release proof bound to that exact session, worktree, candidate and receipt.
- **No permanent block.** A session that has legitimately closed out does not
  leave subsequent work stuck.

## Verified finding: `closeout_handoff` is the right core, and a CLI wrapper is not enough

The handoff core's state machine is provider-agnostic and reusable as-is: R2
exclusion, ownership transition, release proof, `validate_finalization`,
`validate_recovery_readiness`, `consume_exact_request`.

Its **admission layer** is Codex-bound in five enumerable literals, and two
prerequisites do not exist for Claude at all. Measured on `main@4498103e`:

| Layer | Requirement | Claude today |
| --- | --- | --- |
| Session id | `r2._ID` = `[A-Za-z0-9][A-Za-z0-9_-]{0,127}` | **OK** — the UUID `4bd12297-de1b-4a97-a79f-8a4e7c73292f` matches |
| R2 / release proof / finalization | provider-agnostic | **OK** — reusable unchanged |
| Session envelope | `artifacts/runtime/sessions/<sid>/session-envelope.json` matching `envelope_sha256`, else `ENVELOPE_DRIFT` (`_live`) | **MISSING** — 2180 envelopes exist, **0** are UUID-shaped |
| Transcript retention | in-repo immutable locator under `artifacts/runtime/handoff-transcripts/<sid>/` | **MISSING** — Claude transcripts live at `~/.claude/projects/<slug>/<sid>.jsonl`, outside the repo |
| Transcript byte identity | first record `{"type":"session_meta","payload":{"id":<sid>,"cwd":<root>}}` (`_validate_native_snapshot`) | **MISMATCH** — first record is `type: queue-operation` with top-level `sessionId`; `cwd` first appears at record index 2 (`type: user`) |
| Event admission | `native_event.provider == "codex" and event == "SessionEnd"` (`_validate_request`) | **REJECTS** `claude` |
| Snapshot kind | `source_kind == "codex_sessionend_observed_snapshot"` (`_validate_native_ref`) | **REJECTS** a Claude kind |
| Publisher | `publisher_version` ∈ {`core-v1-fixture`, `native-publisher-v1`} | **No Claude value** |

Two conclusions follow.

- The issue's own note is right that `closeout_handoff` "只是程式庫，沒有 CLI 入口",
  but adding a CLI is the *smallest* part of the work. The blocking work is
  admission: an envelope, an in-repo snapshot, and a third qualified provider.
- **Nothing here requires relaxing the `manual_fallback` rejection.** The formal
  entry is a new, qualified path that produces a real release proof. Both R2
  guards stay exactly as they are. That is the preferred direction, not a
  workaround for it.

## Scope

1. A **Claude transcript snapshot producer**: copy the observed session JSONL
   into `artifacts/runtime/handoff-transcripts/<sid>/snapshots/<sha256>.jsonl`
   with its manifest and ref, under the existing
   `owned-sessionend-snapshot` retention semantics and the existing
   `MAX_SNAPSHOT_BYTES` cap.
2. A **`ClaudeTranscriptProvider`** alongside `FixtureTranscriptProvider` and
   `NativeTranscriptProvider`, with its own `source_kind`, `publisher_version`
   and a byte-identity check matching Claude's actual record shape: session id
   from a top-level `sessionId`, and `cwd` from the first record that carries
   one, rather than a `session_meta` first record.
3. **Event-provider admission** widened from the `"codex"` literal to an
   explicit allow-list that includes `claude`, keeping `event` bound per
   provider.
4. A **session envelope for Claude sessions**, using the existing envelope
   schema (`closeout_path`, `provider`, `repo_head_before`, `schema_version`,
   `session_id`, `started_at`).
5. A **CLI entry** that performs the explicit formal closeout for the one
   scenario above and prints a machine-readable result.
6. `manage_agent_closeout print-manual` for Claude points at that entry instead
   of the unusable `manual_fallback` command.

## Non-goals

- **Not** relaxing, bypassing or re-qualifying the `manual_fallback` rejection
  at `session_closeout_entry.py:529-530` or `:752`.
- **Not** changing R2 release-proof requirements, the receipt schema, or the
  ownership state machine.
- **Not** "release ownership without closing out". That remains deferred; it is
  a governance bypass shaped like a convenience.
- **Not** automatic closeout on exit. #231/#232 already decided against it.
- **Not** touching `runtime_hooks/adapters/claude_code/session_lifecycle.py`,
  `governance_tools/manage_agent_closeout.py` or any other file owned by the
  open #232, nor #231's proposal. Tranche 1 must not collide with them; the
  `print-manual` change (scope item 6) is sequenced after #232 lands.
- **Not** a manual fallback for Codex, Copilot, Gemini or ChatGPT-web. Their
  `print-manual` text stays as it is until this path is proven for Claude.
- **Not** fidelity review of the 2026-10-23 memory cutover, and **not** driving
  memory from WARNING to SAFE. Neither is a prerequisite for #233.

## Affected surfaces

Provisional, pending the first diff:

- `governance_tools/closeout_handoff.py` — provider class, admission literals
- a new snapshot producer module under `governance_tools/`
- a new CLI entry module under `governance_tools/`
- `artifacts/runtime/handoff-transcripts/<sid>/**` — new runtime area usage
- `artifacts/runtime/sessions/<sid>/session-envelope.json` — new producer
- `tests/` — new negative-first test module
- `docs/governance/` — this document

## Boundary and API considerations

- The provider triplet (`schema_version`, `publisher_version`, provider class)
  is currently a closed correspondence enforced in `_live`. Adding a third
  member must extend that correspondence explicitly, not loosen it to "any
  provider".
- `_validate_request` derives `request_id` from `_sha(canonical_bytes(binding))`.
  Any new binding field changes every request id, so the Claude path should
  reuse the existing `_BINDING` key set rather than adding keys.
- Claude's transcript lives outside the repository and outside Git. The snapshot
  is therefore *observed bytes*, and the existing `AUTHORITY` constants
  (`completeness: unqualified`, `decision_authority: none`) must be preserved
  verbatim. The snapshot is evidence of what was observed, never proof of
  completeness.
- `canonical()`-style path rules in the R2 layer reject symlink and junction
  placements. A snapshot producer must write real files in the repository area.

## Failure paths and risk points

- **Wrongful release** is the severe one: a provider that validates less than
  the Codex path would let a session release ownership on weaker evidence.
  Mitigation: the Claude provider must be *equally* strict in binding session,
  worktree, candidate, envelope and bytes; only the byte *shape* differs.
- **Transcript forgery.** The snapshot is local bytes; the core already
  disclaims anti-forgery authority. This spec must not claim more.
- **Partial transcript.** Claude's JSONL is appended during the session, so a
  snapshot taken at closeout is a prefix of nothing later. `EMPTY_TRANSCRIPT`
  and the size cap already exist; completeness stays unqualified.
- **Permanent block.** If validation fails after ownership moves to
  `HOLD/closeout_pending`, the session must remain recoverable via the existing
  `validate_recovery_readiness` path rather than needing a hand-edited
  `owner.json`.
- **Envelope drift.** An envelope written at session start and a repo head that
  moves during the session must not make closeout impossible;
  `repo_head_before` is recorded, not required to still be HEAD.

## Evidence plan

Negative-first. The first tranche is not meaningful unless these fail closed,
and each must be a distinct asserted error code, not a generic exception:

| # | Case | Expected |
| --- | --- | --- |
| N1 | `native_event.provider` is an unlisted provider | `INVALID_EVENT` |
| N2 | Claude request submitted with `NativeTranscriptProvider` | `TRANSCRIPT_RETENTION_UNQUALIFIED` |
| N3 | `publisher_version` not the Claude value | `INVALID_PUBLISHER` |
| N4 | snapshot bytes altered after the manifest | `TRANSCRIPT_BYTES_MISMATCH` |
| N5 | snapshot's `sessionId` ≠ request session id | `TRANSCRIPT_SESSION_MISMATCH` |
| N6 | snapshot's `cwd` ≠ consumer root | `TRANSCRIPT_SESSION_MISMATCH` |
| N7 | no session envelope for the session id | `ENVELOPE_DRIFT` |
| N8 | envelope bytes changed after publication | `ENVELOPE_DRIFT` |
| N9 | request binding session ≠ current owner | `OWNER_REQUEST_MISMATCH` |
| N10 | generation mismatch against `owner.json` | `GENERATION_MISMATCH` |
| N11 | session already consumed | `CONSUMED_SESSION` |
| N12 | empty or whitespace-only snapshot | `EMPTY_TRANSCRIPT` |
| N13 | snapshot over `MAX_SNAPSHOT_BYTES` | `SNAPSHOT_CAP_EXCEEDED` |
| N14 | `manual_fallback` still rejected by both guards | `RELEASE_PROOF_INVALID` ×2 |
| N15 | locator pointing outside the handoff area, or via a link | rejected |

Then two positive cases:

| # | Case | Expected |
| --- | --- | --- |
| P1 | A closes out formally | `owner.state == RELEASED`, release record and receipt present |
| P2 | B then acquires ownership and saves a summary | no `OWNER_CONFLICT`, generation increments |

Plus the repository's own gates: `memory_workflow --check --run-guard`,
`architecture_drift_checker`, and the `architecture-review` evidence the impact
preview requires. N14 is the regression guard that this work did not quietly
become the thing it was meant to avoid.

## Implementation tranche recommendation

**Tranche 1 — admission only, no CLI, no `manage_agent_closeout` change.**
The Claude provider, the snapshot producer, the envelope producer, the widened
event allow-list, and N1–N15 plus P1. Nothing in #232's file set. This is the
smallest tranche that still proves the thing in question: that a Claude session
can produce a release proof R2 accepts, without relaxing R2.

Tranche 2 — the CLI entry and P2 (B acquires after A releases).

Tranche 3 — after #232 lands, point Claude's `print-manual` at the real entry.

Tranche 4 — only if the owner wants it: the same path for other adapters.

Tranche 1 is `review-required` at medium risk. It should be reviewed on its
exact head before Tranche 2 begins, because an admission layer that validates
too little cannot be repaired by a later CLI.
