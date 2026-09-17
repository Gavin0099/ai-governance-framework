"""R2 frozen-contract tests: real entrypoint, OS processes and exact release proof."""
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from jsonschema import Draft202012Validator

from governance_tools import shared_closeout_ownership as own
from governance_tools import session_closeout_entry as entry
from runtime_hooks.adapters.codex.session_start import run as start

FRAMEWORK = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'consumer with spaces'
    subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c',
                    'user.email=fixture@example.invalid', 'commit', '--quiet',
                    '--allow-empty', '-m', 'fixture'], check=True)
    (root/'AGENTS.md').write_text('# fixture\n', encoding='utf-8')
    (root/'governance').mkdir()
    (root/'evidence.txt').write_text('fixture evidence', encoding='utf-8')
    return root.resolve()


def start_session(root, sid='session-A'):
    start(dict(hook_event_name='SessionStart', source='startup', session_id=sid, cwd=str(root)), root)


def inputs(root, sid='session-A', version=1):
    candidate = dict(session_id=sid, generated_at=datetime.now(timezone.utc).isoformat(),
        task_intent=sid+' task', work_summary='Inspected evidence.txt for '+sid,
        tools_used=['inspect'], artifacts_referenced=['evidence.txt'], open_risks=[])
    data = json.dumps(candidate).encode()
    rel = f'artifacts/runtime/closeout_candidates/{sid}/{version:06}.json'
    text = (f'TASK_INTENT: {sid} task\nWORK_COMPLETED: Inspected evidence.txt for {sid}\n'
        'FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n'
        'NOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n').encode()
    return {'relative_path':rel, 'sha256':sha(data)}, data, text


def prepare(root, sid='session-A', version=1):
    start_session(root, sid)
    ci, data, text = inputs(root, sid, version)
    with own.execution_exclusion(root) as lease:
        record = own.acquire_owner(lease, sid, ci, sha(text))
        path = root/ci['relative_path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        (root/own.TEXT).write_bytes(text)
        own.confirm_prepared(lease, sid, record['generation'])
    return record


def owner(root):
    return json.loads((root/own.AREA/'owner.json').read_text(encoding='utf-8'))


def invoke(root, monkeypatch, sid='session-A'):
    monkeypatch.setattr(sys, 'argv', ['closeout', '--project-root', str(root),
        '--session-id', sid, '--agent-id', 'codex', '--trigger-mode', 'synthetic_smoke',
        '--format', 'json', '--no-ledger-write'])
    monkeypatch.setattr(sys, 'stdin', io.StringIO(''))
    return entry.main()


def subprocess_code(code, *args):
    return subprocess.run([sys.executable, '-B', '-c', code, *map(str, args)],
        cwd=FRAMEWORK, capture_output=True, text=True, encoding="utf-8", timeout=45,
        env={**os.environ, 'PYTHONIOENCODING':'utf-8'})


def test_formal_main_releases_gate_blocked_session_and_allows_next(repo, monkeypatch, capsys):
    prepare(repo)
    expected = sha((repo/own.TEXT).read_bytes())
    assert invoke(repo, monkeypatch) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['gate_policy']['blocked'] is True
    assert result['closeout_status'] == 'valid'
    receipt = json.loads(Path(result['closeout_receipt_artifact']).read_text(encoding="utf-8"))
    Draft202012Validator(json.loads((FRAMEWORK/'schemas/closeout_receipt.schema.json').read_text(encoding="utf-8"))).validate(receipt)
    assert receipt['checksum_of_cleaned_path'] == expected
    assert receipt['r2_binding']['session_id'] == 'session-A'
    assert receipt['r2_binding']['generation'] == 1
    assert owner(repo)['state'] == 'RELEASED'
    canonical = json.loads((repo/'artifacts/runtime/closeouts/session-A.json').read_text(encoding="utf-8"))
    assert canonical['task_intent'] == 'session-A task'
    prepare(repo, 'session-B')
    assert owner(repo)['generation'] == 2
    before = (repo/own.TEXT).read_bytes()
    assert invoke(repo, monkeypatch, 'session-A') == 1
    assert (repo/own.TEXT).read_bytes() == before


def test_B_and_same_owner_cannot_acquire_during_late_receipt_read(repo, monkeypatch):
    prepare(repo)
    real_checksum = entry._checksum_of_path
    late_attempts = []
    def checksum(path):
        if (repo/'artifacts/runtime/closeout-completions/session-A.json').exists():
            # Real second process must fail at OS exclusion, for either owner.
            result = subprocess_code('''
from pathlib import Path
import sys
from governance_tools.shared_closeout_ownership import execution_exclusion, OwnershipError
try:
    with execution_exclusion(Path(sys.argv[1])):
        raise AssertionError('unexpected lock acquisition')
except OwnershipError as exc:
    assert exc.code == 'R2_BUSY'
    print('blocked')
''', repo)
            assert result.returncode == 0, result.stderr
            assert result.stdout.strip() == 'blocked'
            late_attempts.append(True)
        return real_checksum(path)
    monkeypatch.setattr(entry, '_checksum_of_path', checksum)
    assert invoke(repo, monkeypatch) == 0
    assert len(late_attempts) >= 2  # stale checksum and final receipt checksum


def test_partial_prepare_survives_process_exit_and_retry_appends(repo):
    start_session(repo)
    ci, data, text = inputs(repo)
    with own.execution_exclusion(repo) as lease:
        own.acquire_owner(lease, 'session-A', ci, sha(text))
        p = repo/ci['relative_path']; p.parent.mkdir(parents=True); p.write_bytes(data)
    start_session(repo, 'session-B')
    bci, _, btext = inputs(repo, 'session-B')
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='OWNER_CONFLICT'):
            own.acquire_owner(lease, 'session-B', bci, sha(btext))
    prepare(repo, version=2)
    assert p.read_bytes() == data
    assert len(list(p.parent.glob('*.json'))) == 2
    assert owner(repo)['state'] == 'OWNED' and owner(repo)['generation'] == 2


