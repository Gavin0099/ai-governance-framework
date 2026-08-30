# Gate 3 Authority Source-Set Closure Candidate

Status: **CANDIDATE / NOT ADOPTED / SOURCE GRAPH ONLY**

Date: 2026-08-30

This artifact answers one bounded question:

> Which finite, revision-bound source graph supplies the historical Gate 2
> experiment authority inherited by Gate 3, and which separately committed
> prospective authority governs future Gate 3 work?

It does **not** extract validity predicates, amend the predicate register, adopt
an evidence standard, authorize a provider, or authorize implementation. A
commit of these bytes would establish only a durable candidate identity.

## 1. Closure rule

A node is in the source set only when at least one of the following is true:

1. the final pre-run authority snapshot names it as protocol authority;
2. an included authority node explicitly carries forward, corrects, supersedes,
   or incorporates it;
3. it is an exact-set manifest or append-only promotion record required to
   identify the bytes adopted by an included authority node; or
4. it is a separately committed prospective owner authority for future Gate 3.

Every included node is bound to a commit, blob OID, SHA-256, path, and semantic
anchor. A reference to current worktree line numbers is not an identity.

References that supply treatment bytes, runtime behavior, tests, verification
evidence, or background rationale terminate as classified leaves. They do not
become authority merely because an authority document pins them.

The graph is closed only when every normative inheritance or supersession edge
from an included node resolves to another included node or to a revision-bound
terminal leaf. Any unresolved normative edge makes the result
`SOURCE_SET_INCOMPLETE`.

## 2. Historical cutoff and roots

### 2.1 Final pre-run historical root

The final committed protocol snapshot before the formal Gate 2 run is:

- commit: `c8a9bd059fea2cbda85d6c14b8d493729ebd465d`
- commit time: `2026-07-28T11:55:11+08:00`
- subject: `feat(gate2): use Haiku for blind scorers`
- root path:
  `artifacts/experiments/prepush-bugfix-20260724/gate2-preflight-manifest-20260724.md`
- blob: `1a7d80aab465e5c8aafd7c6f16c899794c5336a6`
- SHA-256:
  `6c91b91b4d904eebf5904d6951ace7d81d26e6d31d03ac4ed84587cfd33b13a2`
- identity: 8,868 bytes, 151 LF, 0 CR
- anchors: `Status: answer-safe setup only`, `Frozen policy (values stamped at
  dispatch)`, `Scorer anonymization handoff — executable contract`, `Terminal
  timeout outcome — new runs only`, and `Remaining — resource-gated`.

The formal evidence directory is named
`gate2-formal-20260728-115533`; its evidence was committed later in
`1d12f6d19b865ad5030049d512201a2cfd326a43`. The
`c8a9bd059fea2cbda85d6c14b8d493729ebd465d` snapshot is the
last protocol-changing commit before that formal-run timestamp. The earlier
`5f0e3570658f200b0de4ee7e3d4ed9ba94e152cc` promotion commit remains an included adoption event, but it is not
the final pre-run root.

### 2.2 Prospective Gate 3 root

Future Gate 3 work is separately governed by the committed PLAN owner decision:

- commit: `01e8c0b4f61b1288d80495230f5fb4d8aeed525a`
- path: `PLAN.md`
- blob: `d4ed290ad17b8e5e7aec83c92f2e1498ed170a63`
- full-file SHA-256:
  `315f7f61ec5f06fbf31675b55de98fe3464ff256c2daa8d3fb1b987be22d5f53`
- anchor: `### Gate 3 first-Skill funding gate — principal before engineering`
- anchored section SHA-256:
  `7974b94ce78e91ee7b2d047208c22caf8ddbee52e93c34ae9d635b980477c168`
- anchored section identity: 2,254 bytes, 36 LF

This prospective root does not retroactively rewrite the historical Gate 2
source graph.

The first paragraph of this PLAN section directly reconciles an older natural
pilot decision. That inherited decision is therefore an included prospective
source node, not an excluded Route C artifact:

- source commit:
  `c14d19cdf81c3fa7707b27fd01f161dd2852b6a5`
