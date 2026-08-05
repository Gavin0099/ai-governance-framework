"""Strong claims must be backed by a registered validator's receipt.

The framework never judges domain semantics here. What these tests pin is the
binding: registered claim kind, registered producer, real anchoring, and a
verdict that rests on more than a process exit code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools.claim_validator_binding import (  # noqa: E402
    BINDING_STRENGTH,
    DOWNGRADE_TO,
    REGISTRY_SCHEMA,
    RECEIPT_SCHEMA,
    STRENGTH_OBSERVED,
    VERDICT_BOUND,
    VERDICT_UNBOUND,
    check_claim_binding,
    load_binding_registry,
    main,
)

CLAIM = "driver_install_verified"
VALIDATOR = "validators/driver_result_validator.py"
SESSION = "session-20260805T000000-aaaaaa"
COMMIT = "a1b2c3d4e5f6"


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "governance").mkdir(parents=True)
    (repo / "validators").mkdir(parents=True)
    (repo / VALIDATOR).write_text("# domain validator", encoding="utf-8")
    (repo / "contract.yaml").write_text(
        "name: consumer\nevidence_roots:\n  - evidence\n", encoding="utf-8"
    )
    (repo / "evidence").mkdir()
    (repo / "governance" / "claim_binding_registry.json").write_text(
        json.dumps(
            {
                "registry_schema": REGISTRY_SCHEMA,
                "bindings": [
                    {
                        "claim_kind": CLAIM,
                        "validator": VALIDATOR,
                        "strength": "strong",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return repo


def _receipt(repo: Path, **overrides) -> str:
    payload = {
        "receipt_schema": RECEIPT_SCHEMA,
        "claim_kind": CLAIM,
        "validator": VALIDATOR,
        "verdict": "pass",
        "verdict_basis": "INF version 3.2.1 and device status OK matched expectation",
        "command": "pnputil /add-driver x.inf /install",
        "exit_code": 0,
        "started_at": "2026-08-05T00:00:00Z",
        "finished_at": "2026-08-05T00:00:04Z",
        "session_id": SESSION,
        "linked_commit": COMMIT,
        "evidence_paths": [],
        "cannot_claim": ["device stability over time"],
    }
    payload.update(overrides)
    name = overrides.pop("_name", "receipt-1.json")
    path = repo / "evidence" / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return f"evidence/{name}"


def _check(repo: Path, receipt: str | None, **kwargs):
    return check_claim_binding(
        repo,
        claim_kind=kwargs.pop("claim_kind", CLAIM),
        receipt_path=receipt,
        session_id=kwargs.pop("session_id", SESSION),
        commit=kwargs.pop("commit", COMMIT),
        **kwargs,
    )


# ── the happy path ────────────────────────────────────────────────────────────

def test_registered_anchored_receipt_binds_a_strong_claim(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo))
    assert result.verdict == VERDICT_BOUND
    assert result.effective_strength == "strong"


def test_bound_result_states_it_does_not_prove_execution(tmp_path: Path) -> None:
    """Every field checked is self-reported; a hand-written receipt passes.

    The result must say so, or `bound` will be read as proof the validator ran.
    """
    repo = _repo(tmp_path)
    payload = _check(repo, _receipt(repo)).as_dict()
    assert payload["binding_strength"] == BINDING_STRENGTH
    assert any("ever executed" in item for item in payload["not_claimed"])
    assert any("written by hand" in item for item in payload["not_claimed"])
    assert "not that the validator ran" in payload["claim_ceiling"]


def test_a_hand_written_receipt_is_indistinguishable_and_still_binds(
    tmp_path: Path,
) -> None:
    """Pins the known gap rather than pretending it is closed.

    Nothing in this module can tell a validator-produced receipt from a
    fabricated one. Closing it needs a canonical runner invocation id and a
    ledger the producer cannot write to. Until then this test documents the
    exposure so it cannot be silently assumed away.
    """
    repo = _repo(tmp_path)
    fabricated = _receipt(repo, verdict_basis="fabricated but plausible basis text")
    assert _check(repo, fabricated).bound is True


def test_short_commit_anchor_matches_full_receipt_commit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo), commit=COMMIT[:7])
    assert result.bound


def test_observed_claims_need_no_receipt(tmp_path: Path) -> None:
    """A claim that asserts only observation is not downgraded for lacking proof."""
    repo = _repo(tmp_path)
    result = _check(repo, None, claimed_strength=STRENGTH_OBSERVED)
    assert result.bound
    assert result.effective_strength == STRENGTH_OBSERVED


# ── everything that must downgrade ────────────────────────────────────────────

def test_no_receipt_downgrades_the_claim(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, None)
    assert result.verdict == VERDICT_UNBOUND
    assert result.effective_strength == DOWNGRADE_TO
    assert "no_receipt_cited" in result.reasons


def test_unregistered_claim_kind_is_unbound(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo), claim_kind="something_invented")
    assert "claim_kind_not_registered" in result.reasons


def test_missing_registry_binds_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "governance" / "claim_binding_registry.json").unlink()
    result = _check(repo, _receipt(repo))
    assert not result.bound
    assert any("registry_unusable" in reason for reason in result.reasons)


def test_receipt_from_an_unregistered_validator_is_rejected(tmp_path: Path) -> None:
    """Well-formed is not the same as authorised."""
    repo = _repo(tmp_path)
    receipt = _receipt(repo, validator="validators/some_other_tool.py")
    result = _check(repo, receipt)
    assert "receipt_validator_not_registered_for_claim_kind" in result.reasons


def test_registered_validator_absent_from_disk_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    receipt = _receipt(repo)
    (repo / VALIDATOR).unlink()
    result = _check(repo, receipt)
    assert any("registered_validator_missing" in reason for reason in result.reasons)


@pytest.mark.parametrize(
    "basis",
    ["exit code 0", "exit_code == 0", "rc 0", "returncode 0", "process succeeded", "no error"],
)
def test_exit_code_alone_cannot_support_a_strong_claim(
    tmp_path: Path, basis: str
) -> None:
    """The pnputil rule, stated without any domain knowledge."""
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo, verdict_basis=basis))
    assert "verdict_basis_is_exit_code_only" in result.reasons
    assert result.effective_strength == DOWNGRADE_TO


def test_a_real_semantic_basis_is_accepted_even_with_exit_code_mentioned(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    receipt = _receipt(
        repo,
        verdict_basis="exit code 0 and driver version 3.2.1 present in pnputil /enum-drivers",
    )
    assert _check(repo, receipt).bound


def test_non_pass_verdict_does_not_support_a_pass_claim(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo, verdict="inconclusive"))
    assert "receipt_verdict_is_inconclusive" in result.reasons


def test_session_mismatch_is_unbound(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo, session_id="session-other"))
    assert "receipt_session_mismatch" in result.reasons


def test_commit_mismatch_is_unbound(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo, linked_commit="9999999999ab"))
    assert "receipt_commit_mismatch" in result.reasons


def test_unanchored_receipt_cannot_back_a_commit_scoped_claim(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo, linked_commit="no_git_worktree"))
    assert "receipt_not_commit_anchored" in result.reasons


def test_receipt_outside_declared_evidence_roots_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    stray = repo / "tmp"
    stray.mkdir()
    (stray / "receipt.json").write_text("{}", encoding="utf-8")
    result = _check(repo, "tmp/receipt.json")
    assert any("receipt_path_rejected" in reason for reason in result.reasons)


def test_receipt_path_escaping_the_repo_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = _check(repo, "evidence/../../outside.json")
    assert any(
        "receipt_path_rejected:path_unsafe" in reason for reason in result.reasons
    )


def test_receipt_citing_a_nonexistent_evidence_path_is_rejected(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    receipt = _receipt(repo, evidence_paths=["evidence/absent.log"])
    result = _check(repo, receipt)
    assert any("receipt_evidence_path_rejected" in r for r in result.reasons)


def test_receipt_without_cannot_claim_is_malformed(tmp_path: Path) -> None:
    """Every receipt must state its own limits; an unbounded claim is not a receipt."""
    repo = _repo(tmp_path)
    result = _check(repo, _receipt(repo, cannot_claim=[]))
    assert "receipt_field_invalid:cannot_claim" in result.reasons


# ── registry loading and CLI ──────────────────────────────────────────────────

def test_registry_schema_mismatch_is_an_error(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "governance" / "claim_binding_registry.json").write_text(
        json.dumps({"registry_schema": "other.v9", "bindings": []}), encoding="utf-8"
    )
    assert load_binding_registry(repo)["error"] == "registry_schema_mismatch"


def test_cli_reports_before_it_fails(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    argv = ["--project-root", str(repo), "--claim-kind", CLAIM]
    # Reporting an unbound claim is the default; failing on it is opt-in.
    assert main(argv) == 0
    assert main([*argv, "--fail-on-unbound"]) == 1