@pytest.mark.parametrize('ambiguity', ['text', 'other-session', 'orphan-candidate', 'release-history'])
def test_initialization_refuses_legacy_or_unknown_state(repo, ambiguity):
    start_session(repo)
    if ambiguity == 'text':
        (repo/own.TEXT).write_bytes(b'legacy text')
    elif ambiguity == 'other-session':
        start_session(repo, 'session-B')
    elif ambiguity == 'orphan-candidate':
        path = repo/'artifacts/runtime/closeout_candidates/orphan/one.json'
        path.parent.mkdir(parents=True); path.write_text('{}')
    else:
        path = repo/own.AREA/'releases/1.json'
        path.parent.mkdir(parents=True); path.write_text('{}')
    ci, _, text = inputs(repo)
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='AMBIGUOUS_LEGACY_STATE'):
            own.acquire_owner(lease, 'session-A', ci, sha(text))
    assert not (repo/own.AREA/'owner.json').exists()


def test_main_missing_owner_never_enters_pipeline(repo, monkeypatch):
    start_session(repo)
    (repo/own.TEXT).write_bytes(b'legacy')
    monkeypatch.setattr(entry, 'run', lambda *a, **kw: pytest.fail('legacy fallback'))
    assert invoke(repo, monkeypatch) == 1
    assert not (repo/'artifacts/runtime/closeout-receipts').exists()


