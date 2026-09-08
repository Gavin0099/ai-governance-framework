"""One owner-authorized delivery of three frozen tasks. No retries or repairs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO))
HEAD='bfae8ce65b997f9690963f8ac396e29e355a8b0f'
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
    owner_scope='Exactly one real Lite run for each of three frozen tasks; scorer, freeze then unblind authorized; no repair/retry/commit/push',
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


started=time.monotonic(); results={}
for key in tasks:
    unchanged()
    if bench.load_fixture(key)!=frozen[key]:raise RuntimeError('Fixture changed')
    folder=BASE/key; task_start=time.monotonic()
    print('TASK_START '+key,flush=True)
    result={'task':key,'status':'BLOCKED','human_execution_interventions':0,'automatic_adapter_retries':0}
    try:
        session=bench.prepare_task(folder,config,skill,key)
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
        report.update(task=key,claim_ceiling=lite.CLAIMS,runner='fresh model generation + host oracle/regression',
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
summary=dict(result='THREE_TASK_LITE_BENCHMARK_TERMINAL',tasks=results,
    elapsed_ms=round((time.monotonic()-started)*1000),claim_ceiling=lite.CLAIMS,
    completed=sum(r['status']=='COMPLETE' for r in results.values()),
    blocked=sum(r['status']!='COMPLETE' for r in results.values()),
    material_changes=0,automatic_adapter_retries=0,human_execution_interventions=0,
    not_claimed=['Generalized Skill effectiveness','Formal/counted evidence','OS isolation','Average operating-cost improvement'],
    interpretation='Only complete task reports support quality comparisons; blocked tasks are not Skill failures or ties.')
live.save(BASE/'summary.json',lite.encode(summary))
print('BENCHMARK_STOP '+str(summary['completed'])+' complete / '+str(summary['blocked'])+' blocked',flush=True)
