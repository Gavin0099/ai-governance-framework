# C1 Stryker validator probe evidence

Terminal disposition: `VALIDATOR_PROBE_FAILED`.

The exact baseline materialization and diff-derived mutation range succeeded.
The timeout sentinel returned the required exit code, and both package tarballs
matched their frozen SHA-512 values. The subsequent installation of those two
verified local tarballs failed with npm `ERESOLVE` while npm reconciled the
historical root dependency tree. The Vitest dry-run and mutation run were not
started.

The raw surfaces that were actually created contain no denied literal. This is
not evidence about the uncreated Stryker dry-run or mutation surfaces and is not
a general non-leakage result.

The consumer repository was used only as the read-only source of `git archive`,
and all probe writes targeted the disposable probe root. Its post-run status
inventory digest nevertheless differs from the pre-run digest. The evidence
preserves that difference without inspecting unrelated dirty paths or assigning
its cause, so it does not claim that the consumer worktree remained unchanged.

`probe-terminal.json` is the terminal authority. The other files are its bound
raw or structured evidence.
