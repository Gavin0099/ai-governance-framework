# Gate 3 M3-b-2 — Materialized-Root Transport

Status: accepted design decision; not implemented and not execution authority.

Accepted: 2026-08-20 by the owner after independent exact-digest review of
normative rev2, SHA-256
`3c3955c0edfe4a370e99b46b272f6bce7a49e2acd2d1a90e39a36affaca0b065`.
Those reviewed bytes were not committed before acceptance and are no longer
retrievable from git; the digest records what the reviewer observed, not a
durable repository object. The post-review acceptance edit changed this status
block and “Acceptance and Authorization Boundary” from conditional to completed
language. Its recorded intent did not change the wire format, grammar, errors,
producer/consumer split, authority boundary, evidence plan or claim ceiling,
but the absent rev2 object means git cannot independently prove that delta.

Date: 2026-08-20

Base: `feat/gate3-historical-materialization@808c5fe7`

## Problem

M3-b-1's closed loader already requires the materialized root. It uses that
root to give each verified module its real materialized `__file__`, to let the
historical builders locate their non-executable data inputs, and to audit that
no module under that root bypassed the buffer loader. The dependency is explicit
in `BufferFinder.__init__`, but no existing process boundary transports it.

The three convenient channels are already closed by the accepted design:

- argv is exactly `[executable, "-I", "-S", "-B", runner_path]`;
- the environment is a constructed mapping and excludes every `GATE3_*` key;
- cwd is an M3-b-owned scratch directory, not the materialized root.

Inventing a value from any of them would create an ambient second authority.
The problem is therefore not merely how to send a path. It is how to carry one
live `MaterializedTree` root to the child without reopening those channels,
changing the M3-a byte authority, or claiming the child can verify more of the
parent's filesystem choice than it actually can.

## Current Repository Truth

- `gate3_historical_materialize.MaterializedTree.root` is derived from the same
  private `_Authority` object that owns the root identity, inventory and held
  handles. `_record_of` refuses forged, recombined or consumed records.
- The materializer creates the root as `Path(base) / deterministic_root_name`.
  The name is `gate3-historical-` plus the first 32 hexadecimal characters of
  SHA-256 over the source commit and the complete retained inventory.
- `gate3_historical_child.encode_stream` and `decode_stream` implement the
  accepted `GATE3HM\0` version-1 M3-a frame. The frame contains candidate-set
  bytes and verified executable buffers, but no materialized root.
- `decode_stream` returns only the verified buffer map. It deliberately keeps
  candidate-set verification ahead of record parsing.
- `BufferFinder` requires an absolute root and constructs module origins under
  it. Historical builders then open materialized data files by name. The root is
  therefore data-selection authority, not cosmetic diagnostic metadata.
- The accepted parent-to-child contract permits one bounded stdin transport and
  explicitly rejects argv, environment, pickle, temporary-file and fallback
  channels.
- M3-b's spawn contract writes the M3-a frame to stdin, uses exact argv and a
  constructed environment, and inherits only the standard-stream handles.
- M3-b-2 process control and the child `__main__` do not exist. `ACTIVE` remains
  `False`; no current caller can reach this path.

## Target Outcome

One versioned launch envelope on the existing stdin pipe carries:

1. one byte-identical M3-a version-1 frame; and
2. the absolute materialized-root path taken from one live, validated
   `MaterializedTree` authority.

The child verifies the inner M3-a authority before decoding or using the root,
then validates the root's wire grammar and deterministic leaf name before
constructing the loader. No fallback exists.

## Decision

Adopt a new outer launch envelope. Do not revise the M3-a frame.

| Layer | Magic / version | Responsibility |
| --- | --- | --- |
| launch envelope | `GATE3HL\0`, version 1 | process-run metadata: inner-frame boundary and materialized root |
| M3-a frame | `GATE3HM\0`, version 1 | candidate-set authority and executable buffers, byte-identical to the committed format |
| result frame | `GATE3HR\0`, version 1 | child-to-parent reconstruction values; unchanged |

This is still one transport: one bounded byte stream on stdin, consumed exactly
once. Nesting two typed frames in that stream does not create an argv,
environment, file or handle channel.

