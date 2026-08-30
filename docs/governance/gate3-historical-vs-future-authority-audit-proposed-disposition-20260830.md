# Gate 3 Historical vs Future Authority Audit — Proposed Disposition

Date: 2026-08-30
Status: `PROPOSED DISPOSITION / OWNER ADOPTION REQUIRED`
Scope: authority-source classification only

## 1. Claim boundary

This report is commit-bound audit evidence. It does not create, amend, or freeze
Gate 2 or Gate 3 authority. Committing it establishes only an immutable identity
for the auditor's proposed classification.

The report does not authorize provider selection, implementation, network use,
rehearsal, counted execution, rev9 revision or resurrection, or memory updates.
It does not repair the historical Gate 2 evidence chain and does not establish
Gate 3 completion.

An owner must separately adopt this report's exact commit, blob OID, SHA-256,
and section anchor before its proposed blocker-admissibility rule can become a
durable authority freeze.

## 2. Audit question and method

The audit asks which predicates may legitimately block the current Gate 3 route
without laundering a later review finding into a pre-existing experiment
requirement.

The classification rule used for this proposal is:

1. A historical predicate must be present in immutable authority that predates
   the formal execution to which it is applied.
2. A prospective predicate may govern future work only from the point at which
   the owner authority that created it became immutable.
3. A reviewed design may supply a proof mechanism without becoming a source of
   new validity requirements.
4. An unsigned candidate, another cohort's authority, or a post-freeze hostile
   finding cannot become a blocker merely because it would improve security.
5. An ambiguity is `UNRESOLVED`; the auditor does not disposition it as new
   authority.

All existing authority sources were read-only during this audit. The only
authorized write is this proposed-disposition artifact.

## 3. Frozen source identities

### 3.1 Historical Gate 2 authority snapshot

Canonical promotion commit:

- commit: `5f0e3570658f200b0de4ee7e3d4ed9ba94e152cc`
- parent: `84077eed5f9080e9e1319044973a59ac9e9ac874`
- committed: `2026-07-27T17:22:19+08:00`
- subject: `chore(gate2): promote scorer-handoff v3 to canonical (preflight manifest only)`

Bound sources at that commit:

| Source and stable content anchor | Blob OID | SHA-256 |
| --- | --- | --- |
| `docs/governance/gate1-prereg-prepush-amendment-v2-20260724.md` — `## 8. Run procedure` / blinded-role requirements | `897f548b85b24a52c50ed32e40f508bdfdc015e7` | `eb1a7747e51bd01566ee04d17123cab5262452961f53631d8769fe392f8a9c64` |
| `docs/governance/gate1-prereg-prepush-amendment-v4-20260726.md` — scorer-handoff v3 authority binding | `1e7d09ea8510a3cd58cf826b3f070a49666ef9db` | `28d074cdc1bca4eb5bf60b4d72dd983a7c836fb8297a8346479b352978f976ba` |
| `artifacts/experiments/prepush-bugfix-20260724/gate2-preflight-manifest-20260724.md` — `## Promotion record` / `## Resource requirements` | `ff81689fc1163e1147faa5b0edb4c722ecb4c72b` | `908ab3613696908c9149f6644cc00f099c623501ed1324e36766cf139b99b1a3` |
| `artifacts/experiments/prepush-bugfix-20260724/candidate/scorer-handoff-contract-v3.json` — `acceptable_handoff`, `role_boundary`, `roles`, `release_gate` | `5ec3079a26d51a083bd16f31a4393484104ab0f3` | `16bf661b5238c906e6e0b4d977bc7f6c9e279a8f20286b8a8b1362de7346e733` |
| `artifacts/experiments/prepush-bugfix-20260724/candidate/scorer-handoff-v3-candidate-manifest.json` — exact scorer-handoff v3 set | `ef272c4f153ff539d3916e2db8432e99663f403a` | `7104b2e03da9e61c8191430fd337b7b73effb41eb787b55e3364a21d1ac2147c` |

This promotion predates the formal Gate 2 evidence commit
`1d12f6d19b865ad5030049d512201a2cfd326a43` of 2026-07-28. The later
correction retained the Gate 2 result as `NOT_ESTABLISHED`; this audit does not
change that result.

### 3.2 Prospective Gate 3 owner authority

Gate 3 funding authority:

- commit: `01e8c0b4f61b1288d80495230f5fb4d8aeed525a`
- parent: `6bd9e2c8fc3a653f4494493ce5f40144c568fbd9`
- `PLAN.md` blob: `d4ed290ad17b8e5e7aec83c92f2e1498ed170a63`
- `PLAN.md` SHA-256: `315f7f61ec5f06fbf31675b55de98fe3464ff256c2daa8d3fb1b987be22d5f53`
- section anchor: `### Gate 3 first-Skill funding gate — principal before engineering`
- section SHA-256: `7974b94ce78e91ee7b2d047208c22caf8ddbee52e93c34ae9d635b980477c168`

