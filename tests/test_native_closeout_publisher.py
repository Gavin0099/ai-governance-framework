"""Publisher boundary tests. Synthetic payloads are not native event evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from governance_tools import native_closeout_publisher as p
from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2
from tests.test_shared_closeout_ownership import repo, prepare, owner


@pytest.fixture
def ready(repo, monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.upper().startswith('GIT_'):
            monkeypatch.delenv(name)
    # Unit registration boundary; real Git qualification/drift runs separately.
    framework = repo / 'SubModule/framework'
    framework.mkdir(parents=True)
    (framework / '.git').write_text('unit metadata')
    (repo / '.gitmodules').write_text('unit registration')
    (repo / 'governance/framework.lock.json').write_text('{"adopted_commit":"' + 'a' * 40 + '"}')
    monkeypatch.setattr(h, 'FRAMEWORK', framework)
    monkeypatch.setattr(h, '_framework_identity', lambda root: {
        'relative_path': 'SubModule/framework', 'gitlink_oid': 'a' * 40,
        'checkout_head': 'a' * 40, 'adopted_commit': 'a' * 40,
        'registration_blob': 'b' * 40, 'lock_blob': 'c' * 40})
    def git(root, *args):
        if args[0] == 'ls-files':
            return ('160000 ' + 'a'*40 + ' 0\tSubModule/framework\0'
                    + '100644 ' + 'b'*40 + ' 0\t.gitmodules\0'
                    + '100644 ' + 'c'*40 + ' 0\tgovernance/framework.lock.json\0')
        if args == ('rev-parse', '--show-toplevel'):
            return str(framework)
        if args[0] == 'rev-parse':
            return 'a'*40
        if args[0] == 'status':
            return '# branch.oid ' + 'a'*40 + '\n# branch.head main'
        raise AssertionError(args)
    monkeypatch.setattr(h, '_git', git)
    prepare(repo)
    source = tmp_path / 'native.jsonl'
    rows = [dict(type='session_meta', payload=dict(id='session-A', cwd=str(repo))),
            dict(type='event_msg', timestamp='2026-09-17T00:00:00Z', payload={
                'type': 'token_count', 'info': {'last_token_usage': {'input_tokens': 10, 'output_tokens': 5}}})]
    source.write_bytes(b''.join(json.dumps(row).encode() + b'\n' for row in rows))
    payload = dict(hook_event_name='SessionEnd', session_id='session-A', cwd=str(repo),
                   transcript_path=str(source), reason='other')
    return repo, source, payload


def publish(ready, **kwargs):
    return p.publish(ready[0], ready[2], deadline_ms=30000, **kwargs)


def request(root):
    return h._read(r2._closeout_request_slot(root, 'session-A'))


def test_publication_exact_owned_bytes_no_closeout(ready):
    root, source, _ = ready
    before = owner(root)
    result = publish(ready)
    req = request(root)
    ref = req['binding']['transcript']
    assert result['status'] == 'REQUESTED'
    assert req['schema_version'] == '1.1'
    assert (root / ref['immutable_locator']).read_bytes() == source.read_bytes()
    assert all(ref[k] == v for k, v in h.AUTHORITY.items())
    assert owner(root) == before
    assert not (root / 'artifacts/runtime/closeout-completions/session-A.json').exists()
    assert not (r2._closeout_request_slot(root, 'session-A').parent / 'finalized.json').exists()


def test_duplicate_ignores_changed_or_removed_source(ready):
    publish(ready)
    before = r2._closeout_request_slot(ready[0], 'session-A').read_bytes()
    ready[1].write_bytes(b'changed')
    assert publish(ready)['status'] == 'ALREADY_REQUESTED'
    ready[1].unlink()
    assert publish(ready)['status'] == 'ALREADY_REQUESTED'
    assert r2._closeout_request_slot(ready[0], 'session-A').read_bytes() == before


@pytest.mark.parametrize('field,value', [('hook_event_name', 'Stop'), ('session_id', '../escape'),
    ('session_id', 'session-B'), ('cwd', 'C:/wrong-root'), ('transcript_path', 'relative.jsonl')])
def test_invalid_identity_before_publication(ready, field, value):
    ready[2][field] = value
    with pytest.raises((ValueError, OSError)):
        publish(ready)
    assert not r2._closeout_request_slot(ready[0], 'session-A').exists()
    assert not (ready[0] / h.NATIVE_AREA).exists()


@pytest.mark.parametrize('content', [b'not-json\n', b'{}\n', b'[]\n', b'',
    b'{"type":"session_meta","payload":{"id":"other"}}\n'])
def test_unsupported_source_never_publishes_ref(ready, content):
    ready[1].write_bytes(content)
    with pytest.raises(ValueError):
        publish(ready)
    assert not list((ready[0] / h.NATIVE_AREA).glob('*/refs/*.json'))
    assert not r2._closeout_request_slot(ready[0], 'session-A').exists()


def test_cap_rejected_before_copy(ready, monkeypatch):
    monkeypatch.setattr(h, 'MAX_SNAPSHOT_BYTES', 8)
    with pytest.raises(h.HandoffError, match='SOURCE_SIZE'):
        publish(ready)
    assert not (ready[0] / h.NATIVE_AREA).exists()


@pytest.mark.parametrize('milliseconds', [None, 0, -1, True, 1.5])
def test_deadline_required_positive_integer(ready, milliseconds):
    with pytest.raises(h.HandoffError, match='INVALID_DEADLINE'):
        p.publish(ready[0], ready[2], deadline_ms=milliseconds)
    assert not (ready[0] / h.NATIVE_AREA).exists()


def test_expiration_after_request_publication_is_unconfirmed_and_reconciles(ready, monkeypatch):
    expired = False
    class Budget:
        def check(self):
            if expired:
                raise p.DeadlineExpired('expired')
    original = h._publish
    def publish_then_expire(lease, relative, value, **kwargs):
        nonlocal expired
        original(lease, relative, value, **kwargs)
        if relative.endswith('/request.json'):
            expired = True
    with monkeypatch.context() as m:
        m.setattr(h, '_publish', publish_then_expire)
        with pytest.raises(p.DeadlineExpired):
            p.publish(ready[0], ready[2], budget=Budget())
    assert r2._closeout_request_slot(ready[0], 'session-A').exists()
    assert publish(ready)['status'] == 'ALREADY_REQUESTED'


@pytest.mark.parametrize('phase', ['snapshot', 'manifest', 'ref', 'request'])
def test_crash_after_durable_phase_retry(ready, monkeypatch, phase):
    original_link, original_publish = os.link, h._publish
    def link(a, b, *args, **kwargs):
        original_link(a, b, *args, **kwargs)
        if phase == 'snapshot' and str(b).endswith('.jsonl'):
            raise OSError('crash')
    def store(lease, relative, value, **kwargs):
        original_publish(lease, relative, value, **kwargs)
        if ((phase == 'manifest' and '/manifests/' in relative) or
            (phase == 'ref' and '/refs/' in relative) or
            (phase == 'request' and relative.endswith('/request.json'))):
            raise OSError('crash')
    with monkeypatch.context() as m:
        m.setattr(os, 'link', link)
        m.setattr(h, '_publish', store)
        with pytest.raises(OSError, match='crash'):
            publish(ready)
    assert owner(ready[0])['state'] == 'OWNED'
    assert publish(ready)['status'] in ('REQUESTED', 'ALREADY_REQUESTED')


def orphan(ready, monkeypatch):
    original = h._publish
    def fail(lease, relative, value, **kwargs):
        if relative.endswith('/request.json'):
            raise OSError('request failed')
        return original(lease, relative, value, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(h, '_publish', fail)
        with pytest.raises(OSError, match='request failed'):
            publish(ready)


def test_orphan_ref_recovery_does_not_read_source(ready, monkeypatch):
    orphan(ready, monkeypatch)
    ready[1].unlink()
    assert publish(ready)['status'] == 'REQUESTED'


def test_orphan_cannot_attach_to_new_preparation(ready, monkeypatch):
    orphan(ready, monkeypatch)
    prepare(ready[0], version=2)
    with pytest.raises(h.HandoffError, match='ORPHAN_BINDING_MISMATCH'):
        publish(ready)
    assert not r2._closeout_request_slot(ready[0], 'session-A').exists()


@pytest.mark.parametrize('change', ['append', 'truncate', 'replace'])
def test_source_changes_during_capture_rejected(ready, monkeypatch, change):
    original = os.fsync
    mutated = False
    def fsync(fd):
        nonlocal mutated
        original(fd)
        if not mutated:
            mutated = True
            if change == 'append':
                with ready[1].open('ab') as stream:
                    stream.write(b'{}\n')
            elif change == 'truncate':
                ready[1].write_bytes(b'')
            else:
                alternate = ready[1].with_suffix('.replacement')
                alternate.write_bytes(ready[1].read_bytes())
                os.replace(alternate, ready[1])
    with monkeypatch.context() as m:
        m.setattr(os, 'fsync', fsync)
        # Windows can deny replacement of an open source: also fail closed.
        with pytest.raises((h.HandoffError, OSError)):
            publish(ready)
    assert not list((ready[0] / h.NATIVE_AREA).glob('*/refs/*.json'))


def test_cross_process_lock_busy_rejects(ready):
    code = ('import sys; from pathlib import Path; '
            'from governance_tools import shared_closeout_ownership as r; '
            'lease=r.execution_exclusion(Path(sys.argv[1])); lease.__enter__(); '
            'print("locked",flush=True); sys.stdin.readline()')
    child = subprocess.Popen([sys.executable, '-c', code, str(ready[0])],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'locked'
        with pytest.raises(r2.OwnershipError):
            publish(ready)
        assert not (ready[0] / h.NATIVE_AREA).exists()
    finally:
        child.communicate('\n', timeout=10)


def test_cli_requires_explicit_budget():
    result = subprocess.run([sys.executable, str(Path(p.__file__)), '--consumer-root', '.'],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert '--deadline-ms' in result.stderr


def test_expired_before_request_keeps_ref_without_request(ready, monkeypatch):
    expired = False
    class Budget:
        def check(self):
            if expired:
                raise p.DeadlineExpired('expired before request')
    original = h._publish
    def store(lease, relative, value, **kwargs):
        nonlocal expired
        original(lease, relative, value, **kwargs)
        if '/refs/' in relative:
            expired = True
    with monkeypatch.context() as m:
        m.setattr(h, '_publish', store)
        with pytest.raises(p.DeadlineExpired):
            p.publish(ready[0], ready[2], budget=Budget())
    assert not r2._closeout_request_slot(ready[0], 'session-A').exists()
    assert len(list((ready[0] / h.NATIVE_AREA).glob('*/refs/*.json'))) == 1
    assert publish(ready)['status'] == 'REQUESTED'


def test_fsync_failure_cannot_publish_ref(ready, monkeypatch):
    def fail(fd):
        raise OSError('fsync failure')
    monkeypatch.setattr(os, 'fsync', fail)
    with pytest.raises(OSError, match='fsync failure'):
        publish(ready)
    assert not list((ready[0] / h.NATIVE_AREA).glob('*/refs/*.json'))
    assert not r2._closeout_request_slot(ready[0], 'session-A').exists()


@pytest.mark.parametrize('target', ['manifest_locator', 'ref_locator', 'immutable_locator'])
def test_corrupt_owned_artifact_rejects_duplicate(ready, target):
    publish(ready)
    ref = request(ready[0])['binding']['transcript']
    (ready[0] / ref[target]).write_bytes(b'corruption')
    with pytest.raises(ValueError):
        publish(ready)
    assert owner(ready[0])['state'] == 'OWNED'


def test_different_event_reason_conflicts_without_mutation(ready):
    publish(ready)
    slot = r2._closeout_request_slot(ready[0], 'session-A')
    before = slot.read_bytes()
    ready[2]['reason'] = 'different'
    with pytest.raises(h.HandoffError, match='REQUEST_CONFLICT'):
        publish(ready)
    assert slot.read_bytes() == before


def test_snapshot_readback_failure_never_publishes_ref(ready, monkeypatch):
    original = os.link
    def corrupt(a, b, *args, **kwargs):
        original(a, b, *args, **kwargs)
        if str(b).endswith('.jsonl'):
            Path(b).write_bytes(b'corrupt')
    monkeypatch.setattr(os, 'link', corrupt)
    with pytest.raises(h.HandoffError, match='SNAPSHOT_READBACK'):
        publish(ready)
    assert not list((ready[0] / h.NATIVE_AREA).glob('*/refs/*.json'))


def test_framework_mismatch_rejected_before_capture(ready, monkeypatch):
    def fail(root):
        raise ValueError('framework mismatch')
    monkeypatch.setattr(h, '_framework_identity', fail)
    with pytest.raises(ValueError, match='framework mismatch'):
        publish(ready)
    assert not (ready[0] / h.NATIVE_AREA).exists()


def test_missing_envelope_rejects_before_lock(repo, monkeypatch):
    def forbidden(root):
        raise AssertionError('lock must not be acquired')
    monkeypatch.setattr(r2, 'execution_exclusion', forbidden)
    payload = dict(hook_event_name='SessionEnd', session_id='fresh', cwd=str(repo),
                   transcript_path=str(repo / 'missing.jsonl'), reason='other')
    with pytest.raises(ValueError):
        p.publish(repo, payload, deadline_ms=3000)
    assert not (repo / r2.AREA).exists()


def test_preflight_identity_is_rechecked_under_lock(ready, monkeypatch):
    from contextlib import contextmanager
    original = r2.execution_exclusion
    @contextmanager
    def changed(root):
        with original(root) as lease:
            (root / 'artifacts/runtime/sessions/session-A/session-envelope.json').unlink()
            yield lease
    monkeypatch.setattr(r2, 'execution_exclusion', changed)
    with pytest.raises(ValueError):
        publish(ready)
    assert not (ready[0] / h.NATIVE_AREA).exists()


def test_one_full_qualification_under_live_lease(ready, monkeypatch):
    original = h._framework_identity
    calls = []
    def qualify(root):
        assert any(lease.root == root for lease in r2._LIVE.values())
        calls.append(root)
        return original(root)
    monkeypatch.setattr(h, '_framework_identity', qualify)
    publish(ready)
    assert calls == [ready[0]]
    assert not h._QUALIFIED


def test_context_membership_lifetime_and_immutable_value(ready, tmp_path):
    from dataclasses import replace, FrozenInstanceError
    root = ready[0]
    with r2.execution_exclusion(root) as lease:
        with h._qualified_framework(lease) as context:
            value = h._qualified_identity(lease, context)
            value['checkout_head'] = '0' * 40
            assert h._qualified_identity(lease, context)['checkout_head'] == 'a' * 40
            with pytest.raises(FrozenInstanceError):
                context.identity_bytes = b'{}'
            for fake in ({'qualified': True}, replace(context)):
                with pytest.raises(h.HandoffError, match='INVALID_QUALIFIED_CONTEXT'):
                    h._qualified_identity(lease, fake)
            other = tmp_path / 'other-repo'
            other.mkdir()
            subprocess.run(['git', 'init', '--quiet', str(other)], check=True)
            with r2.execution_exclusion(other) as other_lease:
                with pytest.raises(h.HandoffError, match='INVALID_QUALIFIED_CONTEXT'):
                    h._qualified_identity(other_lease, context)
        with pytest.raises(h.HandoffError, match='INVALID_QUALIFIED_CONTEXT'):
            h._qualified_identity(lease, context)
    with r2.execution_exclusion(root) as new_lease:
        with pytest.raises(h.HandoffError, match='INVALID_QUALIFIED_CONTEXT'):
            h._qualified_identity(new_lease, context)


@pytest.mark.parametrize('relative', ['.gitmodules', 'governance/framework.lock.json'])
def test_control_drift_during_qualification_not_captured_as_valid(ready, monkeypatch, relative):
    original = h._framework_identity
    def qualify(root):
        result = original(root)
        with (root / relative).open('ab') as stream:
            stream.write(b' ')
        return result
    monkeypatch.setattr(h, '_framework_identity', qualify)
    with pytest.raises(h.HandoffError, match='CONTROL_DRIFT'):
        publish(ready)
    assert not (ready[0] / h.NATIVE_AREA).exists()
    assert not h._QUALIFIED


@pytest.mark.parametrize('relative', ['.gitmodules', 'governance/framework.lock.json'])
def test_post_capture_control_drift_retains_ref_without_request(ready, monkeypatch, relative):
    capture = p._capture
    def changed(*args):
        ref = capture(*args)
        with (ready[0] / relative).open('ab') as stream:
            stream.write(b' ')
        return ref
    monkeypatch.setattr(p, '_capture', changed)
    with pytest.raises(h.HandoffError, match='CONTROL_DRIFT'):
        publish(ready)
    assert list((ready[0] / h.NATIVE_AREA).glob('*/refs/*.json'))
    assert not r2._closeout_request_slot(ready[0], 'session-A').exists()
    assert owner(ready[0])['state'] == 'OWNED'
    assert not h._QUALIFIED


@pytest.mark.parametrize('change', ['index', 'parent-head', 'framework-head', 'framework-dirty', 'unmerged'])
def test_final_git_drift_cannot_publish_request(ready, monkeypatch, change):
    git = h._git
    def changed(root, *args):
        value = git(root, *args)
        if change == 'index' and args[0] == 'ls-files':
            return value.replace('a' * 40, 'd' * 40)
        if change == 'parent-head' and args[:2] == ('rev-parse', '--verify'):
            return 'd' * 40
        if change == 'framework-head' and args[0] == 'status':
            return value.replace('a' * 40, 'd' * 40)
        if change == 'framework-dirty' and args[0] == 'status':
            return value + '\n? shadow.py'
        if change == 'unmerged' and args[0] == 'ls-files':
            return value + value.replace(' 0\t', ' 1\t')
        return value
    monkeypatch.setattr(h, '_git', changed)
    with pytest.raises(h.HandoffError, match='DRIFT'):
        publish(ready)
    assert not r2._closeout_request_slot(ready[0], 'session-A').exists()
    assert not h._QUALIFIED
