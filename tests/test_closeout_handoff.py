"""Handoff Core v1 acceptance probes; fixture retention is not native evidence."""
import hashlib
import json
from pathlib import Path

import pytest

from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2
from governance_tools import session_end_hook as hook
from tests.test_shared_closeout_ownership import repo, prepare, owner


@pytest.fixture
def queued(repo, monkeypatch):
    # Unit boundary fixture only. Does not qualify real submodule identity.
    monkeypatch.setattr(h, '_framework_identity', lambda root: {
        'relative_path': 'SubModule/framework', 'gitlink_oid': 'a' * 40,
        'checkout_head': 'a' * 40, 'adopted_commit': 'a' * 40,
        'registration_blob': 'b' * 40, 'lock_blob': 'c' * 40})
    prepare(repo)
    records = [
        {'type': 'session_meta', 'payload': {'id': 'session-A'}},
        {'type': 'event_msg', 'timestamp': '2026-09-17T00:00:00Z', 'payload': {
            'type': 'token_count', 'info': {'last_token_usage': {
                'input_tokens': 10, 'output_tokens': 5}}}},
    ]
    data = b'\n'.join(json.dumps(r).encode() for r in records) + b'\n'
    sha = hashlib.sha256(data).hexdigest()
    rel = f'artifacts/runtime/handoff-transcript-fixtures/session-A/{sha}.jsonl'
    path = repo / rel
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    ref = dict(session_id='session-A', immutable_locator=rel, sha256=sha,
               retention_contract='fixture-retained-transcript', retention_version='1.0',
               readable_after_hook=True, source_kind='fixture')
    (path.parent / 'manifest.json').write_bytes(h.canonical_bytes(
        {'consumer_root': str(repo), 'transcript': ref}))
    provider = h.FixtureTranscriptProvider(repo)
    result = h.publish_request(repo, 'session-A', ref, provider)
    return repo, result['request_id'], provider, ref


def consume(queued):
    root, request_id, provider, _ = queued
    return h.consume_exact_request(root, request_id, session_id='session-A', provider=provider)


def test_fixture_happy_path_and_exact_duplicate(queued):
    root, request_id, provider, ref = queued
    slot = r2._closeout_request_slot(root, 'session-A')
    before = slot.read_bytes()
    assert h.publish_request(root, 'session-A', ref, provider)['status'] == 'ALREADY_REQUESTED'
    assert slot.read_bytes() == before
    result = consume(queued)
    assert result['status'] == 'FINALIZED'
    assert result['transcript_ingestion'] == 'VERIFIED'
    assert owner(root)['state'] == 'RELEASED'
    final = slot.parent / 'finalized.json'
    final_bytes = final.read_bytes()
    assert consume(queued)['status'] == 'ALREADY_FINALIZED'
    assert final.read_bytes() == final_bytes
    receipt = json.loads(Path(result['closeout_result']['closeout_receipt_artifact']).read_bytes())
    assert receipt['trigger_mode'] == 'wrapper'
    assert receipt['entrypoint'] == 'governance_tools.closeout_handoff'
    assert 'execution_origin' not in receipt


