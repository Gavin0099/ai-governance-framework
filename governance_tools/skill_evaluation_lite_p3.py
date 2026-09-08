"""Opt-in P3 host observation and score constraints; no Strict changes.

Host-authored receipts are trusted evaluator inputs, not OS-attested evidence.
Models never supply attribution flags. Digests bind receipts to the two contents
and scoring input; they do not establish honesty of an arbitrary external host.
"""
from dataclasses import dataclass
from pathlib import Path

from governance_tools import skill_evaluation_lite as lite
from governance_tools import skill_evaluation_lite_live as live
from governance_tools.solo_r2_future_scoring_consumer import ScoringInput


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = 'docs/governance/p3-regression-safety-rubric-amendment-candidate-20260908.md'
ADOPTION = 'memory/evidence/p3-regression-rubric-adoption-20260908/owner-adoption.json'
POLICY_SHA = '9ffa3492be26c822c53b53ecc5b7fbd3dce8782ed473b838806378954153bfc5'
ADOPTION_SHA = 'b22c83005f9050105a523ad362aca18d78397a692c244ddae699980bde61b1c8'
CONTRACT = 'explicit-subject-import-v1'


def policy_text():
    raw = (ROOT / AMENDMENT).read_bytes()
    adopted = (ROOT / ADOPTION).read_bytes()
    if lite.digest(raw) != POLICY_SHA or lite.digest(adopted) != ADOPTION_SHA:
        raise lite.LiteError('P3 adopted authority mismatch')
    text = raw.decode().replace('\r\n', '\n')
    # Verbatim adopted normative and attribution sections, no host paths/IDs.
    return text.split('## Proposed normative delta (prospective only)\n', 1)[1].split(
        '## Unchanged scoring and historical boundary', 1)[0]


@dataclass(frozen=True)
class P3Input:
    scoring: ScoringInput
    observation: bytes
    expected_observation_sha256: str


# Only fixed, admitted submissions are executed; the existing AST boundary stays
# in the caller. Syntax-invalid submissions are compiled only, never executed.
HOST = r'''
import ast, hashlib, json, sys, types, unittest
SOURCE, TEST, SYNTAX_ONLY = CONFIG
raw = {p: open(p, 'rb').read() for p in (SOURCE, TEST)}
versions = {p: hashlib.sha256(b).hexdigest() for p,b in raw.items()}
subject = types.ModuleType(SOURCE[:-3]); tests = types.ModuleType(TEST[:-3])
details = []
phase = 'COMPILE'
def detail(exc, kind):
    typ, value, tb = exc
    origin = 'HOST'; line = 0
    while tb:
        frame = tb.tb_frame
        origin = ('SUBJECT' if frame.f_globals is subject.__dict__ else
                  'TEST' if frame.f_globals is tests.__dict__ else
                  'HOST' if frame.f_globals is globals() else 'EXTERNAL')
        line = tb.tb_lineno
        tb = tb.tb_next
    if typ is SyntaxError and value.filename in (SOURCE, TEST) and phase == 'COMPILE':
        origin = 'SUBJECT' if value.filename == SOURCE else 'TEST'
        line = value.lineno
    details.append(dict(kind=kind, exception=typ.__name__, origin=origin,
                        line=line, name=getattr(value, 'name', None), phase=phase))
class Result(unittest.TextTestResult):
    def addError(self, test, err):
        detail(err, 'ERROR'); super().addError(test, err)
    def addFailure(self, test, err):
        detail(err, 'ASSERTION'); super().addFailure(test, err)
    def addSubTest(self, test, subtest, err):
        if err is not None:
            detail(err, 'ASSERTION' if issubclass(err[0], test.failureException) else 'ERROR')
        super().addSubTest(test, subtest, err)
count = dict(tests_run=0, errors=0, failures=0)
code = 1
try:
    subject_code = compile(raw[SOURCE], SOURCE, 'exec')
    tree = ast.parse(raw[TEST], filename=TEST)
    if SYNTAX_ONLY:
        raise RuntimeError('Expected syntax failure was not reproduced')
    phase = 'LOAD_SUBJECT'
    sys.modules[SOURCE[:-3]] = subject
    exec(subject_code, subject.__dict__)
    phase = 'LOAD_TEST'
    sys.modules[TEST[:-3]] = tests
    if isinstance(tree.body[-1], ast.Expr): tree.body.pop()
    exec(compile(tree, TEST, 'exec'), tests.__dict__)
    phase = 'LOAD_SUITE'
    suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
    phase = 'RUN_TESTS'
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    count = dict(tests_run=result.testsRun, errors=len(result.errors), failures=len(result.failures))
    code = 0 if result.wasSuccessful() and result.testsRun else 1
except BaseException:
    detail(sys.exc_info(), 'COLLECTION')
    print(type(sys.exc_info()[1]).__name__ + ': submitted unit could not be loaded', file=sys.stderr)
after = {p: hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in raw}
print(json.dumps(dict(versions=versions, after=after, count=count, details=details, phase=phase)))
sys.exit(code)
'''


