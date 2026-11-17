"""The operable Claude formal closeout command.

One invocation does what #233 asked for and nothing else: record the owner's
explicit closeout request, publish the Claude SessionEnd evidence, and release
ownership so the next session can acquire it.

    python -m governance_tools.claude_formal_closeout \\
        --project-root . --session-id <sid> \\
        --owner-request "close out this session" \\
        --transcript-path <path to the session jsonl>

or, when the owner authorized the closeout in advance (owner ruling 2026-11-11):

    python -m governance_tools.claude_formal_closeout \\
        --project-root . --session-id <sid> \\
        --authorization-ref docs/slices/<slice>.md@<commit> \\
        --condition-met "<which authorized condition this session met>" \\
        --transcript-path <path to the session jsonl>

It reuses the existing core rather than adding a second closeout mechanism:
claude_closeout_publisher.publish for the evidence, closeout_handoff's
consume_exact_request for the release. The only new thing is the attestation,
and the release gate that requires it lives in the core, not here, because a
gate only this command enforces is not a gate.

THREAT MODEL IS COOPERATIVE. --owner-request records what the owner asked; it
does not prove a human typed it, because the same process can write that record.
This command gives a recorded operation whose bytes are bound to exact state.
It does not establish that the statement came from the owner or that the owner
knew of it, so it is neither authentication nor attribution. manual_fallback remains rejected and is not involved.

--authorization-ref points at an `[Owner Closeout Authorization]` block committed
before this session started (see closeout_attestation). It saves asking the owner
again at every handover; it does not make Git an owner signature. The block must
name a verifiable original owner source, and a person checks that source.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools import claude_closeout_publisher as publisher
from governance_tools import closeout_attestation as attestation
from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2

DEFAULT_DEADLINE_MS = 120000


def close_out(project_root, session_id: str, owner_request: str | None, transcript_path,
              *, deadline_ms: int = DEFAULT_DEADLINE_MS, reason: str = "owner_request",
              authorization_ref: str | None = None, condition_met: str | None = None) -> dict:
    """Attest, publish, release. Each step fails closed on its own evidence."""
    root = Path(project_root).resolve(strict=True)
    source = Path(transcript_path)
    h._require(source.is_absolute() and source.is_file(),
               "INVALID_TRANSCRIPT: an existing absolute path is required")
    standing = authorization_ref is not None
    h._require(standing != (owner_request is not None),
               "AUTHORIZATION_REQUIRED: give exactly one of --owner-request or --authorization-ref")
    h._require(standing == (condition_met is not None),
               "AUTHORIZATION_REQUIRED: --condition-met goes with --authorization-ref")

    if standing:
        attested = attestation.record_standing(root, session_id, authorization_ref, condition_met)
        reason = "owner_authorized_condition"
    else:
        attested = attestation.record(root, session_id, owner_request)

    payload = dict(hook_event_name="SessionEnd", session_id=session_id, cwd=str(root),
                   transcript_path=str(source), reason=reason)
    published = publisher.publish(root, payload, deadline_ms=deadline_ms)
    request_id = published.get("request_id")
    h._require(isinstance(request_id, str) and bool(request_id),
               "PUBLICATION_INCOMPLETE: no request id to consume")

    released = h.consume_exact_request(root, request_id, session_id=session_id,
                                       provider=h.ClaudeTranscriptProvider(root))
    return {"status": released.get("status"),
            "attestation_id": attested["attestation_id"],
            "request_id": request_id,
            "publication": published.get("status"),
            "owner_state": _owner_state(root),
            "transcript_ingestion": released.get("transcript_ingestion"),
            "authorization_kind": "standing_owner_authorization" if standing else "owner_request",
            # Recorded so the caller cannot mistake this for authentication.
            "authorization_model": "cooperative: recorded byte-bound statement; "
                                   "not authentication, not attribution, not "
                                   "proof that the owner made or knew of it"
                                   + ("; the referenced block was committed before this "
                                      "session started and names an owner source that a "
                                      "person must check" if standing else "")}


def _owner_state(root):
    try:
        with r2.execution_exclusion(root) as lease:
            owner = r2._owner(lease)
        return None if owner is None else owner["state"]
    except (ValueError, OSError):
        return "unknown"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--owner-request",
                        help="What the owner actually asked, recorded verbatim.")
    parser.add_argument("--authorization-ref",
                        help="<path>@<commit> of an owner authorization committed before "
                             "this session started; replaces --owner-request.")
    parser.add_argument("--condition-met",
                        help="Which condition of that authorization this session met.")
    parser.add_argument("--transcript-path", type=Path, required=True)
    parser.add_argument("--deadline-ms", type=int, default=DEFAULT_DEADLINE_MS)
    args = parser.parse_args(argv)
    try:
        result = close_out(args.project_root, args.session_id, args.owner_request,
                           args.transcript_path, deadline_ms=args.deadline_ms,
                           authorization_ref=args.authorization_ref,
                           condition_met=args.condition_met)
        print(json.dumps(result))
        return 0
    except (ValueError, TypeError, KeyError, OSError, TimeoutError, RuntimeError) as exc:
        # A failure here never proves the release did not happen; report, do not
        # assert absence.
        print(json.dumps({"status": "UNCONFIRMED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
