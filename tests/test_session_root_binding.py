"""Consumer root identity and legacy envelope compatibility."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from runtime_hooks.core import _canonical_closeout as core
from runtime_hooks.adapters.codex.session_start import run


def event(repo, source='startup', sid='session-a'):
    return dict(hook_event_name='SessionStart', source=source, session_id=sid, cwd=str(repo))


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "consumer's space"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    return root.resolve()


def bound_fixture(repo):
    result = core.write_session_envelope("session-a", repo, provider="codex")
    path = Path(result['artifact_path'])
    payload = json.loads(path.read_text(encoding='utf-8'))
    payload.update(schema_version='1.1', repo_binding={
        'consumer_root': str(repo), 'source': 'codex_session_start'})
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path, payload


def test_reader_support_precedes_writer_enablement(repo):
    bound_fixture(repo)
    assert core.read_session_envelope('session-a', repo)['schema_version'] == '1.1'


@pytest.mark.parametrize('change', [
    {'schema_version': '9.0'}, {'repo_binding': None}, {'repo_binding': {}},
    {'provider': 'claude'}, {'session_id': 'other'},
    {'repo_binding': {'consumer_root': '.', 'source': 'codex_session_start'}},
    {'repo_binding': {'consumer_root': 1, 'source': 'codex_session_start'}},
    {'repo_binding': {'consumer_root': '/', 'source': 'invented'}},
])
def test_reader_rejects_invalid_envelopes_without_mutation(repo, change):
    path, payload = bound_fixture(repo)
    payload.update(change)
    path.write_text(json.dumps(payload), encoding='utf-8')
    before = path.read_bytes()
    assert core.read_session_envelope('session-a', repo) is None
    assert path.read_bytes() == before


def test_source_label_does_not_upgrade_legacy(repo):
    path, payload = bound_fixture(repo)
    payload['schema_version'] = '1.0'
    path.write_text(json.dumps(payload), encoding='utf-8')
    assert core.read_session_envelope('session-a', repo)['schema_version'] == '1.0'


def test_legacy_writer_and_binding_remain_usable(repo):
    envelope = core.write_session_envelope('legacy', repo, provider='codex')
    assert envelope['schema_version'] == '1.0'
    assert 'repo_binding' not in envelope
    candidate = dict(task_intent='inspect', work_summary='Read evidence.txt',
                     tools_used=['inspect'], artifacts_referenced=[], open_risks=[])
    core.write_candidate('legacy', repo, candidate)
    assert core.assess_session_closeout_binding(
        'legacy', repo, core.pick_latest_candidate('legacy', repo))['status'] == 'valid'


@pytest.mark.skipif(os.name != 'nt', reason='Windows filesystem spelling')
@pytest.mark.parametrize('spelling', ['lower', 'dot', 'slashes'])
def test_actual_windows_worktree_equivalence(repo, spelling):
    path, payload = bound_fixture(repo)
    variants = {'lower': str(repo).lower(), 'dot': str(repo) + '/.',
                'slashes': str(repo).replace('\\', '/')}
    payload['repo_binding']['consumer_root'] = variants[spelling]
    path.write_text(json.dumps(payload), encoding='utf-8')
    assert core.read_session_envelope('session-a', Path(variants[spelling])) is not None
    before = path.read_bytes()
    assert run(event(Path(variants[spelling]), 'resume'), Path(variants[spelling]))['status'] == 'preserved'
    assert path.read_bytes() == before


def test_real_writer_reader_and_closeout_are_paired(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    created = run(event(repo), repo)
    envelope = core.read_session_envelope('session-a', repo)
    assert envelope['schema_version'] == '1.1'
    assert envelope['repo_binding']['consumer_root'] == str(repo)
    path = Path(created['session_envelope_path'])
    before = path.read_bytes()
    for source in ['startup', 'resume', 'compact', 'clear']:
        assert run(event(repo, source), repo)['status'] == 'preserved'
        assert path.read_bytes() == before
    (repo / 'evidence.txt').write_text('fixture evidence', encoding='utf-8')
    candidate = dict(task_intent='Inspect root binding', work_summary='Inspected evidence.txt',
        tools_used=['inspect'], artifacts_referenced=['evidence.txt'], open_risks=[])
    core.write_candidate('session-a', repo, candidate)
    text = repo / 'artifacts/session-closeout.txt'
    text.write_text('TASK_INTENT: Inspect root binding\nWORK_COMPLETED: Inspected evidence.txt\n'
        'FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n'
        'NOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n', encoding='utf-8')
    # Avoid filesystem timestamp granularity changing an unrelated freshness condition.
    from datetime import datetime
    after_start = datetime.fromisoformat(envelope['started_at']).timestamp() + 1
    os.utime(text, (after_start, after_start))
    result = run_session_end_hook(repo, hook_session_id='session-a', ledger_write_allowed=False)
    assert result['session_binding']['status'] == 'valid'
    assert result['closeout_status'] == 'valid'
    canonical = json.loads((repo/'artifacts/runtime/closeouts/session-a.json').read_text())
    assert canonical['task_intent'] == candidate['task_intent']
    assert canonical['work_summary'] == candidate['work_summary']
    assert path.read_bytes() == before
    # Canonical compatibility only: absent gate evidence is not full E2E PASS.


def test_old_envelope_never_migrates_on_repeat_events(repo):
    old = core.write_session_envelope('session-a', repo, provider='codex')
    path = Path(old['artifact_path'])
    before = path.read_bytes()
    for source in ['startup', 'resume', 'compact', 'clear']:
        run(event(repo, source), repo)
        assert path.read_bytes() == before
        assert 'repo_binding' not in core.read_session_envelope('session-a', repo)


def test_same_head_different_worktree_rejects_copied_envelope(repo, tmp_path, monkeypatch):
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture',
        '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-m', 'fixture'],
        check=True, capture_output=True)
    other = tmp_path/'other-worktree'
    subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '--detach', str(other)],
                   check=True, capture_output=True)
    created = run(event(repo), repo)
    original = Path(created['session_envelope_path'])
    copied = other/'artifacts/runtime/sessions/session-a/session-envelope.json'
    copied.parent.mkdir(parents=True)
    copied.write_bytes(original.read_bytes())
    before = copied.read_bytes()
    assert core.read_session_envelope('session-a', other) is None
    original_open = Path.open
    def no_lock_write(self, *args, **kwargs):
        assert self.name != '.codex-start.lock', 'wrong root must reject before lock mutation'
        return original_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', no_lock_write)
    with pytest.raises(ValueError, match='invalid'):
        run(event(other, 'resume'), other)
    assert copied.read_bytes() == before
    assert not (other/'artifacts/runtime/.current-session-id').exists()


def test_bound_writer_refuses_existing_legacy_or_bound_envelope(repo):
    old = core.write_session_envelope('session-a', repo, provider='codex')
    path = Path(old['artifact_path'])
    before = path.read_bytes()
    with pytest.raises(ValueError, match='overwritten'):
        core.write_session_envelope('session-a', repo, provider='codex', bound_consumer_root=repo)
    assert path.read_bytes() == before


def test_interrupted_bound_publish_exposes_no_partial_envelope(repo, monkeypatch):
    def fail_replace(self, target):
        raise OSError('injected publication failure')
    monkeypatch.setattr(Path, 'replace', fail_replace)
    with pytest.raises(OSError, match='publication'):
        run(event(repo), repo)
    assert core.read_session_envelope('session-a', repo) is None
    assert not (repo/'artifacts/runtime/.current-session-id').exists()
    session_dir = repo/'artifacts/runtime/sessions/session-a'
    assert list(session_dir.iterdir()) == []
    monkeypatch.undo()
    assert run(event(repo), repo)['status'] == 'created'


def test_consumed_bound_session_preserved_and_not_rebound(repo):
    created = run(event(repo), repo)
    path = Path(created['session_envelope_path'])
    before = path.read_bytes()
    marker = core.write_closeout_completion_marker('session-a', repo, [path])
    marker_before = marker.read_bytes()
    run(event(repo, 'resume'), repo)
    assert path.read_bytes() == before
    assert marker.read_bytes() == marker_before
    assert core.assess_session_closeout_binding('session-a', repo, None)['status'] == 'already_consumed'


def test_bound_writer_cannot_recreate_consumed_identity(repo):
    marker = repo/'artifacts/runtime/closeout-completions/session-a.json'
    marker.parent.mkdir(parents=True)
    marker.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='Completion'):
        core.write_session_envelope('session-a', repo, provider='codex', bound_consumer_root=repo)
    assert not (repo/'artifacts/runtime/sessions').exists()


@pytest.mark.parametrize('provider', ['claude', 'unknown'])
def test_other_providers_cannot_claim_codex_binding(repo, provider):
    with pytest.raises(ValueError, match='Codex'):
        core.write_session_envelope('session-a', repo, provider=provider, bound_consumer_root=repo)
    assert not (repo/'artifacts').exists()


def test_legacy_writer_cannot_downgrade_bound_envelope(repo):
    created = run(event(repo), repo)
    path = Path(created['session_envelope_path'])
    marker = repo/'artifacts/runtime/.current-session-id'
    before, marker_before = path.read_bytes(), marker.read_bytes()
    with pytest.raises(ValueError, match='Legacy writer'):
        core.write_session_envelope('session-a', repo, provider='codex',
                                    started_at='2020-01-01T00:00:00+00:00')
    assert path.read_bytes() == before
    assert marker.read_bytes() == marker_before


def test_legacy_writer_preserves_legacy_rewrite_semantics(repo):
    old = core.write_session_envelope('session-a', repo, provider='codex',
                                     started_at='2020-01-01T00:00:00+00:00')
    new = core.write_session_envelope('session-a', repo, provider='claude',
                                     started_at='2021-01-01T00:00:00+00:00')
    assert new['schema_version'] == '1.0'
    assert 'repo_binding' not in new
    assert new['started_at'] != old['started_at']
    assert core.read_session_envelope('session-a', repo)['provider'] == 'claude'
    assert (repo/'artifacts/runtime/.current-session-id').exists()


@pytest.mark.parametrize('existing_pointer', [False, True])
def test_completion_only_rejected_before_any_mutation(repo, monkeypatch, existing_pointer):
    completion = repo/'artifacts/runtime/closeout-completions/session-a.json'
    completion.parent.mkdir(parents=True)
    completion.write_text('{}', encoding='utf-8')
    marker = repo/'artifacts/runtime/.current-session-id'
    if existing_pointer:
        marker.write_bytes(b'preserve existing pointer')
    original_open = Path.open
    def no_lock(self, *args, **kwargs):
        assert self.name != '.codex-start.lock'
        return original_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', no_lock)
    with pytest.raises(ValueError, match='Completion marker'):
        run(event(repo), repo)
    assert not (repo/'artifacts/runtime/sessions').exists()
    assert completion.read_bytes() == b'{}'
    if existing_pointer:
        assert marker.read_bytes() == b'preserve existing pointer'
    else:
        assert not marker.exists()


def test_completion_appearing_after_preflight_rejected_under_lock(repo, monkeypatch):
    completion = repo/'artifacts/runtime/closeout-completions/session-a.json'
    original_open = Path.open
    lock_acquired = []
    def inject_completion(self, *args, **kwargs):
        stream = original_open(self, *args, **kwargs)
        if self.name == '.codex-start.lock':
            lock_acquired.append(True)
            completion.parent.mkdir(parents=True)
            completion.write_text('{}', encoding='utf-8')
        return stream
    monkeypatch.setattr(Path, 'open', inject_completion)
    with pytest.raises(ValueError, match='Completion marker'):
        run(event(repo), repo)
    assert lock_acquired == [True]
    assert completion.read_bytes() == b'{}'
    assert not (repo/'artifacts/runtime/sessions/session-a/session-envelope.json').exists()
    assert not (repo/'artifacts/runtime/sessions/session-a/.codex-start.lock').exists()
    assert not (repo/'artifacts/runtime/.current-session-id').exists()
