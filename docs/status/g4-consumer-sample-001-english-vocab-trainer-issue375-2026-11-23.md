# G4 Consumer Sample 001 — `english-vocab-trainer` Issue #375 (`FAIL / NOT PERSISTED`)

- **Record Class**: Real Consumer Natural Work-Item Observation (**G4 Consumer Sample 001**)
- **Naming Distinction**: Distinct from the earlier self-hosted `docs/status/g4-work-item-case-001-owner-summary-2026-07-22.md`. Do not merge or double-count across samples.
- **Separate Infrastructure Record**: See `docs/status/codex-native-ab-lifecycle-verification-english-vocab-trainer-2026-11-23.md` for the later standalone-clone native lifecycle verification (`PASS`, infrastructure only). That infrastructure record **does not overwrite** this sample's `FAIL / NOT PERSISTED` outcome.
- **Date**: 2026-11-23
- **Archived Against Framework Main**: `0d7af3c8a017ecd01d023e2c22fad9d2ccc0b42d`
- **Consumer Repository / Base**: `english-vocab-trainer` `origin/main@b24921ea11220fc3b591f142824697c70359c807`
- **Consumer Adopted Governance Lock**: `6c7e24c3161fe80dc4c5bd6bfe1bec5cd04fd8dc` (`adopted_release: 1.2.0`; intentionally kept un-upgraded to measure routine baseline cost separately from upgrade cost)
- **Execution Environment**: Isolated linked git worktree (`E:\BackUp\Git_EE\_worktrees\evt-g4-issue375`, branch `codex/g4-sample1-issue375`) + non-interactive `codex exec` (`codex-cli 0.171.0-alpha.13`) + independent read-only subagent review
- **Work Item**: `english-vocab-trainer` Issue #375 — hyphenated compound word count in story draft checker (`red-hat` must count as 1 word rather than 2)

---

## 1. Outcome Summary (Frozen as `FAIL / NOT PERSISTED`)

| Verification Dimension | Status | Evidence & Boundary |
|---|---|---|
| Product fix & local commit | **PASS (local only)** | Local commit `fd98e078c146867fb52fa9bd73ff329d7b3d8aab` (`.codex/skills/garden-story-authoring/scripts/check-story-draft.mjs` + `scripts/story-draft-check.test.mjs`, `+40/-11`). Also removed `#!/usr/bin/env node` shebang to unblock Windows Vitest (adjacent engineering edit; scope to confirm before any product PR). **Unpushed; GitHub Issue #375 remains `OPEN`.** |
| Automated unit tests | **PASS** | `vitest run scripts/story-draft-check.test.mjs` -> **31/31 PASS** (independently re-verified during review). |
| Independent code review | **PASS** | Independent read-only subagent (`5121c876-32b3-46d0-83d3-d1a6c9791c80`) on `a2875ecd`: **0 P0 / 0 P1 / 0 P2 / 0 P3**. |
| Canonical memory record | **PASS (local only)** | Local commit `a2875ecd584b22c02b8c9fe2aee020d747926211` (`memory/2026-11-23.md` via `governance_tools.memory_record` + `memory/03_knowledge_base.md`). Submodule and `governance/framework.lock.json` untouched. |
| Safe refusal on missing identity | **PASS (agent contract compliance)** | Missing `.current-session-id` -> Codex refused to fabricate candidate/closeout and explicitly reported `NOT PERSISTED` on both attempts. Note: proves agent reporting discipline, **not** that an unexecuted hook intercepted an error. |
| Native `SessionStart` / `Stop` hooks | **FAIL** | Neither `codex exec` attempt loaded `.codex/hooks.json`; `.current-session-id` was never created. |
| Session A -> `RELEASED` -> Session B | **FAIL / NOT PERSISTED** | Ownership never entered `OWNED`/`RELEASED`; Session B handoff not reached. |

---

## 2. Measurement Record (Corrected Owner Accounting)

