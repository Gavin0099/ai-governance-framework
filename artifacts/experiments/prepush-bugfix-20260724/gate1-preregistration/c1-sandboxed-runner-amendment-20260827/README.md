# C1 sandboxed runner amendment freeze

This directory freezes an append-only successor to the C1 common harness. It
replaces the prior full-access Codex command with an elevated Windows
workspace-write command whose model-generated task process must be offline.

The freeze is not an execution authorization. In particular it does not:

- configure or mutate the Windows sandbox;
- execute a hosted-model request;
- create pair-03 randomization;
- execute producer, scorer, or A/B/C/D arms;
- release mapping or write to Rekor.

The qualification executor additionally requires explicit owner authority for
both the reviewed freeze commit and an exact, separately reviewed machine-policy
receipt. The latter is required because elevated sandbox setup can change local
accounts, firewall rules, and local policy outside Git.

The network-denial probe is staged into the runner workspace and must be invoked
through the exact runner's model-generated command path. Running it independently
does not satisfy this freeze.

Status: `SANDBOXED_RUNNER_AMENDMENT_FROZEN_NOT_QUALIFIED`

