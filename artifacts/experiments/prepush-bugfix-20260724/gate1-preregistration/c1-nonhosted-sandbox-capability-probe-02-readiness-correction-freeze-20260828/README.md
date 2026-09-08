# C1 capability-probe-02 execution-readiness correction freeze

This freeze converts the capability-probe-01 preclaim STOP into a general
execution-readiness contract. It does not repair or retry probe-01.

The tracked Gate 1 execution anchor makes the required parent materialize in
every Git checkout. The manifest derives the only accepted parent, anchor,
child allowlist, containment and write-evidence requirements. Before a formal
probe-02 authorization packet may exist, the exact detached checkout and exact
execution identity must produce a bounded readiness receipt, clean its sentinel,
and receive independent review. The formal streamed driver requires the digest
of that review packet and rechecks the receipt against live state before the
atomic attempt claim.

Preclaim failure publishes no claimed-attempt terminal. After a successful
atomic claim, bounded failures publish one terminal. An overlapping loser owns
nothing and may neither clean nor publish the winner's evidence.

The convergence window contains exactly capability-probe-02 and
sandboxed-runner-qualification-03. Any new unmapped fundamental infrastructure
prerequisite triggers `STOP_BEFORE_FURTHER_FORMAL_ATTEMPT`; no probe-03 or
qualification-04 may be created before a runtime dependency inventory and
execution state-machine audit receive a new owner decision.

This freeze does not execute readiness, the capability probe, a hosted request,
qualification-03, randomization, producer, scorer, arms, mapping release, or a
Rekor POST. It does not modify machine policy.