- path: `memory/2026-07-17.md`
- blob: `29c6a6ed15ab554289ba7688c2a4d5c80d11f834`
- full-file SHA-256:
  `348db9d6af6153b343e812f298b1275dba94f73548a6bdff18e2f6bec7bf4b9e`
- anchor: the owner-ratified evidence-first Engineering Skill pilot decision
  beginning `Owner ratified the evidence-first Engineering Skill pilot
  decision` (frozen lines 19–25 at that commit).

This memory node (`P1`) proves the owner ratified a dormant natural pilot and
an eight-step card. The original card's standalone exact bytes are not present
in the bounded repository source chain. The current prospective PLAN node
(`P0`) expressly reconciles the active meaning as program Section 3 steps 1–7
and 9 and states that it is not claiming the later program caused the 2026-07-17
record. Therefore the unavailable original card is an
`UNAVAILABLE_HISTORICAL_REFERENT`, while `P0` supplies the current prospective
normative reconciliation. It must not be reconstructed from an unadopted Route
C candidate.

`P0` also names the later program method and repeats the program's Gate 3
minimum of three separately originated natural bugs across two consumer
repositories. At prospective commit
`01e8c0b4f61b1288d80495230f5fb4d8aeed525a`, the program is still exactly
`H1` (the same blob and SHA-256). Therefore `P0`'s `accepted repeat rules`
reference is bounded to `H1` Section 8's rules: separate preregistration under
the same protocol, non-duplicated root-cause families, and execution not limited
to one agent session. It does **not** import the more detailed two-/three-pair
scheme from the unsigned Gate 3 preregistration candidate.

## 3. Historical documentary source registry

All nodes in this table are read at the frozen
`c8a9bd059fea2cbda85d6c14b8d493729ebd465d` tree unless a row
states a different adoption commit.