def observe(binary, home, root, sources, *, syntax_only=False):
    """Run one fixed Python command; timeout/launch receipts remain available.

    Caller has already validated AST or established compile-only syntax failure.
    No retry, shell, PATH fallback, model, or new execution framework.
    """
    source_name, test_name = sources
    script = HOST.replace('CONFIG', repr((source_name, test_name, syntax_only)), 1)
    try:
        result = live.run_process(binary, ['-I', '-B', '-c', script], root/'workspace',
            live.environment(home, root/'workspace'), 15, root/'regression')
    except lite.LiteError:
        path = root/'regression.result.json'
        if not path.exists():
            raise
        result = lite._parse(path.read_bytes())
        if result.get('status') not in ('TIMEOUT', 'LAUNCH_FAILED'):
            raise
    try:
        receipt = lite._parse(result.get('stdout', ''))
    except lite.LiteError:
        receipt = None
    return dict(contract=CONTRACT, result=result, receipt=receipt,
                source_names=list(sources))


def bind(scoring, observed):
    value = dict(observed, payload_sha256=scoring.expected_payload_sha256,
                 trace_sha256=scoring.expected_trace_sha256)
    raw = lite.encode(value)
    return P3Input(scoring, raw, lite.digest(raw))


def collect(fixture, binary, home, root, value, model_result):
    """Prospective host collection; syntax-invalid content is compiled only."""
    from governance_tools import skill_evaluation_lite_benchmark as bench
    policy_text()
    syntax_only = False
    try:
        bench.validate_submission(fixture, value)
    except lite.LiteError as exc:
        if not isinstance(exc.__cause__, SyntaxError):
            raise
        # validate_submission checked the closed payload, public content and
        # complete test boundaries before parsing. Neither unit is executed.
        syntax_only = True
    _, source, test = fixture.interface
    workspace = root/'workspace'
    workspace.mkdir(exist_ok=False)
    for name, content in ((source, value['source']), (test, value['test_source'])):
        live.save(workspace/name, content.encode())
    if syntax_only:
        correct = dict(oracle_status='NOT_RUN', passed_case_count=0,
                       required_case_count=len(lite._parse(fixture.cases)['oracle_cases']),
                       regression_status='NOT_EVALUATED')
    else:
        oracle = live.run_process(binary, ['-I', '-B', '-c', bench.oracle_program(fixture)],
            workspace, live.environment(home, workspace), 15, root/'oracle')
        correct = bench.correctness(oracle, fixture)
    observed = observe(binary, home, root, (source, test), syntax_only=syntax_only)
    result = observed['result']
    # Internal receipt digests are never copied to the anonymous diagnostic.
    trace_result = dict(result, stdout='', stderr=result.get('stderr', ''),
                        exit_code=result.get('exit_code'))
    trace = live.host_projection(value['source'], value['test_source'], trace_result)
    payload = lite.encode(dict(source=value['source'], final_response={'summary':value['summary']},
        correctness=correct, cost={'tool_calls':0, 'elapsed_ms':model_result['elapsed_ms']}))
    scoring = ScoringInput(payload, trace, lite.digest(payload), lite.digest(trace))
    item = bind(scoring, observed)
    live.save(root/'host-observation.jsonl', trace)
    live.save(root/'payload.json', payload)
    live.save(root/'p3-observation.json', item.observation)
    live.save(root/'input-identity.json', lite.encode(dict(payload_sha256=lite.digest(payload),
        trace_sha256=lite.digest(trace), observation_sha256=item.expected_observation_sha256,
        policy_sha256=POLICY_SHA, contract=CONTRACT)))
    return item


