# E2 Consumer Identifier and F-7 Evidence

Status: evidence-only index; consumer identified; historical F-7 transcript
fingerprinted; durable 2026-07-14 consumer WIP evidence present; adoption remains
partial

## Consumer Identifier

Stable evidence identifier: `E2-CONSUMER-02`

Consumer repository: `lenoveo-isp-tool-avalonia`

Consumer root observed on the evidence machine:
`E:\BackUp\Git_EE\lenoveo-isp-tool-avalonia`

The identifier is bound by repo-local VS Code Copilot session transcripts that
reference the consumer's `contract.yaml`,
`governance/framework.lock.json`, `memory/2026-07-01.md`, and
`external/ai-governance-framework` submodule. This identifies the consumer; it
does not identify the engineer and does not bind the separate nine-file C# /
Avalonia snapshot to this repository.

## Local Evidence Sources

The raw transcripts remain machine-local because they include broader private
workspace conversation. This index stores only the minimum identifiers,
fingerprints, and bounded findings needed for independent rechecking on the
evidence machine.

| Source | Role | SHA-256 | Size |
| --- | --- | --- | ---: |
| VS Code Copilot transcript `c416a54e-e111-4d15-9631-4802d69b6dac.jsonl` | Binds the 2026-07-01 governance refreshes to the consumer and records commits `77fdf15` and `fc59aae`. | `9f22db8eddba889d00064e1a9e7617c6de9882daeb2f70ab8bbd1cb1d793c244` | 261,259 bytes / 584 lines |
| VS Code Copilot transcript `5371be75-924c-4e51-b9eb-56bc426bff0a.jsonl` | Records the 2026-07-02 F-7 dry-run, apply, and human-readable adoption table. | `150d03760a9197543a63bde9392e7e59775e4efc10dab9cee1ff8fb2c775ffa1` | 155,475 bytes / 356 lines |

Evidence root on the observed machine:
`C:\Users\reiko\AppData\Roaming\Code\User\workspaceStorage\8cacedb69ae189d7391ea4131ea4d386\GitHub.copilot-chat\transcripts`

## Durable Consumer Evidence — 2026-07-14

The governed follow-up was performed in an isolated clone so the original
consumer checkout would not be modified. The reviewed chain is:

`3a6af10` → `0462550` → `eadd2fb` → `8522a96` → `8199336`

Artifact paths in the table below are consumer-repository paths committed on
that WIP chain; they are not paths inside this framework repository.

| Commit or artifact | Evidence role |
| --- | --- |
| `0462550` | Commits the reviewed five-file F-7 update: `.gitignore`, `AGENTS.md`, the framework gitlink, `governance/.update-receipt.json`, and `governance/framework.lock.json`. |
| `artifacts/evidence/test-results/receipt-f7-consumer-postcommit-20260714.json` and `.txt` | Preserve the post-commit F-7 dry-run. It reports `f7_final_status=full_update_completed`, a freshly verified upstream target, `framework_pointer=already_current`, and `lock_consistency=consistent`. |
| `eadd2fb` and `8522a96` | Record and publish the consumer F-7 evidence chain to the canonical GitLab WIP branch. |
| `artifacts/evidence/test-results/receipt-gitlab-consumer-f7-push-final-20260714.json` and `.txt` | Verify that the canonical WIP branch resolved to `8522a96`; the receipt is explicitly bound to that same commit. |
| `8199336` | Adds the raw receipt outputs and final remote receipt without rewriting the historical receipt identity. A fresh remote check after publication resolved the WIP branch to `8199336`. |

Canonical consumer branch:
`wip/gavinwu/install-state-false-positive`

The original consumer's committed state was intentionally left at parent commit
`3a6af10`, with framework gitlink `9bfed06c`. Therefore, the durable evidence
proves a published isolated WIP branch, not an update to that committed state or
a merge into the consumer's default branch.

## Event and Commit Trace

1. On 2026-07-01, the consumer transcript records two framework pin refreshes:
   `77fdf15` moved the submodule to `ff96cfad`, then `fc59aae` moved it to
   `c7a63c05`. Those runs used version compatibility, `adoption_doctor`, and a
   product build; they did not execute the F-7 entrypoint and therefore are not
   F-7 completion evidence.
