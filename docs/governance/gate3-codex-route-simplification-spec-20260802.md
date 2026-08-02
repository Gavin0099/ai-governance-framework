# Gate 3 Codex Route — Simplification Specification

Status: **draft for independent review**. Not signed, not promoted, not
authorized. Changes nothing at runtime.

Written 2026-08-02 after canary v6 failed at `packet_build` and Gate 3 was
paused with counted execution at zero.

## Why this exists

Six authorized live attempts produced six failures. Four of them were a pinned
expectation not matching reality, and each was a *different* pin:

| Run | Failure | Kind |
|---|---|---|
| v1 | cleanup residue | setup |
| v2 | rollout must contain one world_state | pinned expectation |
| v3 | route_prepare, zero sessions | setup |
| v4 | arm A source parse | pinned expectation (wrapper) |
| v5 | arm B source parse | pinned expectation (wrapper) |
| v6 | `originator` differs from frozen context | pinned expectation (context) |

The pattern is structural, not bad luck: **the failure surface is the size of
the frozen surface**. Every pinned literal is an independent way for an
authorized pair to end without producing evidence about the question being
studied.

The correction is not to pin less because pinning is inconvenient. It is to
pin each field in the way that actually protects the comparison, which is not
the same for every field.

## What this specification does not decide

- It does not classify `originator`. That needs a semantic ruling first; see
  "Open rulings".
- It does not authorize the calibration probe.
- It does not change any contract, runtime, or candidate manifest.

## Classification model

Four dispositions. Each field gets exactly one, with a reason.

**A. Hard frozen** — a literal value fixed before the experiment. Differing
means it is a different experiment. Fail closed.

**B. Cross-arm equal** — no literal is pinned; both arms must carry the same
value, and it must not change across the runs of one experiment. Fail closed
on inequality, not on the value itself.

**C. Normalized then equal** — the two arms necessarily differ in raw form
(each has its own workspace), so the value is normalized first and the
normalized forms must match. Fail closed after normalization.

**D. Observational** — recorded in evidence, never compared, never a cause of
failure. Identity information that cannot affect what the comparison means.

The distinction that matters: **A and B both fail closed.** B is not weaker
governance, it guards a different and more accurate property — that the two
arms ran alike and the harness did not shift mid-experiment — instead of
guarding that a value equals a string frozen during one rehearsal on
2026-07-29.

## Per-field classification

### Hard frozen (A)

| Field | Reason |
|---|---|
| `model` | A different model is a different experiment. |
| `comp_hash` | Model build identity; the comparison is about one build. |
| `cli_version` | Tool surface; a different CLI can expose different tools. |
| `reasoning` | Directly shapes producer behaviour. |
| `approval_policy` | Determines what the producer may do unattended. |
| `permission_profile` | Capability boundary. |
| `sandbox_policy` | Capability boundary. |
| baseline commit | The task's starting state. |
| task packet | The task itself. |
| treatment packet | The studied factor. |
| permissions, budget | Capability and cost envelope. |
| harness contract, scorer rubric | Measurement instrument. |

These stay literal-pinned and preregistered. Nothing in the six failures
argues against any of them.

### Cross-arm equal (B)

| Field | Reason it need not be a literal |
|---|---|
| `history_mode` | Affects both arms identically if equal; the specific mode is not the studied factor. |
| `thread_source` | Same. |
| `source` | Same, subject to the `originator` ruling below, which may pull this with it. |
| `multi_agent_version` | Same. |
| `personality` | Behaviour-relevant, so equality is required; the particular value is an environment fact. |
| `summary` | Same. |
| `realtime_active` | Same. |
| `timezone` | Affects date handling; must match across arms and across the experiment. |
| `model_provider` | Implied by `model`; equality is the real requirement. |

Anchoring rule: the value is fixed by the **calibration probe**, recorded in
the preregistration, and then treated as hard frozen for the experiment. It is
never anchored by a counted run.

### Normalized then equal (C)

| Field | Normalization |
|---|---|
| `cwd` | Replaced by the arm's public context token before comparison. |
| `workspace_roots` | Same. |
| paths inside base and developer instructions | Same; already implemented as `_normalised_context_view`. |

These *must not* be cross-arm equal in raw form: each arm has its own
workspace by construction. The existing normalization is correct; this
specification only names the category it belongs to.

### Observational (D)

| Field | Reason |
|---|---|
| session id | Identity only; already required to be distinct per arm. |
| timestamps | Ordering evidence, not a comparison control. |
| `current_date` | Recorded. Cross-arm equality is implied by running the pair together; pinning it to the preparation date is what makes a run expire overnight. |

## The counted-run anchoring prohibition

A value observed during a counted run must never become the anchor for that
experiment's expectations. Fixing rules after seeing results is the same
defect as optional stopping: it lets the rules be chosen by the data.

All anchoring comes from the calibration probe, before any counted run, and is
written into the preregistration and signed.

## Calibration probe

A probe is a **single non-counted session**, not a pair.

**It requires its own authorization.** It uses real credentials, starts a real
Codex session and produces a private rollout. Not being a pair does not make
it free. Proposed authorization string:
`non_counted_codex_calibration_probe_only`, exactly one session, no
replacement.

**What it does**: `route_prepare` plus rollout parse only. It records the
observed context identity and a wrapper shape census. It builds no packet,
admits nothing and produces no scorer packet.

**What it must not do**:

- It does not score, and its output is not evidence about the studied effect.
- It does not authorize a pair. A pair remains a separate authorization.
- Its success does not predict that a later pair will pass. A probe reduces
  the risk of one known failure class; it cannot show that every future
  wrapper or context will be admitted.

**Evidence boundary**: the private rollout is wiped by the existing cleanup
path. The public probe receipt carries the observed context field values, the
wrapper shape census and nothing else — no command, argument value, path,
credential, raw output or session identifier. It is subject to the same
`_privacy_violations` refusal as every other published artifact.

The observed context values are the one thing a probe exists to publish, so
they are in scope for the public receipt by design, unlike the corpus scan
where values were classified rather than emitted.

## Open rulings, needed before this specification can be implemented

1. **`originator`.** Not classified here. It may denote a different execution
   surface or a different instruction source, in which case it belongs in
   hard frozen and is a validity control, not identity. It may equally be a
   label with no behavioural consequence, in which case it is cross-arm equal.
   Deciding without evidence is what produced the claim this specification
   exists to correct. The probe should report the observed value and the base
   instruction digest alongside it; the ruling follows that.

2. **Does `source` move with `originator`?** They may describe the same
   distinction. Rule on them together.

3. **Is the Codex live route still the right channel?** Simplification reduces
   the failure surface; it does not make the channel cheap. The alternative is
   a producer channel under direct control, which changes the research
   question from "does the Skill help real Codex" to something narrower.

## Cost of adopting this

Reclassifying context fields changes the signed contract. It requires fresh
independent review, owner exact-byte signature and canonical promotion. The
2026-08-02 approval cannot be reused. There is no shortcut, and this
specification does not claim one.

## Cannot claim

- That the probe is authorized, or that it needs no authorization.
- That `originator` is irrelevant to validity.
- That cross-arm equality is sufficient for every context field.
- That a passing probe predicts a passing pair.
- That Gate 3 may resume, or that counted execution is anything other than 0.