def test_crash_after_receipt_requires_exact_reconciliation(repo):
    prepare(repo)
    crashed = subprocess_code('''
import os,sys
from governance_tools import session_closeout_entry as entry
entry.ownership.finalize_release = lambda *a, **kw: os._exit(73)
sys.argv=['closeout','--project-root',sys.argv[1],'--session-id','session-A',
          '--agent-id','codex','--format','json','--no-ledger-write']
entry.main()
''', repo)
    assert crashed.returncode == 73, crashed.stderr
    held = owner(repo)
    assert held['state'] == 'HOLD' and held['receipt_identity']
    completion = repo/'artifacts/runtime/closeout-completions/session-A.json'
    completion_before = completion.read_bytes()
    start_session(repo, 'session-B')
    ci, _, text = inputs(repo, 'session-B')
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='OWNER_CONFLICT'):
            own.acquire_owner(lease, 'session-B', ci, sha(text))
    for sid, generation, rid in [('session-B',1,held['receipt_identity']),
                                 ('session-A',2,held['receipt_identity']), ('session-A',1,'f'*32)]:
        with pytest.raises(own.OwnershipError):
            own.reconcile_release(repo, sid, generation, rid)
    result = subprocess.run([sys.executable,'-B','-m','governance_tools.shared_closeout_ownership',
        'reconcile-release','--consumer-root',str(repo),'--session-id','session-A',
        '--generation','1','--receipt-identity',held['receipt_identity']],
        cwd=FRAMEWORK,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stderr+result.stdout
    assert json.loads(result.stdout)['status'] == 'RELEASED'
    assert completion.read_bytes() == completion_before
    assert own.reconcile_release(repo,'session-A',1,held['receipt_identity'])['status'] == 'ALREADY_RELEASED'
    prepare(repo,'session-B')
    with pytest.raises(own.OwnershipError):
        own.reconcile_release(repo,'session-A',1,held['receipt_identity'])


@pytest.mark.parametrize('conflict', [False, True])
def test_release_record_published_before_owner_transition_recovery(repo, monkeypatch, conflict):
    prepare(repo)
    original = own._publish
    def fail_owner(lease, relative, data, **kw):
        if relative.endswith('/owner.json') and data['state'] == 'RELEASED':
            raise OSError('crash before owner release')
        return original(lease, relative, data, **kw)
    monkeypatch.setattr(own, '_publish', fail_owner)
    assert invoke(repo, monkeypatch) == 1
    o = owner(repo); release = repo/own.AREA/'releases/1.json'
    assert release.exists() and o['state'] == 'HOLD'
    monkeypatch.setattr(own, '_publish', original)
    if conflict:
        release.write_bytes(b'{}')
        with pytest.raises(own.OwnershipError, match='RELEASE_PROOF_INVALID'):
            own.reconcile_release(repo, 'session-A', 1, o['receipt_identity'])
        assert release.read_bytes() == b'{}' and owner(repo)['state'] == 'HOLD'
    else:
        before = release.read_bytes()
        assert own.reconcile_release(repo,'session-A',1,o['receipt_identity'])['status']=='RELEASED'
        assert release.read_bytes() == before


def test_receipt_publication_failure_preserves_HOLD_and_consumption(repo, monkeypatch):
    prepare(repo)
    original_replace = Path.replace
    def failure(path, target):
        if Path(target).name.startswith('closeout_receipt_') and '_r2_' in Path(target).name:
            raise OSError('receipt publication failure')
        return original_replace(path, target)
    monkeypatch.setattr(Path, 'replace', failure)
    assert invoke(repo, monkeypatch) == 1
    o = owner(repo)
    assert o['state'] == 'HOLD'
    assert (repo/'artifacts/runtime/closeout-completions/session-A.json').exists()
    receipts = list((repo/'artifacts/runtime/closeout-receipts').glob('*.json'))
    assert len(receipts) == 1 and json.loads(receipts[0].read_text(encoding="utf-8"))['session_id'] == ''
    with pytest.raises(own.OwnershipError):
        own.reconcile_release(repo,'session-A',1,o['receipt_identity'])
    ci, _, text = inputs(repo, version=2)
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='CONSUMED_SESSION'):
            own.acquire_owner(lease, 'session-A', ci, sha(text))


