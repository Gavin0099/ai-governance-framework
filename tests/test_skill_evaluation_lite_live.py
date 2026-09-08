import json
from pathlib import Path
import sys

import pytest

from governance_tools import skill_evaluation_lite as lite
from governance_tools import skill_evaluation_lite_live as live
from governance_tools.solo_r2_future_scoring_consumer import prepare_scoring_delivery

FIXED = live.BASELINE.replace('lower < e[0] < upper', 'lower <= e[0] <= upper')
TEST = '''import unittest
from queue_range import select_entries
class Tests(unittest.TestCase):
    def test_endpoints(self):
        self.assertEqual(select_entries([(1,'a'),(2,'b')],1,2),[(1,'a'),(2,'b')])
    def test_preservation(self):
        rows=[(2,'b'),(1,'a'),(1,'a')]; original=list(rows)
        self.assertEqual(select_entries(rows,1,2),original)
        self.assertEqual(rows,original)
    def test_empty_and_reversed(self):
        self.assertEqual(select_entries([],1,2),[])
        self.assertEqual(select_entries([(1,'a')],2,1),[])
if __name__ == '__main__':
    unittest.main()
'''


def binary():
    p=Path(sys.executable).resolve(); b=p.read_bytes()
    return live.Binary(str(p),len(b),lite.digest(b))


def config():
    p=binary()
    return dict(python=vars(p),codex=vars(p),model='test-model',codex_home=str(Path.home()),skill_sha256=lite.digest(b'recipe'))


def test_real_host_oracle_and_regression_preserve_evidence(tmp_path):
    value=dict(source=FIXED,test_source=TEST,summary='Inclusive bounds; submitted tests not executed by author.')
    item=live.collect_arm(binary(),tmp_path,tmp_path,value,dict(elapsed_ms=5))
    result=prepare_scoring_delivery(inputs_by_label={'a'*64:item,'b'*64:item},
        evaluation_id='00000000-0000-4000-8000-000000000001',pair_id='fixture',slot='R2-SHAKEDOWN',
        rubric_id='real',rubric_bytes=live.RUBRIC,expected_rubric_sha256=lite.digest(live.RUBRIC),
        presentation_entropy=bytes(range(32)))
    for row in json.loads(result.scorer_input_bytes)['outputs']:
        assert row['correctness']['passed_case_count']==10
        assert row['regression_evidence']['test_source']==TEST
        run=row['regression_evidence']['executions'][0]
        assert run['exit_code']==0 and 'Ran 3 tests' in run['diagnostic']
        assert run['version_binding']=='EXECUTED_FOR_CURRENT_VERSION'
    req=json.loads((tmp_path/'regression.request.json').read_bytes())
    assert req['argv'][0]==binary().path
    assert 'PATH' not in req['environment']


def test_fixed_oracle_rejects_baseline(tmp_path):
    (tmp_path/'queue_range.py').write_text(live.BASELINE)
    result=live.run_process(binary(),['-I','-B','-c',live.ORACLE],tmp_path,
                            live.environment(tmp_path,tmp_path),15,tmp_path/'baseline')
    correctness=live.oracle_result(result)
    assert correctness['oracle_status']=='FAIL' and correctness['passed_case_count']<10


@pytest.mark.parametrize('result',[dict(stdout='{"cases":[true]}',exit_code=0),
                                  dict(stdout=json.dumps({'cases':[True]*10}),exit_code=1),
                                  dict(stdout='not completion',exit_code=0)])
def test_oracle_unverifiable_is_not_pass(result):
    with pytest.raises(lite.LiteError):live.oracle_result(result)


def test_outer_wrong_pin_no_launch_or_root(tmp_path,monkeypatch):
    called=[]
    monkeypatch.setattr(live.subprocess,'Popen',lambda *a,**k:called.append(True))
    c=config(); c['codex']=dict(c['codex'],sha256='0'*64)
    with pytest.raises(lite.LiteError):live.run_once(tmp_path/'absent',c,b'recipe',authorize_unblinding=True)
    assert not called and not (tmp_path/'absent').exists()


def test_outer_requires_authority_and_exact_recipe(tmp_path):
    with pytest.raises(lite.LiteError):live.run_once(tmp_path/'a',config(),b'recipe',authorize_unblinding=False)
    with pytest.raises(lite.LiteError):live.run_once(tmp_path/'b',config(),b'wrong',authorize_unblinding=True)
    assert not (tmp_path/'a').exists() and not (tmp_path/'b').exists()


def model_result(events,exit_code=0):
    return dict(exit_code=exit_code,stdout='\n'.join(json.dumps(e) for e in events))


