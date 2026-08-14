"""Offline-only bridge from a contained-process result to the injected seam.

The bridge maps exactly one contained result into the ``InjectedContainedResult``
the merged coordinator consumes.  It never launches a process, reads
credentials, retains stdout, or renders either result object.

Scope is mapping characterization only.  The bridge participates in no runtime
authority: its own source is not a ``RUNTIME_SUBJECTS`` member, and the
workspace verdict it derives is a caller-supplied comparison, not public
evidence about a real workspace.
"""

from __future__ import annotations

from typing import Callable, Mapping

import gate3_final_message_runner_integration as integration


FINAL_CAPTURED = "CAPTURED"
FINAL_ABSENT = "ABSENT"
FINAL_READ_FAILED = "READ_FAILED"
WORKSPACE_CHANGED = "CHANGED"
WORKSPACE_UNCHANGED = "UNCHANGED"
WORKSPACE_CAPTURE_FAILED = "CAPTURE_FAILED"


class BridgeError(ValueError):
    """Closed bridge error that never renders private input."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def map_contained_result(completed: object) -> integration.InjectedContainedResult:
    """Map one contained result into the injected seam's closed shape.

    ``stderr`` is dropped rather than forwarded, and ``returncode`` is dropped on
    the timeout path because a non-``EXITED`` disposition requires a null exit
    code.  A result whose process tree was not terminated is a contract failure,
    not a mappable ``TERMINATED`` row: the real runner raises before returning
    such a result, so observing one means the caller is not the runner.
    """

    try:
        stdout = completed.stdout
        timed_out = completed.timed_out
        tree_terminated = completed.tree_terminated
    except AttributeError:
        raise BridgeError("CONTAINED_RESULT_INVALID") from None
    if (
        type(stdout) is not bytes
        or type(timed_out) is not bool
        or type(tree_terminated) is not bool
    ):
        raise BridgeError("CONTAINED_RESULT_INVALID")
    if not tree_terminated:
        raise BridgeError("CONTAINED_TERMINATION_INCOMPLETE")
    if timed_out:
        return integration.InjectedContainedResult(
            returncode=None,
            stdout=stdout,
            stderr=b"",
            process_disposition="TIMED_OUT",
            stdout_eof=True,
            stdout_reader_complete=True,
            stdout_read_failed=False,
        )
    try:
        returncode = completed.returncode
    except AttributeError:
        raise BridgeError("CONTAINED_RESULT_INVALID") from None
    if type(returncode) is not int:
        raise BridgeError("CONTAINED_RESULT_INVALID")
    return integration.InjectedContainedResult(
        returncode=returncode,
        stdout=stdout,
        stderr=b"",
        process_disposition="EXITED",
        stdout_eof=True,
        stdout_reader_complete=True,
        stdout_read_failed=False,
    )


def make_invoke(
    *,
    prepare: Callable[[], None],
    run_contained: Callable[[], object],
) -> Callable[[], integration.InjectedContainedResult]:
    """Build the coordinator's one-shot ``invoke`` callable.

    Preparation runs inside the invocation, after the launch ordinal has been
    consumed.  Any failure from either callable propagates unchanged: the
    coordinator converts it into a closed ``INVOCATION_DISPOSITION_UNKNOWN``.
    The bridge never raises ``ContainedStartFailed``, because from outside a
    single opaque call it cannot prove that no process started.
    """

    def invoke() -> integration.InjectedContainedResult:
        prepare()
        return map_contained_result(run_contained())

    return invoke


def make_observe_final(read_final: Callable[[], bytes | None]) -> Callable[[], str]:
    """Build a content-free final-output observation callback."""

    def observe_final() -> str:
        try:
            payload = read_final()
        except Exception:
            return FINAL_READ_FAILED
        if payload is None:
            return FINAL_ABSENT
        if type(payload) is not bytes:
            return FINAL_READ_FAILED
        return FINAL_CAPTURED

    return observe_final


def make_observe_workspace(
    read_workspace: Callable[[], Mapping[str, bytes]],
    baseline: Mapping[str, bytes],
) -> Callable[[], str]:
    """Build a content-free workspace observation callback.

    The baseline is supplied by the caller and is **not** authority-bound: no
    merged authority carries a workspace baseline field.  The resulting verdict
    is therefore a comparison against whatever the caller supplied, and must not
    be read as public evidence about a real workspace.
    """

    if not isinstance(baseline, Mapping) or not all(
        type(name) is str and type(payload) is bytes
        for name, payload in baseline.items()
    ):
        raise BridgeError("WORKSPACE_BASELINE_INVALID")
    expected = dict(baseline)

    def observe_workspace() -> str:
        try:
            observed = read_workspace()
        except Exception:
            return WORKSPACE_CAPTURE_FAILED
        if not isinstance(observed, Mapping) or not all(
            type(name) is str and type(payload) is bytes
            for name, payload in observed.items()
        ):
            return WORKSPACE_CAPTURE_FAILED
        return (
            WORKSPACE_UNCHANGED if dict(observed) == expected else WORKSPACE_CHANGED
        )

    return observe_workspace