| ID | Role | Path / exact identity | Stable semantic anchor |
|---|---|---|---|
| `H0` | Final pre-run consolidating root | `gate2-preflight-manifest-20260724.md`; blob `1a7d80aab465e5c8aafd7c6f16c899794c5336a6`; SHA-256 `6c91b91b4d904eebf5904d6951ace7d81d26e6d31d03ac4ed84587cfd33b13a2` | `Status: answer-safe setup only`; protocol-authority paragraph |
| `H1` | Program-level staged-gate and validity source | `docs/governance/evidence-backed-engineering-skill-program-2026-07-24.md`; blob `9a6f8fa820498d9316ffbe9c52d92774d83c4e1a`; SHA-256 `e980face7fe67c5813c3d67b65ba864eb4c50dedb0cc49d07f75e6091d5b90ec` | `Four-Layer Responsibility`; `Staged Decision Gates`; `Stop Conditions` |
| `H2` | Gate 0 admissibility source for the selected natural bug | `docs/status/gate0-prepush-outgoing-ref-bug-2026-07-24.md`; blob `d87308909253dc26aae4a563314eaa5c69dbdec4`; SHA-256 `18ca24f5767cbeebaffe06d1c925f29d3816c65bf180c513e68a3907278c0f2f` | `Gate 0 checklist (Section 8)`; `What Gate 0 does NOT authorize` |
| `H3` | Original outgoing-ref preregistration | `docs/governance/gate1-prereg-prepush-outgoing-ref-20260724.md`; blob `ef0559784adce3d8148b392e87b3e002a8180303`; SHA-256 `d7b78e2d98f10834902d9d9a362c590bba437f08c143cd0693493b0315ff2970` | header status and `Program reference`; carried values only where later amendments retain them |
| `H4` | Historical correction v1; source of explicitly carried values | `docs/governance/gate1-prereg-prepush-amendment-20260724.md`; blob `86356fb1e50754b1975cd3850a3e68e78ab52e8d`; SHA-256 `f619eed2c658e5802596bcc1fa8bee6d403c37c436a1236d561381ecfcadb746` | header carry-forward paragraph; Sections B–C |
| `H5` | Primary Gate 1 authority after v1 | `docs/governance/gate1-prereg-prepush-amendment-v2-20260724.md`; blob `897f548b85b24a52c50ed32e40f508bdfdc015e7`; SHA-256 `eb1a7747e51bd01566ee04d17123cab5262452961f53631d8769fe392f8a9c64` | `All other frozen values carry over from v1 unchanged`; owner re-sign; resource preflight |
| `H6` | Validator-packet plus sanitized-export/LF correction and promotion | `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md`; blob `b1bd0b349fa38084cdae44012aba57f374ffb465`; SHA-256 `376fd1f4fc9a1915e2240b6ba4d97d1163158f711e60948c7e20a175d588bdd3` | corrected export procedure; mandatory LF-only worktree check; immutable image ID and Ruff `--no-cache` operational fixes; `Old → new map`; `Owner re-sign`; canonical promotion |
| `H7` | Signed scorer-handoff v3 decision bytes | `docs/governance/gate1-prereg-prepush-amendment-v4-20260726.md`; blob `1e7d09ea8510a3cd58cf826b3f070a49666ef9db`; SHA-256 `28d074cdc1bca4eb5bf60b4d72dd983a7c836fb8297a8346479b352978f976ba` | `Exact candidate set`; `Owner decisions required after review`; `Promotion and execution remain separate` |
| `H8` | Exact signed scorer-handoff v3 set | `artifacts/experiments/prepush-bugfix-20260724/candidate/scorer-handoff-v3-candidate-manifest.json`; blob `ef272c4f153ff539d3916e2db8432e99663f403a`; SHA-256 `7104b2e03da9e61c8191430fd337b7b73effb41eb787b55e3364a21d1ac2147c` | schema `gate2-scorer-handoff-v3-candidate-set.v1`; exact `files` set |
| `H9` | Append-only scorer-handoff promotion evidence | `artifacts/evidence/test-results/receipt-gate2-scorer-handoff-v3-promotion-20260727.json`; blob `2ba86a73a9e84492745fd6d009aab3e223880b3c`; SHA-256 `181c1cd74252ee1a7ace723010e6850a7605c23f83688add4bb3288fd6cb8ec9` | `purpose`; `promotion_method`; `signed_bytes_unchanged` |
| `H10` | New-run-only timeout, recovery-order, and scorer-model amendment | `docs/governance/gate2-timeout-outcome-amendment-v1-20260728.md`; blob `43b755c9fa75228222749bc838b5b3b29f297485`; SHA-256 `b4a20122ebb8ee8d3489246d75da9386df9d2f805ff8cff26bf0bb23c6f629db` | owner authorization; preserved producer model/budget/treatment; normal/timeout terminal outcomes; failure paths; `Observed recovery-order defect correction`; `Scorer quota-cost correction` |
| `H11` | Exact timeout amendment set | `artifacts/experiments/prepush-bugfix-20260724/gate2-timeout-outcome-amendment-v1-manifest.json`; blob `1e961f06a47e34726953cb03c357939576a4734f`; SHA-256 `404c40d81d2cde0ee044270c9811e063cb20c80cb8567b99f2f11858f8b5241c` | schema `gate2-timeout-amendment-set.v1`; authority `owner_authorized_new_run_only` |
| `H12` | Historical PLAN owner-decision/status surface at the cutoff; not the final timeout-set identity | `PLAN.md`; blob `a20a6082f51fa52d8973a49ae4d9155d153f1bc6`; full-file SHA-256 `811760dfb7466969ab99ee0156113f9af1f215ba834a0497e0c692d24a387f22` | `P3 - Engineering Skill Program, pre-push bug study`; anchored cutoff-section SHA-256 `46650a9d966bddd55d60b1d49eaff393f5b1c16a204bcaf1b3a97c161c6e4715` (7,440 bytes, 101 LF) |

The signed `H7` bytes still say candidate and not canonical. That is not a
dangling status conflict. The owner-selected append-only promotion left `H7`
and `H8` byte-stable and recorded canonical promotion in commit
`5f0e3570658f200b0de4ee7e3d4ed9ba94e152cc`, the later `H0` preflight root,
and `H9`. Canonical status derives from that later promotion edge, not from an
in-place edit of `H7`.

## 4. Normative inheritance and supersession edges

