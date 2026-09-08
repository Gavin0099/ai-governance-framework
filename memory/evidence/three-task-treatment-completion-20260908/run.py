"""One owner-authorized delivery of three frozen tasks. No retries or repairs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time
import uuid

REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO))
HEAD='983d5fad7a4a28047b175adcddf904587a55a008'
BASE=Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args])


def sha(raw): return hashlib.sha256(raw).hexdigest()


bound_paths=[
    'governance_tools/skill_evaluation_lite_benchmark.py',
    'governance_tools/skill_evaluation_lite_live.py',
    'governance_tools/skill_evaluation_lite.py',
    'governance_tools/solo_r2_regression_projection.py',
    'governance_tools/solo_r2_future_scoring_consumer.py',
    'governance_tools/solo_r2_blind_scoring_bundle.py',
]
snapshots={p:git('show',HEAD+':'+p) for p in bound_paths}


def unchanged():
    if git('rev-parse','HEAD').decode().strip()!=HEAD:
        raise RuntimeError('HEAD changed; no further execution')
    for p,raw in snapshots.items():
        if (REPO/p).read_bytes()!=raw:
            raise RuntimeError('Bound source changed; no further execution')


unchanged()
from governance_tools import skill_evaluation_lite_benchmark as bench
from governance_tools import skill_evaluation_lite_live as live
from governance_tools import skill_evaluation_lite as lite

prior='memory/evidence/p2-lite-parser-20260908/live/inputs.json'
raw=(REPO/prior).read_bytes()
if raw!=git('show',HEAD+':'+prior): raise RuntimeError('Prior input identity mismatch')
inputs=lite._parse(raw); config=inputs['config']; skill=inputs['skill'].encode()
if sha(skill)!=config['skill_sha256']:raise RuntimeError('Frozen Skill mismatch')
codex=live.Binary(**config['codex']); python=live.Binary(**config['python'])
codex.verify();python.verify()
tasks=tuple(bench.INTERFACES)
frozen={key:bench.load_fixture(key) for key in tasks}
if any((BASE/key).exists() for key in tasks):raise RuntimeError('Existing task; replay forbidden')
live.save(BASE/'authorization.json',lite.encode(dict(
    owner_scope='Preserved first-run CONTROL recollection only; exactly one fresh TREATMENT and one fresh scorer per task; durable freeze then unblind authorized; no CONTROL model, repair, retry, commit or push',
    head=HEAD,config=config,skill_sha256=sha(skill),prior_input_sha256=sha(raw),
    bound_sources={p:sha(b) for p,b in snapshots.items()},manifest_sha256=bench.MANIFEST_SHA256,
    tasks=tasks,model_timeout_seconds=600,host_command_timeout_seconds=15,
    human_intervention_definition='Manual execution/data/config intervention after authorization; monitoring and native approval UI are reported separately',
    claim_ceiling=lite.CLAIMS)))
live.save(BASE/'skill-packet.md',skill)


def evidence(folder):
    record={}
    for who in ('CONTROL','TREATMENT','scorer'):
        root=folder/who
        entry={}
        for name in ('model.result.json','runtime-warnings.json','oracle.result.json','regression.result.json'):
            path=root/name
            if path.exists():entry[name]=lite._parse(path.read_bytes())
        count=root/'workspace/test-count.json'
        if count.exists():entry['test_count']=lite._parse(count.read_bytes())
        entry['host_command_requests']=sum((root/n).exists() for n in ('oracle.request.json','regression.request.json'))
        entry['model_invocations']=int((root/'model.request.json').exists())
        # Accepted Lite turns prohibit tool events. Raw transport remains primary.
        entry['tool_calls']=0 if (root/'response.json').exists() else 'NOT_VERIFIED'
        record[who]=entry
    return record



ORIGINAL=REPO/'memory/evidence/three-task-real-lite-20260908'
originals={}
expected={
 'easy_queue_range':'5c125a6cce3987d664e7098d11b004b5948c85a2b5f4eb2ce2d912f6de6b63bd',
 'medium_interval_merge':'84f62331f085701992ec46a7ef6bd0fd1f0f4d798bbf625283c6bc67e5fcef3c',
 'hard_dependency_cycle':'899ce7f0a30849280ed38beb97ecd7f1b14d367f043eb10d4b876e57193d496d'}
old_config=lite._parse((ORIGINAL/'authorization.json').read_bytes())['config']
if config!=old_config: raise RuntimeError('Original runtime config mismatch')
for key in tasks:
    folder=ORIGINAL/key
    index=lite._parse((folder/'artifact-identities.json').read_bytes())
    for name,digest in index.items():
        path=folder/name
        data=path.read_bytes()
        if sha(data)!=digest:raise RuntimeError('Original evidence changed: '+name)
        originals[str(path)]=digest
    response=(folder/'CONTROL/response.json').read_bytes()
    if sha(response)!=expected[key]:raise RuntimeError('CONTROL response identity mismatch')
    if response!=git('show',HEAD+':tests/fixtures/lite_benchmark_compatibility/'+key+'.json'):
        raise RuntimeError('CONTROL differs from reviewed reproducer')
    if (folder/'CONTROL/prompt.txt').read_bytes()!=bench.prompt(frozen[key]).encode():
        raise RuntimeError('Task prompt drift')
    request=lite._parse((folder/'CONTROL/model.request.json').read_bytes())
    # Exact model argv/config preserved except per-invocation root/schema paths.
    if lite._parse((folder/'CONTROL/model.result.json').read_bytes())['exit_code']!=0:
        raise RuntimeError('Original CONTROL model did not complete')
live.save(BASE/'preserved-control-identities.json',lite.encode(dict(
    responses=expected,original_artifacts=originals,
    provenance='First-run single model outputs; new deterministic collection only; no CONTROL model invocation',
    limitation='CONTROL and TREATMENT model calls occurred at different times; not contemporaneous randomized repeats')))

def prepare_preserved_task(folder,key):
    fixture=frozen[key]
    folder.mkdir(exist_ok=False)
    live.save(folder/'fixture-inputs.json',lite.encode(dict(task=fixture.task.decode(),baseline=fixture.baseline.decode(),
        cases=lite._parse(fixture.cases),rubric=fixture.rubric.decode(),manifest_sha256=bench.MANIFEST_SHA256,config=config)))
    control=folder/'CONTROL';control.mkdir()
    prior=ORIGINAL/key/'CONTROL'
    value=lite._parse((prior/'response.json').read_bytes())
    result=lite._parse((prior/'model.result.json').read_bytes())
    live.save(control/'preserved-model-provenance.json',lite.encode(dict(
        response_sha256=expected[key],original_model_result=result,
        original_model_request_sha256=sha((prior/'model.request.json').read_bytes()),
        original_runtime_warnings=lite._parse((prior/'runtime-warnings.json').read_bytes()),
        model_invocations_this_slice=0)))
    collect_start=time.monotonic()
    inputs={'CONTROL':bench.collect(fixture,python,Path(config['codex_home']),control,value,result)}
    live.save(control/'collection-timing.json',lite.encode(dict(elapsed_ms=round((time.monotonic()-collect_start)*1000))))
    print('CONTROL_RECOLLECTED '+key,flush=True)
    treatment=folder/'TREATMENT';treatment.mkdir()
    print('TREATMENT_START '+key,flush=True)
    value,result=live.model_call(codex,config['model'],Path(config['codex_home']),treatment,
        bench.prompt(fixture)+'\nAdditional process guidance:\n'+skill.decode(),live.ARM_SCHEMA)
    # Check actual persisted invocation uses original auth/model/timeout/env policy.
    current=lite._parse((treatment/'model.request.json').read_bytes())
    previous=lite._parse((prior/'model.request.json').read_bytes())
    def normalize(v):
        if isinstance(v,str):return v.replace(str(treatment),'<CONTEXT>').replace(str(prior),'<CONTEXT>')
        if isinstance(v,list):return [normalize(x) for x in v]
        if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
        return v
    if normalize(current)!=normalize(previous):raise RuntimeError('Arm invocation settings mismatch')
    inputs['TREATMENT']=bench.collect(fixture,python,Path(config['codex_home']),treatment,value,result)
    session=lite.LiteSession(inputs,rubric_bytes=fixture.rubric,run_id=str(uuid.uuid4()),synthetic=False)
    live.save(folder/'scorer-input.json',session.scorer_input)
    return session


started=time.monotonic(); results={}
for key in tasks:
    unchanged()
    if bench.load_fixture(key)!=frozen[key]:raise RuntimeError('Fixture changed')
    folder=BASE/key; task_start=time.monotonic()
    print('TASK_START '+key,flush=True)
    result={'task':key,'status':'BLOCKED','human_execution_interventions':0,'automatic_adapter_retries':0}
    try:
        session=prepare_preserved_task(folder,key)
        scorer=folder/'scorer';scorer.mkdir()
        print('SCORER_START '+key,flush=True)
        response,scorer_result=live.model_call(codex,config['model'],Path(config['codex_home']),scorer,
            'Grade only this anonymous packet. Use no tools, files, prior sessions or identity inference.\n'
            +session.scorer_input.decode(),live.score_schema(session.scorer_input))
        frozen_scores=session.freeze(lite.encode(response))
        live.save(folder/'scores-frozen.json',frozen_scores)
        if (folder/'scores-frozen.json').read_bytes()!=frozen_scores:raise RuntimeError('Freeze readback mismatch')
        print('SCORES_FROZEN '+key+' '+sha(frozen_scores),flush=True)
        # Current owner explicitly authorizes opening only after durable freeze.
        report=lite._parse(session.unblind(authorized_freeze_sha256=sha(frozen_scores)))
        if session.frozen_scores!=frozen_scores:raise RuntimeError('Freeze changed')
        report.update(task=key,claim_ceiling=lite.CLAIMS,runner='preserved first-run CONTROL + fresh TREATMENT; current host oracle/regression',
                      no_os_isolation_claim=True,skill_generalization='NOT_ESTABLISHED')
        live.save(folder/'report.json',lite.encode(report))
        result.update(status='COMPLETE',report=report,freeze_sha256=sha(frozen_scores))
    except Exception as exc:
        result['failure']={'type':type(exc).__name__,'message':str(exc)}
        # Do not overwrite the adapter's own failure receipt.
        print('TASK_BLOCKED '+key+' '+type(exc).__name__+': '+str(exc),flush=True)
    result['elapsed_ms']=round((time.monotonic()-task_start)*1000)
    result['evidence']=evidence(folder)
    if not folder.exists():folder.mkdir()
    live.save(folder/'terminal.json',lite.encode(result))
    live.save(folder/'artifact-identities.json',lite.encode({p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}))
    results[key]=result
    print('TASK_TERMINAL '+key+' '+result['status'],flush=True)

unchanged()
for path,digest in originals.items():
    if sha(Path(path).read_bytes())!=digest:raise RuntimeError('Historical evidence changed')
live.save(BASE/'preservation-verification.json',lite.encode(dict(original_artifact_count=len(originals),unchanged=True,head=HEAD)))
summary=dict(result='THREE_TASK_LITE_BENCHMARK_TERMINAL',tasks=results,
    elapsed_ms=round((time.monotonic()-started)*1000),claim_ceiling=lite.CLAIMS,
    completed=sum(r['status']=='COMPLETE' for r in results.values()),
    blocked=sum(r['status']!='COMPLETE' for r in results.values()),
    material_changes=0,automatic_adapter_retries=0,human_execution_interventions=0,
    not_claimed=['Generalized Skill effectiveness','Formal/counted evidence','OS isolation','Average operating-cost improvement'],
    interpretation='Only complete task reports support quality comparisons; blocked tasks are not Skill failures or ties.')
live.save(BASE/'summary.json',lite.encode(summary))
print('BENCHMARK_STOP '+str(summary['completed'])+' complete / '+str(summary['blocked'])+' blocked',flush=True)
