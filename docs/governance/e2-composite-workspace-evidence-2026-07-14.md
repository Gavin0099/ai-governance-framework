# E2 Composite-Workspace Evidence — eToken System ART

Status: review-only evidence packet; owner-relayed user report plus repository
history and isolated F-7 test evidence; no consumer commit or push

Stable evidence identifier: `E2-CONSUMER-03`

Audited local workspace root: `E:\BackUp\etoken system ART`. This packet does
not refer to the separate similarly named checkout under `E:\BackUp\Git_EE`.

## Reviewer Summary

This packet records one engineer operating one multi-root workspace rather than
three independent consumers. The workspace uses `etoken-system-art` as its
governance and memory center and opens `etoken-server-art` and
`etoken-client-art` as sibling product repositories.

The owner-relayed user response reports that the engineer works across all
three repositories in one AI-agent task, needed no owner assistance after the
June submodule adoption, and observed no later AGENTS, PLAN, or daily-memory
update failure. Repository history corroborates continued engineer-authored
development and memory/PLAN maintenance, but it cannot independently prove
zero owner assistance or complete daily-memory continuity.

An isolated 2026-07-14 F-7 run successfully updated the governance center from
framework commit `f278172a` to canonical GitLab `main` commit `486bda76` and
then returned `framework_pointer=already_current` on a post-apply dry-run. The
same test also exposed a composite-workspace boundary: F-7 updated only
`etoken-system-art`; the server and client sibling repositories did not
automatically receive AGENTS files, hooks, a domain contract, or repository
readiness.

Reviewer disposition requested: accept this as bounded E2 onboarding and F-7
workflow evidence for one composite consumer, while retaining the sibling
governance gap as an open finding. Do not count the three repositories as
three independent onboardings.

## Consumer Identity and Workspace Topology

| Field | Recorded value | Evidence grade |
| --- | --- | --- |
| Stable identifier | `E2-CONSUMER-03` | packet-local identifier |
| Consumer form | one composite multi-root workspace | workspace artifact plus owner-relayed user response |
| Governance and memory center | `etoken-system-art` | owner-relayed user response; repository structure |
| Product siblings | `etoken-server-art`, `etoken-client-art` | workspace artifact plus owner-relayed user response |
| Operator identity | intentionally omitted | privacy boundary |
| Relationship to `E2-CONSUMER-02` | separate consumer; `E2-CONSUMER-02` remains bound to `lenoveo-isp-tool-avalonia` | existing tracked E2 record |

The tracked `eToken_System_ART.code-workspace` file opens the system, server,
and client repositories. It also contains a stale-looking `../etoken_dongle`
entry whose target was absent during this audit. That absent path is not
counted as a fourth consumer or as an F-7 failure.

Workspace artifact fingerprint:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `etoken-system-art/eToken_System_ART.code-workspace` | 659 | `ccc78455b09756a78ccaf26e8a74cc5f41ec42994a6e92538cfb7627e986d8b5` |

## Owner-Relayed User Response

Source date: 2026-07-14. Evidence grade: `owner-relayed / user-attributed`.
No separate user transcript or ticket was added to the repository.

| Question | Recorded response |
| --- | --- |
| Is the multi-root workspace normally used to operate the system, server, and client repositories together? | Yes. |
| Can one AI-agent task modify all three repositories? | Yes. |
| Is `etoken-system-art` treated as the shared governance and memory center? | Yes. |
| Was owner help needed after the June submodule adoption? | The user reported that no help was needed. |
| Were later AGENTS, PLAN, or daily-memory update failures observed? | The user reported none. |
| Was an isolated latest-F-7 test authorized? | Yes, with an explicit prohibition on pushing the tested repository. |

The user responses support the bounded qualitative claim that the engineer
perceived the post-adoption workflow as self-sufficient. They do not by
themselves prove intervention count, continuous agent compliance, or complete
memory updates on every day.

## Repository History Anchors

Original repositories were read-only during the F-7 test and remained clean.

| Repository | Audited HEAD | Role in this packet |
| --- | --- | --- |
| `etoken-system-art` | `5a6e15e4d2cf3c45ce5a497a292509649f17f835` | governance, workspace, PLAN, and memory center |
| `etoken-server-art` | `c12e600f4c85f27ef8a58031c19cea5a8f926b7f` | sibling product repository |
| `etoken-client-art` | `85e289d2dd933c5f2fd4f8ceb2134baa141cb74a` | sibling product repository |

Relevant historical anchors in `etoken-system-art`:

| Commit | Bounded significance |
| --- | --- |
| `4c36774148698c11961534bfd901c8b03d4e2ed5` | owner-authored initial governance verification surfaces |
| `22dd77950caacd1422fd1465d62e2b1ee524dec1` | engineer-authored reorganization that removed the root surfaces and moved governance content |
| `56a4f499e0cd594d7b16284376037bc75dcc057f` | engineer-authored adoption of the framework submodule and removal of copied framework content |
| `a07630831dbdec2ceeb04c75a69a093521893881` | engineer-authored PLAN relocation and reference alignment |
| `f0f8a4cba26c5efac57505d2e12ee9bb49608b87` | engineer-authored 2026-06-30 daily-memory record |
| `5a6e15e4d2cf3c45ce5a497a292509649f17f835` | later merge to main after the governance and memory updates |

