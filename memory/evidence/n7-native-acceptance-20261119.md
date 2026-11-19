# N7 native closeout acceptance

2026-11-19. The framework runtime used for this validation is `98142f55c6cdb8a45162766b2cc2d3c1ab67559e`, the merge commit for #335. The fixtures are disposable Windows consumers.

## A · PLAN reconciliation

[#336](https://github.com/Gavin0099/ai-governance-framework/pull/336) is `READY_FOR_OWNER` at `c884ae1ea4a4fdd1f6f6b49a781ef88343dd1aa4`. All three required checks passed and the exact-head Codex review reported no findings. [PR CI](https://github.com/Gavin0099/ai-governance-framework/actions/runs/44447837760) · [Exact-head review](https://github.com/Gavin0099/ai-governance-framework/pull/336#issuecomment-6998266473) Main still resolved to `98142f55` at the handoff. The owner merge decision is pending.

## B0 · Codex fixture and launcher

The test consumer is `7e5f0bccb38fb8885e9798318a0f7c18fe42c205`. Its committed gitlink, checked-out submodule and framework lock all matched `98142f55`. Existing SessionStart and Stop hooks were installed and trusted. The native client was Codex CLI 0.169.0-alpha.11.1 and the fixture ran Python 3.13.5.

Both prior launcher attempts exited without a recorded session ID or native Stop. The retry passed the prompt as an argument and closed stdin. Its text event renderer exposed hook lifecycle events. The JSONL control emitted thread and turn events and created an envelope, but lacked a Stop event in that output.

## B1 · Codex Stop before prepare

**PASS.** A new native session reported `SessionStart Completed` and `Stop Completed`, with exit code 0. The trace and v1.1 envelope agreed on session identity. The envelope named the Codex provider, exact fixture commit and fixture root. From the immediately preceding inventory to the post-Stop inventory, only the current-session pointer changed and the new envelope appeared. The earlier receipt and release stayed byte-identical, and the new session generated neither.

| Source | SHA-256 |
| --- | --- |
| Native trace | `7c0b906d2f977b782df21f59afaa3b8375751f5f88e58cc949496750e08b80a2` |
| Session envelope | `a1906299c94be49fd7c4972471c2622b0a5dd7676112a66524ccd9c317cc9e14` |
| Inventory before this Stop | `0f19932f6cb94e7df84ef4163ce2ec4549fcfa9734cd84b177622bf69d990d6d` |
| Inventory after this Stop | `cb79935c24946bb3f5639bf897840261906876559b5893c8966732126785d576` |

## B2 · Codex prepared Stop and replay

The first prepared attempt resumed the B1 identity and produced a canonical closeout, a bound receipt and R2 generation 2 in `RELEASED` through the native Stop. The receipt set `gate_blocked=true`. Passing unittest stdout was present, but the strict gate required the canonical test-result artifact. Generation 2 is excluded from positive acceptance. The recovery uses a fresh native session and retains the first receipt for audit.

The recovery passed. A new native unprepared Stop and its exact-ID prepared resume reached `OWNED` and then a canonical valid closeout and `RELEASED` at generation 3. The receipt reported `ok=true`, `gate_blocked=false` and exit code 0. The reviewer matched the candidate, shared text and receipt digests to the R2 binding and matched the completion marker to the actual canonical bytes.

The fixture's pytest run passed 5 tests and 8 subtests. The JUnit ingestor wrote the test-result artifact with 13 passes and zero failures, and exited 1 because the test names did not satisfy its invalid-input, boundary and failure-path coverage classification. The native strict gate admitted the closeout with the artifact present. Coverage classification remains unresolved.

| Replay on the same native session | Normal | Controlled digest change |
| --- | --- | --- |
| Native Codex Stop | Completed with no new closeout or receipt | Completed with no new closeout or receipt. The altered canonical bytes remained in place. Native refusal was `NOT_REACHED` after release. |
| Direct R1 entry | `ALREADY_CONSUMED` | `CLOSEOUT_REPLAY_MISMATCH` |
| Direct R2 reconcile | `ALREADY_RELEASED` | `RELEASE_PROOF_INVALID` with `canonical_closeout_digest_mismatch` |

The native replay inventories allow at most a current-session pointer update. Restoration verified the original canonical bytes and the release and receipt remained unchanged.

| Source | SHA-256 |
| --- | --- |
| Candidate | `e346d467fa18ae135e078712e1e3adc358380d027c073025c4b1f30adb21886d` |
| Canonical closeout | `547b2973372d96884ea443fddf971235bea14d6f699efbfd8931c893370d35f7` |
| Admitted receipt | `3b016ad409bc1efd2c3d2957e4b1b2ff89952b2c6538a236f5283a8d21d11020` |

## B3 · VS Code Copilot Agents window

**PASS on the isolated retry.** The VS Code fixture commit `8a5f130b5d597ada349aedd76854a947f1e02922` pins the same framework and updates the installed Copilot lifecycle bridge to the matching source. The previous fixture changes and existing closeout artifacts were captured before upgrading. The retry started from a clean clone of that commit in the already-trusted disposable workspace, using its existing workspace trust.

The original fixture's native unprepared Stop completed without creating a closeout or R2 generation for that session. Its prepared attempt was rejected during closeout. The coordinator's prepare initially had an invalid field type and was corrected before ownership was acquired. The accepted candidate then attributed coordinator-run pytest to the native transcript and lacked an observable work anchor and legacy pytest evidence path. Native `agentStop` returned code 1. The canonical result was `inconsistent`, so the completion marker and new release were absent despite the reserved receipt reporting a clear test gate. That generation remained in `HOLD` and was preserved.

The retry used a new native identity with a v1.1 `github-copilot-vscode` envelope bound to the fixture root. The first native `agentStop` completed with no candidate, receipt, completion marker or R2 owner. The coordinator ran pytest with its normal cache and recorded the one passing fixture test and its evidence path in the official prepare input. The candidate made no claim that the agent itself ran the tests. The normalized test result was written. The ingestor exited 1 for unmet fixture coverage-name categories.

The coordinator invoked formal prepare with the verified native session ID. Prepare returned `OWNED`, generation 1, and `closeout_executed=false`. The second turn in the same real Agents window produced a successful `agentStop`. A separately checked completion marker matched the canonical closeout digest. The receipt had exit code 0, `ok=true` and `gate_blocked=false`. R2 owner and release both recorded `RELEASED` generation 1 with the matching receipt digest. The candidate and shared text digests also matched the receipt binding.

| Source | SHA-256 |
| --- | --- |
| Unprepared snapshot index | `4aa622880a9d882f34404d7c559d36aec4acbc425e37cad5e3f6dba4949ffd4b` |
| Prepared snapshot index | `fa2caa3bfe8531cd287f9fd85c8998e8ca063700ebfc47f9d075061e40a46e86` |
| Canonical closeout | `2295ba844968959d5d121bbda63c13772b35c7fa61ca6f223266e08c06354980` |
| Admitted receipt | `7a02ae0b52d5014ccb4e50d020fad2724b3d5d7b5cf5e8332876cc9b92822ee3` |
| R2 release | `e2201f7ef4f94db28f395801aac8540a0baaab929fd61565181a90e398b38205` |

## Boundary and next decision

This records Windows native lifecycle evidence for the named clients and pinned runtime. Raw traces, session identifiers and fixture paths are retained locally. The evidence does not qualify POSIX, Python 3.9, end-to-end delivery in a real consumer, Codex native replay refusal, or Gate 3. The follow-up for the pending PR dispositions and the real consumer is subject to the existing owner decisions. The PLAN reconciliation remains on its separate #336 decision path.
