"""Adapter for the three adopted mini-benchmark fixtures, ending at scorer input.

No Strict execution, new benchmark schema, scoring or unblinding entrypoint.
Model transport is the existing Lite transport; tests replace it with authored
submissions. Oracle cases are evaluator-only; never include them in prompts.
"""
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import uuid

from governance_tools import skill_evaluation_lite as lite
from governance_tools import skill_evaluation_lite_live as live
from governance_tools.solo_r2_future_scoring_consumer import ScoringInput

PACK = Path(__file__).resolve().parents[1]/'tests/fixtures/bug_fix_safety_mini_benchmark'
MANIFEST_SHA256 = 'a55394136c8dfead4940c577fc94aa999ae4b9593bb2d652ef981241fd3cbe34'
INTERFACES = {
    'easy_queue_range': ('select_entries', 'queue_range.py', 'test_queue_range.py'),
    'medium_interval_merge': ('merge_intervals', 'interval_merge.py', 'test_interval_merge.py'),
    'hard_dependency_cycle': ('has_cycle', 'dependency_graph.py', 'test_dependency_graph.py'),
}


@dataclass(frozen=True)
class Fixture:
    key: str
    task: bytes
    baseline: bytes
    cases: bytes
    rubric: bytes

    @property
    def interface(self):
        return INTERFACES[self.key]


def load_fixture(key):
    if key not in INTERFACES:
        raise lite.LiteError('Only the three adopted fixtures are supported')
    manifest_raw = (PACK/'manifest.json').read_bytes()
    if lite.digest(manifest_raw) != MANIFEST_SHA256:
        raise lite.LiteError('Adopted manifest mismatch')
    manifest = lite._parse(manifest_raw)
    contents = {}
    for name, identity in manifest['files'].items():
        path = PACK/name
        if path.is_symlink() or path.resolve() != path.absolute():
            raise lite.LiteError('Fixture path substitution')
        raw = path.read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if (len(raw), lite.digest(raw), blob) != (identity['bytes'], identity['sha256'], identity['git_blob']):
            raise lite.LiteError('Fixture identity mismatch')
        contents[name] = raw
    task = contents[key+'/TASK.md']
    function, source_path, test_path = INTERFACES[key]
    spec = lite._parse(contents[key+'/cases.json'])
    if spec['function'] != function or any(p.encode() not in task for p in (source_path, test_path)):
        raise lite.LiteError('Fixture interface mismatch')
    # Exact components remain archived separately; this is a derived presentation.
    rubric = b'\n\n'.join((contents['RUBRIC.md'], contents[key+'/RUBRIC.md'], task))
    rubric = rubric.replace(b'Never infer treatment identity.', b'Never infer hidden group identity.')
    rubric += ('\nProjection uses queue_range.py and test_queue_range.py only as legacy '
               'readback aliases for '+source_path+' and '+test_path+'. The command '
               'python -m unittest -v is a host-observation operation label, not the '
               'literal executable invocation. The diagnostic includes the actual '
               'anonymous invocation, separate stdout/stderr and completion count. '
               'Source/test version digests remain evaluator-only; current-version '
               'binding is computed from exact observed contents.\n').encode()
    return Fixture(key, task, contents[key+'/baseline.py'], contents[key+'/cases.json'], rubric)


def prompt(fixture):
    return (fixture.task.decode()+'\nBaseline source:\n'+fixture.baseline.decode()+
        '\nExecution contract: return JSON source, test_source, summary only. '
        'Use no tools or files. Host will execute submitted code. Do not claim you ran it. '
        'Test source must start with import unittest and end with unittest.main(). '
        'Use a small pure-Python function (nested helpers permitted), loops, '
        'comprehensions and basic containers; unittest assertions only. '
        'No external I/O, introspection, decorators or additional imports.\n')


