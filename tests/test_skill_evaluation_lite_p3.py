"""Actual synthetic Python receipts -> anonymous P3 input -> frozen scores."""
from dataclasses import replace
import pytest
from governance_tools import skill_evaluation_lite as lite
from governance_tools import skill_evaluation_lite_p3 as p3
from governance_tools import skill_evaluation_lite_benchmark as bench
from governance_tools import skill_evaluation_lite_live as live
from tests.test_skill_evaluation_lite_benchmark import binary, config, submission


def collected(tmp_path, kind='pass'):
    fixture = bench.load_fixture('easy_queue_range')
    value = submission(fixture)
    if kind == 'import':
        value['test_source'] = value['test_source'].replace('from queue_range import select_entries\n', '')
    elif kind == 'syntax':
        value['source'] = value['source'].replace('):', ')', 1)
    elif kind == 'assertion':
        value['test_source'] = value['test_source'].replace('self.assertEqual(', 'self.assertNotEqual(')
    elif kind == 'unknown':
        value['test_source'] = value['test_source'].replace('self.assertEqual(', 'self.assertEqual(1/0, ')
    item = bench.collect(fixture, binary(), tmp_path, tmp_path, value, {'elapsed_ms':0}, p3=True)
    return fixture, item


def session(fixture, item):
    return lite.LiteSession({'CONTROL':item, 'TREATMENT':item},
        rubric_bytes=fixture.rubric, run_id='00000000-0000-4000-8000-000000000003', synthetic=True)


@pytest.mark.parametrize('kind,expected', [('import',0), ('syntax',0), ('assertion',0), ('unknown',lite.NA), ('pass',2)])
def test_real_synthetic_completion_and_freeze(tmp_path, kind, expected):
    fixture, item = collected(tmp_path, kind)
    run = session(fixture, item)
    rows = lite._parse(run.scorer_input)['outputs']
    for row in rows:
        assessment = row['regression_assessment']
        assert assessment['version_identity'] == 'CONFIRMED'
        assert assessment['execution_status'] == ('COMPLETED' if kind=='pass' else 'ERROR')
        assert assessment['required_regression_score'] == (None if expected==2 else expected)
        assert row['regression_evidence']['test_source']
        assert item.expected_observation_sha256 not in run.scorer_input.decode()
    with pytest.raises(lite.LiteError):
        run.unblind(authorized_freeze_sha256='0'*64)
    response = lite.synthetic_scorer(run.scorer_input)
    assert all(d['regression_safety']['score']==expected for d in lite._parse(response)['scores'].values())
    frozen = run.freeze(response)
    report = lite._parse(run.unblind(authorized_freeze_sha256=lite.digest(frozen)))
    assert frozen == run.frozen_scores
    assert report['arms']['CONTROL']['oracle'] == rows[0]['correctness']
    assert report['claim_ceiling'] == list(lite.CLAIMS)


def change(item, edit):
    observation = lite._parse(item.observation)
    edit(observation)
    raw = lite.encode(observation)
    return replace(item, observation=raw, expected_observation_sha256=lite.digest(raw))


@pytest.mark.parametrize('kind', ['timeout','missing','stale','harness','exit_only'])
def test_incomplete_or_unattributable_receipts_remain_na(tmp_path,kind):
    fixture,item = collected(tmp_path,'import')
    def edit(o):
        if kind=='timeout': o['result']['status']='TIMEOUT'
        if kind=='missing': o['result']['exit_code']=None
        if kind=='stale': o['receipt']['after']['queue_range.py']='0'*64
        if kind=='harness':
            for d in o['receipt']['details']: d['origin']='HOST'
        if kind=='exit_only':
            o['receipt']['details']=[]
            o['receipt']['count']={'tests_run':0,'errors':0,'failures':0}
    run=session(fixture,change(item,edit))
    for row in lite._parse(run.scorer_input)['outputs']:
        assert row['regression_assessment']['required_regression_score']==lite.NA


