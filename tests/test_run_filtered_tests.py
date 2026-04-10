"""
Tests for governance_tools/run_filtered_tests.py — E2+ enforcement layer.

These tests verify that:
- --dry-run resolves the k_expression from registry (not hand-written)
- The resolved command includes the generated -k string
- The resolved command matches what live exclusion_registry_tool would produce
- Passthrough args after -- are appended to the pytest command
- --format json produces parseable output in dry-run mode
- Missing registry exits with code 2
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.run_filtered_tests import build_pytest_command, main
from governance_tools.exclusion_registry_tool import (
    load_registry,
    generate_filter,
)

REAL_REGISTRY = Path(__file__).parent.parent / "governance" / "test_exclusion_registry.yaml"


# ── build_pytest_command ──────────────────────────────────────────────────────

def test_build_command_includes_k_expression():
    cmd = build_pytest_command("not foo and not bar", test_paths=["tests/"], extra_args=[])
    assert "-k" in cmd
    idx = cmd.index("-k")
    assert cmd[idx + 1] == "not foo and not bar"


def test_build_command_includes_test_path():
    cmd = build_pytest_command("not foo", test_paths=["tests/"], extra_args=[])
    assert "tests/" in cmd


def test_build_command_appends_passthrough():
    cmd = build_pytest_command("not foo", test_paths=["tests/"], extra_args=["-v", "--tb=short"])
    assert "-v" in cmd
    assert "--tb=short" in cmd


def test_build_command_no_k_when_empty_expression():
    cmd = build_pytest_command("", test_paths=["tests/"], extra_args=[])
    assert "-k" not in cmd


# ── dry-run mode ──────────────────────────────────────────────────────────────

def test_dry_run_exits_zero(capsys):
    rc = main(["--dry-run"])
    assert rc == 0


def test_dry_run_human_output_shows_k_expression(capsys):
    main(["--dry-run"])
    out = capsys.readouterr().out
    assert "k_expression" in out
    assert "trust_signal" in out  # real registry has trust_signal exclusion


def test_dry_run_json_output_is_parseable(capsys):
    rc = main(["--dry-run", "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "command" in data
    assert "k_expression" in data
    assert data["active_exclusions"] >= 9


def test_dry_run_command_matches_registry_output(capsys):
    """The -k string baked into the command must match what exclusion_registry_tool produces."""
    main(["--dry-run", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)

    entries = load_registry(REAL_REGISTRY)
    expected_k = generate_filter(entries, warn_expired=False)

    assert data["k_expression"] == expected_k, (
        "run_filtered_tests k_expression must match registry generate-filter output"
    )


def test_dry_run_with_passthrough_args(capsys):
    rc = main(["--dry-run", "--", "-v", "--tb=short"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "-v" in out or "verbose" in out or "-v" in str(out)


# ── missing registry ──────────────────────────────────────────────────────────

def test_missing_registry_exits_2(tmp_path):
    fake_registry = str(tmp_path / "nonexistent.yaml")
    rc = main(["--registry", fake_registry, "--dry-run"])
    assert rc == 2


# ── k_expression is never empty for real registry ─────────────────────────────

def test_real_registry_produces_non_empty_k_in_dry_run(capsys):
    main(["--dry-run", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["k_expression"], "k_expression must not be empty — registry has active entries"


# ── enforcement contract ──────────────────────────────────────────────────────

def test_k_expression_contains_all_active_patterns(capsys):
    """Every active pattern in the registry must appear in the k_expression."""
    from governance_tools.exclusion_registry_tool import load_registry
    entries = load_registry(REAL_REGISTRY)
    active_patterns = [e.pattern for e in entries if e.active]

    main(["--dry-run", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    k = data["k_expression"]

    for pattern in active_patterns:
        assert pattern in k, (
            f"Active pattern {pattern!r} not found in generated k_expression. "
            "Registry may not be fully enforced."
        )
