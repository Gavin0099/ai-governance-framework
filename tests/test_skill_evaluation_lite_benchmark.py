"""No-model integration: authored submissions, actual pinned host Python runs."""
import ast
import json
from pathlib import Path
import shutil
import sys

import pytest

from governance_tools import skill_evaluation_lite_benchmark as bench
from governance_tools import skill_evaluation_lite_live as live
from governance_tools import skill_evaluation_lite as lite


def binary():
    path=Path(sys.executable).resolve(); raw=path.read_bytes()
    return live.Binary(str(path),len(raw),lite.digest(raw))


def config():
    return dict(codex=vars(binary()),python=vars(binary()),model='fixture-only',
        codex_home=str(Path.home()),skill_sha256=lite.digest(b'fixed-recipe'))


def submission(fixture, variant='correct'):
    # Evaluator-only fixtures become authored synthetic submissions IN TESTS ONLY.
    tree=ast.parse((bench.PACK/fixture.key/'validation_variants.py').read_bytes())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==variant)
    node.name=fixture.interface[0]
    source=ast.unparse(node)+'\n'
    function,source_name,_=fixture.interface
    rows=['import unittest',f'from {source_name[:-3]} import {function}', 'class Tests(unittest.TestCase):']
    for i,case in enumerate(lite._parse(fixture.cases)['oracle_cases']):
        rows += [f'    def test_case_{i}(self):',f'        self.assertEqual({function}({', '.join(repr(a) for a in case["args"])}), {case["expected"]!r})']
    rows += ["if __name__ == '__main__':",'    unittest.main()']
    return dict(source=source,test_source='\n'.join(rows)+'\n',summary='Authored integration fixture only; no quality or Skill result claimed.')


@pytest.mark.parametrize('key',bench.INTERFACES)
def test_full_no_model_workspace_oracle_projection_scorer(tmp_path,monkeypatch,key):
    fixture=bench.load_fixture(key); calls=[]
    def fake(binary,model,home,root,prompt,schema):
        calls.append((binary,model,home,root,prompt,schema))
        return submission(fixture),dict(elapsed_ms=1)
    monkeypatch.setattr(live,'model_call',fake)
    root=tmp_path/'run'
    session=bench.prepare_task(root,config(),b'fixed-recipe',key)
    assert len(calls)==2
    assert calls[0][:3]==calls[1][:3] and calls[0][5]==calls[1][5]
    assert calls[1][4]==calls[0][4]+'\nAdditional process guidance:\nfixed-recipe'
    assert fixture.task.decode() in calls[0][4] and fixture.baseline.decode() in calls[0][4]
    assert 'def correct(' not in calls[0][4] and 'def superficial(' not in calls[0][4]
    assert calls[0][3]!=calls[1][3]
    requests=[]
    for arm in ('CONTROL','TREATMENT'):
        folder=root/arm
        requests.append(lite._parse((folder/'regression.request.json').read_bytes()))
        receipt=lite._parse((folder/'input-identity.json').read_bytes())
        for name,digest in receipt['source_versions'].items():
            assert lite.digest((folder/'workspace'/name).read_bytes())==digest
        assert set(receipt['source_versions'])==set(fixture.interface[1:])
    assert requests[0]['argv']==requests[1]['argv']
    assert requests[0]['timeout_seconds']==requests[1]['timeout_seconds']==15
    assert {k:v for k,v in requests[0]['environment'].items() if k not in ('TEMP','TMP')}=={k:v for k,v in requests[1]['environment'].items() if k not in ('TEMP','TMP')}
    visible=lite._parse(session.scorer_input)
    assert visible['rubric']==fixture.rubric.decode()
    assert 'CONTROL' not in session.scorer_input.decode() and 'TREATMENT' not in session.scorer_input.decode()
    assert str(tmp_path) not in session.scorer_input.decode()
    for row in visible['outputs']:
        assert row['correctness']['required_case_count']==len(lite._parse(fixture.cases)['oracle_cases'])
        assert row['correctness']['oracle_status']=='PASS'
        assert row['regression_evidence']['test_source']==submission(fixture)['test_source']
        execution=row['regression_evidence']['executions'][0]
        assert execution['version_binding']=='EXECUTED_FOR_CURRENT_VERSION'
        diagnostic=execution['diagnostic']
        assert 'HOST_COMPLETION: COMPLETED' in diagnostic and 'EXIT_CODE: 0' in diagnostic
        assert 'STDOUT:' in diagnostic and 'STDERR:' in diagnostic and 'TESTS_RUN:' in diagnostic
        assert fixture.interface[2] in diagnostic
        assert lite._available(row,'regression_safety')
    with pytest.raises(lite.LiteError,match='Freeze'):
        session.unblind(authorized_freeze_sha256='0'*64)
    assert not (root/'scores-frozen.json').exists()
    with pytest.raises(FileExistsError):
        bench.prepare_task(root,config(),b'fixed-recipe',key)


