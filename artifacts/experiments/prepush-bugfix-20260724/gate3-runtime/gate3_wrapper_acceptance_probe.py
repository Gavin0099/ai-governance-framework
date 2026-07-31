"""Offline probe for the frozen route's tool-input wrapper acceptance set.

The live canary rejects any tool call whose input does not match
``SHELL_WRAPPER_RE`` or ``PATCH_WRAPPER_RE``. Each live pair costs one
authorization and, historically, surfaced a single rejected shape. This probe
answers the same question offline: given wrapper shapes the Codex CLI is known
to emit, which ones does the frozen route accept, and how does the failure-path
classifier describe the ones it rejects?

The probe never runs a session, never touches credentials, and never reads a
rollout. Its variants are written here by hand; it is evidence about the
acceptance set, not evidence about any particular live run.

Usage:
    python gate3_wrapper_acceptance_probe.py --out <report.json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate3_codex_live_canary as live  # noqa: E402

WORKSPACE = "C:/workspace"
COMMAND = "git rev-parse HEAD"


def _shell(body: str) -> str:
    return f"const r = await tools.shell_command({{{body}}}); text(r)\n"


def _variants() -> list[tuple[str, str, str]]:
    """Return (variant_id, rationale, tool input) triples.

    The rationale records why the shape is plausible, so a reader can judge
    whether a rejection is a real gap or a shape nobody would emit.
    """
    command = json.dumps(COMMAND)
    workdir = json.dumps(WORKSPACE)
    return [
        (
            "frozen_shell",
            "the exact shape the frozen route pins",
            _shell(f"command:{command},workdir:{workdir}"),
        ),
        (
            "frozen_patch",
            "the exact patch shape the frozen route pins",
            'const patch = "*** Begin Patch\\n*** End Patch\\n";\n'
            "text(await tools.apply_patch(patch));\n",
        ),
        (
            "field_timeout_ms",
            "timeout_ms is a documented shell_command field",
            _shell(f"command:{command},workdir:{workdir},timeout_ms:120000"),
        ),
        (
            "field_justification",
            "justification is emitted when a command needs escalation",
            _shell(
                f"command:{command},workdir:{workdir},justification:"
                + json.dumps("read the current commit")
            ),
        ),
        (
            "field_sandbox_permissions",
            "sandbox_permissions is emitted under some approval policies",
            _shell(
                f"command:{command},workdir:{workdir},sandbox_permissions:[]"
            ),
        ),
        (
            "field_login",
            "login is emitted by some shell wrappers",
            _shell(f"command:{command},workdir:{workdir},login:false"),
        ),
        (
            "field_prefix_rule",
            "prefix_rule is emitted alongside prefix-based approvals",
            _shell(
                f"command:{command},workdir:{workdir},prefix_rule:"
                + json.dumps("git")
            ),
        ),
        (
            "order_workdir_first",
            "object key order is not guaranteed by the emitter",
            _shell(f"workdir:{workdir},command:{command}"),
        ),
        (
            "spacing_after_colon",
            "a space after the key colon is ordinary formatting variance",
            _shell(f"command: {command}, workdir: {workdir}"),
        ),
        (
            "quoted_keys",
            "quoted object keys are valid JS and a plausible emission",
            _shell(f'"command":{command},"workdir":{workdir}'),
        ),
        (
            "variable_named_result",
            "the result variable name is arbitrary",
            f"const result = await tools.shell_command({{command:{command},"
            f"workdir:{workdir}}}); text(result)\n",
        ),
        (
            "direct_text_await",
            "the result can be passed straight into text()",
            f"text(await tools.shell_command({{command:{command},"
            f"workdir:{workdir}}}));\n",
        ),
        (
            "trailing_semicolon",
            "a trailing semicolon after text(r) is ordinary formatting",
            f"const r = await tools.shell_command({{command:{command},"
            f"workdir:{workdir}}}); text(r);\n",
        ),
        (
            "no_workdir",
            "workdir is omitted when the default cwd is used",
            _shell(f"command:{command}"),
        ),
    ]


def _classify(source: str) -> dict[str, Any]:
    accepted = bool(
        live.SHELL_WRAPPER_RE.fullmatch(source)
        or live.PATCH_WRAPPER_RE.fullmatch(source)
    )
    entry: dict[str, Any] = {"accepted": accepted}
    if not accepted:
        entry["classification"] = live._tool_input_wrapper_diagnostic(source)
    return entry


def build_report() -> dict[str, Any]:
    results = []
    for variant_id, rationale, source in _variants():
        results.append(
            {
                "variant_id": variant_id,
                "rationale": rationale,
                **_classify(source),
            }
        )
    accepted = [entry["variant_id"] for entry in results if entry["accepted"]]
    rejected = [
        entry["variant_id"] for entry in results if not entry["accepted"]
    ]
    return {
        "accepted_variants": accepted,
        "authorization_cost": "none: offline probe, no session invoked",
        "boundary": (
            "Variants are hand-written plausible shapes, not observed "
            "emissions. A rejection here proves the acceptance set is "
            "narrower than the variant, not that the CLI emits it."
        ),
        "rejected_variants": rejected,
        "results": results,
        "schema": "gate3-codex-wrapper-acceptance-probe.v1",
        "variant_count": len(results),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = build_report()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    violations = live._privacy_violations(encoded.encode("utf-8"))
    if violations:
        raise SystemExit(f"probe report is not privacy-safe: {violations}")
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