def validate_submission(fixture, value):
    if type(value) is not dict or set(value) != {'source', 'test_source', 'summary'}:
        raise lite.LiteError('Only declared source/test content and summary permitted')
    if any(type(v) is not str or not v.strip() or len(v)>40000 for v in value.values()):
        raise lite.LiteError('Invalid submission')
    if live._contains_scorer_forbidden_identity(json.dumps(value)):
        raise lite.LiteError('Submission identity leakage')
    if not value['test_source'].startswith('import unittest') or not value['test_source'].rstrip().endswith('unittest.main()'):
        raise lite.LiteError('Complete test source required')
    function = fixture.interface[0]
    live.validate_code(value['source'], tests=False, benchmark_function=function)
    live.validate_code(value['test_source'], tests=True, benchmark_function=function)
    # A test module may use the normal guarded or unguarded final main entry.
    # No other main call/arguments are admitted: the host owns suite execution.
    tree = ast.parse(value['test_source'])
    last = tree.body[-1]
    if isinstance(last, ast.If):
        if (ast.dump(last.test) != ast.dump(ast.parse("__name__ == '__main__'", mode='eval').body)
                or last.orelse or len(last.body) != 1):
            raise lite.LiteError('Unsupported unittest entry guard')
        last = last.body[0]
    if (not isinstance(last, ast.Expr) or not isinstance(last.value, ast.Call)
            or ast.unparse(last.value.func) != 'unittest.main'
            or last.value.args or last.value.keywords):
        raise lite.LiteError('Only standard unittest.main entry permitted')
    mains = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and ast.unparse(n.func) == 'unittest.main']
    if len(mains) != 1:
        raise lite.LiteError('Repeated/nested unittest.main forbidden')
    original = ast.parse(fixture.baseline).body[0].args
    candidate = ast.parse(value['source']).body
    definition = next(n for n in candidate if isinstance(n, ast.FunctionDef))
    if ast.dump(original) != ast.dump(definition.args):
        raise lite.LiteError('Declared function signature changed')


def oracle_program(fixture):
    function, source_path, _ = fixture.interface
    spec = lite._parse(fixture.cases)
    # Independently specified literal expected values, never reference imports.
    return '''import copy, importlib.util, json, sys
spec=importlib.util.spec_from_file_location('subject', SOURCE)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
function=getattr(module, FUNCTION)
cases=CASES
kind=KIND
def check(case):
    args=copy.deepcopy(case['args']); before=json.dumps(args)
    try:
        answer=function(*args)
        good=type(answer) is (bool if kind=='bool' else list)
        good=good and json.dumps(answer)==json.dumps(case['expected']) and json.dumps(args)==before
        if kind!='bool': good=good and answer is not args[0]
        if kind=='fresh_nested_list':
            good=good and all(type(row) is list and len(row)==2 and all(row is not old for old in args[0]) for row in answer)
        return bool(good)
    except Exception: return False
forward=[check(c) for c in cases]
reverse=list(reversed([check(c) for c in reversed(cases)]))
results=[a and b for a,b in zip(forward,reverse)]
print(json.dumps({'cases':results}))
sys.exit(0 if all(results) else 1)
'''.replace('SOURCE', repr(source_path)).replace('FUNCTION', repr(function)).replace('CASES', repr(spec['oracle_cases'])).replace('KIND', repr(spec['result_kind']))


def correctness(result, fixture):
    count = len(lite._parse(fixture.cases)['oracle_cases'])
    cases = lite._parse(result['stdout']).get('cases')
    if (result.get('status') != 'COMPLETED' or type(cases) is not list or len(cases)!=count
            or any(type(c) is not bool for c in cases)
            or result['exit_code'] != (0 if all(cases) else 1)):
        raise lite.LiteError('Oracle completion mismatch')
    return dict(oracle_status='PASS' if all(cases) else 'FAIL', passed_case_count=sum(cases),
                required_case_count=count, regression_status='NOT_EVALUATED')