| Edge | From → to | Exact edge semantics | Resolution |
|---|---|---|---|
| `E1` | `H1 → H2` | The program requires Gate 0 admissibility; `H2` evaluates the selected bug under that gate. | Closed |
| `E2` | `H1 + H2 → H3` | The outgoing preregistration invokes the program freeze list and the Gate 0 admissibility record. | Closed |
| `E3` | `H3 → H4` | v1 narrows/corrects the task while retaining its own Sections B–C values for later carry-forward. | Closed |
| `E4` | `H4 → H5` | v2 supersedes v1 isolation, validator layout, and status; v2 Section C explicitly carries all other frozen v1 values unchanged. | Closed |
| `E5` | `H5 → H6` | v3 supersedes the two validator-packet rows and corrects the sanitized-baseline export by pinning `core.autocrlf=false` plus a mandatory LF-only worktree check. It also records the already-applied non-frozen immutable-image and Ruff `--no-cache` operational fixes. All other v2 dimensions remain authoritative. | Closed |
| `E6` | `H5 + H6 → H7 + H8` | v4 proposes a new exact scorer-handoff set while preserving producer treatments, arm order, budgets, validators, and scoring release gates. | Closed |
| `E7` | `H7 + H8 → H9 + H12 → H0` | The owner re-sign and append-only promotion supersede scorer-handoff v2 only; historical PLAN, the receipt, and `H0` record the promoted exact set. | Closed |
| `E8` | `H5 + H6 + H7/H8/H9 → H10 + H11 → H0` | The new-run amendment adds verified terminal-timeout semantics; corrects recovery so only intended retained state is accepted while the exposing run remains preserved and is never resumed; and owner-authorizes Sonnet producers with separate Haiku admission/formal scorers plus model-alias evidence. Producer model, budget, and treatment remain preserved; scorer alias is the explicit changed dimension. The final `404c40d81d2cde0ee044270c9811e063cb20c80cb8567b99f2f11858f8b5241c` set is closed by `H10`/`H11` and `H0`, not by historical PLAN. | Closed |
| `E9` | `H12 → H0` | Historical PLAN records the initial timeout owner/admission history but still names the older `dd2b97eb1a47796b5320d0581b299b5f123ab5b8416736690a6cf93d93bf09df` manifest. The later final pre-run root is the authority for the corrected `404c40d81d2cde0ee044270c9811e063cb20c80cb8567b99f2f11858f8b5241c` set. | Closed; stale projection is not used as final exact-set authority |
| `E10` | `H5 + H6 + H7/H8/H9 + H10/H11 + H12 → H0` | Final pre-run manifest consolidates the active protocol and explicitly assigns which earlier node remains authoritative for each dimension. | Closed |
| `E11` | `P1 → P0` | The 2026-07-17 committed memory preserves the owner-ratified dormant natural-pilot decision; the 2026-08-20 committed PLAN owner decision defines its current eight-step reconciliation to program Section 3. | Closed; original standalone card bytes unavailable and not reconstructed |
| `E12` | `H1 → P0` | The prospective PLAN imports the unchanged program's Section 3 method and Section 8 Gate 3 count/repeat rules; no unsigned paired-repeat candidate is imported. | Closed |
| `E13` | `P0 ↛ H0–H12 historical bytes` | The later committed Gate 3 PLAN section governs future funding/evidence work and imports only the explicit `H1 → P0` program rules; it does not retroactively rewrite historical Gate 2 bytes. | Closed as a non-rewrite boundary |

The phrases `separate explicit owner "start Gate 2"` and `pre-approved
improvement threshold` may still require downstream semantic disposition. They
are not missing source edges: their source locations are included in `H0`/`H5`
and `H1`, respectively. This candidate deliberately does not interpret them.

## 5. Revision-bound terminal leaves

These leaves are in the closed graph because an authority node pins their bytes
or roles. They are not independently elevated to documentary authority.

### 5.1 Historical protocol-input leaves at `c8a9bd059fea2cbda85d6c14b8d493729ebd465d`