def project(item, row):
    """Derive assessment from a host receipt, never a submitted attribution flag."""
    if type(item) is not P3Input or lite.digest(item.observation) != item.expected_observation_sha256:
        raise lite.LiteError('P3 observation identity mismatch')
    value = lite._parse(item.observation)
    if set(value) != {'contract', 'result', 'receipt', 'source_names', 'payload_sha256', 'trace_sha256'}:
        raise lite.LiteError('P3 observation fields mismatch')
    if (value['contract'] != CONTRACT or value['payload_sha256'] != lite.digest(item.scoring.payload)
            or value['trace_sha256'] != lite.digest(item.scoring.trace)):
        raise lite.LiteError('P3 input binding mismatch')
    names = value['source_names']
    from governance_tools.skill_evaluation_lite_benchmark import INTERFACES
    if type(names) is not list or tuple(names) not in [i[1:] for i in INTERFACES.values()]:
        raise lite.LiteError('P3 source names mismatch')
    current = dict(zip(names, [lite.digest(row['source'].encode()),
        lite.digest((row['regression_evidence']['test_source'] or '').encode())]))
    result, receipt = value['result'], value['receipt']
    state = dict(version_identity='NOT_CONFIRMED', execution_status='UNKNOWN',
                 attribution='UNKNOWN', required_regression_score=lite.NA,
                 test_count=None, exit_code=None, failure_locations=[],
                 diagnostic='Completion evidence unavailable.')
    if type(result) is not dict:
        raise lite.LiteError('P3 result malformed')
    if result.get('status') != 'COMPLETED':
        return state
    code = result.get('exit_code')
    if type(code) is not int or type(receipt) is not dict:
        return state
    if set(receipt) != {'versions', 'after', 'count', 'details', 'phase'}:
        raise lite.LiteError('P3 receipt malformed')
    state.update(execution_status='ERROR' if code else 'COMPLETED', exit_code=code,
                 diagnostic=result.get('stderr', ''))
    if receipt['versions'] != current or receipt['after'] != current:
        return state
    state['version_identity'] = 'CONFIRMED'
    count, details = receipt['count'], receipt['details']
    if (type(count) is not dict or set(count) != {'tests_run', 'errors', 'failures'}
            or any(type(v) is not int or v < 0 for v in count.values()) or type(details) is not list):
        raise lite.LiteError('P3 test evidence malformed')
    state['test_count'] = count
    if receipt['phase'] not in ('COMPILE', 'LOAD_SUBJECT', 'LOAD_TEST', 'LOAD_SUITE', 'RUN_TESTS'):
        raise lite.LiteError('P3 phase malformed')
    collection = (len(details) == 1 and type(details[0]) is dict
                  and details[0].get('kind') == 'COLLECTION')
    if collection:
        if any(count.values()):
            raise lite.LiteError('P3 interrupted run cannot claim completed counts')
    elif receipt['phase'] == 'RUN_TESTS':
        if count['errors'] + count['failures'] != len(details):
            raise lite.LiteError('P3 count/detail mismatch')
    elif any(count.values()) or len(details) != 1:
        raise lite.LiteError('P3 collection receipt mismatch')
    caused = []
    for detail in details:
        if (type(detail) is not dict or set(detail) != {'kind', 'exception', 'origin', 'line', 'name', 'phase'}
                or type(detail['line']) is not int):
            raise lite.LiteError('P3 error evidence malformed')
        origin = detail['origin'] in ('SUBJECT', 'TEST')
        if detail['phase'] != receipt['phase']:
            raise lite.LiteError('P3 detail phase mismatch')
        syntax = (detail['kind'] == 'COLLECTION' and detail['exception'] == 'SyntaxError'
                  and detail['phase'] == 'COMPILE')
        missing = (detail['exception'] == 'NameError' and type(detail['name']) is str
                   and bool(detail['name']) and detail['phase'] in ('LOAD_SUBJECT', 'LOAD_TEST', 'RUN_TESTS'))
        assertion = (detail['kind'] == 'ASSERTION' and detail['exception'] == 'AssertionError'
                     and detail['phase'] == 'RUN_TESTS' and count['failures'] > 0
                     and detail['origin'] in ('TEST', 'EXTERNAL'))
        # Assertions originate inside unittest; their test was admitted/executed.
        caused.append((origin and detail['line'] > 0 and (syntax or missing)) or assertion)
    state['failure_locations'] = details
    if code == 0:
        if details or count['errors'] or count['failures'] or receipt['phase'] != 'RUN_TESTS':
            raise lite.LiteError('P3 success contradicts error evidence')
        if count['tests_run'] > 0:
            state.update(attribution='NONE', required_regression_score=None)
    elif code == 1 and details and all(caused):
        state.update(attribution='SUBMISSION_CAUSED', required_regression_score=0)
    elif details and all(d['origin'] == 'HOST' for d in details):
        state['attribution'] = 'HARNESS_OR_ENVIRONMENT'
    return state


