# C1 Probe-02 parent-readiness evidence-publication correction freeze

This freeze adds the missing evidence-publication boundary around the reviewed
parent-readiness trusted bootstrap. It does not execute readiness.

The publisher is itself accepted only when streamed from the exact
owner-authorized commit blob into the exact Python interpreter with `-I -`.
It verifies its frozen inventory, predecessor bootstrap, predecessor manifests,
Git, Python, repository HEAD, evidence parent, and create-once evidence state
before creating the evidence root or launching the readiness child.

After exclusive root creation, `start.json` is atomically published and read
back before the child starts. A successful child must return exactly one
bounded JSON receipt on stdout, return zero, produce no stderr, and satisfy the
frozen `PARENT_READINESS_PASSED` schema and sentinel assertions. The exact
stdout bytes are published with exclusive create, fsync, and readback at the
manifest-bound rev1 receipt path. Failures after start produce a bounded
`terminal.json`; raw stdout and stderr are never retained. If terminal
publication itself fails, the durable start record remains.

This freeze never creates or approves the independent review packet. It grants
no readiness, Probe-02, hosted-request, Qualification-03, randomization,
producer, scorer, or arm execution authority.
