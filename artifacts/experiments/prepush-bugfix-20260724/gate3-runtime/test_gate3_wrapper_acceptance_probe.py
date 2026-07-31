"""Characterization tests for the offline wrapper acceptance probe.

These lock in what the frozen route accepts today. If a change widens or
narrows the acceptance set, these fail and force the decision to be explicit
rather than discovered by a live canary pair.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate3_codex_live_canary as live  # noqa: E402
import gate3_wrapper_acceptance_probe as probe  # noqa: E402


def test_only_the_two_frozen_shapes_are_accepted() -> None:
    report = probe.build_report()
    assert report["accepted_variants"] == ["frozen_shell", "frozen_patch"]


def test_pure_formatting_variance_is_currently_rejected() -> None:
    """The acceptance set is byte-exact, not semantic.

    Key order, spacing, quoted keys, the result variable name and a trailing
    semicolon all change nothing about what the tool call does, yet each is
    rejected. Recorded so the cost of that choice stays visible.
    """
    report = probe.build_report()
    formatting_only = {
        "order_workdir_first",
        "spacing_after_colon",
        "quoted_keys",
        "variable_named_result",
        "trailing_semicolon",
    }
    assert formatting_only <= set(report["rejected_variants"])


def test_allowlisted_field_names_are_not_accepted_fields() -> None:
    """SAFE_TOOL_INPUT_FIELD_NAMES is a census allowlist, not an accept list.

    Every field name the census can report, other than command and workdir,
    is rejected by the wrapper. Keeping these distinct is deliberate: naming a
    field in a receipt must never imply the route admits it.
    """
    report = probe.build_report()
    rejected = set(report["rejected_variants"])
    for name in live.SAFE_TOOL_INPUT_FIELD_NAMES:
        if name in {"command", "workdir"}:
            continue
        assert f"field_{name}" in rejected


def test_every_rejection_is_classified_and_privacy_safe() -> None:
    report = probe.build_report()
    for entry in report["results"]:
        if entry["accepted"]:
            assert "classification" not in entry
            continue
        classification = entry["classification"]
        assert set(classification) == {
            "argument_shape",
            "envelope",
            "field_name_census",
            "frozen_tool_call_token_count",
            "rejection_class",
            "tool_call_token_count",
            "tool_family",
        }
        assert classification["rejection_class"] in live.WRAPPER_REJECTION_CLASSES
    encoded = json.dumps(report, sort_keys=True).encode("utf-8")
    assert live._privacy_violations(encoded) == []


def test_probe_writes_a_report_without_running_a_session(
    tmp_path: Path,
) -> None:
    out = tmp_path / "nested" / "report.json"
    assert probe.main(["--out", str(out)]) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["schema"] == "gate3-codex-wrapper-acceptance-probe.v1"
    assert written["variant_count"] == len(written["results"])
