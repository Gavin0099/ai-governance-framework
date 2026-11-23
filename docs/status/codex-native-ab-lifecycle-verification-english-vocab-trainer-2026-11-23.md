# Codex Native A→B Lifecycle Verification — `english-vocab-trainer` Standalone Clone (`PASS`, Infrastructure Only)

- **Record Class**: **Infrastructure Native Lifecycle Verification (`PASS`) — NOT a Natural Product Delivery / NOT a G4 Sample PASS**
- **Sample Accounting Rule**: Do **not** count this record as a G4 natural product delivery sample, and do **not** use it to overwrite `docs/status/g4-consumer-sample-001-english-vocab-trainer-issue375-2026-11-23.md` (`FAIL / NOT PERSISTED`).
- **Date**: 2026-11-23
- **Archived Against Framework Main**: `0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d`
- **Disposable Standalone Clone**: `C:\Users\reiko\AppData\Local\Temp\evt-hook-verify-clone\english-vocab-trainer`
- **Consumer Base**: `english-vocab-trainer` `main@b24921ea11220fc3b591f142824697c70359c807`
- **Adopted Governance Submodule / Lock**: `6c7e24c3161fe80dc4c5bd6bfe1bec5cd04fd8dc` (`adopted_release: 1.2.0`)
- **Execution Environment**: Standalone `git clone` (non-worktree) + interactive `codex.exe --no-daemon` (`codex-cli 0.171.0-alpha.13`) + explicit owner `/hooks` trust initialization
- **Setup Human Intervention**: **1 manual initialization step** (owner ran interactive `/hooks` to trust `SessionStart` and `Stop` hooks in the new standalone clone; cannot be claimed as zero-setup automation).

---

## 1. Verified Lifecycle Chain (`Session A -> RELEASED -> Session B -> RELEASED`)

No product code was modified (`git diff --name-only` limited to `memory/01_active_task.md`, `memory/03_knowledge_base.md`, `memory/04_review_log.md`).

| Artifact / Check | Session A (Generation 1) | Session B (Generation 2) |
|---|---|---|
| Native `CODEX_THREAD_ID` == `.current-session-id` | `01a207be-f1b0-72c0-b3db-6b732887e06e` (matched) | `01a207c9-1fef-7bc1-819b-f63b9edbd00b` (matched; distinct from A) |
| `SessionStart` v1.1 envelope | `artifacts/runtime/sessions/01a207be-.../session-envelope.json` | `artifacts/runtime/sessions/01a207c9-.../session-envelope.json` |
| Candidate preparation (`prepare_codex_closeout.py`) | `PREPARED`, `OWNED`, `generation: 1`, 24 project closeout tests PASS | `PREPARED`, `OWNED`, `generation: 2`, 24 project closeout tests PASS; verified A `RELEASED` and read A summary from `memory/2026-11-23.md` |
| Candidate SHA-256 | `c9470d23d6cdce4aa03eacc9b0df7296e498ea5357ec955145c6e18eebf0142d` | `d65c74acf72a0843b52e5937ebbcb79a9f2aa85c838897ce2388a727e1fb5d4f` |
| Shared closeout text SHA-256 | `7dcd1d22d36d8a0fc1cec4a0279d7014f43c041391af2ddd682c53875642c62e` | `3af6b3094e3c3586d1ebebb32cf8b932275ce9c2b479abdf6756701aab702efa` |
| Native `Stop` hook R2 receipt | `closeout_receipt_20261123T093525202793Z_r2_156aa4270c704c8da8b3ad5864feb568.json` (`trigger_mode: "native_hook"`, `exit_code: 0`, `ok: true`, `gate_blocked: false`) | `closeout_receipt_20261123T095548592336Z_r2_d9469afee2084048be025f7e9c913f9e.json` (`trigger_mode: "native_hook"`, `exit_code: 0`, `ok: true`, `gate_blocked: false`) |
| R2 Ownership & Release | `artifacts/runtime/shared-closeout/releases/1.json` -> `state: "RELEASED"`, `generation: 1` | `owner.json` & `releases/2.json` -> `state: "RELEASED"`, `generation: 2`, `hold_reason: null` |
| Completion marker | `artifacts/runtime/closeout-completions/01a207be-...json` (8/8 required artifacts) | `artifacts/runtime/closeout-completions/01a207c9-...json` (8/8 required artifacts, `2026-11-23T09:55:49Z`) |
| Canonical daily memory (`memory/2026-11-23.md`) | `writer: governance_tools.memory_record`, `decision=AUTO_PROMOTE`, `closeout_status=valid`, `record_identity: 7113bf54d08bd76317bc95d4796d96f5eb3b1e08e0144d52b9d8253d91fe8a8d` | Appended cleanly without overwriting A: `decision=AUTO_PROMOTE`, `closeout_status=valid`, `record_identity: db42f89d894df32e5ce76ecaf213d8a5819b4f551448ab318c28036a5511c308` |

### Additional Minimal `codex exec` Control on Same Standalone Clone
- Prior to interactive Session A, a minimal isolated-`CODEX_HOME` `codex exec` probe (`"Reply OK"`, `23,046` input / `5` output tokens) on the same standalone clone also executed native `SessionStart` and wrote `.current-session-id` + v1.1 `session-envelope.json` (`session_id: 01a207b6-1bf2-7400-9ea0-02ddfece5bfd`, `exit_code: 0`).

---

## 2. Analytical Boundaries & Claim Ceiling (`NOT_CLAIMED`)

- **What This Proves**:
  - At least one real Codex CLI native execution path (standalone clone of `english-vocab-trainer@b24921ea` with `6c7e24c3` + interactive Codex `--no-daemon` + `/hooks` trust) completes the full `SessionStart -> PREPARED -> native Stop hook -> Valid Receipt -> Canonical Memory -> R2 RELEASED -> Session B handoff -> R2 RELEASED` infrastructure loop with zero residual ownership block and matching SHA-256 bindings.
- **Controlled-Variable Caution**:
  - Compared with `G4 Consumer Sample 001`, three variables changed simultaneously: linked worktree -> standalone clone, `codex exec` -> interactive Codex, and unverified trust -> explicit `/hooks` trust. This proves the new combination works; isolating every pairwise interaction remains bounded by the 6-probe matrix in `G4 Consumer Sample 001`.
- **Not Claimed**:
  - Does **not** constitute a G4 natural product delivery PASS (no product task was implemented).
  - Does **not** prove zero-intervention setup (manual `/hooks` trust was required once for the new clone).
  - Does **not** validate Gemini CLI or Antigravity lifecycle parity (separate platform track `GM-S0`–`GM-S3`).
