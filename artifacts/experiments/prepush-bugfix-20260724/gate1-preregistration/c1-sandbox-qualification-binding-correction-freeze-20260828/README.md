# C1 sandbox qualification binding correction freeze

This directory supersedes the unexecuted qualification pre-run freeze merged by
PR #127. It closes the two P1 review findings without executing qualification.

The executor first resolves and verifies the owner-authorized HEAD. It then
loads this manifest from that exact Git commit, not from the working tree. Every
source binding is read and verified from Git objects into memory before any
staging root is created, authentication bytes are read, executable module is
imported, or hosted request can occur.

After all bindings pass, the exact source blobs are materialized under the
owned CLI staging root. Modules are loaded by exact file path while the required
dependency names are temporarily bound to those exact modules; pre-existing
`sys.modules` entries and `sys.path` entries cannot select executable code.

Qualification attempt `C1-sandboxed-runner-qualification-01` remains
unexecuted. The output and staging roots are unchanged and create-once. Any
future execution still requires a new owner authorization bound to the exact
reviewed correction commit.

No hosted request, consumer amendment, randomization, producer, scorer, arm,
mapping release, or Rekor POST belongs to this freeze.