def prepare_delivery(inputs_by_label, **kwargs):
    from governance_tools.solo_r2_future_scoring_consumer import prepare_scoring_delivery, ScoringDelivery
    from governance_tools import solo_r2_blind_scoring_bundle as blind
    if any(type(i) is not P3Input for i in inputs_by_label.values()):
        raise lite.LiteError('Both P3 inputs required; no mixed scoring policies')
    if lite.digest(kwargs['rubric_bytes']) != kwargs['expected_rubric_sha256']:
        raise lite.LiteError('P3 base rubric mismatch')
    rubric = kwargs['rubric_bytes'] + (
        '\nProspective adopted P3 exception supersedes only the preceding pre-assertion/zero-test rule.\n'
        + policy_text()).encode()
    kwargs = dict(kwargs, rubric_bytes=rubric, expected_rubric_sha256=lite.digest(rubric))
    delivery = prepare_scoring_delivery(inputs_by_label={k:i.scoring for k,i in inputs_by_label.items()}, **kwargs)
    visible = lite._parse(delivery.scorer_input_bytes)
    outputs = {}
    for row in visible['outputs']:
        key = row['presentation_key']
        row['regression_assessment'] = project(inputs_by_label[key], row)
        row['regression_execution_contract'] = (
            'Tests must explicitly import the declared function from the submitted subject module. '
            'The host does not inject subject symbols into tests. Both submitted units must be '
            'independently loadable. The host compiles both units before execution and delegates '
            'the standard unittest.main entry to loadTestsFromModule. regression_assessment '
            'records the prospective host version/outcome/attribution; legacy_projection_only '
            'marks the retained earlier event projection, not an override of that assessment. '
            'A successful receipt does not prove required coverage; apply the frozen rubric '
            'to the actual assertions for the unchanged 0/1/2 distinction.')
        # P3 observation is authoritative for version/outcome; legacy event
        # projection remains separately labeled and unmodified, not conflated.
        row['regression_evidence']['legacy_projection_only'] = True
        payload = {k:v for k,v in row.items() if k != 'presentation_key'}
        if blind._contains_scorer_forbidden_identity(lite.encode(payload).decode()):
            raise lite.LiteError('P3 scorer identity leakage')
        outputs[key] = lite.encode(payload).decode()
    bundle = blind.build_blind_scoring_bundle(evaluation_id=kwargs['evaluation_id'],
        pair_id=kwargs['pair_id'], slot=kwargs['slot'], rubric_id=kwargs['rubric_id'],
        outputs_by_label=outputs, presentation_entropy=kwargs['presentation_entropy'])
    return ScoringDelivery(blind.encode_blind_scoring_bundle(bundle), lite.encode(visible))
