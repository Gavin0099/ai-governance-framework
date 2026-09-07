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
    created = getattr(env, 'create', create)(env)
    pair = getattr(env, 'create_pair', pairs.create_disposable_shakedown_pair)(**pair_args(env, created))
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
    public = getattr(env, 'public', env.root/profile.LEDGER_PATH)
    event = ledger.read_ledger(public)[1]
    bind = preflight.PairBinding(created.evaluation_id,pair.pair_id,event['slot'],event['category'],
                                 authority().repository,authority().pair_identities(),authority())
    lock = preflight.PairLedgerLock(ledger_path=public,lock_path=env.roots['controller-state']/'lock',
                                   binding=bind,expected_ledger_sha256=pair.ledger_sha256)
    order = runtime.SealedArmOrder.from_sealed_package(pair.checkpoint_path,
        key_path=env.key,custody_boundary=env.custody,expected_digest=pair.sealed_package_digest,pair_lock=lock)
    # The real one-shot window and handoff run; only OS/native observations are doubles.
    from tests.test_solo_r2_runtime_window import FreezeProbeDouble, _freeze
    marker = env.roots['execution'] / 'inert-executable-marker'
    marker.write_bytes(b'not executable')
    pin = material.PinnedExecutable.capture(marker.resolve())
    freeze = replace(_freeze(pin, bind, GENERATION),
                     ledger_sha256=hashlib.sha256(public.read_bytes()).hexdigest())
    probe = FreezeProbeDouble(lock, freeze, pin)
    probe.repository_probe = object.__new__(execution.DisposableRepositoryFreezeProbe)
    probe.assert_execution_unchanged = lambda freeze, coordinator: coordinator._validated_events()
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
        return _result(kwargs['output_root'],'codex-trace','shell')
    backend=SimpleNamespace(native_backend=SimpleNamespace(execute=native,
        executable=pin, owner_payload_pin=None), codex_home=env.roots['execution'],
        whoami=pin, provision_sandbox=lambda: SimpleNamespace(generation_after=GENERATION),
        bind_freeze=lambda generation: None, prepared_ordinals=order.ordinals(),
        require_boundary_evidence=lambda: SimpleNamespace(validate=lambda:None,
            host_local=HOST_LOCAL,evidence_sha256='e'*64))
    adapter=SimpleNamespace(backend=backend, qualify_canary=lambda:_canary(),
                            prepare_formal_arm=lambda ordinal:_arm(ordinal))
    probe.backend=backend.native_backend
    window=runtime.PreAttemptFrozenRuntimeWindow(backend=backend,adapter=adapter,
        freeze_probe=probe,materializer=mat,pair_lock=lock,sealed_order=order)
    args=dict(window=window,controller_root=env.roots['controller-state'],scoring_root=env.roots['scoring'],
              key_path=env.key,custody_boundary=env.custody,
              expected_genesis_binding_sha256=created.binding_sha256,expected_order_sha256=pair.sealed_package_digest)
    if hasattr(env, 'load_binding'):
        args['replacement_binding'] = env.load_binding(created)
    state.run=execution.DisposableArmExecution(**args)
    state.execute=lambda: state.run.run(previously_verified_readiness=window.run())
    state.args=args
    state.mat=mat
    state.public=public
    return state


def test_disposable_pair_to_two_terminal_outputs_without_oracle_or_unblinding(setup):
    s=setup
    old=[p.read_bytes() for p in (s.env.original,s.env.replacement)]
    coordinator=s.execute()
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
    with pytest.raises(runtime.RuntimeWindowError): s.execute()
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
    with pytest.raises(material.MaterializationError): s.execute()
    assert s.public.read_bytes()==before and not s.calls
    assert not list(s.mat.leaves.root.iterdir())


@pytest.mark.parametrize('field',['expected_genesis_binding_sha256','expected_order_sha256'])
def test_wrong_attach_identity_no_attempt_or_prompt(setup,field):
    s=setup
    s.run.attach_args[field]='0'*64
    before=s.public.read_bytes()
    with pytest.raises(Exception): s.execute()
    assert s.public.read_bytes()==before and not s.calls


