"""External synthetic roots only; native launch is replaced, lifecycle is real."""
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import tarfile
import shutil

import pytest

from governance_tools import solo_r2_attempt_materialization as material
from governance_tools import solo_r2_attempt_execution as preflight
from governance_tools import solo_r2_disposable_execution as execution
from governance_tools import solo_r2_disposable_materialization as subject
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools import solo_r2_runtime_window as runtime
from governance_tools import solo_attempt_ledger_v2 as ledger
from tests.test_solo_r2_disposable_binding import environment, create, pair_args, authority, pairs, REPO
from tests.test_solo_r2_attempt_execution import _arm, _canary, _result, HOST_LOCAL, OFFLINE_SID, GENERATION


def archive(entries):
    out = BytesIO()
    with tarfile.open(fileobj=out, mode='w:') as stream:
        for name, raw, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(raw)
            stream.addfile(info, BytesIO(raw))
    return out.getvalue()


@pytest.fixture
def setup(environment, monkeypatch):
    env = environment
    created = create(env)
    pair = pairs.create_disposable_shakedown_pair(**pair_args(env, created))
    data = authority().document()
    entries = [(Path(i['path']).name, (REPO/i['path']).read_bytes(), tarfile.REGTYPE)
               for i in data['base_snapshot']['files']]
    state = SimpleNamespace(archive=archive(entries), entries=entries, calls=[], env=env, pair=pair)
    state.repaired=(REPO/data['reference_repair']['path']).read_bytes()
    def git(executable, repository, args, **kwargs):
        if 'archive' in args:
            assert args == ('--no-replace-objects','-c','core.autocrlf=false','archive','--format=tar',
                            data['base_snapshot']['commit']+':'+data['base_snapshot']['subdirectory'])
            return state.archive
        assert args[1:3] == ('cat-file','blob')
        return (REPO/data['task_prompt']['path']).read_bytes()
    monkeypatch.setattr(material, '_run_git', git)
    def acl(path):
        return material.LeafAclObservation(path, OFFLINE_SID, GENERATION.value, True, True)
    leaves = material.LeafWorkspaceManager(env.roots['materialization'], acl_probe=acl)
    mat = subject.DisposableGitMaterializer(authority=authority(), git=None,
        repository=env.args['repository'], leaves=leaves,
        packet=material.TreatmentInstruction.load(REPO/'artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md'))
    public = env.root/profile.LEDGER_PATH
    event = ledger.read_ledger(public)[1]
    bind = preflight.PairBinding(created.evaluation_id,pair.pair_id,event['slot'],event['category'],
                                 authority().repository,authority().pair_identities(),authority())
    lock = preflight.PairLedgerLock(ledger_path=public,lock_path=env.roots['controller-state']/'lock',
                                   binding=bind,expected_ledger_sha256=pair.ledger_sha256)
    order = runtime.SealedArmOrder.from_sealed_package(pair.checkpoint_path,
        key_path=env.key,custody_boundary=env.custody,expected_digest=pair.sealed_package_digest,pair_lock=lock)
    # Only machine readiness/native transport are synthetic; production preflight,
    # Pair binding, sealed state and complete lifecycle remain under test.
    window = object.__new__(runtime.PreAttemptFrozenRuntimeWindow)
    window.materializer=mat
    window.pair_lock=lock
    window.sealed_order=order
    window.freeze_probe=SimpleNamespace(repository_probe=object.__new__(execution.DisposableRepositoryFreezeProbe),
        assert_unchanged=lambda freeze: None,
        assert_execution_unchanged=lambda freeze, coordinator: coordinator._validated_events())
    def ready(self):
        with lock:
            evidence=mat.qualify_pair(pair.pair_id,HOST_LOCAL)
            validation=preflight.PreAttemptExecutionCoordinator(lock).validate(
                materialization=evidence,canary=_canary(),control=_arm(1),treatment=_arm(2))
            freeze = window.freeze_probe.capture() if hasattr(window.freeze_probe,'capture') else None
        return SimpleNamespace(freeze=freeze,prepared_control=_arm(1),prepared_treatment=_arm(2),validation=validation)
    monkeypatch.setattr(runtime.PreAttemptFrozenRuntimeWindow,'run',ready)
    def native(**kwargs):
        events=ledger.read_ledger(public)
        assert events[-1]['event_type']=='TASK_EXPOSED'
        assert kwargs['allow_non_git_workdir'] is True
        workspace=kwargs['workspace_root']
        assert set(p.name for p in workspace.iterdir())=={'queue_range.py','test_queue_range.py'}
        task=(REPO/data['task_prompt']['path']).read_bytes()
        expected=task if kwargs['prepared_arm'].arm_ordinal==1 else task+b'\n'+mat.packet.payload
        assert kwargs['prompt']==expected
        state.calls.append(kwargs)
        (workspace/'queue_range.py').write_bytes(state.repaired)
        return _result(kwargs['output_root'],'runtime','shell')
    window.backend=SimpleNamespace(native_backend=SimpleNamespace(execute=native,
        executable=SimpleNamespace(verify=lambda: None)),codex_home=env.roots['execution'])
    window.freeze_probe.backend=window.backend.native_backend
    args=dict(window=window,controller_root=env.roots['controller-state'],scoring_root=env.roots['scoring'],
              key_path=env.key,custody_boundary=env.custody,
              expected_genesis_binding_sha256=created.binding_sha256,expected_order_sha256=pair.sealed_package_digest)
    state.run=execution.DisposableArmExecution(**args)
    state.args=args
    state.mat=mat
    state.public=public
    return state


