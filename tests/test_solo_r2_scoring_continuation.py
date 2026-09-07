"""Synthetic final custody only. Never invoke real continuation or a Codex arm."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from governance_tools import solo_r2_disposable_execution as subject
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_disposable_profile as profile
from tests.test_solo_r2_replacement_binding import replacement as replacement_fixture, environment, execution_setup, REPO


def identity(path):
    raw=path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def saved(environment, monkeypatch, tmp_path):
    env=replacement_fixture.__wrapped__(environment,monkeypatch,tmp_path,SimpleNamespace(param=True))
    s=execution_setup.__wrapped__(env,monkeypatch)
    live=s.execute()
    record=json.loads((REPO/subject.SCORING_ADOPTION_PATH).read_bytes())
    record['evaluation_id']=live._evaluation_id
    record['pair_id']=live._pair_id
    record['ledger_prefix']={**identity(s.public),'event_count':8}
    record['attempt_bound_checkpoint']=identity(live._checkpoint_path(controller.ATTEMPT_BOUND))
    local=env.root/'continuation-evidence';local.mkdir()
    def copy_identity(item,name,raw=None):
        path=local/name
        path.write_bytes(Path(item['path']).read_bytes() if raw is None else raw)
        return identity(path)
    record['input_authority']=copy_identity(record['input_authority'],'inputs.json')
    # Rubric value must remain the exact authority-relative path; copy to fixture root.
    rp=env.root/record['frozen_rubric']['path'];rp.parent.mkdir(parents=True,exist_ok=True)
    rp.write_bytes((REPO/record['frozen_rubric']['path']).read_bytes())
    for i,(handle,row) in enumerate(zip(live._terminal_outputs,record['terminal_outputs'])):
        d=live._controller_root/handle
        row['attempt_handle']=handle
        row['terminal_output']=identity(d/'queue_range.py')
        row['runtime_evidence']=identity(d/'runtime-evidence.json')
        for field in ['final_message','trace','initial_oracle_record','oracle_stdout','oracle_stderr']:
            raw=b'{"summary":"inclusive endpoints repaired"}' if field=='final_message' else b'fixture evidence'
            row[field]=copy_identity(row[field],str(i)+field,raw)
        oracle=dict(evaluation_id=live._evaluation_id,pair_id=live._pair_id,attempt_handle=handle,
            output_sha256=row['terminal_output']['sha256'],oracle_status='PASS',passed_case_count=10,required_case_count=10)
        row['verified_oracle']=copy_identity(row['verified_oracle'],str(i)+'oracle',json.dumps(oracle).encode())
    for field in ['oracle_correction_summary','oracle_initial_summary']:
        record[field]=copy_identity(record[field],field,b'{}')
    monkeypatch.setattr(subject,'load_scoring_continuation_authority',lambda **kw:record)
    monkeypatch.setattr(subject.binding,'load_final_ledger_binding',lambda **kw:s.args['replacement_binding'])
    env.record=record;env.live=live;env.saved_prefix=s.public.read_bytes()
    env.run=lambda:subject.prepare_final_scoring_continuation(**env.args)
    return env


def test_existing_builder_seals_once_after_exact_inputs(saved):
    e=saved
    delivery=e.run()
    bundle=subject.lifecycle.scoring_bundle.parse_blind_scoring_bundle(delivery.bundle_bytes)
    assert len(bundle['outputs'])==2
    assert e.public.read_bytes().startswith(e.saved_prefix)
    events=subject.ledger.read_ledger(e.public)
    assert len(events)==9 and events[-1]['event_type']=='CONTROLLER_STATE_SEALED'
    assert subject.ledger.validate_ledger_file(e.public).initiated_attempt_count==2
    assert e.live._checkpoint_path(controller.SCORING_BOUND).exists()
    with pytest.raises(Exception):e.run()
    assert len(subject.ledger.read_ledger(e.public))==9


@pytest.mark.parametrize('field',['ledger_prefix','attempt_bound_checkpoint','frozen_rubric','input_authority','oracle_correction_summary'])
def test_changed_adopted_artifact_rejected(saved,field):
    e=saved;p=Path(e.record[field]['path']);p=p if p.is_absolute() else e.root/p
    p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(Exception):e.run()
    assert not e.live._bundle_path().exists()


@pytest.mark.parametrize('field',['terminal_output','runtime_evidence','verified_oracle','final_message','oracle_stderr'])
def test_changed_arm_evidence_rejected(saved,field):
    e=saved;p=Path(e.record['terminal_outputs'][0][field]['path']);p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(Exception):e.run()
    assert e.public.read_bytes()==e.saved_prefix
    assert not e.live._bundle_path().exists()


@pytest.mark.parametrize('field',['evaluation_id','pair_id'])
def test_wrong_instance_rejected(saved,field):
    e=saved;e.record[field]='wrong'
    with pytest.raises(Exception):e.run()
    assert e.public.read_bytes()==e.saved_prefix


def test_mapping_argument_not_accepted(saved):
    with pytest.raises(TypeError):subject.prepare_final_scoring_continuation(**saved.args,mapping={'CONTROL':'x'})
    assert saved.public.read_bytes()==saved.saved_prefix


def test_identity_in_output_rejected_even_with_matching_digest(saved):
    e=saved;row=e.record['terminal_outputs'][0];p=Path(row['final_message']['path']);p.write_bytes(b'{"summary":"TREATMENT"}');row['final_message']=identity(p)
    with pytest.raises(Exception):e.run()
    assert e.public.read_bytes()==e.saved_prefix
    assert not e.live._bundle_path().exists()


def test_existing_checkpoint_rejected(saved):
    e=saved;e.live._checkpoint_path(controller.SCORING_BOUND).write_bytes(b'occupied')
    with pytest.raises(Exception):e.run()
    assert e.public.read_bytes()==e.saved_prefix


def test_invalid_persisted_bundle_cannot_append_sealing(saved,monkeypatch):
    e=saved;original=subject.lifecycle._write_create_once
    def corrupt(path,raw):
        original(path,raw)
        if path.name.endswith('blind-scoring-bundle.json'):path.write_bytes(b'{}')
    monkeypatch.setattr(subject.lifecycle,'_write_create_once',corrupt)
    with pytest.raises(Exception):e.run()
    assert e.public.read_bytes()==e.saved_prefix


def test_wrong_adoption_rejected_before_consumer(monkeypatch,tmp_path):
    monkeypatch.setattr(subject.binding,'_root',lambda r:tmp_path)
    monkeypatch.setattr(subject.material,'verify_repository_binding',lambda *a,**k:None)
    monkeypatch.setattr(subject.material,'_run_git',lambda *a,**k:b'{}')
    p=tmp_path/subject.SCORING_ADOPTION_PATH;p.parent.mkdir(parents=True);p.write_bytes(b'{}')
    with pytest.raises(Exception):subject.load_scoring_continuation_authority(git=None,repository=None,temp_root=tmp_path)


def test_nonterminal_ledger_even_with_updated_digest_rejected(saved):
    e=saved
    e.public.write_bytes(b"\n".join(e.saved_prefix.splitlines()[:-1])+b"\n")
    e.record['ledger_prefix']=identity(e.public)
    with pytest.raises(Exception):e.run()
    assert not e.live._bundle_path().exists()


def test_oracle_nonpass_even_with_updated_digest_rejected(saved):
    e=saved;row=e.record['terminal_outputs'][0];p=Path(row['verified_oracle']['path'])
    value=json.loads(p.read_bytes());value['oracle_status']='FAIL';p.write_text(json.dumps(value));row['verified_oracle']=identity(p)
    with pytest.raises(Exception):e.run()
    assert e.public.read_bytes()==e.saved_prefix


def test_scoring_label_collision_with_existing_handle_rejected(saved,monkeypatch):
    e=saved;handle=e.record['terminal_outputs'][0]['attempt_handle']
    monkeypatch.setattr(subject.lifecycle.random_domains,'derive_opaque_identifier',lambda *args:handle)
    with pytest.raises(Exception):e.run()
    assert e.public.read_bytes()==e.saved_prefix
    assert not e.live._bundle_path().exists()
