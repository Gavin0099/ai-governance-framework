import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import subprocess

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('disposable_launcher', HERE/'controller.py')
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(c, 'BASE', tmp_path)
    record = c.canonical(dict(schema='solo-r2-owner-payload-pin/v1',authority_class='OWNER_ATTESTED',
        evaluation_id='f024bb09-f7ae-4868-9b7d-e6e493f5c53b',pair_id='7ce56c1c-52df-43fd-ac70-20c6c8fd3588',
        slot='R2-SHAKEDOWN',payload_byte_length=123,payload_sha256='a'*64))
    (tmp_path/'payload-pin.candidate.json').write_bytes(record)
    obj=dict(evaluation_id=json.loads(record)['evaluation_id'],pair_id=json.loads(record)['pair_id'],
        payload_record_bytes=len(record),payload_record_sha256=c.digest(record),
        manifest_sha256=c.digest((HERE/'manifest.json').read_bytes()))
    (tmp_path/'phase-a.json').write_bytes(c.canonical(obj))
    return obj


def test_adopts_entire_exact_record_once(state):
    raw=c.adopt_record(state,'ADOPT '+state['payload_record_sha256'])
    assert (c.BASE/'payload-pin.adopted.json').read_bytes()==raw
    with pytest.raises(FileExistsError): c.adopt_record(state,'ADOPT '+state['payload_record_sha256'])


@pytest.mark.parametrize('answer',['','YES','ADOPT '+'a'*64])
def test_requires_full_record_adoption(state,answer):
    with pytest.raises(RuntimeError): c.adopt_record(state,answer)
    assert not (c.BASE/'payload-pin.adopted.json').exists()


@pytest.mark.parametrize('field',['evaluation_id','pair_id','payload_record_bytes','payload_record_sha256'])
def test_wrong_state_rejected(state,field):
    state[field]=0 if field=='payload_record_bytes' else 'wrong'
    with pytest.raises(RuntimeError): c.adopt_record(state,'ADOPT '+str(state['payload_record_sha256']))
    assert not (c.BASE/'payload-pin.adopted.json').exists()


def test_candidate_byte_drift_rejected(state):
    with (c.BASE/'payload-pin.candidate.json').open('ab') as stream: stream.write(b' ')
    with pytest.raises(RuntimeError): c.adopt_record(state,'ADOPT '+state['payload_record_sha256'])


def test_phase_b_rehashes_after_owner_adoption_before_runtime(state,monkeypatch):
    calls=[]
    monkeypatch.setattr(c,'verify_zero',lambda *args: calls.append('zero'))
    monkeypatch.setattr('builtins.input',lambda: 'ADOPT '+state['payload_record_sha256'])
    def resolve(**kwargs):
        assert (c.BASE/'payload-pin.adopted.json').exists()
        calls.append('rehash')
        raise RuntimeError('PAYLOAD_CHANGED')
    runner=NS(OwnerPayloadPin=lambda *a:a,resolve_codex_payload=resolve)
    material=NS(PinnedExecutable=lambda *a:a)
    with pytest.raises(RuntimeError,match='PAYLOAD_CHANGED'):
        c.phase_b(dict(runner=runner,runtime=NS(),material=material),{},c.digest(c.canonical(state)))
    assert calls==['zero','rehash']


def test_phase_b_wrong_state_before_adoption(state):
    with pytest.raises(RuntimeError,match='state identity'): c.phase_b({}, {}, '0'*64)
    assert not (c.BASE/'payload-pin.adopted.json').exists()


def test_phase_a_real_function_stops_without_runtime(tmp_path,monkeypatch,capsys):
    base=tmp_path/'new'; root=tmp_path/'repo'; root.mkdir()
    monkeypatch.setattr(c,'BASE',base); monkeypatch.setattr(c,'ROOT',root)
    calls=[]; authority=object()
    monkeypatch.setattr(c,'check_pin',lambda *a: calls.append('payload'))
    monkeypatch.setattr(c,'context',lambda *a: ('git','repo'))
    monkeypatch.setattr(c,'verify_zero',lambda *a: calls.append('verify_zero'))
    def create(**kwargs):
        calls.append('create')
        return NS(evaluation_id='evaluation',binding_sha256='binding',genesis_sha256='genesis')
    def pair(**kwargs):
        calls.append('pair')
        return NS(pair_id='pair',ledger_sha256='ledger',sealed_package_digest='sealed',checkpoint_path=base/'checkpoint')
    modules=dict(runtime=NS(WindowsCodexRuntimeQuiescence=lambda **k:lambda:calls.append('quiescence')),
        runner=NS(_windows_process_identity=lambda:NS(validate=lambda *a:calls.append('owner'))),
        binding=NS(load_input_authority=lambda **k:authority,create_disposable_evaluation=create,
            validate_disposable_pair_preconditions=lambda **k:(None,None,authority)),
        profile=NS(LEDGER_PATH=Path('public/ledger'),BINDING_PATH=Path('private/binding')),
        de=NS(DisposableRepositoryFreezeProbe=lambda **k:NS(capture=lambda:calls.append('freeze'))),
        custody=NS(CustodyBoundary=lambda *a:None,create_controller_key=lambda *a,**k:calls.append('key')),
        pairs=NS(validate_replacement_targets=lambda **k:None,create_disposable_shakedown_pair=pair))
    c.phase_a(modules,dict(candidate_payload=dict(bytes=123,sha256='a'*64)))
    assert calls==['quiescence','owner','payload','freeze','key','create','pair','payload','verify_zero']
    assert (base/'phase-a.json').exists()
    assert 'readiness NOT RUN' in capsys.readouterr().out
    assert not (base/'payload-pin.adopted.json').exists()


