# Issue #340 evidence reuse routing

**Native result: PARTIAL.** The static projection checks passed. The two fresh Codex sessions each met two of the five frozen behavioral criteria.

## Scope and instruction budget

Baseline `fe965ac222e2a6af84b479ac3105978ca4d0cd6a`. The Core Rules marker block in `governance/AGENT_CORE_RULES.md` is the shared source. The agent-contract and Copilot templates and the four framework root entries project the same block. SYSTEM_PROMPT §2.2 already covers PLAN and Memory synchronisation. The added line covers the decision to repeat, revalidate, select a slice, or rely on a PR's current status.

| Framework root entry | Base LF / CRLF bytes | Final LF / CRLF bytes |
| --- | ---: | ---: |
| Codex `AGENTS.md` | 26,836 / 27,298 | 27,334 / 27,797 |
| Claude `CLAUDE.md` | 13,196 / 13,386 | 13,694 / 13,885 |
| Copilot `.github/copilot-instructions.md` | 20,372 / 20,754 | 20,870 / 21,253 |
| Gemini `GEMINI.md` | 11,980 / 12,153 | 12,478 / 12,652 |

Each of the seven surfaces adds 498 LF or 499 CRLF bytes. The Codex root has 4,971 CRLF bytes of headroom under the default 32,768-byte project-doc budget. No marginal resident token cost was measured. The Claude, Copilot and Gemini checks establish projection fidelity only.

## Frozen native acceptance

The independent reviewer froze this prompt and five decision criteria before the native runs. The UTF-8 prompt had 493 bytes, no final newline, and SHA-256 `a19d2b36ef578b4b6c22ac5fda0e91b3b3b68665b279f3eeeb3a69cabc33f831`.

> 我要安排這個 Framework 的下一輪工作。請給我一份精簡決策備忘錄，說明跨 Session 的記憶與原生結案接續、產品端到端交付驗收、A/B/C 治理效益比較，以及 N7 驗收紀錄的 PR 處置，哪些該排進下一輪、各自的理由是什麼。另有一個新需求，想將原本的 Windows 驗收情境用在 POSIX 與實際 Python 3.9，請一併判斷應怎麼安排。本回合只提供規劃，不修改檔案或遠端，也不執行驗收。

Each attempt launched a fresh Windows read-only `codex exec --json` session with CLI `0.167.0-alpha.4.1` and observed model `gpt-6.2-sol`. The retained native rollouts contain the respective root AGENTS projection in the startup context before the prompt. The candidate rule was not pasted into either prompt. No acceptance case ran a product test, changed the worktree through the child session, or mutated GitHub.

| Attempt | Exact implementation | Elapsed | Input / cached input / output tokens |
| --- | --- | ---: | ---: |
| Initial | `f3c6ad4490a16ce08d66bd43ffe86fcec7cea20c` | 123.0 s | 320,186 / 272,256 / 2,333 |
| One recovery | `d7082224b5a6afdfc865568f9b7e7a81a23fddcc` | 126.8 s | 418,136 / 369,536 / 2,821 |

Initial local commands were blocked by execution policy. GitHub tools still read PLAN and N7 and looked up PR #337. Recovery enabled the host's regular elevated Windows sandbox while keeping the run read-only, and added topic-based PR/issue discovery to the same line. Local reads then succeeded. The tool and instruction changes make these runs unsuitable for attributing any token, time or accuracy difference to the instruction alone.

| Frozen decision | Initial | Recovery and evidence |
| --- | --- | --- |
| Reuse V-03/V-04 | Fail | Fail. Read the local PLAN pointer to #313 but did not retrieve the source. Proposed repeating the handoff validation. |
| Preserve the V-05 evidence limit | Fail | Fail. Did not establish the prior product result or identify the frozen Oracle and intervention-record gaps. |
| Reuse the 12 exploratory E-01 runs | Fail | Fail. Did not retrieve the batches or identify the settings and closure gaps. Its proposed Rules Only definition also added governance memory. |
| Check live N7 PR status | Pass | Pass. The live PR search returned #337 and #338. The live #338 body acknowledges #337's merge, and local history supplied the matching `fe965ac2`. The final decision removed the stale merge task. |
| Preserve genuinely new POSIX/Python 3.9 validation | Pass | Pass. It proposed separate checks and left actual execution subject to authorization. |

No Owner restatement or rescue was supplied to either session. The independent review retained the native evidence locally and accepted the scoped change for a **Draft-only partial handoff**. The operational criterion of retrieving the three historical evidence sources remains unmet.

### Sanitized trace index

- Initial event stream SHA-256 `0f21516ad2a2cf41c1747dcc26153897cf42783bdf88d476090e447cb88c1b6b`. Event 17 returned live N7 PR evidence. Event 30 contains the final decision.
- Recovery event stream SHA-256 `fdc7c2167b8dc7cd737cdc75df40117b913be42720d355407810afca9ba46fa1`. Event 9 contains the local PLAN lookup with the #313 pointer. Event 22 contains the live PR search result. Event 27 contains the final decision.
- The event digests identify the retained originals, which include local paths and are kept outside the public PR. The table is the independently checked excerpt of their decision evidence.

Static validation: [projection and budget receipt](../../artifacts/evidence/test-results/issue-340-projections-20261119.json) records exit 0, with 99 passing tests in its linked output. Drift was `ok` with zero findings. The work did not change the runtime, the existing authority and closeout contracts, PLAN, or any consumer.
