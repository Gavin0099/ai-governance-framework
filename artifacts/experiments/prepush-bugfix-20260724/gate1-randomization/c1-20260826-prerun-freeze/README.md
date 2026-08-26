# C1 Gate 1 randomization pre-run freeze

This correction freezes the only executor allowed to create the first C1
randomization_committed event for pair-02. Pair-01 remains consumed as an
infrastructure-invalid, zero-event attempt. Authoring and review do not execute
pair-02.

The executor validates the reviewed D5 admission, exact client-side invocation
identity, a fresh 12-hour batch window, and complete A/B input bindings before
it accesses randomness. An executable-launch failure has its own infrastructure
terminal and consumes pair-02 without retry. It then stages a private mapping reveal, a public
randomization record, exactly one evidence-chain event, and one terminal before
publishing the attempt directory create-once.

The manifest freezes one repository-relative evidence root and one final attempt
root. The executor rejects any caller-supplied path that differs and scans the
entire frozen evidence root for prior pair-02 record, event, or terminal state
before it accesses randomness. Publication uses a deterministic staging directory
created with parent ACL inheritance; it does not rename a private `mkdtemp`
directory into the evidence surface. Create-once therefore applies to the comparison,
not merely to a caller-selected path.

The private mapping reveal is never a producer or scorer input. No hosted-model
request, producer, scorer, arm, mapping release, or Rekor POST belongs to this
freeze.

Execution requires a later owner authorization whose SHA equals the actual
reviewed freeze commit. The committed manifest remains unauthorized.
