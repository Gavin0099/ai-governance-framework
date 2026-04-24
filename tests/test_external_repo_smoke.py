from __future__ import annotations

import shutil
import textwrap
from datetime import date as _date
from pathlib import Path

import pytest
import yaml

from governance_tools.external_repo_smoke import format_human, infer_smoke_rules, run_external_repo_smoke


FIXTURE_ROOT = Path("tests/_tmp_external_repo_smoke")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def smoke_root(request):
    path = FIXTURE_ROOT / request.node.name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _write_version_manifest(root: Path, **overrides) -> None:
    defaults = {
        "schema_version": "1.0",
        "governance_version": "0.4.0",
        "contract_schema_version": "1.2.0",
        "runtime_entrypoint_version": "1.1.0",
        "hook_wiring_version": "1.0.0",
        "artifact_layout_version": "1.0.0",
        "memory_layout_version": "1.0.0",
    }
    path = root / ".governance" / "version_manifest.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump({**defaults, **overrides}), encoding="utf-8")


def test_infer_smoke_rules_includes_common_and_external_pack(smoke_root: Path) -> None:
    rules_root = smoke_root / "rules"
    _write(rules_root / "firmware" / "safety.md", "# Firmware safety\n")

    rules = infer_smoke_rules({"rule_roots": [str(rules_root)]})

    assert rules == ["common", "firmware"]


def test_run_external_repo_smoke_succeeds_for_valid_external_contract(smoke_root: Path) -> None:
    _write_version_manifest(smoke_root)
    _write(
        smoke_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(smoke_root / "AGENTS.md", "# Agents\n")
    _write(smoke_root / "CHECKLIST.md", "# Checklist\n")
    _write(smoke_root / "rules" / "firmware" / "safety.md", "# Firmware safety\n")
    _write(smoke_root / "validators" / "check.py", "def x():\n    return True\n")
    _write(
        smoke_root / "contract.yaml",
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

    result = run_external_repo_smoke(smoke_root)

    assert result.ok is True
    assert result.rules == ["common", "firmware"]
    assert result.pre_task_ok is True
    assert result.session_start_ok is True
    assert result.post_task_ok is None


def test_run_external_repo_smoke_replays_compliant_post_task_fixture(smoke_root: Path) -> None:
    _write_version_manifest(smoke_root)
    _write(
        smoke_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(smoke_root / "AGENTS.md", "# Agents\n")
    _write(smoke_root / "CHECKLIST.md", "# Checklist\n")
    _write(smoke_root / "rules" / "firmware" / "safety.md", "# Firmware safety\n")
    _write(
        smoke_root / "validators" / "check.py",
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
        smoke_root / "contract.yaml",
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
        smoke_root / "fixtures" / "post_task_response.txt",
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
        smoke_root / "fixtures" / "smoke_compliant.checks.json",
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

    result = run_external_repo_smoke(smoke_root)

    assert result.ok is True
    assert result.post_task_ok is True
    assert len(result.post_task_cases) == 1
    assert result.post_task_cases[0]["ok"] is True
    assert result.post_task_cases[0]["domain_validator_count"] == 1


def test_run_external_repo_smoke_fails_for_missing_external_rule_pack(smoke_root: Path) -> None:
    _write(
        smoke_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(
        smoke_root / "contract.yaml",
        "\n".join(
            [
                "name: broken-contract",
                "rule_roots:",
                "  - missing-rules",
            ]
        ),
    )

    result = run_external_repo_smoke(smoke_root)

    assert result.ok is False
    assert result.pre_task_ok is False or result.session_start_ok is False
    assert any("Unknown rule packs" in item or "PLAN.md" not in item for item in result.errors)


def test_format_human_uses_shared_summary_shape(smoke_root: Path) -> None:
    _write_version_manifest(smoke_root)
    _write(
        smoke_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(smoke_root / "AGENTS.md", "# Agents\n")
    _write(smoke_root / "CHECKLIST.md", "# Checklist\n")
    _write(smoke_root / "rules" / "firmware" / "safety.md", "# Firmware safety\n")
    _write(
        smoke_root / "contract.yaml",
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

    result = run_external_repo_smoke(smoke_root)
    output = format_human(result)

    assert "[external_repo_smoke]" in output
    assert "summary=ok=True | rules=common,firmware | pre_task_ok=True | session_start_ok=True | post_task_ok=None" in output
    assert f"contract_path={(smoke_root / 'contract.yaml').resolve()}" in output
