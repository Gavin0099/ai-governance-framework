# Gate 3 M3 — The Framed Transport and the Closed Child

Status: design-only candidate; not approved, not implemented, and not execution
authority. No child interpreter was started to write this, no historical module
was imported, and nothing was materialized. Two read-only measurements were
taken against the local interpreter and are labelled as such below.

Date: 2026-08-18

Revision: 5 — the four live pointers to the authority still named revision 9,
which stopped being the current revision when the parent went to revision 10 in
the same slice. Correcting the parent's changelog and leaving the subordinate
document pointing at the revision it corrected would have left the same class of
defect the whole reconciliation exists to close: a document deferring to a
surface that has moved. Header, carried-authority statement, bounds pointer and
authorization boundary now name revision 10. The historical statements inside
Decision 3 keep naming revision 9, because revision 9 is where the normative
bullet was introduced and that is a fact about the past, not a pointer.

Revision 4 — the round-trip clause rested on a case that cannot occur. Strict
UTF-8 decoding is canonical: bytes that decode successfully re-encode to exactly
those bytes, and the non-canonical forms that would break it — overlong
sequences, encoded surrogates, five-byte forms, anything above `U+10FFFF` — are
rejected at the decode, before the clause is reached. Measured rather than
recalled: across every 1-, 2- and 3-byte sequence, 2,668,544 decoded
successfully and **zero** failed to round-trip, and each classic non-canonical
form was refused at strict decode. The clause stays as a postcondition, because
what it defends against is a *decoder* that stops being strict; but its stated
justification and its evidence case both claimed a natural input reaches it, and
neither does. Both are rewritten. This is the same defect twice — an evidence
item that cannot distinguish what it is named after — and it is fixed in the
rationale as well as in the test, because fixing only the test would leave the
document asserting the reason the test no longer has.

Also corrected in the parent document, at revision 10: revision 9's changelog
stated the `sys.path` measurement backwards.

Revision 3 — the conflict revision 2 recorded is resolved rather than carried.
The authority was amended: revision 9 of the parent document replaces the
"same grammar" bullet with the wire grammar, so Decision 3 becomes adopted and
the wire grammar returns to M3-a's scope. One evidence item is added — `e15`,
the wire grammar's own cases and the one-directional differential against
`_checked_relative` — because restoring a surface to scope without restoring
its evidence would specify something that nothing checks. Nothing else moves: the
trusted computing base, the other evidence items and the claim ceiling stand as
revision 2 left them.

Revision 2 — closes four review findings.

- Revision 1's Decision 3 declared a second, stricter path grammar while this
  document also declared revision 8 unchanged. Revision 8 requires the child to
  apply *the same grammar the parent applied*, so the two documents specified
  different things and the subordinate one loses. Decision 3 is now marked
  **blocked** and carries the exact amendment revision 8 needs; it is not
  authority until that amendment is made.
- Evidence `e3` asked for a legal path whose code-point order and UTF-8 byte
  order differ. No such path exists: byte-wise ordering of well-formed UTF-8
  preserves scalar-value ordering, so on the accepted domain a decoded-string
  sort is observationally identical to a byte sort and `e3` could not have
  distinguished them. Replaced with comparators that *are* distinguishable.
- The trusted runner's path was treated as if executing it were free. What binds
  that path to reviewed bytes was never stated, and "defends against a corrupted
  parent" was written broadly enough to imply it covered the spawn target. A new
  section names the trusted computing base and narrows the claim.
- "M3-a executes nothing" was false as written: M3-a runs an encoder, a decoder,
  a JSON parser and an inventory derivation in the parent process. The ceiling
  now says what is actually true — no spawn, no historical code.

Revision 1 — initial candidate.

Base: `feat/gate3-historical-materialization@eea9a7f4e633fd6f179c971fd8dcba0054ced654`

Design authority this document is subordinate to:
`docs/governance/gate3-historical-evidence-materialization-design-candidate-20260815.md`
revision 10, whose sections *The parent-to-child channel — normative*, *The
child executes verified bytes, not a path* and *Bootstrap validation happens
before any historical code runs* remain the specification of the wire format,
the bounds and the authority chain. **This document restates none of them**, and
where it would contradict one it says so and stops rather than overriding it.
Revision 9 exists because it did stop, once: the amendment quoted in Decision 3
was made in the authority rather than asserted here. Revision 10 carries that
bullet forward unchanged and corrects a sentence in revision 9's own changelog,
so revision 10 is the current authority and revision 9 is where the normative
grammar was introduced.