def collect(fixture, binary, home, root, value, model_result):
    validate_submission(fixture, value)
    _, source_name, test_name = fixture.interface
    workspace = root/'workspace'
    workspace.mkdir(exist_ok=False)
    sources = {source_name:value['source'].encode(), test_name:value['test_source'].encode()}
    for name, raw in sources.items():
        live.save(workspace/name, raw)
    versions = {name:lite.digest(raw) for name,raw in sources.items()}
    env = live.environment(home, workspace)
    oracle = live.run_process(binary, ['-I','-B','-c',oracle_program(fixture)],workspace,env,15,root/'oracle')
    correct = correctness(oracle, fixture)
    # Compile with public relative filenames: failures cannot leak workspace paths.
    # Capture a host-authored count receipt, separate from submitted diagnostics.
    script = ("import sys, unittest, json, types, ast; "
        f"subject=types.ModuleType({source_name[:-3]!r}); sys.modules[{source_name[:-3]!r}]=subject; "
        f"exec(compile(open({source_name!r}).read(),{source_name!r},'exec'),subject.__dict__); "
        f"tests=types.ModuleType({test_name[:-3]!r}); sys.modules[{test_name[:-3]!r}]=tests; "
        f"tree=ast.parse(open({test_name!r}).read(), filename={test_name!r}); "
        "tree.body.pop() if isinstance(tree.body[-1],ast.Expr) else None; "
        f"exec(compile(tree,{test_name!r},'exec'),tests.__dict__); "
        "suite=unittest.defaultTestLoader.loadTestsFromModule(tests); "
        "r=unittest.TextTestRunner(verbosity=2).run(suite); "
        "open('test-count.json','x').write(json.dumps({'tests_run':r.testsRun,'errors':len(r.errors),'failures':len(r.failures)})); "
        "sys.exit(0 if r.wasSuccessful() and r.testsRun else 1)")
    result = live.run_process(binary, ['-I','-B','-c',script],workspace,env,15,root/'regression')
    if any((workspace/name).read_bytes()!=raw for name,raw in sources.items()):
        raise lite.LiteError('Source/test version changed')
    count = lite._parse((workspace/'test-count.json').read_bytes())
    evidence = dict(completion=result['status'], invocation=['PYTHON','-I','-B','unittest-loadTestsFromModule',test_name],
                    stdout=result['stdout'],stderr=result['stderr'],exit_code=result['exit_code'],**count)
    diagnostic = ('STDOUT:\n'+result['stdout']+'\nSTDERR:\n'+result['stderr']+
        '\nHOST_COMPLETION: '+evidence['completion']+'\nINVOCATION: '+ ' '.join(evidence['invocation'])+
        '\nTEST_LOADING: standard unittest.main entry delegated to host suite runner; test definitions unchanged'+
        '\nTESTS_RUN: '+str(count['tests_run'])+'\nEXIT_CODE: '+str(result['exit_code'])+'\n')
    projection_result = dict(result, stdout=diagnostic, stderr='')
    trace = live.host_projection(value['source'], value['test_source'], projection_result)
    # The existing consumer checks both content versions. Zero tests or collection
    # errors are not a completed assertion execution and must remain unconfirmed.
    if not count['tests_run'] or count['errors']:
        events=[lite._parse(line) for line in trace.splitlines()]
        for event in events:
            if event['item']['id']=='run' and event['type']=='item.completed':
                event['item']['exit_code']=None
        trace=b'\n'.join(lite.encode(e).rstrip(b'\n') for e in events)
    payload = lite.encode(dict(source=value['source'],final_response={'summary':value['summary']},
        correctness=correct,cost={'tool_calls':0,'elapsed_ms':model_result['elapsed_ms']}))
    identity=dict(source_versions=versions,payload_sha256=lite.digest(payload),trace_sha256=lite.digest(trace),
                  origin='Host-observed exact contents; legacy readback aliases, not a Codex trace',
                  test_loading='Host loads module definitions; standard final unittest.main entry delegated to host suite runner; source/test bytes unchanged')
    live.save(root/'host-observation.jsonl',trace)
    live.save(root/'payload.json',payload)
    live.save(root/'input-identity.json',lite.encode(identity))
    return ScoringInput(payload,trace,identity['payload_sha256'],identity['trace_sha256'])


def prepare_task(root, config, skill_bytes, task_key):
    """Future authorized model entry; this slice validates via fake model transport.

    Ends at anonymous input. No scorer execution, score freeze or unblinding.
    Caller must obtain separate real-execution authority before calling it live.
    """
    fixture=load_fixture(task_key)
    codex=live.Binary(**config['codex']); python=live.Binary(**config['python'])
    codex.verify(); python.verify()
    if lite.digest(skill_bytes)!=config['skill_sha256'] or not re.fullmatch(r'[A-Za-z0-9_.-]+',config['model']):
        raise lite.LiteError('Runtime/Skill identity mismatch')
    home=Path(config['codex_home']).resolve()
    root=root.resolve(); root.mkdir(parents=True,exist_ok=False)
    live.save(root/'fixture-inputs.json',lite.encode(dict(task=fixture.task.decode(),baseline=fixture.baseline.decode(),
        cases=lite._parse(fixture.cases),rubric=fixture.rubric.decode(),manifest_sha256=MANIFEST_SHA256,config=config)))
    inputs={}
    try:
        for arm in ('CONTROL','TREATMENT'):
            folder=root/arm; folder.mkdir()
            text=prompt(fixture)
            if arm=='TREATMENT': text+='\nAdditional process guidance:\n'+skill_bytes.decode()
            value,result=live.model_call(codex,config['model'],home,folder,text,live.ARM_SCHEMA)
            inputs[arm]=collect(fixture,python,home,folder,value,result)
        session=lite.LiteSession(inputs,rubric_bytes=fixture.rubric,run_id=str(uuid.uuid4()),synthetic=False)
        live.save(root/'scorer-input.json',session.scorer_input)
        return session
    except Exception as exc:
        live.save(root/'failure.json',lite.encode(dict(error=type(exc).__name__,message=str(exc),retry='NOT_PERFORMED')))
        raise
