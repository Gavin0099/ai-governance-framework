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
from tests.test_solo_r2_replacement_binding import adopted

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('replacement_launcher', HERE / 'controller.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
POWERSHELL = 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'


@pytest.fixture
def phase(environment, monkeypatch, tmp_path):
    env = environment
    old = env.root / profile.LEDGER_PATH
    old.parent.mkdir()
    old.write_bytes((REPO / profile.LEDGER_PATH).read_bytes())
    base = tmp_path / 'replacement-only'
    monkeypatch.setattr(profile, 'REPLACEMENT_RUNTIME_ROOT', base)
    monkeypatch.setattr(c, 'BASE', base)
    monkeypatch.setattr(c, 'ROOT', env.root)
    monkeypatch.setattr(c, 'context', lambda *a: (None, env.args['repository']))
    monkeypatch.setattr(binding, 'load_replacement_authority', lambda **k: adopted())
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
    public=s.env.root/profile.REPLACEMENT_LEDGER_PATH
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
    if failure=='authority':monkeypatch.setattr(binding,'load_replacement_authority',reject)
    elif failure=='payload':s.manifest['candidate_payload']['sha256']='0'*64
    elif failure=='quiescence':s.modules['runtime']=NS(WindowsCodexRuntimeQuiescence=lambda **k:reject)
    else:(s.env.root/profile.REPLACEMENT_LEDGER_PATH).parent.mkdir()
    monkeypatch.setattr(custody,'create_controller_key',lambda *a,**k:pytest.fail('key created'))
    monkeypatch.setattr(binding,'uuid4',lambda:pytest.fail('ID generated'))
    with pytest.raises(RuntimeError):c.phase_a(s.modules,s.manifest)
    assert not s.base.exists()


def test_old_phase_a_identity_cannot_verify_against_new_pair(phase):
    s=phase;c.phase_a(s.modules,s.manifest)
    state=json.loads((s.base/'phase-a.json').read_bytes())
    bound=binding.load_replacement_ledger_binding(**s.env.args,
        expected_binding_sha256=state['binding_sha256'],expected_evaluation_id=state['evaluation_id'])
    state['evaluation_id']=json.loads(s.old.read_bytes().splitlines()[0])['evaluation_id']
    with pytest.raises(RuntimeError):c.verify_zero(s.modules,state,bound=bound)


def outer(path=HERE/'launch.ps1', *args, env=None):
    return subprocess.run([POWERSHELL,'-NoProfile','-File',str(path),*args],
        capture_output=True,text=True,env=env)


def test_outer_check_does_not_create_real_allocation():
    targets=[Path('D:/r2-replacement-disposable-shakedown-20260906'),REPO/profile.REPLACEMENT_LEDGER_PATH]
    before=[p.exists() for p in targets]
    result=outer(HERE/'launch.ps1','-Mode','check')
    assert result.returncode==0,result.stderr
    assert 'STATIC_BINDINGS_PASS' in result.stdout
    assert [p.exists() for p in targets]==before


@pytest.mark.parametrize('mode',['phase-b','controlled-readiness-and-wait'])
def test_outer_has_no_readiness_or_execution_mode(mode):
    result=outer(HERE/'launch.ps1','-Mode',mode)
    assert result.returncode!=0 and 'STATIC_BINDINGS_PASS' not in result.stdout


def wrapper_at(tmp_path, manifest=None):
    original=(HERE/'manifest.json').read_bytes()
    raw=original if manifest is None else c.canonical(manifest)
    (tmp_path/'manifest.json').write_bytes(raw)
    (tmp_path/'controller.py').write_bytes((HERE/'controller.py').read_bytes())
    wrapper=(HERE/'launch.ps1').read_text().replace(c.digest(original),c.digest(raw))
    wrapper=wrapper.replace("$Here = Join-Path $Root 'artifacts\\experiments\\solo-r2-replacement-disposable-launcher-20260906'", "$Here = '"+str(tmp_path)+"'")
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
