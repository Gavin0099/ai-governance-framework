# Gotchas

- `--mode enforce` currently runs shared smoke plus a focused pytest suite. It is a meaningful gate, but it is not the same as proving every repository test path is green.
- On Windows, this wrapper expects a bash-capable environment. Do not misreport a missing shell as a governance failure.
- If pytest is missing, the failure is environment setup, not code correctness.
- Do not collapse multiple failures into "precommit failed". The useful distinction is whether the blocker is shell, Python, smoke, or focused tests.
- Passing the local gate does not justify claims about PR readiness or CI status. Those are later stages.
- A passing gate does not erase scoped review risks. Missing tests, weak evidence, or an over-broad claim still need to be reported before commit.
- Keep the precommit review scoped to the current diff. Do not turn it into unrelated cleanup advice unless the unrelated issue directly threatens the commit.
