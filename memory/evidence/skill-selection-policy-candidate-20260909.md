# Advisory Skill Selection Policy — Candidate

Status: CANDIDATE. Not owner-adopted; not a runtime policy or deployment.
Scope: the twelve non-deprecated repository Skill entries reviewed in this session.
Authority: none beyond the user's authorization to draft and independently review this candidate.

## Purpose

Support task-specific Skill selection without treating more Skills, more artifacts,
or more evaluation as inherently better. Twelve entries have selection dispositions
or explicit limitations; this is not twelve effectiveness validations.

## Selection principles

1. Keep selection-review status separate from effectiveness evidence.
2. Choose the minimum set of Skills covering distinct, currently unmet task needs.
   Consider guidance already supplied by applicable repository rules and the task.
   Multiple matching descriptions do not require cumulative loading.
3. A Skill supplies guidance, not execution authorization, acceptance evidence,
   merge authority, or a replacement for applicable repository contracts.
4. Repository membership, language, phase, task size, or session ending alone
   should not justify stacking Skills. Explicit user requests and applicable
   governing instructions remain in force; this candidate does not override them.
5. A measurement gap does not automatically authorize evaluator implementation.
   Further work needs a concrete unresolved question capable of changing selection.
6. This advisory candidate neither overrides nor changes existing routing or agent
   declarations. Record disagreement as implementation drift, not compliance.
   Recommendation, declaration, actual content loading, and outcome are distinct.

## Evidence classes

- Outcome evidence: python and human-readable-cli have bounded fresh A/B evidence.
  Python showed no incremental value in one interval-merge task, with a worse
  treatment regression result. This does not establish general harm or recommend
  against Python Skill use. Human-readable-cli showed local message-quality gains,
  not general decision gains, production CLI safety, or measured human usability.
- Routing/responsibility evidence: nine other entries have static role, overlap,
  input/output or consumer-path evidence. This is not observed Agent improvement.
- Measurement limitation: code-style remains UNASSESSED-DEFERRED; maintainability
  benefit cannot be decided using the existing patch evaluation evidence.

No entry currently has sufficient reviewed evidence here to justify global DEFAULT.
This is an evidence limit, not an instruction to disable existing configuration.

## Per-Skill candidate selection

| Skill | Selection disposition | Consider when | Limitation |
| --- | --- | --- | --- |
| python | OPTIONAL | Task-specific Python guidance is needed, or explicitly requested | Insufficient evidence for DEFAULT; not evidence to avoid use |
| code-style | NO_CHANGE / UNASSESSED-DEFERRED | No new trigger proposed by this review | Neither default promotion nor retirement supported |
| human-readable-cli | OPTIONAL / POSITIVE_SIGNAL | Human-facing CLI communication needs guidance | Message-level evidence only |
| governance-runtime | ROUTING_CANDIDATE | Facts indicate governance enforcement, evidence, policy, lifecycle or audit impact | Actual activation UNKNOWN; outcome UNASSESSED |
| tech-spec | ON_DEMAND | Unresolved scope, behavior, boundary or acceptance needs a reviewable decision artifact | Complexity alone is insufficient; do not rewrite a complete plan |
| precommit | ROUTING_CANDIDATE / ON_DEMAND | Runtime-governance gate preparation, diagnosis or claim interpretation is needed | Not changed-file-based test selection |
| runtime-smoke | ROUTING_CANDIDATE / ON_DEMAND | Runtime entry selection or contract/event/wrapper fault isolation is needed | No new readiness standard |
| reviewer-handoff | ROUTING_CANDIDATE / ON_DEMAND | An identified reviewer needs a multi-source governance evidence entrypoint | Do not duplicate sufficient PR/report material merely for presentation |
| pr-review-merge-gate | ON_DEMAND | Explicitly authorized PR review with conditional merge needs orchestration | Every applicable authority predicate remains required; not review-only |
| wrap-up | ON_DEMAND | An authorized canonical closeout needs a new or updated candidate input | Candidate valid is not task complete; no automatic repeated artifacts |
| external-onboarding | ROUTING_CANDIDATE / ON_DEMAND | First external integration or a concrete cross-repo onboarding diagnosis is needed | Tool/contract owns readiness; Skill has a documented semantics caveat |
| domain-contract-authoring | ON_DEMAND | Contract framework structure or authoring integration has a concrete gap | Not a domain-correctness evaluator or authority-design method |

These are consideration criteria, not executable loading rules or proof that an
independent Skill must be retained. An existing Skill may be reused without
recreating its artifacts; generating artifacts requires an actual task need.

## Known version bounds

- Main workspace branch: feat/gate3-historical-materialization, HEAD
  09248cb4e7ac49f7e78bc55e4db45668264bc9e4; existing unrelated dirty state excluded.
- Comparison integration HEAD: 3be206957b2964a01aaf118a8358b4439cbbb376.
- Eleven shared Skill main files compare equal after CRLF-to-LF normalization,
  but not as exact raw bytes. This is not full references/baseline reconciliation.
- pr-review-merge-gate was reviewed only in the integration checkout; it is absent
  from the main workspace. Its conclusions must not be silently applied elsewhere.
- Prior A/B conclusions remain bound to their evaluated inputs/rubrics and are not
  requalified for a new target version by this document.

## Known implementation drift and limits

- rule_pack_suggester seeds code-style and governance-runtime unconditionally and
  adds python based on language detection. This does not implement unmet-need routing.
- Python and CLI agent declarations contain fixed Skill lists. Changing the
  suggester alone would not establish that these declarations or activation changed.
- Reviewed runtime consumers forward/display suggestions; no direct automatic
  governance-runtime content-loading chain was established. External client
  behavior remains unknown. No token savings or outcome improvement is claimed.
- external-onboarding guidance says missing hooks alone can fail readiness, while
  the inspected readiness predicate excludes hooks_ready. Use the actual contract
  and tool result; this document does not repair that discrepancy.

## Review basis

The session's accepted selection synthesis and bounded source reviews are the
basis, not new experiments. Relevant source anchors include:

- governance_tools/rule_pack_suggester.py:461 and :578 — suggestion seed/advisory limit.
- .github/agents/python-agent.agent.md:10 and cli-agent.agent.md:10 — declarations.
- .agents/skills/*/SKILL.md and .github/skills/*/skill.md — reviewed Skill surfaces.
- governance_tools/external_repo_readiness.py:289 — inspected readiness predicate.
- memory/evidence/post-gate3-pr-delivery-20260908/governance-runtime-routing-review.json.
- memory/evidence/post-gate3-pr-delivery-20260908/human-readable-cli-scenarios/fresh-ab-20260909/terminal.json.

These anchors are review provenance, not a declaration that every input is frozen
or that current line numbers persist across target versions.

## Non-goals and adoption boundary

- No suggester, agent declaration, Skill description, loader or routing changes.
- No automatic Skill activation claim, cross-machine qualification or cost claim.
- No authorization for execution, commit, push, merge, onboarding or closeout.
- No claim that twelve Skills are effectiveness-validated; no historical rescoring.
- No new schema, gate, benchmark, evaluator, or automatic Slice 2.
- No retirement, deployment or canonical authority conferred by this candidate.

Independent review may establish ADOPTABLE only. Owner adoption remains separate.
Any later deployment requires an authorized target branch/version, reconciliation
of affected references and baseline rules, explicit affected entrypoints, and
scope-matched validation. Unknowns are revisited only when they block that decision.