@pytest.mark.parametrize('key',bench.INTERFACES)
@pytest.mark.parametrize('variant',['baseline','superficial'])
def test_each_oracle_rejects_wrong_repair(tmp_path,key,variant):
    fixture=bench.load_fixture(key)
    value=submission(fixture,variant if variant!='baseline' else 'correct')
    if variant=='baseline':value['source']=fixture.baseline.decode()
    item=bench.collect(fixture,binary(),tmp_path,tmp_path,value,dict(elapsed_ms=0))
    correctness=lite._parse(item.payload)['correctness']
    assert correctness['oracle_status']=='FAIL'
    assert correctness['passed_case_count']<correctness['required_case_count']


@pytest.mark.parametrize('key',bench.INTERFACES)
def test_wrong_paths_signature_and_identity_rejected_before_workspace(tmp_path,key):
    fixture=bench.load_fixture(key); value=submission(fixture)
    for change in [dict(files={'../escape.py':'x'}),dict(summary='CONTROL identity'),
                   dict(test_source=value['test_source'].replace(fixture.interface[1][:-3],'wrong_module')),
                   dict(source=value['source'].replace(fixture.interface[0]+'(', 'wrong_name(',1))]:
        bad=dict(value,**change)
        with pytest.raises(lite.LiteError):bench.collect(fixture,binary(),tmp_path,tmp_path,bad,dict(elapsed_ms=0))
        assert not (tmp_path/'workspace').exists()


def test_manifest_and_source_mismatch_fail_before_model(tmp_path,monkeypatch):
    pack=tmp_path/'pack'; shutil.copytree(bench.PACK,pack);monkeypatch.setattr(bench,'PACK',pack)
    p=pack/'hard_dependency_cycle/TASK.md';p.write_bytes(p.read_bytes()+b'x')
    monkeypatch.setattr(live,'model_call',lambda *a:pytest.fail('must not launch'))
    with pytest.raises(lite.LiteError,match='Fixture identity'):
        bench.prepare_task(tmp_path/'no-root',config(),b'fixed-recipe','hard_dependency_cycle')
    assert not (tmp_path/'no-root').exists()
    with pytest.raises(lite.LiteError):bench.load_fixture('fourth-task')
    (pack/'manifest.json').write_bytes(b'{}')
    with pytest.raises(lite.LiteError,match='manifest'):bench.load_fixture('easy_queue_range')


def test_zero_tests_remains_not_assessable(tmp_path):
    f=bench.load_fixture('easy_queue_range');v=submission(f)
    v['test_source']="import unittest\nif __name__ == '__main__':\n    unittest.main()\n"
    item=bench.collect(f,binary(),tmp_path,tmp_path,v,dict(elapsed_ms=0))
    session=lite.LiteSession({'CONTROL':item,'TREATMENT':item},rubric_bytes=f.rubric,run_id='00000000-0000-4000-8000-000000000001',synthetic=True)
    for row in lite._parse(session.scorer_input)['outputs']:
        assert row['correctness']['oracle_status']=='PASS'
        assert not lite._available(row,'regression_safety')


def test_source_mutation_rejected(tmp_path,monkeypatch):
    f=bench.load_fixture('easy_queue_range'); real=live.run_process
    def changed(binary,args,cwd,env,timeout,stem,stdin=None):
        result=real(binary,args,cwd,env,timeout,stem,stdin)
        if stem.name=='regression':(cwd/f.interface[1]).write_text('changed')
        return result
    monkeypatch.setattr(live,'run_process',changed)
    with pytest.raises(lite.LiteError,match='version changed'):
        bench.collect(f,binary(),tmp_path,tmp_path,submission(f),dict(elapsed_ms=0))


@pytest.mark.parametrize('source',["import os\ndef has_cycle(graph): return False", "def has_cycle(graph): return open('x').read()", "def has_cycle(graph): return graph.__class__"])
def test_benchmark_ast_still_rejects_host_access(source):
    with pytest.raises(lite.LiteError):live.validate_code(source,tests=False,benchmark_function='has_cycle')


def test_wrong_oracle_count_rejected():
    f=bench.load_fixture('hard_dependency_cycle')
    with pytest.raises(lite.LiteError):bench.correctness(dict(status='COMPLETED',stdout='{"cases":[true]}',exit_code=0),f)
