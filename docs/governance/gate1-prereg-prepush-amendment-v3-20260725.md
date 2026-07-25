# Gate 1 Correction Amendment v3 — Arm D expected signal + validator config binding

Status: **CORRECTION v3, RE-SIGNED, PROMOTED, AND PREFLIGHTED 2026-07-25
(Section E).** The two candidate packets (pins, expectation) are signed,
canonically promoted, and the post-sign image preflight found **no
regression** (`POST-SIGN-PREFLIGHT-20260725.md`). All Section E steps are
DONE. Gate 2 must still NOT start: resource preflight (4+2 isolated
contexts, out-of-band model channel) and
a separate owner start command remain outstanding regardless of this signature.
Amendment v2 stays authoritative for everything it covers; v3 corrects only the
Arm D validator treatment (expected signal, config binding) and the
sanitized-baseline export procedure. No hook, runtime, CI, schema, gate, or
enforcement changes.

Trigger: a review ran the pinned validators against the **real** frozen baseline
tree and found the frozen expectation false. This session independently
reproduced every claim inside the pinned runtime image, and found the two
findings are **coupled** plus two further defects.

## A. Measured reality (reproduced in image `sha256:e6df7283…`, linux/amd64)

Against the real sanitized baseline (tree `36c346fa…`), with LF-clean files:

