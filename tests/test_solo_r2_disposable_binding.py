"""Synthetic creation only. Real repository access below is read-only Git."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from uuid import UUID

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_bootstrap as bootstrap
from governance_tools import solo_r2_disposable_binding as subject
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools import solo_r2_pair_creation as pairs
from governance_tools import solo_r2_attempt_execution as execution
from governance_tools.solo_r2_attempt_materialization import PinnedExecutable, RepositoryBinding
from tests.test_solo_r2_pair_creation import _environment

REPO = Path(__file__).resolve().parents[1]
EVALUATION = "a39fed08-e056-41d3-a758-7bf7f9cad100"
EVENT = "a39fed08-e056-41d3-a758-7bf7f9cad101"


def authority():
    return subject.ExperimentInputAuthority((REPO / profile.INPUT_PATH).read_bytes())


@pytest.fixture
def environment(tmp_path, monkeypatch):
    root, custody, key, original, roots = _environment(tmp_path)
    assert root != REPO and REPO not in root.parents
    replacement = root / ledger.REPLACEMENT_PUBLIC_LEDGER_PATH
    replacement.parent.mkdir(parents=True)
    replacement.write_bytes((REPO / ledger.REPLACEMENT_PUBLIC_LEDGER_PATH).read_bytes())
    (root / profile.BINDING_PATH).parent.parent.mkdir(parents=True)
    monkeypatch.setattr(profile, "ROOT", root)
    monkeypatch.setattr(subject, "load_input_authority", lambda **kwargs: authority())
    ids = iter((UUID(EVALUATION), UUID(EVENT)))
    monkeypatch.setattr(subject, "uuid4", lambda: next(ids))
    repo = SimpleNamespace(root=root)
    return SimpleNamespace(root=root, custody=custody, key=key, roots=roots,
                           args=dict(git=None, repository=repo, temp_root=tmp_path),
                           original=original, replacement=replacement)


def create(env):
    return subject.create_disposable_evaluation(**env.args)


def verify(env, result):
    return subject.validate_disposable_pair_preconditions(
        **env.args, expected_binding_sha256=result.binding_sha256,
        expected_evaluation_id=result.evaluation_id,
    )


def pair_args(env, result):
    return dict(**env.args, expected_binding_sha256=result.binding_sha256,
                expected_evaluation_id=result.evaluation_id,
                controller_root=env.roots["controller-state"], key_path=env.key,
                commitment_path=env.roots["controller-custody"] / "creation.json",
                custody_boundary=env.custody)


def test_creation_and_pre_pair_binding_preserve_existing_ledgers(environment, monkeypatch):
    env = environment
    before = [p.read_bytes() for p in (env.original, env.replacement)]
    result = create(env)
    monkeypatch.setattr(subject, "uuid4", lambda: pytest.fail("verifier generated an ID"))
    public, genesis, view = verify(env, result)
    assert public == env.root / profile.LEDGER_PATH
    assert genesis["schema_version"] == "solo_attempt_ledger.v2.1"
    assert genesis["evaluation_id"] == EVALUATION
    assert genesis["adopted_schema_id"] == profile.SCHEMA_ID
    assert genesis["attempt_ceiling_total"] == 14
    assert view.repository == "ai-governance-framework"
    binding = json.loads((env.root / profile.BINDING_PATH).read_bytes())
    assert binding["input_authority_sha256"] == profile.INPUT_SHA256
    assert binding["genesis_sha256"] == hashlib.sha256(public.read_bytes()).hexdigest()
    assert [p.read_bytes() for p in (env.original, env.replacement)] == before
    assert ledger.validate_ledger_file(public).pair_count == 0


def test_disposable_pair_uses_verified_authority_and_seals_before_append(environment):
    env = environment
    before = [p.read_bytes() for p in (env.original, env.replacement)]
    result = create(env)
    pair = pairs.create_disposable_shakedown_pair(**pair_args(env, result))
    events = ledger.read_ledger(env.root / profile.LEDGER_PATH)
    assert events[1]["pair_id"] == pair.pair_id
    assert events[1]["repository"] == "ai-governance-framework"
    assert events[1]["frozen_identities"] == authority().pair_identities()
    assert pair.checkpoint_path.is_file()
    summary = ledger.validate_ledger_events(events)
    assert summary.schema_version == profile.SCHEMA
    assert summary.pair_count == 1 and summary.admitted_attempt_count == 0
    assert [p.read_bytes() for p in (env.original, env.replacement)] == before
    with pytest.raises(subject.DisposableBindingError):
        verify(env, result)  # exact genesis-only boundary cannot admit another Pair


@pytest.mark.parametrize("kind", ["schema", "evaluation", "protocol", "execution_contract", "authority", "genesis_digest", "binding_digest", "missing_binding"])
def test_wrong_identity_fails_before_pair_id_or_sealing(environment, monkeypatch, kind):
    env = environment
    result = create(env)
    public = env.root / profile.LEDGER_PATH
    binding_path = env.root / profile.BINDING_PATH
    if kind in ("schema", "evaluation", "protocol", "execution_contract"):
        event = json.loads(public.read_bytes())
        key, value = {
            "schema": ("schema_version", ledger.LEDGER_SCHEMA),
            "evaluation": ("evaluation_id", EVENT),
            "protocol": ("adopted_protocol_sha256", "0" * 64),
            "execution_contract": ("adopted_contract_sha256", "0" * 64),
        }[kind]
        event[key] = value
        public.write_bytes(ledger.encode_event(event))
    elif kind == "missing_binding":
        binding_path.unlink()
    elif kind == "binding_digest":
        result = replace(result, binding_sha256="0" * 64)
    else:
        binding = json.loads(binding_path.read_bytes())
        binding["input_authority_sha256" if kind == "authority" else "genesis_sha256"] = "0" * 64
        raw = ledger.encode_event(binding)
        binding_path.write_bytes(raw)
        result = replace(result, binding_sha256=hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(pairs, "_new_uuid4", lambda: pytest.fail("Pair ID generated"))
    with pytest.raises((subject.DisposableBindingError, ledger.LedgerError)):
        pairs.create_disposable_shakedown_pair(**pair_args(env, result))
    assert not list(env.roots["controller-state"].iterdir())


@pytest.mark.parametrize("which", ["ledger", "binding"])
def test_occupied_namespace_refuses_before_randomness(environment, monkeypatch, which):
    env = environment
    target = env.root / (profile.LEDGER_PATH if which == "ledger" else profile.BINDING_PATH)
    target.parent.mkdir()
    monkeypatch.setattr(subject, "uuid4", lambda: pytest.fail("ID generated"))
    with pytest.raises(subject.DisposableBindingError):
        create(env)
    assert not target.exists()


def test_second_creation_cannot_consume_another_allocation(environment, monkeypatch):
    env = environment
    create(env)
    monkeypatch.setattr(subject, "uuid4", lambda: pytest.fail("second ID generated"))
    with pytest.raises(subject.DisposableBindingError):
        create(env)


def test_wrong_root_cannot_redirect_publication(environment):
    env = environment
    env.args["repository"] = SimpleNamespace(root=env.root.parent)
    with pytest.raises(subject.DisposableBindingError):
        create(env)
    assert not (env.root / profile.LEDGER_PATH).exists()


def test_no_caller_selected_path_parameter(environment):
    with pytest.raises(TypeError):
        subject.create_disposable_evaluation(**environment.args, ledger_path=environment.original)


def test_collision_with_existing_evaluation_never_publishes(environment, monkeypatch):
    old = ledger.read_ledger(environment.original)[0]["evaluation_id"]
    values = iter((UUID(old), UUID(EVENT)))
    monkeypatch.setattr(subject, "uuid4", lambda: next(values))
    with pytest.raises(subject.DisposableBindingError):
        create(environment)
    assert not (environment.root / profile.LEDGER_PATH).parent.exists()


def test_partial_publication_is_not_cleaned_or_retried(environment, monkeypatch):
    real_write = subject._write_once
    def fail_binding(path, raw):
        if path.name == "genesis-binding.json":
            raise OSError("injected storage failure")
        real_write(path, raw)
    monkeypatch.setattr(subject, "_write_once", fail_binding)
    with pytest.raises(subject.DisposableBindingError):
        create(environment)
    assert (environment.root / profile.LEDGER_PATH).is_file()
    with pytest.raises(subject.DisposableBindingError):
        create(environment)


def test_both_callers_using_same_wrong_repository_are_rejected(environment):
    result = create(environment)
    public, genesis, view = verify(environment, result)
    event = pairs._pair_event(pair_id="synthetic-pair")
    event.update(schema_version=profile.SCHEMA, frozen_identities=view.pair_identities())
    binding = execution.PairBinding(EVALUATION, "synthetic-pair", "R2-SHAKEDOWN",
                                    event["category"], "Bookstore-Scraper",
                                    view.pair_identities(), view)
    with pytest.raises(execution.AttemptExecutionError):
        binding.validate_event(genesis, event)
    event["repository"] = view.repository
    replace(binding, repository=view.repository).validate_event(genesis, event)


@pytest.mark.parametrize("mutation", ["other_slot", "old_keys", "wrong_authority", "mixed_version"])
def test_v21_rejects_other_slots_old_or_mixed_identities(environment, mutation):
    result = create(environment)
    _, genesis, view = verify(environment, result)
    event = pairs._pair_event(pair_id="synthetic-pair")
    old = event["frozen_identities"]
    event.update(schema_version=profile.SCHEMA, repository=view.repository,
                 frozen_identities=view.pair_identities())
    if mutation == "other_slot": event["slot"] = "A1"
    if mutation == "old_keys": event["frozen_identities"] = old
    if mutation == "wrong_authority": event["frozen_identities"]["input_authority_sha256"] = "0" * 64
    if mutation == "mixed_version": event["schema_version"] = ledger.LEDGER_SCHEMA
    with pytest.raises(ledger.LedgerError):
        ledger.validate_ledger_events([genesis, event])


def test_v2_rejects_new_identity_shape():
    genesis = bootstrap.build_genesis_event(evaluation_id=EVALUATION, event_id=EVENT,
                                          timestamp_utc="2026-09-06T00:00:00Z")
    event = pairs._pair_event(pair_id="synthetic-pair")
    event["frozen_identities"] = authority().pair_identities()
    with pytest.raises(ledger.LedgerError):
        ledger.validate_ledger_events([genesis, event])


def test_exact_authority_view_rejects_mutation_and_returns_no_mutable_alias():
    view = authority()
    document = view.document()
    document["base_snapshot"]["source_repository"] = "wrong"
    assert view.repository == "ai-governance-framework"
    with pytest.raises(subject.DisposableBindingError):
        replace(view, raw=view.raw + b" ").document()


def test_generic_genesis_writer_cannot_publish_v21(environment):
    result = create(environment)
    public, genesis, _ = verify(environment, result)
    alternate = public.parent / "alternate.ndjson"
    with pytest.raises(ledger.LedgerError):
        ledger.create_genesis_ledger(alternate, genesis)
    assert not alternate.exists()


def test_generic_append_rejects_copied_v21_ledger_at_wrong_path(environment):
    result = create(environment)
    public, genesis, view = verify(environment, result)
    alternate = public.parent / "alternate.ndjson"
    alternate.write_bytes(public.read_bytes())
    event = pairs._pair_event(pair_id="synthetic-pair")
    event.update(schema_version=profile.SCHEMA, repository=view.repository,
                 frozen_identities=view.pair_identities())
    before = alternate.read_bytes()
    with pytest.raises(ledger.LedgerError):
        ledger.append_event(alternate, event)
    assert alternate.read_bytes() == before


def test_creation_authority_failure_precedes_rng_and_files(environment, monkeypatch):
    def fail(**kwargs):
        raise subject.DisposableBindingError()
    monkeypatch.setattr(subject, "load_input_authority", fail)
    monkeypatch.setattr(subject, "uuid4", lambda: pytest.fail("ID generated"))
    with pytest.raises(subject.DisposableBindingError):
        create(environment)
    assert not (environment.root / profile.LEDGER_PATH).parent.exists()
    assert not (environment.root / profile.BINDING_PATH).parent.exists()


def test_expected_evaluation_identity_cannot_be_taken_from_ledger(environment):
    result = create(environment)
    with pytest.raises(subject.DisposableBindingError):
        verify(environment, replace(result, evaluation_id=EVENT))


def test_genesis_whitespace_drift_fails_exact_identity(environment):
    result = create(environment)
    path = environment.root / profile.LEDGER_PATH
    path.write_bytes(path.read_bytes().replace(b'{', b'{ ', 1))
    with pytest.raises(subject.DisposableBindingError):
        verify(environment, result)


def test_pinned_git_mismatch_never_launches_or_generates_id(tmp_path, monkeypatch):
    from governance_tools import solo_r2_attempt_materialization as materialization
    git = PinnedExecutable.capture(Path(shutil.which("git")).resolve())
    repository = RepositoryBinding(REPO, REPO / ".git", REPO / ".git")
    monkeypatch.setattr(materialization.subprocess, "run", lambda *a, **k: pytest.fail("unverified executable launched"))
    monkeypatch.setattr(subject, "uuid4", lambda: pytest.fail("ID generated"))
    with pytest.raises(materialization.MaterializationError):
        subject.load_input_authority(git=replace(git, sha256="0" * 64),
                                     repository=repository, temp_root=tmp_path)


def test_loader_rejects_unavailable_committed_authority(tmp_path, monkeypatch):
    git = PinnedExecutable.capture(Path(shutil.which("git")).resolve())
    repository = RepositoryBinding(REPO, REPO / ".git", REPO / ".git")
    monkeypatch.setattr(subject, "verify_repository_binding", lambda *a, **k: None)
    def wrong_object(*args, **kwargs):
        command = args[2]
        if command[1:3] == ("cat-file", "-t"):
            return b"commit\n" if ":" not in command[3] else b"blob\n"
        return b"wrong committed bytes"
    monkeypatch.setattr(subject, "_run_git", wrong_object)
    with pytest.raises(subject.DisposableBindingError):
        subject.load_input_authority(git=git, repository=repository, temp_root=tmp_path)


def test_real_committed_authority_resolution_is_read_only(tmp_path, monkeypatch):
    # Only load_input_authority is invoked on REPO, never creation or Pair APIs.
    git = PinnedExecutable.capture(Path(shutil.which("git")).resolve())
    repository = RepositoryBinding(REPO, REPO / ".git", REPO / ".git")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "decoy"))
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(subject, "uuid4", lambda: pytest.fail("read generated an ID"))
    loaded = subject.load_input_authority(git=git, repository=repository, temp_root=tmp_path)
    assert loaded.raw == authority().raw
    assert not (REPO / profile.LEDGER_PATH).exists()
