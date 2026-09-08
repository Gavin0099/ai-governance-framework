import hashlib
import json
from uuid import uuid4

import pytest

from governance_tools import solo_r2_regression_projection as p
from governance_tools import solo_r2_blind_scoring_bundle as b


SOURCE = 'import unittest\nclass Tests(unittest.TestCase):\n    def test_bound(self):\n        self.assertEqual(1, 1)\n\nif __name__ == "__main__":\n    unittest.main()\n'
MISSING = "python : The term 'python' is not recognized as the name of a cmdlet\nCommandNotFoundException\n"


def command(cmd, output, code=0):
    return {'type': 'item.completed', 'item': {'type': 'command_execution',
            'command': cmd, 'aggregated_output': output, 'exit_code': code}}


def encode(events):
    raw = '\n'.join(json.dumps(e) for e in events).encode()
    return raw, hashlib.sha256(raw).hexdigest()


def project(events):
    raw, digest = encode(events)
    return p.project_regression_evidence(raw, expected_trace_sha256=digest)


def test_source_and_failed_start_survive_bundle_to_scorer_without_correctness_override():
    raw, digest = encode([command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py', SOURCE),
                          command('python -m unittest -v', MISSING, 1)])
    base = dict(source='def f(): pass', final_response={'summary': 'Tests could not run.'},
                correctness={'oracle_status': 'PASS', 'regression_status': 'NOT_EVALUATED'}, cost={'tool_calls': 3})
    enriched = p.project_scoring_input(json.dumps(base), raw, expected_trace_sha256=digest)
    labels = [hashlib.sha256(x.encode()).hexdigest() for x in ('x', 'y')]
    bundle = b.build_blind_scoring_bundle(evaluation_id=str(uuid4()), pair_id='synthetic-pair',
        slot='R2-SHAKEDOWN', rubric_id='frozen', outputs_by_label=dict.fromkeys(labels, enriched),
        presentation_entropy=bytes(range(32)))
    delivered = b.parse_blind_scoring_bundle(b.encode_blind_scoring_bundle(bundle))
    for row in delivered['outputs']:
        payload = json.loads(row['output_payload'])
        assert {k: payload[k] for k in base} == base
        evidence = payload['regression_evidence']
        assert evidence['test_source'] == SOURCE
        assert evidence['executions'] == [dict(command='python -m unittest -v',
            execution_status='NOT_EXECUTED', exit_code=1, diagnostic=MISSING, version_binding='NOT_CONFIRMED')]


@pytest.mark.parametrize('output,code', [('Ran 2 tests in 0.001s\n\nOK\n', 0),
                                        ('Ran 2 tests in 0.001s\n\nFAILED (failures=1)\n', 1)])
def test_actual_results_preserved_without_assigning_quality(output, code):
    e = project([command('python -m unittest -v', output, code)])
    assert e['executions'][0] == dict(command='python -m unittest -v',
        execution_status='EXECUTED', exit_code=code, diagnostic=output, version_binding='NOT_CONFIRMED')
    assert e['source_status'] == 'MISSING'


def test_absence_not_success():
    assert project([]) == dict(test_source=None, source_status='MISSING', executions=[],
                               execution_evidence_status='MISSING')


def test_missing_exit_code_does_not_establish_startup_failure():
    assert project([command('python -m unittest -v', MISSING, None)])['executions'][0]['execution_status'] == 'UNRESOLVED'


@pytest.mark.parametrize('cmd,out', [('python -m unittest -v', 'All good'),
                                    ('python -m unittest -v; echo OK', MISSING)])
def test_unknown_or_compound_execution_not_inferred(cmd, out):
    assert project([command(cmd, out, 1)])['executions'][0]['execution_status'] == 'UNRESOLVED'


def test_transport_wrapper_removed_only():
    cmd = r'"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -Command "python -m unittest -v"'
    assert project([command(cmd, MISSING, 1)])['executions'][0]['command'] == 'python -m unittest -v'


