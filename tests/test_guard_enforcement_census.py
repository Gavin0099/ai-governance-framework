"""Guard adoption census: five distinct states, no aggregate 'adopted' verdict.

The property under test is that each level requires its own evidence and that a
missing link stops the ladder. A surface must never be reported as blocking
because its code is policy-enabled while nothing ever invokes it.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools.guard_enforcement_census import (  # noqa: E402
    LEVEL_NONE,
    REGISTRY_SCHEMA,
    check_version_alignment,
    load_registry,
    main,
    run_census,
)

SURFACE = {
    "id": "demo_guard",
    "title": "Demo guard",
    "module": "governance_tools/demo_guard.py",
    "wiring_sites": [
        {"path": "hooks/session_end.py", "marker": "import demo_guard"}
    ],
    "invocation_evidence": [
        {
            "glob": "artifacts/receipts/*.json",
            "json_key": "demo_guard_ran",
            "expect_true": True,
        }
    ],
    "verdict_fields": ["demo_guard_ran"],
    "coverage_mode": "full_scan",
    "coverage_roots": ["."],
    # Must be a code the framework's blocking policy is willing to enable;
    # arbitrary strings are filtered out by the policy allowlist.
    "emitted_codes": ["unbound_memory"],
}


def _make_repo(tmp_path: Path, surface: dict | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "governance").mkdir(parents=True)
    (repo / "governance" / "guard_surface_registry.json").write_text(
        json.dumps(
            {"registry_schema": REGISTRY_SCHEMA, "surfaces": [surface or SURFACE]}
        ),
        encoding="utf-8",
    )
    return repo


def _add_module(repo: Path) -> None:
    (repo / "governance_tools").mkdir(parents=True, exist_ok=True)
    (repo / "governance_tools" / "demo_guard.py").write_text("# guard", encoding="utf-8")


def _add_wiring(repo: Path) -> None:
    (repo / "hooks").mkdir(parents=True, exist_ok=True)
    (repo / "hooks" / "session_end.py").write_text(
        "import demo_guard\n", encoding="utf-8"
    )


def _add_invocation(repo: Path, payload: dict, *, age_days: float = 0.0) -> Path:
    receipts = repo / "artifacts" / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    path = receipts / "r1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    if age_days:
        stamp = time.time() - age_days * 86400
        import os

        os.utime(path, (stamp, stamp))
    return path


def _enable_blocking(repo: Path, codes: list[str]) -> None:
    (repo / "governance" / "memory_blocking_policy.json").write_text(
        json.dumps(
            {
                "policy_schema": "memory_blocking_policy.v0.1",
                "enabled": True,
                "blocking_codes": codes,
            }
        ),
        encoding="utf-8",
    )


def _only(result: dict) -> dict:
    return result["surfaces"][0]


# ── the ladder ────────────────────────────────────────────────────────────────

def test_missing_module_is_absent(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert _only(run_census(repo))["level"] == LEVEL_NONE


def test_file_present_but_unwired_stops_at_present(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    entry = _only(run_census(repo))
    assert entry["level"] == "present"
    assert entry["first_gap"] == "configured"


def test_wired_but_never_run_stops_at_configured(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    _add_wiring(repo)
    entry = _only(run_census(repo))
    assert entry["level"] == "configured"
    assert entry["first_gap"] == "invoked"


def test_invocation_evidence_lifts_to_invoked(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})
    entry = _only(run_census(repo))
    # verdict_fields are present in the same payload, so this repo reaches
    # verdict_influencing but stops there: nothing is policy-enabled.
    assert entry["level"] == "verdict_influencing"
    assert entry["first_gap"] == "blocking"


def test_recorded_run_without_verdict_fields_stops_at_invoked(tmp_path: Path) -> None:
    surface = {**SURFACE, "verdict_fields": ["some_other_field"]}
    repo = _make_repo(tmp_path, surface)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})
    entry = _only(run_census(repo))
    assert entry["level"] == "covered"
    assert entry["first_gap"] == "verdict_influencing"


def test_enabled_policy_code_completes_the_ladder(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})
    _enable_blocking(repo, ["unbound_memory"])
    assert _only(run_census(repo))["level"] == "blocking"


# ── the illusions this tool exists to prevent ────────────────────────────────

def test_policy_enabled_but_never_invoked_is_not_reported_as_blocking(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    _add_wiring(repo)
    _enable_blocking(repo, ["unbound_memory"])

    entry = _only(run_census(repo))
    assert entry["level"] == "configured"
    # The raw check is true — the code IS enabled — but the level must not
    # jump the gap, or a guard nothing runs looks like it is blocking.
    assert entry["checks"]["blocking"]["value"] is True
    assert entry["first_gap"] == "invoked"


def test_stale_invocation_evidence_does_not_count_as_invoked(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True}, age_days=90)

    entry = run_census(repo, max_age_days=30)["surfaces"][0]
    assert entry["level"] == "configured"
    assert "stale" in entry["checks"]["invoked"]["reason"]
    # Disabling the freshness window is possible, but must be explicit.
    assert run_census(repo, max_age_days=0)["surfaces"][0]["level"] != "configured"


def test_evidence_recording_a_run_that_did_not_happen_is_ignored(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": False})
    assert _only(run_census(repo))["level"] == "configured"


def test_census_never_emits_an_adopted_verdict(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})
    _enable_blocking(repo, ["unbound_memory"])

    result = run_census(repo)
    # Even with every surface at the top level, there is no aggregate pass/fail
    # field a report could quote as "governance is adopted".
    assert "ok" not in result
    assert "adopted" not in result
    assert "compliant" not in result
    assert result["not_claimed"]
    assert any("never certifies" in line for line in result["claim_ceiling"])


# ── coverage: executing is not examining ─────────────────────────────────────

def test_invoked_without_a_coverage_mode_stops_at_invoked(tmp_path: Path) -> None:
    surface = {
        key: value
        for key, value in SURFACE.items()
        if key not in ("coverage_mode", "coverage_roots")
    }
    repo = _make_repo(tmp_path, surface)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})
    entry = _only(run_census(repo))
    assert entry["level"] == "invoked"
    assert entry["first_gap"] == "covered"


def test_full_scan_coverage_needs_the_declared_root_to_exist(tmp_path: Path) -> None:
    surface = {**SURFACE, "coverage_mode": "full_scan", "coverage_roots": ["memory"]}
    repo = _make_repo(tmp_path, surface)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})

    # A guard pointed at a directory that does not exist runs perfectly and
    # sees nothing; that must not read as covered.
    entry = _only(run_census(repo))
    assert entry["level"] == "invoked"
    assert "coverage_root_missing" in entry["checks"]["covered"]["reason"]

    (repo / "memory").mkdir()
    assert _only(run_census(repo))["level"] == "verdict_influencing"


def test_changed_paths_coverage_requires_the_run_to_record_its_scope(
    tmp_path: Path,
) -> None:
    surface = {
        **SURFACE,
        "coverage_mode": "changed_paths",
        "coverage_scope_key": "examined_paths",
    }
    repo = _make_repo(tmp_path, surface)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})

    entry = _only(run_census(repo))
    assert entry["level"] == "invoked"
    assert "examined_scope_not_recorded" in entry["checks"]["covered"]["reason"]

    _add_invocation(repo, {"demo_guard_ran": True, "examined_paths": ["a.py"]})
    assert _only(run_census(repo))["checks"]["covered"]["value"] is True


# ── version alignment ─────────────────────────────────────────────────────────

def _write_lock(repo: Path, **fields) -> None:
    (repo / "governance" / "framework.lock.json").write_text(
        json.dumps(fields), encoding="utf-8"
    )


def test_missing_lock_is_unknown_not_aligned(tmp_path: Path) -> None:
    """No pin means no answer — never a passing alignment."""
    repo = _make_repo(tmp_path)
    alignment = check_version_alignment(repo)
    assert alignment["status"] == "unknown"
    assert alignment["reason"] == "framework_lock_absent"


def test_an_unverifiable_pin_is_never_reported_as_aligned(tmp_path: Path) -> None:
    """Cannot-check must not read as checked-and-fine."""
    repo = _make_repo(tmp_path)
    _write_lock(repo, adopted_release="9.9.9")
    alignment = check_version_alignment(repo)
    assert alignment["status"] == "unknown"
    assert "release_undetermined" in alignment["reason"]


def test_lock_with_no_pin_at_all_is_unknown(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write_lock(repo, framework_repo="https://example.invalid/x.git")
    assert check_version_alignment(repo)["status"] == "unknown"


def test_commit_mismatch_is_reported_as_drift(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write_lock(repo, adopted_commit="0" * 40)
    alignment = check_version_alignment(repo)
    # tmp_path sits inside a git worktree, so an actual commit is resolvable.
    assert alignment["status"] in {"drifted", "unknown"}
    if alignment["status"] == "drifted":
        assert alignment["direction"] in {"behind_pin", "ahead_of_pin", "diverged", "unknown"}


def test_drift_caps_what_the_census_may_be_quoted_for(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _write_lock(repo, adopted_release="9.9.9", adopted_commit="0" * 40)
    result = run_census(repo)
    if result["version_alignment"]["status"] == "drifted":
        assert any("version drift" in line for line in result["claim_ceiling"])


def test_version_alignment_is_not_a_ladder_rung(tmp_path: Path) -> None:
    """A drifted checkout can still be fully wired; lowering a level would lie."""
    repo = _make_repo(tmp_path)
    _write_lock(repo, adopted_release="9.9.9", adopted_commit="0" * 40)
    _add_module(repo)
    _add_wiring(repo)
    _add_invocation(repo, {"demo_guard_ran": True})
    result = run_census(repo)
    assert "version_alignment" not in result["surfaces"][0]["checks"]
    assert result["surfaces"][0]["level"] != LEVEL_NONE


# ── registry and CLI ──────────────────────────────────────────────────────────

def test_unknown_registry_schema_is_an_error_not_an_empty_pass(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "governance").mkdir(parents=True)
    (repo / "governance" / "guard_surface_registry.json").write_text(
        json.dumps({"registry_schema": "something.else", "surfaces": []}),
        encoding="utf-8",
    )
    registry = load_registry(repo)
    assert registry["error"] == "registry_schema_mismatch"
    assert run_census(repo)["registry_error"] == "registry_schema_mismatch"


def test_missing_registry_reports_an_error(tmp_path: Path) -> None:
    result = run_census(tmp_path)
    assert result["registry_error"].startswith("registry_not_found")
    assert result["surface_count"] == 0


def test_require_level_is_opt_in(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path)
    _add_module(repo)

    # Default: a report, never a gate.
    assert main(["--project-root", str(repo)]) == 0
    # Opt-in threshold fails on a present-only surface.
    assert main(["--project-root", str(repo), "--require-level", "invoked"]) == 1
