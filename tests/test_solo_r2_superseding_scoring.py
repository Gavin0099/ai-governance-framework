"""Isolated fixture custody only; never invoke real runtime/scorer or oracle."""
import json
from pathlib import Path
import pytest
from tests.test_solo_r2_scoring_continuation import saved, environment, identity
from governance_tools import solo_r2_superseding_scoring as s


@pytest.fixture
def setup(saved,monkeypatch):
    e=saved; e.run()
    monkeypatch.setattr(s,'EVALUATION',e.record['evaluation_id'])
    monkeypatch.setattr(s,'PAIR',e.record['pair_id'])
    monkeypatch.setattr(s,'TOKEN',e.live._pair_token())
    p=s._paths(e.root)
    monkeypatch.setattr(s,'HISTORY',tuple((n,len(p[n].read_bytes()),s._sha(p[n].read_bytes())) for n in ('ledger','old_bundle','old_checkpoint')))
    monkeypatch.setattr(s,'_policy',lambda *args:e.root)
    e.kw={**e.args,'verify_custody':lambda *args:None}
    e.generate=lambda:s.generate_candidate(**e.kw,verify_projection=lambda payloads:None)
    e.p=p
    e.before={n:p[n].read_bytes() for n,_,_ in s.HISTORY}
    return e


def activate(e):
    generated=e.generate()
    s._write(e.p['activation'],dict(decision='OWNER_ADOPTED_EXACT_TRANSITION',transition=generated))
    return {**e.kw,'expected_activation_sha256':s._sha(e.p['activation'].read_bytes())}


def score_bytes(e):
    value=s.bundle.parse_blind_scoring_bundle(e.p['bundle'].read_bytes())
    result={}
    for x in value['outputs']:
        p=json.loads(x['output_payload']);label=x['presentation_key']
        result[label]=s._canonical(dict(presentation_key=label,correctness=p['correctness'],cost=p['cost'],
            dimensions={n:dict(score='NOT_ASSESSABLE',evidence='Necessary evidence absent in supplied output') for n in
                ('causal_explanation','regression_safety','patch_focus','evidence_quality')},quality_total='NOT_ASSESSABLE'))
    return result


def test_full_detached_path_preserves_history(setup):
    e=setup; auth=activate(e)
    delivery=s.deliver(**auth,verify_fresh_scorer=lambda *a:None)
    value=s.bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)
    scores=score_bytes(e)
    frozen=s.freeze_scores(scores,**auth)
    permit=dict(decision='OWNER_AUTHORIZES_OPENING',activation=auth['expected_activation_sha256'],scores_sha256=frozen['sha256'])
    s._write(e.p['private']/'opening-authorization.json',permit)
    kwargs=dict(expected_scores_sha256=frozen['sha256'],expected_opening_authorization_sha256=s._sha(s._canonical(permit)))
    assert len(s.open_after_scores(**auth,**kwargs))==2
    for n,b in e.before.items(): assert e.p[n].read_bytes()==b
    with pytest.raises(Exception):s.open_after_scores(**auth,**kwargs)
    with pytest.raises(Exception):e.generate()
    with pytest.raises(Exception):s.deliver(**auth,verify_fresh_scorer=lambda *a:None)
    with pytest.raises(Exception):s.freeze_scores(scores,**auth)


@pytest.mark.parametrize('name',['ledger','old_bundle','old_checkpoint'])
def test_history_drift_rejects_before_reservation(setup,name):
    e=setup;e.p[name].write_bytes(e.p[name].read_bytes()+b' ')
    with pytest.raises(Exception):e.generate()
    assert not e.p['private'].exists()


@pytest.mark.parametrize('field',['terminal_output','runtime_evidence','verified_oracle','final_message'])
def test_source_drift_rejected(setup,field):
    e=setup;p=Path(e.record['terminal_outputs'][0][field]['path']);p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(Exception):e.generate()
    assert not e.p['private'].exists()


@pytest.mark.parametrize('field',['evaluation_id','pair_id'])
def test_wrong_instance_rejects(setup,field):
    e=setup;e.record[field]='wrong'
    with pytest.raises(Exception):e.generate()
    assert not e.p['private'].exists()


def test_unadopted_new_digest_rejected(setup):
    e=setup;e.generate()
    with pytest.raises(Exception):s.deliver(**e.kw,expected_activation_sha256='0'*64,verify_fresh_scorer=lambda *a:None)
    assert not (e.p['private']/'dispatch.json').exists()


@pytest.mark.parametrize('part',['bundle','checkpoint','activation','transition'])
def test_modified_activation_tuple_rejected(setup,part):
    e=setup;auth=activate(e);e.p[part].write_bytes(e.p[part].read_bytes()+b' ')
    with pytest.raises(Exception):s.deliver(**auth,verify_fresh_scorer=lambda *a:None)
    assert not (e.p['private']/'dispatch.json').exists()


@pytest.mark.parametrize('part',['bundle','checkpoint'])
def test_old_identity_rejected_even_if_new_activation_adopts_it(setup,part):
    e=setup;auth=activate(e)
    e.p[part].write_bytes(e.p['old_'+part].read_bytes())
    t=s._parse(e.p['transition'].read_bytes());t[part]=identity(e.p[part]);e.p['transition'].write_bytes(s._canonical(t))
    a=dict(decision='OWNER_ADOPTED_EXACT_TRANSITION',transition=identity(e.p['transition']));e.p['activation'].write_bytes(s._canonical(a))
    auth['expected_activation_sha256']=s._sha(e.p['activation'].read_bytes())
    with pytest.raises(Exception):s.deliver(**auth,verify_fresh_scorer=lambda *a:None)