The separation is load-bearing. The materialized root affects where historical
data is read, but it does not decide which module bytes compile. Putting it
inside `GATE3HM\0` would mix launch metadata into the authority frame and force
either an incompatible version change or a dual-version decoder. The outer
envelope leaves every M3-a byte and test fixture intact.

## Wire Format

All integers are unsigned, little-endian and fixed-width.

| Position | Field | Width | Rule |
| --- | --- | --- | --- |
| header | magic | 8 bytes | `47 41 54 45 33 48 4c 00` (`GATE3HL\0`) |
| header | version | 2 bytes | exactly `1` |
| header | inner-frame length | 4 bytes | `1..34,638,232` |
| header | root length | 4 bytes | `1..65,536`, measured in UTF-8 bytes |
| body | M3-a frame | inner-frame length | one complete `GATE3HM\0` version-1 frame |
| body | materialized root | root length | strict UTF-8 under the grammar below |

Header size is 18 bytes. The maximum legal launch stream is therefore
`18 + 34,638,232 + 65,536 = 34,703,786` bytes. This derived value is not an
independent gate; the two component limits are the gates. A reader reads at most
that derived maximum plus one byte so it can distinguish exact-bound from
over-bound input without reading an unbounded stream.

The name of that outer bound is
`MAX_LAUNCH_STREAM_BYTES = 34,703,786`. It is deliberately not the existing
M3-a `DERIVED_MAX_STREAM_BYTES = 34,638,232`: the former bounds the whole launch
envelope, while the latter bounds only the inner M3-a frame.

The inner frame comes first so the candidate-set authority can be verified
before root text is decoded or used. The root length is present in the header
only so the outer frame can be sliced without a delimiter. No allocation is
sized from either length before its bound is checked.

## Producer

The producer is the later M3-b-2 parent orchestration, not
`gate3_historical_child.encode_launch_stream` by itself.

It must perform this sequence:

1. receive one live `MaterializedTree`, never a caller-supplied root string;
2. validate that tree through a materializer-owned helper that applies the
   existing private-authority, unconsumed-record and root-anchor identity checks;
3. take `os.fspath(tree.root)` from that same authority without calling
   `resolve()`, `absolute()`, cwd lookup or an environment fallback;
4. verify/read the retained bytes through the held M2 handles as required by the
   existing M3 contract and build the ordinary M3-a frame;
5. pass that inner frame and the authority-derived root to the launch-envelope
   encoder; and
6. complete the envelope before `CreateProcessW` is attempted.

The generic encoder enforces syntax and bounds for diagnosis, but it does not
make an arbitrary string authoritative. A structural test must show that the
M3-b-2 producer's public entrypoint accepts a `MaterializedTree`, not a root
string, and that no other value source reaches the encoder.

A forged, recombined or consumed tree is refused as
`MATERIALIZED_ROOT_RECORD_INVALID`. The adapter may translate the existing M2
`RECORD_INVALID` internally, but no private record detail crosses the boundary.

## Consumer

The consumer is the future `gate3_historical_child.py` `__main__` path. It:

1. reads stdin to EOF under `MAX_LAUNCH_STREAM_BYTES + 1`;
2. parses the launch header, checks both lengths, slices exactly one inner frame
   and one raw root field, and refuses a trailing byte;
3. calls the existing M3-a decoder on the inner frame;
4. only after that succeeds, strictly decodes and validates the root;
5. derives the expected deterministic root leaf from the already verified
   candidate-set bytes and rejects a mismatch;
6. calls `load_buffers(verified_buffers, validated_root)`; and
7. offers no bare-M3-a, argv, environment, cwd or temporary-file fallback.

To avoid a second M3-a framing walk, implementation may refactor the current
decoder into one private function returning both verified candidate-set bytes
and verified payloads. Public `decode_stream` keeps returning only the payload
map; `decode_launch_stream` uses the private verified result to derive the root
leaf. The candidate-set bytes are not exposed to historical code.

## Materialized-Root Encoding and Grammar

The wire encoding is strict UTF-8, without BOM or terminator. UTF-8 is chosen
because it gives one canonical byte sequence for each accepted Python string and
matches the existing byte-oriented transport. It is not a claim that Win32 uses
UTF-8; native process and file APIs remain wide-character APIs.

The encoder and decoder apply the same positive grammar:

