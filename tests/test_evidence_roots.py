"""Contract-driven evidence roots: declaration, hardening, and triage buckets.

These tests pin the property that motivated the module: a repo storing evidence
outside artifacts/ must produce a *different* finding from a repo that cited no
evidence at all. Collapsing the two is what made the provenance stream
untriageable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools.evidence_roots import (  # noqa: E402
    DEFAULT_EVIDENCE_ROOTS,
    FRAMEWORK_OWNED_ROOTS,
    SOURCE_DECLARED_EMPTY,
    looks_like_evidence_file,
    NOT_A_FILE,
    NOT_FOUND,
    OK,
    OUTSIDE_ROOTS,
    SOURCE_CONTRACT,
    SOURCE_DEFAULT,
    UNSAFE_ABSOLUTE,
    UNSAFE_ESCAPES_ROOT,
    UNSAFE_TRAVERSAL,
    classify_evidence_path,
    find_evidence_tokens,
    load_evidence_root_policy,
    normalize_root,
    policy_from_values,
)


def _write_contract(root: Path, body: str) -> None:
    (root / "contract.yaml").write_text(body, encoding="utf-8")


# ── policy loading ────────────────────────────────────────────────────────────

def test_missing_contract_falls_back_to_framework_default(tmp_path: Path) -> None:
    policy = load_evidence_root_policy(tmp_path)
    assert policy.roots == DEFAULT_EVIDENCE_ROOTS
    assert policy.source == SOURCE_DEFAULT
    assert policy.is_framework_default


def test_declared_roots_extend_the_framework_owned_roots(tmp_path: Path) -> None:
    _write_contract(
        tmp_path,
        "name: consumer\nevidence_roots:\n  - Tools/TestTools/Evidence\n"
        "  - memory/governance_onboarding\n",
    )
    policy = load_evidence_root_policy(tmp_path)
    assert policy.source == SOURCE_CONTRACT
    assert policy.consumer_roots == (
        "Tools/TestTools/Evidence",
        "memory/governance_onboarding",
    )
    # Consumer roots are additive. The framework writes its own runtime
    # closeouts and receipts under artifacts/, so a contract that dropped it
    # would make the framework stop recognising its own artifacts.
    assert policy.roots[0] == "artifacts"
    assert set(FRAMEWORK_OWNED_ROOTS).issubset(policy.roots)


def test_consumer_cannot_remove_a_framework_owned_root(tmp_path: Path) -> None:
    _write_contract(tmp_path, "name: consumer\nevidence_roots:\n  - only/mine\n")
    policy = load_evidence_root_policy(tmp_path)
    assert "artifacts" in policy.roots


def test_explicitly_empty_declaration_is_visible_not_silent(tmp_path: Path) -> None:
    """`evidence_roots:` with no entries is a misconfiguration, not a default."""
    _write_contract(tmp_path, "name: consumer\nevidence_roots:\n")
    policy = load_evidence_root_policy(tmp_path)
    assert policy.roots == FRAMEWORK_OWNED_ROOTS
    assert policy.source == SOURCE_DECLARED_EMPTY
    assert any("declared_but_empty" in warning for warning in policy.warnings)
    # Distinguishable from the key simply being absent.
    assert policy.source != SOURCE_DEFAULT


def test_contract_above_the_project_root_is_not_inherited(tmp_path: Path) -> None:
    """Discovery walks upward; a parent repo's roots do not describe this one."""
    _write_contract(tmp_path, "name: parent\nevidence_roots:\n  - parent-evidence\n")
    nested = tmp_path / "nested-repo"
    nested.mkdir()

    policy = load_evidence_root_policy(nested)
    assert policy.roots == DEFAULT_EVIDENCE_ROOTS
    assert any("outside_project_root" in warning for warning in policy.warnings)


def test_contract_without_the_key_keeps_the_default(tmp_path: Path) -> None:
    _write_contract(tmp_path, "name: consumer\ndomain: driver\n")
    policy = load_evidence_root_policy(tmp_path)
    assert policy.roots == DEFAULT_EVIDENCE_ROOTS
    assert policy.source == SOURCE_DEFAULT


