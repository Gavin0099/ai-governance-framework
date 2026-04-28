from __future__ import annotations

import json
import shutil
from pathlib import Path

from governance_tools.authority_rollout_policy import (
    DEFAULT_POLICY_MODE,
    STRICT_POLICY_MODE,
    resolve_authority_rollout_policy,
)


def _tmp_dir(name: str) -> Path:
    path = Path("tests") / "_tmp_authority_rollout_policy" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_default_is_compatibility_mode():
    project_root = _tmp_dir("default_compatibility")
    policy = resolve_authority_rollout_policy(project_root=project_root)

    assert policy.require_register is False
    assert policy.policy_mode == DEFAULT_POLICY_MODE
    assert policy.policy_source == "default_compatibility"
    assert policy.explicit_override is False


def test_policy_file_can_enable_strict_mode():
    project_root = _tmp_dir("policy_file_strict")
    policy_file = project_root / "artifacts" / "governance" / "authority-rollout-policy.json"
    policy_file.parent.mkdir(parents=True, exist_ok=True)
    policy_file.write_text(
        json.dumps({"policy_mode": STRICT_POLICY_MODE}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    policy = resolve_authority_rollout_policy(project_root=project_root)

    assert policy.require_register is True
    assert policy.policy_mode == STRICT_POLICY_MODE
    assert policy.policy_source == "policy_file"
    assert policy.explicit_override is False


def test_explicit_override_wins_over_policy_file():
    project_root = _tmp_dir("explicit_override_precedence")
    policy_file = project_root / "artifacts" / "governance" / "authority-rollout-policy.json"
    policy_file.parent.mkdir(parents=True, exist_ok=True)
    policy_file.write_text(
        json.dumps({"policy_mode": STRICT_POLICY_MODE}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    policy = resolve_authority_rollout_policy(
        project_root=project_root,
        require_register_override=False,
    )

    assert policy.require_register is False
    assert policy.policy_mode == DEFAULT_POLICY_MODE
    assert policy.policy_source == "explicit_override"
    assert policy.explicit_override is True