def test_exposure_append_failure_does_not_deliver_prompt(setup,monkeypatch):
    s=setup
    original=ledger.append_event
    def append(path,event):
        if event['event_type']=='TASK_EXPOSED': raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)
        return original(path,event)
    monkeypatch.setattr(ledger,'append_event',append)
    with pytest.raises(Exception): s.execute()
    assert not s.calls
    assert ledger.validate_ledger_file(s.public).initiated_attempt_count==0
    assert list(s.env.roots['controller-state'].glob('*.execution-started'))


def test_native_failure_after_exposure_cannot_retry(setup):
    s=setup
    def fail(**kwargs):
        s.calls.append(kwargs)
        raise RuntimeError('synthetic transport failure')
    s.run.window.backend.native_backend.execute=fail
    with pytest.raises(RuntimeError): s.execute()
    assert ledger.validate_ledger_file(s.public).initiated_attempt_count==1
    with pytest.raises(Exception): execution.DisposableArmExecution(**s.args).run()
    assert len(s.calls)==1 and s.mat.leaves.active is None
    failure=json.loads((s.calls[0]['output_root']/'execution-failure.json').read_bytes())
    assert failure['unavailable_metrics']==['tool_calls']
    assert failure['terminal_event_ready'] is False
    assert ledger.read_ledger(s.public)[-1]['event_type']=='TASK_EXPOSED'


def test_native_failure_with_retained_trace_is_terminal_and_never_retried(setup, monkeypatch):
    s=setup
    captured=[]
    handler=execution.DisposableArmExecution._record_exposed_failure
    def observe(coordinator, *args):
        captured.append(coordinator)
        return handler(coordinator, *args)
    monkeypatch.setattr(execution.DisposableArmExecution, '_record_exposed_failure', staticmethod(observe))
    original=s.run.window.backend.native_backend.execute
    def fail(**kwargs):
        original(**kwargs)  # Retain real-format trace, then simulate catalog rejection.
        raise RuntimeError('synthetic post-dispatch catalog rejection')
    s.run.window.backend.native_backend.execute=fail
    with pytest.raises(RuntimeError) as caught: s.execute()
    events=ledger.read_ledger(s.public)
    assert [e['event_type'] for e in events][-2:]==['TASK_EXPOSED','EXECUTION_TERMINAL'], repr(caught.value)
    assert events[-1]['correctness_result']['scope_status']=='NOT_EVALUATED'
    assert events[-1]['cost_metrics']['tool_calls']>=0
    assert len(s.calls)==1
    assert ledger.validate_ledger_file(s.public).initiated_attempt_count==1
    evidence=json.loads((s.calls[0]['output_root']/'execution-failure.json').read_bytes())
    assert evidence['disposition']=='UNCLASSIFIED' and evidence['terminal_event_ready']
    assert captured[0]._terminal_outputs == {}
    assert captured[0]._stopped
    with pytest.raises(Exception): captured[0].prepare_scoring()
    with pytest.raises(Exception): s.execute()
    assert len(s.calls)==1


def test_failure_evidence_write_error_cannot_append_or_continue(setup, monkeypatch):
    s=setup
    original=s.run.window.backend.native_backend.execute
    def fail(**kwargs):
        original(**kwargs)
        raise RuntimeError('synthetic post dispatch failure')
    s.run.window.backend.native_backend.execute=fail
    writer=execution._write_once
    def reject(path, raw):
        if path.name=='execution-failure.json': raise OSError('synthetic persistence failure')
        return writer(path, raw)
    monkeypatch.setattr(execution,'_write_once',reject)
    with pytest.raises(OSError): s.execute()
    assert ledger.read_ledger(s.public)[-1]['event_type']=='TASK_EXPOSED'
    with pytest.raises(Exception): s.execute()
    assert len(s.calls)==1 and s.mat.leaves.active is None


