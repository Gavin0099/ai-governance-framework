# Codex hook trust diagnostic (#246)

Status: implemented using Codex's own `hooks/list` protocol. The negative hash
experiment below is retained; the implementation does not recreate that hash.

## Empirical evidence

The owner-provided path-free snapshot contains 69 trust records referencing 29
current hook files. Of these records, 61 have an existing file, 59 still locate
the recorded event/group/hook, and eight have no file. Records are numbered from
one in snapshot order. No real user config or private command/path is reproduced.

All 59 addressable definitions failed to match their recorded `trusted_hash`
under the following SHA-256 / UTF-8 candidates:

- Decoded file text (BOM stripped, newlines normalized), command string,
  hook object, group object, and full file object.
- JSON with sorted/source keys, ASCII/Unicode strings, compact/spaced separators,
  and no indentation or two/four-space indentation.
- Every nonempty subset and key permutation of the source hook fields, including
  omission of `commandWindows`, `timeout`, and `statusMessage`.
- Normalized camel/snake field names, timeout field/unit variants, missing
  options omitted or null, and timeout defaults null/600/60/30/10/5/0.
- Additional default flags, event/matcher wrappers, and external enum wrappers.

The normalized second pass made 7,714,400 serialization/hash comparisons
(including duplicate candidates), with **zero matching records**. The initial
source-form pass also matched zero. No candidate matched even a positive subset.
The table shows representative failures for sorted, compact JSON of the source
hook object; hashes below show their first 16 hexadecimal characters only.

| Record | Snapshot file | Event/group/hook | Recorded hash prefix | Candidate hash prefix |
| --- | --- | --- | --- | --- |
| 1 | hooks-01.json | stop/0/0 | 878c140372908a49 | cb5f992d37f43fa8 |
| 3 | hooks-03.json | stop/0/0 | 2e0a5da16dc55a15 | 290de6ebb0b5eead |
| 7 | hooks-04.json | stop/0/0 | d575988dde689203 | 5e3e055fc1d87039 |
| 11 | hooks-06.json | session_start/0/0 | 3b96ed451c3e6ef3 | c296926ed8b06a3e |
| 14 | hooks-07.json | session_start/0/0 | 03698945daea6c12 | 32d68fddf1f07fc7 |
| 42 | hooks-17.json | pre_tool_use/0/0 | c212f79abbfee887 | eff1b84dddeab8ea |
| 59 | hooks-24.json | stop/0/0 | ebbfb2ba2119b40c | eeba2ce185387c0d |

Records 9 (`hooks-04.json`, stop/1/0) and 10 (`hooks-05.json`, stop/0/0)
are demonstrably stale: their files exist but those definitions are absent.
This does not establish that the other 59 records are stale. Historical trusted
definition bytes and a known fresh positive control are missing; these negative
results establish neither the canonical serializer nor current trust states.

## Implemented diagnostic

`governance_tools.codex_hook_trust_status` reads `.codex/hooks.json` and queries
one local `codex app-server` over stdio JSON-RPC: `initialize`, `initialized`,
then `hooks/list` with `cwds: [repo]`. This follows the coordinator-provided
live probe and generated HooksListParams/HooksListResponse protocol schemas.
Codex supplies trust status, enabled state, and its opaque current hash; the
diagnostic does not read or parse user config and never computes trust hashes.

| State | Meaning |
| --- | --- |
| `not_installed` | The hook definition/file is absent; missing expected SessionStart/Stop entries are reported explicitly. |
| `installed_not_loaded` | The file defines the hook, but Codex does not return it. This can occur before project trust; no cause is inferred. |
| `installed_untrusted` | Codex reports `trustStatus: untrusted`. |
| `installed_modified` | Codex reports `modified`: the definition changed since trust and is skipped. |
| `installed_trusted` | Codex reports `trusted` or `managed`; the original trust status is retained. |
| `trust_unknown` | Probe deferred, missing binary, timeout, load/protocol error, unreadable hooks, or unsupported format. |

Only trusted/managed hooks with `enabled: true` count as adopted. Missing,
unloaded, untrusted, modified, unknown, and disabled hooks do not. Trusted does
not prove event execution, command success, or formal closeout; existing R1/R2
identity, ownership, and receipt requirements remain authoritative.

Match full normalized source paths, event names, and group/hook indices; split
keys from the right to retain Windows drive colons. An unrelated project's hook
cannot satisfy the target. A definition edited during a probe becomes unknown.
Output excludes hook command strings, source paths, and raw server error text.

Run from an environment where the framework tools are importable:

```console
python -X utf8 -m governance_tools.codex_hook_trust_status --repo . --timeout 5 --json
```

Binary selection is `--codex`, then `CODEX_BINARY`, then PATH; nothing is
installed. The whole protocol exchange has a five-second default deadline.
The child is always killed/reaped, including success and failure paths, with
bounded cleanup waits. All diagnostic states return exit code zero.

Routine adoption/update reports deliberately do not spawn app-server: startup
is environment-dependent and adds process/timeout cost to every report. The
shared maturity summary includes per-hook unknown/not-installed rows, structured
details, and the explicit CLI command. Existing adoption and F-7 table forwarding
carry these rows without editing either updater. Git-hook reporting remains
separate. No gate, installation validator, update completion decision, hook
behavior, or closeout entry logic is changed.

## Verification and remaining work

Tests use a Python JSON-RPC fixture, not a real Codex binary. They cover every
state, disabled hooks, changed definitions, missing server entries, unreadable
hooks, missing binaries, malformed/error replies, handshake order, timeouts,
process cleanup, Windows/POSIX keys, and shared report forwarding.

The coordinator will verify the completed CLI against real Codex. The supplied
live probe is input evidence, not a live replay performed by this implementation
agent. Other platforms and end-to-end R1/R2 execution/closeout qualification
remain outside this change. The exact canonical trust-hash rule is still unknown
and is no longer needed by this diagnostic.