- value type is exactly `str`, non-empty;
- strict UTF-8 encode/decode round-trips to the identical bytes;
- no NUL and no BOM;
- at most 65,536 UTF-8 bytes;
- at most 32,766 UTF-16 code units, reserving one unit for the terminating NUL
  when the path is handed to a Win32 wide-character API;
- Windows path semantics are applied with `ntpath`, not the parent's current
  platform-dependent cwd semantics;
- the path is absolute drive, UNC or extended-length form; drive-relative forms
  such as `C:child` are rejected;
- `/` is rejected; the wire uses Windows `\` separators only;
- `ntpath.normpath(value) == value`; dot segments, doubled separators where
  normalization changes meaning, and trailing separators are therefore refused
  rather than silently rewritten;
- the path has a non-root leaf component; a drive root or UNC share root is
  rejected; and
- that leaf exactly equals the deterministic materializer root name derived
  from the verified candidate-set source commit and complete retained inventory.

The two length limits are independent and both are reachable. An all-ASCII path
can fit the UTF-8 byte bound while exceeding 32,766 UTF-16 units; a path dominated
by three-byte UTF-8 BMP characters can remain below the UTF-16-unit bound while
reaching 65,536 wire bytes. Neither limit may be removed as redundant, and the
derived outer maximum is computed from the byte bound because that is what the
wire length field measures.

The 32,766-unit protocol bound is conservative. Microsoft documents an
approximate extended-length maximum of 32,767 wide characters; the protocol
reserves the terminator and still treats component and filesystem limits as
runtime facts, not properties established by the frame. See
<https://learn.microsoft.com/windows/win32/fileio/maximum-file-path-limitation>.

The decoder performs no filesystem existence check, canonical-name lookup,
reparse resolution or `Path.resolve()`. Those would resolve the name again and
would still not prove it denotes the object whose handles the parent owns.

The deterministic leaf derivation is byte-exact, not an instruction to
reimplement the idea:

1. parse the already digest-verified candidate set and require
   `source_base_commit` to be 40 lowercase hexadecimal characters;
2. validate the complete retained `files` inventory under the existing
   `{"bytes", "path", "sha256"}` record grammar;
3. sort `(path, digest)` pairs by Python string ordering, exactly as M2 does;
4. form `joined = "\n".join(f"{path}:{digest}" ...)`;
5. form `(source_base_commit + "\n" + joined).encode("ascii")` with strict
   encoding; and
6. take `"gate3-historical-" + sha256(bytes).hexdigest()[:32]`.

The frozen candidate currently satisfies the ASCII precondition. A future
candidate repin containing a non-ASCII retained path would be refused as
`MATERIALIZED_ROOT_NAME_DERIVATION_FAILED` until M2 and this derivation are
changed and reviewed together. Neither side may silently switch encoding or
normalization to make the new candidate fit.

## Authority Boundary

Three different claims must not be collapsed:

1. **Executable bytes.** Independently checked in the child against the frozen
   candidate-set digest through the unchanged M3-a frame.
2. **Root record at an intact parent.** Bound by the parent to one live
   `MaterializedTree` authority and its held root anchor before encoding.
3. **Full root path against a corrupted parent.** Not independently verifiable
   by the child. The verified candidate set determines the leaf name, but it
   contains no trusted absolute base. Two absolute bases containing the same
   deterministic leaf are indistinguishable to the child.

Sending `root_identity` beside the path does not improve item 3: the child has no
inherited root handle or independent identity oracle to compare it with. It
would be a stream value vouching for another stream value. Inheriting such a
handle is rejected for this tranche because it would reverse the accepted
handle-isolation boundary and require a different child I/O design.

The accepted claim is therefore bounded: the launch envelope catches malformed,
misframed, non-canonical and wrong-leaf roots; parent authority binding catches
an intact parent passing an arbitrary string. It does not defend against a
parent that substitutes a different absolute base containing the same leaf.
That limitation must appear in M3-b-2's claim ceiling and may not be summarized
as “the child verifies the materialized root.”

## Version and Compatibility

- `GATE3HM\0` remains version 1 and byte-identical.
- `GATE3HL\0` starts at version 1; unknown versions are refused.
- The process entrypoint accepts only `GATE3HL\0`. A bare M3-a frame is a launch
  magic mismatch, not a compatibility path.
- There is no version negotiation. Parent and child are one reviewed checkout;
  accepting multiple versions would add a state the tranche does not need.
- There is no fallback after any launch-envelope failure.

Upon acceptance, this decision amends two sentences without reopening their
other decisions:

- M3's “one transport” remains one stdin stream; that stream is now the launch
  envelope containing the unchanged M3-a frame and root.
- M3-b's “parent writes the M3-a frame to stdin” becomes “parent writes one
  launch envelope containing exactly one M3-a frame to stdin.” Exact argv,
  environment, cwd and handle-inheritance decisions remain unchanged.

## Closed Errors and Rejection Order

Outer-envelope errors are distinct from inner M3-a errors:

| Code | Trigger |
| --- | --- |
| `LAUNCH_STREAM_INVALID` | encoder/decoder input has the wrong Python type |
| `LAUNCH_MAGIC_MISMATCH` | outer magic is not `GATE3HL\0`, including a bare M3-a frame |
| `LAUNCH_VERSION_UNSUPPORTED` | outer version is not 1 |
| `LAUNCH_STREAM_TRUNCATED` | header or either declared body field ends early |
| `LAUNCH_INNER_LENGTH_INVALID` | inner length is zero or exceeds the existing M3-a `DERIVED_MAX_STREAM_BYTES` (`34,638,232`) |
| `MATERIALIZED_ROOT_LENGTH_EXCEEDED` | UTF-8 byte or UTF-16-unit bound is exceeded |
| `LAUNCH_TRAILING_BYTES` | bytes remain after the declared inner frame and root |
| `MATERIALIZED_ROOT_INVALID` | type, encoding, round-trip, NUL/BOM, separator, normalization or root-only rule fails |
| `MATERIALIZED_ROOT_NOT_ABSOLUTE` | relative or drive-relative root |
| `MATERIALIZED_ROOT_NAME_MISMATCH` | leaf differs from the name derived from verified candidate-set bytes |
| `MATERIALIZED_ROOT_NAME_DERIVATION_FAILED` | verified candidate-set fields cannot produce the exact M2 ASCII root-name formula |
| `MATERIALIZED_ROOT_RECORD_INVALID` | producer was not given one live, internally consistent M2 authority |

The rejection order is fixed:

1. outer type, magic, version, length bounds, truncation and trailing bytes;
2. unchanged inner M3-a decoding, propagating its existing exact codes;
3. root UTF-8, length, path grammar and deterministic leaf;
4. loader construction.

No root bytes, historical exception text, source excerpt or path is included in
an error. The code is the complete external message.

## Scope

- Decide the only transport channel and its exact bytes.
- Bind the producer to a live `MaterializedTree` authority.
- Name the child consumer and validation order.
- Define root encoding, bounds, grammar, deterministic-name check and errors.
- State version behavior, rejection behavior and the corrupted-parent limit.
- Define evidence required of the later implementation.

## Non-Goals

- No M3-b-2 implementation, native binding, process, job object or pipe.
- No change to M3-a or result-frame bytes.
- No historical module execution and no M3-b-3 work.
- No inherited materialized-root handle.
- No independent child proof of the absolute base path.
- No runner-path or runner-byte TOCTOU repair.
- No materializer activation, availability change, PR, push or CI claim.
- No B-1 work.

## Affected Surfaces if Later Implemented

- `gate3_historical_child.py`: launch-envelope constants, encoder/decoder,
  private verified-inner result, root grammar and future `__main__` consumption.
- `gate3_historical_materialize.py`: one authority-owned helper that returns the
  transport root only for a live consistent tree.
- focused tests for those modules: independent raw envelope builder/parser,
  authority binding, exact errors and sensitivity mutations.
- the later M3-b-2 parent adapter: sole producer callsite and bounded stdin read.
- the M3 and M3-b design records: narrow sentence amendments listed above.

No public production API or active routing surface changes in this design.

## Failure Paths and Risk Points

- Treating root as diagnostic metadata would miss that historical builders open
  data under it.
- Passing a raw root string into the M3-b-2 public entrypoint would sever it from
  M2 authority even if the string is syntactically valid.
- Calling `resolve()` would add another name resolution and still would not bind
  the result to the held root object.
- Revising M3-a version 1 would invalidate an already reviewed authority frame
  for launch metadata that does not select executable bytes.
- Accepting a bare M3-a frame would create an implicit compatibility branch.
- Decoding root semantics before the inner frame would let unauthoritative data
  act before candidate-set verification.
- Repeating the M3-a framing walk inside the outer decoder would create two
  implementations of one authority format.
- Carrying `root_identity` without an independent child-side oracle would look
  stronger while proving nothing.
- Claiming full corrupted-parent resistance would be false because the verified
  candidate set does not anchor the absolute base.

## Evidence Plan

Every item names the defect it must detect:

1. An independent fixture parser, written from the table rather than the
   encoder, confirms magic, widths, ordering and exact end offset.
2. The inner bytes extracted from an encoded launch envelope are byte-identical
   to direct `encode_stream(...)` output; a mutation that re-encodes the inner
   frame fails this test.
3. A raw fixture builder reaches every malformed outer-frame case that the
   production encoder refuses to emit, with one exact error per case.
4. Decoder spies show inner M3-a verification completes before root UTF-8 decode
   and before loader construction.
5. Unknown launch version, bare M3-a frame, zero/over-bound inner length,
   over-bound root, truncation and trailing bytes each fail with their exact
   outer code.
6. Root corpus covers invalid UTF-8, unencodable surrogate, NUL, BOM, `/`,
   relative, drive-relative, dot segment, doubled separator, trailing separator,
   drive/share root and wrong deterministic leaf.
7. A named valid corpus covers drive, UNC and extended-length absolute forms and
   asserts strict byte round-trip plus the UTF-16-unit bound.
8. Differential root-name tests compare the child's derivation with
   `gate3_historical_materialize._root_name` over the real candidate set and a
   named mutation corpus. This is agreement over that corpus, not universal
   independent verification.
9. Producer tests reject a raw string, forged tree, recombined authority and
   consumed tree; a live verified tree produces exactly its stored root without
   `resolve()`, cwd or environment access.
10. A structural callsite test shows only the M3-b-2 parent adapter invokes the
    launch encoder and its public entrypoint accepts a `MaterializedTree`.
11. Exact argv, exact environment key set, scratch cwd and inherited-handle list
    remain unchanged when the launch envelope is later integrated.
12. A limitation test demonstrates that two different absolute bases with the
    same valid deterministic leaf both pass child syntax checks. Its purpose is
    to prevent future prose from claiming independent base verification.
13. Derived-maximum arithmetic is recomputed from constants; changing a
    component bound without its recorded maximum fails.
14. AST evidence continues to show `gate3_historical_child.py` imports only the
    standard library.

This design requires no runtime test because it changes no runtime. The later
implementation requires in-process envelope and authority tests first; the real
process integration remains part of M3-b-2's already specified evidence.

## Claim Ceiling

This document establishes only the accepted transport decision and the repository
truth it cites. It does not establish that the envelope exists, that any root is
transported, that a child starts, that the parent is contained, or that Gate 3
succeeds.

Even after implementation, the child would independently verify executable
buffers and the deterministic root leaf, not the absolute base path. The parent
would remain trusted to bind that base to the live M2 authority. `ACTIVE` and all
availability predicates remain unchanged; the consumed pair remains
`NON_SUCCESS`.

## Implementation Tranche Recommendation

When separately authorized, M3-b-2 should begin with the in-process launch
envelope and materializer authority helper, satisfying evidence items 1–10,
12–14 before any native process-control callsite consumes them. The same M3-b-2
tranche may then integrate the already designed process boundary and satisfy
item 11 plus its real-process evidence. No M3-b-3 historical execution belongs
in that tranche.

## Acceptance and Authorization Boundary

The owner accepted the outer-envelope decision, the exact wire and errors, the
producer/consumer split, and the explicit limit on corrupted-parent protection
on 2026-08-20. That acceptance authorizes the two amendments in “Version and
Compatibility” and record reconciliation only. It does not authorize
implementation.

Any Python edit, commit, push, PR or M3-b-2 execution requires separate
authorization. The design dependency recorded in `BufferFinder` is resolved by
this decision; the implementation dependency remains open.
