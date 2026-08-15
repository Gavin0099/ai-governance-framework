from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import gate3_historical_bootstrap as bootstrap


HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "gate3-route-v2-ab-contract-manifest-candidate.json"
CANDIDATE_PATH = HERE / "gate3-route-v2-ab-candidate-set.json"
OWNER_PIN_PATH = HERE / "gate3-route-v2-ab-owner-pin.json"


def retained_contract() -> bytes:
    """Retained bytes are read by the *test* and injected into the module."""

    return CONTRACT_PATH.read_bytes()


def retained_candidate() -> bytes:
    return CANDIDATE_PATH.read_bytes()


def retained_pin() -> bytes:
    return OWNER_PIN_PATH.read_bytes()


def chain(**overrides):
    kwargs = {
        "owner_pin": retained_pin(),
        "owner_pin_path": bootstrap.OWNER_PIN_PATH,
        "contract_manifest": retained_contract(),
        "candidate_set": retained_candidate(),
    }
    kwargs.update(overrides)
    return bootstrap.verify_bootstrap_chain(**kwargs)


def mutated(payload: bytes, old: bytes, new: bytes) -> bytes:
    assert old in payload
    return payload.replace(old, new, 1)


# --- the chain --------------------------------------------------------------


def test_chain_validates_the_retained_artifacts() -> None:
    result = chain()
    assert result["contract_manifest_sha256"] == bootstrap.CONTRACT_MANIFEST_SHA256
    assert result["candidate_set_sha256"] == bootstrap.CANDIDATE_SET_SHA256
    assert result["source_commit"] == bootstrap.SOURCE_COMMIT
    assert result["promotion_state"] == "SIGNED_AND_PROMOTED"
    assert len(result["retained_inventory"]) == 11
    assert len(result["runtime_module_inventory"]) == 4


def test_contract_manifest_digest_is_checked() -> None:
    payload = mutated(retained_contract(), b'"pair_id"', b'"pair_ID"')
    with pytest.raises(bootstrap.BootstrapError) as caught:
        chain(contract_manifest=payload)
    assert caught.value.code == "CONTRACT_MANIFEST_DIGEST_MISMATCH"


# --- owner pin, which an earlier revision skipped entirely ------------------


def test_owner_pin_is_actually_validated() -> None:
    value = bootstrap.verify_owner_pin(retained_pin(), bootstrap.OWNER_PIN_PATH)
    assert value["status"] == "SIGNED_AND_PROMOTED"
    assert value["manifest_sha256"] == bootstrap.CONTRACT_MANIFEST_SHA256


@pytest.mark.parametrize(
    ("forged", "code"),
    [
        (b'{"manifest_sha256":"' + b"0" * 64 + b'","schema":"gate3-route-v2-ab.owner-manifest-pin.v1","status":"SIGNED_AND_PROMOTED"}',
         "OWNER_PIN_MANIFEST_MISMATCH"),
        (b'{"manifest_sha256":"fd6c75eb7e3bb7f36f85804b7b2398a07d5647d948691f2d9ff64ea094998440","schema":"wrong","status":"SIGNED_AND_PROMOTED"}',
         "OWNER_PIN_SCHEMA_INVALID"),
        (b'{"manifest_sha256":"fd6c75eb7e3bb7f36f85804b7b2398a07d5647d948691f2d9ff64ea094998440","schema":"gate3-route-v2-ab.owner-manifest-pin.v1","status":"CANDIDATE"}',
         "OWNER_PIN_NOT_PROMOTED"),
        (b'{"manifest_sha256":"fd6c75eb7e3bb7f36f85804b7b2398a07d5647d948691f2d9ff64ea094998440","schema":"gate3-route-v2-ab.owner-manifest-pin.v1","status":"SIGNED_AND_PROMOTED","extra":1}',
         "OWNER_PIN_SCHEMA_INVALID"),
        (b"", "ARTIFACT_UNPARSEABLE"),
    ],
)
def test_forged_owner_pins_fail_closed(forged: bytes, code: str) -> None:
    with pytest.raises(bootstrap.BootstrapError) as caught:
        chain(owner_pin=forged)
    assert caught.value.code == code