def test_disposable_pair_to_two_terminal_outputs_without_oracle_or_unblinding(setup):
    s=setup
    old=[p.read_bytes() for p in (s.env.original,s.env.replacement)]
    coordinator=s.run.run()
    events=ledger.read_ledger(s.public)
    assert [e['event_type'] for e in events]==['V2_GENESIS','PAIR_CREATED']+[
        'ATTEMPT_ADMITTED','TASK_EXPOSED','EXECUTION_TERMINAL']*2
    assert all(e['schema_version']=='solo_attempt_ledger.v2.1' for e in events)
    assert ledger.validate_ledger_file(s.public).initiated_attempt_count==2
    assert len(s.calls)==2 and s.mat.leaves.active is None
    for call in s.calls:
        output=call['output_root']
        assert (output/'queue_range.py').read_bytes()==s.repaired
        assert s.repaired!=s.entries[0][1]
        assert json.loads((output/'runtime-evidence.json').read_bytes())['input_authority_sha256']==profile.INPUT_SHA256
        assert call['prepared_arm'].execution_policy.max_elapsed_seconds==1800
        assert call['prepared_arm'].execution_policy.max_tool_calls==60
        assert call['prepared_arm'].execution_policy.retry_limit==0
    assert all(e['correctness_result']['oracle_status']=='NOT_RUN' for e in events if e['event_type']=='EXECUTION_TERMINAL')
    assert len(coordinator._terminal_outputs)==2
    assert all(json.loads(payload)['source'].encode()==s.repaired
               for _,payload in coordinator._terminal_outputs.values())
    assert [p.read_bytes() for p in (s.env.original,s.env.replacement)]==old
    with pytest.raises(material.MaterializationError): s.run.run()
    with pytest.raises(Exception): execution.DisposableArmExecution(**s.args).run()
    assert len(s.calls)==2


@pytest.mark.parametrize('kind',['parent','duplicate','missing','wrong-bytes','symlink','hardlink','absolute','traversal'])
def test_archive_mismatch_rejected_before_leaf_or_attempt(setup,kind):
    s=setup
    entries=list(s.entries)
    name,raw,typ=entries[0]
    if kind=='parent': entries.append(('evaluator/oracle.py',b'secret',typ))
    elif kind=='duplicate': entries.append(entries[0])
    elif kind=='missing': entries.pop()
    elif kind=='wrong-bytes': entries[0]=(name,b'x'*len(raw),typ)
    else: entries[0]=({'absolute':'/'+name,'traversal':'../'+name}.get(kind,name),raw,
                      {'symlink':tarfile.SYMTYPE,'hardlink':tarfile.LNKTYPE}.get(kind,typ))
    s.archive=archive(entries)
    before=s.public.read_bytes()
    with pytest.raises(material.MaterializationError): s.run.run()
    assert s.public.read_bytes()==before and not s.calls
    assert not list(s.mat.leaves.root.iterdir())


