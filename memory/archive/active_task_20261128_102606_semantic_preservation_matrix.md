# N5 Plan A - Manual Semantic Preservation Matrix

Author: Codex Implementer, 2026-11-28. Base: c386ab5081a3a1079ff0766ff77ac697e247ef3e.

Status: **CANDIDATE ONLY / INDEPENDENT SEMANTIC-FIDELITY REVIEW PENDING**.
This is an author-prepared preservation proposal and traceability record, not an independent review verdict or authorization to replace active memory.

## Frozen identities and measurement

All paths below are relative to D:/agf-n5-cutover. All line references are 1-based and inclusive.

| Artifact | Exact path | Raw-byte SHA-256 |
| --- | --- | --- |
| Byte-exact predecessor archive | memory/archive/active_task_20261128_102606.md | 59a58fcb84f4464d67436f7a3f8e98ec055d2b3813e48e617184b3dc1df892e3 |
| Existing prepared manifest | memory/archive/active_task_20261128_102606_cutover_manifest.json | 4168669b52cd32ca9593dffde7d65596c510b960004cbb088d645fe481f05183 |
| Plan A candidate | memory/archive/active_task_20261128_102606_replacement_candidate.md | 32cac60cce9399a2ca1b8c4984e25f0ef205789f3b567b6b172a862a5a83f402 |
| Formal active memory, unchanged | memory/01_active_task.md | 59a58fcb84f4464d67436f7a3f8e98ec055d2b3813e48e617184b3dc1df892e3 |

The archive is byte-equal to the formal active file and matches the prepared manifest: 9,811 bytes, 136 CRLF sequences, no BOM, trailing LF. The manifest remains prepared; it has not been rewritten to imply verification, review, adoption or cutover.

| MemoryJanitor target | Lines | Chars | Level | Threshold interpretation |
| --- | ---: | ---: | --- | --- |
| Archive / unchanged active file | 136 | 9673 | WARNING | Character threshold reached; active pressure is not resolved. |
| Candidate | 117 | 6967 | SAFE | Below 180 lines and 8000 chars; also below the Owner's 7000-char target. |

Candidate: 6,967 bytes, LF endings, no BOM, trailing LF. Headroom below the SAFE character boundary is 1,033 chars. Measurement uses MemoryJanitor's UTF-8 text-mode Unicode character count, including normalized newlines, and splitlines(), including blank lines. It is not a byte-count substitute.

Reproduce the candidate measurement without writing active memory:

~~~python
from pathlib import Path
from governance_tools.memory_janitor import MemoryJanitor

candidate = Path("memory/archive/active_task_20261128_102606_replacement_candidate.md")
janitor = MemoryJanitor(candidate.parent)
janitor.active_task_file = candidate
print(janitor.check_hot_memory_status())
# (117, 6967, 'SAFE')
~~~

## Preservation interpretation

"Archive Lx-Ly" always means the byte-exact predecessor identified above, not the older 2026-10-23 archive. "Candidate Lx-Ly" always means the exact candidate SHA-256 above. Archive-only retention establishes recoverability, not canonical authority. The existing commit-bound sources remain the authority references; neither this matrix nor the archive creates a new authority source.

The candidate's Authority Index explicitly identifies the repository-relative archive path and its exact row numbers. Paths copied verbatim inside protected sections retain their original intended memory/01_active_task.md context: for example, archive/active_task_20261023_124358_cutover_manifest.json is relative to memory/. Candidate storage under memory/archive/ does not relocate that referenced source.

Every independent review result in the tables below is **PENDING**. Verbatim equality is a measured text property. Condensation and omission rationales are the implementer's proposals; they have not been certified as reviewed semantic equivalents.

## Complete section and archival map

