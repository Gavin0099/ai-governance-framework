from dataclasses import replace
import json

import pytest

from governance_tools import skill_evaluation_lite as lite
from governance_tools.solo_r2_blind_scoring_bundle import BlindScoringBundleError
from tests.test_solo_r2_regression_projection import read_versions, execute, encode, SUBJECT


def test_cli_complete_synthetic_flow(tmp_path, capsys):
    root = tmp_path/'new'
    assert lite.main(['--synthetic','--output',str(root),'--authorize-synthetic-unblinding']) == 0
    report = json.loads((root/'report.json').read_bytes())
    frozen = (root/'scores-frozen.json').read_bytes()
    assert report['result'] == 'LITE_SYNTHETIC_END_TO_END_WIRING_VALIDATED'
    assert report['freeze_sha256'] == lite.digest(frozen)
    assert report['claim_ceiling'] == list(lite.CLAIMS)
    assert report['not_claimed'] == list(lite.NOT_CLAIMED)
    assert report['quality_comparison'] == 'NOT_DETERMINED'
    for arm in report['arms'].values():
        assert arm['quality']['regression_safety']['score'] == lite.NA
        assert arm['quality_total'] == lite.NA
        assert arm['oracle']['passed_case_count'] == 10
    visible = (root/'scorer-input.json').read_text()
    assert 'CONTROL' not in visible and 'TREATMENT' not in visible
    assert 'synthetic-lite-only' not in visible
    assert 'LITE_SYNTHETIC_END_TO_END_WIRING_VALIDATED' in capsys.readouterr().out


def test_unblinding_requires_freeze_and_exact_authorization():
    session = lite.SyntheticLite(lite.synthetic_inputs())
    with pytest.raises(lite.LiteError, match='Freeze both'):
        session.unblind(authorized_freeze_sha256='0'*64)
    frozen = session.freeze(lite.synthetic_scorer(session.scorer_input))
    with pytest.raises(lite.LiteError, match='Exact freeze'):
        session.unblind(authorized_freeze_sha256='0'*64)
    session.unblind(authorized_freeze_sha256=lite.digest(frozen))
    assert session.frozen_scores == frozen
    with pytest.raises(lite.LiteError):
        session.unblind(authorized_freeze_sha256=lite.digest(frozen))
    with pytest.raises(lite.LiteError, match='Already frozen'):
        session.freeze(lite.synthetic_scorer(session.scorer_input))


@pytest.mark.parametrize('leak',['CONTROL','attempt_handle: '+'a'*64,r'D:\private\workspace'])
def test_input_identity_leakage_rejected(leak):
    inputs = lite.synthetic_inputs()
    item = inputs['CONTROL']
    value = json.loads(item.payload)
    value['final_response']['summary'] = leak
    raw = lite.encode(value)
    inputs['CONTROL'] = replace(item,payload=raw,expected_payload_sha256=lite.digest(raw))
    with pytest.raises((BlindScoringBundleError,lite.LiteError)):
        lite.SyntheticLite(inputs)


@pytest.mark.parametrize('mutation',['oracle','mapping','missing_arm','bool','out_of_range','empty_evidence','leak','regression_upgrade'])
def test_scorer_cannot_invert_oracle_or_invent_evidence(mutation):
    session = lite.SyntheticLite(lite.synthetic_inputs())
    response = json.loads(lite.synthetic_scorer(session.scorer_input))
    key = next(iter(response['scores']))
    rating = response['scores'][key]['causal_explanation']
    if mutation == 'oracle': response['correctness'] = {'oracle_status':'FAIL'}
    if mutation == 'mapping': response['mapping'] = {key:'CONTROL'}
    if mutation == 'missing_arm': del response['scores'][key]
    if mutation == 'bool': rating['score'] = True
    if mutation == 'out_of_range': rating['score'] = 3
    if mutation == 'empty_evidence': rating['evidence'] = ' '
    if mutation == 'leak': rating['evidence'] = 'TREATMENT'
    if mutation == 'regression_upgrade': response['scores'][key]['regression_safety']['score'] = 2
    with pytest.raises(lite.LiteError): session.freeze(lite.encode(response))
    with pytest.raises(lite.LiteError,match='not frozen'): _ = session.frozen_scores


def test_current_version_fixture_can_carry_numeric_regression_score():
    inputs = lite.synthetic_inputs()
    trace,sha = encode(read_versions()+execute('run'))
    for arm,item in inputs.items():
        payload = json.loads(item.payload);payload['source'] = SUBJECT
        raw = lite.encode(payload)
        inputs[arm] = replace(item,payload=raw,expected_payload_sha256=lite.digest(raw),trace=trace,expected_trace_sha256=sha)
    session = lite.SyntheticLite(inputs)
    frozen = session.freeze(lite.synthetic_scorer(session.scorer_input))
    report = json.loads(session.unblind(authorized_freeze_sha256=lite.digest(frozen)))
    assert all(arm['quality_total'] == 8 for arm in report['arms'].values())
    assert report['quality_comparison'] == 'EQUAL'
    assert report['synthetic'] is True


def test_missing_summary_does_not_become_numeric_quality():
    inputs = lite.synthetic_inputs()
    for arm,item in inputs.items():
        payload=json.loads(item.payload);payload['final_response']={}
        raw=lite.encode(payload)
        inputs[arm]=replace(item,payload=raw,expected_payload_sha256=lite.digest(raw))
    session=lite.SyntheticLite(inputs)
    scores=json.loads(session.freeze(lite.synthetic_scorer(session.scorer_input)))['scores']
    assert all(s['causal_explanation']['score']==lite.NA and s['evidence_quality']['score']==lite.NA for s in scores.values())


def test_cli_freeze_only_and_no_overwrite(tmp_path):
    root=tmp_path/'once'
    lite.main(['--synthetic','--output',str(root)])
    before=(root/'scores-frozen.json').read_bytes()
    assert not (root/'report.json').exists()
    with pytest.raises(FileExistsError):
        lite.main(['--synthetic','--output',str(root),'--authorize-synthetic-unblinding'])
    assert (root/'scores-frozen.json').read_bytes()==before


def test_duplicate_json_and_real_mode_rejected(tmp_path):
    session=lite.SyntheticLite(lite.synthetic_inputs())
    with pytest.raises(lite.LiteError):session.freeze(b'{"scores":{},"scores":{}}')
    with pytest.raises(SystemExit):lite.main(['--output',str(tmp_path/'real')])
    assert not (tmp_path/'real').exists()