VALID_PIN_FIELDS = {
    "manifest_sha256": b'"fd6c75eb7e3bb7f36f85804b7b2398a07d5647d948691f2d9ff64ea094998440"',
    "schema": b'"gate3-route-v2-ab.owner-manifest-pin.v1"',
    "status": b'"SIGNED_AND_PROMOTED"',
}
HOSTILE_FIRST_VALUES = {
    "manifest_sha256": b'"' + b"0" * 64 + b'"',
    "schema": b'"attacker-schema"',
    "status": b'"CANDIDATE"',
}


def pin_with_duplicate(field: str) -> bytes:
    """A pin whose first value for `field` is hostile and second is valid.

    json.loads keeps the last value, so without duplicate rejection the
    exact-field check would never see the hostile one.
    """

    parts = [b'"' + field.encode() + b'":' + HOSTILE_FIRST_VALUES[field]]
    parts += [
        b'"' + name.encode() + b'":' + value
        for name, value in VALID_PIN_FIELDS.items()
    ]
    return b"{" + b",".join(parts) + b"}"


@pytest.mark.parametrize("field", ["manifest_sha256", "schema", "status"])
def test_duplicate_keys_cannot_smuggle_a_hostile_value(field: str) -> None:
    forged = pin_with_duplicate(field)
    # the last-value-wins parse is what the module must refuse
    assert json.loads(forged)[field] == json.loads(
        b"{" + b",".join(
            b'"' + name.encode() + b'":' + value
            for name, value in VALID_PIN_FIELDS.items()
        ) + b"}"
    )[field]
    with pytest.raises(bootstrap.BootstrapError) as caught:
        chain(owner_pin=forged)
    assert caught.value.code == "ARTIFACT_DUPLICATE_KEY"


def test_duplicate_keys_are_refused_in_every_parsed_artifact() -> None:
    duplicated = b'{"schema":"a","schema":"b"}'
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.verify_candidate_set(duplicated)
    assert caught.value.code == "CANDIDATE_SET_DIGEST_MISMATCH"
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap._parse(duplicated)
    assert caught.value.code == "ARTIFACT_DUPLICATE_KEY"


def test_duplicate_key_error_carries_no_artifact_content() -> None:
    with pytest.raises(bootstrap.BootstrapError) as caught:
        chain(owner_pin=pin_with_duplicate("manifest_sha256"))
    rendered = str(caught.value) + repr(caught.value)
    assert "manifest_sha256" not in rendered
    assert "0" * 64 not in rendered


def test_owner_pin_path_must_be_exact() -> None:
    for wrong in ("", "gate3-route-v2-ab-owner-pin.json", None):
        with pytest.raises(bootstrap.BootstrapError) as caught:
            chain(owner_pin_path=wrong)
        assert caught.value.code == "OWNER_PIN_PATH_INVALID"


def test_candidate_set_digest_is_checked() -> None:
    payload = mutated(retained_candidate(), b'"files"', b'"Files"')
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.verify_candidate_set(payload)
    assert caught.value.code == "CANDIDATE_SET_DIGEST_MISMATCH"


def test_source_commit_must_be_exact() -> None:
    value = dict(json.loads(retained_candidate()))
    for wrong in ("", "204965c9", "0" * 40, None, 204965):
        value["source_base_commit"] = wrong
        with pytest.raises(bootstrap.BootstrapError) as caught:
            bootstrap.verify_source_commit(value)
        assert caught.value.code == "SOURCE_COMMIT_MISMATCH"


def test_swapping_candidate_set_and_source_commit_together_is_rejected() -> None:
    """The owner pin does not cover these, so the frozen literal must."""

    value = dict(json.loads(retained_candidate()))
    value["source_base_commit"] = "1" * 40
    forged = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    with pytest.raises(bootstrap.BootstrapError) as caught:
        chain(candidate_set=forged)
    assert caught.value.code == "CANDIDATE_SET_DIGEST_MISMATCH"


