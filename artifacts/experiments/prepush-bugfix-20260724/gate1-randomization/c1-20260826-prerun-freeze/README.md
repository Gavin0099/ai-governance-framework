# C1 Gate 1 randomization pre-run freeze

This directory freezes the only executor allowed to create the first C1
randomization_committed event. Authoring and review do not execute it.

The executor validates the reviewed D5 admission, exact client-side invocation
identity, a fresh 12-hour batch window, and complete A/B input bindings before
it accesses randomness. It then stages a private mapping reveal, a public
randomization record, exactly one evidence-chain event, and one terminal before
publishing the attempt directory create-once.

The private mapping reveal is never a producer or scorer input. No hosted-model
request, producer, scorer, arm, mapping release, or Rekor POST belongs to this
freeze.

Execution requires a later owner authorization whose SHA equals the actual
reviewed freeze commit. The committed manifest remains unauthorized.

