# Technical specification

## Scope

Freeze only Finding 60 at execution base
`0a882464833c9c023272befdc3a258409c4a0f08`. Every active Probe-02
execution layer must identify the Windows command processor by exact bytes and
must not inherit ambient `COMSPEC`.

## Observed failure

The repo-external external-executable-resolution audit rev2 established that
ambient `COMSPEC` could reach the capability plane. An attacker-controlled
value could therefore redirect command-shell resolution even though Git,
Python, Codex, PowerShell, and whoami were otherwise pinned.

## Corrected trust chain

1. The outer bootstrap runs only as stdin from an owner-authorized commit blob.
2. Before Git-directory identity, HEAD/blob binding, or journal claim, it
   verifies `C:/Windows/System32/cmd.exe`, 344,064 bytes, SHA-256
   `8dd1ebb0b969370c70a5ee7f7ee347949aa7046aa5e1a33fcd7b1e9415b21fc3`.
3. Outer Git and child environments use the frozen COMSPEC value and do not
   inherit ambient PATH or COMSPEC.
4. The child bootstrap re-verifies the same executable before its Git binding
   and materialization work, then supplies the fixed value to the driver.
5. The driver re-verifies the executable before identity/readiness validation.
6. Before capability execution, the driver replaces the engine's minimal
   environment builder with a wrapper that re-verifies cmd.exe, writes the
   frozen COMSPEC value, and rejects PATH.
7. The predecessor exact-Git, checkout identity, whoami identity, journal,
   cleanup, and terminal contracts remain unchanged.

## Adversarial evidence

- wrong outer COMSPEC digest fails before Git binding, child launch, and all
  journal/start/attempt roots;
- hostile ambient COMSPEC is replaced in outer, child, driver, and capability
  engine environments;
- exact cmd.exe bytes and digest are checked against the live binary;
- end-to-end outer-to-child launch receives only the frozen COMSPEC;
- source-order checks pin all re-verification points and the engine override;
- predecessor malicious-PATH, decoy-repository, create-once, and zero-root
  tests remain in the focused suite.

## Non-goals

This freeze does not attest operating-system DLL loading and does not establish
a machine-wide shell prohibition outside the exact Probe-02 path. It creates no
execution-authorization packet and performs no Probe-02 execution.