def test_unreadable_contract_degrades_to_default_with_a_warning(tmp_path: Path) -> None:
    """A broken contract must not silently disable the provenance check."""
    _write_contract(tmp_path, "evidence_roots:\n  - artifacts\nnot-a-mapping-line\n")
    policy = load_evidence_root_policy(tmp_path)
    assert policy.roots == DEFAULT_EVIDENCE_ROOTS
    assert policy.source == SOURCE_DEFAULT
    assert any("contract_unreadable" in warning for warning in policy.warnings)


@pytest.mark.parametrize(
    "value",
    ["/etc", "C:/Windows", "../outside", "evidence/../../escape", "~/evidence", ""],
)
def test_unsafe_roots_are_rejected(value: str) -> None:
    assert normalize_root(value) is None


def test_all_roots_invalid_degrades_to_framework_roots(tmp_path: Path) -> None:
    policy = policy_from_values(["/abs", "../up"])
    assert policy.roots == FRAMEWORK_OWNED_ROOTS
    assert policy.source == SOURCE_DECLARED_EMPTY
    assert any("all_invalid" in warning for warning in policy.warnings)


def test_case_insensitive_filesystems_still_match_declared_roots(
    tmp_path: Path,
) -> None:
    """On Windows `EVIDENCE/x.json` and `evidence/x.json` are the same file."""
    policy = policy_from_values(["evidence"])
    target = tmp_path / "evidence" / "run.json"
    target.parent.mkdir()
    target.write_text("{}", encoding="utf-8")

    verdict = classify_evidence_path(tmp_path, "EVIDENCE/run.json", policy)
    if sys.platform == "win32":
        assert verdict.status == OK
    else:
        # A case-sensitive filesystem genuinely has no such file.
        assert verdict.status != OK


def test_declared_suffixes_extend_the_framework_set() -> None:
    policy = policy_from_values(["evidence"], suffixes=["pnp", ".devlog"])
    assert ".pnp" in policy.suffixes and ".devlog" in policy.suffixes
    # Framework-known formats are never dropped by a consumer declaration.
    assert ".json" in policy.suffixes


def test_quoted_paths_with_spaces_are_found() -> None:
    policy = policy_from_values(["Test Tools/Evidence"])
    prose = 'PASS: suite green; receipt "Test Tools/Evidence/run 1.json"'
    # The unquoted scan stops at the space; the quoted span recovers the
    # whole path, which is the one that actually resolves.
    assert "Test Tools/Evidence/run 1.json" in find_evidence_tokens(prose, policy)


def test_root_normalization_is_idempotent_across_separators() -> None:
    policy = policy_from_values(["./Tools\\Evidence/", "Tools/Evidence"])
    assert policy.consumer_roots == ("Tools/Evidence",)


# ── token discovery ───────────────────────────────────────────────────────────

def test_tokens_are_found_for_declared_roots_in_either_separator() -> None:
    policy = policy_from_values(["Tools/TestTools/Evidence"])
    prose = (
        "PASS: ran suite; see Tools/TestTools/Evidence/run-1.json and "
        r"Tools\TestTools\Evidence\run-2.json"
    )
    tokens = find_evidence_tokens(prose, policy)
    assert len(tokens) == 2


def test_undeclared_root_produces_no_tokens() -> None:
    policy = policy_from_values(["Tools/Evidence"])
    assert find_evidence_tokens("PASS: unrelated/dir/x.json", policy) == []


# ── path classification ───────────────────────────────────────────────────────

def test_existing_file_under_declared_root_is_ok(tmp_path: Path) -> None:
    policy = policy_from_values(["evidence"])
    target = tmp_path / "evidence" / "run.json"
    target.parent.mkdir()
    target.write_text("{}", encoding="utf-8")

    verdict = classify_evidence_path(tmp_path, "evidence/run.json", policy)
    assert verdict.status == OK
    assert verdict.matched_root == "evidence"
    assert verdict.resolved_path == target.resolve()


def test_path_outside_declared_roots_is_its_own_bucket(tmp_path: Path) -> None:
    policy = policy_from_values(["evidence"])
    other = tmp_path / "elsewhere" / "run.json"
    other.parent.mkdir()
    other.write_text("{}", encoding="utf-8")

    verdict = classify_evidence_path(tmp_path, "elsewhere/run.json", policy)
    # The file exists; it is simply not in a place this repo declared.
    assert verdict.status == OUTSIDE_ROOTS
    assert not verdict.ok


