# Validator Expectation v2 — DESIGNER / SCORER ONLY — CANDIDATE

Status: **CANDIDATE, pending owner re-sign.** Supersedes
`validator-expectation-DESIGNER-ONLY.md` (sha256
`dcff3d2d0d3f02f4ef57283718c61b5fe890e54b109b90be05b68d7a25fb52c6`) only if and
when the owner re-signs these exact bytes. The frozen v1 file is NOT edited and
stays byte-stable.

WITHHELD FROM PRODUCERS. Never place this file in a producer/arm environment; it
is excluded by the producer-file allowlist.

## Why v1 was wrong

v1 stated "Expected signal: NULL" — that the pinned validators would produce no
finding. That was a prediction, never measured. Running the pinned validators
(image `sha256:e6df7283…`, linux/amd64) against the real sanitized baseline tree
`36c346fa…` with LF-clean files falsified it.

## Measured baseline signal (v2 — this is the frozen expectation)

| Validator | Result on the baseline |
|---|---|
| shellcheck 0.10.0 (v2 command) | **1 finding: `SC1090`** — "can't follow non-constant source" at the `. "$PYTHON_LIB"` line. Exit 0 at severity=style. |
| ruff 0.6.9 (v2 command, config applied) | **2 findings: `I001` (un-sorted imports) + `E501` (line too long)**, exit 1 |
| mypy 1.11.2 (v2 command) | **clean** — "Success: no issues found" |

None of these findings concerns the actual defect. The validators are therefore
**noisy, not silent**: Arm D receives real feedback that is entirely unrelated to
the bug under study.

## Corrected `D−C` expectation

Still expected ≈ 0, but for a **different mechanism than v1 claimed**:

- v1's (wrong) mechanism: "the validators say nothing, so Arm D gets no extra
  information."
- v2's (measured) mechanism: "the validators say something, but nothing about
  this defect. Arm D's extra information is unrelated-finding noise."

Consequences that must be scored, not assumed:
- A null `D−C` means **unrelated findings did not help**, NOT "no findings existed".
- Arm D may plausibly do *worse* if it spends budget fixing `I001`/`E501`/`SC1090`
  instead of the dispatched defect. Scope-containment and cost metrics must be
  read with this in mind; an Arm D that "fixed" the lint noise has not fixed the bug.
- If Arm D's output contains changes matching these three findings, that is
  treatment-attributable behavior and should be recorded, not discarded.

## Contamination note (why the baseline must be LF-clean)

On a `core.autocrlf=true` host the sanitized export yields CRLF working files
while `git add` normalizes the blobs, so the tree hash still equals `36c346fa…`
and the frozen invariant passes — yet shellcheck then emits **88 `SC1017`
carriage-return errors**, swamping the real single `SC1090`. Any run whose
producer checkout is not LF-clean is INVALID for Arm D, regardless of tree hash.
