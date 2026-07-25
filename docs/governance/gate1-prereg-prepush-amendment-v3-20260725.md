# Gate 1 Correction Amendment v3 — Arm D expected signal + validator config binding

Status: **CORRECTION v3, PENDING OWNER RE-SIGN.** Gate 2 must NOT start until this
is re-signed. Amendment v2 stays authoritative for everything it covers; v3
corrects only the Arm D validator treatment (expected signal, config binding) and
the sanitized-baseline export procedure. No hook, runtime, CI, schema, gate, or
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

**B4 [WARNING, found by this session] `--read-only` breaks ruff's default cache.**
Ruff aborts with "Failed to initialize cache" because `.ruff_cache` targets the
read-only mount. That abort is *not* a validator result and must not be recorded
as one. Fixed in RUN-RECIPE by mandating `--no-cache` (or a tmpfs cache dir).

**B5 [WARNING, from review] Mutable image tag.** Dispatch must use the immutable
image ID `sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`
(linux/amd64), recorded identically for all four arms. Fixed in RUN-RECIPE.

## C. Required corrections to FROZEN packets (require re-sign)

1. **`validator-expectation-DESIGNER-ONLY.md`** — replace "Expected signal: NULL"
   with the measured baseline: ShellCheck SC1090; Ruff I001 + E501 under the
   frozen config; mypy clean. Restate the `D−C` expectation as *"validator
   feedback exists but is unrelated to the defect"*, so a null effect is
   interpreted as "unrelated findings did not help", not "no findings existed".
2. **`validator-pins.md` (producer-safe)** — make the commands actually carry the
   frozen config (explicit flags, since the packet must stay a single file), and
   add `--no-cache`. Both packet sha256 values change and must be re-recorded in
   amendment v2 Section A/B and the preflight manifest.

Because these are frozen, experiment-defining artifacts, they are **not edited by
this document**. They change only after owner re-sign, in one slice, with the new
hashes recorded.

## D. Why Gate 2 must not start first

Starting now would produce **protocol-invalid Arm D data**: the arm's actual
treatment (noisy, unrelated validator findings, possibly plus 80 spurious CRLF
errors) would differ from what was pre-registered (silence). Per program Section 9
that is an INVALID run — excluded from comparison, not merely lower-scored. The
cheapest correct action is to re-sign this amendment first.

## E. Owner re-sign required

Gate 2 stays blocked until the owner confirms:
1. The corrected Arm D expected signal (C1).
2. The corrected validator commands + new packet hashes (C2).
3. The hermetic export + LF check, immutable image ID, and ruff `--no-cache`
   (already applied to the non-frozen manifest/recipe).

## F. Cannot claim

- That Gate 2 may start, or that any arm has run.
- That Arm D's treatment currently matches the pre-registration (it does not).
- That the tree-hash invariant alone proves an uncontaminated producer checkout.
- That the Bug Fix Skill or the validator treatment is effective.