It exists because implementing them made three questions answerable that were
not answerable while they were only written down, and because the answer to the
first one constrains what the other two are allowed to look like.

---

## What is already decided and is not reopened here

The framing table, the bounds table, the record order, the derived stream
maximum, the authority chain and its four steps, and the rule that the child
re-verifies against a frozen literal rather than against the stream: all of that
is settled in revision 10 and is carried unchanged. The arithmetic of the derived
maximum was re-checked while writing this and holds:
`20 + 1,048,580 + (64 × 550) + 33,554,432 = 34,638,232`.

What was never decided is **how the trusted child code gets into the child**,
and that turns out to constrain everything else.

---

## Measurement: the child's import roots, and what they cost

Two facts, measured on the local interpreter and true of it rather than of
CPython in general.

Interpreter: `3.12.10 (tags/v3.12.10:0cc8128, Apr 8 2025) [MSC v.1943 64 bit
(AMD64)]`.

Running a script **by path** under `-I -S -B`:

| Flag state | Observed |
| --- | --- |
| `sys.flags.isolated` | `1` |
| `sys.flags.no_site` | `1` |
| `sys.flags.dont_write_bytecode` | `1` |
| `sys.flags.safe_path` | `True` |

and `sys.path` was exactly four entries, all under the interpreter's own
installation: `python312.zip`, `DLLs`, `Lib`, and the installation root.
`site-packages` was absent, and — the fact that matters — **the script's own
directory was absent too**. Without `-I` the same script's directory was
`sys.path[0]`.

That is the design's `import roots` row delivering exactly what it promised.
It also has a consequence the design did not state:

> **The child cannot import any repo-local module, including the trusted ones
> this design needs it to run.**

Not the transport decoder, not `gate3_historical_bootstrap`, not
`gate3_historical_materialize`. The isolation that keeps the historical modules
from resolving by path keeps the trusted modules from resolving by path in
exactly the same way, because it is one mechanism and it does not take sides.

Three ways out were considered and two are rejected here so they are not
revisited:

- **put the runner's directory on `sys.path`** — rejected. That directory is
  `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/`, which also
  contains the *active* `gate3_route_v2.py` and `gate3_route_v2_codex.py`. It
  would make the present importable inside the process whose entire purpose is
  that the present is not reachable, and it would do so by name, which is the
  selection mechanism this design exists to remove;
- **send the trusted modules over the stream** — rejected as circular. Decoding
  the stream is the thing being delivered;
- **make the trusted child code one self-contained file** — adopted, below.

---

## The trusted computing base, named

The child runs trusted code that arrived by path. Nothing in this design
verifies that path's bytes before the operating system executes them, and until
this section existed the document proceeded as though executing it were free.
It is not free; it is a trust assumption, and an unnamed trust assumption is the
kind this work stream exists to stop making.

**In the TCB for M3:**

| Element | Why it is trusted |
| --- | --- |
| the interpreter executable the parent spawns | selected by the parent; no integrity check is performed on it here |
| `gate3_historical_child.py`, as a **file at a path** | executed by the child as `__main__` before any check this design specifies can run |
| the frozen literals inside it | reviewed, merged code — the same mechanism M1 already relies on |
| the repository checkout and the operating system's resolution of that path | everything above depends on both |

**What "defends against a corrupted parent" does and does not mean.** Revision 1
used that phrase without bounding it. Bounded:

- it covers the parent's **transport and data state** — the stream it builds,
  the inventory it derived, the digests it computed, the bytes it read from the
  materialized tree. A parent wrong or subverted about any of those is caught by
  the child, because the child's authority is a literal the stream cannot reach;
- it does **not** cover the **spawn target**. A parent that launches a different
  interpreter, or points at different runner bytes, has replaced the checker.
  Nothing downstream of that can detect it, because the thing that would detect
  it is what was replaced;
- it does not cover the runner file's bytes. There is no pre-spawn digest check,
  and adding one would not change the previous point: the check would live in
  the parent, and a parent corrupt enough to change the spawn target is corrupt
  enough to skip it. It would defend against runner-file tampering *with an
  intact parent*, which is a narrower and different property. Whether that is
  worth having is a question for M3-b, not an omission being smuggled past here.