def test_digest_and_mixed_policy_rejected(tmp_path):
    fixture,item=collected(tmp_path)
    with pytest.raises(lite.LiteError):session(fixture,replace(item,observation=item.observation+b' '))
    with pytest.raises(lite.LiteError):
        lite.LiteSession({'CONTROL':item,'TREATMENT':item.scoring},rubric_bytes=fixture.rubric,run_id='mix',synthetic=True)


def test_nonzero_cannot_override_required_score(tmp_path):
    fixture,item=collected(tmp_path,'import'); run=session(fixture,item)
    wrong=lite._parse(lite.synthetic_scorer(run.scorer_input))
    for d in wrong['scores'].values():d['regression_safety']['score']=2
    with pytest.raises(lite.LiteError):run.freeze(lite.encode(wrong))


@pytest.mark.parametrize('key',bench.INTERFACES)
def test_future_entry_uses_explicit_contract_without_models(tmp_path,monkeypatch,key):
    fixture=bench.load_fixture(key); prompts=[]
    def fake(*args):
        prompts.append(args[4]); return submission(fixture),{'elapsed_ms':0}
    monkeypatch.setattr(live,'model_call',fake)
    run=bench.prepare_task(tmp_path/'new',config(),b'fixed-recipe',key,p3=True)
    assert len(prompts)==2
    assert 'tests must explicitly use' in prompts[0]
    assert prompts[1]==prompts[0]+'\nAdditional process guidance:\nfixed-recipe'
    assert 'regression_assessment' in lite._parse(run.scorer_input)['outputs'][0]


def test_authority_failure_precedes_model_or_workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(p3,'POLICY_SHA','0'*64)
    monkeypatch.setattr(live,'model_call',lambda *a:pytest.fail('model called'))
    with pytest.raises(lite.LiteError):bench.prepare_task(tmp_path/'new',config(),b'fixed-recipe','easy_queue_range',p3=True)
    assert not (tmp_path/'new').exists()


@pytest.mark.parametrize('phase',['LOAD_TEST','LOAD_SUITE','RUN_TESTS'])
def test_actual_host_failure_not_submission_fault(tmp_path,monkeypatch,phase):
    marker = f"phase = '{phase}'"
    monkeypatch.setattr(p3,'HOST',p3.HOST.replace(marker, marker+'\n    missing_host_symbol'))
    fixture,item=collected(tmp_path)
    state=lite._parse(session(fixture,item).scorer_input)['outputs'][0]['regression_assessment']
    assert state['version_identity']=='CONFIRMED'
    assert state['execution_status']=='ERROR'
    assert state['attribution']=='HARNESS_OR_ENVIRONMENT'
    assert state['required_regression_score']==lite.NA


def test_subtest_assertion_failures_keep_attribution(tmp_path):
    fixture=bench.load_fixture('hard_dependency_cycle'); value=submission(fixture)
    value['test_source']='''import unittest
from dependency_graph import has_cycle
class Tests(unittest.TestCase):
    def test_cases(self):
        for graph in [{}, {'a': []}]:
            with self.subTest(graph=graph):
                self.assertTrue(has_cycle(graph))
unittest.main()
'''
    item=bench.collect(fixture,binary(),tmp_path,tmp_path,value,{'elapsed_ms':0},p3=True)
    state=lite._parse(session(fixture,item).scorer_input)['outputs'][0]['regression_assessment']
    assert state['test_count']==dict(tests_run=1,errors=0,failures=2)
    assert state['required_regression_score']==0


def test_original_error_semantics_remain_unchanged(tmp_path):
    fixture=bench.load_fixture('easy_queue_range'); value=submission(fixture)
    value['test_source']=value['test_source'].replace('from queue_range import select_entries\n','')
    item=bench.collect(fixture,binary(),tmp_path,tmp_path,value,{'elapsed_ms':0})
    run=session(fixture,item)
    assert all(d['regression_safety']['score']==lite.NA
        for d in lite._parse(lite.synthetic_scorer(run.scorer_input))['scores'].values())
    assert 'regression_assessment' not in run.scorer_input.decode()