def test_release_record_crash_must_not_report_finalized_with_owner_hold(queued, monkeypatch):
    root = queued[0]
    publish = r2._publish
    def crash(lease, relative, value, **kwargs):
        if relative == r2.AREA + '/owner.json' and value.get('state') == 'RELEASED':
            raise OSError('crash after release record before owner update')
        return publish(lease, relative, value, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(r2, '_publish', crash)
        with pytest.raises(OSError, match='crash after release record'):
            consume(queued)
    assert owner(root)['state'] == 'HOLD'
    assert (root / r2.AREA / 'releases/1.json').exists()
    result = consume(queued)
    assert result['status'] == 'FINALIZED'
    # Contract requires release-only reconciliation, not a false terminal claim.
    assert owner(root)['state'] == 'RELEASED'


def test_ingestion_failure_cannot_turn_into_success_on_retry(queued, monkeypatch):
    root = queued[0]
    monkeypatch.setattr(hook, '_ingest_transcript_for_closeout', lambda *a, **k: None)
    with pytest.raises(h.HandoffError, match='INGESTION_UNCONFIRMED'):
        consume(queued)
    with pytest.raises(h.HandoffError, match='INGESTION_UNCONFIRMED'):
        consume(queued)
    assert not (r2._closeout_request_slot(root, 'session-A').parent / 'finalized.json').exists()


def try_next(root):
    from tests.test_shared_closeout_ownership import start_session, inputs, sha
    start_session(root, 'session-B')
    ci, _, text = inputs(root, 'session-B')
    with r2.execution_exclusion(root) as lease:
        return r2.acquire_owner(lease, 'session-B', ci, sha(text))


def final_path(root):
    return r2._closeout_request_slot(root, 'session-A').parent / 'finalized.json'


def test_release_recovery_precedes_finalization_and_B_takeover(queued, monkeypatch):
    root = queued[0]
    publish = h._publish
    def pause_final(lease, relative, value, **kwargs):
        if relative.endswith('/finalized.json'):
            assert owner(root)['state'] == 'RELEASED'
            raise OSError('before final publication')
        return publish(lease, relative, value, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(h, '_publish', pause_final)
        with pytest.raises(OSError, match='before final'):
            consume(queued)
    assert owner(root)['state'] == 'RELEASED'
    released = owner(root)
    assert r2.reconcile_release(root, 'session-A', 1, released['receipt_identity'])['status'] == 'ALREADY_RELEASED'
    before = (root / r2.AREA / 'owner.json').read_bytes()
    with pytest.raises(h.HandoffError):
        try_next(root)
    assert (root / r2.AREA / 'owner.json').read_bytes() == before
    # Recovery must not rerun any closeout side effects.
    from governance_tools import session_closeout_entry as entry
    monkeypatch.setattr(entry, 'run', lambda *a, **k: pytest.fail('replayed core'))
    assert consume(queued)['status'] == 'FINALIZED'
    assert try_next(root)['generation'] == 2


@pytest.mark.parametrize('damage', ['missing', 'malformed', 'extra', 'request_id', 'request_sha256',
    'attempt_id', 'attempt_sha256', 'receipt_identity', 'receipt_sha256', 'release_sha256',
    'ingestion_sha256', 'execution_origin', 'schema_version'])
def test_B_rejects_incomplete_or_conflicting_finalization(queued, damage):
    root = queued[0]
    consume(queued)
    path = final_path(root)
    data = json.loads(path.read_bytes())
    if damage == 'missing':
        path.unlink()
    elif damage == 'malformed':
        path.write_bytes(b'{')
    else:
        data[damage] = 'conflict'
        path.write_bytes(h.canonical_bytes(data))
    before = (root / r2.AREA / 'owner.json').read_bytes()
    with pytest.raises((h.HandoffError, r2.OwnershipError)):
        try_next(root)
    assert (root / r2.AREA / 'owner.json').read_bytes() == before


@pytest.mark.parametrize('which', ['request', 'attempt', 'receipt', 'release', 'ingestion'])
@pytest.mark.parametrize('damage', ['missing', 'conflict'])
def test_B_rejects_broken_referenced_proof(queued, which, damage):
    root = queued[0]
    consume(queued)
    area = final_path(root).parent
    paths = {'request': area / 'request.json', 'attempt': next((area / 'attempts').glob('*.json')),
             'receipt': next((root / 'artifacts/runtime/closeout-receipts').glob('*.json')),
             'release': root / r2.AREA / 'releases/1.json',
             'ingestion': next((area / 'ingestion').glob('*.json'))}
    # A missing request is outside the final-request presence gate. Keep the
    # slot present but invalid to model unreadable/partial publication instead.
    if which == 'request' and damage == 'missing':
        paths[which].write_bytes(b'')
    elif damage == 'missing':
        paths[which].unlink()
    else:
        obj = json.loads(paths[which].read_bytes())
        obj['unexpected'] = True
        paths[which].write_bytes(h.canonical_bytes(obj))
    before = (root / r2.AREA / 'owner.json').read_bytes()
    with pytest.raises((ValueError, OSError)):
        try_next(root)
    assert (root / r2.AREA / 'owner.json').read_bytes() == before


def test_A_duplicate_after_B_uses_only_immutable_proof(queued, monkeypatch):
    root, request_id, provider, ref = queued
    consume(queued)
    prepare(root, 'session-B')
    before = (root / r2.TEXT).read_bytes()
    monkeypatch.setattr(r2, '_owner', lambda *a: pytest.fail('read current owner'))
    monkeypatch.setattr(r2, '_payloads', lambda *a: pytest.fail('read shared text'))
    monkeypatch.setattr(h, '_framework_identity', lambda *a: pytest.fail('read live framework'))
    monkeypatch.setattr(provider, 'validate', lambda *a: pytest.fail('read live transcript'))
    assert consume(queued)['status'] == 'ALREADY_FINALIZED'
    assert h.publish_request(root, 'session-A', ref, provider)['status'] == 'ALREADY_FINALIZED'
    assert (root / r2.TEXT).read_bytes() == before
    damaged = json.loads(final_path(root).read_bytes())
    damaged['request_sha256'] = '0' * 64
    final_path(root).write_bytes(h.canonical_bytes(damaged))
    with pytest.raises(h.HandoffError):
        consume(queued)


def test_direct_finalization_rejects_HOLD_even_with_release_record(queued, monkeypatch):
    root = queued[0]
    publish = r2._publish
    def crash(lease, relative, value, **kwargs):
        if relative == r2.AREA + '/owner.json' and value.get('state') == 'RELEASED':
            raise OSError('crash')
        return publish(lease, relative, value, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(r2, '_publish', crash)
        with pytest.raises(OSError):
            consume(queued)
    request = h._read(r2._closeout_request_slot(root, 'session-A'))
    with r2.execution_exclusion(root) as lease:
        with pytest.raises(h.HandoffError, match='OWNER_NOT_RELEASED'):
            h._finalize(lease, request)
    assert not final_path(root).exists()
    with pytest.raises(r2.OwnershipError, match='OWNER_CONFLICT'):
        try_next(root)
    assert consume(queued)['status'] == 'FINALIZED'
    assert owner(root)['state'] == 'RELEASED'


@pytest.mark.parametrize('phase', ['claim', 'begin', 'receipt', 'release', 'released', 'finalized'])
def test_real_process_crash_recovery(queued, phase):
    import os
    import subprocess
    import sys
    root, request_id, provider, _ = queued
    code = r'''
import json, os, sys
from pathlib import Path
from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r
root=Path(sys.argv[1]); phase=sys.argv[3]
req=h._read(r._closeout_request_slot(root,'session-A'))
h._framework_identity=lambda root: req['binding']['framework']
rpub=r._publish; hpub=h._publish

def rp(lease,relative,value,**kw):
    result=rpub(lease,relative,value,**kw)
    hit=(phase=='begin' and relative.endswith('/owner.json') and value.get('hold_reason')=='closeout_pending'
      or phase=='receipt' and 'closeout-receipts/' in relative
      or phase=='release' and '/releases/' in relative
      or phase=='released' and relative.endswith('/owner.json') and value.get('state')=='RELEASED')
    if hit: os._exit(86)
    return result

def hp(lease,relative,value,**kw):
    result=hpub(lease,relative,value,**kw)
    if (phase=='claim' and '/attempts/' in relative and value.get('receipt_identity') is None
        or phase=='finalized' and relative.endswith('/finalized.json')): os._exit(86)
    return result
r._publish=rp; h._publish=hp
h.consume_exact_request(root,sys.argv[2],session_id='session-A',provider=h.FixtureTranscriptProvider(root))
'''
    result = subprocess.run([sys.executable, '-B', '-c', code, str(root), request_id, phase],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, encoding='utf-8',
        env={**os.environ, 'PYTHONUTF8':'1', 'PYTHONIOENCODING':'utf-8'}, timeout=40)
    assert result.returncode == 86, result.stdout + result.stderr
    if phase == 'begin':
        with pytest.raises(h.HandoffError):
            consume(queued)
        assert owner(root)['state'] == 'HOLD'
        assert not final_path(root).exists()
        assert not (root/'artifacts/runtime/closeout-completions/session-A.json').exists()
        return
    if phase == 'finalized':
        prepare(root, 'session-B')
        assert consume(queued)['status'] == 'ALREADY_FINALIZED'
        return
    with pytest.raises((ValueError, OSError)):
        try_next(root)
    result = consume(queued)
    assert result['status'] == 'FINALIZED'
    assert owner(root)['state'] == 'RELEASED'
    assert try_next(root)['generation'] == 2
    if phase != 'claim':
        # Recovery does not rerun transcript ingestion.
        import sqlite3
        with sqlite3.connect(root/'artifacts/codeburn_closeout_ingest.db') as db:
            assert db.execute("select count(*) from steps where session_id='session-A'").fetchone()[0] == 1


@pytest.mark.parametrize('operation', ['reprepare-A', 'prepare-B', 'publish', 'consume'])
def test_independent_process_cannot_enter_while_closeout_holds_lease(queued, monkeypatch, operation):
    import os
    import subprocess
    import sys
    from governance_tools import session_closeout_entry as entry
    root = queued[0]
    real = entry.run
    def run(*args, **kwargs):
        # Every public operation must first acquire this same OS exclusion;
        # exercise actual APIs from a second process while core owns it.
        code = r'''
import json,sys
from pathlib import Path
from governance_tools import closeout_handoff as h,shared_closeout_ownership as r
from tests.test_shared_closeout_ownership import prepare
root=Path(sys.argv[1]); op=sys.argv[2]
req=h._read(r._closeout_request_slot(root,'session-A'))
h._framework_identity=lambda root: req['binding']['framework']
try:
 if op=='reprepare-A': prepare(root,'session-A',2)
 elif op=='prepare-B': prepare(root,'session-B')
 elif op=='publish': h.publish_request(root,'session-A',req['binding']['transcript'],h.FixtureTranscriptProvider(root))
 else: h.consume_exact_request(root,req['request_id'],session_id='session-A',provider=h.FixtureTranscriptProvider(root))
except r.OwnershipError as e:
 assert e.code=='R2_BUSY',str(e)
 print('BUSY')
else: raise AssertionError('concurrent operation entered')
'''
        p = subprocess.run([sys.executable,'-B','-c',code,str(root),operation],
            cwd=Path(__file__).resolve().parents[1], capture_output=True,text=True,encoding='utf-8',
            env={**os.environ,'PYTHONUTF8':'1'},timeout=30)
        assert p.returncode == 0 and p.stdout.strip() == 'BUSY', p.stdout+p.stderr
        return real(*args, **kwargs)
    monkeypatch.setattr(entry,'run',run)
    assert consume(queued)['status'] == 'FINALIZED'


@pytest.mark.parametrize('stage', ['before_link', 'after_link'])
def test_publication_failure_preserves_exact_slot_or_partial_temp(queued, monkeypatch, stage):
    # Reuse a prepared fixture, remove only the test's request to exercise its
    # first publication. Production never removes requests or rolls back.
    root, _, provider, ref = queued
    slot = r2._closeout_request_slot(root,'session-A')
    slot.unlink()
    import os
    link = os.link
    def fail(source, target):
        if stage == 'after_link': link(source,target)
        raise OSError('publication interrupted')
    with monkeypatch.context() as m:
        m.setattr(h.os,'link',fail)
        with pytest.raises(OSError,match='interrupted'):
            h.publish_request(root,'session-A',ref,provider)
    assert list(slot.parent.glob('*.tmp'))
    assert slot.exists() == (stage == 'after_link')
    retained = {p.name:p.read_bytes() for p in slot.parent.glob('*.tmp')}
    assert h.publish_request(root,'session-A',ref,provider)['status'] in {'REQUESTED','ALREADY_REQUESTED'}
    assert all((slot.parent/name).read_bytes() == data for name,data in retained.items())
    assert owner(root)['state'] == 'OWNED'


@pytest.mark.parametrize('field,value', [('schema_version','9'),('request_id','0'*64),
    ('generation',True),('session_id','../escape'),('consumer_root','wrong'),
    ('envelope_sha256','no'),('unexpected',1)])
def test_corrupt_request_rejects_before_attempt_or_consumption(queued, field, value):
    root=queued[0]; slot=r2._closeout_request_slot(root,'session-A')
    request=json.loads(slot.read_bytes())
    target=request if field in {'schema_version','request_id'} else request['binding']
    target[field]=value
    slot.write_bytes(h.canonical_bytes(request))
    before=(root/r2.AREA/'owner.json').read_bytes()
    with pytest.raises((ValueError,OSError,TypeError)):
        consume(queued)
    assert (root/r2.AREA/'owner.json').read_bytes()==before
    assert not (slot.parent/'attempts').exists()
    assert not (root/'artifacts/runtime/closeout-completions/session-A.json').exists()


@pytest.mark.parametrize('damage',['manifest_missing','transcript_missing','transcript_changed','wrong_root'])
def test_transcript_provider_rejection_never_consumes(queued, damage):
    root, _, provider, ref=queued
    path=root/ref['immutable_locator']
    if damage=='manifest_missing': (path.parent/'manifest.json').unlink()
    elif damage=='transcript_missing': path.unlink()
    elif damage=='transcript_changed': path.write_bytes(b'changed')
    else: provider.root=root.parent
    with pytest.raises((ValueError,OSError)):
        consume(queued)
    assert owner(root)['state']=='OWNED'
    assert not (root/'artifacts/runtime/closeout-completions/session-A.json').exists()


@pytest.fixture(scope='module')
def handoff_framework_source(tmp_path_factory):
    import subprocess
    import shutil
    import zipfile
    from tests.test_prepare_closeout_candidate import git
    source=tmp_path_factory.mktemp('handoff-source')
    archive=source.parent/(source.name+'.zip')
    framework=Path(__file__).resolve().parents[1]
    with archive.open('wb') as output:
        subprocess.run(['git','archive','--format=zip','HEAD'],cwd=framework,stdout=output,check=True)
    with zipfile.ZipFile(archive) as z: z.extractall(source)
    for relative in ['governance_tools/closeout_handoff.py',
                     'governance_tools/shared_closeout_ownership.py',
                     'governance_tools/session_closeout_entry.py']:
        shutil.copyfile(framework/relative,source/relative)
    git(source,'init','--quiet')
    git(source,'add','.')
    git(source,'commit','-qm','disposable handoff fixture snapshot')
    return source


def test_real_registered_submodule_handoff_and_dirty_binding_rejection(tmp_path,handoff_framework_source):
    import os
    import subprocess
    import sys
    from tests.test_prepare_closeout_candidate import git, environment, SUBMODULE
    root=tmp_path/'actual submodule consumer';root.mkdir()
    git(root,'init','--quiet')
    git(root,'-c','protocol.file.allow=always','submodule','add','--quiet',str(handoff_framework_source),SUBMODULE)
    (root/'governance').mkdir()
    (root/'AGENTS.md').write_text('# disposable fixture\n',encoding='utf-8')
    (root/'evidence.txt').write_text('fixture',encoding='utf-8')
    (root/'governance/framework.lock.json').write_text(json.dumps({'adopted_commit':git(root/SUBMODULE,'rev-parse','HEAD')}),encoding='utf-8')
    git(root,'add','.');git(root,'commit','-qm','registered disposable consumer')
    code=r'''
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from governance_tools import closeout_handoff as h
from governance_tools.prepare_closeout_candidate import prepare
from runtime_hooks.adapters.codex.session_start import run
root=Path(sys.argv[2]);sid='real-submodule'
run(dict(hook_event_name='SessionStart',source='startup',session_id=sid,cwd=str(root)),root)
prepare(root,Path(sys.argv[1]),sid,dict(task_intent='fixture integration',work_summary='Inspected evidence.txt for disposable consumer integration.',
 tools_used=['read'],artifacts_referenced=['evidence.txt'],open_risks=[],checks_run='NONE',
 not_done='NONE',recommended_memory_update='NO_UPDATE'))
data=(json.dumps(dict(type='session_meta',payload=dict(id=sid)))+'\n'+json.dumps(dict(type='event_msg',
 payload=dict(type='token_count',info=dict(last_token_usage=dict(input_tokens=10,output_tokens=5)))))+'\n').encode()
sha=hashlib.sha256(data).hexdigest();rel=f'artifacts/runtime/handoff-transcript-fixtures/{sid}/{sha}.jsonl'
p=root/rel;p.parent.mkdir(parents=True);p.write_bytes(data)
ref=dict(session_id=sid,immutable_locator=rel,sha256=sha,retention_contract='fixture-retained-transcript',
 retention_version='1.0',readable_after_hook=True,source_kind='fixture')
(p.parent/'manifest.json').write_bytes(h.canonical_bytes(dict(consumer_root=str(root),transcript=ref)))
provider=h.FixtureTranscriptProvider(root)
r=h.publish_request(root,sid,ref,provider)
# Dirty adoption metadata rejects consumption before any attempt/core mutation.
lock=root/'governance/framework.lock.json';before=lock.read_bytes();lock.write_bytes(before+b' ')
try:
 h.consume_exact_request(root,r['request_id'],session_id=sid,provider=provider)
except ValueError: pass
else: raise AssertionError('dirty binding accepted')
assert not (root/f'artifacts/runtime/closeout-requests/{sid}/attempts').exists()
lock.write_bytes(before)
result=h.consume_exact_request(root,r['request_id'],session_id=sid,provider=provider)
assert result['status']=='FINALIZED'
assert result['transcript_ingestion']=='VERIFIED'
assert result['closeout_result']['closeout_status']=='valid'
print('SUBMODULE_CORE_PASS')
'''
    result=subprocess.run([sys.executable,'-B','-c',code,str(root/SUBMODULE),str(root)],cwd=root,
        env=environment(),capture_output=True,text=True,encoding='utf-8',timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.rstrip().endswith('SUBMODULE_CORE_PASS')


@pytest.mark.parametrize('change', ['reason','transcript','framework','envelope'])
def test_duplicate_conflict_never_rewrites_request(queued, monkeypatch, change):
    root, _, provider, ref=queued
    slot=r2._closeout_request_slot(root,'session-A');before=slot.read_bytes()
    kwargs={}
    if change=='reason': kwargs['reason']='different'
    elif change=='transcript': ref={**ref,'sha256':'0'*64}
    elif change=='framework': monkeypatch.setattr(h,'_framework_identity',lambda root:{})
    else:
        path=root/'artifacts/runtime/sessions/session-A/session-envelope.json'
        path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises((ValueError,OSError)):
        h.publish_request(root,'session-A',ref,provider,**kwargs)
    assert slot.read_bytes()==before
    assert owner(root)['state']=='OWNED'


def test_missing_ingestion_blocks_initial_finalization_and_next_owner(queued, monkeypatch):
    root=queued[0]
    publish=h._publish
    def stop_before_final(lease,relative,value,**kwargs):
        if relative.endswith('/finalized.json'): raise OSError('stop')
        return publish(lease,relative,value,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(h,'_publish',stop_before_final)
        with pytest.raises(OSError): consume(queued)
    assert owner(root)['state']=='RELEASED'
    next((final_path(root).parent/'ingestion').glob('*.json')).unlink()
    with pytest.raises(h.HandoffError,match='INGESTION_UNCONFIRMED'): consume(queued)
    with pytest.raises(h.HandoffError): try_next(root)
    assert not final_path(root).exists()