| Validator | Command as documented | Measured result |
|---|---|---|
| ShellCheck 0.10.0 | `--shell=bash --severity=style scripts/hooks/pre-push` | **SC1090** (can't follow non-constant source) — **NOT null** |
| Ruff 0.6.9 | frozen config (`select E,F,W,I,B`, line-length 100) | **2 errors (I001, E501)** — **NOT null** |
| Ruff 0.6.9 | the documented command (defaults, no config) | All checks passed — null |
| mypy 1.11.2 | frozen flags | Success, no issues — null |

## B. Findings

**B1 [BLOCKING] The frozen "Expected signal: NULL" is false.**
`validator-expectation-DESIGNER-ONLY.md` states Arm D's validators produce no
finding. ShellCheck produces SC1090 and Ruff-with-frozen-config produces I001 +
E501. Arm D would therefore receive **real, non-empty validator feedback** — all
of it unrelated to the pre-push defect. The prediction "`D−C` ≈ 0 because the
validators are silent" was wrong in its mechanism: the validators are *noisy*,
not silent. That is a different treatment (distraction / unrelated-fix pressure)
and must be pre-registered honestly rather than discovered mid-run.

**B2 [BLOCKING] Config binding gap.** `validator-pins.md` freezes a ruff config
but its documented command never applies it. Run as written, ruff exits 0 (null);
run with the frozen config, it reports 2 errors. The pins file is
internally inconsistent, so "the frozen validator treatment" is currently
ambiguous.

**B3 [BLOCKING, coupled — found by this session] Line-ending contamination is
invisible to the frozen invariant.** On a `core.autocrlf=true` host the export
yields CRLF working files while `git add` normalizes the blobs, so the tree hash
still equals `36c346fa…` and the authoritative check **passes** — yet ShellCheck
then emits **80+ spurious `SC1017`** errors. Tree-hash verification alone does
not protect Arm D. Fixed in the sanitized-baseline manifest by pinning
`core.autocrlf=false` and adding a mandatory LF-only worktree check.

**B4 [WARNING, found by this session] ruff aborts when its cache target sits on a
read-only filesystem.** Precisely: not every `--read-only` run fails, only one
where `.ruff_cache` resolves onto the read-only mount (the default, since the
cache is written beside the scanned tree). Ruff then exits 2 with "Failed to
initialize cache". That abort is *not* a validator result and must not be recorded
as one. Fixed in RUN-RECIPE by mandating `--no-cache` (or a tmpfs cache dir).

**B5 [WARNING, from review] Mutable image tag.** Dispatch must use the immutable
image ID `sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`
(linux/amd64), recorded identically for all four arms. Fixed in RUN-RECIPE.

## C. Candidate replacement packets — EXACT BYTES NOW EXIST FOR REVIEW

A prior draft of this section asked the owner to confirm hashes that did not yet
exist, and proposed rewriting the signed amendment v2 in place. Both were wrong
and are withdrawn. Corrected procedure: the replacements exist first as
**versioned candidate files**, their exact sha256 are recorded below, they are
probed, and only then does the owner re-sign **those exact bytes**.

### C1. Old → new map (append-only; amendment v2 is NEVER edited)

| Role | Frozen v1 (stays byte-stable) | v1 sha256 | Candidate v2 | v2 sha256 |
|---|---|---|---|---|
| Producer-safe pins | `validator-pins.md` | `6ea4b3226a3f54dce265ad27a67209b9d803b27d690cc4d899d20fff9a7f2d5f` | `candidate/validator-pins-v2.md` | `877896c7672b1f47383e19ab00a38049344634c12c328a205a1651c6da4bf46d` |
| Designer-only expectation | `validator-expectation-DESIGNER-ONLY.md` | `dcff3d2d0d3f02f4ef57283718c61b5fe890e54b109b90be05b68d7a25fb52c6` | `candidate/validator-expectation-DESIGNER-ONLY-v2.md` | `61e1e52743e78ad9d38bd50e311978f5d49f513d617a48fd9a9b5a0901d02092` |
| Scorer contract | `scorer-handoff-contract.json` | `e8945c4b7eee256c96e6c7f21beef02f885b9f6c7caf6b2b65197088bcd5226a` | **unchanged** | — |

**Superseded v2 fields (recorded here, not rewritten there):** amendment v2
Section A's producer-file allowlist row for `validator-pins.md` and Section B's
designer-only row are superseded by the v2 rows above. Amendment v2 keeps its
original bytes and hashes so it stays possible to know exactly what the owner
signed on 2026-07-24. On re-sign, the canonical producer packet path becomes
`candidate/validator-pins-v2.md` and the designer-only path becomes
`candidate/validator-expectation-DESIGNER-ONLY-v2.md`.

### C2. What the candidates change

- **pins v2**: every frozen setting is now carried explicitly on the command line
  (so the command *is* the config, closing B2), plus `--no-cache` /
  `--no-incremental` so a cache-init failure can never be mistaken for a result.
- **expectation v2**: replaces "Expected signal: NULL" with the measured baseline
  and restates `D−C` ≈ 0 as *"validator feedback exists but is unrelated to the
  defect"*, adds that Arm D may do **worse** by spending budget on the unrelated
  findings, and records the LF-clean precondition.

### C3. Scoped probe of the candidate commands (verbatim, in image `sha256:e6df7283…`)

Run against the LF-clean sanitized baseline (tree `36c346fa…`, verified LF-only):

| Candidate v2 command | Measured |
|---|---|
| `shellcheck --shell=bash --severity=style scripts/hooks/pre-push` | only `SC1090`, **exit 1** |
| `ruff check --no-cache --line-length 100 --target-version py312 --select E,F,W,I,B governance_tools/version_bump_guard.py` | `I001` (line 6), `E501` (line 125, 104>100), "Found 2 errors", exit 1 |
| `mypy --no-incremental --python-version 3.12 --warn-unused-ignores --warn-return-any --no-implicit-optional governance_tools/version_bump_guard.py` | "Success: no issues found in 1 source file", exit 0 |

**Exit-code correction (2026-07-25).** An earlier draft of this table and of the
first expectation candidate recorded shellcheck as **exit 0**. That was wrong: the
probe read `$?` after a pipeline, so it captured the pipeline's last element, not
shellcheck. Measured directly (output discarded, `$?` read immediately) the exact
commands return shellcheck **1**, ruff **1**, mypy **0**. The expectation
candidate was corrected and re-hashed from `1678e663…` to `61e1e527…`; the
superseded hash must not be signed. This is the same exit-code-masking class that
has recurred in this work, so exit codes are now measured without pipes.

These match `expectation v2` exactly, so the candidate pair is internally
consistent and reproducible before any signature.

## D. Why Gate 2 must not start first

Starting now would produce **protocol-invalid Arm D data**: the arm's actual
treatment (noisy, unrelated validator findings, possibly plus 80 spurious CRLF
errors) would differ from what was pre-registered (silence). Per program Section 9
that is an INVALID run — excluded from comparison, not merely lower-scored. The
cheapest correct action is to re-sign this amendment first.

## E. Owner re-sign — SIGNED 2026-07-25

The owner re-signed these exact bytes, on the independently-reviewed and
APPROVED corrected values (shellcheck=1, ruff=1, mypy=0; superseded hash
`1678e663…` explicitly not signed):

1. `candidate/validator-pins-v2.md`, sha256
   `877896c7672b1f47383e19ab00a38049344634c12c328a205a1651c6da4bf46d`
   — **SIGNED.** Canonical producer-safe pins packet.
2. `candidate/validator-expectation-DESIGNER-ONLY-v2.md`, sha256
   `61e1e52743e78ad9d38bd50e311978f5d49f513d617a48fd9a9b5a0901d02092`
   — **SIGNED.** Canonical designer-only expectation, replacing "NULL" with the
   measured SC1090 (exit 1) / I001+E501 (exit 1) / clean-mypy (exit 0) baseline.
3. The C1 old→new map is confirmed, with amendment v2 left **byte-stable** (its
   rows are superseded by this document, never rewritten in place).
4. The already-applied non-frozen fixes: hermetic export pinning
   `core.autocrlf=false` plus the LF-only worktree check, the immutable image ID,
   and ruff `--no-cache`.

**This signature is not itself a Gate 2 start command.** One further step
remains before Gate 2 can be considered:

- **Canonical promotion slice — DONE 2026-07-25.** The preflight manifest's
  packet pointers were updated to the candidate paths/hashes above (the
  manifest's authority line was also corrected to name this re-signed v3, not
  v2 alone, for the validator packets); this amendment's status is marked
  "RE-SIGNED AND PROMOTED" above. Nothing was recomputed — the hashes were
  already final.
- **Post-sign image preflight — DONE 2026-07-25.** Re-ran the pinned-image
  synthetic preflight against the newly-canonical packets:
  `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/POST-SIGN-PREFLIGHT-20260725.md`.
  Same image digest, same baseline reconstruction (tree `36c346fa…`, LF-only),
  same isolation probes (all passed), same three exact validator commands,
  measured directly with no pipe: shellcheck 1, ruff 1, mypy 0 — **no
  regression** from the signed expectation.

All Section E steps are complete. What remains is entirely the
**still-outstanding resource preflight** (4 answer-blind
producer contexts, 2 arm-identity-blind scorer contexts, an out-of-band model
control plane, stamped model/permission constants), may the owner issue a
**separate, explicit** "start Gate 2" command.

## F. Cannot claim

- That Gate 2 may start, or that any arm has run.
- That any producer or scorer context, or an out-of-band model control plane,
  exists.
- That the post-sign image preflight (which found no regression) constitutes a
  producer or scorer run, or any part of Gate 2 execution — it is verification
  only, performed by this design session.
- That the tree-hash invariant alone proves an uncontaminated producer checkout
  (the mandatory LF-only check is still required alongside it).
- That the Bug Fix Skill or the validator treatment is effective.