| Class | Included leaves | Closure boundary |
|---|---|---|
| Baseline/isolation inputs | `sanitized-baseline-manifest-20260724.md`: blob `6b153ff606364dadde94da5f67e595c0dfc1e666`, SHA-256 `084c157c54aadb075069faa39b3ebbecffbaa5281bf56c9abcbd7f29b961246f`; `isolation-template-spec.md`: blob `ca884e0ad8816b1f890d21400eb12681fd594719`, SHA-256 `ad3610289123af6eeb0cdb3968d7e9c78a26d6ea9cbef2fbf122bd787e9587f0` | Normative input leaf; does not create a new owner-decision edge |
| Treatment packets | `arm-dispatch-packet.md`: blob `6a0a729e41c80f8411a93e1d619aba1f9db2b029`, SHA-256 `59ef5915bccf09eb6a5c7a344412d512415eb6e8fab0c83e7f122612a3b822a8`; `skill-packet-bugfix.md`: blob `a37320e37f587fc45f9fd5797d91bb9f2762ac71`, SHA-256 `f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14`; `governance-packet.md`: blob `91e4e646659d3b9e4c2a9f9099aefab6d5904e70`, SHA-256 `f6dfe7268851b59717405550c39502a76774165a1b35ee9c9e056506c79bdc28` | Exact treatment inputs pinned by `H0`/`H5` |
| Validator packets | `candidate/validator-pins-v2.md`: blob `112875e3ffdfbaa2f2e2109393a97ed0cce73665`, SHA-256 `877896c7672b1f47383e19ab00a38049344634c12c328a205a1651c6da4bf46d`; `candidate/validator-expectation-DESIGNER-ONLY-v2.md`: blob `f0d27488d901fe2fb86f859d3edf76365afdc334`, SHA-256 `61e1e52743e78ad9d38bd50e311978f5d49f513d617a48fd9a9b5a0901d02092` | Canonical packet leaves under `H6`. Superseded provenance: `validator-pins.md`, blob `2087a2be3703a98f56ff906bf8b6b09e51f0b7b3`, SHA-256 `6ea4b3226a3f54dce265ad27a67209b9d803b27d690cc4d899d20fff9a7f2d5f`; `validator-expectation-DESIGNER-ONLY.md`, blob `5e18e754930eb2d236dd3cc5563b76b1435d75e0`, SHA-256 `dcff3d2d0d3f02f4ef57283718c61b5fe890e54b109b90be05b68d7a25fb52c6` |
| Scorer contract | `candidate/scorer-handoff-contract-v3.json`: blob `5ec3079a26d51a083bd16f31a4393484104ab0f3`, SHA-256 `16bf661b5238c906e6e0b4d977bc7f6c9e279a8f20286b8a8b1362de7346e733` | Exact input leaf under `H8`; old `scorer-handoff-contract.json`: blob `193fbd4a4880463b0b3e595e2bd4d2a9975c4ea9`, SHA-256 `e8945c4b7eee256c96e6c7f21beef02f885b9f6c7caf6b2b65197088bcd5226a`, is superseded provenance |
| Receipt template | `gate2-producer-receipt-template.json`: blob `59dba1f1766f653b90bba42420ae53a5b01ce61e`, SHA-256 `72d8068b3e05feb98b111365e93fdee67307a1d5f6a69ae28c435eae609869a1` | Template leaf referenced by `H0`; it is not a receipt authority |

The full paths in this table are under
`artifacts/experiments/prepush-bugfix-20260724/` unless already absolute within
the repository. Future extraction must still read the revision-bound source or
manifest rather than substitute mutable worktree bytes.

### 5.2 Scorer-handoff exact-set leaves

`H8` binds its member bytes at the signed candidate snapshot rooted in
implementation commit `b596153b193e754a1a0e8c99ecb24c58413f451d` and later
promoted without editing those signed bytes. Its members are:

- `.gitattributes`: blob `3598419c61f39bdd779873f292f0692c14b162bd`,
  SHA-256 `e7c9c51b48aa4532365626bde90ab907cab7110cc1f02c9086fa1cc6e32cdd06`;
