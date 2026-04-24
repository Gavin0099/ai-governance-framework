from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.agents_calibration_maturity import assess_agents_calibration_maturity


FIXTURE_ROOT = Path("tests/_tmp_agents_calibration_maturity")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scaffold_only_when_all_key_sections_are_na() -> None:
    tmp_path = _reset_fixture("scaffold_only")
    _write(
        tmp_path / "AGENTS.md",
        "\n".join(
            [
                "# AGENTS.md",
                "## Repo-Specific Risk Levels",
                "<!-- governance:key=risk_levels -->",
                "N/A",
                "",
                "## Must-Test Paths",
                "<!-- governance:key=must_test_paths -->",
                "N/A",
                "",
                "## L1 -> L2 Escalation Triggers",
                "<!-- governance:key=escalation_triggers -->",
                "N/A",
                "",
                "## Repo-Specific Forbidden Behaviors",
                "<!-- governance:key=forbidden_behaviors -->",
                "N/A",
            ]
        ),
    )

    result = assess_agents_calibration_maturity(tmp_path)

    assert result.status == "scaffold_only"
    assert result.reason == "all_key_sections_are_NA"
    assert len(result.next_questions) == 4


def test_generic_filled_when_content_has_no_repo_specific_signal() -> None:
    tmp_path = _reset_fixture("generic_filled")
    _write(
        tmp_path / "AGENTS.md",
        "\n".join(
            [
                "# AGENTS.md",
                "## Repo-Specific Risk Levels",
                "<!-- governance:key=risk_levels -->",
                "- HIGH: important code",
                "",
                "## Must-Test Paths",
                "<!-- governance:key=must_test_paths -->",
                "- critical paths",
                "",
                "## L1 -> L2 Escalation Triggers",
                "<!-- governance:key=escalation_triggers -->",
                "- public API changes",
                "",
                "## Repo-Specific Forbidden Behaviors",
                "<!-- governance:key=forbidden_behaviors -->",
                "- don't break production",
            ]
        ),
    )

    result = assess_agents_calibration_maturity(tmp_path)

    assert result.status == "generic_filled"
    assert result.reason == "no_repo_local_paths_commands_or_boundaries_detected"
    assert len(result.next_questions) == 4


def test_repo_specific_minimal_when_path_or_command_detected() -> None:
    tmp_path = _reset_fixture("repo_specific_minimal")
    _write(
        tmp_path / "AGENTS.md",
        "\n".join(
            [
                "# AGENTS.md",
                "## Repo-Specific Risk Levels",
                "<!-- governance:key=risk_levels -->",
                "- HIGH: changes under runtime_hooks/core/ can alter pre-task routing",
                "",
                "## Must-Test Paths",
                "<!-- governance:key=must_test_paths -->",
                "- `python -m pytest -q tests/test_runtime_pre_task_check.py`",
            ]
        ),
    )

    result = assess_agents_calibration_maturity(tmp_path)

    assert result.status == "repo_specific_minimal"
    assert result.reason == "repo_local_paths_commands_or_boundaries_detected"
    assert result.repo_specific_signals


def test_reviewer_verified_requires_explicit_review_signal() -> None:
    tmp_path = _reset_fixture("reviewer_verified")
    _write(
        tmp_path / "AGENTS.md",
        "\n".join(
            [
                "# AGENTS.md",
                "<!-- governance:reviewer_verified -->",
                "## Repo-Specific Forbidden Behaviors",
                "<!-- governance:key=forbidden_behaviors -->",
                "- Do not change Hub -> PD -> Scaler update order",
            ]
        ),
    )
    _write(
        tmp_path / ".governance" / "agents_calibration_review.json",
        json.dumps({"status": "reviewer_verified"}, indent=2),
    )

    result = assess_agents_calibration_maturity(tmp_path)

    assert result.status == "reviewer_verified"
    assert result.reason == "reviewer_verified_signal_present"
    assert result.reviewer_signal is not None