| Predecessor section / exact archive range | Candidate location / preservation mode | Recoverability and intended decision effect | Independent review |
| --- | --- | --- | --- |
| Predecessor pointer comments, L1-L2; 2026-10-23 introduction, L6-L9 | Candidate L3 replaces the introduction; old comments/narrative archived only | Exact text remains at Archive L1-L9. The candidate still disclaims canonical authority and claim re-verification. The old archive path and recorded predecessor digest remain recoverable; no historical authorization is renewed. | PENDING |
| Title L4; separator blank lines L3, L5, L10 | Candidate L1, L2, L4 | Title retained; blank lines have no authority content. | PENDING |
| Current Gate 3 State, L11-L28 | Candidate L5-L22; all substantive text verbatim | Frozen source/register boundary, permanent rev9 rejection/no rev10, unauthorized future activities, design-only maturity and post-cutover STOP are unchanged. | PENDING |
| Irreversible State And Prohibitions, L29-L46 | Candidate L23-L40; all substantive text verbatim | NON_SUCCESS terminal consumption, no reuse/retry/replacement, no retrospective Gate 2 repair, unrelated dirty-work exclusion, fail-closed janitor, spent historical attempt and rollback/STOP rule remain explicit. The historical 2026-10-23 text inside this protected section is deliberately retained. | PENDING |
| Durable Authority And Evidence Index heading/table, L47-L58 | Candidate L41-L54; concise seven-row pointer table | Every original row L51-L57 has its own candidate row, exact archive line and full commit identity where one was recorded. Full blobs, digests, parent binding and use limitations remain at those exact archive rows; detailed proof follows below. | PENDING |
| Adoption-source qualification, L59-L62 | Candidate L55-L58; verbatim | Source/register committed bytes still carry candidate labels. ADOPTED derives from the recorded explicit owner decisions, never from commit existence. | PENDING |
| Other Retained Workstream State heading, L63-L64; active items L66-L75 | Candidate L59-L70; verbatim | M3-b-2B lacks two clean-context reports/verdict/implementation authority; M3-b-3, M4, B-1 and disclosure/config caveats are not upgraded. | PENDING |
| M3-b-2A obsolete pre-merge projection pointer, L65 | Archived only | Archive L65 retains the exact old-source pointer and PR #108 / a59b0aef checkpoint text. Independent durable recovery: memory/evidence/m3-b-2a-adoption-review-20261001/pre-adoption-active-task.md L61-L64; memory/2026-10-01.md L4-L15; memory/04_review_log.md L5297-L5306. This removes historical narrative, not the retained M3-b-2B prohibition. | PENDING |
| F-7 complete/inactive status and expansion prohibition, L76-L78 | Completed status archived; prohibition retained at Candidate L71-L72 | Archive L76-L77 preserves the completed/inactive statement. Candidate L71 says "Do not expand F-7 without a new observed consumer failure." The operative prerequisite is retained; completion does not create new work authority. | PENDING |
| Open Risks, L79-L91 | Candidate L73-L85; all substantive text verbatim | All four risks remain unresolved as recorded: session binding, parser shape, PLAN freshness discrepancy and historical live-byte dependency. No risk repair or current runtime requalification is claimed. | PENDING |
| Next Decision Boundary heading L92-L93 and old cutover step L94 | Candidate L86-L88; unreviewed current-task clarification | Old step remains at Archive L94. Candidate explicitly requires independent semantic-fidelity review and separate Owner SHA-256 approval before replacement, followed by STOP. This adds no cutover authority to the current candidate-only instruction. | PENDING |
| Separately authorized provider evaluation / visualizations exclusion, L95-L100 | Candidate L89-L94; verbatim | New owner authorization remains mandatory; visualizations remains outside the critical path and this slice. | PENDING |
| Claim Ceiling, L101-L124 | Candidate L95-L117; heading and all seven ceilings verbatim | Each ceiling, qualifier and correction remains directly present. Only the final separator blank line is omitted; item-level mapping follows. | PENDING |
| Canonical Checkpoint Projections historical cutover narrative, L125-L135 | Archived only | Exact predecessor identities and recoverability narrative remain at Archive L125-L134, including older durable source pointers. No claim is made that the historical twelve-projection review was repeated here. Removing a projection marker removes its local memory_record idempotency anchor; a later identical replay can re-append it. | PENDING |
| Draft #351 projection, L136 | Removed after canonical daily recovery check | Exact projection payload and marker remain at Archive L136. Its full identity is independently present in memory/2026-11-23.md L17-L28; daily identity parser returned True. Review/history limitations and replay consequences are recorded below. | PENDING |

This map covers the entire 136-line predecessor. It distinguishes retained rules from archived episodic narrative; it does not silently discard unresolved authority.

## Seven Claim Ceiling rules: verbatim correspondence