def test_missing_file_under_declared_root_is_not_found(tmp_path: Path) -> None:
    policy = policy_from_values(["evidence"])
    verdict = classify_evidence_path(tmp_path, "evidence/absent.json", policy)
    assert verdict.status == NOT_FOUND


def test_directory_is_not_accepted_as_evidence(tmp_path: Path) -> None:
    policy = policy_from_values(["evidence"])
    (tmp_path / "evidence" / "subdir").mkdir(parents=True)
    verdict = classify_evidence_path(tmp_path, "evidence/subdir", policy)
    assert verdict.status == NOT_A_FILE


def test_root_itself_is_not_evidence(tmp_path: Path) -> None:
    policy = policy_from_values(["evidence"])
    (tmp_path / "evidence").mkdir()
    verdict = classify_evidence_path(tmp_path, "evidence", policy)
    assert verdict.status != OK


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("/etc/passwd", UNSAFE_ABSOLUTE),
        ("C:/Windows/system32/x.json", UNSAFE_ABSOLUTE),
        ("evidence/../../outside.json", UNSAFE_TRAVERSAL),
        ("evidence/../secrets.json", UNSAFE_TRAVERSAL),
    ],
)
def test_unsafe_tokens_are_rejected_before_existence(
    tmp_path: Path, token: str, expected: str
) -> None:
    policy = policy_from_values(["evidence"])
    verdict = classify_evidence_path(tmp_path, token, policy)
    assert verdict.status == expected
    assert verdict.is_unsafe


def test_traversal_is_rejected_even_when_it_lands_on_a_real_file(
    tmp_path: Path,
) -> None:
    """Normalizing first would let evidence/../evidence/x.json through."""
    policy = policy_from_values(["evidence"])
    target = tmp_path / "evidence" / "run.json"
    target.parent.mkdir()
    target.write_text("{}", encoding="utf-8")

    verdict = classify_evidence_path(
        tmp_path, "evidence/../evidence/run.json", policy
    )
    assert verdict.status == UNSAFE_TRAVERSAL


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("evidence/run.json", True),
        ("out/results.ndjson", True),
        ("logs/suite.log", True),
        ("reports/junit.xml", True),
        # Naming what you ran is not producing evidence of the result. A test
        # target must never be reclassified as misplaced evidence, or an
        # unsupported claim gets relabelled as a mere contract gap.
        ("tests/test_reviewer_summary_linter.py", False),
        ("scripts/run_probe.py", False),
        ("src/module.ts", False),
        ("config/settings.yaml", False),
        # Windows domain evidence: the formats CFU-style driver work produces.
        ("evidence/trace.etl", True),
        ("evidence/system.evtx", True),
        ("evidence/driver.cat", True),
        ("evidence/driver.inf", True),
        ("evidence/crash.dmp", True),
    ],
)
def test_only_output_shaped_files_are_evidence_candidates(
    path: str, expected: bool
) -> None:
    assert looks_like_evidence_file(path) is expected


def test_extensionless_file_counts_only_when_it_actually_exists() -> None:
    """Real evidence is often a bare `stdout` file; requiring a suffix would
    push those into the "claimed success with no evidence" bucket."""
    assert looks_like_evidence_file("evidence/stdout", exists=True) is True
    assert looks_like_evidence_file("evidence/stdout", exists=False) is False
    # An existing source file is still never evidence.
    assert looks_like_evidence_file("scripts/run.py", exists=True) is False


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlink creation needs elevation on Windows"
)
def test_symlinked_evidence_escaping_the_repo_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    outside = tmp_path / "outside"
    (project / "evidence").mkdir(parents=True)
    outside.mkdir()
    (outside / "run.json").write_text("{}", encoding="utf-8")
    (project / "evidence" / "linked.json").symlink_to(outside / "run.json")

    policy = policy_from_values(["evidence"])
    verdict = classify_evidence_path(project, "evidence/linked.json", policy)
    assert verdict.status == UNSAFE_ESCAPES_ROOT