def test_fresh_scorer_mandatory(setup):
    e=setup;auth=activate(e)
    with pytest.raises(Exception):s.deliver(**auth,verify_fresh_scorer=lambda *a:False)
    assert not (e.p['private']/'dispatch.json').exists()


def test_premature_opening_and_scores_before_dispatch_rejected(setup):
    e=setup;auth=activate(e)
    with pytest.raises(Exception):s.open_after_scores(**auth,expected_scores_sha256='0'*64,expected_opening_authorization_sha256='0'*64)
    with pytest.raises(Exception):s.freeze_scores({},**auth)
    assert not e.p['opening'].exists()


def test_missing_scores_and_tampered_frozen_scores(setup):
    e=setup;auth=activate(e);d=s.deliver(**auth,verify_fresh_scorer=lambda *a:None)
    labels=s.bundle.parse_blind_scoring_bundle(d.bundle_bytes)['presentation_order']
    with pytest.raises(Exception):s.freeze_scores({labels[0]:b'{}'},**auth)
    with pytest.raises(Exception):s.freeze_scores({l:b'{}' for l in labels},**auth)
    f=s.freeze_scores(score_bytes(e),**auth)
    (e.p['private']/(labels[0]+'.score.json')).write_bytes(b'changed')
    with pytest.raises(Exception):s.open_after_scores(**auth,expected_scores_sha256=f['sha256'],expected_opening_authorization_sha256='0'*64)
    assert not e.p['opening'].exists()


@pytest.mark.parametrize('failure',['reservation.json','scoring-bound.sealed.json','blind-scoring-bundle.json'])
def test_partial_failure_is_quarantined_no_retry(setup,monkeypatch,failure):
    e=setup;original=s._write
    def fail(path,value):
        original(path,value)
        if path.name==failure: raise OSError('fixture disk failure')
    monkeypatch.setattr(s,'_write',fail)
    with pytest.raises(Exception):e.generate()
    assert e.p['private'].exists() and not e.p['activation'].exists()
    with pytest.raises(Exception):e.generate()
    for n,b in e.before.items():assert e.p[n].read_bytes()==b


def test_semantic_projection_and_custody_checks_before_reservation(setup):
    e=setup
    with pytest.raises(Exception):s.generate_candidate(**e.kw,verify_projection=lambda *a:False)
    kw={**e.kw,'verify_custody':lambda *a:False}
    with pytest.raises(Exception):s.generate_candidate(**kw,verify_projection=lambda *a:None)
    assert not e.p['private'].exists()


def test_projection_removes_only_known_link_destination(setup):
    e=setup;row=e.record['terminal_outputs'][0];p=Path(row['final_message']['path'])
    prefix=str(s.inputs.profile.FINAL_RUNTIME_ROOT).replace('\\','/')+f'/materialization/{s.PAIR}-execution-0/'
    p.write_text(json.dumps({'summary':f'Changed [queue_range.py]({prefix}queue_range.py:5). Tests not run.'}))
    row['final_message']=identity(p)
    e.generate()
    b=e.p['bundle'].read_bytes()
    assert prefix.encode() not in b and b'Tests not run.' in b


def test_unhandled_leak_rejected_not_silently_removed(setup):
    e=setup;row=e.record['terminal_outputs'][0];p=Path(row['final_message']['path'])
    p.write_text(json.dumps({'summary':'See C:/unrelated/private/report.txt'}));row['final_message']=identity(p)
    with pytest.raises(Exception):e.generate()
    assert not e.p['private'].exists()


def test_no_mapping_input_capability(setup):
    with pytest.raises(TypeError):s.generate_candidate(**setup.kw,verify_projection=lambda *a:None,mapping={})


def test_new_label_collision_rejected(setup,monkeypatch):
    e=setup
    handle=e.record['terminal_outputs'][0]['attempt_handle']
    monkeypatch.setattr(s.randoms,'derive_opaque_identifier',lambda *a:handle)
    with pytest.raises(Exception):e.generate()
    assert e.p['private'].exists() and not e.p['checkpoint'].exists()


def test_nonce_reuse_rejected(setup,monkeypatch):
    e=setup
    package=s.crypto.SealedControllerPackage(e.p['old_checkpoint'].read_bytes(),s.HISTORY[2][2])
    monkeypatch.setattr(s.crypto,'seal_controller_state',lambda *a,**k:package)
    with pytest.raises(Exception):e.generate()
    assert e.p['private'].exists() and not e.p['checkpoint'].exists()


def test_wrong_score_label_and_opening_authority_rejected(setup):
    e=setup;auth=activate(e);s.deliver(**auth,verify_fresh_scorer=lambda *a:None)
    scores=score_bytes(e);wrong=dict(scores);wrong['0'*64]=wrong.pop(next(iter(wrong)))
    with pytest.raises(Exception):s.freeze_scores(wrong,**auth)
    frozen=s.freeze_scores(scores,**auth)
    s._write(e.p['private']/'opening-authorization.json',dict(decision='OWNER_AUTHORIZES_OPENING',activation='wrong',scores_sha256=frozen['sha256']))
    h=s._sha((e.p['private']/'opening-authorization.json').read_bytes())
    with pytest.raises(Exception):s.open_after_scores(**auth,expected_scores_sha256=frozen['sha256'],expected_opening_authorization_sha256=h)
    assert not e.p['opening'].exists()


def test_hardlinked_activation_rejected(setup):
    import os
    e=setup;auth=activate(e)
    os.link(e.p['activation'],e.p['private']/'activation-alias.json')
    with pytest.raises(Exception):s.deliver(**auth,verify_fresh_scorer=lambda *a:None)
    assert not (e.p['private']/'dispatch.json').exists()


def test_relative_custody_file_rejected(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);Path('record.json').write_bytes(b'{}')
    with pytest.raises(Exception):s._raw(Path('record.json'))