These commits corroborate adoption work and continued repository activity.
Authorship and commit sequence are not proof that no unrecorded owner guidance
occurred.

## Isolated F-7 Evidence

Test date: 2026-07-14. The three repositories were cloned into a machine-local
temporary workspace. No original consumer repository was modified. No commit
or push was created from the isolated workspace.

The framework submodule retained its canonical GitLab origin. Git objects were
preseeded from the local framework checkout to avoid re-downloading the large
history; F-7 itself still resolved and fetched the target through the formal
GitLab remote.

| Stage | Result |
| --- | --- |
| Original committed framework pointer | `f278172ab9b4093d8755014f687913989d6991da` |
| Canonical GitLab target | `486bda762d71adaddbbf3293b2c5597c6632b143` |
| Initial canonical dry-run | `ok=True`; target source `fresh_remote_ls_remote`; update available |
| Apply | `ok=True`; `f7_final_status=full_update_completed`; target source `fresh_remote_fetch_head` |
| Post-apply dry-run | `ok=True`; `framework_pointer=already_current`; `f7_final_status=full_update_completed` |
| Repo-local instruction stage | updated, then verified |
| Hook/validator enforcement stage | local hooks updated, then verified; validator adoption remained unverified because no domain contract exists |
| Memory-writer coverage | verified by F-7 surface checks |
| Existing-memory normalization | verified by F-7 stage result |
| Adoption summary | `partial`; missing surface: `domain_contract` |
| Commit / push | none / none |

The apply receipt reported:

- `framework_before=f278172ab9b4093d8755014f687913989d6991da`
- `framework_after=486bda762d71adaddbbf3293b2c5597c6632b143`
- `target_fresh_upstream_verified=true`
- `target_source=fresh_remote_fetch_head`
- `update_status=updated`

Machine-local receipt fingerprint:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| isolated `governance/.update-receipt.json` | 1,412 | `4e0f967fb87a241d3ef3a61b7e5f9ff74c27e4fbe072f0287a1071c232445247` |

The receipt remains machine-local and is not a durable tracked artifact. This
packet preserves its fingerprint and bounded fields, but cannot guarantee the
temporary receipt will remain available for future byte-for-byte comparison.

## Sibling Governance Gap

The composite workspace is a real operating convention, but current F-7 scope
is repository-root based. The isolated test produced the following result:

| Surface | `etoken-system-art` | `etoken-server-art` | `etoken-client-art` |
| --- | --- | --- | --- |
| `AGENTS.md` / `AGENTS.base.md` | present after F-7 | absent | absent |
| AI Governance pre-commit / pre-push hooks | present after F-7 | absent | absent |
| `contract.yaml` | absent | absent | absent |
| `PLAN.md` | present | absent | absent |
| Explicit-framework-root readiness | partial composite center | `ready=false` | `ready=false` |

For both sibling repositories, readiness specifically reported:

- `git_repo_present=true`
- `plan_present=false`
- `contract_resolved=false`
- `hooks_ready=false`
- `framework_version_known=false`

The system repository's Copilot instructions name the server and client
repositories, but naming sibling paths does not install their repo-local
AGENTS files or hooks and does not make their independent Git roots ready.

This is an observed composite-workspace coverage gap, not evidence that F-7
failed for its current single-repository contract. The 2026-07-14
`full_update_completed` result applies to `etoken-system-art` only.

## Claim Ceiling

Can claim:

- One engineer uses one multi-root eToken System ART workspace across three
  repositories and regards `etoken-system-art` as the shared governance and
  memory center, based on an owner-relayed user response.
- Repository history independently corroborates framework-submodule adoption,
  PLAN/memory maintenance, and later development activity.
- Latest F-7 successfully updated an isolated `etoken-system-art` clone from
  `f278172a` to canonical GitLab `486bda76`, wrote a receipt, and returned
  `already_current` on the post-apply dry-run.
- The F-7 workflow completed for the governance-center repository while the
  user-facing adoption status remained `partial` because the domain contract
  was absent.
- The server and client sibling repositories did not automatically gain
  repo-local governance surfaces from the system-repository F-7 run.

Cannot claim:

- Three independent consumer onboardings or three independent operators.
- Independent verification that the engineer never received owner help.
- Complete daily-memory continuity or sustained agent compliance.
- F-7 completion for `etoken-server-art` or `etoken-client-art`.
- Cross-repository hook, runtime, CI, validator, or policy enforcement.
- Full governance adoption, domain correctness, release readiness, or runtime
  smoke success.
- A durable consumer commit, merge, or remote publication from this test.
- That the machine-local receipt will remain available after temporary-file
  cleanup.

## Reviewer Questions

1. Accept `E2-CONSUMER-03` as one composite-workspace onboarding record rather
   than three consumer records?
2. Accept the isolated F-7 run as evidence of the current single-repo workflow
   while preserving `adoption_status=partial`?
3. Record sibling governance coverage as an observed gap requiring a separate
   design/reconciliation slice before any cross-repo coverage claim?