def test_malformed_failure_trace_never_fabricates_cost_or_terminal(setup):
    s=setup
    def fail(**kwargs):
        s.calls.append(kwargs)
        (kwargs['output_root']/'codex-trace.jsonl').write_bytes(b'invalid')
        raise RuntimeError('synthetic malformed trace')
    s.run.window.backend.native_backend.execute=fail
    with pytest.raises(RuntimeError): s.execute()
    failure=json.loads((s.calls[0]['output_root']/'execution-failure.json').read_bytes())
    assert failure['unavailable_metrics']==['tool_calls']
    assert 'tool_calls' not in failure['cost_metrics']
    assert ledger.read_ledger(s.public)[-1]['event_type']=='TASK_EXPOSED'


def test_failure_terminal_append_error_remains_stopped(setup,monkeypatch):
    s=setup; original=s.run.window.backend.native_backend.execute
    def fail(**kwargs):
        original(**kwargs)
        raise RuntimeError('synthetic post dispatch failure')
    s.run.window.backend.native_backend.execute=fail
    append=ledger.append_event
    def reject(path,event):
        if event['event_type']=='EXECUTION_TERMINAL': raise ledger.LedgerError('synthetic append failure')
        return append(path,event)
    monkeypatch.setattr(ledger,'append_event',reject)
    with pytest.raises(ledger.LedgerError): s.execute()
    assert (s.calls[0]['output_root']/'execution-failure.json').exists()
    assert ledger.read_ledger(s.public)[-1]['event_type']=='TASK_EXPOSED'
    with pytest.raises(Exception): s.execute()
    assert len(s.calls)==1


def test_materialization_authority_must_match_pair(setup):
    s=setup
    s.run.window.pair_lock.binding=replace(s.run.window.pair_lock.binding,input_authority=None)
    with pytest.raises(Exception): s.execute()
    assert not s.calls and ledger.validate_ledger_file(s.public).admitted_attempt_count==0


def test_altered_treatment_packet_rejected_before_any_leaf(setup):
    s=setup
    s.mat.packet=replace(s.mat.packet,payload=b'not the frozen packet')
    with pytest.raises(material.MaterializationError): s.execute()
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
        boundary_evidence=None,
        assert_runtime_quiescent=lambda:None)
    window.backend.whoami=pin
    window.backend.require_boundary_evidence=lambda: SimpleNamespace(validate=lambda:None,host_local=HOST_LOCAL,evidence_sha256="e"*64)
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
        s.execute()
        assert len(s.calls)==2
    else:
        with pytest.raises(Exception): s.execute()
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


@pytest.mark.parametrize('mutation',['unrelated-source','unrelated-test','extra','missing-test','ledger'])
def test_post_arm_mismatch_never_becomes_successful_output(setup,mutation):
    s=setup
    original=s.run.window.backend.native_backend.execute
    def dispatch(**kwargs):
        result=original(**kwargs)
        if mutation in ('unrelated-source','unrelated-test','extra'):
            name={'unrelated-source':'other.py','unrelated-test':'test_other.py','extra':'unexpected.txt'}[mutation]
            (kwargs['workspace_root']/name).write_bytes(b'extra')
        elif mutation=='missing-test': (kwargs['workspace_root']/'test_queue_range.py').unlink()
        else:
            raw=s.public.read_bytes()
            changed=raw.replace(b'{',b'{ ',1)
            assert changed!=raw
            s.public.write_bytes(changed)
        return result
    s.run.window.backend.native_backend.execute=dispatch
    with pytest.raises(Exception): s.execute()
    assert len(s.calls)==1
    terminals=[e for e in ledger.read_ledger(s.public) if e['event_type']=='EXECUTION_TERMINAL']
    if mutation=='ledger':
        assert not terminals
    else:
        assert len(terminals)==1 and terminals[0]['correctness_result']['scope_status']=='NOT_EVALUATED'


@pytest.mark.parametrize('changed', [('queue_range.py',), ('test_queue_range.py',),
                                    ('queue_range.py','test_queue_range.py')])