# --- the frozen expectation does not move ----------------------------------


def test_frozen_expectation_does_not_follow_the_candidate_bytes() -> None:
    """Mutating the artifact must not move the expected value."""

    before = bootstrap.CANDIDATE_SET_SHA256
    forged = mutated(retained_candidate(), b'"authorization"', b'"Authorization"')
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.verify_candidate_set(forged)
    assert bootstrap.CANDIDATE_SET_SHA256 == before
    assert bootstrap.CANDIDATE_SET_SHA256 != _digest(forged)


def _digest(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def test_expectations_are_module_literals_not_derived_at_import() -> None:
    source = Path(bootstrap.__file__).read_text(encoding="utf-8")
    for value in (
        bootstrap.CONTRACT_MANIFEST_SHA256,
        bootstrap.CANDIDATE_SET_SHA256,
        bootstrap.SOURCE_COMMIT,
    ):
        assert f'"{value}"' in source or f"'{value}'" in source


# --- no worktree lookup, no side effects ------------------------------------


def test_module_never_reads_the_worktree_for_its_expectations() -> None:
    """Bytes are injected; the module touches no filesystem read path.

    An earlier revision patched only `builtins.open`, which `Path.read_bytes`
    bypasses. This denies every read seam the module could plausibly use.
    """

    import builtins
    import io

    calls: list[str] = []

    def deny(name):
        def blocked(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"M1 must not read the filesystem via {name}")

        return blocked

    seams = {
        (builtins, "open"): deny("builtins.open"),
        (io, "open"): deny("io.open"),
        (Path, "open"): deny("Path.open"),
        (Path, "read_bytes"): deny("Path.read_bytes"),
        (Path, "read_text"): deny("Path.read_text"),
    }
    originals = {(obj, name): getattr(obj, name) for obj, name in seams}

    # capture the injected bytes before the seams are closed
    payloads = {
        "owner_pin": retained_pin(),
        "owner_pin_path": bootstrap.OWNER_PIN_PATH,
        "contract_manifest": retained_contract(),
        "candidate_set": retained_candidate(),
    }
    for (obj, name), replacement in seams.items():
        setattr(obj, name, replacement)
    try:
        bootstrap.verify_bootstrap_chain(**payloads)
    finally:
        for (obj, name), original in originals.items():
            setattr(obj, name, original)
    assert calls == []


def test_no_child_process_is_started() -> None:
    import subprocess

    calls: list[object] = []
    originals = {
        name: getattr(subprocess, name) for name in ("run", "Popen", "check_output")
    }

    def blocked(*args, **kwargs):
        calls.append(args)
        raise AssertionError("M1 must not start a process")

    for name in originals:
        setattr(subprocess, name, blocked)
    try:
        chain()
    finally:
        for name, value in originals.items():
            setattr(subprocess, name, value)
    assert calls == []


def test_no_historical_module_is_imported(tmp_path: Path) -> None:
    before = set(sys.modules)
    chain()
    added = set(sys.modules) - before
    assert not [name for name in added if name.startswith("gate3_")]
    assert list(tmp_path.iterdir()) == []


def test_module_imports_no_gate3_module() -> None:
    import ast

    tree = ast.parse(Path(bootstrap.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(name.startswith("gate3_") for name in imported), imported
    assert "subprocess" not in imported
    assert "tempfile" not in imported


# --- not active -------------------------------------------------------------


def test_m1_is_not_wired_into_the_production_verifier() -> None:
    """The production path switches at M4; assert it has not switched."""

    assert bootstrap.ACTIVE is False
    candidate_source = (HERE / "gate3_route_v2_ab_candidate.py").read_text(
        encoding="utf-8"
    )
    assert "gate3_historical_bootstrap" not in candidate_source
    checkout_source = (HERE / "gate3_route_v2_ab_checkout.py").read_text(
        encoding="utf-8"
    )
    assert "gate3_historical_bootstrap" not in checkout_source


# --- inventory --------------------------------------------------------------


def test_inventory_is_derived_only_from_verified_bytes() -> None:
    value = bootstrap.verify_candidate_set(retained_candidate())
    inventory = bootstrap.retained_inventory(value)
    assert all(len(digest) == 64 for digest in inventory.values())
    assert any(path.endswith("gate3_route_v2_codex.py") for path in inventory)


# --- executable authority is the allowlist, not the retained set ------------


def test_runtime_modules_are_the_allowlist_not_every_retained_file() -> None:
    value = bootstrap.verify_candidate_set(retained_candidate())
    retained = bootstrap.retained_inventory(value)
    runtime = bootstrap.runtime_module_inventory(value)

    assert len(retained) == 11 and len(runtime) == 4
    assert set(runtime) == set(bootstrap.RUNTIME_MODULE_ALLOWLIST)
    assert all(path.endswith(".py") for path in runtime)
    excluded = set(retained) - set(runtime)
    assert any(path.endswith(".gitattributes") for path in excluded)
    assert any(path.endswith(".json") for path in excluded)
    assert any(path.endswith(".md") for path in excluded)
    assert any("test_" in path for path in excluded)
    for path, digest in runtime.items():
        assert retained[path] == digest


def test_missing_allowlisted_module_fails_closed() -> None:
    value = dict(json.loads(retained_candidate()))
    dropped = [
        record
        for record in value["files"]
        if not record["path"].endswith("gate3_route_v2_codex.py")
    ]
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.runtime_module_inventory({**value, "files": dropped})
    assert caught.value.code == "RUNTIME_MODULE_MISSING"


def test_role_substitution_does_not_grant_executable_authority() -> None:
    """A non-allowlisted file cannot become a runtime module by renaming."""

    value = dict(json.loads(retained_candidate()))
    swapped = []
    for record in value["files"]:
        record = dict(record)
        if record["path"].endswith("skill-packet-bugfix.md"):
            record["path"] = record["path"].replace(
                "skill-packet-bugfix.md", "gate3-route-v2/impostor.py"
            )
        swapped.append(record)
    runtime = bootstrap.runtime_module_inventory({**value, "files": swapped})
    assert set(runtime) == set(bootstrap.RUNTIME_MODULE_ALLOWLIST)
    assert not any("impostor" in path for path in runtime)


@pytest.mark.parametrize(
    "records",
    [
        [],
        "not-a-list",
        [{"path": "a", "sha256": "0" * 64}],
        [{"bytes": 1, "path": "a", "sha256": "zz"}],
        [{"bytes": -1, "path": "a", "sha256": "0" * 64}],
        [{"bytes": 1, "path": "", "sha256": "0" * 64}],
    ],
)
def test_malformed_inventories_fail_closed(records: object) -> None:
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.retained_inventory({"files": records})
    assert caught.value.code == "FILE_INVENTORY_INVALID"


def test_duplicate_paths_fail_closed() -> None:
    record = {"bytes": 1, "path": "a", "sha256": "0" * 64}
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.retained_inventory({"files": [record, dict(record)]})
    assert caught.value.code == "FILE_INVENTORY_DUPLICATE"


@pytest.mark.parametrize("payload", [b"", b"[]\n", b"{", "not-bytes"])
def test_unparseable_or_non_bytes_input_fails_closed(payload: object) -> None:
    with pytest.raises(bootstrap.BootstrapError) as caught:
        chain(contract_manifest=payload)
    assert caught.value.code in {
        "ARTIFACT_NOT_BYTES",
        "CONTRACT_MANIFEST_DIGEST_MISMATCH",
    }


def test_closed_errors_carry_no_artifact_content() -> None:
    forged = mutated(retained_candidate(), b'"schema"', b'"Schema"')
    with pytest.raises(bootstrap.BootstrapError) as caught:
        bootstrap.verify_candidate_set(forged)
    rendered = str(caught.value) + repr(caught.value)
    assert rendered.count("CANDIDATE_SET_DIGEST_MISMATCH") >= 1
    assert "source_base_commit" not in rendered
    assert "files" not in rendered
