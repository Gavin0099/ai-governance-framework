"""
Regression tests for issue #219 (part B).

B1: governance.yml declares a least-privilege top-level GITHUB_TOKEN scope.
B2: every third-party action is pinned to a full commit SHA with a version
    comment, and Dependabot keeps those pins current.

These are static checks so they run locally even when CI is unavailable; the
SHAs themselves were verified against each action's release tags with gh api
when they were pinned.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))
_PINNED = re.compile(r"^[\w.-]+/[\w.-]+(?:/[\w./-]+)?@[0-9a-f]{40}$")
_USES_LINE = re.compile(r"^\s*-?\s*uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
_VERSION_COMMENT = re.compile(r"^\s+#\s+v\d+\.\d+\.\d+\s*$")


def _uses_lines(path: Path) -> list[tuple[int, str, str]]:
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = _USES_LINE.match(line)
        if match:
            found.append((number, match.group("ref"), match.group("rest")))
    return found


def test_workflows_are_present():
    names = {path.name for path in WORKFLOWS}
    assert {"governance.yml", "docs-pages.yml"} <= names


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_remote_action_is_pinned_to_a_full_sha_with_version_comment(workflow):
    lines = _uses_lines(workflow)
    assert lines, f"{workflow.name} has no uses: lines"
    for number, ref, rest in lines:
        if ref.startswith("./") or ref.startswith("docker://"):
            continue  # local actions and image digests are out of scope
        assert _PINNED.match(ref), f"{workflow.name}:{number} not pinned to a SHA: {ref}"
        assert _VERSION_COMMENT.match(rest), f"{workflow.name}:{number} missing '# vX.Y.Z': {rest!r}"


def test_one_sha_per_action_version_across_workflows():
    seen: dict[tuple[str, str], str] = {}
    for workflow in WORKFLOWS:
        for number, ref, rest in _uses_lines(workflow):
            if "@" not in ref or not _VERSION_COMMENT.match(rest):
                continue
            action, sha = ref.split("@", 1)
            key = (action, rest.strip().lstrip("#").strip())
            assert seen.setdefault(key, sha) == sha, (
                f"{workflow.name}:{number} pins {key} to {sha}, elsewhere {seen[key]}"
            )


def test_governance_workflow_token_is_read_only():
    workflow = yaml.safe_load((REPO / ".github/workflows/governance.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "read"}
    for name, job in workflow["jobs"].items():
        scopes = job.get("permissions") or {}
        if isinstance(scopes, str):
            assert scopes in {"read-all", "{}"}, f"job {name} widens token: {scopes}"
            continue
        writes = {scope for scope, level in scopes.items() if level == "write"}
        assert not writes, f"job {name} requests write scopes {writes}"


def test_dependabot_tracks_github_actions():
    config = yaml.safe_load((REPO / ".github/dependabot.yml").read_text(encoding="utf-8"))
    assert config["version"] == 2
    actions = [u for u in config["updates"] if u["package-ecosystem"] == "github-actions"]
    assert len(actions) == 1
    assert actions[0]["directory"] == "/"
    assert actions[0]["schedule"]["interval"] in {"daily", "weekly", "monthly"}
