from __future__ import annotations

from pathlib import Path

from governance_tools.phase3_gate_adoption_audit import audit_phase3_gate_adoption


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_adoption_audit_passes_with_only_canonical_modules(tmp_path):
    _write(
        tmp_path / "governance_tools" / "phase2_aggregation_consumer.py",
        "current_state='closure_verified'\n",
    )
    _write(
        tmp_path / "governance_tools" / "phase3_promotion_gate.py",
        "phase3_entry_allowed=True\ncurrent_state='closure_verified'\npromote_eligible=True\n",
    )
    _write(
        tmp_path / "scripts" / "phase2_aggregation_dry_run.py",
        "expected='closure_verified'\n",
    )

    result = audit_phase3_gate_adoption(tmp_path)
    assert result["ok"] is True
    assert result["violations"] == []


def test_adoption_audit_flags_noncanonical_closure_verified_usage(tmp_path):
    _write(
        tmp_path / "governance_tools" / "phase2_aggregation_consumer.py",
        "current_state='closure_verified'\n",
    )
    _write(
        tmp_path / "governance_tools" / "phase3_promotion_gate.py",
        "phase3_entry_allowed=True\n",
    )
    _write(
        tmp_path / "governance_tools" / "legacy_phase3_logic.py",
        "if state == 'closure_verified':\n    allowed=True\n",
    )

    result = audit_phase3_gate_adoption(tmp_path)
    assert result["ok"] is False
    assert any(v["rule"] == "closure_verified_outside_canonical_modules" for v in result["violations"])


def test_adoption_audit_flags_parallel_phase3_logic(tmp_path):
    _write(
        tmp_path / "governance_tools" / "phase2_aggregation_consumer.py",
        "current_state='closure_verified'\n",
    )
    _write(
        tmp_path / "governance_tools" / "phase3_promotion_gate.py",
        "phase3_entry_allowed=True\n",
    )
    _write(
        tmp_path / "scripts" / "manual_promotion.py",
        "def f(p):\n"
        "  current_state=p.get('current_state')\n"
        "  promote_eligible=p.get('promote_eligible')\n"
        "  # phase3 promotion logic\n"
        "  return current_state=='closure_verified' and promote_eligible\n",
    )

    result = audit_phase3_gate_adoption(tmp_path)
    assert result["ok"] is False
    assert any(v["rule"] == "potential_parallel_phase3_decision_logic" for v in result["violations"])


def test_adoption_audit_flags_workflow_phase3_terms_without_canonical_gate(tmp_path):
    _write(
        tmp_path / ".github" / "workflows" / "governance.yml",
        "name: governance\njobs:\n  x:\n    steps:\n      - run: echo phase3_entry_allowed\n",
    )
    _write(tmp_path / "governance_tools" / "phase3_promotion_gate.py", "phase3_entry_allowed=True\n")
    _write(tmp_path / "governance_tools" / "phase2_aggregation_consumer.py", "current_state='closure_verified'\n")

    result = audit_phase3_gate_adoption(tmp_path)
    assert result["ok"] is False
    assert any(v["rule"] == "workflow_phase3_terms_without_canonical_gate" for v in result["violations"])


def test_adoption_audit_flags_doc_bypass_phrases(tmp_path):
    _write(tmp_path / "governance_tools" / "phase3_promotion_gate.py", "phase3_entry_allowed=True\n")
    _write(tmp_path / "governance_tools" / "phase2_aggregation_consumer.py", "current_state='closure_verified'\n")
    _write(tmp_path / "docs" / "bad.md", "Please skip phase3 gate when urgent.")

    result = audit_phase3_gate_adoption(tmp_path)
    assert result["ok"] is False
    assert any(v["rule"] == "doc_mentions_promotion_bypass" for v in result["violations"])


def test_adoption_audit_passes_current_repo():
    repo_root = Path(__file__).resolve().parents[1]
    result = audit_phase3_gate_adoption(repo_root)
    assert result["ok"] is True, result["violations"]