**Runner identity and TOCTOU are not solved and are not deferred quietly.** The
path is resolved by the operating system at spawn. The native handle boundary is
not applied to it, so a replacement between the parent forming the path and the
OS opening it is not detected. This is recorded as an **accepted trust
assumption of M3**, not as an M3-b work item, because calling it deferred would
imply a plan exists. If it is to be closed, closing it is its own tranche with
its own design, and it would need the boundary to reach a file the parent hands
to `CreateProcess` — which is not a capability the boundary has today.

---

## Decision 1: one file, two roles

`gate3_historical_child.py` is a single module that:

- the **parent imports** for `encode_stream(...)`;
- the **child executes by absolute path** under `-I -S -B`, as `__main__`,
  where it decodes, re-verifies and loads.

It imports only the standard library. It imports no repo-local module, and a
test asserts that from its AST rather than from a comment, because the property
is load-bearing: the moment it acquires a repo-local import it stops working in
the child, and it stops working in the child *at the point where the child is
already running*, which is the worst place to discover it.

Being one file is what makes the encoder and the decoder share a definition of
the wire instead of agreeing about it. Two files would have been two statements
of the framing table, and this repository has already paid for that mistake
once: a specification that did not retire beside the thing that replaced it.

**The parent still never imports a historical module.** `gate3_historical_child`
is not historical; it is present-day reviewed code that happens to run in both
processes, and it is in the TCB named above.

---

## Decision 2: what the child re-derives, and the honest name for it

Revision 8 requires the child to derive the expected inventory from the verified
candidate-set bytes rather than from the stream. Because the child cannot import
`gate3_historical_bootstrap`, it must contain its own:

- frozen `CANDIDATE_SET_SHA256` literal;
- JSON parse that rejects duplicate keys;
- retained-inventory extraction and record validation;
- runtime-module allowlist and the selection from it.

That is the same work `gate3_historical_bootstrap` does in the parent, written a
second time. **Calling that duplication would be the wrong description, and
calling it independent verification would be an overclaim.** Both are stated
here so neither is assumed:

- it is *not* duplication in the sense of accidental drift, because the
  independence is the mechanism. A child that imported the parent's derivation
  would be trusting the parent's runtime state, and the entire reason the child
  re-verifies is that it does not;
- it is *not* independent verification in the strong sense either. Both copies
  are written by the same author from the same design. It defends against the
  parent's transport and data state being wrong — and only that, within the
  bounds set out in the TCB section above. **It does not defend against a
  mistake present in the design or in the author's understanding of it**, which
  would be made identically in both places, and it does not defend against a
  substituted spawn target.

Two bindings keep the pair honest, and neither is a comment:

1. a test asserting `gate3_historical_child.CANDIDATE_SET_SHA256` equals
   `gate3_historical_bootstrap.CANDIDATE_SET_SHA256`, and the same for the
   runtime-module allowlist, failing on any divergence;
2. a differential test running both derivations over a **named corpus** — the
   real candidate-set bytes plus an enumerated list of mutations — asserting
   they agree on the accepted value and agree on rejecting each listed mutation.

The second is the one that matters. The first would pass if both were changed
together; the second fails if either stops rejecting something in the corpus
that the other rejects. Neither establishes agreement on inputs outside the
corpus, and this document does not claim they do.

---

## Decision 3: the wire path grammar, and the check it is not

Adopted. Revision 2 recorded this as blocked, because revision 8 required the
child to apply "the same grammar the parent applied" and this section declared
two. That was a real conflict and it was resolved in the authority: revision 9
replaces that bullet with the text quoted below. The history is kept because the
resolution is the point — a subordinate document that had simply asserted the
stricter grammar would have left the contradiction in place and unreadable.

`gate3_historical_materialize._checked_relative` rejects a path that could
escape a root before it is joined. The child has no root to join against and
cannot import it, so the wire needs a path check that lives in the child.

These are different checks and do not pretend to be the same:

| Checker | Question it answers |
| --- | --- |
| `_checked_relative` (M2, parent) | can this path escape the materialized root when joined to it |
| wire grammar (M3, both sides) | is this byte sequence a legal repo-relative path to *compare against an inventory* |

The wire grammar is the stricter of the two and is defined positively rather
than by exclusion: a path is legal when its UTF-8 decodes strictly, contains no
NUL, no backslash, no colon, no leading or trailing `/`, no empty segment, no
`.` or `..` segment, no BOM, is at most 512 bytes, and re-encodes to exactly
the bytes received.

