from dataclasses import replace
import hashlib
import json
from uuid import uuid4

import pytest

from governance_tools import solo_r2_future_scoring_consumer as c
from governance_tools import solo_r2_blind_scoring_bundle as b
from tests.test_solo_r2_regression_projection import SOURCE, MISSING, command, encode
from tests.test_solo_r2_regression_projection import read_versions, execute, change, SUBJECT
from tests.test_solo_r2_regression_projection import broken_histories


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def args():
    trace, trace_sha = encode([
        command(r'Get-Content -Raw -LiteralPath .\test_queue_range.py', SOURCE),
        command('python -m unittest -v', MISSING, 1)])
    base = json.dumps(dict(source='def f(): pass', final_response={'summary':'Unable to run tests.'},
        correctness={'oracle_status':'PASS','regression_status':'NOT_EVALUATED'}, cost={'tool_calls':2})).encode()
    item = c.ScoringInput(base, trace, digest(base), trace_sha)
    return dict(inputs_by_label={digest(b'a'):item,digest(b'b'):item},
        evaluation_id=str(uuid4()), pair_id='future-fixture', slot='R2-SHAKEDOWN',
        rubric_id='frozen-rubric', rubric_bytes=b'Assess only the evidence supplied.',
        expected_rubric_sha256=digest(b'Assess only the evidence supplied.'),
        presentation_entropy=bytes(range(32)))


def test_consumer_delivers_all_five_evidence_fields_without_metadata(args):
    delivery = c.prepare_scoring_delivery(**args)
    visible = json.loads(delivery.scorer_input_bytes)
    assert set(visible) == {'rubric','outputs'}
    packed = b.parse_blind_scoring_bundle(delivery.bundle_bytes)
    for row, stored in zip(visible['outputs'], packed['outputs']):
        assert row == dict(presentation_key=stored['presentation_key'], **json.loads(stored['output_payload']))
        evidence = row['regression_evidence']
        assert evidence['test_source'] == SOURCE
        assert evidence['executions'] == [dict(command='python -m unittest -v',
            execution_status='NOT_EXECUTED', exit_code=1, diagnostic=MISSING, version_binding='NOT_CONFIRMED')]
        assert row['correctness']['regression_status'] == 'NOT_EVALUATED'
        assert 'quality_total' not in row
    assert args['evaluation_id'].encode() not in delivery.scorer_input_bytes
    assert args['pair_id'].encode() not in delivery.scorer_input_bytes


@pytest.mark.parametrize('field', ['expected_trace_sha256','expected_payload_sha256'])
def test_bad_input_digest_rejected(args, field):
    label = next(iter(args['inputs_by_label']))
    args['inputs_by_label'][label] = replace(args['inputs_by_label'][label], **{field:'0'*64})
    with pytest.raises(b.BlindScoringBundleError): c.prepare_scoring_delivery(**args)


@pytest.mark.parametrize('leak', ['CONTROL', 'attempt_handle: '+ 'f'*64, r'D:\private\file'])
def test_bound_but_identity_leaking_trace_rejected(args, leak):
    trace, sha = encode([command('python -m unittest -v', leak, 1)])
    label = next(iter(args['inputs_by_label']))
    args['inputs_by_label'][label] = replace(args['inputs_by_label'][label], trace=trace, expected_trace_sha256=sha)
    with pytest.raises(b.BlindScoringBundleError): c.prepare_scoring_delivery(**args)


def test_wrong_rubric_digest_rejected(args):
    args['expected_rubric_sha256'] = '0'*64
    with pytest.raises(b.BlindScoringBundleError): c.prepare_scoring_delivery(**args)


def test_no_mapping_argument_or_scoring_execution_capability(args):
    with pytest.raises(TypeError): c.prepare_scoring_delivery(**args, mapping={})


def test_version_binding_survives_consumer_bundle_and_scorer_input(args):
    trace, sha = encode(read_versions()+execute('old')+change('queue_range.py')
                        +read_versions(subject=SUBJECT+'\n')+execute('new'))
    for label, item in args['inputs_by_label'].items():
        value = json.loads(item.payload)
        value['source'] = SUBJECT+'\n'
        raw = json.dumps(value).encode()
        args['inputs_by_label'][label] = c.ScoringInput(raw,trace,digest(raw),sha)
    delivered = c.prepare_scoring_delivery(**args)
    for row in json.loads(delivered.scorer_input_bytes)['outputs']:
        assert [x['version_binding'] for x in row['regression_evidence']['executions']] == [
            'EXECUTED_FOR_STALE_VERSION','EXECUTED_FOR_CURRENT_VERSION']
        assert row['correctness']['regression_status'] == 'NOT_EVALUATED'


@pytest.mark.parametrize('events', broken_histories())
def test_incomplete_or_compound_history_never_upgraded_by_consumer(args, events):
    trace, sha = encode(events)
    for label, item in args['inputs_by_label'].items():
        value = json.loads(item.payload)
        value['source'] = SUBJECT
        raw = json.dumps(value).encode()
        args['inputs_by_label'][label] = c.ScoringInput(raw,trace,digest(raw),sha)
    visible = json.loads(c.prepare_scoring_delivery(**args).scorer_input_bytes)
    for row in visible['outputs']:
        assert all(x['version_binding'] == 'NOT_CONFIRMED' for x in row['regression_evidence']['executions'])
