from __future__ import annotations

import textwrap
from datetime import date as _date
from pathlib import Path

from governance_tools.external_repo_smoke import format_human, infer_smoke_rules, run_external_repo_smoke


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_infer_smoke_rules_includes_common_and_external_pack(tmp_path: Path) -> None:
    rules_root = tmp_path / "rules"
    _write(rules_root / "firmware" / "safety.md", "# Firmware safety\n")

    rules = infer_smoke_rules({"rule_roots": [str(rules_root)]})

    assert rules == ["common", "firmware"]


def test_run_external_repo_smoke_succeeds_for_valid_external_contract(tmp_path: Path) -> None:
    _write(
        tmp_path / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(tmp_path / "AGENTS.md", "# Agents\n")
    _write(tmp_path / "CHECKLIST.md", "# Checklist\n")
    _write(tmp_path / "rules" / "firmware" / "safety.md", "# Firmware safety\n")
    _write(tmp_path / "validators" / "check.py", "def x():\n    return True\n")
    _write(
        tmp_path / "contract.yaml",
        "\n".join(
            [
                "name: sample-contract",
                "domain: firmware",
                "documents:",
                "  - CHECKLIST.md",
                "ai_behavior_override:",
                "  - AGENTS.md",
                "rule_roots:",
                "  - rules",
                "validators:",
                "  - validators/check.py",
            ]
        ),
    )

    result = run_external_repo_smoke(tmp_path)

    assert result.ok is True
    assert result.rules == ["common", "firmware"]
    assert result.pre_task_ok is True
    assert result.session_start_ok is True
    assert result.post_task_ok is None


def test_run_external_repo_smoke_replays_compliant_post_task_fixture(tmp_path: Path) -> None:
    _write(
        tmp_path / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(tmp_path / "AGENTS.md", "# Agents\n")
    _write(tmp_path / "CHECKLIST.md", "# Checklist\n")
    _write(tmp_path / "rules" / "firmware" / "safety.md", "# Firmware safety\n")
    _write(
        tmp_path / "validators" / "check.py",
        textwrap.dedent(
            """
            from governance_tools.validator_interface import DomainValidator, ValidatorResult

            class CheckValidator(DomainValidator):
                @property
                def rule_ids(self):
                    return ["firmware"]

                def validate(self, payload):
                    ok = bool((payload.get("checks") or {}).get("validator_ok"))
                    return ValidatorResult(
                        ok=ok,
                        rule_ids=self.rule_ids,
                        warnings=[] if ok else ["validator did not approve payload"],
                    )
            """
        ).strip()
        + "\n",
    )
    _write(
        tmp_path / "contract.yaml",
        "\n".join(
            [
                "name: sample-contract",
                "domain: firmware",
                "documents:",
                "  - CHECKLIST.md",
                "ai_behavior_override:",
                "  - AGENTS.md",
                "rule_roots:",
                "  - rules",
                "validators:",
                "  - validators/check.py",
            ]
        ),
    )
    _write(
        tmp_path / "fixtures" / "post_task_response.txt",
        "\n".join(
            [
                "[Governance Contract]",
                "LANG = C++",
                "LEVEL = L2",
                "SCOPE = feature",
                "PLAN = PLAN.md",
                "LOADED = SYSTEM_PROMPT, HUMAN-OVERSIGHT",
                "CONTEXT = repo -> firmware smoke; NOT: platform rewrite",
                "PRESSURE = SAFE (20/200)",
                "RULES = common,firmware",
                "RISK = medium",
                "OVERSIGHT = review-required",
                "MEMORY_MODE = candidate",
            ]
        )
        + "\n",
    )
    _write(
        tmp_path / "fixtures" / "smoke_compliant.checks.json",
        "\n".join(
            [
                "{",
                '  "warnings": [],',
                '  "errors": [],',
                '  "validator_ok": true,',
                '  "test_names": ["firmware_tests::test_failure_cleanup_path"],',
                '  "exception_verified": true,',
                '  "cleanup_verified": true',
                "}",
            ]
        )
        + "\n",
    )

    result = run_external_repo_smoke(tmp_path)

    assert result.ok is True
    assert result.post_task_ok is True
    assert len(result.post_task_cases) == 1
    assert result.post_task_cases[0]["ok"] is True
    assert result.post_task_cases[0]["domain_validator_count"] == 1


def test_run_external_repo_smoke_fails_for_missing_external_rule_pack(tmp_path: Path) -> None:
    _write(
        tmp_path / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(
        tmp_path / "contract.yaml",
        "\n".join(
            [
                "name: broken-contract",
                "rule_roots:",
                "  - missing-rules",
            ]
        ),
    )

    result = run_external_repo_smoke(tmp_path)

    assert result.ok is False
    assert result.pre_task_ok is False or result.session_start_ok is False
    assert any("Unknown rule packs" in item or "PLAN.md" not in item for item in result.errors)


def test_format_human_uses_shared_summary_shape(tmp_path: Path) -> None:
    _write(
        tmp_path / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(tmp_path / "AGENTS.md", "# Agents\n")
    _write(tmp_path / "CHECKLIST.md", "# Checklist\n")
    _write(tmp_path / "rules" / "firmware" / "safety.md", "# Firmware safety\n")
    _write(
        tmp_path / "contract.yaml",
        "\n".join(
            [
                "name: sample-contract",
                "domain: firmware",
                "documents:",
                "  - CHECKLIST.md",
                "ai_behavior_override:",
                "  - AGENTS.md",
                "rule_roots:",
                "  - rules",
            ]
        ),
    )

    result = run_external_repo_smoke(tmp_path)
    output = format_human(result)

    assert "[external_repo_smoke]" in output
    assert "summary=ok=True | rules=common,firmware | pre_task_ok=True | session_start_ok=True | post_task_ok=None" in output
    assert f"contract_path={tmp_path / 'contract.yaml'}" in output