| Ceiling | Archive lines | Candidate lines | Preserved restriction | Independent review |
| --- | --- | --- | --- | --- |
| 1 | L103-L105 | L97-L99 | No Gate 3 success, treatment/Skill effect, feasibility, Gate 2 integrity, implementation readiness or counted evidence. | PENDING |
| 2 | L106-L110 | L100-L104 | Unreachable native boundary; both flags False; twice-corrected distinction between self-created objects and borrowed base/ancestors. | PENDING |
| 3 | L111-L113 | L105-L107 | Design/review is not runtime evidence; no committed tranche claimed to execute, spawn, compile or import historical code. | PENDING |
| 4 | L114-L116 | L108-L110 | M3-b-1 80b2a74c mutation declaration remains non-rerunnable; fa10dda8 and later have no mutation evidence. | PENDING |
| 5 | L117-L118 | L111-L112 | No real-consumer adoption/update or report-only enforcement claim. | PENDING |
| 6 | L119-L122 | L113-L116 | Canonical enforce wrapper incomplete; no inference about Owner Bash/Python availability and no full-repository enforce-gate PASS. | PENDING |
| 7 | L123 | L117 | Workspace remains NOT CLEAN; no clean-workspace claim. | PENDING |

The four protected sections were compared as exact normalized text blocks with only separator blanks excluded. The seven bullet bodies were additionally checked individually and in order. No wording in those bodies was shortened.

## Seven Authority Index entries: traceability proof

The table's blob and digest references resolve through the archived original row, not through an invented replacement authority. Local Git object identity checks are provenance checks, not fresh owner attestations or maturity upgrades.

| Surface | Exact archive / candidate lines | Identity check and preserved recorded status | Independent review |
| --- | --- | --- | --- |
| Gate 3 funding authority | Archive L51; Candidate L47 | Commit 01e8c0b4f61b1288d80495230f5fb4d8aeed525a resolves to a commit and contains PLAN blob d4ed290ad17b8e5e7aec83c92f2e1498ed170a63. The raw blob SHA-256 matches Archive L51. Recorded status remains committed owner-decision section. Archive L51 retains the exact section title/digest, PIN-before-first-authoritative-mapping-release rule and no-retrospective-repair condition. | PENDING |
| Release-Order design | Archive L52; Candidate L48 | Commit d3b28213513589cfec8b95edd4965cd631052449 contains blob 58dadf63f69fefd153c1cbecb3e5df6fc1c83bfd at docs/governance/gate3-release-order-authority-design-candidate-20260830.md; raw SHA-256 matches Archive L52. Remains a reviewed design candidate, not feasibility, implementation authority or runtime proof. Candidate L16-L18 and L105-L107 retain those direct ceilings. | PENDING |
| Authority source-set closure | Archive L53, L59-L61; Candidate L49, L55-L57 | Commit 0269ce9e858c161c2d425aaa442529453defecf9 contains blob 0fedd18031ba1c8b6d2ecdd28224acd1fd77c625 at docs/governance/gate3-authority-source-set-closure-candidate-20260830.md; raw SHA-256 matches Archive L53. ADOPTED is the archived owner-decision status; candidate labeling and UNAVAILABLE_HISTORICAL_REFERENT remain explicit. | PENDING |
| Closed-source predicate register | Archive L54, L59-L61; Candidate L50, L55-L57 | Commit 6501d90f52c5e372fc049da34b3210fd01245fb4 contains blob cb7b9ce25d7776b5924450a81388e7219511d871 at docs/governance/gate3-closed-source-predicate-register-candidate-20260830.md; raw SHA-256 matches Archive L54. Its parent is exactly 0269ce9e858c161c2d425aaa442529453defecf9. ADOPTED and the 63-predicate split, 43 historical / 20 prospective, remain in the exact referenced row. | PENDING |
| rev9 rejected bytes | Archive L55; Candidate L51 | Archive L55 retains exact worktree SHA-256 92004c3f59aa16dcc6152c1be61d83f7ee67e4f1be963b058d7f9e3acc481f7d. No committed blob is claimed or manufactured. CHANGES_REQUESTED / HIGH remains explicit; Candidate L12-L15 also retains permanent rejection/no rev10. Archive L55 retains the limitation that current-state evidence cannot prove absence of earlier authoritative publication. The historical worktree bytes were not revalidated. | PENDING |
| Memory-cutover fidelity finding | Archive L56; Candidate L52 | Commit 885c5de79d414b08136f5a06ed0cba77c81d30c2 resolves locally and records the fidelity failure. Irreversible state, effective ceilings, exact references/status and the historical one-final-candidate boundary are retained. Candidate L32-L39 retains the spent attempt and new-authorization/STOP conditions; this pointer cannot renew an old grant. | PENDING |
| Unsafe-janitor finding and containment | Archive L57; Candidate L53 | Finding commit d84ebf8e9ee990bcc340a327d5e44f30706b7bd9 and fix commit 6ca4800bf6259ffede7ee02e53a37d958a0e6a92 both resolve locally. Destructive compression remains prohibited. Archive L57 retains that containment does not reduce pressure; unchanged active memory is still WARNING. | PENDING |

