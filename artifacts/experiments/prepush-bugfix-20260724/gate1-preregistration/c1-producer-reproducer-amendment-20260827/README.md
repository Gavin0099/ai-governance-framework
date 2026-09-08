# C1 producer-visible reproducer amendment

This directory freezes the missing black-box reproducer that the C1 common task
already promises to both A and B producers. The reproducer is derived only from
the pinned baseline's public bulk-import route. It does not contain a correction,
a scorer assertion, a historical fix, or a candidate-derived expectation.

The producer-visible surface is exactly:

- `producer-visible-bulk-import-reproducer.test.ts`, materialized byte-for-byte
  at the frozen destination; and
- the structured `argv` in `reproducer-contract.json`, invoked without a shell
  from an owned disposable checkout of the pinned baseline.

The reproducer succeeds after printing one canonical observation line. Success
means only that the baseline behavior was observed through the product route; it
does not mean the bug was corrected. The fixture, contract, validation receipt,
technical specification, tests, and manifest are coordinator/reviewer surfaces,
not additional producer input.

`common-input-amendment.json` is an append-only amendment to the immutable C1
preregistration. It adds the same reproducer and command to A and B. It changes
no threshold, treatment packet, budget, scorer surface, attempt-06 quarantine,
or D5 countability decision.

Status: `COMMON_INPUT_REPRODUCER_FROZEN_NOT_EXECUTED`.
