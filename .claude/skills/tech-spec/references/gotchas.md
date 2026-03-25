# Gotchas

- Not every change needs a long spec. Trivial fixes can use a short version, but the problem, scope, and evidence still need to be explicit.
- Do not spec work outside this repository's intended boundary, such as IDE-native generation interception or a generic multi-agent orchestration platform.
- Keep the problem statement separate from the first implementation tranche. A broad problem does not justify a broad first diff.
- Non-goals are mandatory. If they are missing, scope will drift during implementation.
- If candidate touched files are only guesses, label architecture-impact output as provisional rather than treating it as final project truth.