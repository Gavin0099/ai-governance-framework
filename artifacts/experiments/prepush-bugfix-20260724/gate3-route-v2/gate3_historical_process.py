"""In-process M3-b-2 launch producer; native process control is not here yet.

The accepted materialized-root transport requires one parent-owned adapter to
bind a launch envelope to a live ``MaterializedTree``.  This module is that
seam.  It deliberately has no spawn, pipe, job, timeout, scratch-directory or
``__main__`` behaviour; those remain M3-b-2B.

Not active.  M4 is the only tranche allowed to switch the production route.
"""

from __future__ import annotations

import gate3_historical_bootstrap as bootstrap
import gate3_historical_child as child
import gate3_historical_materialize as materialize


ACTIVE = False
"""The launch producer is not wired into the production verifier."""


def build_launch_stream(
    tree: materialize.MaterializedTree,
    candidate_set_bytes: bytes,
    *,
    bindings=None,
) -> bytes:
    """Build one envelope from one M1 candidate and one matching M2 tree."""

    try:
        root, commit, retained, payloads = materialize.transport_bundle(
            tree, bindings=bindings
        )
    except materialize.MaterializationError as error:
        if error.code in {"RECORD_INVALID", "ROOT_IDENTITY_CHANGED"}:
            raise child.TransportError("MATERIALIZED_ROOT_RECORD_INVALID") from None
        raise

    candidate = bootstrap.verify_candidate_set(candidate_set_bytes)
    expected_commit = bootstrap.verify_source_commit(candidate)
    expected_retained = bootstrap.retained_inventory(candidate)
    expected_runtime = bootstrap.runtime_module_inventory(candidate)
    if commit != expected_commit or dict(retained) != expected_retained:
        raise child.TransportError("MATERIALIZED_ROOT_RECORD_INVALID")
    runtime_payloads = {path: payloads[path] for path in expected_runtime}

    inner_frame = child.encode_stream(candidate_set_bytes, runtime_payloads)
    return child.encode_launch_stream(inner_frame, root)
