"""Replacement APIs exercised only on isolated synthetic custody/ledger roots."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from uuid import UUID

import pytest

from governance_tools import solo_r2_disposable_binding as binding
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_pair_creation as pairs
from governance_tools import solo_r2_controller_state as controller
from governance_tools.solo_r2_attempt_materialization import PinnedExecutable, RepositoryBinding
from tests.test_solo_r2_disposable_binding import environment, REPO, authority, pair_args, EVENT
from tests.test_solo_r2_disposable_execution import setup as execution_setup


def adopted():
    return binding.ReplacementAuthority(tuple((REPO / p).read_bytes()
        for _, p, _ in profile.REPLACEMENT_DOCUMENTS))


@pytest.fixture(params=[False, True], ids=["replacement", "final"])
def replacement(environment, monkeypatch, tmp_path, request):
    env = environment
    old = env.root / profile.LEDGER_PATH
    old.parent.mkdir()
    old.write_bytes((REPO / profile.LEDGER_PATH).read_bytes())
    final = request.param
    prior = env.root / profile.REPLACEMENT_LEDGER_PATH
    if final:
        prior.parent.mkdir()
        prior.write_bytes((REPO / profile.REPLACEMENT_LEDGER_PATH).read_bytes())
    base = tmp_path / ('final-runtime' if final else 'replacement-runtime')
    base.mkdir()
    for name in ('controller', 'keys', 'commitments', 'consumer', 'materialization', 'execution', 'scoring'):
        (base / name).mkdir()
    monkeypatch.setattr(profile, 'FINAL_RUNTIME_ROOT' if final else 'REPLACEMENT_RUNTIME_ROOT', base)
    monkeypatch.setattr(binding, 'load_replacement_authority', lambda **kwargs: adopted())
    env.custody = controller.CustodyBoundary(governance_root=env.root,
        **{name + '_root': base / name for name in ('consumer', 'materialization', 'execution', 'scoring')})
    env.key = base / 'keys/controller-key.json'
    controller.create_controller_key(env.key, custody_boundary=env.custody)
    env.roots = {name: base / name for name in ('consumer', 'materialization', 'execution', 'scoring')}
    env.roots.update({'controller-state': base / 'controller', 'controller-custody': base / 'commitments'})
    env.final = final
    env.history = [env.original, env.replacement, old] + ([prior] if final else [])
    env.binding_path = profile.FINAL_BINDING_PATH if final else profile.REPLACEMENT_BINDING_PATH
    env.decision = profile.FINAL_DECISION_SHA256 if final else profile.REPLACEMENT_DECISION_SHA256
    env.public = env.root / (profile.FINAL_LEDGER_PATH if final else profile.REPLACEMENT_LEDGER_PATH)
    monkeypatch.setattr(binding, 'load_final_authority', lambda **kwargs: final_adopted())
    env.old = old
    env.create = lambda e: (binding.create_final_disposable_evaluation if final else binding.create_replacement_disposable_evaluation)(**e.args)
    def create_pair(**kwargs):
        kwargs['commitment_path'] = base / 'commitments/sealed-package-digest.commitment'
        return (pairs.create_final_disposable_shakedown_pair if final else pairs.create_replacement_disposable_shakedown_pair)(**kwargs)
    env.create_pair = create_pair
    env.load_binding = lambda result: (binding.load_final_ledger_binding if final else binding.load_replacement_ledger_binding)(**env.args,
        expected_binding_sha256=result.binding_sha256, expected_evaluation_id=result.evaluation_id)
    return env


def pair_event():
    event = pairs._pair_event(pair_id=EVENT)
    event.update(schema_version=profile.SCHEMA, repository=authority().repository,
                 frozen_identities=authority().pair_identities())
    return event


def test_create_pair_and_append_are_bound_and_preserve_old_ledgers(replacement):
    env = replacement
    before = [p.read_bytes() for p in env.history]
    result = env.create(env)
    bound = env.load_binding(result)
    assert bound.evaluation_id == result.evaluation_id
    assert json.loads(bound.raw)['allocation_sha256'] == env.decision
    assert json.loads(bound.raw)['placement_sha256'] == env.decision
    pair = env.create_pair(**pair_args(env, result))
    events = ledger.read_ledger(env.public)
    assert len(events) == 2 and events[1]['pair_id'] == pair.pair_id
    assert events[1]['repository'] == authority().repository
    assert [p.read_bytes() for p in env.history] == before
    with pytest.raises(Exception):
        env.create_pair(**pair_args(env, result))


@pytest.mark.parametrize('kind', ['missing', 'old_binding', 'old_path', 'genesis', 'evaluation',
    'binding_file', 'decision', 'cost_authority', 'other_slot', 'arbitrary_path', 'repository'])
def test_wrong_append_binding_rejected_without_any_write(replacement, kind):
    env = replacement
    result = env.create(env)
    bound = env.load_binding(result)
    event = pair_event()
    path = env.public
    options = {'replacement_binding': bound}
    if kind == 'missing': options = {}
    elif kind == 'old_binding':
        old_event = json.loads(env.old.read_bytes().splitlines()[0])
        options['replacement_binding'] = replace(bound,
            raw=ledger.encode_event(binding._binding(env.root, old_event, env.old.read_bytes().splitlines(keepends=True)[0])))
    elif kind == 'old_path': path = env.old
    elif kind == 'genesis': options['replacement_binding'] = replace(bound, genesis=bound.genesis + b' ')
    elif kind == 'evaluation': options['replacement_binding'] = replace(bound, evaluation_id=EVENT)
    elif kind == 'binding_file':
        (env.root / env.binding_path).write_bytes(bound.raw + b' ')
    elif kind == 'decision':
        options['replacement_binding'] = replace(bound, authority=replace(bound.authority,
            documents=(b'wrong', *bound.authority.documents[1:])))
    elif kind == 'cost_authority': options['cost_authority'] = object()
    elif kind == 'other_slot': event['slot'] = 'A1'
    elif kind == 'repository': event['repository'] = 'Bookstore-Scraper'
    elif kind == 'arbitrary_path':
        path = env.root / 'other.ndjson';path.write_bytes(env.public.read_bytes())
    before = [p.read_bytes() for p in (env.public, env.old, path)]
    with pytest.raises(Exception): ledger.append_event(path, event, **options)
    assert [p.read_bytes() for p in (env.public, env.old, path)] == before


@pytest.mark.parametrize('kind', ['digest', 'evaluation', 'genesis', 'allocation', 'schema'])
def test_wrong_pre_pair_identity_rejects_before_pair_id(replacement, monkeypatch, kind):
    env = replacement;result = env.create(env)
    if kind == 'digest': result = replace(result, binding_sha256='0'*64)
    elif kind == 'evaluation': result = replace(result, evaluation_id=EVENT)
    elif kind == 'genesis': env.public.write_bytes(env.public.read_bytes() + b'\n')
    elif kind == 'allocation':
        path=env.root/env.binding_path;data=json.loads(path.read_bytes())
        data['allocation_sha256']=profile.ALLOCATION_SHA256;raw=ledger.encode_event(data)
        path.write_bytes(raw);result=replace(result,binding_sha256=hashlib.sha256(raw).hexdigest())
    else:
        data=json.loads(env.public.read_bytes());data['adopted_schema_id']='wrong'
        env.public.write_bytes(ledger.encode_event(data))
    monkeypatch.setattr(pairs, '_new_uuid4', lambda: pytest.fail('Pair ID generated before rejection'))
    with pytest.raises(Exception): env.create_pair(**pair_args(env,result))
    assert not list(env.roots['controller-state'].iterdir())


def test_second_allocation_rejects_before_uuid(replacement, monkeypatch):
    env=replacement;env.create(env)
    monkeypatch.setattr(binding,'uuid4',lambda:pytest.fail('second allocation generated ID'))
    with pytest.raises(binding.DisposableBindingError): env.create(env)


def test_failed_disposable_evaluation_collision_rejected(replacement, monkeypatch):
    env=replacement;old=json.loads(env.old.read_bytes().splitlines()[0])['evaluation_id']
    ids=iter((UUID(old),UUID(EVENT)));monkeypatch.setattr(binding,'uuid4',lambda:next(ids))
    with pytest.raises(binding.DisposableBindingError): env.create(env)
    assert not env.public.parent.exists()


def test_changed_historical_ledger_rejected_before_uuid(replacement, monkeypatch):
    env=replacement;env.old.write_bytes(env.old.read_bytes()+b'\n')
    monkeypatch.setattr(binding,'uuid4',lambda:pytest.fail('ID generated'))
    with pytest.raises(binding.DisposableBindingError):env.create(env)


def test_partial_creation_is_reserved_not_retried(replacement, monkeypatch):
    env=replacement;write=binding._write_once
    def fail(path,raw):
        if path==env.root/env.binding_path: raise OSError('fixture failure')
        return write(path,raw)
    monkeypatch.setattr(binding,'_write_once',fail)
    with pytest.raises(binding.DisposableBindingError):env.create(env)
    assert env.public.exists()
    monkeypatch.setattr(binding,'uuid4',lambda:pytest.fail('retry generated ID'))
    with pytest.raises(binding.DisposableBindingError):env.create(env)


def test_replacement_lifecycle_carries_binding_to_both_fresh_arms(replacement,monkeypatch):
    state=execution_setup.__wrapped__(replacement,monkeypatch)
    before=replacement.old.read_bytes()
    coordinator=state.execute()
    summary=ledger.validate_ledger_file(state.public)
    assert summary.initiated_attempt_count==2 and summary.terminal_execution_count==2
    assert len(coordinator._terminal_outputs)==2
    assert replacement.old.read_bytes()==before
    with pytest.raises(Exception):state.execute()


def test_old_custody_rejected_before_pair_id(replacement,monkeypatch):
    env=replacement;result=env.create(env);args=pair_args(env,result)
    args['controller_root']=env.root.parent/'controller-state'
    monkeypatch.setattr(pairs,'_new_uuid4',lambda:pytest.fail('Pair ID generated'))
    with pytest.raises(binding.DisposableBindingError):env.create_pair(**args)


def test_exact_committed_adoptions_resolve_read_only(tmp_path,monkeypatch):
    monkeypatch.setattr(profile, "ROOT", REPO)
    old=(REPO/profile.LEDGER_PATH).read_bytes()
    git=PinnedExecutable.capture(Path(shutil.which('git')).resolve())
    repo=RepositoryBinding(REPO,REPO/'.git',REPO/'.git')
    monkeypatch.setattr(binding,'uuid4',lambda:pytest.fail('read generated UUID'))
    got=binding.load_replacement_authority(git=git,repository=repo,temp_root=tmp_path)
    assert got==adopted()
    assert (REPO/profile.LEDGER_PATH).read_bytes()==old


def final_adopted():
    return binding.FinalAuthority(tuple((REPO / p).read_bytes() for _, p, _ in profile.FINAL_DOCUMENTS))


def test_final_exact_committed_adoption_resolves_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "ROOT", REPO)
    git = PinnedExecutable.capture(Path(shutil.which('git')).resolve())
    repo = RepositoryBinding(REPO, REPO/'.git', REPO/'.git')
    monkeypatch.setattr(binding, 'uuid4', lambda: pytest.fail('read generated ID'))
    assert binding.load_final_authority(git=git, repository=repo, temp_root=tmp_path) == final_adopted()


def test_final_rejects_prior_replacement_binding_and_ledger(replacement):
    env = replacement
    if not env.final:
        return
    result = env.create(env)
    bound = env.load_binding(result)
    before = [p.read_bytes() for p in [*env.history, env.public]]
    old_bound = binding.ReplacementLedgerBinding(adopted(), bound.raw,
        bound.evaluation_id, bound.genesis, bound.input_authority)
    with pytest.raises(Exception):
        ledger.append_event(env.public, pair_event(), replacement_binding=old_bound)
    with pytest.raises(Exception):
        ledger.append_event(env.root/profile.REPLACEMENT_LEDGER_PATH, pair_event(), replacement_binding=bound)
    assert [p.read_bytes() for p in [*env.history, env.public]] == before


def test_final_rejects_prior_replacement_id_before_publication(replacement, monkeypatch):
    env = replacement
    if not env.final:
        return
    old = json.loads((env.root/profile.REPLACEMENT_LEDGER_PATH).read_bytes().splitlines()[0])['evaluation_id']
    ids = iter([UUID(old), UUID(EVENT)])
    monkeypatch.setattr(binding, 'uuid4', lambda: next(ids))
    with pytest.raises(binding.DisposableBindingError):
        env.create(env)
    assert not env.public.parent.exists()


@pytest.mark.parametrize('historical', ['first', 'replacement'])
def test_final_rejects_historical_pair_before_sealing(replacement, monkeypatch, historical):
    env = replacement
    if not env.final:
        return
    result=env.create(env)
    old_path=profile.LEDGER_PATH if historical=='first' else profile.REPLACEMENT_LEDGER_PATH
    old_pair=json.loads((env.root/old_path).read_bytes().splitlines()[1])['pair_id']
    monkeypatch.setattr(pairs,'_new_uuid4',lambda:old_pair)
    before=env.public.read_bytes()
    with pytest.raises(Exception):env.create_pair(**pair_args(env,result))
    assert env.public.read_bytes()==before and not list(env.roots['controller-state'].iterdir())
    event=pair_event();event['pair_id']=old_pair
    with pytest.raises(Exception):ledger.append_event(env.public,event,replacement_binding=env.load_binding(result))
    assert env.public.read_bytes()==before