The four full-blob SHA-256 checks matched these archived values:

| Archive row | Recomputed raw Git blob SHA-256 |
| --- | --- |
| L51 | 315f7f61ec5f06fbf31675b55de98fe3464ff256c2daa8d3fb1b987be22d5f53 |
| L52 | e010197852f491824c4cfd8ecad93821f661b67a353690e356522c4c6dd6b9bd |
| L53 | dec86ce98bc6ab1c090c879c46649f7b28891cc51b6cf6d32fb14ad25a460614 |
| L54 | 8e67c8740e9ec0036b9bae391b2f44decf0889b432d8b790112b1f96e2a07f2b |

Reproduction used git cat-file -t COMMIT, git ls-tree -r COMMIT, git cat-file blob BLOB and hashlib.sha256(raw_blob_bytes). The funding subsection SHA-256 is preserved as a recorded reference at Archive L51; its original subsection-selection convention is not established here, and a subsection-digest verification is not claimed. Whole-PLAN blob verification is separate and matched. Neither local object existence nor a matching hash proves the original human decision.

## Removed projection recovery and idempotency

Removed identity:

    41e7196cb1a50cc6f46fb635c80c4aa54653352d3241f59e262c81a7151f6667

- Archive L136 preserves the exact active-task-summary payload and marker.
- memory/2026-11-23.md L17-L28 is an existing canonical daily record written by governance_tools.memory_record. L21-L22 binds commit 0dccebe3fcfd5810f9b8611e3a7715bbe8a7d71b; L25 preserves the original evidence pointer; L26 preserves the Draft #351 re-review continuation; L28 preserves the exact identity.
- memory_record.daily_memory_contains_record_identity() returned True. The unchanged helper's evaluate() classified Archive L136 as REMOVED - RECOVERABLE using that daily record.
- memory/04_review_log.md and memory/archive/active_task_projection_history.md were searched for the full identity/payload. Neither contains this same identity; no review-log or history recovery is claimed. History L42 contains predecessor identity 359afaef4534262cbf5922e88a4ca1e090d757d6d19f85466a7dcb344fa293ee and cannot substitute for this one.
- The archived source has no supersession relation endpoint requiring this projection to stay. No writer-owned marker or supersession relation was invented in the candidate.
- Removing the active projection removes its local idempotency anchor. A later identical writer replay may re-append it. The candidate and this matrix do not change writer semantics.
- This is recovery of a historical projection, not a live assertion that PR #351 is still Draft or still awaits review. No remote PR state was requalified for this task.

## Validation, hard boundaries and remaining gates

