# C1 sandbox qualification-02 diagnostic correction freeze

This directory freezes a new, unexecuted qualification attempt after
qualification-01 produced the reviewed terminal bound in
`qualification-01-terminal-binding.json`.

It closes two observed failures:

- an unclassified post-launch exception was mislabeled as a binding mismatch;
- failure terminals discarded all bounded stdout/stderr evidence.

Qualification-02 uses an explicit failure-stage machine. Terminal status is
derived from the stage and exception type, never from exception-message
substrings. The catch-all is `SANDBOXED_RUNNER_UNCLASSIFIED_FAILURE`.

After the launcher returns, return code, timeout state, stdout/stderr byte counts,
and stdout/stderr SHA-256 values are captured before probe reading or validation.
Raw stdout, stderr, model output, prompt, environment, credentials, and exception
messages are never retained.

The trusted execution shape remains the reviewed commit-blob bootstrap:

```text
git --no-replace-objects cat-file blob <authorized-bootstrap-oid>
  | <exact-python> -I - --repo-root <repo>
      --owner-authorized-freeze-commit <authorized-commit>
      --auth-file <private-auth-file>
```

Direct working-tree bootstrap or executor execution remains forbidden.

## Authority boundary

This freeze does not authorize qualification-02, a hosted request, a consumer
amendment, randomization, producer/scorer/arm execution, mapping release, or a
Rekor POST. Qualification-01 remains consumed and may not be retried.
