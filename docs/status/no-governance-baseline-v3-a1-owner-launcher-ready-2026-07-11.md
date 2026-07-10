# No-Governance Baseline v3 — Arm A Run 1 Owner Launcher Ready (2026-07-11)

> **Status: offline preparation complete; launcher not executed; no API transmission.**

## Scope

This record binds the frozen v3 Arm A Run 1 launcher to a fresh host-owned
scratch repository. It is a preparation record only, not run evidence.

- Launcher: `artifacts/evidence/test-results/launcher-no-governance-baseline-v3-a1-owner-20260711.ps1`
- Scratch root: `C:\Users\daish\.codex\visualizations\2026\07\10\019f4c83-2f1f-7b30-af00-324063641a72\v3-arm-a-run-1-owner`
- Scratch owner: `DESKTOP-EJOULKM\daish`
- Seed tree: `27b7d8f9e7c7b7bccce5d47ce991c92a6e3fea71`
- Seeded task SHA-256: `16642a46a363b10ccb53f74bd0efdf027b47d08c39726259c5c86c08b5659065`
- Package lock: PFN `OpenAI.Codex_2p2nqsd0c76g0`, AppId `App`, version `26.707.3748.0`

## Frozen execution path

The launcher refuses to run unless the package version/PFN, scratch owner,
seed tree, seeded task hash, and clean scratch state match the frozen v3
pre-registration. It refuses to overwrite any existing Run 1 raw-output or
result receipt. It uses `Invoke-CommandInDesktopPackage` with AppId `App` and
`-PreventBreakaway`, then records the package-context process exit code,
timestamps, package-context flag, prevent-breakaway flag, and scratch owner.

The owner must execute the committed script from an ordinary PowerShell window.
This preparation step does not execute the script or create Run 1 output.

## Not claimed

- No OpenAI API request, Codex session, task-file read/write, or Run 1 result.
- No semantic repair, validator result, score, ledger update, or treatment
  comparison.
- No proof that the package-context harness remains qualified after the
  preparation timestamp.
