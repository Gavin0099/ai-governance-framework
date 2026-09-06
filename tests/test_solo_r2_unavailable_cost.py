"""Isolated ledger copies; no real append, runtime, key access or arm disclosure."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_disposable_binding as binding
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools import solo_r2_lifecycle_integration as lifecycle
from tests.test_solo_attempt_ledger_v2 import _genesis, _append_complete_pair

ROOT = Path(__file__).resolve().parents[1]
USAGE = dict(input_tokens=119407, cached_input_tokens=101248,
             cache_write_input_tokens=0, output_tokens=2422, reasoning_output_tokens=807)


@pytest.fixture
def case(tmp_path, monkeypatch, request):
    # Public metadata only; no historical trace, key, output or arm order is read.
    # Replay the exact adopted pre-terminal prefix, not the evolving ledger tail.
    # CostAmendmentAuthority.verify_prefix below pins these four original events.
    prefix = b''.join((ROOT / profile.LEDGER_PATH).read_bytes().splitlines(keepends=True)[:4])
    authority = ledger.CostAmendmentAuthority(
        (ROOT/profile.COST_AMENDMENT_PATH).read_bytes(),
        (ROOT/profile.COST_ADOPTION_PATH).read_bytes())
    authority.verify_prefix(prefix)
    root = tmp_path / 'isolated'
    path = root/profile.LEDGER_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(prefix)
    monkeypatch.setattr(profile, 'ROOT', root)
    events = ledger.read_ledger(path)
    assert len(events) == 4
    rows = [{'type':'thread.started'}, {'type':'turn.started'}]
    rows += [{'type':'item.started', 'item':{'id':str(n), 'type':
              'command_execution' if n < 6 else 'file_change'}} for n in range(7)]
    rows += [{'type':'turn.completed', 'usage':USAGE}]
    trace = ''.join(json.dumps(row)+'\n' for row in rows)
    private = tmp_path/'controller'
    output = private/events[3]['attempt_handle']
    output.mkdir(parents=True)
    monkeypatch.setattr(profile, 'COST_CONTROLLER_ROOT', private)
    if getattr(request, 'param', True):
        (output/'codex-trace.jsonl').write_bytes(trace.encode())
    event = dict(schema_version=profile.SCHEMA, event_seq=5, event_type='EXECUTION_TERMINAL',
                 event_id=str(uuid4()), timestamp_utc='2026-09-06T12:00:00Z',
                 pair_id=events[1]['pair_id'], slot='R2-SHAKEDOWN',
                 attempt_handle=events[3]['attempt_handle'], attempt_state='TERMINAL',
                 correctness_result=dict(oracle_status='NOT_RUN',required_case_count=10,
                    passed_case_count=0,regression_status='NOT_EVALUATED',scope_status='NOT_EVALUATED'),
                 cost_metrics={'elapsed_ms':'UNAVAILABLE','tool_calls':7},
                 cost_amendment_sha256=profile.COST_AMENDMENT_SHA256,
                 terminal_classification='HARNESS_FAILURE',
                 unavailable_cost_reasons={'elapsed_ms':ledger.MEASUREMENT_EXCEPTION})
    evidence = dict(ledger_prefix_sha256=hashlib.sha256(prefix).hexdigest(),
                    attempt_handle=event['attempt_handle'], classification='HARNESS_FAILURE',
                    exception_type='CatalogMismatch', trace_jsonl=trace,
                    observed_costs={'tool_calls':7}, measurement_failures=dict(event['unavailable_cost_reasons']),
                    token_components=dict(USAGE), aggregation_rule=None,
                    tokens_total_omission_reason='NO_ADOPTED_AGGREGATION_RULE')
    return SimpleNamespace(path=path,prefix=prefix,authority=authority,events=events,
                           event=event,evidence=evidence,root=root,private=private,output=output)


def append(c):
    ledger.validate_ledger_events([*ledger.read_ledger(c.path),c.event],cost_authority=c.authority)
    receipt=binding.persist_failure_cost_evidence(c.event,c.evidence,c.path.read_bytes())
    return ledger.append_event(c.path,c.event,cost_authority=c.authority,failure_evidence=receipt)


def test_valid_failure_appends_once_without_losing_count(case):
    before=ledger.validate_ledger_events(case.events)
    result=append(case)
    assert result.initiated_attempt_count == before.initiated_attempt_count == 1
    assert result.terminal_execution_count == 1
    assert case.path.read_bytes().startswith(case.prefix)
    assert ledger.validate_ledger_file(case.path,cost_authority=case.authority)==result
    assert 'tokens_total' not in ledger.read_ledger(case.path)[-1]['cost_metrics']
    with pytest.raises(ledger.LedgerError):
        append(case)
    assert len(ledger.read_ledger(case.path))==5


@pytest.mark.parametrize('mutation', [
    'v2','no_reason','unknown_reason','wrong_class','missing_tool','null','float','bool',
    'negative','wrong_digest','extra_key','reason_on_numeric','empty_reasons','wrong_pair'])
def test_invalid_public_representation_rejects(case,mutation):
    e=case.event
    if mutation=='v2': e['schema_version']=ledger.LEDGER_SCHEMA
    elif mutation=='no_reason': del e['unavailable_cost_reasons']
    elif mutation=='unknown_reason': e['unavailable_cost_reasons']['elapsed_ms']='UNKNOWN'
    elif mutation=='wrong_class': e['terminal_classification']='UNCLASSIFIED'
    elif mutation=='missing_tool': del e['cost_metrics']['tool_calls']
    elif mutation in ('null','float','bool','negative'):
        e['cost_metrics']['tool_calls']={'null':None,'float':7.0,'bool':True,'negative':-1}[mutation]
    elif mutation=='wrong_digest': e['cost_amendment_sha256']='0'*64
    elif mutation=='extra_key': e['reason']='exception'
    elif mutation=='reason_on_numeric': e['unavailable_cost_reasons']['tool_calls']=ledger.MEASUREMENT_EXCEPTION
    elif mutation=='empty_reasons': e['unavailable_cost_reasons']={}
    elif mutation=='wrong_pair': e['pair_id']=str(uuid4())
    with pytest.raises((ledger.LedgerError,binding.DisposableBindingError)):
        append(case)
    assert case.path.read_bytes()==case.prefix


@pytest.mark.parametrize('mutation', [
    'missing_evidence','wrong_count','hidden_known_elapsed','hidden_known_tool','lost_token_component',
    'wrong_prefix','wrong_handle','adopted_rule_without_total','invented_total','wrong_omission_reason'])
def test_controller_evidence_cannot_hide_available_observations(case,mutation):
    e,c=case.evidence,case.event['cost_metrics']
    if mutation=='missing_evidence': case.evidence=None
    elif mutation=='wrong_count': c['tool_calls']=8
    elif mutation=='hidden_known_elapsed': e['observed_costs']['elapsed_ms']=100
    elif mutation=='hidden_known_tool':
        c['tool_calls']='UNAVAILABLE'
        e['observed_costs'].pop('tool_calls')
        e['measurement_failures']['tool_calls']=ledger.MEASUREMENT_EXCEPTION
        case.event['unavailable_cost_reasons']['tool_calls']=ledger.MEASUREMENT_EXCEPTION
    elif mutation=='lost_token_component': del e['token_components']['cache_write_input_tokens']
    elif mutation=='wrong_prefix': e['ledger_prefix_sha256']='0'*64
    elif mutation=='wrong_handle': e['attempt_handle']='0'*64
    elif mutation=='adopted_rule_without_total': e['aggregation_rule']='purported-adopted-rule'
    elif mutation=='invented_total': c['tokens_total']=121829
    elif mutation=='wrong_omission_reason': e['tokens_total_omission_reason']='UNKNOWN'
    with pytest.raises((ledger.LedgerError,binding.DisposableBindingError)):
        append(case)
    assert case.path.read_bytes()==case.prefix


@pytest.mark.parametrize('case',[False],indirect=True)
def test_same_exception_class_can_lose_tool_measurement_instead(case):
    case.event['cost_metrics']={'elapsed_ms':19,'tool_calls':'UNAVAILABLE'}
    case.event['unavailable_cost_reasons']={'tool_calls':ledger.MEASUREMENT_EXCEPTION}
    case.evidence.update(trace_jsonl=None,token_components={},observed_costs={'elapsed_ms':19},
                         measurement_failures={'tool_calls':ledger.MEASUREMENT_EXCEPTION})
    assert append(case).terminal_execution_count==1


@pytest.mark.parametrize('kind',['missing','amendment','adoption','prefix','genesis','path'])
def test_authority_and_placement_are_not_caller_flags(case,kind):
    if kind=='missing': case.authority=None
    elif kind=='amendment':
        case.authority=ledger.CostAmendmentAuthority(b'changed',case.authority.adoption)
    elif kind=='adoption':
        case.authority=ledger.CostAmendmentAuthority(case.authority.amendment,b'changed')
    elif kind in ('prefix','genesis'):
        events=deepcopy(case.events)
        events[0 if kind=='genesis' else 3]['timestamp_utc']='2026-09-06T01:00:00Z'
        case.path.write_bytes(b''.join(ledger.encode_event(e) for e in events))
    elif kind=='path':
        path=case.path.parent/'wrong.ndjson'
        path.write_bytes(case.prefix)
        case.path=path
    before=case.path.read_bytes()
    with pytest.raises((ledger.LedgerError,binding.DisposableBindingError)):
        append(case)
    assert case.path.read_bytes()==before


def test_v2_numeric_semantics_unchanged():
    events=[_genesis()]
    _append_complete_pair(events,'R2-SHAKEDOWN','synthetic-pair',123)
    assert ledger.validate_ledger_events(events).terminal_execution_count==2
    event=next(e for e in events if e['event_type']=='EXECUTION_TERMINAL')
    event['cost_metrics']['elapsed_ms']='UNAVAILABLE'
    with pytest.raises(ledger.LedgerError): ledger.validate_ledger_events(events)


def test_numeric_v21_needs_no_supplemental_authority(case):
    event=case.event
    for key in ledger._COST_EXTENSION_KEYS: del event[key]
    event['cost_metrics']['elapsed_ms']=20
    assert ledger.append_event(case.path,event).terminal_execution_count==1


def test_unknown_metrics_and_omitted_aggregate_never_reduce_to_zero():
    assert binding.available_cost_total([{'elapsed_ms':'UNAVAILABLE'},{'elapsed_ms':3}], 'elapsed_ms')=='UNAVAILABLE'
    assert binding.available_cost_total([{}], 'tokens_total')=='UNAVAILABLE'
    assert binding.available_cost_total([{'tool_calls':7},{'tool_calls':2}], 'tool_calls')==9


def test_committed_loader_requires_exact_blobs(case,monkeypatch,tmp_path):
    monkeypatch.setattr(binding,'verify_repository_binding',lambda *a,**k:None)
    monkeypatch.setattr(binding,'_root',lambda repo:case.root)
    calls=[]
    def git(exe,repo,args,**kwargs):
        calls.append(args)
        ref=args[-1]
        assert ref.startswith(profile.COST_ADOPTION_COMMIT+':')
        if args[-2]=='-t': return b'blob\n'
        return (ROOT/ref.split(':',1)[1]).read_bytes()
    monkeypatch.setattr(binding,'_run_git',git)
    a=binding.load_cost_amendment_authority(git=None,repository=None,temp_root=tmp_path)
    assert a==case.authority and len(calls)==4
    monkeypatch.setattr(binding,'_run_git',lambda *a,**k:b'wrong')
    with pytest.raises(binding.DisposableBindingError):
        binding.load_cost_amendment_authority(git=None,repository=None,temp_root=tmp_path)


def test_lifecycle_retains_private_evidence_and_stops_without_scoring(case,tmp_path):
    class DisposableTestCoordinator(lifecycle.SyntheticLifecycleCoordinator):
        def _event_schema(self): return profile.SCHEMA
    private=case.private
    pair=case.events[1]
    c=DisposableTestCoordinator(lifecycle._START_TOKEN,ledger_path=case.path,
        controller_root=private,scoring_root=tmp_path/'scoring',key_path=tmp_path/'unused-key',
        custody_boundary=None,evaluation_id=case.events[0]['evaluation_id'],pair_id=pair['pair_id'],
        category=pair['category'],repository=pair['repository'],frozen_identities=pair['frozen_identities'],
        preflight_ids=['test'],rubric_id='test')
    result=c.record_harness_failure(case.event['attempt_handle'],cost_authority=case.authority,
        cost_metrics=case.event['cost_metrics'],unavailable_cost_reasons=case.event['unavailable_cost_reasons'],
        failure_evidence=case.evidence,correctness_result=case.event['correctness_result'])
    assert result.terminal_execution_count==1 and c._stopped and not c._terminal_outputs
    evidence=json.loads((case.output/'unavailable-cost.json').read_bytes())['observations']
    assert evidence['token_components']==USAGE
    with pytest.raises(lifecycle.LifecycleIntegrationError): c.admit_attempt()
    with pytest.raises(lifecycle.LifecycleIntegrationError): c.prepare_scoring()
    assert len(ledger.read_ledger(case.path))==5


def test_existing_trace_cannot_be_declared_absent(case):
    case.event['cost_metrics']={'elapsed_ms':19,'tool_calls':'UNAVAILABLE'}
    case.event['unavailable_cost_reasons']={'tool_calls':ledger.MEASUREMENT_EXCEPTION}
    case.evidence.update(trace_jsonl=None,token_components={},observed_costs={'elapsed_ms':19},
                         measurement_failures={'tool_calls':ledger.MEASUREMENT_EXCEPTION})
    with pytest.raises(binding.DisposableBindingError): append(case)
    assert case.path.read_bytes()==case.prefix


def test_direct_append_cannot_bypass_durable_controller_evidence(case):
    with pytest.raises(binding.DisposableBindingError):
        ledger.append_event(case.path,case.event,cost_authority=case.authority,failure_evidence=case.evidence)
    receipt=binding.RetainedFailureCostEvidence(case.event['attempt_handle'],'0'*64)
    with pytest.raises((binding.DisposableBindingError,OSError)):
        ledger.append_event(case.path,case.event,cost_authority=case.authority,failure_evidence=receipt)
    assert case.path.read_bytes()==case.prefix


@pytest.mark.parametrize('change',['trace','evidence','prefix'])
def test_evidence_or_source_drift_after_persistence_rejects(case,change):
    receipt=binding.persist_failure_cost_evidence(case.event,case.evidence,case.prefix)
    path={'trace':case.output/'codex-trace.jsonl', 'evidence':case.output/'unavailable-cost.json',
          'prefix':case.path}[change]
    path.write_bytes(path.read_bytes()+b'\n')
    before=case.path.read_bytes()
    with pytest.raises((binding.DisposableBindingError,ledger.LedgerError)):
        ledger.append_event(case.path,case.event,cost_authority=case.authority,failure_evidence=receipt)
    assert case.path.read_bytes()==before
