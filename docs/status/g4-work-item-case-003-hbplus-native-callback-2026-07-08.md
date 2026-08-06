# G4 Manual Work-Item Case 003 - Native Callback Root Cause And Masked Test Assumption (HBPlus.Avalonia)

Event date: 2026-07-08
Record written: 2026-08-06 (retrospective; see Recording Boundary)
Repository: `hbplus.avalonia` (HBPlus.Avalonia), with one dependency change in `hbncm`
Developer: Standy (`standy.huang`) — **not a framework author**
Work item: find and fix why native callbacks never reached the adapter, and
resolve what that fix exposed in the existing test suite
Classification: independent non-author consumer case; product domain
Case status: outcome observed for this work item
G4 status: NOT ACHIEVED

## Plain-Language Result

Native callbacks (`StatesUpdated` and others) never fired, even though
initialization succeeded and real peer connections worked. **The delivery chain
had two blockers, both of which had to be removed**, in two different
repositories:

1. **HBPlus side — no Win32 message pump on the initializing thread.**
   `HostBridge_Initial` was called via `Task.Run`. On Windows it creates a
   hidden window and dispatches most callbacks via `PostMessage` to it; without
   a pump on that exact thread, the commit message records that "those callbacks
   silently never fired".
2. **hbncm side — split singleton.** The C wrapper embedded its own
   `HostBridge` instance in `HostBridgeContext` while the rest of the SDK
   resolved the listener through the process-wide
   `HostBridge::GetHostBridgeImpl()` singleton, so the listener lookup was
   always empty.

With **both** blockers removed, the consumer record reports callbacks firing and
matching polled state in a live two-PC run. That then exposed a second problem:
an existing test had encoded an assumption that had never actually been
exercised, because without a working callback path the test soft-skipped instead
of running.

This is one independent, non-author product-domain case. It is not proof of
transfer, sustained benefit, or that governance benefit exceeds its cost.

## Recording Boundary

This record was written on 2026-08-06 from repository evidence, four weeks after
the events.

**Nothing in this record was re-executed for it.** No build was run, no test
suite was run, and no hardware was connected. Every build result, test count,
and two-PC observation below is reported **as recorded in the consumer's
`memory/2026-07-08.md`**, not as a verified-by-this-record result. Where a
commit lives outside `hbplus.avalonia`, that is stated explicitly.

## Work-Item Boundary

This case groups **one** work item with two phases:

1. root-causing and clearing **both** blockers in the callback delivery chain
   (record 2 of `memory/2026-07-08.md`; commit `7c11d2d` in `hbplus.avalonia`
   plus the reported `hbncm` commit `9d3ab729`);
2. the refactor and the corrected test assumption that the fix made visible
   (record 3, commit `8c528ae`).

Phase 2 is **not** a separate G4 sample. It exists only because phase 1
succeeded — the wrong assertion could not be detected while callbacks were
broken. Counting them separately would inflate the sample count, which
`memory/00_long_term.md` explicitly warns against.

Also excluded from this case: the governance self-audit recorded in the *first*
record of the same file on the same day. That belongs to Case 002's causal
chain, not this one. Same day, same developer, different work item.

Start condition:

- `HostBridge_Initial` succeeded, peer connections and features worked, but
  `HBPlus.Adapter.PeerHarness` never received native callbacks.

End condition:

- Callbacks fired in a live two-PC run and agreed with `GetConnectionState()`
  polling, and the test that had encoded the masked assumption was corrected.

## Evidence Chain