@pytest.mark.parametrize('field',['expected_genesis_binding_sha256','expected_order_sha256'])
def test_wrong_attach_identity_no_attempt_or_prompt(setup,field):
    s=setup
    s.run.attach_args[field]='0'*64
    before=s.public.read_bytes()
    with pytest.raises(Exception): s.run.run()
    assert s.public.read_bytes()==before and not s.calls


def test_exposure_append_failure_does_not_deliver_prompt(setup,monkeypatch):
    s=setup
    original=ledger.append_event
    def append(path,event):
        if event['event_type']=='TASK_EXPOSED': raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)
        return original(path,event)
    monkeypatch.setattr(ledger,'append_event',append)
    with pytest.raises(Exception): s.run.run()
    assert not s.calls
    assert ledger.validate_ledger_file(s.public).initiated_attempt_count==0
    assert list(s.env.roots['controller-state'].glob('*.execution-started'))


def test_native_failure_after_exposure_cannot_retry(setup):
    s=setup
    def fail(**kwargs):
        s.calls.append(kwargs)
        raise RuntimeError('synthetic transport failure')
    s.run.window.backend.native_backend.execute=fail
    with pytest.raises(RuntimeError): s.run.run()
    assert ledger.validate_ledger_file(s.public).initiated_attempt_count==1
    with pytest.raises(Exception): execution.DisposableArmExecution(**s.args).run()
    assert len(s.calls)==1 and s.mat.leaves.active is None


def test_materialization_authority_must_match_pair(setup):
    s=setup
    s.run.window.pair_lock.binding=replace(s.run.window.pair_lock.binding,input_authority=None)
    with pytest.raises(Exception): s.run.run()
    assert not s.calls and ledger.validate_ledger_file(s.public).admitted_attempt_count==0


def test_altered_treatment_packet_rejected_before_any_leaf(setup):
    s=setup
    s.mat.packet=replace(s.mat.packet,payload=b'not the frozen packet')
    with pytest.raises(material.MaterializationError): s.run.run()
    assert not list(s.mat.leaves.root.iterdir()) and not s.calls


@pytest.mark.parametrize('mutation',['none','repository','command','helper','generation'])
def test_real_freeze_probe_between_arms_allows_only_owned_ledger_progress(setup,monkeypatch,mutation):
    s=setup
    window=s.run.window
    marker=s.env.roots['controller-state']/'synthetic-executable'
    marker.write_bytes(b'non executable test marker')
    pin=material.PinnedExecutable.capture(marker.resolve())
    native=window.backend.native_backend
    native.executable=pin
    native.resolve_payload=lambda: pin
    native.owner_payload_pin=None
    state=SimpleNamespace(command=('pinned','exec'),generation=GENERATION,
        repository=runtime.RepositoryRuntimeIdentity('a'*40,
          runtime.RepositoryFileIdentity('runner',1,'b'*64),
          runtime.RepositoryFileIdentity('materializer',1,'c'*64),
          (runtime.RepositoryFileIdentity('disposable',1,'d'*64),)))
    native.command_policy_projection=lambda **kwargs: state.command
    repo=object.__new__(execution.DisposableRepositoryFreezeProbe)
    monkeypatch.setattr(execution.DisposableRepositoryFreezeProbe,'capture',lambda self: state.repository)
    window.freeze_probe=runtime.RuntimeFreezeProbe(backend=native,repository_probe=repo,
        qualification_helper=pin,generation_probe=lambda:state.generation,pair_lock=window.pair_lock,
        boundary_evidence=SimpleNamespace(validate=lambda:None,evidence_sha256='e'*64),
        assert_runtime_quiescent=lambda:None)
    original=native.execute
    def dispatch(**kwargs):
        result=original(**kwargs)
        if mutation=='repository': state.repository=replace(state.repository,disposable_sources=())
        elif mutation=='command': state.command=('different','exec')
        elif mutation=='helper': marker.write_bytes(b'changed helper')
        elif mutation=='generation': state.generation=replace(GENERATION,value='bad-generation')
        return result
    native.execute=dispatch
    if mutation=='none':
        s.run.run()
        assert len(s.calls)==2
    else:
        with pytest.raises(Exception): s.run.run()
        assert len(s.calls)==1
        assert ledger.validate_ledger_file(s.public).initiated_attempt_count==1