def test_outer_check_and_bad_state_argument():
    command=['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-File',str(HERE/'launch.ps1')]
    result=subprocess.run(command+['-Mode','check'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'STATIC_BINDINGS_PASS' in result.stdout
    result=subprocess.run(command+['-Mode','phase-b','-StateSha256','invalid'],capture_output=True,text=True)
    assert result.returncode!=0
    assert 'STATIC_BINDINGS_PASS' not in result.stdout


@pytest.mark.parametrize('target',['controller.py','manifest.json'])
def test_outer_rejects_changed_bytes_before_python(tmp_path,target):
    for name in ('controller.py','manifest.json'):
        (tmp_path/name).write_bytes((HERE/name).read_bytes())
    with (tmp_path/target).open('ab') as stream: stream.write(b' ')
    source=(HERE/'launch.ps1').read_text()
    source=source.replace("$Here = Join-Path $Root 'artifacts\\experiments\\solo-r2-disposable-launcher-20260906'", "$Here = '"+str(tmp_path)+"'")
    wrapper=tmp_path/'launch.ps1'; wrapper.write_text(source)
    result=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-File',str(wrapper),'-Mode','check'],capture_output=True,text=True)
    assert result.returncode!=0
    assert 'Digest mismatch' in result.stderr
    assert 'STATIC_BINDINGS_PASS' not in result.stdout


@pytest.mark.parametrize('change',['stdlib_hash','stdlib_inventory','python_hash'])
def test_outer_bootstrap_rejection_before_child(tmp_path,change):
    original=(HERE/'manifest.json').read_bytes()
    value=json.loads(original)
    if change=='stdlib_inventory':
        value['trees'][0]['files'].append(str(tmp_path/'unexpected.pyc'))
    else:
        suffix='\\Lib\\json\\__init__.py' if change=='stdlib_hash' else '\\.venv\\Scripts\\python.exe'
        entry=next(p for p in value['pins'] if p['path'].endswith(suffix))
        entry['sha256']='0'*64
    raw=c.canonical(value)
    (tmp_path/'manifest.json').write_bytes(raw)
    (tmp_path/'controller.py').write_bytes((HERE/'controller.py').read_bytes())
    source=(HERE/'launch.ps1').read_text().replace(c.digest(original),c.digest(raw))
    source=source.replace("$Here = Join-Path $Root 'artifacts\\experiments\\solo-r2-disposable-launcher-20260906'", "$Here = '"+str(tmp_path)+"'")
    wrapper=tmp_path/'launch.ps1'; wrapper.write_text(source)
    result=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-File',str(wrapper),'-Mode','check'],capture_output=True,text=True)
    assert result.returncode!=0
    assert ('inventory changed' if change=='stdlib_inventory' else 'Digest mismatch') in result.stderr
    assert 'STATIC_BINDINGS_PASS' not in result.stdout


@pytest.fixture
def refresh_setup(state,monkeypatch):
    for name in ('execution','materialization','scoring','consumer'): (c.BASE/name).mkdir()
    c.adopt_record(state,'ADOPT '+state['payload_record_sha256'])
    monkeypatch.setattr(c,'verify_zero',lambda *a: None)
    app=c.BASE/'installed'; child=app/'OpenAI/Codex/bin/1234'; child.mkdir(parents=True)
    (child/'codex.exe').write_bytes(b'new bytes')
    import re
    runner=NS(_closed_directory=lambda p:p,_windows_local_app_data_path=lambda:app,
        _PAYLOAD_DIRECTORY_NAME=re.compile('[0-9a-f]+'))
    payload=NS(byte_length=9,sha256=c.digest(b'new bytes'),verify=lambda:None)
    mods=dict(runner=runner,material=NS(PinnedExecutable=NS(capture=lambda p:payload)))
    return state,mods


def test_refresh_same_pair_preserves_old_adoption_and_stops(refresh_setup,capsys):
    state,mods=refresh_setup
    old=(c.BASE/'payload-pin.adopted.json').read_bytes()
    c.refresh_candidate(mods,{},c.digest(c.canonical(state)))
    fresh=json.loads((c.BASE/'payload-pin-refresh/payload-pin.candidate.json').read_bytes())
    assert fresh['pair_id']==state['pair_id'] and fresh['evaluation_id']==state['evaluation_id']
    assert (c.BASE/'payload-pin.adopted.json').read_bytes()==old
    assert not (c.BASE/'payload-pin-refresh/payload-pin.adopted.json').exists()
    assert 'candidate only; readiness NOT RUN' in capsys.readouterr().out
    with pytest.raises(RuntimeError,match='already exists'): c.refresh_candidate(mods,{},c.digest(c.canonical(state)))


@pytest.mark.parametrize('directory',['execution','materialization','scoring','consumer'])
def test_refresh_rejects_started_readiness(refresh_setup,directory):
    state,mods=refresh_setup
    (c.BASE/directory/'started').write_bytes(b'x')
    with pytest.raises(RuntimeError,match='already started'): c.refresh_candidate(mods,{},c.digest(c.canonical(state)))
    assert not (c.BASE/'payload-pin-refresh').exists()


def test_refresh_rejects_ledger_drift(refresh_setup,monkeypatch):
    state,mods=refresh_setup
    monkeypatch.setattr(c,'verify_zero',lambda *a:c.stop('ledger changed'))
    with pytest.raises(RuntimeError,match='ledger changed'): c.refresh_candidate(mods,{},c.digest(c.canonical(state)))
    assert not (c.BASE/'payload-pin-refresh').exists()


def test_refreshed_adoption_then_payload_recheck(refresh_setup,monkeypatch):
    state,mods=refresh_setup
    state_sha=c.digest(c.canonical(state))
    c.refresh_candidate(mods,{},state_sha)
    record=(c.BASE/'payload-pin-refresh/payload-pin.candidate.json').read_bytes()
    monkeypatch.setattr('builtins.input',lambda:'ADOPT '+c.digest(record))
    def resolve(**kwargs):
        assert (c.BASE/'payload-pin-refresh/payload-pin.adopted.json').read_bytes()==record
        raise RuntimeError('REHASH_AFTER_ADOPTION')
    mods['runner']=NS(OwnerPayloadPin=lambda *a:a,resolve_codex_payload=resolve)
    mods['material']=NS(PinnedExecutable=lambda *a:a);mods['runtime']=NS()
    with pytest.raises(RuntimeError,match='REHASH_AFTER_ADOPTION'): c.phase_b(mods,{},state_sha,c.digest(record))
    assert (c.BASE/'payload-pin.adopted.json').read_bytes()!=(c.BASE/'payload-pin-refresh/payload-pin.adopted.json').read_bytes()


def test_refresh_ambiguous_installed_payload(refresh_setup):
    state,mods=refresh_setup
    other=c.BASE/'installed/OpenAI/Codex/bin/5678';other.mkdir()
    (other/'codex.exe').write_bytes(b'other')
    with pytest.raises(RuntimeError,match='ambiguous'): c.refresh_candidate(mods,{},c.digest(c.canonical(state)))
    assert not (c.BASE/'payload-pin-refresh').exists()


def test_refresh_old_adoption_mismatch(refresh_setup):
    state,mods=refresh_setup
    (c.BASE/'payload-pin.owner-adoption.json').write_bytes(b'{}')
    with pytest.raises(RuntimeError,match='old adoption mismatch'): c.refresh_candidate(mods,{},c.digest(c.canonical(state)))


def test_refresh_wrong_pair_even_with_matching_caller_digest(refresh_setup):
    state,mods=refresh_setup
    sha=c.digest(c.canonical(state));c.refresh_candidate(mods,{},sha)
    directory=c.BASE/'payload-pin-refresh'
    value=json.loads((directory/'payload-pin.candidate.json').read_bytes())
    value['pair_id']='f024bb09-f7ae-4868-9b7d-e6e493f5c53b';raw=c.canonical(value)
    (directory/'payload-pin.candidate.json').write_bytes(raw)
    binding=json.loads((directory/'refresh-binding.json').read_bytes())
    binding.update(candidate_sha256=c.digest(raw),candidate_bytes=len(raw))
    (directory/'refresh-binding.json').write_bytes(c.canonical(binding))
    with pytest.raises(RuntimeError,match='changed Pair'): c.phase_b(mods,{},sha,c.digest(raw))
    assert not (directory/'payload-pin.adopted.json').exists()


def test_live_wait_ignores_blank_and_wrong_authorization(tmp_path,monkeypatch):
    calls=[]; window=object(); readiness=object()
    state=dict(pair_id='pair',evaluation_id='evaluation',binding_sha256='genesis',sealed_package_digest='order')
    p={k:tmp_path/k for k in ('execution','controller','scoring','keys')}
    p['execution'].mkdir()
    monkeypatch.setattr(c.secrets,'token_hex',lambda n:'nonce')
    answers=iter(['','EXECUTE wrong nonce','EXECUTE pair nonce'])
    def answer():
        assert not calls
        return next(answers)
    monkeypatch.setattr('builtins.input',answer)
    monkeypatch.setattr(c,'verify_zero',lambda *a:None)
    def constructor(**kwargs):
        assert kwargs['window'] is window
        assert (p['execution']/'owner-execution-authorization.json').exists()
        return NS(run=lambda **kw:calls.append(kw['previously_verified_readiness']))
    c.await_execution(dict(de=NS(DisposableArmExecution=constructor)),state,window,readiness,None,p)
    assert calls==[readiness]


def test_live_wait_eof_never_constructs_execution(tmp_path,monkeypatch):
    monkeypatch.setattr('builtins.input',lambda: (_ for _ in ()).throw(EOFError()))
    with pytest.raises(RuntimeError,match='disconnected'):
        c.await_execution({},dict(pair_id='pair'),object(),object(),None,{})


def test_live_wait_identity_drift_after_authorization_rejects(tmp_path,monkeypatch):
    monkeypatch.setattr(c.secrets,'token_hex',lambda n:'nonce')
    monkeypatch.setattr('builtins.input',lambda:'EXECUTE pair nonce')
    monkeypatch.setattr(c,'verify_zero',lambda *a:c.stop('ledger changed'))
    with pytest.raises(RuntimeError,match='ledger changed'):
        c.await_execution({},dict(pair_id='pair'),object(),object(),None,{})


def test_archive_renames_preserving_exact_evidence(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'BASE',tmp_path)
    state=dict(evaluation_id='1ebfbc48-d2fe-459d-bab7-b9fd75a5810b',pair_id='747c09b2-56d0-42d0-bc34-d505e23e311e')
    raw=c.canonical(dict(attempt=0,claim='readiness only; not transferable execution authority',
        **state,status='R2_READY_BEFORE_ATTEMPT_HANDLE_CREATION',task_exposure_state='NONE'))
    (tmp_path/'readiness-result.json').write_bytes(raw)
    for name in ('execution','materialization','scoring','consumer','temp'):
        (tmp_path/name).mkdir();(tmp_path/name/'evidence').write_bytes(name.encode())
    c.archive_readiness(state)
    archive=tmp_path/'historical-readiness-live-continuity-lost'
    assert (archive/'readiness-result.json').read_bytes()==raw
    for name in ('execution','materialization','scoring','consumer','temp'):
        assert (archive/name/'evidence').read_bytes()==name.encode()
        assert not list((tmp_path/name).iterdir())
    with pytest.raises(RuntimeError,match='reserved'): c.archive_readiness(state)


def test_archive_changed_historical_receipt_stops_before_mutation(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'BASE',tmp_path)
    (tmp_path/'readiness-result.json').write_bytes(b'{}')
    with pytest.raises(RuntimeError,match='historical readiness bytes changed'): c.archive_readiness({})
    assert not (tmp_path/'historical-readiness-live-continuity-lost').exists()


def test_execution_catalog_accepts_edit_events_but_not_unknown_tools():
    from governance_tools import solo_r2_codex_runner as runner
    catalog=c.execution_catalog(runner)
    trace=b'\n'.join(json.dumps(e).encode() for e in [
        {'type':'thread.started'}, {'type':'turn.started'},
        {'type':'item.started','item':{'id':'edit','type':'file_change'}},
        {'type':'item.completed','item':{'id':'edit','type':'file_change'}},
        {'type':'turn.completed'}])+b'\n'
    metrics=runner.derive_trace_metrics(trace)
    assert metrics.tool_call_count==1
    assert catalog.admits(metrics.observed_tool_inventory)
    assert catalog.admits(('command_execution','file_change'))
    assert not catalog.admits(('network_call',))