| Stage | Observed evidence | Verifiability |
|---|---|---|
| **Blocker 1 — HBPlus thread/message-pump lifetime** | `HostBridgeAdapter.InitializeAsync` ran `HostBridge_Initial` via `Task.Run`. `HostBridge_Initial` creates a hidden window on Windows and dispatches most callbacks (`StatesUpdated` etc.) via `PostMessage` to it; the commit message states that "without a message pump on that exact thread, those callbacks silently never fired". Fixed by moving to a dedicated long-lived thread pumping `GetMessage`/`DispatchMessage` until `WM_QUIT` | **Locally verifiable** — stated in the `7c11d2d` commit message in `hbplus.avalonia` |
| **Blocker 2 — hbncm split singleton** | `HostBridgeC.cpp` embedded an independently constructed `HostBridge` in `HostBridgeContext`, while `WindowsUIThreadManager` / `ClipboardMonitor` and others resolved the listener via the process-wide `HostBridge::GetHostBridgeImpl()` singleton — two `HostBridgeImpl` objects, so `GetListener().lock()` on the singleton side was always empty | Reported in `memory/2026-07-08.md` record 2 and referenced in the `7c11d2d` commit message. Not independently re-derived here |
| Dependency fix for blocker 2 | The consumer memory reports `hbncm` commit `9d3ab729`, pushed to `test/standy/sdk-dll-validation`, making `HostBridgeContext.bridge` a non-owning pointer to `HostBridge::GetInstance()` | **NOT verifiable from the `hbplus.avalonia` checkout reviewed for this record** — `git log 9d3ab729` there returns `unknown revision`. This does **not** establish that no verifiable `hbncm` checkout exists elsewhere. Reported by the consumer record only |
| Consumer fix (both blocker 1 and the tooling) | `hbplus.avalonia` commit `7c11d2d` (2026-07-08, `standy.huang`) — 20 files, +1212 / −156. Also carries: `SessionPhase` state machine replacing a boolean guard with `IsUsable`/`ThrowIfDisposed` across ~24 handle-dependent methods, `GCHandle` leak prevention, a `ShareStatus` domain enum, the single-collection-fixture `IntegrationTests` redesign (native `HostBridge_Initial` supports one call per process), and the new `PeerHarness` console app | **Locally verifiable.** Commit, stat, and message confirmed in `hbplus.avalonia` |
| How blocker 2 was found | Structured logging across the whole `RegisterCallbacks` native→Subject hand-off (Debug/Information/Warning per event) plus Trace-level Win32 message-pump tracing, added in the same commit. The commit message states this combination "is what allowed finding and confirming the matching hbncm HostBridgeC.cpp singleton-listener bug" | Commit is locally verifiable; the causal attribution is the consumer's. **The evidence does not fix a strict temporal order** between the two blockers' repairs — only that the blocker-1 work and its logging enabled finding blocker 2 |
| Phase 1 result | Build 0 warn/err; `dotnet test --filter Category!=Integration` 212/212 pass; `hbncm` `HostBridgeC` target compiles clean; **live two-PC run** shows `StatesUpdated` firing and `GetConnectionState()` reporting `PeerName=PC24-01/ConnectedReady` | **As recorded.** Not re-run for this record; no hardware was connected |
| Phase 2 — masked assumption | `SingleConnectionConstraintTests.Connected_peer_is_reported_as_a_single_node` asserted `Assert.Single(network.Value)`, wrongly assuming `GetNetworkState()` returns only the peer — described in the record as "an assumption never live-tested before the earlier hbncm singleton fix". First real run against peer PC24-01 showed it returns **all** known nodes (self + peer); assertion changed to check exactly one entry matching the connected peer's name | Reported in record 3; commit `8c528ae` locally verifiable (5 files, +210 / −149) |
| Phase 2 result | Integration suite `HOSTBRIDGE_NATIVE_TESTS=1` against live peer PC24-01: **6/6 pass (was 5/6)**; offline 212/212 pass | **As recorded**, and additionally restated in the `8c528ae` commit message |

## Why Phase 2 Is The More Interesting Half

Phase 1 is an ordinary, well-executed bug fix. Phase 2 is a **coverage illusion
made visible**: a test was green for a reason unrelated to the property it
claimed to check, and could only be shown wrong once the underlying transport
worked. The consumer recorded that reasoning explicitly rather than quietly
editing the assertion.

The forward-looking note in record 2 makes the same point before phase 2
happened — it flags that the integration suite had been "relying on the
soft-skip-if-zero fallback that may have been masking this same bug", and asks
whether an earlier soft-assert should be reverted to a hard assert now that the
root cause is fixed.

### What this actually is, in precise terms

An earlier draft called this "a genuine false-negative observation". That is
stronger than the evidence. Split into three claims:

| Claim | Status |
|---|---|
| The assertion was never really executed, because without a peer connection the test early-returned / soft-skipped | **Confirmed coverage illusion** |
| Once callbacks worked, `Assert.Single(network.Value)` failed against the correct self+peer result — the oracle itself was wrong | **Confirmed test-oracle false positive** |
| The soft-skip had previously granted a false green light to the callback defect itself | **Suspected, not established.** The consumer record says only "*may have been* masking this same bug" |

So this case contributes a **confirmed coverage illusion and test-oracle false
positive; a possible soft-skip false negative was suspected but not
established.** That still falls inside the false-positive / false-negative
observation type `memory/00_long_term.md` lists as required for G4 — but what is
formally contributed here is the false-**positive** side.

It is one observation, not a rate: no observation window is defined and no
denominator exists.

