"""Offline-only bridge from a contained-process result to the injected seam.

The bridge maps exactly one contained result into the ``InjectedContainedResult``
the merged coordinator consumes.  It never launches a process, reads
credentials, retains stdout, or renders either result object.

The bridge owns the contained-result mapping and the final-output observation.
It does **not** own workspace observation: under contract v2 the coordinator
receives the private baseline map and the authorized digest and performs that
comparison itself.
"""

from __future__ import annotations

from typing import Callable

import gate3_final_message_runner_integration as integration


FINAL_CAPTURED = "CAPTURED"
FINAL_ABSENT = "ABSENT"
FINAL_READ_FAILED = "READ_FAILED"


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


# `make_observe_workspace` was retired when the contract v2 coordinator took
# ownership of workspace observation.  It built a callback that closed over a
# caller-supplied baseline, but the coordinator field accepted any zero-argument
# callable, so nothing forced callers through the builder.  Ownership moved
# rather than gaining a check inside it: the coordinator now receives the private
# baseline map and the authorized digest and performs the comparison itself,
# leaving no callable to substitute.  The bridge keeps its mapping, disposition
# and privacy behaviour, and `make_observe_final` is unaffected.
