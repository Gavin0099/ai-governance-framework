"""Read-only diagnosis: use real disposable ownership, never fixture file presence alone."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from governance_tools import closeout_status as status
from governance_tools import closeout_handoff as h
from governance_tools import shared_closeout_ownership as r2
from tests.test_shared_closeout_ownership import repo, owner, prepare
from tests.test_closeout_handoff import queued, consume, _tail_crash, try_next


def inventory(root):
    return {p.relative_to(root).as_posix(): (None if p.is_dir() else p.read_bytes())
            for p in root.rglob('*')}


def inspect_unchanged(root, sid='session-A'):
    before = inventory(root)
    result = status.inspect_closeout(root, sid)
    assert inventory(root) == before
    assert result['process_dead'] == 'not_established'
    return result


def test_missing_lock_no_file_or_directory_created(repo):
    result = inspect_unchanged(repo)
    assert result['status'] == 'UNKNOWN'
    assert result['reason'] == 'LOCK_OR_ROOT_MISSING'
    assert not (repo / r2.AREA).exists()


def test_lock_open_permission_failure_is_unknown(repo, monkeypatch):
    prepare(repo)
    def denied(*a, **k):
        raise PermissionError('diagnostic denied')
    monkeypatch.setattr(r2.os, 'open', denied)
    assert inspect_unchanged(repo)['status'] == 'UNKNOWN'


def test_real_other_process_lock_busy(queued):
    root = queued[0]
    code = """
import sys
from pathlib import Path
from governance_tools import shared_closeout_ownership as r
with r.execution_exclusion(Path(sys.argv[1])):
 print('LOCKED',flush=True)
 sys.stdin.readline()
