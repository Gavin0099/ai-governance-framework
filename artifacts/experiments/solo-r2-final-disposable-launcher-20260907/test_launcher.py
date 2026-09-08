"""Static outer checks and synthetic Phase A only; no real allocation/runtime."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS

import pytest

from governance_tools import solo_r2_disposable_binding as binding
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools import solo_r2_pair_creation as pairs
from governance_tools import solo_r2_controller_state as custody
from governance_tools import solo_attempt_ledger_v2 as ledger
from tests.test_solo_r2_disposable_binding import environment, REPO
from tests.test_solo_r2_replacement_binding import final_adopted

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('final_launcher', HERE / 'controller.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
POWERSHELL = 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'


@pytest.fixture
def phase(environment, monkeypatch, tmp_path):
    env = environment
    old = env.root / profile.LEDGER_PATH
    old.parent.mkdir()
    old.write_bytes((REPO / profile.LEDGER_PATH).read_bytes())
    prior = env.root / profile.REPLACEMENT_LEDGER_PATH
    prior.parent.mkdir()
    prior.write_bytes((REPO / profile.REPLACEMENT_LEDGER_PATH).read_bytes())
    base = tmp_path / 'final-only' 
    monkeypatch.setattr(profile, 'FINAL_RUNTIME_ROOT', base)
    monkeypatch.setattr(c, 'BASE', base)
    monkeypatch.setattr(c, 'ROOT', env.root)
    monkeypatch.setattr(c, 'context', lambda *a: (None, env.args['repository']))
    monkeypatch.setattr(binding, 'load_final_authority', lambda **k: final_adopted())
    calls = []
    payload = tmp_path / 'inert-payload'; payload.write_bytes(b'not executable')
    manifest = {'candidate_payload': {'path': str(payload), 'bytes': 14, 'sha256': c.digest(payload.read_bytes())}}
    modules = dict(binding=binding, profile=profile, pairs=pairs, custody=custody, ledger=ledger,
        runtime=NS(WindowsCodexRuntimeQuiescence=lambda **k: lambda: calls.append('quiescence')),
        runner=NS(_windows_process_identity=lambda: NS(validate=lambda owner: calls.append('owner'))),
        de=NS(DisposableRepositoryFreezeProbe=lambda **k: NS(capture=lambda: calls.append('freeze'))))
    return NS(env=env, base=base, old=old, modules=modules, manifest=manifest, calls=calls)


def test_real_phase_a_uses_replacement_apis_and_stops_at_pin_candidate(phase, capsys):
    s=phase; before=s.old.read_bytes()
    c.phase_a(s.modules, s.manifest)
    public=s.env.root/profile.FINAL_LEDGER_PATH
    events=ledger.read_ledger(public); summary=ledger.validate_ledger_events(events)
    assert len(events)==2 and summary.initiated_attempt_count==0 and summary.admitted_attempt_count==0
    record=json.loads((s.base/'payload-pin.candidate.json').read_bytes())
    assert record['evaluation_id']==events[0]['evaluation_id']
    assert record['pair_id']==events[1]['pair_id']
    assert record['evaluation_id']!=json.loads(before.splitlines()[0])['evaluation_id']
    assert not (s.base/'payload-pin.adopted.json').exists()
    assert s.calls==['quiescence','owner','freeze']
    assert s.old.read_bytes()==before
    assert 'readiness NOT RUN; Attempt 0; exposure NONE' in capsys.readouterr().out
    with pytest.raises(RuntimeError,match='already exists'):c.phase_a(s.modules,s.manifest)
    assert public.read_bytes()==b''.join(ledger.encode_event(e) for e in events)


@pytest.mark.parametrize('failure',['authority','payload','quiescence','occupied'])
def test_failure_before_key_or_ids_preserves_allocation(phase,monkeypatch,failure):
    s=phase
    def reject(*a,**k):raise RuntimeError('fixture rejected')
    if failure=='authority':monkeypatch.setattr(binding,'load_final_authority',reject)
    elif failure=='payload':s.manifest['candidate_payload']['sha256']='0'*64
    elif failure=='quiescence':s.modules['runtime']=NS(WindowsCodexRuntimeQuiescence=lambda **k:reject)
    else:(s.env.root/profile.FINAL_LEDGER_PATH).parent.mkdir()
    monkeypatch.setattr(custody,'create_controller_key',lambda *a,**k:pytest.fail('key created'))
    monkeypatch.setattr(binding,'uuid4',lambda:pytest.fail('ID generated'))
    with pytest.raises(RuntimeError):c.phase_a(s.modules,s.manifest)
    assert not s.base.exists()


def test_old_phase_a_identity_cannot_verify_against_new_pair(phase):
    s=phase;c.phase_a(s.modules,s.manifest)
    state=json.loads((s.base/'phase-a.json').read_bytes())
    bound=binding.load_final_ledger_binding(**s.env.args,
        expected_binding_sha256=state['binding_sha256'],expected_evaluation_id=state['evaluation_id'])
    state['evaluation_id']=json.loads(s.old.read_bytes().splitlines()[0])['evaluation_id']
    with pytest.raises(RuntimeError):c.verify_zero(s.modules,state,bound=bound)


def outer(path=HERE/'launch.ps1', *args, env=None):
    return subprocess.run([POWERSHELL,'-NoProfile','-File',str(path),*args],
        capture_output=True,text=True,env=env)


def test_outer_check_does_not_create_real_allocation():
    targets=[Path('D:/r2-final-disposable-shakedown-20260907'),REPO/profile.FINAL_LEDGER_PATH]
    before=[p.exists() for p in targets]
    result=outer(HERE/'launch.ps1','-Mode','check')
    assert result.returncode==0,result.stderr
    assert 'STATIC_BINDINGS_PASS' in result.stdout
    assert [p.exists() for p in targets]==before


@pytest.mark.parametrize('mode',['refresh-payload-pin-candidate','controlled-readiness-and-wait'])
def test_outer_has_no_readiness_or_execution_mode(mode):
    result=outer(HERE/'launch.ps1','-Mode',mode)
    assert result.returncode!=0 and 'STATIC_BINDINGS_PASS' not in result.stdout


def wrapper_at(tmp_path, manifest=None):
    original=(HERE/'manifest.json').read_bytes()
    raw=original if manifest is None else c.canonical(manifest)
    (tmp_path/'manifest.json').write_bytes(raw)
    (tmp_path/'controller.py').write_bytes((HERE/'controller.py').read_bytes())
    wrapper=(HERE/'launch.ps1').read_text().replace(c.digest(original),c.digest(raw))
    wrapper=wrapper.replace("$Here = Join-Path $Root 'artifacts\\experiments\\solo-r2-final-disposable-launcher-20260907'", "$Here = '"+str(tmp_path)+"'")
    (tmp_path/'launch.ps1').write_text(wrapper)
    return tmp_path/'launch.ps1'


@pytest.mark.parametrize('target',['controller.py','manifest.json'])
def test_outer_rejects_changed_source_before_python(tmp_path,target):
    wrapper=wrapper_at(tmp_path)
    with (tmp_path/target).open('ab') as stream:stream.write(b' ')
    result=outer(wrapper,'-Mode','check')
    assert result.returncode!=0 and 'Digest mismatch' in result.stderr
    assert 'STATIC_BINDINGS_PASS' not in result.stdout


@pytest.mark.parametrize('kind',['python_hash','stdlib_inventory','binding_module'])
def test_outer_rejects_dependency_drift(tmp_path,kind):
    m=json.loads((HERE/'manifest.json').read_bytes())
    if kind=='stdlib_inventory':m['trees'][0]['files'].append(str(tmp_path/'unlisted.py'))
    else:
        suffix='\\.venv\\Scripts\\python.exe' if kind=='python_hash' else '\\governance_tools\\solo_r2_disposable_binding.py'
        next(p for p in m['pins'] if p['path'].endswith(suffix))['sha256']='0'*64
    result=outer(wrapper_at(tmp_path,m),'-Mode','check')
    assert result.returncode!=0 and 'STATIC_BINDINGS_PASS' not in result.stdout


def test_hostile_ambient_selectors_do_not_redirect_outer_check(tmp_path):
    marker=tmp_path/'executed'
    for name in ('python','git'):
        (tmp_path/(name+'.cmd')).write_text('@echo off\r\necho BAD>'+str(marker)+'\r\n')
    env=dict(os.environ,PATH=str(tmp_path),PYTHONPATH=str(tmp_path),GIT_DIR=str(tmp_path/'decoy'),
        GIT_WORK_TREE=str(tmp_path/'wrong'),COMSPEC=str(tmp_path/'cmd.exe'))
    result=outer(HERE/'launch.ps1','-Mode','check',env=env)
    assert result.returncode==0,result.stderr
    assert not marker.exists()


def test_payload_drift_rejected_without_creation(tmp_path):
    m=json.loads((HERE/'manifest.json').read_bytes());m['candidate_payload']['sha256']='0'*64
    result=outer(wrapper_at(tmp_path,m),'-Mode','check')
    assert result.returncode!=0 and 'STATIC_BINDINGS_PASS' not in result.stdout


@pytest.fixture
def phase_b_fixture(phase, monkeypatch):
    s = phase
    c.phase_a(s.modules, s.manifest)
    state_raw = (s.base/'phase-a.json').read_bytes()
    state = json.loads(state_raw)
    record = (s.base/'payload-pin.candidate.json').read_bytes()
    adoption = dict(status='OWNER_ADOPTED', allocation_sha256=profile.FINAL_DECISION_SHA256, record_sha256=c.digest(record), record_bytes=319,
        evaluation_id=state['evaluation_id'], pair_id=state['pair_id'],
        phase_a_state_sha256=c.digest(state_raw), verified_ledger_sha256=state['ledger_sha256'])
    # Phase A fixture uses small inert payload, so canonical record length differs.
    # Match production length without making this a real executable.
    value = json.loads(record); value['payload_byte_length'] = 295408944
    record = c.canonical(value)
    assert len(record) == 319
    (s.base/'payload-pin.candidate.json').write_bytes(record)
    state['payload_record_bytes'] = 319; state['payload_record_sha256'] = c.digest(record)
    state_raw = c.canonical(state); (s.base/'phase-a.json').write_bytes(state_raw)
    adoption.update(record_sha256=c.digest(record), phase_a_state_sha256=c.digest(state_raw))
    adopted_raw = c.canonical(adoption)
    directory = s.env.root/c.ADOPTION_DIR; directory.mkdir(parents=True, exist_ok=True)
    blobs = {'payload-pin.adopted.json': record, 'owner-adoption.json': adopted_raw}
    for n, raw in blobs.items(): (directory/n).write_bytes(raw)
    monkeypatch.setattr(c, 'ADOPTION_SHA', c.digest(adopted_raw))
    monkeypatch.setattr(c, 'ADOPTION_COMMIT', 'a'*40)
    monkeypatch.setattr(c, 'committed_blob', lambda modules, manifest, path: blobs[path.name])
    return NS(s=s, state=state, blobs=blobs, directory=directory)


def test_phase_b_verifies_bound_inputs_without_creation(phase_b_fixture, monkeypatch):
    x=phase_b_fixture
    monkeypatch.setattr(binding,'uuid4',lambda:pytest.fail('ID created'))
    state,bound,record=c.load_phase_b_inputs(x.s.modules,x.s.manifest)
    assert state==x.state and bound.evaluation_id==state['evaluation_id']
    assert record==x.blobs['payload-pin.adopted.json']


@pytest.mark.parametrize('target',['committed_pin','committed_adoption','working_adoption','state',
    'candidate','ledger','started','checkpoint'])
def test_phase_b_rejects_drift_before_runtime(phase_b_fixture,target):
    x=phase_b_fixture;s=x.s
    if target.startswith('committed_'):
        name='payload-pin.adopted.json' if target=='committed_pin' else 'owner-adoption.json'
        x.blobs[name]+=b' '
    else:
        path={'working_adoption':x.directory/'owner-adoption.json','state':s.base/'phase-a.json',
            'candidate':s.base/'payload-pin.candidate.json',
            'ledger':s.env.root/profile.FINAL_LEDGER_PATH,
            'started':s.base/'execution'/'already-started',
            'checkpoint':s.base/'controller'/'unexpected'}[target]
        with path.open('ab') as stream:stream.write(b' ')
    with pytest.raises(RuntimeError):c.load_phase_b_inputs(s.modules,s.manifest)


def test_phase_b_ready_keeps_same_live_objects_until_explicit_abort(phase_b_fixture,monkeypatch,capsys):
    x=phase_b_fixture;s=x.s
    ready=NS(disposition='READY',task_exposure_state='NONE',attempt_handle=None)
    calls=[]
    window=NS(run=lambda:(calls.append('run') or ready))
    boundary=object();paths=c.paths()
    monkeypatch.setattr(c,'build_readiness_window',lambda *args:(window,boundary,paths))
    s.modules['runtime']=NS(READY_BEFORE_ATTEMPT='READY')
    inputs=iter(['', 'EXECUTE wrong', 'ABORT'])
    original=c.wait_for_owner
    def waiting(state,w,r,b,p,bound,transition):
        assert w is window and r is ready and b is boundary and p is paths
        return original(state,w,r,b,p,bound,transition)
    monkeypatch.setattr(c,'wait_for_owner',waiting)
    monkeypatch.setattr(c,'execution_transition',lambda *args:('fixture',lambda *a:False))
    monkeypatch.setattr('builtins.input',lambda:next(inputs))
    with pytest.raises(RuntimeError,match='explicit owner abort'):c.phase_b(s.modules,s.manifest)
    assert calls==['run']
    assert capsys.readouterr().out.count('Not authorized. Still waiting.')==2
    assert len(ledger.read_ledger(s.env.root/profile.FINAL_LEDGER_PATH))==2


def test_wait_eof_does_not_return_or_authorize(monkeypatch):
    answers=iter([EOFError(),'ABORT']);slept=[]
    def read():
        a=next(answers)
        if isinstance(a,Exception):raise a
        return a
    monkeypatch.setattr('builtins.input',read);monkeypatch.setattr(c.time,'sleep',slept.append)
    with pytest.raises(RuntimeError,match='explicit owner abort'):
        c.wait_for_owner({},object(),object(),object(),{},object(),('fixture',lambda *args:pytest.fail('EOF authorized')))
    assert slept==[1]


def test_missing_home_rejected_before_native_runtime(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'HOME',tmp_path/'absent')
    with pytest.raises(RuntimeError,match='HOME missing'):c.build_readiness_window({}, {}, {}, None, b'')


@pytest.mark.parametrize('stale_payload',[False,True])
def test_window_assembly_uses_replacement_binding_and_rechecks_payload(phase_b_fixture,monkeypatch,tmp_path,stale_payload):
    x=phase_b_fixture;s=x.s
    state,bound,record=c.load_phase_b_inputs(s.modules,s.manifest)
    home=tmp_path/'dedicated-home';home.mkdir();monkeypatch.setattr(c,'HOME',home)
    made={};calls=[]
    def constructor(name):
        def create(*args,**kwargs):
            value=NS(args=args,kwargs=kwargs);made[name]=value;return value
        return create
    def resolve(**kwargs):
        calls.append('payload')
        if stale_payload:raise RuntimeError('stale payload')
        return NS(sha256='f'*64)
    runner=NS(OwnerPayloadPin=constructor('pin'),resolve_codex_payload=resolve,
        _windows_process_identity=lambda:NS(validate=lambda sid:calls.append('identity')),
        ToolCatalog=NS(project=constructor('catalog')),ToolDescriptor=lambda name:name,
        RuntimeIdentity=constructor('identity'),IDENTITY_DISPOSITION='fixture',
        NativeCodexExecBackend=constructor('native'),CodexRunnerAdapter=constructor('adapter'),
        capture_sandbox_generation=lambda **k:pytest.fail('native generation executed'))
    runtime=NS(WindowsCodexRuntimeQuiescence=lambda **k:lambda:calls.append('quiescence'),
        SealedArmOrder=NS(from_sealed_package=constructor('order')))
    for name in ['NativePreExposureObservationBackend','PreExposureBoundaryEvidenceProducer',
        'MachineBackedBoundaryProbe','OffHostControlEndpoint','RuntimeFreezeProbe','PreAttemptFrozenRuntimeWindow']:
        setattr(runtime,name,constructor(name))
    material=NS(PinnedExecutable=constructor('executable'),
        LeafWorkspaceManager=NS(for_windows_runtime=constructor('leaves')),
        TreatmentInstruction=NS(load=constructor('packet')))
    modules=dict(s.modules,runner=runner,runtime=runtime,material=material,
        attempt=NS(PairBinding=constructor('pair'),PairLedgerLock=constructor('lock')),
        dm=NS(DisposableGitMaterializer=constructor('materializer')))
    manifest={'executables':{name:dict(path='C:/fixture.exe',bytes=1,sha256='f'*64) for name in ['whoami','powershell']}}
    if stale_payload:
        with pytest.raises(RuntimeError,match='stale payload'):c.build_readiness_window(modules,manifest,state,bound,record)
        assert calls==['payload'] and not tuple((s.base/'execution').iterdir())
    else:
        window,boundary,p=c.build_readiness_window(modules,manifest,state,bound,record)
        assert calls==['payload','quiescence','identity']
        assert made['lock'].kwargs['ledger_path']==s.env.root/profile.FINAL_LEDGER_PATH
        assert made['lock'].kwargs['expected_ledger_sha256']==state['ledger_sha256']
        assert made['order'].kwargs['expected_digest']==state['sealed_package_digest']
        assert window.kwargs['backend'] is made['NativePreExposureObservationBackend']
        assert window.kwargs['adapter'] is made['adapter']
        assert window.kwargs['materializer'] is made['materializer']
        assert made['materializer'].kwargs['authority']==bound.input_authority


@pytest.fixture
def transition_fixture(phase_b_fixture,monkeypatch):
    x=phase_b_fixture;s=x.s
    state,bound,record=c.load_phase_b_inputs(s.modules,s.manifest)
    ready=NS(disposition='READY',task_exposure_state='NONE',attempt_handle=None)
    window=NS(backend=NS(native_backend=object()),adapter=object(),freeze_probe=object(),
        materializer=NS(leaves=object()),pair_lock=object(),sealed_order=object())
    window._issued_readiness=(ready,None,None,(window.backend,window.adapter,window.freeze_probe,
        window.materializer,window.pair_lock,window.sealed_order,window.backend.native_backend,
        window.materializer.leaves))
    calls=[]
    def execution(**kwargs):
        assert kwargs['window'] is window
        assert kwargs['replacement_binding'].evaluation_id==state['evaluation_id']
        assert kwargs['expected_genesis_binding_sha256']==state['binding_sha256']
        assert kwargs['expected_order_sha256']==state['sealed_package_digest']
        return NS(run=lambda **k:calls.append(k))
    s.modules.update(runner=NS(OwnerPayloadPin=lambda *a:a,resolve_codex_payload=lambda **k:None),
        material=NS(PinnedExecutable=lambda *a:a),de=NS(DisposableArmExecution=execution))
    command,execute=c.execution_transition(s.modules,s.manifest,state,window,ready,object(),c.paths(),bound)
    return NS(x=x,command=command,execute=execute,window=window,ready=ready,calls=calls)


def test_exact_authorization_invokes_execution_once_and_rejects_replay(transition_fixture):
    t=transition_fixture
    assert t.execute(t.command,t.window,t.ready) is True
    assert t.calls==[{'previously_verified_readiness':t.ready}]
    with pytest.raises(RuntimeError,match='already consumed'):t.execute(t.command,t.window,t.ready)
    assert len(t.calls)==1


@pytest.mark.parametrize('kind',['blank','space','malformed','evaluation','pair','nonce'])
def test_wrong_authorization_never_reaches_execution(transition_fixture,kind):
    t=transition_fixture;parts=t.command.split()
    if kind=='blank':answer=''
    elif kind=='space':answer=' '+t.command
    elif kind=='malformed':answer='EXECUTE'
    else:
        parts[{'evaluation':1,'pair':2,'nonce':3}[kind]]='wrong';answer=' '.join(parts)
    assert t.execute(answer,t.window,t.ready) is False and not t.calls
    assert not (t.x.s.base/'execution'/'owner-execution-authorization.json').exists()


@pytest.mark.parametrize('kind',['window','readiness','issued','consumed','backend','ledger','state','adoption','payload'])
def test_authorized_transition_rejects_current_drift(transition_fixture,kind):
    t=transition_fixture;s=t.x.s;window=t.window;ready=t.ready
    if kind=='window':window=NS(**vars(window))
    elif kind=='readiness':ready=NS(**vars(ready))
    elif kind=='issued':window._issued_readiness=tuple(list(window._issued_readiness))
    elif kind=='consumed':window._readiness_consumed=True
    elif kind=='backend':window.backend=NS(native_backend=object())
    elif kind=='payload':
        def reject(**kwargs):raise RuntimeError('payload changed')
        s.modules['runner'].resolve_codex_payload=reject
    else:
        path={'ledger':s.env.root/profile.FINAL_LEDGER_PATH,
            'state':s.base/'phase-a.json','adoption':t.x.directory/'owner-adoption.json'}[kind]
        with path.open('ab') as stream:stream.write(b' ')
    with pytest.raises(RuntimeError):t.execute(t.command,window,ready)
    assert not t.calls
    with pytest.raises(RuntimeError,match='already consumed'):t.execute(t.command,t.window,t.ready)


def test_live_wait_accepts_only_matching_authorization_after_blank_and_eof(transition_fixture,monkeypatch):
    t=transition_fixture;answers=iter(['',EOFError(),'EXECUTE wrong',t.command]);slept=[]
    def read():
        answer=next(answers)
        if isinstance(answer,Exception):raise answer
        return answer
    monkeypatch.setattr('builtins.input',read);monkeypatch.setattr(c.time,'sleep',slept.append)
    c.wait_for_owner(t.x.state,t.window,t.ready,object(),c.paths(),object(),(t.command,t.execute))
    assert slept==[1] and t.calls==[{'previously_verified_readiness':t.ready}]


@pytest.mark.parametrize('kind', ['allocation', 'evaluation', 'pair', 'payload-pair', 'old-manifest'])
def test_old_instance_authority_cannot_be_reused_even_with_new_adoption_hash(phase_b_fixture, monkeypatch, kind):
    x=phase_b_fixture
    adoption=json.loads(x.blobs['owner-adoption.json'])
    if kind=='allocation': adoption['allocation_sha256']=profile.REPLACEMENT_DECISION_SHA256
    elif kind in ('evaluation','pair'): adoption[kind+'_id']='747c09b2-56d0-42d0-bc34-d505e23e311e'
    elif kind=='payload-pair':
        value=json.loads(x.blobs['payload-pin.adopted.json']);value['pair_id']='747c09b2-56d0-42d0-bc34-d505e23e311e'
        raw=c.canonical(value);x.blobs['payload-pin.adopted.json']=raw
        (x.directory/'payload-pin.adopted.json').write_bytes(raw)
        adoption['record_sha256']=c.digest(raw)
    else:
        state=dict(x.state,manifest_sha256='0'*64);raw=c.canonical(state)
        (x.s.base/'phase-a.json').write_bytes(raw);adoption['phase_a_state_sha256']=c.digest(raw)
    raw=c.canonical(adoption);x.blobs['owner-adoption.json']=raw
    (x.directory/'owner-adoption.json').write_bytes(raw);monkeypatch.setattr(c,'ADOPTION_SHA',c.digest(raw))
    with pytest.raises(RuntimeError):c.load_phase_b_inputs(x.s.modules,x.s.manifest)


def test_previous_launcher_manifest_is_not_final_authority(monkeypatch):
    old=HERE.parent/'solo-r2-replacement-disposable-launcher-20260906/manifest.json'
    raw=old.read_bytes()
    monkeypatch.setattr(c,'regular',lambda path:raw)
    with pytest.raises(RuntimeError,match='wrong launcher allocation identity'):c.bootstrap(c.digest(raw))


def test_phase_b_without_owner_adoption_reference_stops(phase_b_fixture,monkeypatch):
    monkeypatch.setattr(c,'ADOPTION_COMMIT',None)
    with pytest.raises(RuntimeError,match='exact owner adoption'):c.load_phase_b_inputs(phase_b_fixture.s.modules,phase_b_fixture.s.manifest)


def test_no_old_instance_defaults_are_embedded():
    source=(HERE/'controller.py').read_text()
    for forbidden in ('8e3fb9fe-d94b-45d5-897c-3a3e75849bd8','eef1c2f5-91d7-4d8d-b765-251340f35d67','0edfdabdb50094e0fa72eb6edd6ab9c17987c917bd2f530908920cf7f2ef99e8'):
        assert forbidden not in source