That last clause is a postcondition, and it is worth being exact about what it
buys. It is **not** reachable by any legal input: strict UTF-8 decoding is
canonical, so bytes that decode at all re-encode to themselves, and the
non-canonical forms that would break that are refused at the decode. What the
clause defends against is the decoder itself changing — an `errors` mode that
replaces rather than raises, a normalization step added for tidiness, a
codec swapped for a lenient one. Any of those would let two byte sequences
claim one path while the record order is defined on the bytes. The clause costs
one comparison and turns a silent change of meaning into a refusal, which is
why it stays even though nothing on the wire can trip it.

**What the authority now says.** Revision 8's *the child checks* list required
"every path passes the same grammar the parent applied". That could not be
implemented: the parent's check is the containment check, the child never joins
a path, and the child cannot import the module the check lives in. Revision 9
replaces that bullet with:

> - every path passes the wire grammar, which is defined once in the trusted
>   child module and applied identically by the parent when it encodes and by
>   the child when it decodes. It is not the parent's filesystem-containment
>   check: that one answers whether a path can escape a materialized root when
>   joined to it, which the child never does. The wire grammar accepts a subset
>   of what the containment check accepts, and a test asserts that direction
>   over a named corpus.

The subset direction is asserted and the reverse is not. The wire grammar
rejects strictly more, so claiming equivalence would be false, and a test
written to prove equivalence would have to be wrong in one direction to pass.
The named corpus is what makes even the one direction checkable: it is a finite
enumerated list, and no finite list establishes a claim about all inputs.

The rejected alternative is recorded so it is not revisited by default: making
the wire grammar the only grammar and having M2 adopt it. It fails because the
two checks answer different questions — a containment check that stopped asking
about root escape would stop protecting the join it exists to protect.

---

## Decision 4: the encoder enforces the bounds too

Revision 10 states the bounds as things the child checks, and carries them
unchanged since revision 8, which is where they were written. The encoder
enforces them as well, and refuses rather than emitting a stream it knows is
illegal.

Not because the child's check is insufficient — it is the one that matters, and
it stays — but because a parent that can emit an illegal stream has a bug whose
first symptom is a child failing far away from the cause, after a process spawn,
with a closed error code. The encoder's refusal is a *diagnosis* mechanism, and
it is described that way rather than as a second line of defence, because a
second line of defence would suggest the child's check could be relaxed.

The test suite must therefore be able to build illegal streams **without** the
encoder, or every out-of-bounds decoder case would be unreachable. A raw builder
lives in the tests, not in the module: the module has no way to emit an illegal
stream, and the tests have nothing else.

---

## Implementation split

Two tranches, each separately authorized, each reviewed at exact digests.

**M3-a — the transport.** `gate3_historical_child.py` with `encode_stream`,
`decode_stream`, the wire grammar, the frozen literals and the inventory
derivation. Runs in-process in the parent. Spawns no child, compiles nothing,
imports no historical module, and executes no historical code. `ACTIVE = False`.
The wire grammar is defined once in this module and used by both `encode_stream`
and `decode_stream`, which is what makes "applied identically by both sides" a
property of the code rather than a promise about it.

**M3-b — the closed loader and the spawn.** The `__main__` path, the
`-I -S -B` spawn from the parent, the loader over verified buffers, and the
return channel. This is the tranche that first executes historical code, and it
does not begin until M3-a is delivered and reviewed.

M3-a is proposed as the next slice. It is the part with no spawn and no
historical execution in it, which is why it goes first.

---

## Evidence plan for M3-a

Offline, in-process, no spawn, no historical import, no credentials, no
preflight, no live.