This section prospectively requires an independent external-pin authority,
append-only protected evidence, no retrospective pin, and a fail-closed STOP
when no qualifying principal or surface exists. It does not retroactively add a
new requirement to the July Gate 2 execution.

### 3.3 Reviewed proof-mechanism input

Release-Order design:

- commit: `d3b28213513589cfec8b95edd4965cd631052449`
- parent: `01e8c0b4f61b1288d80495230f5fb4d8aeed525a`
- path: `docs/governance/gate3-release-order-authority-design-candidate-20260830.md`
- blob: `58dadf63f69fefd153c1cbecb3e5df6fc1c83bfd`
- SHA-256: `e010197852f491824c4cfd8ecad93821f661b67a353690e356522c4c6dd6b9bd`
- section anchors: `## 2. Conditional sufficiency proposition` and
  `## 6. Claim ceiling and explicit non-claims`

This candidate is a conditional proof mechanism. It is not a source of new
experiment validity requirements and it does not establish provider feasibility.

## 4. Historical/future predicate register

| ID | Predicate | Authority time | Applicability | Proposed blocker classification | Existing proof status |
| --- | --- | --- | --- | --- | --- |
| `HIST-PRODUCER-01` | Answer-blind producer contexts are technically unable to read the answer/meta repository and are not the design author/session. | Pre-run, bound by `5f0e3570…` | Historical Gate 2; proposed carry-forward to future counted runs only if owner adopts this audit disposition. | Legitimate pre-existing information-isolation predicate. | Source-defined role and access procedure exists. Release-Order proves none of this predicate. |
| `HIST-BLIND-01` | Two isolated, arm-identity-blind scorers do not know the A/B/C/D mapping before scoring and receive no identity-bearing source. | Pre-run, bound by `5f0e3570…` | Historical Gate 2; proposed carry-forward to future counted runs only if owner adopts this audit disposition. | Legitimate pre-existing validity predicate; independent from release ordering. | Source-defined procedure exists. Historical process integrity remains `NOT_ESTABLISHED`. Release-Order proves none of this predicate. |
| `HIST-ORDER-01` | Both scorers submit scores and blinding-check guesses before mapping release. | Pre-run, bound by `5f0e3570…` | Historical Gate 2. | Legitimate pre-existing temporal validity predicate. | Historical run lacks an independently sufficient receipt chain; not repaired here. |
| `FUT-FIRST-RELEASE-01` | External pin precedes the first authoritative mapping release; retrospective pin fails closed. | Prospective, bound by `01e8c0b4…`. | Future Route B only. | Legitimate prospective validity predicate; cannot retroactively invalidate or repair Gate 2. | Release-Order candidate is conditionally sufficient only when its authority assumptions are satisfied. Provider feasibility is unproven. |
| `FUT-PRINCIPAL-01` | Pin controller is genuinely independent; surface is append-only/protected and retains protection evidence. | Prospective, bound by `01e8c0b4…`. | Future Route B only. | Legitimate prospective admission predicate. | No qualifying principal or provider has been established. |
| `OUTCOME-NATURAL-01` | Gate 3 completion still requires at least three independent natural bug sources across at least two consumer repositories. | Prospective owner PLAN. | Gate 3 terminal outcome. | Outcome/sufficiency criterion, not a per-run provider-feasibility predicate. | No completion claim is made. |

### 4.1 Required separation

The following two predicates are not interchangeable:

```text
(a) submission committed before authoritative mapping release
(b) scorer did not know mapping before scoring
```

Release-Order addresses the temporal and authoritative-publication side of
`(a)`. It expressly does not prove `(b)`, including private disclosure,
scorer-visible disclosure, coordinator ignorance, or scorer independence.

Therefore a provider that satisfies `FUT-FIRST-RELEASE-01` alone cannot be
treated as satisfying `HIST-BLIND-01`.

### 4.2 Frozen evidence surface proposed for owner adoption

For `HIST-PRODUCER-01` and `HIST-BLIND-01`, the pre-existing authority requires
the admitted process to retain the following source-defined properties:

- answer-blind producer contexts technically unable to read the answer/meta
  repository and separated from the design author/session;
- distinct arm-identity-blind scorer contexts;
- verified redacted and identity-free handoff material;
- no raw identity-bearing source or A/B/C/D mapping supplied to scorers before
  scoring;
