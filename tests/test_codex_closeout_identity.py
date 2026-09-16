"""Concurrent-session regression through the real closeout entry and core."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_shared_closeout_ownership import repo as protected_repo, prepare

from runtime_hooks.adapters.codex.session_start import run as start
from runtime_hooks.core._canonical_closeout import write_candidate, write_session_envelope
from governance_tools.session_end_hook import run_session_end_hook

ENTRY = Path(__file__).resolve().parents[1] / 'governance_tools/session_closeout_entry.py'


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'concurrent repo'
    subprocess.run(['git', 'init', str(root)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c',
                    'user.email=fixture@example.test', 'commit', '--allow-empty', '-m', 'fixture'],
                   check=True, capture_output=True)
    (root / 'AGENTS.md').write_text('# fixture governance root\n')
    (root / 'governance').mkdir()
    (root / 'evidence.txt').write_text('isolated evidence')
    for sid in ('session-A', 'session-B'):
        start({'hook_event_name':'SessionStart', 'source':'startup', 'session_id':sid, 'cwd':str(root)}, root)
    select_content(root, 'session-B')
    return root


def select_content(root, sid):
    write_candidate(sid, root, {'task_intent':sid+' task', 'work_summary':'Inspected evidence.txt for '+sid,
        'tools_used':['inspect'], 'artifacts_referenced':['evidence.txt'], 'open_risks':[]})
    (root / 'artifacts/session-closeout.txt').write_text(
        f'TASK_INTENT: {sid} task\nWORK_COMPLETED: Inspected evidence.txt for {sid}\n'
        'FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n'
        'NOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n')


def snapshot(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for sub in ('artifacts','memory') for p in (root/sub).rglob('*') if p.is_file()}


def invoke(root, payload, *extra):
    return subprocess.run([sys.executable, str(ENTRY), '--project-root', str(root), '--agent-id',
        'codex', '--format', 'json', '--no-ledger-write', *extra], input=payload,
        capture_output=True, text=True, encoding='utf-8',
        env={**os.environ, 'PYTHONIOENCODING':'utf-8'}, timeout=45)


@pytest.mark.parametrize('payload', ['', '{broken', '{}', '[]', '{"session_id":null}',
                                     '{"session_id":" "}', '{"session_id":"../session-B"}',
                                     '{"session_id":"COM1"}'])
def test_missing_or_invalid_codex_identity_cannot_consume_B(repo, payload):
    before = snapshot(repo)
    result = invoke(repo, payload)
    assert result.returncode == 1
    assert json.loads(result.stdout)['ok'] is False
    assert snapshot(repo) == before


def test_legacy_core_fallback_cannot_consume_B(repo):
    before = snapshot(repo)
    with pytest.raises(ValueError, match='shared fallback is ambiguous'):
        run_session_end_hook(repo, hook_session_id=None, ledger_write_allowed=False)
    assert snapshot(repo) == before


@pytest.mark.parametrize('manual', [False, True])
def test_explicit_A_ignores_B_pointer_and_links_receipt_to_HEAD(protected_repo, manual):
    repo = protected_repo
    prepare(repo, 'session-A')
    start({'hook_event_name':'SessionStart', 'source':'startup', 'session_id':'session-B', 'cwd':str(repo)}, repo)
    write_candidate('session-B', repo, {'task_intent':'B', 'work_summary':'B',
        'tools_used':[], 'artifacts_referenced':[], 'open_risks':[]})
    # The pointer still selects B; explicit A must be the only consumed session.
    result = invoke(repo, '' if manual else '{"session_id":"session-A"}',
                    *(['--session-id', 'session-A'] if manual else []))
    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data['session_id'] == 'session-A'
    assert data['closeout_status'] == 'valid'
    assert (repo/'artifacts/runtime/closeout-completions/session-A.json').exists()
    assert not (repo/'artifacts/runtime/closeout-completions/session-B.json').exists()
    receipt = json.loads(Path(data['closeout_receipt_artifact']).read_text())
    head = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    assert receipt['linked_head_commit'] == head


def test_conflicting_explicit_identity_is_rejected_without_writes(repo):
    before = snapshot(repo)
    result = invoke(repo, '{"session_id":"session-A"}', '--session-id', 'session-B')
    assert result.returncode == 1
    assert 'conflicts' in json.loads(result.stdout)['error']
    assert snapshot(repo) == before


def test_non_codex_fallback_remains_compatible(repo):
    write_session_envelope('legacy-session', repo, provider='test')
    select_content(repo, 'legacy-session')
    result = run_session_end_hook(repo, ledger_write_allowed=False)
    assert result['session_id'] == 'legacy-session'
    assert result['closeout_status'] == 'valid'


def test_manual_codex_command_requires_explicit_identity(tmp_path):
    from governance_tools.manage_agent_closeout import _manual_closeout_cmd
    assert '--session-id <SESSION_ID>' in _manual_closeout_cmd(tmp_path, 'codex')
    assert '--session-id' not in _manual_closeout_cmd(tmp_path, 'claude')


def test_unprepared_codex_smoke_is_not_R2_activation(repo):
    result = subprocess.run([
        sys.executable, '-m', 'governance_tools.manage_agent_closeout',
        '--project-root', str(repo), '--format', 'json', 'smoke', '--agent', 'codex',
    ], capture_output=True, text=True, encoding='utf-8',
        env={**os.environ, 'PYTHONIOENCODING':'utf-8',
             'AI_GOVERNANCE_FRAMEWORK_ROOT':str(ENTRY.parent.parent)}, timeout=45)
    # The legacy smoke authors no R2 ownership; deployment requires a separate
    # preparation/activation slice. It must not silently bypass protected main.
    assert result.returncode != 0, result.stdout
    assert not (repo/'artifacts/runtime/shared-closeout/owner.json').exists()
    assert not (repo/'artifacts/runtime/closeout-completions/session-A.json').exists()
    assert not (repo/'artifacts/runtime/closeout-completions/session-B.json').exists()
