# Gate 3 Structural Non-`repr` Boundary Design Candidate

Status: design-only candidate; not approved, not implemented, and not execution
authority

Date: 2026-08-14

Base: `main@d937d59e4573e365461e2736d10efa8942fdd5be` (merge of PR #68)

Scope: a single structural rendering boundary for every type that holds private
payloads — group B-1 of the five production-wiring preconditions

## Problem

This is not a theoretical hardening. It fired.

During the P3 tranche the first failing test produced a pytest traceback that
rendered a dataclass holding raw stdout, printing `PRIVATE_STDOUT_CANARY` into
the test log. The workaround was a local `__repr__` on the test's own fake. The
production types were left as they are.

The mechanism is ordinary and reproducible today:

```
InjectedContainedResult(returncode=0, stdout=b"PRIVATE_STDOUT_CANARY", …)
repr()      → canary present
str()       → canary present
f"{value}"  → canary present
```

The timing is what makes convention useless here. Rendering happens on
**failure** — an assertion, an unhandled exception, a debug print added while
diagnosing — which is precisely when discipline is least likely to hold. A rule
that says "never format these objects" is enforced by the person having the
worst day.

## Current Repository Truth

Types holding private payloads, verified at the base commit:

| Type | Location | Private fields |
| --- | --- | --- |
| `SyntheticResult` | `gate3_route_v2.py:76` | `stdout`, `final_message`, `workspace` |
| `_ContainedResult` | `gate3_route_v2_codex.py:251` | `stdout`, `stderr` |
| `InjectedContainedResult` | `gate3_final_message_runner_integration.py:349` | `stdout`, `stderr` |

All three are `@dataclass(frozen=True)` with generated `__repr__`, so all three
render their payloads. `str()` and `f"{}"` fall through to the same method.

B-2, once implemented, adds three more: the contained-execution capability, the
sealed activation binding and the activation. Each holds private run
derivation, envelope data and a diagnostic nonce. **B-1 must land before B-2's
implementation** so those types are born inside the boundary rather than
retrofitted — which is the sequencing already decided.

Types deliberately *not* in scope: `CaptureBindings`, `RuntimeAuthority` and
`RuntimeAuthorityV2` hold digests and closed tokens, not payloads. Rendering
them is harmless and sometimes useful.

## Decision: one shared rendering boundary, applied uniformly

A single mechanism, not a per-type convention:

1. every in-scope type declares `@dataclass(frozen=True, repr=False)`, so no
   generated `__repr__` exists to fall back to;
2. every in-scope type inherits a shared base that defines `__repr__`,
   `__str__` **and** `__format__` to return one fixed closed token naming only
   the type — for example `<InjectedContainedResult redacted>`;
3. the token is constant. It carries no field, no length, no count and no
   digest, because a length or count is itself a private observation.

All three methods are required. Overriding `__repr__` alone leaves `str()`
falling back to it and `f"{value:>10}"` going through `__format__`; overriding
`__repr__` and `__str__` still leaves an explicit format spec unhandled.

## The rendering boundary alone does not close assertion output

An earlier revision claimed it did. It does not, and the gap is exactly the path
that triggered B-1.

pytest compares two same-type dataclasses with its own comparator, which reads
`dataclasses.fields()` and prints a per-field diff **without consulting
`__repr__`**. Measured with the boundary in place:

```
E  AssertionError: assert <Sensitive redacted> == <Sensitive redacted>
E      stdout: b'PRIVATE_STDOUT_CANARY' != b'DIFFERENT'
```

Two candidate fixes were measured. One works and one is worse than the problem.

| Mechanism | Result |
| --- | --- |
| sensitive fields declared `field(compare=False, repr=False)` | **closes it.** pytest's comparator filters on `field.compare`, so the field never enters the diff |
| replacing the dataclass with a plain class | **rejected — it leaks more.** pytest then explains the sub-expression: `where <NotADataclass redacted> = NotADataclass(b'PRIVATE_STDOUT_CANARY')` |
| a `pytest_assertrepr_compare` conftest hook | defense in depth only, **not the mechanism**: it lives in test configuration, so the property would vanish for anyone running without that conftest |

### Decision

An earlier revision stopped at `field(compare=False, repr=False)` and accepted
that private payloads would leave `__eq__`. **That cost was unnecessary**, and
it was wrong on its own terms: stdout, stderr, the final message and the
workspace are the primary result data of these types, not incidental metadata.
Two executions differing in their output are not the same execution.

The construction that keeps both properties, measured:

| Element | Purpose |
| --- | --- |
| private fields `field(compare=False, repr=False)` | pytest's comparator filters on `field.compare`, so the field never enters the diff |
| `@dataclass(frozen=True, repr=False, eq=False)` | no generated `__eq__`, so the dataclass machinery does not decide equality |
| explicit `__eq__` reproducing the type's existing generated behaviour | equality stays exactly what it was, payload included |
| explicit `__hash__` reproducing the same, including staying unhashable where the type already is | the equal/hash contract is preserved rather than left to drift |

The `__hash__` line matters and is easy to miss: `eq=False` suppresses the
frozen dataclass's generated `__hash__` as well, so without an explicit one the
type would inherit identity hashing and two equal objects could hash
differently.

### The rule is "reproduce current behaviour", not "compare all fields"

An earlier revision said the explicit methods compare all fields. That
over-generalizes in two ways, and the requirement is narrowed accordingly.

**`SyntheticResult` must stay unhashable when it is.** Its `workspace` field can
be a plain `dict`, and today `hash()` on such an instance raises
`TypeError: unhashable type: 'dict'` — verified at the base commit, alongside
`workspace=None` hashing fine and `InjectedContainedResult` hashing fine. A
hand-written `__hash__` that canonicalizes the mapping to make it hashable would
*add* a capability the type never had. The requirement is therefore to
**reproduce each type's existing generated behaviour exactly**, including that
`TypeError`.

**Hash inequality is not a contract.** Python guarantees only that equal objects
hash equally; unequal objects may collide. An earlier evidence item asserted
that differing payloads hash differently. That assertion is removed.

### Hand-written methods need drift protection, normatively

Replacing generated `__eq__`/`__hash__` with hand-written ones creates a
regression path that no rendering test can see:

1. a field is added to the dataclass later;
2. the constructor and field inventory update normally;
3. the hand-written methods are not updated;
4. every rendering test still passes, while equality has silently stopped
   matching the generated semantics this design promised to preserve.

The protection is therefore a **required evidence item, not a review question**:

- the test retains an expected **field-name inventory** for each result type;
- an independent **reference dataclass** — declared with ordinary generated
  `__eq__`/`__hash__` and the same fields — serves as the oracle for what the
  behaviour must be;
- for each field in turn, one instance is varied in that field alone and the
  production type's equality result is asserted equal to the reference type's;
- for hashable fixtures, the production hash is compared against the reference
  hash;
- for `SyntheticResult` with a `dict` workspace, both the production and the
  reference type must raise the same `TypeError`;
- adding a field without updating the reference inventory **fails the test
  immediately**, which is the point.

This is what keeps the hand-written semantics, introduced here only to stop a
leak, from drifting later.

### B-2's identity-bearing types are governed differently

B-2's capability, sealed binding and activation are admitted by **exact object
identity** — `candidate is exact_object`. Applying result-value equality to them
would let two field-identical instances compare equal, in direct conflict with
that boundary.

For those types B-1 governs **only** the rendering boundary, the private field
metadata and the pytest exclusion. **Their equality and hash semantics belong to
B-2's identity contract**, and this design imposes nothing on them.

**This design therefore changes rendering only.** No equality, hash, field or
constructor semantics change.

### Residual: pytest sub-expression explanation

pytest renders values appearing in the assert expression itself. An assertion
that constructs a sensitive object inline from a literal will still show that
literal, whatever the type does:

```
assert Sensitive(b"PRIVATE_STDOUT_CANARY") == other   # literal is visible
```

No property of the type closes this. It is closed only by test-authoring
practice — bind the payload to a variable and assert on the object — and the
design says so rather than claiming coverage it does not have.

## What this closes, and what it does not

**Closes:** traceback locals, `repr`, `str`, `f"{}"`, `f"{!r}"`, `"%s" %`,
`"{}".format()`, `print`, `logging`, `pprint`, and the pytest dataclass field
diff.

**Does not close:** *access*. All of the following still expose the payload, and
this design does not claim otherwise:

- reading the field directly and rendering that;
- `vars()`, `__dict__`, `dataclasses.asdict()`, `dataclasses.fields()`;
- a sensitive literal written inline in an assert expression;
- a debugger, a memory dump, or C-level inspection;
- serialization by any caller that chooses to write the bytes somewhere.

The boundary makes accidental disclosure structurally harder and deliberate
disclosure still possible. That is the achievable property. **It is not a
confidentiality guarantee**, and no later section may restate it as one.

**`dataclasses.asdict()` is an explicit non-goal.** An earlier revision said
that putting the containing type inside the boundary handles the recursion; that
is false — `asdict` recurses into fields regardless of any base class or
rendering method. Closing it would need a serialization restriction, which is
not in this group.

## Discovery, and what it honestly covers

The failure mode after implementation is not a leak in these three types; it is
the fourth type, added later, that nobody remembers to cover.

An earlier revision claimed inheritance was the only marker with no second list
to drift, and then required a hand-maintained named inventory — which is exactly
a second list. It also claimed the arrangement was durable against future
omissions while admitting the bytes census cannot see a non-bytes payload. Both
claims are withdrawn.

### The mechanism

**A field-level private marker, discoverable by census regardless of type.**

Each private field is declared
`field(compare=False, repr=False, metadata={"private": True})`. The census walks
every dataclass in the in-scope modules, inspects `fields()` metadata, and
requires any type owning a marked field to be inside the boundary.

This is the part that scales past bytes. B-2's capability, sealed binding and
activation hold envelopes, run derivation, an object reference and a nonce —
none of them bytes-shaped — and every one of those fields carries the marker, so
the census finds them without a separate list.

A bytes-shaped census is retained as a **backstop** for a payload field whose
author forgot the marker: any resolved hint containing `bytes`, directly or
inside a union, alias or nested generic, must also be inside the boundary.

### What it does not cover

**A new field that is private, not bytes-shaped, and unmarked is invisible to
both checks.** Nothing in this design catches that, and the design does not
claim to. The marker moves the decision to the moment the field is written,
which is the best available place for it, but it is still a decision a person
must make.

The honest claim is: the boundary covers every field that is marked, plus every
bytes-shaped field whether marked or not. It is not a guarantee against future
omission.

## Scope

### In scope

- the shared rendering base and its three methods;
- applying it to the three existing types;
- the field-level private marker and the census that reads it;
- canary evidence across every rendering path.

### Explicit non-goals and prohibitions

- No claim of confidentiality, secure erasure or protection against deliberate
  access.
- No change to any field **name, type, default, `init` position**, constructor
  signature, public schema, contract byte, authority field or oracle literal.
  `Field.compare`, `Field.repr` and field metadata **do** change — that is the
  mechanism — so the earlier blanket "no change to any field" is withdrawn.
- No new copy/pickle refusals here; B-2 owns those for its own types.
- No implementation, staging, commit, push, MR, credentials, preflight,
  subprocess, network or live execution.

## DONE for a Later Offline Implementation Tranche

`DONE = Every in-scope type declares repr=False and inherits one shared base
defining __repr__, __str__ and __format__ to return a constant closed token
naming only the type; sensitive fields are declared field(compare=False,
repr=False) so the pytest dataclass comparator cannot diff them, while eq=False
plus explicit __eq__ and __hash__ reproduce each result type's existing
behaviour including remaining unhashable where it already is; identity-bearing
types added by B-2 take only the rendering boundary and field metadata, their
equality and hash being owned by B-2's identity contract; canary payloads are absent from repr, str, f-string,
conversion and format-spec output, %-formatting, logging, pprint, assertion
output and exception tracebacks; a field-level private marker makes every marked field
discoverable by census regardless of type, with a bytes-shaped census resolving
postponed annotations as a backstop, and the residual — an unmarked,
non-bytes-shaped private field — recorded rather than claimed closed;
a reference-dataclass oracle proves the hand-written equality and hash have not
drifted from the generated semantics; and no field name, type, default, init
position, constructor signature, public schema, contract byte, authority field
or oracle literal changes.`

This is a proposed later tranche, not current implementation authority.

## Focused Offline Evidence Plan

1. `repr`, `str`, `f"{v}"`, `f"{v!r}"`, `f"{v:>40}"`, `"%s" % v` and
   `"{}".format(v)` each return the closed token and contain no canary;
2. `print`, `logging` at every level, and `pprint.pformat` contain no canary;
3. an assertion failure comparing two in-scope objects produces no canary in
   pytest output — captured from the actual report, not inferred from the token
   — and the sensitive fields are confirmed absent from `dataclasses.fields`
   comparison by asserting `field.compare is False`;
3a. equality remains payload-sensitive: objects differing only in payload
   compare unequal. Equal objects hash equally; **no assertion is made that
   unequal objects hash differently**, because Python permits collisions;
3b. field-drift protection: a reference dataclass with generated methods is the
   oracle; each field is varied in turn and production equality matches the
   reference; hashable fixtures match the reference hash; a field added without
   updating the retained field-name inventory fails the test;
3c. each of the three result types reproduces its existing generated behaviour:
   `SyntheticResult` with a `dict` workspace still raises
   `TypeError: unhashable type: 'dict'`, `SyntheticResult` with
   `workspace=None` still hashes, and `InjectedContainedResult` still hashes;
3b. an assert expression constructing a sensitive object from an inline literal
   is shown to still reveal that literal, documenting the residual instead of
   claiming closure;
4. an unhandled exception whose traceback displays the object produces no
   canary;
5. the token is constant: it does not vary with payload length, field count or
   content;
6. each in-scope dataclass has `repr=False` and does not define its own
   `__repr__` outside the base;
7. the bytes-like census resolves postponed annotations through
   `get_type_hints` and catches `bytes`, `bytes | None`, `Mapping[str, bytes]`
   and an aliased form, each verified by a type added inside the test;
7a. the marker census catches a type whose only private field is **not**
   bytes-shaped — an object reference, a nonce or an envelope — verified by a
   type added inside the test;
7b. the census is shown **not** to catch a private field that is neither marked
   nor bytes-shaped, documenting the residual instead of implying coverage;
8. `dataclasses.asdict` on a containing object is shown to expose the payload
   even when both types inherit the base, documenting the limit rather than
   pretending it is closed;
9. field access still works: the boundary changes rendering only, and the
   existing mapping, disposition and privacy behaviour is unchanged;
10. no schema, contract byte, authority field or oracle literal differs from the
    merged values.

## Affected Surfaces if Later Implemented

- `gate3_route_v2.py` and `test_gate3_route_v2.py`
- `gate3_route_v2_codex.py` and `test_gate3_route_v2_codex.py`
- `gate3_final_message_runner_integration.py` and its test
- one new small module holding the shared base, or the base placed in an
  existing module if that avoids a new import edge

**Changing `gate3_route_v2.py` or `gate3_route_v2_codex.py` alters their module
digests. This costs more than this document originally said, and the correction
is recorded here rather than left in a later note.**

The original text named only invalidated measured preflights, and called that
cost already sunk because a fresh zero-session preflight is required before any
live step regardless. That much still holds.

What it missed, found by implementing it: those two paths are also the promoted
historical candidate source snapshot for the consumed `NON_SUCCESS` pair.
`gate3_route_v2_ab_candidate.py` compares the worktree bytes against
`git show 204965c9…:<path>` and rebuilds the retained manifests from the
currently imported modules, so editing either file breaks the exact
reconstruction of owner-promoted evidence.

Measured by running the directory suite with the B-1 edits present and again
with them stashed: **six regressions** are caused by the edits —
`test_candidate_runtime_inputs_match_source_commit`,
`test_candidate_contract_mutation_is_rejected`,
`test_exact_git_tree_materializes_and_reconstructs_non_success`, and
`test_materialized_runtime_residue_still_fails_closed` in three parametrized
cases. A seventh failure,
`test_exact_candidate_reconstructs_and_validates`, fails in **both** runs: it is
pre-existing, caused by untracked evidence paths already in the directory, and
is not evidence of this conflict.

Underneath is an architectural conflict — historical evidence and active source
sharing one path — which reverting B-1 would not fix. But the omission here is
this document's: **not a defect in the rendering mechanism, which review left
intact, but an affected-surface omission in the approved design.** The design
understated its impact, and that is a design completeness defect, recorded as
such. It is addressed by a separate historical-materialization design, and
**B-1 implementation is blocked until that lands.** Neither the retained
manifests nor the owner pin may be re-derived to accommodate this work: the old
pair ran the bytes at `204965c9…`, and no artifact may imply otherwise.

The capture adapter, its schemas, the oracle module and worksheet, manifests,
owner pins, promotion state, `PLAN.md`, memory and all evidence paths remain
unchanged.

## Review Questions

1. Is a constant token right, or should the boundary allow a type-level
   discriminator that helps debugging without revealing payload properties?
2. Should `SyntheticResult` be in scope, given it lives in the shared route
   module and is used well beyond the Gate 3 runner path?
3. Is a field-level marker the right primary rule, given it still depends on an
   author marking the field at declaration time?
3a. Is a reference dataclass the right oracle for drift, or should the
   production methods be generated from a shared helper so no hand-written copy
   exists to drift in the first place?
4. Should the `asdict` recursion limit be closed rather than documented, given
   it defeats the boundary for any containing object?
5. Does landing B-1 before B-2's implementation actually help, or would B-2's
   types be easier to design correctly if written first and adapted?

## Authorization Boundary

This candidate authorizes no implementation, credentials, preflight, live
execution, staging, commit, push, MR, merge, manifest update, owner-pin update
or promotion. B-2 implementation, route retirement, Group C and the consolidated
contract slice each require their own separate authorization. Gate 3 remains
`NON_SUCCESS`.