| Metric | Recorded Value | Notes & Attribution Boundary |
|---|---|---|
| `total_codex_minutes` | **13m 07s** | Attempt 1 (`06:58:42Z`–`07:04:27Z`, 5m45s) + Attempt 2 (`07:05:18Z`–`07:12:40Z`, 7m22s). Excludes `npm ci` (20s) and independent review (~1m). |
| `environment_retry` | **1 full retry (5m 45s)** | Attempt 1 blocked by `workspace-write` sandbox on `.codex/` and linked-worktree `.git` metadata (44% of total Codex time, 35% of total input tokens). Environment friction, **not** directly attributed to AI Governance Framework. |
| `attempt2_split_minutes` | **4m 28s task / 2m 54s post-commit** | Product commit `fd98e078` landed at `07:09:46Z` (4m28s). Remaining 2m54s included memory record, receipt, and diagnosing why hooks did not load (not purely routine governance overhead). |
| `total_tokens` | **4,751,569 input / 25,342 output** | Attempt 1: `1,670,720` in (`1,578,240` cached / `92,480` non-cached), `11,017` out. Attempt 2: `3,080,849` in (`2,959,360` cached / `121,489` non-cached), `14,325` out. ~95.5% of input tokens were cached; API cost must price cached vs non-cached separately. |
| `governance_tokens` | **Estimated ~35–40% of Attempt 2 (unmeasured)** | `codex exec --json` aggregates usage per turn, not per tool call. Retained explicitly as an estimate. |
| `human_interventions` | **1** | Switched sandbox parameter for Attempt 2 (`danger-full-access` used strictly as an isolated test workaround; **not** authorized for routine consumer development). |
| `false_blocks` | **0 observed** | Does not imply a zero false-block rate; hook-loading failure is tracked separately under environment/integration failure. |
| `true_catches` | **1 class of safe refusal** | Honest `NOT PERSISTED` refusal when native session identity was absent. Routine `memory_record` completion is not double-counted as a catch. |
| `review_rework_rounds` | **0** | Independent review passed on first pass (0 findings). |
| `session_ab_loop` | **FAIL / NOT PERSISTED** | Formal closeout and Session B handoff did not complete. |
| `local_preserved_commits` | `fd98e078`, `a2875ecd` | Retained locally in `E:\BackUp\Git_EE\_worktrees\evt-g4-issue375`; unpushed, unmerged. |

---

## 3. Minimal Hook Diagnosis Summary (`codex-cli 0.171.0-alpha.13`, Isolated `CODEX_HOME`)

To isolate why `.codex/hooks.json` did not load without modifying `~/.codex/config.toml`, the framework, or consumer hooks, 6 minimal `"Reply OK"` probes were executed under an isolated temporary `CODEX_HOME` using a clean temporary regular clone (`regular-clone`, marker `FROM_CLONE_HOOK`) and a linked worktree (`linked-wt`, marker `FROM_WT_HOOK`):

| Probe | Checkout Type | Project Trust | Hook Trust / Flag | Exit | `clone_marker` | `wt_marker` | Finding |
|---|---|---|---|---:|---|---|---|
| `P1` | Regular Clone | Untrusted | `--dangerously-bypass-hook-trust` | 0 | `NO` | `NO` | Untrusted project skips `.codex/hooks.json` even with hook-trust bypass |
| `P2` | Regular Clone | Trusted (`config.toml`) | `--dangerously-bypass-hook-trust` | 0 | `FROM_CLONE_HOOK:` | `NO` | `codex exec` triggers `SessionStart` when both trusts hold |
| `P3` | Linked Worktree | Untrusted | `--dangerously-bypass-hook-trust` | 0 | `NO` | `NO` | Untrusted linked worktree skips hooks |
| `P4` | Linked Worktree | Trusted (`wt` only) | `--dangerously-bypass-hook-trust` | 0 | `NO` | `FROM_CLONE_HOOK:` | Linked worktree loaded `.codex/hooks.json` from the **main checkout** (`regular-clone`), not from `linked-wt` |
| `P5` | Regular Clone | Trusted (`config.toml`) | None (no `[hooks.state]` hash) | 0 | `NO` | `NO` | Trusted project without hook trust does not execute hooks |
| `P6` | Linked Worktree | `--trust` flag | `--trust --dangerously-bypass-hook-trust` | 0 | `NO` | `FROM_CLONE_HOOK:` | `--trust` enables project trust, still resolves hooks from the main checkout |

- **Interpretation Boundary**: Consistent with Codex Hooks documentation noting that linked worktrees can load project hooks from the primary checkout. Because `E:\BackUp\Git_EE\english-vocab-trainer` main checkout was on an older 2026-09 branch lacking `.codex/hooks.json`, `evt-g4-issue375` hooks did not load. This does **not** prove `session_start.py` is bug-free across all versions/OSes, nor does it turn Sample 001 into a PASS.

---

## 4. Claim Ceiling (`NOT_CLAIMED`)

- **Not Claimed**:
  - Formal delivery of `english-vocab-trainer` Issue #375 (commits remain local and unpushed; Issue #375 is still `OPEN`).
  - Completion of G4 or proof that governance benefit exceeds cost.
  - Cross-consumer portability or compatibility of `codex exec` + linked worktree without pre-configured primary checkout hooks and trust.
  - Behavioral equivalence with latest framework `main` (`0d7af3c8` / `1a30faed`), since this consumer ran on `6c7e24c3`.