- The exact archive and existing manifest remain unchanged. The formal active file remains byte-equal to the archive, with empty working-tree and staged diffs for memory/01_active_task.md.
- governance_tools/active_task_cutover.py remains unchanged at raw SHA-256 709e83c2ccd065e3815ee4a60a188c8757f3edc85ffe3193fb03420d4514787f. governance_tools/memory_janitor.py remains unchanged at raw SHA-256 8375a2fee9d8786894db0072aacce9c20a00e92c770c5cb518f55843ffa57dd3. No validator or schema was modified.
- Only the candidate and this manual matrix were authored. The two prepared untracked inputs were inspected without editing. No commit, push, staging, cutover, rollback or session-end closeout was performed.
- The candidate and matrix are owner-requested review artifacts, not new session-derived daily/review/projection records. No canonical writer was used to append a record. The explicitly forbidden active-task milestone/review summary was not written.
- The read-only active_task_cutover.evaluate() returned FAIL: 115 predecessor nonblank items; 87 verbatim, 1 removed/recoverable projection, 12 added/unreviewed lines, 27 unresolved predecessor lines. The unresolved archive lines are 1, 2, 6-9, 49, 51-57, 65, 76-77, 94, 125, 127-134. They correspond to the explicit archival/condensation map above. This expected strict-verifier result is not waived or represented as PASS.
- The helper's mutating verify command was not run; it would produce its separate mechanical matrix and update the manifest. The manual semantic matrix does not substitute for or falsify that mechanical result. Formal replacement remains blocked under the unchanged automated path. Any later manual path requires separate review and Owner authorization; no future path is approved here.
- python -m governance_tools.memory_workflow --check --repo . --run-guard returned exit 0 with guard_ran=True and completion_claim_allowed=True, meaning no current memory-completion blocker was reported. This is not semantic-fidelity approval or proof that historical memory debt is resolved. The candidate-stage guard reported active_non_canonical_writer=0, current_diff_b0_blocker_count=0 and repo_state_b0_blocker_count=0.
- Existing guard warnings remain disclosed: missing_canonical_memory=19, non_canonical_writer=86, test_evidence_artifact_metadata_invalid=25, test_evidence_artifact_metadata_missing=34, test_evidence_exit_code_contradicts_claim=3; background unbound_memory=349, test_evidence_provenance_not_found=579, test_evidence_linked_commit_mismatch=33. They are not repaired or converted into clean-memory claims by this task.
- No runtime tests were needed for these two documentation artifacts. Scoped checks are content equality, seven-row/ceiling mapping, raw hash identity, MemoryJanitor measurement, memory workflow guard and Git diff inspection.

Review handoff: inspect the exact candidate hash above, check every PENDING row, and issue an independent semantic-fidelity disposition. Owner SHA-256 authorization for formal replacement is absent. A blocking semantic-fidelity finding means STOP under the retained boundary; it does not authorize another same-method candidate loop.

## Retained response envelope

This evidence envelope is associated with this N5 candidate-preparation validation event. It is not a canonical session-derived memory entry or a session-end receipt.

~~~yaml
mode: VALIDATION
mode_source: validation_command
task: N5 Plan A active-task replacement candidate and manual preservation matrix
task_authority: user_request
scope:
  - memory/archive/active_task_20261128_102606_replacement_candidate.md
  - memory/archive/active_task_20261128_102606_semantic_preservation_matrix.md
done:
  - Local candidate and manual traceability matrix prepared for independent review.
  - Seven ceilings and the three other protected sections retained verbatim.
  - Candidate measured at 117 lines and 6967 chars, SAFE.
  - Formal active memory and prepared archive/manifest preserved unchanged.
claim_ceiling:
  - Local review artifacts, measured equality and provenance/recoverability only.
  - No overall committed delivery or independent semantic approval.
not_claimed:
  - Independent semantic-fidelity PASS or Owner SHA-256 replacement authorization.
  - Automated verifier PASS, formal cutover or resolved active-memory pressure.
  - New authority, maturity, Gate 3, consumer-adoption or runtime qualification.
  - Canonical daily/review record, session closeout, commit, push, merge or clean workspace.
evidence_refs:
  - artifact: memory/archive/active_task_20261128_102606_replacement_candidate.md
    result: PASS
  - artifact: memory/archive/active_task_20261128_102606.md
    result: PASS
  - command: governance_tools.memory_janitor.MemoryJanitor.check_hot_memory_status on candidate
    result: PASS
  - command: governance_tools.active_task_cutover.evaluate on frozen archive and candidate
    result: FAIL
  - command: python -m governance_tools.memory_workflow --check --repo . --run-guard
    result: PASS
  - command: git diff --exit-code -- memory/01_active_task.md
    result: PASS
  - command: git diff --cached --exit-code -- memory/01_active_task.md
    result: PASS
risk:
  - Manual condensations require independent review; strict automated cutover remains blocked.
  - Workspace deliberately retains four in-scope untracked review artifacts; no commit/push authorized.
  - Existing guard warnings and historical claim limitations remain unresolved.
next_action: Submit candidate SHA-256 32cac60cce9399a2ca1b8c4984e25f0ef205789f3b567b6b172a862a5a83f402 for independent semantic-fidelity review; formal replacement remains unauthorized.
~~~