def test_external_overwrite_is_detected_without_release(repo, monkeypatch):
    prepare(repo)
    original = entry._write_closeout_receipt
    def overwrite(*args, **kw):
        if kw.get('r2_lease') is not None:
            (repo/own.TEXT).write_bytes(b'external B writer ignores lock')
        return original(*args, **kw)
    monkeypatch.setattr(entry,'_write_closeout_receipt',overwrite)
    assert invoke(repo,monkeypatch) == 1
    assert owner(repo)['state'] == 'HOLD'
    assert not (repo/own.AREA/'releases').exists()


def test_os_lock_failure_has_no_local_mutex_fallback(repo, monkeypatch):
    start_session(repo)
    def failure(*args):
        raise OSError('backend unavailable')
    if os.name == 'nt':
        import msvcrt
        monkeypatch.setattr(msvcrt,'locking',failure)
    else:
        import fcntl
        monkeypatch.setattr(fcntl,'flock',failure)
    with pytest.raises(own.OwnershipError, match='R2_BUSY'):
        with own.execution_exclusion(repo):
            pytest.fail('must not enter without OS lock')
    assert not (repo/own.AREA/'owner.json').exists()


def test_expired_lease_cannot_mutate(repo):
    start_session(repo)
    with own.execution_exclusion(repo) as lease:
        pass
    ci, _, text = inputs(repo)
    with pytest.raises(own.OwnershipError, match='R2_BUSY'):
        own.acquire_owner(lease,'session-A',ci,sha(text))


def test_schema_legacy_and_strict_extension(repo, monkeypatch, capsys):
    prepare(repo)
    assert invoke(repo,monkeypatch) == 0
    result=json.loads(capsys.readouterr().out)
    receipt=json.loads(Path(result['closeout_receipt_artifact']).read_text(encoding="utf-8"))
    validator=Draft202012Validator(json.loads((FRAMEWORK/'schemas/closeout_receipt.schema.json').read_text(encoding="utf-8")))
    validator.validate(receipt)
    legacy=copy.deepcopy(receipt); del legacy['r2_binding']; validator.validate(legacy)
    changes=[{'generation':0},{'generation':True},{'generation':'1'},
             {'expected_text_digest':'bad'},{'receipt_identity':'../x'},
             {'unknown':'reject'},{'schema_version':'2.0'},{'candidate_identity':{}},
             {'candidate_identity':{'relative_path':'one.json','sha256':'a'*64,'extra':True}}]
    for change in changes:
        invalid=copy.deepcopy(receipt); invalid['r2_binding'].update(change)
        assert list(validator.iter_errors(invalid)),change
    for key in receipt['r2_binding']:
        invalid=copy.deepcopy(receipt); del invalid['r2_binding'][key]
        assert list(validator.iter_errors(invalid)),key
    invalid=copy.deepcopy(receipt); invalid['schema_version']='1.4'
    assert list(validator.iter_errors(invalid))


def test_initial_owner_publication_failure_leaves_no_claim(repo, monkeypatch):
    start_session(repo)
    ci, _, text=inputs(repo)
    monkeypatch.setattr(Path,'replace',lambda *a: (_ for _ in ()).throw(OSError('publish failure')))
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(OSError):
            own.acquire_owner(lease,'session-A',ci,sha(text))
    assert not (repo/own.AREA/'owner.json').exists()
    assert not (repo/own.TEXT).exists()

@pytest.mark.parametrize('directory', ['verdicts', 'traces', 'summaries', 'candidates', 'curated'])
def test_initialization_rejects_orphan_pipeline_evidence(repo, directory):
    start_session(repo)
    path = repo/'artifacts/runtime'/directory/'orphan.json'
    path.parent.mkdir(parents=True); path.write_text('{}', encoding='utf-8')
    ci, _, text = inputs(repo)
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='AMBIGUOUS_LEGACY_STATE'):
            own.acquire_owner(lease, 'session-A', ci, sha(text))
    assert not (repo/own.AREA/'owner.json').exists()