def test_later_file_change_invalidates_source_observation():
    change = {'type': 'item.completed', 'item': {'type': 'file_change', 'changes': [
        {'path': r'D:\private\test_queue_range.py', 'kind': 'update'}]}}
    e = project([command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py', SOURCE), change])
    assert e['source_status'] == 'STALE_OBSERVATION'
    assert e['test_source'] == SOURCE


@pytest.mark.parametrize('leak', [r'C:\secret\workspace', 'TREATMENT', 'execution-2', 'a'*64])
def test_leaking_diagnostic_rejected(leak):
    with pytest.raises(b.BlindScoringBundleError):
        project([command('python -m unittest -v', leak, 1)])


def test_leaking_test_source_rejected():
    with pytest.raises(b.BlindScoringBundleError):
        project([command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py',
                         SOURCE.replace('import unittest', 'import unittest\n# CONTROL'))])


def test_digest_mismatch_rejects_before_projection():
    with pytest.raises(b.BlindScoringBundleError):
        p.project_regression_evidence(b'{}', expected_trace_sha256='0'*64)


def test_malformed_trace_rejected():
    raw = b'not json'
    with pytest.raises(b.BlindScoringBundleError):
        p.project_regression_evidence(raw, expected_trace_sha256=hashlib.sha256(raw).hexdigest())


def test_unrelated_readback_not_misrepresented_as_test_source():
    e = project([command('echo "test_queue_range.py"', SOURCE)])
    assert e['test_source'] is None


def paired(end):
    import copy
    end = copy.deepcopy(end)
    end['item']['id'] = str(uuid4())
    start = copy.deepcopy(end)
    start['type'] = 'item.started'
    for field in ('aggregated_output', 'exit_code'):
        start['item'].pop(field, None)
    return [start, end]

SUBJECT = 'def select_entries(entries, lower, upper):\n    return entries\n'


def read_versions(test=SOURCE, subject=SUBJECT):
    return paired(command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py', test)) + paired(
        command(r'Get-Content -Raw -LiteralPath .\queue_range.py', subject))


def execute(name='cmd'):
    end = command('python -m unittest -v', 'Ran 2 tests in 0.001s\n\nOK\n')
    end['item']['id'] = name
    return [{'type':'item.started','item':{'type':'command_execution','id':name,
             'command':'python -m unittest -v'}}, end]


def change(name):
    return paired({'type':'item.completed','item':{'type':'file_change','changes':[{'path':name,'kind':'update'}]}})


@pytest.mark.parametrize('name', ['test_queue_range.py','queue_range.py'])
def test_success_before_relevant_change_is_stale(name):
    new = read_versions(test=SOURCE+'\n' if name.startswith('test_') else SOURCE,
                        subject=SUBJECT+'\n' if name=='queue_range.py' else SUBJECT)
    e = project(read_versions()+execute()+change(name)+new)
    assert e['executions'][0]['version_binding'] == 'EXECUTED_FOR_STALE_VERSION'


def test_changed_readback_then_execution_is_current():
    e = project(change('test_queue_range.py')+read_versions()+execute())
    assert e['executions'][0]['version_binding'] == 'EXECUTED_FOR_CURRENT_VERSION'


def test_two_executions_bind_different_content_versions():
    e = project(read_versions()+execute('old')+change('queue_range.py')
                +read_versions(subject=SUBJECT+'\n')+execute('new'))
    assert [x['version_binding'] for x in e['executions']] == [
        'EXECUTED_FOR_STALE_VERSION','EXECUTED_FOR_CURRENT_VERSION']


@pytest.mark.parametrize('events', [execute(), read_versions()+execute()[1:],
    read_versions()+execute()+change('queue_range.py'),
    read_versions()+execute()[:1]+change('queue_range.py')+read_versions()+execute()[1:]])
def test_unknown_or_incomplete_version_relationship_not_confirmed(events):
    assert project(events)['executions'][0]['version_binding'] == 'NOT_CONFIRMED'


def test_same_content_after_change_is_not_misclassified_by_ordinal():
    e = project(read_versions()+execute()+change('test_queue_range.py')+read_versions())
    assert e['executions'][0]['version_binding'] == 'EXECUTED_FOR_CURRENT_VERSION'


def test_original_reproducer_now_differs():
    a = project(read_versions()+execute()+change('test_queue_range.py')+read_versions(test=SOURCE+'\n'))
    b = project(read_versions()+change('test_queue_range.py')+read_versions(test=SOURCE+'\n')+execute())
    assert a != b


def test_final_payload_subject_mismatch_never_current():
    raw, digest = encode(read_versions()+execute())
    e = p.project_regression_evidence(raw, expected_trace_sha256=digest, expected_subject_source='different')
    assert e['executions'][0]['version_binding'] == 'NOT_CONFIRMED'


def broken_histories():
    compound = paired(command('python -m unittest -v; Set-Content .\\queue_range.py changed',
                              'Ran 2 tests in 0.001s\n\nOK\n'))
    mismatch = paired(command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py', SOURCE))
    mismatch[0]['item']['command'] = 'echo unknown'
    return [
        read_versions()+execute()+compound,
        read_versions()+compound+execute(),
        read_versions()+execute()+[{'type':'item.started','item':{'type':'file_change','id':'pending','changes':[]}}],
        mismatch+paired(command(r'Get-Content -Raw -LiteralPath .\queue_range.py', SUBJECT))+execute(),
        read_versions()+execute()+execute('unfinished')[:1],
        read_versions()+execute()+change('queue_range.py')[:1],
        read_versions()+execute()+change('queue_range.py')[1:]+read_versions(),
        read_versions()+execute()+paired(command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py', '# changed\n'+SOURCE)),
    ]


@pytest.mark.parametrize('events', broken_histories())
def test_event_integrity_review_reproducers_fail_closed(events):
    assert all(x['version_binding'] == 'NOT_CONFIRMED' for x in project(events)['executions'])


def test_mismatched_mutation_pair_cannot_be_repaired_by_later_readback():
    mutation = change('queue_range.py')
    mutation[-1]['item']['changes'][0]['kind'] = 'delete'
    e = project(read_versions()+mutation+read_versions()+execute())
    assert e['executions'][0]['version_binding'] == 'NOT_CONFIRMED'


def test_unpaired_readback_cannot_establish_version():
    reads = [command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py', SOURCE),
             command(r'Get-Content -Raw -LiteralPath .\queue_range.py', SUBJECT)]
    assert project(reads+execute())['executions'][0]['version_binding'] == 'NOT_CONFIRMED'

