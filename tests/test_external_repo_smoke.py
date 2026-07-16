from __future__ import annotations

import shutil
import subprocess
import textwrap
import json
from datetime import date as _date
from pathlib import Path

import pytest
import yaml

from governance_tools.external_repo_smoke import (
    FrameworkIdentity,
    _framework_identity,
    format_human,
    format_json,
    infer_smoke_rules,
    run_external_repo_smoke,
    write_json_result,
)
import governance_tools.external_repo_smoke as external_repo_smoke


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


@pytest.fixture(autouse=True)
def _clean_framework_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    root = Path(external_repo_smoke.__file__).resolve().parent.parent
    monkeypatch.setattr(
        external_repo_smoke,
        "_framework_identity",
        lambda: FrameworkIdentity(
            root=str(root),
            commit="0" * 40,
            worktree_clean=True,
            worktree_changes=[],
        ),
    )


def _make_git_framework(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    _write(path / "governance_tools" / "base.py", "VALUE = 1\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "framework fixture"], cwd=path, check=True, stdout=subprocess.PIPE)
    return path


def _assert_dirty_framework_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    smoke_root: Path,
    identity: FrameworkIdentity,
) -> None:
    monkeypatch.setattr(external_repo_smoke, "_framework_identity", lambda: identity)
    result = run_external_repo_smoke(smoke_root)
    assert result.ok is False
    assert result.framework_worktree_clean is False
    assert any("refusing attributable smoke evidence" in item for item in result.errors)


def test_tracked_dirty_framework_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    framework = _make_git_framework(tmp_path / "framework")
    _write(framework / "governance_tools" / "base.py", "VALUE = 2\n")

    identity = _framework_identity(framework)

    assert identity.worktree_clean is False
    assert any(item.startswith(" M ") for item in identity.worktree_changes)
    _assert_dirty_framework_fails_closed(monkeypatch, tmp_path / "consumer", identity)


def test_staged_dirty_framework_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    framework = _make_git_framework(tmp_path / "framework")
    _write(framework / "governance_tools" / "base.py", "VALUE = 2\n")
    subprocess.run(["git", "add", "governance_tools/base.py"], cwd=framework, check=True)

    identity = _framework_identity(framework)

    assert identity.worktree_clean is False
    assert any(item.startswith("M  ") for item in identity.worktree_changes)
    _assert_dirty_framework_fails_closed(monkeypatch, tmp_path / "consumer", identity)


def test_untracked_importable_framework_code_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    framework = _make_git_framework(tmp_path / "framework")
    _write(framework / "governance_tools" / "untracked_plugin.py", "ENABLED = True\n")

    identity = _framework_identity(framework)

    assert identity.worktree_clean is False
    assert any(
        item.startswith("?? ") and "governance_tools/untracked_plugin.py" in item.replace("\\", "/")
        for item in identity.worktree_changes
    )
    _assert_dirty_framework_fails_closed(monkeypatch, tmp_path / "consumer", identity)


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


def test_format_json_includes_schema_and_generated_at(smoke_root: Path) -> None:
    _write_version_manifest(smoke_root)
    _write(
        smoke_root / "PLAN.md",
        f"> **最後更新**: {_date.today().isoformat()}\n> **Owner**: tester\n> **Freshness**: Sprint (7d)\n",
    )
    _write(smoke_root / "AGENTS.md", "# Agents\n")
    _write(
        smoke_root / "contract.yaml",
        "\n".join(
            [
                "name: sample-contract",
                "domain: firmware",
            ]
        ),
    )

    result = run_external_repo_smoke(smoke_root)
    payload = json.loads(format_json(result))

    assert payload["result_schema"] == "external_repo_smoke_result.v0.2"
    assert payload["generated_at"].endswith("Z")
    assert payload["ok"] is True
    assert payload["repo_root"] == str(smoke_root.resolve())


def test_write_json_result_persists_parseable_attributable_evidence(smoke_root: Path) -> None:
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

    output = write_json_result(result, smoke_root / "artifacts" / "evidence" / "test-results" / "external-runtime-smoke.json")

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["result_schema"] == "external_repo_smoke_result.v0.2"
    assert payload["repo_root"] == str(smoke_root.resolve())
    assert payload["ok"] is True
    assert payload["framework_worktree_clean"] is True
    assert payload["framework_worktree_changes"] == []


def test_run_external_repo_smoke_fails_on_gitlab_adapter_scope_mismatch(smoke_root: Path) -> None:
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
    _write(
        smoke_root / "lib" / "adapters" / "gitlab-wiki-adapter.ts",
        "\n".join(
            [
                "export class GitLabWikiAdapter {",
                "  async listPages(opts = {}) {",
                "    const projectId = opts.projectId?.toString() ?? this.projectId;",
                "    return [];",
                "  }",
                "  async _fetchPage(slug: string) {",
                "    const url = `${this.baseUrl}/api/v4/projects/${encodeURIComponent(this.projectId)}/wikis/${encodeURIComponent(slug)}`;",
                "    return url;",
                "  }",
                "}",
            ]
        )
        + "\n",
    )

    result = run_external_repo_smoke(smoke_root)

    assert result.ok is False
    assert any("gitlab-adapter-scope:" in item for item in result.errors)
