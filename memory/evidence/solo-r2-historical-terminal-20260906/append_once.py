"""One authorized historical closure; never launches or resumes an arm."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path('D:/ai-governance-framework')
sys.path.insert(0, str(ROOT))
from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_disposable_binding as binding
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools.solo_r2_codex_runner import derive_trace_metrics

OUT = Path(__file__).resolve().parent
EXPECTED_HEAD = '1880be0f19f10bbbf1a2b75d62dd259b587cef6e'
PREFIX_SHA = 'ee51b11bdaa746e6cb338ca6245029563de858653b5062bfeab9ca1c83faf0da'
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(['git', '--no-replace-objects', '-C', str(ROOT), *args])
def save(name, value):
    binding._write_once(OUT/name, (json.dumps(value, indent=2, sort_keys=True)+'\n').encode())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--append', action='store_true')
    args = parser.parse_args()
    assert git('rev-parse','HEAD').decode().strip() == EXPECTED_HEAD
    for review in ('solo-r2-unavailable-cost-implementation-20260906', 'solo-r2-unavailable-cost-r1-refresh-20260906'):
        record = json.loads((ROOT/'memory/evidence'/review/'review.json').read_bytes())
        for path, digest in record['reviewed_sha256'].items():
            assert sha((ROOT/path).read_bytes()) == digest == sha(git('show','HEAD:'+path))
    authority = ledger.CostAmendmentAuthority(*(git('show',profile.COST_ADOPTION_COMMIT+':'+p)
        for p in (profile.COST_AMENDMENT_PATH, profile.COST_ADOPTION_PATH)))
    path = ROOT/profile.LEDGER_PATH
    prefix = path.read_bytes()
    assert sha(prefix) == PREFIX_SHA
    authority.verify_prefix(prefix)
    events = ledger.read_ledger(path)
    assert len(events)==4 and events[-1]['event_type']=='TASK_EXPOSED'
    before = ledger.validate_ledger_file(path, cost_authority=authority)
    assert before.initiated_attempt_count==1 and before.terminal_execution_count==0
    handle = events[-1]['attempt_handle']
    trace_path, receipt_path = binding._cost_evidence_paths(handle)
    assert not receipt_path.exists(), 'Existing receipt: inspect; never blindly retry'
    raw = trace_path.read_bytes()
    metrics = derive_trace_metrics(raw)
    rows = [json.loads(line) for line in raw.splitlines()]
    usage = [r['usage'] for r in rows if r.get('type')=='turn.completed'][0]
    assert metrics.tool_call_count==7
    assert usage==dict(input_tokens=119407,cached_input_tokens=101248,cache_write_input_tokens=0,
                       output_tokens=2422,reasoning_output_tokens=807)
    assert set().union(*(r.keys() for r in rows)) <= {'item','thread_id','type','usage'}
    event = dict(schema_version=profile.SCHEMA,event_seq=5,event_type='EXECUTION_TERMINAL',
        event_id=str(uuid4()),timestamp_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        pair_id=events[1]['pair_id'],slot='R2-SHAKEDOWN',attempt_handle=handle,attempt_state='TERMINAL',
        correctness_result=dict(oracle_status='NOT_RUN',required_case_count=10,passed_case_count=0,
                                regression_status='NOT_EVALUATED',scope_status='NOT_EVALUATED'),
        cost_metrics=dict(elapsed_ms='UNAVAILABLE',tool_calls=7),
        cost_amendment_sha256=profile.COST_AMENDMENT_SHA256,terminal_classification='HARNESS_FAILURE',
        unavailable_cost_reasons=dict(elapsed_ms=ledger.MEASUREMENT_EXCEPTION))
    evidence = dict(ledger_prefix_sha256=PREFIX_SHA,attempt_handle=handle,classification='HARNESS_FAILURE',
        exception_type='RunnerGateError',trace_jsonl=raw.decode('utf-8'),observed_costs=dict(tool_calls=7),
        measurement_failures=event['unavailable_cost_reasons'],token_components=usage,aggregation_rule=None,
        tokens_total_omission_reason='NO_ADOPTED_AGGREGATION_RULE')
    ledger.validate_ledger_events(events+[event],cost_authority=authority)
    binding._validate_failure_cost_observations(event,evidence,prefix)
    binding._verify_retained_trace(handle,evidence)
    proposal = dict(owner_instruction='授權你做下去',interpretation='Authorization for previously proposed single historical terminal append only',
        implementation_head=EXPECTED_HEAD,evaluation_id=events[0]['evaluation_id'],prefix_sha256=PREFIX_SHA,
        genesis_sha256=sha(prefix.splitlines(keepends=True)[0]),event_content={k:v for k,v in event.items() if k not in ('event_id','timestamp_utc')},
        generated_fields='event_id generated once at append; timestamp is current append time, not execution end',
        trace_identity=dict(bytes=len(raw),sha256=sha(raw)),elapsed_basis='Adopted C05 and retained metadata: original monotonic timing lost after catalog exception',
        not_authorized=['retry','new Pair','Attempt 2','execution','scoring','push'])
    if not args.append:
        save('authorization-and-preflight.json',proposal)
        print('PREFLIGHT PASS; ledger remains 4 events; proposed event content retained; no trace contents disclosed')
        return
    assert json.loads((OUT/'authorization-and-preflight.json').read_bytes())==proposal
    assert path.read_bytes()==prefix
    receipt = binding.persist_failure_cost_evidence(event,evidence,prefix)
    # Exactly one call; exceptions are not retried. Inspect on uncertain writes.
    result = ledger.append_event(path,event,cost_authority=authority,failure_evidence=receipt)
    after = path.read_bytes()
    assert after==prefix+ledger.encode_event(event) and trace_path.read_bytes()==raw
    assert ledger.validate_ledger_file(path,cost_authority=authority)==result
    assert result.ledger_event_count==5 and result.initiated_attempt_count==1 and result.terminal_execution_count==1
    save('result.json',dict(mode='historical_terminal_append',mode_source='Owner-authorized append completed and verified',
        task_authority=proposal,scope='Single historical terminal only',done='Ledger fifth event verified; unchanged four-event prefix',
        claim_ceiling='Historical HARNESS_FAILURE closure only',not_claimed=['retry','output sealing','Skill correctness','A/B completion','push','commit'],
        evidence_refs=['authorization-and-preflight.json',str(profile.LEDGER_PATH)],
        before_sha256=PREFIX_SHA,after_sha256=sha(after),terminal_sha256=sha(ledger.encode_event(event)),
        controller_evidence_sha256=receipt.sha256,summary=asdict(result),risk='Elapsed unavailable; no correctness evaluation or retry authority',
        next_action='STOP; separately address catalog and post-exposure handler before any owner retry decision'))
    print('TERMINAL APPENDED AND VERIFIED; events=5; initiated=1; terminal=1; prefix preserved; STOP')

if __name__=='__main__': main()
