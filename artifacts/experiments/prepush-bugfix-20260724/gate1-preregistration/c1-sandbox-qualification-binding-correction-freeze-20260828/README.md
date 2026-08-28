# C1 sandbox qualification binding correction freeze

This directory supersedes the unexecuted qualification pre-run freeze merged by
PR #127. It closes the reviewed binding and publication findings without
executing qualification.

The only authorized entrypoint is `qualification_binding_bootstrap.py` streamed
directly from the owner-authorized commit blob into the exact Python interpreter
with `-I -`. Direct execution of either working-tree Python file is forbidden.
The bootstrap uses Git with `--no-replace-objects`, verifies HEAD, the manifest,
the complete frozen-file tree, every frozen blob OID/content binding, and the
Python executable before creating its bounded staging root. It then materializes
the verified executor and launches only that copy. The executor rejects any base
directory other than the frozen bootstrap staging root.

The reviewed execution shape is:

```text
git --no-replace-objects -c safe.directory=<repo> -C <repo> show <authorized-commit>:artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/c1-sandbox-qualification-binding-correction-freeze-20260828/qualification_binding_bootstrap.py | <exact-python> -I - --repo-root <repo> --owner-authorized-freeze-commit <authorized-commit> --auth-file <authorized-auth-file>
```

Changing the left side to a working-tree read, invoking either Python file by
path, or omitting `-I` is outside this freeze and is not authorized.

The materialized executor resolves and verifies the owner-authorized HEAD. It
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