def test_receipt_names_preserve_existing_latest_reader(repo, monkeypatch):
    prepare(repo)
    assert invoke(repo, monkeypatch) == 0
    first = entry._latest_receipt_checksum(repo)
    prepare(repo, 'session-B')
    expected = sha((repo/own.TEXT).read_bytes())
    assert expected != first
    assert invoke(repo, monkeypatch, 'session-B') == 0
    assert entry._latest_receipt_checksum(repo) == expected


def test_simultaneous_process_acquisition_has_one_owner(repo, monkeypatch):
    prepare(repo)
    assert invoke(repo, monkeypatch) == 0
    for sid in ['session-B', 'session-C']:
        start_session(repo, sid)
    code = '''
import json,sys
from pathlib import Path
from governance_tools import shared_closeout_ownership as own
root=Path(sys.argv[1]); sid=sys.argv[2]
print('ready',flush=True)
sys.stdin.readline()
try:
    with own.execution_exclusion(root) as lease:
        own.acquire_owner(lease,sid,{'relative_path':f'artifacts/runtime/closeout_candidates/{sid}/new.json','sha256':'a'*64},'b'*64)
    print('acquired',flush=True)
except own.OwnershipError as exc:
    print(exc.code,flush=True)
'''
    children = [subprocess.Popen([sys.executable, '-B', '-c', code, str(repo), sid],
        cwd=FRAMEWORK, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True) for sid in ['session-B', 'session-C']]
    try:
        for child in children:
            assert child.stdout.readline().strip() == 'ready'
        for child in children:
            child.stdin.write('go\n'); child.stdin.flush()
        results = [child.communicate(timeout=30) for child in children]
        assert all(child.returncode == 0 for child in children), results
        statuses = [out.strip() for out, _ in results]
        assert statuses.count('acquired') == 1, statuses
        assert all(status in {'acquired', 'OWNER_CONFLICT', 'R2_BUSY'} for status in statuses)
        assert owner(repo)['generation'] == 2
    finally:
        for child in children:
            if child.poll() is None:
                child.kill(); child.wait()


@pytest.mark.parametrize('damage', ['missing-field', 'boolean-generation', 'different-root'])
def test_reconciliation_rejects_tampered_reserved_receipt(repo, monkeypatch, damage):
    prepare(repo)
    original = own.finalize_release
    monkeypatch.setattr(own, 'finalize_release', lambda *a: (_ for _ in ()).throw(OSError('stop')))
    assert invoke(repo, monkeypatch) == 1
    held = owner(repo)
    receipt = repo/own._receipt_relative(held)
    payload = json.loads(receipt.read_text(encoding='utf-8'))
    if damage == 'missing-field':
        del payload['agent_id']
    elif damage == 'boolean-generation':
        payload['r2_binding']['generation'] = True
    else:
        payload['r2_binding']['consumer_root'] = str(repo.parent)
    receipt.write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.setattr(own, 'finalize_release', original)
    with pytest.raises(own.OwnershipError, match='RELEASE_PROOF_INVALID'):
        own.reconcile_release(repo, 'session-A', 1, held['receipt_identity'])
    assert owner(repo)['state'] == 'HOLD'
    assert not (repo/own.AREA/'releases').exists()


def test_manual_fallback_rejects_before_any_closeout_mutation(repo, monkeypatch, capsys):
    prepare(repo)
    before = {str(p.relative_to(repo)): p.read_bytes() for p in (repo/'artifacts').rglob('*') if p.is_file()}
    monkeypatch.setattr(entry, 'run', lambda *a, **kw: pytest.fail('pipeline must not start'))
    monkeypatch.setattr(sys, 'argv', ['closeout', '--project-root', str(repo),
        '--session-id', 'session-A', '--agent-id', 'codex', '--trigger-mode',
        'manual_fallback', '--format', 'json', '--no-ledger-write'])
    monkeypatch.setattr(sys, 'stdin', io.StringIO(''))
    assert entry.main() == 1
    assert 'manual_fallback receipt production is not qualified' in json.loads(capsys.readouterr().out)['error']
    after = {str(p.relative_to(repo)): p.read_bytes() for p in (repo/'artifacts').rglob('*') if p.is_file()}
    assert before == after
    assert owner(repo)['state'] == 'OWNED'
    assert not (repo/'artifacts/runtime/closeout-completions/session-A.json').exists()