- blinding-check guesses submitted as part of the scorer handoff.

These are procedural and information-isolation requirements. This audit does
not convert them into a cryptographic proof of subjective ignorance. Whether a
future route can produce evidence sufficient for this predicate remains
`UNRESOLVED` pending an owner-authorized feasibility slice.

For `FUT-FIRST-RELEASE-01`, the Release-Order mechanism is admissible only under
its own conditional proposition: historical empty state, monotonic continuity,
non-equivocation, same comparison unit and mapping digest, and an authority in
which the recorded release event is the authoritative publication event.

## 5. Inputs that may not become blockers by audit inference

### 5.1 Unsigned Gate 3 preregistration candidate

The following commit is in current HEAD ancestry but remains explicitly
`pending_independent_review_and_owner_signature`:

- commit: `c5be84dbb75f52567bd1b5c2a559126765cda3af`
- document blob: `e2a97aaa0e4df422cf218defd283ac964fb7cbc0`
- document SHA-256: `33f5844b5e62f08b4e58ebeca443dbf8e738c8d6a6832ed4a797824ac5dc6117`
- manifest blob: `1eb1b7509d9f704361271c83fb0fed51591e518a`
- manifest SHA-256: `51ac12190156eb0465d8e39a562eec0d31145bf41da5ddf8d5f1c6781a5a6801`

Disposition: `DESIGN INPUT / NOT CANONICAL BLOCKER AUTHORITY`.

### 5.2 Separate C1 cohort freeze

Commit `7109f3c24f9e38df161e4fd93c729820a151f0eb` (`feat(gate3): freeze C1
Gate 1 preregistration`) is not an ancestor of current HEAD and belongs to a
separate C1 route/cohort.

Disposition: `OUT OF CURRENT ROUTE / OWNER ROUTE-CONVERGENCE REQUIRED`.
It cannot silently supply blocker authority to this route.

### 5.3 Release-Order non-claims

The following are outside the reviewed Release-Order claim ceiling and cannot
become blockers merely by inference from that design:

- private, covert, scorer-visible, or out-of-band disclosure;
- global first publication outside the defined authoritative surface or unit;
- attempt count, discarded runs, covert runs, first append, bounded attempts,
  dispatch count, or global uniqueness;
- scorer blindness, scorer independence, or coordinator ignorance;
- Gate 2 repair, Gate 3 completion, provider feasibility, or implementation
  readiness.

### 5.4 rev9 residual design findings

Admission/profile error precedence, orphan-attempt disposition, and downstream
error overlap remain deferred design-integration findings. They are not
independently admissible experiment blockers unless an owner maps them to an
already frozen predicate. This report does not close or repair them.

## 6. Proposed blocker-admissibility freeze

If the owner adopts this artifact's exact identity, the proposed rule is:

1. A Gate 3 blocker must map to a row in `## 4. Historical/future predicate
   register` or to an earlier immutable authority identity explicitly retained
   by the owner adoption.
2. The mapping must preserve the row's historical/prospective applicability;
   prospective authority may not be applied retroactively.
3. A reviewed mechanism can fail to satisfy a frozen predicate, but cannot add
   a predicate.
4. A new hostile finding after adoption defaults to limitation, residual risk,
   or future hardening unless it demonstrates failure against an already frozen
   predicate.
5. Unsigned candidates and other-cohort authorities require a new owner decision
   before they may affect this route.
6. Ambiguous mappings remain `UNRESOLVED`; they do not become blockers by
   auditor discretion.

This section is a proposal until separately adopted. The commit containing this
file is evidence of the audit, not evidence of owner adoption.

## 7. Proposed owner decision boundary

The next owner decision may either:

- adopt this exact audit identity as the blocker-admissibility freeze;
- reject it; or
- request one bounded correction and a new exact identity.

No provider feasibility work should begin merely because this audit artifact is
committed. Provider work starts only after a separate owner adoption and a new,
bounded authorization.

## 8. Audit conclusion

Proposed disposition:

- scorer blindness is a legitimate, pre-run Gate 2 predicate and remains
  separate from release ordering;
- scorer submission before release is also a legitimate pre-run Gate 2
  predicate;
- `PIN < FIRST AUTHORITATIVE RELEASE` and independent-pin admission are
  prospective Gate 3 requirements fixed by the committed PLAN authority;
- the Release-Order candidate supplies only a conditional mechanism for the
  prospective ordering predicate;
- unsigned candidates, separate cohorts, design residuals, and post-freeze
  hardening do not automatically acquire blocker status.

Owner adoption remains required. No Gate 3 authority or claim ceiling changes
merely because this report exists or is committed.
