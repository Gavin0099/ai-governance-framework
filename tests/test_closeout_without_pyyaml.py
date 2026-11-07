"""The formal closeout runs, with the same policy, in a Python without PyYAML.

A consumer's Codex Stop hook may resolve the consumer's own virtualenv, which
need not have PyYAML. The two framework-shipped policies on the closeout path
therefore have JSON twins that are read only without PyYAML.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.test_shared_closeout_ownership import prepare, repo as protected_repo  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "governance_tools/session_closeout_entry.py"
TWINS = [
    ROOT / "governance/runtime/runtime_phase_policy.yaml",
    ROOT / "governance/gate_policy.yaml",
]
# Prepended to a child interpreter: every `import yaml` then raises ImportError.
NO_YAML = "import sys; sys.modules['yaml'] = None\n"


@pytest.mark.parametrize("source", TWINS, ids=lambda p: p.name)
def test_json_twin_matches_its_yaml_policy(source: Path) -> None:
    twin = source.with_suffix(".json")
    canonical = lambda data: json.dumps(data, sort_keys=True)  # True vs 1, 3 vs 3.0 stay distinct
    assert canonical(json.loads(twin.read_text(encoding="utf-8"))) == canonical(
        yaml.safe_load(source.read_text(encoding="utf-8"))), (
        f"{twin.name} differs from {source.name}; regenerate it with: python -c \"import json,yaml,pathlib; "
        f"p=pathlib.Path('{source.relative_to(ROOT).as_posix()}'); "
        "p.with_suffix('.json').write_text(json.dumps(yaml.safe_load(p.read_text(encoding='utf-8')), "
        "indent=2, ensure_ascii=False) + '\\n', encoding='utf-8')\""
    )


def _child(code: str, *, block_yaml: bool) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", (NO_YAML if block_yaml else "") + code],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=60,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(ROOT)},
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


POLICY_PROBE = """
import dataclasses, json
from governance_tools import gate_policy, runtime_phase_policy as rp
gate = dataclasses.asdict(gate_policy.load_policy(project_root=None))
print(json.dumps({
    "has_yaml": gate_policy._HAS_YAML,
    "gate": {k: v for k, v in gate.items() if k != "source"},
    "phase_policy": rp.load_runtime_phase_policy(),
    "classification": rp.build_phase_classification(
        action_ids=["canonical_closeout", "memory_candidate_snapshot", "precondition_gate", "unknown"],
        hook="session_end"),
}, default=str))
"""


def test_policies_apply_identically_without_pyyaml() -> None:
    with_yaml = _child(POLICY_PROBE, block_yaml=False)
    without = _child(POLICY_PROBE, block_yaml=True)
    assert with_yaml.pop("has_yaml") is True and without.pop("has_yaml") is False
    assert without == with_yaml
    assert without["gate"]["policy_source"] == "framework_default"
    assert without["gate"]["hook_coverage_tier"] == "A"


def test_repo_local_gate_policy_is_still_refused_without_pyyaml(tmp_path: Path) -> None:
    (tmp_path / "governance").mkdir()
    (tmp_path / "governance/gate_policy.yaml").write_text("fail_mode: strict\n", encoding="utf-8")
    code = (
        "from pathlib import Path\nfrom governance_tools import gate_policy\n"
        "import json\ntry:\n"
        f"    gate_policy.load_policy(project_root=Path({str(tmp_path)!r}))\n"
        "    print(json.dumps({'refused': False}))\n"
        "except RuntimeError as exc:\n"
        "    print(json.dumps({'refused': True, 'message': str(exc)}))\n"
    )
    result = _child(code, block_yaml=True)
    assert result["refused"] is True and "PyYAML is not installed" in result["message"]


def _closeout(repo: Path, *, block_yaml: bool) -> dict:
    code = (
        "import runpy, sys\n"
        f"sys.argv = [{str(ENTRY)!r}, '--project-root', {str(repo)!r}, '--agent-id', 'codex',"
        " '--format', 'json', '--no-ledger-write', '--session-id', 'session-A']\n"
        f"runpy.run_path({str(ENTRY)!r}, run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", (NO_YAML if block_yaml else "") + code],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", cwd=repo, timeout=90,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def _decision_view(repo: Path, out: dict) -> dict:
    """Everything the closeout decided, without paths and times that differ per run."""
    phase = json.loads((repo / "artifacts/governance/runtime_phase_summary.json").read_text(encoding="utf-8"))
    closeout = json.loads((repo / "artifacts/runtime/closeouts/session-A.json").read_text(encoding="utf-8"))
    return {
        "closeout_status": out.get("closeout_status"),
        "ok": out.get("ok"),
        "phase_summary": phase.get("phase_summary"),
        "rules": phase.get("rules"),
        "closeout": {k: v for k, v in closeout.items() if k not in ("closed_at",)},
        "completion": (repo / "artifacts/runtime/closeout-completions/session-A.json").is_file(),
    }


@pytest.fixture
def second_repo(tmp_path_factory):
    # Same shape as the shared ownership fixture, built without pytest internals.
    root = tmp_path_factory.mktemp("second") / "consumer with spaces"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "--quiet",
                    "--allow-empty", "-m", "fixture"], check=True)
    (root / "AGENTS.md").write_text("# fixture\n", encoding="utf-8")
    (root / "governance").mkdir()
    (root / "evidence.txt").write_text("fixture evidence", encoding="utf-8")
    return root.resolve()


def test_formal_closeout_is_valid_and_identical_without_pyyaml(protected_repo, second_repo) -> None:
    prepare(protected_repo, "session-A")
    prepare(second_repo, "session-A")

    with_yaml = _closeout(protected_repo, block_yaml=False)
    without = _closeout(second_repo, block_yaml=True)

    assert without["closeout_status"] == "valid", without
    assert _decision_view(second_repo, without) == _decision_view(protected_repo, with_yaml)
    owner = json.loads((second_repo / "artifacts/runtime/shared-closeout/owner.json").read_text(encoding="utf-8"))
    assert owner["state"] == "RELEASED"