def test_R2_rejects_legacy_envelope_without_rewriting_it(repo):
    from runtime_hooks.core._canonical_closeout import write_session_envelope
    write_session_envelope('legacy', repo, provider='test')
    envelope = repo/'artifacts/runtime/sessions/legacy/session-envelope.json'
    before = envelope.read_bytes()
    ci, _, text = inputs(repo, 'legacy')
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='qualified R1 binding required'):
            own.acquire_owner(lease, 'legacy', ci, sha(text))
    assert envelope.read_bytes() == before
    assert not (repo/own.AREA/'owner.json').exists()


@pytest.mark.parametrize('candidate_path', ['../outside.json', 'artifacts/runtime/closeout_candidates/session-B/one.json'])
def test_candidate_containment_rejects_before_owner_mutation(repo, candidate_path):
    start_session(repo)
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='INVALID_OWNER'):
            own.acquire_owner(lease, 'session-A', {'relative_path':candidate_path, 'sha256':'a'*64}, 'b'*64)
    assert not (repo/own.AREA/'owner.json').exists()
    assert not (repo/own.TEXT).exists()


def test_R2_helper_imports_with_site_packages_disabled():
    result = subprocess.run([sys.executable, '-S', '-B', '-c',
        'from governance_tools import shared_closeout_ownership'], cwd=FRAMEWORK,
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_protected_main_does_not_require_jsonschema(repo):
    prepare(repo)
    # Existing core imports PyYAML; isolate the NEW dependency without pretending
    # this slice has made that pre-existing core entirely dependency-free.
    result = subprocess_code("""
import builtins,sys
original=builtins.__import__
def without_jsonschema(name,*args,**kwargs):
    if name == 'jsonschema' or name.startswith('jsonschema.'):
        raise ModuleNotFoundError('jsonschema intentionally unavailable')
    return original(name,*args,**kwargs)
builtins.__import__=without_jsonschema
from governance_tools import session_closeout_entry as entry
sys.argv=['closeout','--project-root',sys.argv[1],'--session-id','session-A',
          '--agent-id','codex','--format','json','--no-ledger-write']
raise SystemExit(entry.main())
""", repo)
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout)['closeout_status'] == 'valid'
    assert owner(repo)['state'] == 'RELEASED'


@pytest.mark.parametrize('payload_kind', ['text', 'candidate'])
def test_released_owner_requires_retained_payloads_before_reconcile_or_acquire(repo, monkeypatch, payload_kind):
    prepare(repo)
    assert invoke(repo, monkeypatch) == 0
    held = owner(repo)
    target = repo/(own.TEXT if payload_kind == 'text' else held['candidate_identity']['relative_path'])
    target.write_bytes(b'corrupted after release')
    owner_before = (repo/own.AREA/'owner.json').read_bytes()
    with pytest.raises(own.OwnershipError, match='PAYLOAD_MISMATCH'):
        own.reconcile_release(repo, 'session-A', held['generation'], held['receipt_identity'])
    start_session(repo, 'session-B')
    ci, _, text = inputs(repo, 'session-B')
    with own.execution_exclusion(repo) as lease:
        with pytest.raises(own.OwnershipError, match='PAYLOAD_MISMATCH'):
            own.acquire_owner(lease, 'session-B', ci, sha(text))
    assert (repo/own.AREA/'owner.json').read_bytes() == owner_before
    assert not (repo/ci['relative_path']).exists()


