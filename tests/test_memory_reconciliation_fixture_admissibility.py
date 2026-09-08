from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from governance_tools.authority_loader import parse_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
GITATTRIBUTES = REPO_ROOT / ".gitattributes"
AUTHORITY = REPO_ROOT / "governance" / "AUTHORITY.md"
CONTRACT = REPO_ROOT / "governance" / "MEMORY_RECONCILIATION_FIXTURE_ADMISSIBILITY_CONTRACT.md"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "memory_reconciliation_exact_duplicate"
MANIFEST = FIXTURE_ROOT / "fixture.json"


def _requirements() -> dict[str, Any]:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- mrcsp-m0-admissibility-requirements:begin -->\s*"
        r"```json\s*(.*?)\s*```\s*"
        r"<!-- mrcsp-m0-admissibility-requirements:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _fixture_bytes(manifest: dict[str, Any]) -> tuple[bytes, bytes]:
    path_errors, paths = _fixture_path_errors(manifest)
    assert path_errors == []
    source = paths["source"].read_bytes()
    candidate = paths["candidate"].read_bytes()
    return source, candidate


def _fixture_path_errors(
    manifest: dict[str, Any],
) -> tuple[list[str], dict[str, Path]]:
    errors: list[str] = []
    paths: dict[str, Path] = {}
    root = FIXTURE_ROOT.resolve()

    for role, field in (("source", "source_path"), ("candidate", "candidate_path")):
        value = manifest.get(field)
        if not isinstance(value, str) or not value:
            errors.append("fixture_path_missing")
            continue

        posix_path = PurePosixPath(value)
        windows_path = PureWindowsPath(value)
        portable_parts = value.split("/")
        if (
            "\\" in value
            or posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or any(part in {"", ".", ".."} for part in portable_parts)
        ):
            errors.append("fixture_path_outside_root")
            continue

        resolved = (FIXTURE_ROOT / Path(*posix_path.parts)).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append("fixture_path_outside_root")
            continue

        paths[role] = resolved
        unresolved = FIXTURE_ROOT / Path(*posix_path.parts)
        if not unresolved.exists():
            errors.append("fixture_file_missing")
        elif unresolved.is_symlink():
            errors.append("fixture_symlink_not_allowed")
        elif not unresolved.is_file():
            errors.append("fixture_not_regular_file")

    if paths.get("source") == paths.get("candidate") and "source" in paths:
        errors.append("fixture_paths_not_distinct")

    return errors, paths


def _admission_errors(
    manifest: dict[str, Any],
    requirements: dict[str, Any],
    *,
    source_override: bytes | None = None,
    candidate_override: bytes | None = None,
) -> list[str]:
    errors, paths = _fixture_path_errors(manifest)
    paths_admissible = not errors and set(paths) == {"source", "candidate"}
    source = paths["source"].read_bytes() if paths_admissible else None
    candidate = (
        paths["candidate"].read_bytes() if paths_admissible else None
    )
    if source_override is not None:
        source = source_override
    if candidate_override is not None:
        candidate = candidate_override

    if source is not None and candidate is not None and source != candidate:
        errors.append("byte_mismatch")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict) or any(
        not provenance.get(field) for field in requirements["required_provenance_fields"]
    ):
        errors.append("missing_provenance")
    elif provenance.get("kind") != "synthetic_redacted_reconstruction":
        errors.append("invalid_provenance_kind")

    digest = manifest.get("digest")
    if not isinstance(digest, dict) or not digest.get("algorithm") or not digest.get("value"):
        errors.append("missing_digest")
    elif digest.get("algorithm") != requirements["required_digest_algorithm"]:
        errors.append("unsupported_digest_algorithm")
    elif source is not None and candidate is not None:
        pinned = digest["value"]
        if hashlib.sha256(source).hexdigest() != pinned:
            errors.append("source_digest_mismatch")
        if hashlib.sha256(candidate).hexdigest() != pinned:
            errors.append("candidate_digest_mismatch")

    redaction = manifest.get("redaction")
    required_boundaries = set(requirements["required_redaction_boundaries"])
    if (
        not isinstance(redaction, dict)
        or redaction.get("status") != "complete"
        or redaction.get("original_identifiers_included") is not False
        or not required_boundaries.issubset(set(redaction.get("boundaries", [])))
    ):
        errors.append("incomplete_redaction")

    if manifest.get("fixture_usage") != requirements["fixture_usage"]:
        errors.append("fixture_not_test_only")
    if manifest.get("expected_relation") != requirements["required_relation"]:
        errors.append("unexpected_relation")
    if not manifest.get("claim_ceiling"):
        errors.append("missing_claim_ceiling")

    return errors


def test_contract_is_registered_canonical_on_demand_authority() -> None:
    assert parse_frontmatter(CONTRACT) == {
        "audience": "agent-on-demand",
        "authority": "canonical",
        "can_override": False,
        "overridden_by": "AGENT.md",
        "default_load": "on-demand",
    }
    authority = AUTHORITY.read_text(encoding="utf-8")
    assert (
        "| `governance/MEMORY_RECONCILIATION_FIXTURE_ADMISSIBILITY_CONTRACT.md` "
        "| agent-on-demand | canonical | false | AGENT.md | on-demand |"
    ) in authority