def test_frozen_task_authorized_changes_collected_without_false_rejection(setup, changed):
    s=setup
    original=s.run.window.backend.native_backend.execute
    baseline={name:raw for name,raw,_ in s.entries}
    assert set(baseline)=={'queue_range.py','test_queue_range.py'}
    def dispatch(**kwargs):
        result=original(**kwargs)
        for name,raw in baseline.items():
            # Reset the native double's source edit for the test-only case.
            payload=raw+b'\n# Direct regression coverage note\n' if name in changed else raw
            (kwargs['workspace_root']/name).write_bytes(payload)
        return result
    s.run.window.backend.native_backend.execute=dispatch
    s.execute()
    terminals=[e for e in ledger.read_ledger(s.public) if e['event_type']=='EXECUTION_TERMINAL']
    assert len(s.calls)==2 and len(terminals)==2
    assert all(e['correctness_result']['scope_status']=='WITHIN_SCOPE' for e in terminals)
    for call in s.calls:
        assert (call['output_root']/'runtime-evidence.json').is_file()
        assert not (call['output_root']/'execution-failure.json').exists()


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


def test_real_readiness_handoff_consumed_without_second_window_run(setup, monkeypatch):
    s = setup
    window = s.run.window
    readiness = window.run()
    before = s.public.read_bytes()
    assert readiness.disposition == runtime.READY_BEFORE_ATTEMPT
    assert window._used and not s.calls
    assert ledger.validate_ledger_file(s.public).admitted_attempt_count == 0
    with pytest.raises(runtime.RuntimeWindowError):
        window.run()
    def forbidden_run(self):
        pytest.fail('execution reran readiness')
    monkeypatch.setattr(runtime.PreAttemptFrozenRuntimeWindow, 'run', forbidden_run)
    s.run.run(previously_verified_readiness=readiness)
    assert len(s.calls) == 2 and s.public.read_bytes() != before
    with pytest.raises(Exception):
        execution.DisposableArmExecution(**s.args).run(previously_verified_readiness=readiness)
    assert len(s.calls) == 2


@pytest.mark.parametrize('mutation', [
    'missing', 'not-pass', 'clone', 'evaluation', 'pair', 'ledger', 'genesis',
    'authority', 'runtime', 'consumed', 'exposed', 'unissued', 'binding-pair',
    'native-backend', 'both-native-backends', 'leaf-manager',
])
def test_handoff_rejects_before_attempt(setup, mutation):
    s = setup
    window = s.run.window
    ready = window.run()
    if mutation == 'missing': ready = None
    elif mutation == 'not-pass': ready = replace(ready, disposition='FAIL')
    elif mutation == 'clone': ready = replace(ready)
    elif mutation in ('evaluation', 'pair'):
        object.__setattr__(ready, 'freeze', replace(ready.freeze, **{mutation+'_id':'wrong'}))
    elif mutation == 'ledger': s.public.write_bytes(s.public.read_bytes()+b'\n')
    elif mutation == 'genesis': s.run.attach_args['expected_genesis_binding_sha256']='0'*64
    elif mutation == 'authority': window.pair_lock.binding=replace(window.pair_lock.binding,input_authority=None)
    elif mutation == 'runtime': window.freeze_probe.freeze=replace(ready.freeze,payload_sha256='0'*64)
    elif mutation == 'consumed': window.consume_readiness(ready)
    elif mutation == 'exposed': object.__setattr__(ready,'task_exposure_state','TASK_EXPOSED')
    elif mutation == 'unissued': del window._issued_readiness
    elif mutation in ('native-backend', 'both-native-backends'):
        from copy import copy
        window.backend.native_backend=copy(window.backend.native_backend)
        if mutation == 'both-native-backends': window.freeze_probe.backend=window.backend.native_backend
    elif mutation == 'leaf-manager':
        from copy import copy
        window.materializer.leaves=copy(window.materializer.leaves)
    elif mutation == 'binding-pair': window.pair_lock.binding=replace(window.pair_lock.binding,pair_id='wrong')
    before = s.public.read_bytes()
    with pytest.raises(Exception): s.run.run(previously_verified_readiness=ready)
    assert s.public.read_bytes() == before
    assert not s.calls
    assert not list(s.env.roots['controller-state'].glob('*.execution-started'))