@pytest.mark.parametrize('events',[
    [{'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}}],
    [{'type':'turn.failed'}],
    [{'type':'item.completed','item':{'type':'command_execution','command':'read mapping'}},{'type':'turn.completed'}],
    [{'type':'item.completed','item':{'type':'mcp_tool_call'}},{'type':'turn.completed'}],
    [{'type':'turn.completed'},{'type':'turn.completed'}]])
def test_model_no_completion_or_tool_call_rejected(events):
    with pytest.raises(lite.LiteError):live.parse_model(model_result(events))


def test_model_completion_not_natural_language_claim():
    events=[{'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}},
            {'type':'turn.completed'}]
    assert live.parse_model(model_result(events))=={'ok':True}
    with pytest.raises(lite.LiteError):live.parse_model(model_result(events,1))


def test_closed_environment_and_model_command(tmp_path,monkeypatch):
    monkeypatch.setenv('PATH','hostile');monkeypatch.setenv('PYTHONPATH','hostile')
    monkeypatch.setenv('GIT_DIR','hostile')
    captured=[]
    def capture(b,args,cwd,env,timeout,stem,stdin):
        captured.append((args,cwd,env,stdin))
        return model_result([{'type':'item.completed','item':{'type':'agent_message','text':'{}'}},
                             {'type':'turn.completed'}])
    monkeypatch.setattr(live,'run_process',capture)
    live.model_call(binary(),'same-model',tmp_path,tmp_path,'anonymous only',{'type':'object'})
    args,cwd,env,stdin=captured[0]
    assert '--ignore-user-config' in args and '--ephemeral' in args
    assert args.count('cli_auth_credentials_store="keyring"') == 1
    assert args[args.index('cli_auth_credentials_store="keyring"') - 1] == '-c'
    assert 'project_doc_max_bytes=0' in args and 'shell_tool' in args
    assert 'skip_host_skill_discovery' in args
    assert cwd==tmp_path/'context' and stdin==b'anonymous only'
    assert not {'PATH','PYTHONPATH','GIT_DIR'} & env.keys()


def test_live_coordinator_real_host_with_fake_model_transport(tmp_path,monkeypatch):
    calls=[]
    def fake_model(b,model,home,folder,prompt,schema):
        calls.append((folder,prompt))
        if folder.name=='scorer':
            packet=json.loads(prompt.split('\n',1)[1])
            assert 'CONTROL' not in json.dumps(packet) and 'TREATMENT' not in json.dumps(packet)
            assert 'host-warning-with-private-identity' not in json.dumps(packet)
            assert not (folder.parent/'scores-frozen.json').exists()
            return json.loads(lite.synthetic_scorer(lite.encode(packet))),{'elapsed_ms':1,'runtime_warnings':['host-warning-with-private-identity']}
        return dict(source=FIXED,test_source=TEST,summary='Boundary predicates repaired; tests submitted to host.'),{'elapsed_ms':1,'runtime_warnings':['host-warning-with-private-identity']}
    monkeypatch.setattr(live,'model_call',fake_model)
    report=live.run_once(tmp_path/'new',config(),b'recipe',authorize_unblinding=True)
    assert report['result']=='REAL_LITE_END_TO_END_VALIDATED'
    assert report['synthetic'] is False and report['claim_ceiling']==list(lite.CLAIMS)
    assert 'Additional process guidance' not in calls[0][1] and 'Additional process guidance' in calls[1][1]
    assert report['freeze_sha256']==lite.digest((tmp_path/'new'/'scores-frozen.json').read_bytes())
    assert all(row['oracle']['passed_case_count']==10 for row in report['arms'].values())
    assert report['runtime_warnings']==dict.fromkeys(('CONTROL','TREATMENT','scorer'),['host-warning-with-private-identity'])
    with pytest.raises(FileExistsError):live.run_once(tmp_path/'new',config(),b'recipe',authorize_unblinding=True)
    assert len(calls)==3  # no second generation


def test_failure_stops_without_scorer_or_report(tmp_path,monkeypatch):
    calls=[]
    def fake(*a):
        calls.append(True)
        return dict(source=FIXED,test_source=TEST,summary='CONTROL identity'),{'elapsed_ms':1}
    monkeypatch.setattr(live,'model_call',fake)
    with pytest.raises(lite.LiteError):live.run_once(tmp_path/'new',config(),b'recipe',authorize_unblinding=True)
    assert len(calls)==1 and not (tmp_path/'new'/'report.json').exists()
    assert json.loads((tmp_path/'new'/'failure.json').read_bytes())['retry']=='NOT_PERFORMED'


def test_subprocess_timeout_is_not_completion(tmp_path):
    with pytest.raises(lite.LiteError,match='timeout'):
        live.run_process(binary(),['-I','-c','import time; time.sleep(3)'],tmp_path,
                         live.environment(tmp_path,tmp_path),0.1,tmp_path/'timeout')
    assert json.loads((tmp_path/'timeout.result.json').read_bytes())['status']=='TIMEOUT'


@pytest.mark.parametrize('source',[
    'import os\ndef select_entries(entries, lower, upper): return []',
    'def select_entries(entries, lower, upper):\n    open("stolen", "w").write("x")',
    'def select_entries(entries, lower, upper):\n    return entries.__class__.__base__',
    'def select_entries(entries, lower, upper):\n    return eval("1")'])
def test_unsafe_generated_source_rejected_before_execution(source,tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(live,'run_process',lambda *a,**k:calls.append(True))
    with pytest.raises(lite.LiteError):
        live.collect_arm(binary(),tmp_path,tmp_path,dict(source=source,test_source=TEST,summary='summary'),{'elapsed_ms':1})
    assert not calls and not (tmp_path/'workspace').exists()


def test_test_file_cannot_import_host_io():
    with pytest.raises(lite.LiteError):live.validate_code(TEST.replace('import unittest','import unittest\nimport subprocess'),tests=True)


def test_scorer_has_independent_task_and_baseline():
    assert b'Task contract:' in live.RUBRIC and live.BASELINE.encode() in live.RUBRIC


# Exact warning text captured from the completed 0.153.4 live turn.
OBSERVED_WARNINGS = ['Configured value for `windows.sandbox` is disallowed by requirements; falling back to required value Some(Elevated). Details: invalid value for `windows.sandbox`: `None` is not in the allowed set [Elevated] (set by C:\\ProgramData\\OpenAI\\Codex\\requirements.toml)', 'Under-development features enabled: skip_host_skill_discovery. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in C:\\Users\\daish\\.codex\\config.toml.', 'Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.']


def warning_turn(message):
    return model_result([
        {'type':'item.completed','item':{'id':'w','type':'error','message':message}},
        {'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}},
        {'type':'turn.completed'}])


@pytest.mark.parametrize('message', OBSERVED_WARNINGS)
def test_observed_warning_is_preserved_with_completed_response(message):
    warnings=[]
    assert live.parse_model(warning_turn(message),warnings=warnings)=={'ok':True}
    assert len(warnings)==1 and warnings[0]['message']==message
    assert warnings[0]['category']


@pytest.mark.parametrize('message', ['Runtime failed', 'Access denied',
    *[m+' unexpected extra error' for m in OBSERVED_WARNINGS]])
def test_unknown_or_extended_error_remains_closed(message):
    warnings=[]
    with pytest.raises(lite.LiteError,match='Unrecognized runtime error'):
        live.parse_model(warning_turn(message),warnings=warnings)
    assert warnings==[]


@pytest.mark.parametrize('kind',['command_execution','file_change','mcp_tool_call'])
def test_warning_never_excuses_forbidden_tool_event(kind):
    result=warning_turn(OBSERVED_WARNINGS[0])
    result['stdout']+='\n'+json.dumps({'type':'item.completed','item':{'type':kind}})
    with pytest.raises(lite.LiteError,match='Tool access'):
        live.parse_model(result)


@pytest.mark.parametrize('mutation',['nonzero','missing_completion','turn_failed','extra_field','unfinished_error'])
def test_known_warning_never_excuses_incomplete_or_invalid_turn(mutation):
    result=warning_turn(OBSERVED_WARNINGS[0])
    events=[json.loads(x) for x in result['stdout'].splitlines()]
    if mutation=='nonzero': result['exit_code']=1
    if mutation=='missing_completion': events.pop()
    if mutation=='turn_failed': events[-1]={'type':'turn.failed'}
    if mutation=='extra_field': events[0]['item']['command']='forbidden command'
    if mutation=='unfinished_error': events[0]['type']='item.started'
    result['stdout']='\n'.join(json.dumps(e) for e in events)
    with pytest.raises(lite.LiteError): live.parse_model(result)


def test_model_call_durably_retains_warning_without_altering_response(tmp_path,monkeypatch):
    original=warning_turn(OBSERVED_WARNINGS[0])
    monkeypatch.setattr(live,'run_process',lambda *a,**k:dict(original))
    value,result=live.model_call(binary(),'test',tmp_path,tmp_path,'anonymous',{'type':'object'})
    assert value=={'ok':True}
    saved=json.loads((tmp_path/'runtime-warnings.json').read_bytes())
    assert saved==result['runtime_warnings'] and saved[0]['message']==OBSERVED_WARNINGS[0]
    assert result['stdout']==original['stdout']