## Governance Decision Effect

**Weaker than Case 002, and stated as such.** What can be shown:

- The work was recorded through the canonical writer with `memory_binding:
  bound`, real commit anchors, and `test_evidence` that separates offline test
  counts from the live two-PC observation.
- Record 3 distinguishes "no behavior change, live-verified against a real peer"
  from the assertion correction, rather than merging them.

What cannot be shown:

- No record states that a governance signal changed what the developer would
  otherwise have done. Unlike Case 002 — where a CI warning was explicitly
  identified and declined — this case shows governance-shaped **recording** of
  engineering work, not governance-caused **action change**.

Do not upgrade this to a decision-effect case without such a statement.

## Owner Interventions

| Item | Status |
|---|---|
| Live guidance from the framework owner during this work | **None — owner attestation, Gavin, 2026-08-06.** Git history can show independent authorship; it cannot prove the absence of side-channel help. Treat as testimony |
| Consumer developer informed that this work is being recorded as G4 evidence | Yes — confirmed by the framework owner, 2026-08-06 |
| Owner corrections to the consumer's conclusions | None recorded |

## Observable Cost

| Measure | Value | Boundary |
|---|---|---|
| Commits in this work item, locally verified | 2 in `hbplus.avalonia` (`7c11d2d`, `8c528ae`) | Countable |
| Additional commit reported | 1 in `hbncm` (`9d3ab729`) | **As recorded** — not verifiable from the checkout reviewed here; not the same evidence grade as the two above |
| Code churn | +1212 / −156 then +210 / −149 | Countable |
| Sessions | 2 session ids (`2026-07-08-hostbridge-callback-fix`, `2026-07-08-native-thread-refactor`) | Countable; **not** two work items |
| Elapsed span | Same day | Countable |
| Human minutes | **Not measured** | Cannot compare |
| Tokens | **Not measured** | Cannot compare |
| Rework baseline | **Not available** | No counterfactual |

Benefit-over-cost remains unestablished, as in Cases 001 and 002.

## Outcome And Recurrence

Outcome: a real defect that made an entire callback surface silently
non-functional was root-caused across two repositories and fixed —
**reported by the consumer record as verified against real hardware** (not
re-run for this record) — and a test that had been passing for the wrong reason
was corrected.

Recurrence: **one work item, one consumer context, spanning two repositories;
no independent recurrence observed.** The record's own next step — re-running
the integration suite to confirm deterministic behavior rather than relying on
the soft-skip fallback — is a follow-up, not a recurrence.

## Transfer Gap

- Same developer, same consumer context, same agent surface as Case 002. This
  case **adds no breadth** on the independence axis; it deepens one existing
  case.
- **No transfer is established.** Both blockers — the Win32 message-pump
  lifetime on the initializing thread, and the `hbncm` split singleton — were
  observed only in this SDK-specific Windows integration context. That is a
  statement about what was observed, not a claim that neither pattern can occur
  elsewhere.
- No second non-author has been observed.

## Known Limitation Of The Current Checkout

The consumer repository's framework submodule checkout is `737fcd48`
(2026-06-24) while the parent-recorded pin is `048201c` (2026-07-15) — the
checkout is 821 commits behind the pin.

For this case the evidence is dated 2026-07-08, before the pin date, so the
effective framework version is the checkout itself. Any later case drawing on
records after 2026-07-15 must establish the effective checkout first.

## G4 Contribution And Claim Ceiling

Contributes:

- One **confirmed coverage illusion and test-oracle false positive** from a
  non-author, which is a distinct evidence type from anything in Cases 001 and
  002. A possible soft-skip false negative was suspected but not established.
- One real engineering outcome **recorded as hardware-verified** by the
  consumer, with the claim boundaries the framework asks for.

Does not contribute:

- Breadth. Same developer, repository, and agent surface as Case 002.
- Decision effect. Governance shaped how the work was recorded, not what was
  done.
- Comparable cost, transfer, recurrence, or benefit-over-cost.
- Any hardware claim verified by this record. All two-PC results are reported
  as recorded by the consumer.

**G4 remains NOT ACHIEVED.** Independence remains at one developer.

## Next Observation

1. The single most valuable missing item across Cases 002 and 003 is unchanged:
   a **second** non-author, in a different repository.
2. For any future case in this repository, capture human time at the time of the
   work. Retrospective records cannot recover it, which is why every cost table
   in Cases 001–003 has the same three empty rows.
3. Do not build measurement tooling to close these gaps. Neither a second
   developer nor a retrospective clock can be produced by a new schema.
