"""Classify a corpus of real Codex rollouts against the frozen route wrapper.

The offline probe in ``gate3_wrapper_acceptance_probe.py`` answers "what does
the route accept" using hand-written shapes. This answers the complementary
question -- "what does the CLI actually emit" -- from rollouts that already
exist on disk, at zero authorization cost and without invoking a session.

Privacy boundary, and it is the whole point of this module: a rollout corpus is
private material. Nothing derived from a tool input is emitted except its
structural classification -- tool family, envelope, argument shape, and field
names drawn from ``SAFE_TOOL_INPUT_FIELD_NAMES``. No command, path, argument
value, session identifier or file name reaches the report, and the report is
refused if ``_privacy_violations`` finds anything.

Passing that check is not a licence to publish. It shows no obvious sensitive
string survived; it does not show that statistics derived from someone's
private sessions are fit to publish. A full report describes a usage profile --
which CLI builds, how much, which rare structures -- and a rare structure can
identify a session on its own. Two defaults exist for that reason:

* ``--min-signature-count`` folds thinly-attested signatures into a count-only
  bucket, so no classification rests on a handful of sessions.
* ``--aggregate-only`` drops the per-version and per-signature breakdowns
  entirely and keeps the totals and the cosmetic/privilege split, which is the
  shape to use if a report is ever reviewed for publication.

Treat a full report as local working material.

Usage:
    python gate3_wrapper_corpus_scan.py --sessions-root <dir> --out <report>
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate3_codex_live_canary as live  # noqa: E402

# What admitting a field would mean for the route, used to separate wrapper
# variance that is merely cosmetic from variance that would widen privilege.
FIELD_SEMANTICS = {
    "command": "core",
    "workdir": "core",
    "timeout_ms": "execution_bound",
    "justification": "approval_metadata",
    "prefix_rule": "approval_policy",
    "sandbox_permissions": "privilege",
    "login": "shell_semantics",
}
PRIVILEGE_AFFECTING = {"approval_policy", "privilege", "shell_semantics"}


def _signature(source: str) -> dict[str, Any]:
    diagnostic = live._tool_input_wrapper_diagnostic(source)
    census = diagnostic["field_name_census"]
    names = sorted(census["known_field_counts"])
    semantics = sorted({FIELD_SEMANTICS[name] for name in names})
    return {
        "argument_shape": diagnostic["argument_shape"],
        "envelope": diagnostic["envelope"],
        "field_names": names,
        "field_semantics": semantics,
        "privilege_affecting": any(
            value in PRIVILEGE_AFFECTING for value in semantics
        ),
        "rejection_class": diagnostic["rejection_class"],
        "tool_family": diagnostic["tool_family"],
        "unknown_field_count": census["unknown_field_count"],
    }


def _exec_inputs(path: Path):
    """Yield (cli_version, tool input) for exec calls in one rollout."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    cli_version = "<unknown>"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if record.get("type") == "session_meta":
            cli_version = str(payload.get("cli_version", "<unknown>"))
        if (
            payload.get("type") != "custom_tool_call"
            or payload.get("name") != "exec"
        ):
            continue
        source = payload.get("input")
        if isinstance(source, str):
            yield cli_version, source


DEFAULT_MIN_SIGNATURE_COUNT = 5


def scan(
    sessions_root: Path,
    *,
    min_signature_count: int = DEFAULT_MIN_SIGNATURE_COUNT,
    aggregate_only: bool = False,
) -> dict[str, Any]:
    totals: collections.Counter = collections.Counter()
    accepted: collections.Counter = collections.Counter()
    signatures: dict[str, dict[str, Any]] = {}
    unknown_fields_seen = 0
    sessions = 0
    for path in sorted(sessions_root.rglob("*.jsonl")):
        seen_any = False
        for cli_version, source in _exec_inputs(path):
            seen_any = True
            totals[cli_version] += 1
            if live.SHELL_WRAPPER_RE.fullmatch(
                source
            ) or live.PATCH_WRAPPER_RE.fullmatch(source):
                accepted[cli_version] += 1
                continue
            signature = _signature(source)
            unknown_fields_seen += signature["unknown_field_count"]
            key = json.dumps(signature, sort_keys=True)
            entry = signatures.setdefault(
                key, {**signature, "count": 0, "cli_versions": {}}
            )
            entry["count"] += 1
            entry["cli_versions"][cli_version] = (
                entry["cli_versions"].get(cli_version, 0) + 1
            )
        if seen_any:
            sessions += 1
    all_signatures = sorted(
        signatures.values(), key=lambda entry: (-entry["count"], entry["envelope"])
    )
    for entry in all_signatures:
        entry["cli_versions"] = dict(sorted(entry["cli_versions"].items()))
    retained = [
        entry for entry in all_signatures if entry["count"] >= min_signature_count
    ]
    below = [
        entry for entry in all_signatures if entry["count"] < min_signature_count
    ]
    total = sum(totals.values())
    accepted_total = sum(accepted.values())
    privilege_affecting = sum(
        entry["count"] for entry in all_signatures if entry["privilege_affecting"]
    )
    rejected_total = total - accepted_total
    report: dict[str, Any] = {
        "boundary": [
            "Structural classification only; no tool input content is "
            "retained, and no session, file or path identity is recorded.",
            "Acceptance counts describe this corpus, not the population of "
            "runs the frozen route will see.",
            "A corpus produced by the same route the wrapper was written "
            "against cannot independently confirm that wrapper.",
            "Passing the privacy check does not make a full report fit to "
            "publish; it still describes a private usage profile.",
        ],
        "distinct_rejected_signatures": len(all_signatures),
        "exec_tool_calls": total,
        "exec_tool_calls_accepted": accepted_total,
        "field_name_allowlist_covered_every_emission": unknown_fields_seen == 0,
        "min_signature_count": min_signature_count,
        "pinned_cli_version": live.DEFAULT_CLI_VERSION,
        "privilege_affecting_rejections": privilege_affecting,
        "cosmetic_rejections": rejected_total - privilege_affecting,
        "rejections_by_class": {
            name: sum(
                entry["count"]
                for entry in all_signatures
                if entry["rejection_class"] == name
            )
            for name in live.WRAPPER_REJECTION_CLASSES
        },
        "schema": "gate3-codex-wrapper-corpus-scan.v1",
        "sessions_with_exec_calls": sessions,
    }
    if aggregate_only:
        report["aggregate_only"] = True
        return report
    report["by_cli_version"] = {
        version: {"accepted": accepted.get(version, 0), "total": count}
        for version, count in sorted(totals.items())
    }
    report["rejected_signatures"] = retained
    report["below_threshold"] = {
        "distinct_signatures": len(below),
        "total_count": sum(entry["count"] for entry in below),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-root", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--min-signature-count",
        type=int,
        default=DEFAULT_MIN_SIGNATURE_COUNT,
        help=(
            "fold signatures seen fewer than this many times into a "
            "count-only bucket, so no class rests on a handful of sessions"
        ),
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help=(
            "drop the per-version and per-signature breakdowns; use this "
            "shape if a report is ever reviewed for publication"
        ),
    )
    args = parser.parse_args(argv)
    if not args.sessions_root.is_dir():
        raise SystemExit("sessions root is not a directory")
    if args.min_signature_count < 1:
        raise SystemExit("minimum signature count must be at least 1")
    report = scan(
        args.sessions_root,
        min_signature_count=args.min_signature_count,
        aggregate_only=args.aggregate_only,
    )
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    violations = live._privacy_violations(encoded.encode("utf-8"))
    if violations:
        raise SystemExit(f"corpus report is not privacy-safe: {violations}")
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