def test_real_pinned_git_exports_only_frozen_subtree_under_poisoned_environment(tmp_path,monkeypatch):
    from governance_tools.solo_r2_disposable_binding import load_input_authority
    git=material.PinnedExecutable.capture(Path(shutil.which('git')).resolve())
    repo=material.RepositoryBinding(REPO,REPO/'.git',REPO/'.git')
    monkeypatch.setenv('PATH',str(tmp_path))
    monkeypatch.setenv('GIT_DIR',str(tmp_path/'decoy'))
    loaded=load_input_authority(git=git,repository=repo,temp_root=tmp_path)
    leaves=material.LeafWorkspaceManager(tmp_path/'leaves',acl_probe=lambda p:
        material.LeafAclObservation(p,OFFLINE_SID,GENERATION.value,True,True))
    mat=subject.DisposableGitMaterializer(authority=loaded,git=git,repository=repo,leaves=leaves,
        packet=material.TreatmentInstruction.load(REPO/'artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md'))
    leaf=mat.materialize('synthetic-read-only-git-export')
    try:
        assert [(p.name,p.stat().st_size) for p in sorted(leaf.path.iterdir())]==[
            ('queue_range.py',187),('test_queue_range.py',529)]
        assert not (leaf.path/'.git').exists()
    finally: leaves.release(leaf)


@pytest.mark.parametrize('mutation',['test','extra','ledger'])
def test_post_arm_mismatch_never_becomes_terminal_output(setup,mutation):
    s=setup
    original=s.run.window.backend.native_backend.execute
    def dispatch(**kwargs):
        result=original(**kwargs)
        if mutation=='test': (kwargs['workspace_root']/'test_queue_range.py').write_bytes(b'changed')
        elif mutation=='extra': (kwargs['workspace_root']/'extra.py').write_bytes(b'extra')
        else:
            raw=s.public.read_bytes()
            changed=raw.replace(b'{',b'{ ',1)
            assert changed!=raw
            s.public.write_bytes(changed)
        return result
    s.run.window.backend.native_backend.execute=dispatch
    with pytest.raises(Exception): s.run.run()
    assert len(s.calls)==1
    assert not any(e['event_type']=='EXECUTION_TERMINAL' for e in ledger.read_ledger(s.public))


@pytest.mark.parametrize('name',['solo_r2_disposable_materialization','solo_r2_disposable_execution'])
def test_disposable_freeze_captures_actual_new_consumer_bytes(tmp_path,monkeypatch,name):
    repo=tmp_path/'repo'; repo.mkdir()
    committed=b'committed source\n'
    for relative in execution.DisposableRepositoryFreezeProbe.SOURCES:
        path=repo/relative; path.parent.mkdir(exist_ok=True); path.write_bytes(committed)
    legacy=runtime.RepositoryRuntimeIdentity('a'*40,
        runtime.RepositoryFileIdentity('runner',1,'b'*64),runtime.RepositoryFileIdentity('materializer',1,'c'*64))
    monkeypatch.setattr(runtime.GitRepositoryFreezeProbe,'capture',lambda self:legacy)
    monkeypatch.setattr(runtime,'_run_git',lambda *args,**kwargs:committed)
    probe=execution.DisposableRepositoryFreezeProbe(git=SimpleNamespace(verify=lambda:None),
        repository=SimpleNamespace(root=repo),temp_root=tmp_path)
    assert len(probe.capture().disposable_sources)==8
    (repo/'governance_tools'/f'{name}.py').write_bytes(b'changed source\n')
    with pytest.raises(runtime.RuntimeWindowError): probe.capture()


@pytest.mark.parametrize('mismatch',['backend','leaf-root'])
def test_miswired_runtime_rejected_before_readiness(setup,mismatch):
    s=setup
    if mismatch=='backend': s.run.window.freeze_probe.backend=object()
    else: s.mat.leaves.root=s.env.roots['scoring']
    before=s.public.read_bytes()
    with pytest.raises(material.MaterializationError): execution.DisposableArmExecution(**s.args)
    assert s.public.read_bytes()==before and not s.calls