2. Framework commits `d37d937d`, `28a3ebb5`, and `435509c8` introduced,
   localized, and relayed the adoption feature table. Commit `1b71ed92`
   required the human adoption summary in update reports. Commit `105ec30c`
   required F-7 table relay, with `9bfed06c` recording that wording in framework
   memory.
3. Consumer commit `3a6af10` pinned the framework to `9bfed06c` on
   2026-07-02. It is evidence that the consumer adopted the table-relay baseline;
   it is not the later F-7 execution result.
4. The second transcript records an actual F-7 dry-run and apply against the
   consumer at framework commit `7eb96d0`. The operator-facing report was
   emitted at 2026-07-02T07:29:31Z and included the human-readable adoption
   table. No parent-repository commit was created for that F-7 run.
5. On 2026-07-14, isolated consumer commit `0462550` committed a reviewed F-7
   update against framework commit `cc934dc0`. The post-commit dry-run reported
   `full_update_completed` for the F-7 workflow while the adoption summary
   remained `partial`.
6. Commits `eadd2fb`, `8522a96`, and `8199336` published and contained the
   consumer-side memory and receipt evidence on the canonical GitLab WIP
   branch. The final remote receipt is bound to `8522a96`; `8199336` commits
   that receipt and its raw output.

## Historical F-7 Result Preserved by the Transcript

The F-7 report's important result was `user-facing adoption status: partial`.
In plain language, the table made the incomplete surfaces visible instead of
presenting the framework pointer update as complete adoption.

| Reported surface | Recorded state |
| --- | --- |
| Framework topology | `submodule_consumer` |
| Static framework files | available |
| Repo-specific rules | available |
| Git hooks | available on the observed machine |
| Domain contract | available |
| Validator surface | not adopted |
| Runtime-capable governance | `not_checked` |
| Memory workflow | `not_checked` |
| Human-readable adoption summary | reported |

The same report disclosed that `governance/framework.lock.json` still pointed
to `9bfed06c` while the F-7 run had advanced the submodule to `7eb96d0`.
Consequently, this artifact supports a partial / incomplete update result, not
`full_update_completed` or `already_current`.

## 2026-07-14 F-7 Result

The isolated rerun resolves the earlier pointer/lock inconsistency and supplies
a committed consumer-side F-7 artifact. Two statuses must remain separate:

| Status layer | Result | Meaning |
| --- | --- | --- |
| F-7 workflow | `full_update_completed` | Every required F-7 stage for this isolated run returned an eligible completed, verified, or not-applicable state. |
| Governance adoption | `partial` | The consumer still lacks a declared validator surface; runtime-capable governance and memory workflow remain `not_checked` in the adoption summary. |

This is evidence that one real `submodule_consumer` update path completed. It is
not evidence that every consumer role is supported or that this consumer has
full governance adoption.

## Evidence Grade and Claim Boundary

Can claim:

- `E2-CONSUMER-02` identifies `lenoveo-isp-tool-avalonia` as the C# / Avalonia
  consumer associated with the recorded governance-update sequence.
- A local Copilot transcript records an actual F-7 dry-run and apply followed by
  a nine-row, human-readable adoption table.
- The recorded table classified the consumer as partial and exposed missing or
  unverified validator, runtime, memory, and lock-consistency surfaces.
- Framework and consumer commit history corroborate when the table-relay
  remediation entered the consumer's framework pin.
- The isolated 2026-07-14 WIP chain contains a committed F-7 result, consistent
  framework pointer and lock, raw receipt outputs, and remote publication
  evidence through `8199336`.
- For that isolated run, F-7 workflow completion is supported while governance
  adoption remains partial.

Cannot claim:

- full or correct consumer adoption;
- that the 2026-07-01 pointer refreshes were completed F-7 runs;
- that the WIP evidence was merged into the consumer's default branch or
  applied to the original consumer checkout;
- that one successful `submodule_consumer` run proves F-7 works for every repo
  role or consumer;
- that the engineer independently understood every row beyond the existing
  retrospective self-report;
- that the nine-file C# / Avalonia snapshot came from, was loaded by, or was
  followed by this consumer;
- the engineer's identity, intervention count, or causal product/runtime effect.
