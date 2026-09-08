# Technical specification

## Scope

Freeze only Finding 59 at execution base
`4be68faf9965430d35040304c4514aca2645b9c2`. The SID-producing executable used
by reviewed-readiness validation must be identified by exact bytes, not merely
an absolute path.

## Observed failure

The active `execution_readiness.identity_projection()` runs
`C:/Windows/System32/whoami.exe`. Its output participates in the comparison
between the live execution identity and the independently reviewed readiness
receipt. The external-executable-resolution audit rev1 therefore classified
the path-only executable as an active ambient trust root and returned
`AMBIENT_EXECUTABLE_TRUST_ROOT_REMAINS`.

## Corrected trust chain

1. The outer bootstrap may run only as stdin from an owner-authorized commit
   blob and verifies the new frozen inventory before journal claim.
2. The outer bootstrap selects the corrected child from that inventory.
3. The corrected child selects the corrected driver from the same correction
   manifest and launches it with exact digest-bound Python using `-I -`.
4. Before Git-directory identity, HEAD/blob binding, reviewed-readiness
   validation, or any formal root, the driver verifies:
   - `C:/Windows/System32/whoami.exe`;
   - byte count `98304`;
   - SHA-256
     `23240ef9f8b0a9a324110b1c2331de31dc1b0e08f5359cb707e51a939af56cd3`.
5. The identity adapter accepts only
   `[whoami.exe, /user, /fo, csv, /nh]`, empty stdin, captured output,
   `check=False`, and the frozen timeout.
6. Its environment inherits only `SYSTEMDRIVE`, `SYSTEMROOT`, and `WINDIR`,
   plus fixed `NO_COLOR=1`; it does not inherit `PATH` or arbitrary `GIT_*`.
7. The driver explicitly calls `identity_projection(runner=pinned_runner)` and
   passes the result as `identity=` to `validate_reviewed_readiness`. The
   validator cannot reach its default `subprocess.run` identity path.
8. Existing exact Git, checkout-identity, capability engine, journal, and
   terminal semantics remain unchanged.

## Adversarial evidence

- wrong frozen whoami digest fails before journal/start/attempt roots;
- a hostile `PATH` containing `whoami.cmd` is ignored by the exact runner;
- wrong identity argv or subprocess parameters are rejected;
- the live exact binary produces a bounded SID projection;
- source-order tests require pinned identity projection before reviewed
  readiness validation and require the explicit `identity=` injection;
- the prior exact-Git, decoy-repository, create-once, and zero-root tests remain
  in the focused suite.

## Non-goals

No attempt is made to attest every operating-system DLL or to generalize this
identity runner beyond the active Probe-02 path. No authorization packet or
execution artifact is created.