| # | Evidence |
| --- | --- |
| e1 | a round trip: encode an inventory, decode it, get the same map back, byte-identically |
| e2 | encoding the same inventory twice produces byte-identical streams, and reordering the input map does not change the output |
| e3 | record order is asserted against an **expected raw byte sequence** written out in the test, not against "sorted" — see the note below |
| e3b | three wrong comparators are each shown to produce a different stream and to be rejected: `str.casefold`, Unicode NFC/NFD normalization of an already-legal path, and `locale.strxfrm` under a non-C locale where one is available, skipped explicitly by name where it is not |
| e4 | each of the six framing fields corrupted independently, each rejected with its own code |
| e5 | a trailing byte after the last record is rejected; a stream one byte short is rejected; the two produce different codes |
| e6 | the candidate-set block failing the frozen digest is rejected **before** any record is parsed, proven by a parse spy rather than by ordering in the source |
| e7 | each bound crossed by exactly one: 65 records, a 513-byte path, a candidate set of 1,048,577, a single payload of 4,194,305, an aggregate of 33,554,433 |
| e8 | a record whose declared payload length would push the running total past the aggregate is refused **at that record**, before its bytes are read — proven by the reader position, not by the exception type |
| e9 | nothing is allocated from an unchecked number: a header declaring 65,535 records with no records following fails on the count, not on a read |
| e10 | a payload whose SHA-256 matches the framed digest but not the derived inventory is rejected, and the converse also — the two comparisons are separate and neither is dropped |
| e11 | the two bindings of Decision 2, over the named corpus they are defined on |
| e12 | an AST test asserting the module imports only the standard library |
| e13 | duplicate paths, and a path present in the stream but absent from the derived inventory, each rejected with its own code |
| e14 | a mutation check on the round-trip test: an encoder that silently drops the last record must fail e1 |
| e15 | the wire grammar: each rejected form given its own case — invalid UTF-8 including an overlong sequence and an encoded surrogate, NUL, backslash, colon, leading `/`, trailing `/`, empty segment, `.`, `..`, BOM, 513 bytes; and the one-directional differential against `_checked_relative` over the named corpus, asserting the wire grammar rejects everything the containment check rejects and **not** the reverse |
| e16 | the round-trip postcondition, as a sensitivity test rather than an input case: with the decoder mutated to `errors="replace"`, to apply NFC normalization, and to a lenient codec, the postcondition must fire in each. No legal input reaches it — the test says so in its name and its docstring, so a later reader does not go looking for the byte sequence that does |

**Why `e3` changed.** Revision 1 asked for a legal path whose code-point order
and UTF-8 byte order differ, to catch an implementation that sorted decoded
strings. There is no such path. Byte-wise ordering of well-formed UTF-8
preserves scalar-value ordering, and the accepted domain is exactly the
well-formed, round-trip-stable sequences, so a decoded-string sort and a byte
sort are observationally identical there. The old `e3` would have passed against
both implementations while claiming to distinguish them — a test named after an
invariant it cannot check, which is a shape this work stream has produced
before. What *is* distinguishable is a comparator that is not order-preserving
at all, which is what `e3b` now targets.

The property was measured rather than recalled, on the interpreter named above:
across 3,275,520 pairs drawn from scalar values spanning `U+0000`–`U+08FF`, the
surrogate boundary either side, `U+FF00`–`U+FF0F`, `U+10000`–`U+1004F` and the
top of plane 16, and across 200,000 randomly generated 1-to-4 character pairs,
the string comparison and the UTF-8 byte comparison disagreed **zero** times.
The two `e3b` comparators were confirmed distinguishable in the same run:
`casefold` reorders `["B.py", "a.py"]`, and an NFD path and its NFC equivalent
are different byte sequences that normalization collapses onto one.

Every failure code is asserted by value. A test that accepts any exception from
a decoder is a test that would pass on the wrong rejection, and the wrong
rejection is how a bounds error becomes a parse error and stops being visible.

---

## Claim ceiling

- **M3-a spawns no child, compiles nothing, executes no historical code and
  imports no historical module.** It does execute its own encoder, decoder, JSON
  parser and inventory derivation in the parent process; revision 1 said
  "executes nothing", which was false. It moves no availability flag and is
  wired to no caller; `ACTIVE = False` and a test asserts it.
- The child's re-verification defends against the parent's transport and data
  state being wrong. It does **not** defend against a substituted spawn target
  or substituted runner bytes, and it does **not** defend against a design error
  common to both derivations. No test in this plan can establish either.
- The runner's path-to-bytes binding, and the TOCTOU window on it, are accepted
  trust assumptions of M3, not solved problems and not deferred work items.
- Nothing here bears on whether the pinned commit is what actually executed.
  The pin remains a record.
- The consumed A/B pair remains `NON_SUCCESS` and does not become reusable
  through any of this. No manifest is repinned and no pair evidence is
  rewritten.
- The two interpreter measurements above describe the local CPython 3.12.10 on
  Windows. They are not a claim about other interpreters or other platforms, and
  M3-b must re-measure rather than inherit them if either changes.

---

## Authorization boundary

This document proposes. It authorizes nothing. M3-a implementation, the file it
creates, any commit, any push and any merge request each need their own owner
authorization. The revision 10 authority reconciliation was authorized as part
of this design-only slice, and it is the only authority change made here.
Credentials, preflight and live remain unauthorized, and no part of M3
approaches them.