"""
    before = inventory(root)
    child = subprocess.Popen([sys.executable, '-B', '-c', code, str(root)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'LOCKED'
        result = status.inspect_closeout(root, 'session-A')
        assert result['status'] == 'BUSY'
        assert result['lock'] == 'busy_observed'
    finally:
        child.communicate('\n', timeout=15)
    assert child.returncode == 0
    assert inventory(root) == before


@pytest.mark.parametrize('kind', ['tail_receipt', 'release', 'finalization'])
def test_recoverable_uses_shared_validator_without_mutation(queued, monkeypatch, kind):
    root = queued[0]
    if kind == 'tail_receipt':
        _tail_crash(queued, monkeypatch)
    else:
        original = r2._publish if kind == 'release' else h._publish
        def crash(lease, relative, value, **kw):
            if ((kind == 'release' and '/releases/' in relative)
                    or (kind == 'finalization' and relative.endswith('/finalized.json'))):
                raise OSError('controlled crash')
            return original(lease, relative, value, **kw)
        with monkeypatch.context() as m:
            m.setattr(r2 if kind == 'release' else h, '_publish', crash)
            with pytest.raises(OSError, match='controlled crash'):
                consume(queued)
    def forbidden(*a, **k):
        pytest.fail('status called mutation')
    with monkeypatch.context() as m:
        for module, name in ((h, '_publish'), (r2, '_publish'), (h, '_bind_attempt'),
                             (h, '_recover_receipt_material'), (h, 'consume_exact_request'),
                             (r2, 'publish_receipt'), (r2, 'finalize_release'), (h, '_finalize')):
            m.setattr(module, name, forbidden)
        result = inspect_unchanged(root)
        assert result['status'] == 'RECOVERABLE', result
        assert result['recovery_kind'] == kind
    assert consume(queued)['status'] == 'FINALIZED'


def test_finalized_history_independent_of_B(queued, monkeypatch):
    root = queued[0]
    consume(queued)
    try_next(root)
    monkeypatch.setattr(h, '_live', lambda *a, **k: pytest.fail('historical live access'))
    monkeypatch.setattr(r2, '_owner', lambda *a, **k: pytest.fail('historical owner access'))
    assert inspect_unchanged(root)['status'] == 'FINALIZED'


def test_early_hold_has_no_replay_or_dead_process_claim(queued):
    root = queued[0]
    req = h._read(r2._closeout_request_slot(root, 'session-A'))
    with r2.execution_exclusion(root) as lease:
        path, attempt = h._claim(lease, req)
        reserved = r2.begin_closeout(lease, 'session-A')
        h._bind_attempt(lease, path, attempt, reserved)
    result = inspect_unchanged(root)
    assert result['status'] == 'EARLY_HOLD_UNKNOWN'
    assert result['evidence']['checkpoint'] == 'missing'
    assert result['evidence']['receipt'] == 'missing'
    assert result['lock'] == 'free_observed'


@pytest.mark.parametrize('damage', ['checkpoint', 'receipt', 'ingestion', 'release', 'completion'])
def test_proof_presence_never_suffices(queued, monkeypatch, damage):
    root = queued[0]
    checkpoint, material = _tail_crash(queued, monkeypatch)
    paths = {'checkpoint': checkpoint, 'receipt': root / material['receipt_relative_path'],
             'ingestion': root / material['ingestion_relative_path'],
             'release': root / r2.AREA / 'releases/1.json',
             'completion': root / 'artifacts/runtime/closeout-completions/session-A.json'}
    path = paths[damage]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'{}')
    result = inspect_unchanged(root)
    assert result['status'] == 'PROOF_CONFLICT', result
    assert owner(root)['state'] == 'HOLD'


def test_observed_change_returns_unstable(queued, monkeypatch):
    root = queued[0]
    _tail_crash(queued, monkeypatch)
    original = h.validate_recovery_readiness
    path = root / 'artifacts/runtime/change-observed.txt'
    def change(*a, **k):
        result = original(*a, **k)
        path.write_text('external change', encoding='utf-8')
        return result
    monkeypatch.setattr(h, 'validate_recovery_readiness', change)
    result = status.inspect_closeout(root, 'session-A')
    assert result['status'] == 'UNKNOWN'
    assert result['reason'] == 'UNSTABLE'
    assert 'recovery_kind' not in result


def test_cli_json_creates_nothing(repo):
    before = inventory(repo)
    result = subprocess.run([sys.executable, '-B', '-m', 'governance_tools.closeout_status',
        '--consumer-root', str(repo), '--session-id', 'session-A', '--format', 'json'],
        capture_output=True, text=True, encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'})
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)['status'] == 'UNKNOWN'
    assert inventory(repo) == before


def test_default_execution_still_creates_lock(repo):
    with r2.execution_exclusion(repo):
        assert (repo / r2.AREA / 'execution.lock').is_file()

# These consumers execute the actual registered checkout in a fresh process.
# Only the controlled receipt crash is injected; framework validation is real.
@pytest.fixture(scope='module')
def status_framework_source(tmp_path_factory):
    import io
    import shutil
    import zipfile
    from tests.test_prepare_closeout_candidate import git, environment
    source = tmp_path_factory.mktemp('status-framework-source')
    current = Path(__file__).resolve().parents[1]
    archive = subprocess.run(['git', '-C', str(current), 'archive', '--format=zip', 'HEAD'],
                             check=True, capture_output=True, env=environment()).stdout
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        bundle.extractall(source)
    for relative in ('governance_tools/closeout_status.py', 'tests/test_closeout_status.py',
                     'governance_tools/closeout_handoff.py',
                     'governance_tools/shared_closeout_ownership.py',
                     'governance_tools/prepare_closeout_candidate.py'):
        shutil.copyfile(current / relative, source / relative)
    git(source, 'init', '--quiet')
    git(source, 'add', '.')
    git(source, 'commit', '-qm', 'disposable exact status candidate')
    return source


def _real_request(root, stage):
    import hashlib
    prepare(root)
    records = [{'type': 'session_meta', 'payload': {'id': 'session-A'}},
               {'type': 'event_msg', 'timestamp': '2026-09-17T00:00:00Z',
                'payload': {'type': 'token_count', 'info': {'last_token_usage':
                            {'input_tokens': 10, 'output_tokens': 5}}}}]
    data = b'\n'.join(json.dumps(record).encode() for record in records) + b'\n'
    sha = hashlib.sha256(data).hexdigest()
    relative = f'artifacts/runtime/handoff-transcript-fixtures/session-A/{sha}.jsonl'
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    ref = dict(session_id='session-A', immutable_locator=relative, sha256=sha,
               retention_contract='fixture-retained-transcript', retention_version='1.0',
               readable_after_hook=True, source_kind='fixture')
    (path.parent / 'manifest.json').write_bytes(h.canonical_bytes(
        {'consumer_root': str(root), 'transcript': ref}))
    provider = h.FixtureTranscriptProvider(root)
    result = h.publish_request(root, 'session-A', ref, provider)
    if stage == 'tail':
        with pytest.MonkeyPatch.context() as m:
            _tail_crash((root, result['request_id'], provider, ref), m)
    elif stage == 'early':
        request = h._read(r2._closeout_request_slot(root, 'session-A'))
        with r2.execution_exclusion(root) as lease:
            path, attempt = h._claim(lease, request)
            h._bind_attempt(lease, path, attempt, r2.begin_closeout(lease, 'session-A'))


@pytest.mark.parametrize('stage,expected', [('tail', 'RECOVERABLE'),
                                           ('early', 'EARLY_HOLD_UNKNOWN'), ('busy', 'BUSY')])
def test_real_registered_submodule_status_read_only(tmp_path, status_framework_source, stage, expected):
    from tests.test_prepare_closeout_candidate import git, environment, SUBMODULE
    root = (tmp_path / 'real consumer').resolve()
    root.mkdir()
    git(root, 'init', '--quiet')
    git(root, '-c', 'protocol.file.allow=always', 'submodule', 'add', '--quiet',
        str(status_framework_source), SUBMODULE)
    (root / 'governance').mkdir()
    (root / 'governance/framework.lock.json').write_text(json.dumps(
        {'adopted_commit': git(root / SUBMODULE, 'rev-parse', 'HEAD')}), encoding='utf-8')
    (root / 'evidence.txt').write_text('fixture evidence', encoding='utf-8')
    (root / 'AGENTS.md').write_text('# fixture\n', encoding='utf-8')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'registered consumer')
    env = environment()
    def execute(code):
        return subprocess.run([sys.executable, '-B', '-c',
            'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); ' + code,
            str(root / SUBMODULE), str(root)], cwd=root, env=env,
            capture_output=True, text=True, encoding='utf-8', timeout=60)
    setup = execute('from tests.test_closeout_status import _real_request; '
                    f'_real_request(Path(sys.argv[2]), {stage!r})')
    assert setup.returncode == 0, setup.stdout + setup.stderr
    # Touch clean controls to force an opportunity for Git's optional stat-cache refresh.
    for path in (root / '.gitmodules', root / 'governance/framework.lock.json',
                 root / SUBMODULE / 'governance_tools/prepare_closeout_candidate.py'):
        os.utime(path, None)
    before = inventory(root)
    indexes = [p for p in root.rglob('index') if '.git' in p.parts]
    index_stats = {str(p): (p.stat().st_mtime_ns, p.stat().st_ctime_ns, p.read_bytes()) for p in indexes}
    child = None
    try:
        if stage == 'busy':
            code = ('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                    'from governance_tools import shared_closeout_ownership as r; '
                    'exec("with r.execution_exclusion(Path(sys.argv[2]),create=False):\\n '
                    'print(\'LOCKED\',flush=True); sys.stdin.readline()")')
            child = subprocess.Popen([sys.executable, '-B', '-c', code, str(root / SUBMODULE), str(root)],
                cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            assert child.stdout.readline().strip() == 'LOCKED'
        result = execute('from governance_tools.closeout_status import main; '
                         'raise SystemExit(main(["--consumer-root",sys.argv[2],"--session-id",'
                         '"session-A","--format","json"]))')
        assert result.returncode in (0, 2), result.stderr
        report = json.loads(result.stdout)
        assert report['status'] == expected, report
        if stage == 'tail':
            assert report['recovery_kind'] == 'tail_receipt'
    finally:
        if child:
            child.communicate('\n', timeout=15)
            assert child.returncode == 0
    assert inventory(root) == before
    assert {str(p): (p.stat().st_mtime_ns, p.stat().st_ctime_ns, p.read_bytes()) for p in indexes} == index_stats
    assert indexes


def test_external_git_optional_locks_still_rejected(repo, monkeypatch):
    from governance_tools.prepare_closeout_candidate import validate_framework_binding, PreparationError
    for key in list(os.environ):
        if key.upper().startswith('GIT_'):
            monkeypatch.delenv(key)
    monkeypatch.setenv('GIT_OPTIONAL_LOCKS', '0')
    with pytest.raises(PreparationError, match='Git environment overrides unsupported: GIT_OPTIONAL_LOCKS'):
        validate_framework_binding(repo, repo)


def test_git_optional_locks_only_in_child_environment(repo, monkeypatch):
    from governance_tools import prepare_closeout_candidate as preparation
    monkeypatch.delenv('GIT_OPTIONAL_LOCKS', raising=False)
    original = preparation.subprocess.run
    seen = []
    def observe(*args, **kwargs):
        seen.append(kwargs['env']['GIT_OPTIONAL_LOCKS'])
        assert 'GIT_OPTIONAL_LOCKS' not in os.environ
        return original(*args, **kwargs)
    monkeypatch.setattr(preparation.subprocess, 'run', observe)
    preparation._git(repo, 'status', '--porcelain=v1')
    assert seen == ['0']
    assert 'GIT_OPTIONAL_LOCKS' not in os.environ