def test_stdlib_receipt_validation_matches_schema_matrix(repo, monkeypatch, capsys):
    prepare(repo)
    assert invoke(repo, monkeypatch) == 0
    result = json.loads(capsys.readouterr().out)
    receipt = json.loads(Path(result['closeout_receipt_artifact']).read_text(encoding='utf-8'))
    schema = json.loads((FRAMEWORK/'schemas/closeout_receipt.schema.json').read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema)
    own._receipt_schema(receipt)
    cases = []
    for key in schema['required']:
        invalid = copy.deepcopy(receipt); del invalid[key]; cases.append(invalid)
    for key in receipt['r2_binding']:
        invalid = copy.deepcopy(receipt); del invalid['r2_binding'][key]; cases.append(invalid)
    for key in receipt:
        invalid = copy.deepcopy(receipt); invalid[key] = None; cases.append(invalid)
    for status in ['written', 'already_present', 'failed']:
        invalid = copy.deepcopy(receipt); invalid['daily_memory_write_status'] = status; cases.append(invalid)
    for field, value in [('generation',True),('expected_text_digest','bad'),
                         ('receipt_identity','../bad'),('candidate_identity',{'relative_path':'x','sha256':'bad'}),
                         ('unexpected',True)]:
        invalid = copy.deepcopy(receipt); invalid['r2_binding'][field] = value; cases.append(invalid)
    for field, value in [('schema_version','1.4'),('trigger_mode','manual_fallback'),
                         ('exit_code',True),('unexpected',True),('memory_unbound_count',-1),
                         ('memory_workflow_warning_codes',[1])]:
        invalid = copy.deepcopy(receipt); invalid[field] = value; cases.append(invalid)
    numeric = copy.deepcopy(receipt)
    numeric['exit_code'] = 0.0
    numeric['memory_unbound_count'] = 0.0
    numeric['r2_binding']['generation'] = 1.0
    assert validator.is_valid(numeric)
    cases.append(numeric)
    assert sum(not validator.is_valid(case) for case in cases) > 50
    for case in cases:
        if validator.is_valid(case):
            own._receipt_schema(case)
        else:
            with pytest.raises(own.OwnershipError, match='RELEASE_PROOF_INVALID'):
                own._receipt_schema(case)
    schema['allOf'].append({'if':{'required':['never-present']},'then':{'unknownKeyword':True}})
    monkeypatch.setattr(own, '_json', lambda path: schema)
    with pytest.raises(own.OwnershipError, match='unsupported receipt schema keyword'):
        own._receipt_schema(receipt)


@pytest.mark.parametrize('content', [b'{}', b'broken json', b'{"request_id":"conflicting"}'])
@pytest.mark.parametrize('operation', ['acquire', 'confirm'])
def test_request_final_slot_freezes_all_preparation(repo, content, operation):
    start_session(repo)
    ci, data, text = inputs(repo)
    with own.execution_exclusion(repo) as lease:
        reserved = own.acquire_owner(lease, 'session-A', ci, sha(text))
        path = repo / ci['relative_path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        (repo / own.TEXT).write_bytes(text)
        before = (repo / own.AREA / 'owner.json').read_bytes()
        slot = own._closeout_request_slot(repo, 'session-A')
        slot.parent.mkdir(parents=True)
        slot.write_bytes(content)
        with pytest.raises(own.OwnershipError, match='CLOSEOUT_REQUESTED'):
            if operation == 'confirm':
                own.confirm_prepared(lease, 'session-A', reserved['generation'])
            else:
                ci2, _, _ = inputs(repo, version=2)
                own.acquire_owner(lease, 'session-A', ci2, sha(text))
        assert (repo / own.AREA / 'owner.json').read_bytes() == before
        assert (repo / own.TEXT).read_bytes() == text
        assert path.read_bytes() == data
