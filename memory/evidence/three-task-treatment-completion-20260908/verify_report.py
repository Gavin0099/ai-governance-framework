from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
    raw=(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    with p.open('xb') as f:f.write(raw)
    assert p.read_bytes()==raw
summary=load(ROOT/'summary.json')
auth=load(ROOT/'authorization.json')
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD']).decode().strip()==auth['head']
for path,digest in auth['bound_sources'].items():assert sha((REPO/path).read_bytes())==digest
old=load(ROOT/'preserved-control-identities.json')
for path,digest in old['original_artifacts'].items():assert sha(Path(path).read_bytes())==digest
verified=0
rows=[]
for key,result in summary['tasks'].items():
    folder=ROOT/key
    for name,digest in load(folder/'artifact-identities.json').items():
        assert sha((folder/name).read_bytes())==digest
        verified+=1
    assert not (folder/'CONTROL/model.request.json').exists()
    row={'task':key,'status':result['status'],'arms':{}}
    for arm in ('CONTROL','TREATMENT'):
        root=folder/arm
        data={}
        for name in ('oracle.result.json','regression.result.json','workspace/test-count.json','payload.json'):
            if (root/name).exists():data[name]=load(root/name)
        if arm=='CONTROL':
            prov=load(root/'preserved-model-provenance.json')
            data['model_elapsed_ms']=prov['original_model_result']['elapsed_ms']
            data['model_origin']='preserved first-run model'
        elif (root/'model.result.json').exists():
            data['model_elapsed_ms']=load(root/'model.result.json')['elapsed_ms']
            data['model_origin']='fresh single invocation'
        row['arms'][arm]=data
    if result['status']=='COMPLETE':
        frozen=(folder/'scores-frozen.json').read_bytes()
        report=load(folder/'report.json')
        assert sha(frozen)==report['freeze_sha256']==result['freeze_sha256']
        scores=load(folder/'scores-frozen.json')
        assert scores['scorer_input_sha256']==sha((folder/'scorer-input.json').read_bytes())
        for arm,v in report['arms'].items():
            assert v['quality']==scores['scores'][v['presentation_key']]
        assert (folder/'report.json').stat().st_mtime_ns >= (folder/'scores-frozen.json').stat().st_mtime_ns
        row['report']=report
    else:row['failure']=result.get('failure')
    rows.append(row)
verification={'head':auth['head'],'bound_source_match':True,'historical_artifact_count':len(old['original_artifacts']),
 'historical_unchanged':True,'verified_new_task_artifacts':verified,'control_model_invocations':0,
 'treatment_model_invocations':sum((ROOT/k/'TREATMENT/model.request.json').exists() for k in summary['tasks']),
 'scorer_model_invocations':sum((ROOT/k/'scorer/model.request.json').exists() for k in summary['tasks']),
 'freeze_linkage_verified':True,'summary_sha256':sha((ROOT/'summary.json').read_bytes())}
save(ROOT/'verification.json',verification)
save(ROOT/'comparison-evidence.json',rows)
lines=['# Three-task Lite: preserved CONTROL + fresh TREATMENT','',
 'Scope: NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY.',
 'CONTROL responses are the original single-run outputs. Only deterministic collection/oracle/regression was rerun under committed corrected harness bytes. CONTROL model was not invoked again.',
 'TREATMENT uses the same frozen task/baseline/model/auth/timeout/environment settings with the frozen Skill packet. Context paths differ by design. Calls are not contemporaneous; no repeated-sample or generalized causal claim.',
 '', '| Task | Status | CONTROL oracle / regression | TREATMENT oracle / regression | Quality C / T |',
 '|---|---|---|---|---|']
for row in rows:
    cells=[]
    for arm in ('CONTROL','TREATMENT'):
        d=row['arms'][arm]
        c=d.get('payload.json',{}).get('correctness',{})
        t=d.get('workspace/test-count.json',{})
        cells.append(f"{c.get('passed_case_count','?')}/{c.get('required_case_count','?')}; tests={t.get('tests_run','?')}, errors={t.get('errors','?')}, failures={t.get('failures','?')}")
    q=row.get('report',{}).get('arms',{})
    totals=' / '.join(str(q.get(a,{}).get('quality_total','NOT_AVAILABLE')) for a in ('CONTROL','TREATMENT'))
    lines.append('| '+row['task']+' | '+row['status']+' | '+cells[0]+' | '+cells[1]+' | '+totals+' |')
lines+=['','## Evidence and interpretation','',
 'Regression test methods are actual unittest counts, not oracle cases or subTest iterations. Errors/NameError do not establish successful assertion execution and remain NOT_ASSESSABLE under the frozen rubric. Oracle correctness does not substitute for quality evidence.',
 'Missing total means neither overall winner nor overall tie can be inferred. No source/test repair, material supplementation, scorer retry or post-unblinding score edit was performed.',
 '', '## Model elapsed time (ms)','', '| Task | Original CONTROL | Fresh TREATMENT |', '|---|---|---|']
for r in rows:lines.append('| '+r['task']+' | '+str(r['arms']['CONTROL'].get('model_elapsed_ms','?'))+' | '+str(r['arms']['TREATMENT'].get('model_elapsed_ms','?'))+' |')
lines+=['','Detailed rubric evidence and mappings: per-task report.json; immutable scores: per-task scores-frozen.json. Raw completion evidence remains per-task, per-arm model/oracle/regression request/result/stdout/stderr.',
 'Known runtime warnings are retained in runtime-warnings.json and never relabeled as no runtime issues.',
 'Manual execution/data repair interventions: 0. Automatic adapter retries: 0. Owner authorization and normal tool approval are not classified as manual benchmark repairs.',
 'Governance-cost observation: no new substantive governance friction observed in this execution slice; extra time not separately measured. Prior harness repair cost remains in its historical evidence.',
 'No commit or push; STOP after aggregation. Real-model results alone do not establish generalized Skill efficacy, difficulty calibration, or average operating-cost reduction.']
with (ROOT/'benchmark-report.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
print(json.dumps(verification))
for r in rows:
    print(r['task'],r['status'],json.dumps(r.get('report',{}).get('arms',{})))