- `H7` and the v3 scorer contract;
- `redaction_runner.py`: blob `41060d91aa053168ea719e60106fec6db8c6c83d`,
  SHA-256 `d612f75e0851239fe164f9918fd13e55416f7fff9b1f337ad3f54460a91955d5`;
- `test_redaction_runner.py`: blob
  `fc5521e7c24931d97cf6b6603b58036c1e574e69`, SHA-256
  `ffe3ef3b674c7189d6b0f4414e0a91325d12c814fc3cd26bcb56c636a86398ec`;
- `scorer_packet_v2.py`: blob `fc0769af7994c3137d2a8de31b0b405da630c704`,
  SHA-256 `a96711338ed5b873660fde892cc32b0b28cd25deaa440c4f67b1571371bbb40e`;
- `scorer_handoff_v3.py`: blob `f9b1775450e669b71fbaf1bb9e47337f47de63ec`,
  SHA-256 `77360e8fa20a30e3c39e1efde0dfbde94a9952d391358e39b2e68c1b28cba06e`;
- `test_scorer_packet_v2.py`: blob
  `7435ad168842138f9ac3adfe171622472ce5d405`, SHA-256
  `724250f537201e3ac4aa173b41ba6a786c7846807e1f7577bbd9c10e561e5055`;
- `test_scorer_handoff_v3.py`: blob
  `24f9f785b89fe95af1e6ffb5dbdef1bb0d3517eb`, SHA-256
  `62354907241a1e8c9009f15de261a3260a06f49a91c09a59ad28107b20703fce`.

The runtime and test members are `IMPLEMENTATION_OR_TEST_LEAF`; the shipped
smoke members are `VERIFICATION_EVIDENCE_LEAF`. Their exact complete hashes and
byte counts are closed by `H8`. They are not recursively searched for new
governance requirements.

The `.gitattributes` bytes in this signed set differ from the later timeout-set
version. This is not an identity collision: each edge is bound to its own
revision and manifest. No current-worktree path is used as a substitute for
either historical byte sequence.

### 5.3 Timeout exact-set leaves

`H11`, at `c8a9bd059fea2cbda85d6c14b8d493729ebd465d`, binds:

- `.gitattributes`: blob `ab193f23364299ea8dd56ce4d7d67e82dd214554`,
  SHA-256 `39d90d82b706dc3a545ae505ff4e9a67ba32e576e7d9935b72a4954c9568a0a2`;
- `H10`;
- `gate2_formal_runner.py`: blob `b3db5eb2c02bcab52572eef5e93ba7e986398543`,
  SHA-256 `7ca53e9dffc5f3550a746831e51a9f2b4b1f5c3e450b802ac07975d23f8b03e8`;
- `gate2_terminal_outcome.py`: blob
  `69cb625cdf94cc72a10f4914de8675110dd93616`, SHA-256
  `a4349ea1c408e2a1879b14ad8ffcf18d0d91c78dad284bc34698f138d3241e11`;
- `test_gate2_formal_runner.py`: blob
  `b2c3f6f521e6e720549d46e608bddc1f4a93c055`, SHA-256
  `7b3645e1bfeb6d383093c2eaf58037d19b25638b1859565977ba4f4b923e4c97`;
- `test_gate2_terminal_outcome.py`: blob
  `ca400d0c31779897d22fffce76bf7dbd57d141e9`, SHA-256
  `85b366e38a76767389d522fe725441b5785637fb6a75c4431a1bfa6c105abf97`.

The code/test members are `IMPLEMENTATION_OR_TEST_LEAF`. Their exact complete
hashes and byte counts are carried by `H11`; they do not become predicate
sources.

## 6. Classified terminal references and exclusions