def test_owner_set_scope_and_non_goals_are_explicit() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "owner-set scope, not text derived\nfrom line 607" in contract
    assert "no M1a detector or reconciliation implementation" in contract
    assert "no writer, runtime, public schema, hook, CI, gate, blocker, or enforcement" in contract
    assert "These are contract-test cases, not a production validator API." in contract


def test_normative_requirements_match_owner_authorized_done() -> None:
    requirements = _requirements()
    assert requirements == {
        "contract_version": "mrcsp-fixture-admissibility.v0.1",
        "fixture_count": 1,
        "fixture_usage": "test_only",
        "required_relation": "exact_byte_duplicate",
        "required_digest_algorithm": "sha256",
        "required_provenance_fields": ["kind", "basis", "created_by", "created_at"],
        "required_redaction_boundaries": [
            "repository_identity",
            "person_identity",
            "session_identity",
            "commit_identity",
            "artifact_locator",
            "source_timestamp",
            "unneeded_free_text",
        ],
        "required_rejection_codes": [
            "byte_mismatch",
            "missing_provenance",
            "missing_digest",
            "incomplete_redaction",
        ],
    }


def test_redacted_exact_duplicate_fixture_is_admissible() -> None:
    manifest = _manifest()
    source, candidate = _fixture_bytes(manifest)
    assert _admission_errors(manifest, _requirements()) == []
    assert b"<REDACTED_" in source


def test_fixture_census_locks_one_manifest_and_one_pair() -> None:
    manifests = sorted(
        path.resolve()
        for path in (REPO_ROOT / "tests" / "fixtures").glob(
            "memory_reconciliation_*/fixture.json"
        )
    )
    assert manifests == [MANIFEST.resolve()]
    assert sorted(path.name for path in FIXTURE_ROOT.iterdir()) == [
        "candidate_record.md",
        "fixture.json",
        "source_record.md",
    ]


def test_fixture_bytes_are_not_subject_to_checkout_eol_conversion() -> None:
    attributes = GITATTRIBUTES.read_text(encoding="utf-8").splitlines()
    assert "/tests/fixtures/memory_reconciliation_exact_duplicate/*.md -text" in attributes


def test_byte_mismatch_is_rejected() -> None:
    manifest = _manifest()
    source, candidate = _fixture_bytes(manifest)
    assert "byte_mismatch" in _admission_errors(
        manifest,
        _requirements(),
        candidate_override=candidate + b"\nmodified",
    )


def test_fixture_path_outside_root_is_rejected() -> None:
    manifest = deepcopy(_manifest())
    manifest["source_path"] = "../../../README.md"
    manifest["candidate_path"] = "../../../README.md"
    external_bytes = (REPO_ROOT / "README.md").read_bytes()
    manifest["digest"]["value"] = hashlib.sha256(external_bytes).hexdigest()
    errors = _admission_errors(
        manifest,
        _requirements(),
        source_override=external_bytes,
        candidate_override=external_bytes,
    )
    assert "fixture_path_outside_root" in errors


def test_identical_fixture_paths_are_rejected() -> None:
    manifest = deepcopy(_manifest())
    manifest["candidate_path"] = manifest["source_path"]
    source, _ = _fixture_bytes(_manifest())
    assert "fixture_paths_not_distinct" in _admission_errors(
        manifest, _requirements(), source_override=source, candidate_override=source
    )


def test_missing_fixture_file_is_rejected() -> None:
    manifest = deepcopy(_manifest())
    manifest["candidate_path"] = "missing_record.md"
    source, candidate = _fixture_bytes(_manifest())
    assert "fixture_file_missing" in _admission_errors(
        manifest, _requirements(), source_override=source, candidate_override=candidate
    )


def test_missing_provenance_is_rejected() -> None:
    manifest = _manifest()
    source, candidate = _fixture_bytes(manifest)
    manifest.pop("provenance")
    assert "missing_provenance" in _admission_errors(
        manifest, _requirements(), source_override=source, candidate_override=candidate
    )


def test_missing_digest_is_rejected() -> None:
    manifest = _manifest()
    source, candidate = _fixture_bytes(manifest)
    manifest.pop("digest")
    assert "missing_digest" in _admission_errors(
        manifest, _requirements(), source_override=source, candidate_override=candidate
    )


def test_incomplete_redaction_is_rejected() -> None:
    mutations = []

    missing_boundary = deepcopy(_manifest())
    missing_boundary["redaction"]["boundaries"].remove("person_identity")
    mutations.append(missing_boundary)

    incomplete_status = deepcopy(_manifest())
    incomplete_status["redaction"]["status"] = "partial"
    mutations.append(incomplete_status)

    identifiers_included = deepcopy(_manifest())
    identifiers_included["redaction"]["original_identifiers_included"] = True
    mutations.append(identifiers_included)

    for manifest in mutations:
        source, candidate = _fixture_bytes(manifest)
        assert "incomplete_redaction" in _admission_errors(
            manifest, _requirements(), source_override=source, candidate_override=candidate
        )
