# C1 sandbox qualification pre-run freeze

This directory freezes the only reviewed execution path for the task-neutral,
non-counted sandbox qualification. It does not authorize or execute the hosted
request.

The executor derives the publication root, machine-policy receipt, installed
APPX source, exact Python interpreter, and temporary CLI staging root from the
manifest. The only runtime inputs are the exact owner-authorized freeze commit
and an authentication file whose bytes are neither frozen nor retained.

Qualification success requires the conjunction already defined by the merged
sandboxed-runner amendment: hosted transport completion, denial of every
applicable task-command network class through the exact runner tool path,
elevated sandbox identity, enforced managed requirements, no fallback, and
complete cleanup. A successful terminal remains `NOT_RANDOMIZED`.

The compatibility/authority reconciliation selects the sandboxed runner for
future C1 arm execution, but existing consumers are intentionally unchanged in
this tranche. A separate amendment may update those consumers only after this
qualification produces a reviewed PASS terminal.

No retry is authorized. Any terminal consumes this qualification attempt.