| Reference | Classification | Why traversal stops |
|---|---|---|
| Prior `codex-review-fast` blind rerun and its result | `BACKGROUND_EVIDENCE` | Program non-claim rationale, not inherited protocol authority |
| `memory/03_knowledge_base.md` layer-boundary pointer | `BACKGROUND_RATIONALE` | `H1` states its own layer rule; the memory link is corroboration, not the source of this experiment's frozen protocol |
| Runtime implementations, tests, smoke output, verification JSON, and resource-admission evidence | `IMPLEMENTATION_OR_EVIDENCE_LEAF` | They may prove conformance to a source but cannot add source predicates |
| Release-Order design commit `d3b28213513589cfec8b95edd4965cd631052449` / blob `58dadf63f69fefd153c1cbecb3e5df6fc1c83bfd` / SHA-256 `e010197852f491824c4cfd8ecad93821f661b67a353690e356522c4c6dd6b9bd` | `PROOF_MECHANISM_INPUT` | Reviewed mechanism candidate; not the origin of a validity predicate |
| Base audit commit `36f66c79338a4447103b94757ccf490d1663b7e8` / blob `bad17e7329cbef601333e5b95a5553b820e1cbd6` / SHA-256 `085a7576b17a374ef10da4b5d501a3a4bbed09bff66406c1087e38d927195a12` | `AUDIT_OUTPUT / NOT AUTHORITY` | Proposed classification artifact cannot define its own source universe |
| Unadopted amendment draft SHA-256 `4b3e2c997200b5b90ffaa7fb657af12aa897a04d18642cc76b2b58e8dc3cb026` | `AUDIT_OUTPUT / CHANGES_REQUESTED / NOT AUTHORITY` | Its newly exposed completeness question is input to this closure work, but the draft is not a source node |
| Unsigned Gate 3 preregistration candidates | `UNADOPTED_CANDIDATE` | No owner adoption; cannot enter the frozen source set |
| Unadopted Route C candidate | `SEPARATE_ROUTE_CANDIDATE / NOT AUTHORITY` | It does not become authority merely by discussing the natural pilot; the actual inherited owner-decision node is `P1`, and current normative reconciliation is `P0` |
| Original standalone natural-pilot eight-step card bytes | `UNAVAILABLE_HISTORICAL_REFERENT` | No exact artifact was located in the bounded chain; `P0` explicitly reconciles current meaning without claiming historical causation, so the bytes are not guessed or reconstructed |
| Current dirty worktree versions and naked line-number citations | `NON_IDENTITY` | Mutable state cannot replace commit + blob + SHA-256 + anchor binding |

If a later reverse audit finds a purported binding requirement whose only source
is one of these terminal classes, it must not silently reclassify the leaf. It
must raise a new source-set question for owner disposition.

## 7. Mechanical closure result

Closure was evaluated as follows:

1. start at historical root `H0`, prospective PLAN root `P0`, and follow `P0`'s
   direct reconciliation edge to `P1`;
2. follow every explicit authority, carry-forward, correction, supersession,
   amendment, adoption, and exact-set edge;
3. require an exact identity for each documentary node;
4. terminate treatment/runtime/evidence references only after classifying them;
5. verify that v4's unchanged candidate wording is resolved by the later
   append-only promotion rather than by an assumed in-place edit;
6. keep semantic ambiguities inside included sources for the later predicate
   audit instead of converting them into source-graph gaps; and
7. reject mutable worktree paths or historical line numbers as identities.

Result: **`SOURCE_SET_COMPLETE_CANDIDATE`**.

No dangling normative inheritance edge was found within the bounded direct
reference chain. This result is a candidate for independent review. It is not
owner adoption and is not permission to extract or freeze predicates.

## 8. Downstream use if later adopted

Only after owner adoption of an exact reviewed identity may a new predicate
audit:

1. extract historical predicates from `H0` through `H12` and the classified
   protocol-input leaves;
2. extract prospective predicates from the exact PLAN section;
3. preserve historical versus prospective applicability;
4. retain ambiguity instead of author-dispositioning it; and
5. reject a blocker whose alleged authority falls outside this closed set unless
   a later explicit owner decision amends the source set.

## 9. Claim ceiling

This candidate does not establish:

- that the source set has been independently reviewed or adopted;
- that every predicate has been extracted or correctly subsumed;
- that scorer blindness, first-release ordering, countability, or any other
  predicate is satisfied;
- that the Release-Order mechanism is provider-feasible;
- that the prior audit or its amendment is accepted;
- that Gate 3 is ready, complete, or implementation-authorized; or
- that any commit or push is authorized beyond the separately bounded candidate
  checkpoint.
