# Technical specification

## Scope

Freeze the narrow Finding 58 correction at execution base
`de7a3f05f196895dc55a5e406f2c4ef2f19ed23e`: the outer Probe-02 invocation
journal must not obtain Git identity or blob evidence through ambient command
resolution.

## Trust chain

1. The bootstrap may run only as stdin from an owner-authorized commit blob.
2. Before Git is invoked, the exact Git and Python files are checked by path,
   byte count, and SHA-256; `sys.executable` must be the pinned Python.
3. A subprocess.run-compatible adapter accepts only the frozen repository
   prefix and the required `rev-parse`, `cat-file blob`, or
   `ls-tree --name-only` command shapes.
4. The adapter executes the exact pinned Git path and retains
   `--no-replace-objects`.
5. The Git child receives an explicit environment allowlist. Ambient `GIT_*`
   variables—including repository, worktree, object-store, index, and config
   selectors—are not inherited; system/global config and system attributes are
   disabled by fixed values.
6. Manifest, frozen inventory, source bindings, HEAD, and anchor OIDs all use
   that adapter.
7. The outer journal obtains the corrected child bootstrap only from the
   owner-authorized commit's frozen inventory. The child and its corrected
   driver repeat the exact-Git verification and use equivalent allowlisted Git
   environments. The child-launch and driver-launch environments exclude
   ambient `PATH` and arbitrary `GIT_*`; the downstream readiness and capability
   engine Git entrypoints are explicitly routed through the corrected driver's
   pinned adapter.
8. Before HEAD or blob lookup, outer, corrected child, and corrected driver
   independently validate the same detached-worktree identity contract:
   - the checkout root equals the single frozen owner-approved path; a second
     valid linked worktree is not an equivalent execution identity;
   - the checkout root is a non-reparse directory and `.git` is a non-reparse
     LF-only regular gitfile;
   - its absolute target is exactly
     `D:/ai-governance-framework/.git/worktrees/<checkout-name>`;
   - the target, common Git directory, and `worktrees` directory are
     non-reparse directories;
   - the target's reverse `gitdir` record resolves exactly to the checkout
     gitfile and `commondir` is byte-exact `../..\n`;
   - pinned Git's `--show-toplevel`, `--absolute-git-dir`, and
     `--git-common-dir` outputs match the independently derived identities.
9. Only after all bindings and pre-journal state checks pass may the journal
   root and `start.json` be created and the child be launched.

## Preserved semantics

- Attempt id remains `C1-nonhosted-sandbox-capability-probe-02`.
- The journal, attempt, CLI-staging, and private paths remain unchanged.
- `start.json` remains the authority-consumption boundary and precedes child
  launch.
- Maximum executions remains one; retry remains forbidden.
- Hosted requests, auth payloads, qualification, randomization, and arms remain
  outside this freeze.

## Adversarial evidence

The focused tests place a fake Git command first on `PATH` and execute the real
`execute()` entry.  The pinned Git must report the real HEAD mismatch, the fake
Git marker must remain absent, and the journal/start/attempt/CLI/private roots
must remain absent. A second execute-path test sets `GIT_DIR` and
`GIT_WORK_TREE` to an authorized decoy repository; the adapter must still read
the target checkout. Additional tests reject malformed adapter prefixes,
unexpected Git commands, altered subprocess parameters, and ambient Git
selectors.
The cross-layer test then publishes a synthetic start record and launches the
corrected child with hostile ambient `PATH`, `GIT_DIR`, and `GIT_WORK_TREE`.
The child must use the target checkout and pinned Git, return a bounded nonzero
before capability execution, and leave the fake-Git marker absent.
Git-directory adversarial tests run the same validator through outer, corrected
child, and corrected driver. They reject a redirected checkout gitfile, a
reparse gitfile or worktree-admin directory, a decoy reverse gitfile, and any
disagreement in the three pinned-Git identity queries. A real detached worktree
at the owner-approved identity is accepted; a second otherwise valid worktree
is rejected. An execute-path binding failure leaves journal, start,
attempt, CLI, and private roots absent.

The frozen execution checkout is intentionally not materialized by this
authoring freeze. Tests therefore distinguish two claims: the exact path token
is pinned byte-for-byte across all three executables, manifest, and policy and
is currently absent; the filesystem topology validator is exercised against a
real current detached checkout only after explicitly binding that checkout as
a synthetic test identity. Live validation of the frozen execution path occurs
after its separately authorized materialization and before any journal claim.

## Claim ceiling

This freeze can establish reviewable pinned-Git implementation bytes and
synthetic/adversarial evidence that ambient `PATH` or repository-selecting
`GIT_*` cannot select Git or repository identity across the outer-to-child
verification path.  It does not authorize or establish Probe-02,
readiness, sandbox capability, hosted transport, qualification, randomization,
or arm results.
