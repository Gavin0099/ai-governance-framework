"""One fixed, owner-activated detached scoring instance. No CLI or automatic run.

Custody verifiers are mandatory host-integration capabilities, not booleans.
Fresh scorer isolation must be established by the later execution integration.
No ledger writes, arm/oracle execution, or scorer process launch occurs here.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re

from governance_tools import solo_r2_disposable_execution as inputs
from governance_tools import solo_r2_blind_scoring_bundle as bundle
from governance_tools import solo_r2_controller_state as crypto
from governance_tools import solo_r2_random_domains as randoms

POLICY_COMMIT = '3e36fef9535aff0c4b048ad26d9304e2ee4633d7'
POLICY_PATH = 'docs/governance/solo-r2-superseding-scoring-sealing-authority-candidate-20260907.md'
POLICY_SHA = '10fc9ad2e7ab83088391ed3beaa705d65fc69f0456142bfd3fb329f5cb77535c'
ADOPTION_PATH = 'memory/evidence/solo-r2-superseding-scoring-adoption-20260907/owner-adoption.json'
ADOPTION_SHA = '42a64c0fca128de1f098ba988b4e26d6a8663ffeb8be46b29c1d52b4cf5b9b36'
TOKEN = '2a92a1fff13490d92d0f2cec26cd99016a2f82719cee9847297bf0f30b6878fb'
EVALUATION = '74ad1963-e24c-4ced-9f84-32e3c0daf900'
PAIR = '93584d7e-2bf9-4535-93c8-5593fcd3e272'
HISTORY = (
    ('ledger', 5193, 'e471517f5e6e36e2fdce3f42c8e87edf6b87c2cc4a67e47acbf90352140eac77'),
    ('old_bundle', 3055, 'f0e8af8750182d6dc4bacd5b7f0c280f8b0acccd1dc57ea7844c2fcff5516dce'),
    ('old_checkpoint', 3074, '243e6c2defc1272347b940e8ac20786e0e52f626216ff71a43cf34b3a5243558'),
)


def _fail():
    raise RuntimeError('SUPERSEDING_SCORING_REJECTED / STOP') from None


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode()


def _raw(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        _fail()
    for node in (path, *path.parents):
        info = node.lstat()
        if node.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            _fail()
    inputs.material._regular_unlinked_path(path)
    if path.stat().st_nlink != 1:
        _fail()
    return path.read_bytes()


def _parse(raw):
    value = inputs.binding._json(raw)
    if _canonical(value) != raw:
        _fail()
    return value


def _write(path, value):
    raw = value if type(value) is bytes else _canonical(value)
    inputs._write_once(path, raw)
    if _raw(path) != raw:
        _fail()


def _identity(path):
    raw = _raw(path)
    return dict(path=str(path), bytes=len(raw), sha256=_sha(raw))


def _check(identity, path):
    if identity != _identity(path):
        _fail()


def _paths(root):
    base = inputs.profile.FINAL_RUNTIME_ROOT
    private = base/'controller/superseding-scoring-1'
    return dict(base=base, private=private, scorer=base/'scoring/superseding-scoring-1',
        ledger=root/inputs.profile.FINAL_LEDGER_PATH,
        old_bundle=base/'scoring'/f'{TOKEN}.blind-scoring-bundle.json',
        old_checkpoint=base/'controller'/f'{TOKEN}.scoring-bound.sealed.json',
        checkpoint=private/'scoring-bound.sealed.json', transition=private/'transition.json',
        activation=private/'owner-activation.json', bundle=base/'scoring/superseding-scoring-1/blind-scoring-bundle.json',
        scores=private/'scores-frozen.json', opening=private/'unblinding-receipt.json')


def _policy(git, repository, temp_root):
    root = inputs.binding._root(repository)
    inputs.material.verify_repository_binding(git, repository, temp_root=temp_root)
    for path, expected in ((POLICY_PATH, POLICY_SHA), (ADOPTION_PATH, ADOPTION_SHA)):
        raw = inputs.material._run_git(git, repository,
            ('--no-replace-objects', 'cat-file', 'blob', POLICY_COMMIT+':'+path), temp_root=temp_root)
        if _sha(raw) != expected or _raw(root/path) != raw:
            _fail()
    return root


def _load(git, repository, temp_root, verify_custody):
    root = _policy(git, repository, temp_root)
    p = _paths(root)
    boundary = crypto.CustodyBoundary(root, *(p['base']/n for n in ('consumer','materialization','execution','scoring')))
    key = p['base']/'keys/controller-key.json'
    inputs.binding.verify_final_custody(controller_root=p['base']/'controller',key_path=key,custody_boundary=boundary)
    # Must perform current owner/ACL and deny-boundary checks; no truthy shortcuts.
    if not callable(verify_custody) or verify_custody(p['private'], p['scorer'], boundary) is not None:
        _fail()
    for name, length, digest in HISTORY:
        raw = _raw(p[name])
        if len(raw) != length or _sha(raw) != digest:
            _fail()
    record = inputs.load_scoring_continuation_authority(git=git,repository=repository,temp_root=temp_root)
    if record['evaluation_id'] != EVALUATION or record['pair_id'] != PAIR:
        _fail()
    captured = {}
    def walk(value):
        if type(value) is dict:
            if {'path','bytes','sha256'} <= value.keys():
                path=Path(value['path']); path=path if path.is_absolute() else root/path
                if not (path.is_relative_to(root) or path.is_relative_to(p['base'])):
                    _fail()
                raw=_raw(path)
                if path==p['ledger']:
                    raw=b''.join(raw.splitlines(keepends=True)[:8])
                if len(raw)!=value['bytes'] or _sha(raw)!=value['sha256']:
                    _fail()
                captured[path]=raw
            for v in value.values(): walk(v)
        elif type(value) is list:
            for v in value: walk(v)
    walk(record)
    if len(captured)!=22: _fail()
    events=inputs.ledger.read_ledger(p['ledger']); inputs.ledger.validate_ledger_events(events)
    if len(events)!=9 or events[-1]['event_type']!='CONTROLLER_STATE_SEALED' or events[-1]['sealed_package_digest']!=HISTORY[2][2]:
        _fail()
    if events[0]['evaluation_id']!=EVALUATION or events[1]['pair_id']!=PAIR: _fail()
    state=crypto.open_controller_package(_raw(p['old_checkpoint']),key_path=key,custody_boundary=boundary,
        expected_digest=HISTORY[2][2],expected_evaluation_id=EVALUATION,expected_pair_id=PAIR,expected_slot='R2-SHAKEDOWN')
    handles=[e['attempt_handle'] for e in events if e['event_type']=='ATTEMPT_ADMITTED']
    if state['state_phase']!=crypto.SCORING_BOUND or [x['attempt_handle'] for x in state['attempt_bindings']]!=handles: _fail()
    return root,p,boundary,key,record,events,state


def _project(row, terminal, root, ordinal):
    def read(name):
        path=Path(row[name]['path']); return _raw(path if path.is_absolute() else root/path)
    source=read('terminal_output')
    runtime=inputs.binding._json(read('runtime_evidence'))
    oracle=inputs.binding._json(read('verified_oracle'))
    if (terminal.get('terminal_classification') is not None or runtime['runtime_result']['disposition']!='SUCCESS'
        or runtime['source_sha256']!=_sha(source) or oracle['output_sha256']!=_sha(source)
        or oracle['evaluation_id']!=EVALUATION or oracle['pair_id']!=PAIR or oracle['attempt_handle']!=row['attempt_handle']
        or oracle['oracle_status']!='PASS' or oracle['passed_case_count']!=10 or oracle['required_case_count']!=10): _fail()
    final=inputs.binding._json(read('final_message'))
    if set(final)!={'summary'} or type(final['summary']) is not str: _fail()
    # Only strip exact known custody link destinations, preserving visible text.
    prefix=str(inputs.profile.FINAL_RUNTIME_ROOT).replace('\\','/')+f'/materialization/{PAIR}-execution-{ordinal}/'
    pattern=r'\[([^\]\n]+)\]\('+re.escape(prefix)+r'(?:queue_range|test_queue_range)\.py(?::\d+)?\)'
    summary=re.sub(pattern,lambda m:m[1],final['summary'])
    payload=json.dumps(dict(source=source.decode('utf-8'),final_response={'summary':summary},
        correctness={**terminal['correctness_result'],'oracle_status':'PASS','passed_case_count':10},cost=terminal['cost_metrics']))
    if bundle._contains_scorer_forbidden_identity(payload): _fail()
    return payload


def generate_candidate(*, git, repository, temp_root, verify_custody, verify_projection):
    """Separate owner generation authorization required. Returns identities only."""
    root,p,boundary,key,record,events,old=_load(git,repository,temp_root,verify_custody)
    if os.path.lexists(p['private']) or os.path.lexists(p['scorer']): _fail()
    outputs=[_project(row,events[index],root,i) for i,(row,index) in enumerate(zip(record['terminal_outputs'],(4,7)))]
    if [row['attempt_handle'] for row in record['terminal_outputs']] != [x['attempt_handle'] for x in old['attempt_bindings']]: _fail()
    if not callable(verify_projection) or verify_projection(tuple(outputs)) is not None: _fail()
    # Reservation before RNG/writes; any subsequent error consumes this instance.
    p['private'].mkdir(); _write(p['private']/'reservation.json',dict(policy=POLICY_SHA,revision=1))
    p['scorer'].mkdir()
    if verify_custody(p['private'],p['scorer'],boundary) is not None: _fail()
    seen={x['attempt_handle'] for x in old['attempt_bindings']} | set(old['presentation_order'])
    labels=[]
    for _ in range(2):
        label=randoms.derive_opaque_identifier(randoms.SCORING_LABEL_DOMAIN,os.urandom(32))
        if label in seen: _fail()
        seen.add(label); labels.append(label)
    value=bundle.build_blind_scoring_bundle(evaluation_id=EVALUATION,pair_id=PAIR,slot='R2-SHAKEDOWN',
        rubric_id=record['frozen_rubric']['sha256'],outputs_by_label=dict(zip(labels,outputs)),presentation_entropy=os.urandom(32))
    new=deepcopy(old); new['presentation_order']=value['presentation_order']
    new['scoring_bindings']=[dict(scoring_label=l,attempt_handle=x['attempt_handle']) for l,x in zip(labels,old['attempt_bindings'])]
    package=crypto.seal_controller_state(crypto.freeze_controller_state(new),key_path=key,custody_boundary=boundary)
    previous_nonces={crypto.parse_sealed_package(_raw(f))['nonce_b64'] for f in (p['base']/'controller').glob('*.sealed.json')}
    if crypto.parse_sealed_package(package.package_bytes)['nonce_b64'] in previous_nonces: _fail()
    _write(p['checkpoint'],package.package_bytes); _write(p['bundle'],bundle.encode_blind_scoring_bundle(value))
    _write(p['private']/'projection.json',dict(source_adoption=inputs.SCORING_ADOPTION_SHA256,
        original_final_messages=[r['final_message'] for r in record['terminal_outputs']],projected_payload_sha256=[_sha(v.encode()) for v in outputs]))
    # Revalidate all original identities and verify saved products before transition.
    _load(git,repository,temp_root,verify_custody)
    bundle.parse_blind_scoring_bundle(_raw(p['bundle']))
    if _raw(p['checkpoint'])!=package.package_bytes: _fail()
    transition=dict(evaluation_id=EVALUATION,pair_id=PAIR,revision=1,policy_adoption_sha256=ADOPTION_SHA,
        policy_sha256=POLICY_SHA,source_adoption_sha256=inputs.SCORING_ADOPTION_SHA256,
        history={n:_identity(p[n]) for n,_,_ in HISTORY},bundle=_identity(p['bundle']),checkpoint=_identity(p['checkpoint']),
        old_disposition='NOT_ADMISSIBLE_FOR_SCORING',state='SUPERSEDING_CANDIDATE')
    _write(p['transition'],transition)
    return _identity(p['transition'])


def _active(*, git, repository, temp_root, verify_custody, expected_activation_sha256):
    root,p,boundary,key,record,events,old=_load(git,repository,temp_root,verify_custody)
    activation_raw=_raw(p['activation'])
    if _sha(activation_raw)!=expected_activation_sha256: _fail()
    activation=_parse(activation_raw)
    if set(activation)!={'decision','transition'} or activation['decision']!='OWNER_ADOPTED_EXACT_TRANSITION': _fail()
    _check(activation['transition'],p['transition']); t=_parse(_raw(p['transition']))
    expected=dict(evaluation_id=EVALUATION,pair_id=PAIR,revision=1,policy_adoption_sha256=ADOPTION_SHA,
        policy_sha256=POLICY_SHA,source_adoption_sha256=inputs.SCORING_ADOPTION_SHA256,
        history={n:_identity(p[n]) for n,_,_ in HISTORY},bundle=_identity(p['bundle']),checkpoint=_identity(p['checkpoint']),
        old_disposition='NOT_ADMISSIBLE_FOR_SCORING',state='SUPERSEDING_CANDIDATE')
    if t!=expected or t['checkpoint']['sha256']==HISTORY[2][2] or t['bundle']['sha256']==HISTORY[1][2]: _fail()
    value=bundle.parse_blind_scoring_bundle(_raw(p['bundle']))
    state=crypto.open_controller_package(_raw(p['checkpoint']),key_path=key,custody_boundary=boundary,
        expected_digest=t['checkpoint']['sha256'],expected_evaluation_id=EVALUATION,expected_pair_id=PAIR,expected_slot='R2-SHAKEDOWN')
    for field in ('attempt_bindings','realized_order','order_entropy','attempt_output_refs'):
        if state[field]!=old[field]: _fail()
    if state['presentation_order']!=value['presentation_order'] or set(state['presentation_order']) & (set(old['presentation_order'])|{x['attempt_handle'] for x in old['attempt_bindings']}): _fail()
    if value['rubric_id']!=record['frozen_rubric']['sha256'] or value['evaluation_id']!=EVALUATION or value['pair_id']!=PAIR: _fail()
    return p,value,state,t


def deliver(*, verify_fresh_scorer, **authority):
    """Separately authorized dispatch only; does not launch a scorer."""
    p,value,state,t=_active(**authority)
    if not callable(verify_fresh_scorer) or verify_fresh_scorer(p['bundle'],t['bundle']['sha256']) is not None: _fail()
    _write(p['private']/'dispatch.json',dict(activation=authority['expected_activation_sha256'],transition=_identity(p['transition'])))
    return inputs.lifecycle.ScorerDelivery(p['bundle'],_raw(p['bundle']))


def _validate_score(raw, label, payload):
    score = inputs.binding._json(raw)
    names = {'causal_explanation','regression_safety','patch_focus','evidence_quality'}
    if (set(score) != {'presentation_key','correctness','cost','dimensions','quality_total'}
        or score['presentation_key'] != label or score['correctness'] != payload['correctness']
        or score['cost'] != payload['cost'] or type(score['dimensions']) is not dict
        or set(score['dimensions']) != names): _fail()
    points = []
    for item in score['dimensions'].values():
        if type(item) is not dict or set(item) != {'score','evidence'}: _fail()
        point = item['score']
        if not ((type(point) is int and point in (0,1,2)) or point == 'NOT_ASSESSABLE'): _fail()
        if type(item['evidence']) is not str or not item['evidence'].strip(): _fail()
        if bundle._contains_scorer_forbidden_identity(item['evidence']): _fail()
        points.append(point)
    total = 'NOT_ASSESSABLE' if 'NOT_ASSESSABLE' in points else sum(points)
    if score['quality_total'] != total or type(score['quality_total']) is not type(total): _fail()


def freeze_scores(scores, **authority):
    """Consume both opaque score bytes once, after separate scoring authority."""
    p,value,state,t=_active(**authority)
    dispatch=_parse(_raw(p['private']/'dispatch.json'))
    if dispatch!=dict(activation=authority['expected_activation_sha256'],transition=_identity(p['transition'])): _fail()
    if type(scores) is not dict or set(scores)!=set(value['presentation_order']) or any(type(b) is not bytes or not b for b in scores.values()): _fail()
    payloads={x['presentation_key']:json.loads(x['output_payload']) for x in value['outputs']}
    for label,raw in scores.items(): _validate_score(raw,label,payloads[label])
    # Score contents are rubric evidence, not an execution or correctness override.
    for label,raw in scores.items():
        _write(p['private']/(label+'.score.json'),raw)
    _write(p['scores'],dict(activation=authority['expected_activation_sha256'],transition=_identity(p['transition']),
        scores={l:_identity(p['private']/(l+'.score.json')) for l in value['presentation_order']}))
    return _identity(p['scores'])


def open_after_scores(*, expected_scores_sha256, expected_opening_authorization_sha256, **authority):
    """Owner-only authenticated opening. Return is private; never print/publish it."""
    p,value,state,t=_active(**authority)
    raw=_raw(p['scores'])
    if _sha(raw)!=expected_scores_sha256: _fail()
    scores=_parse(raw)
    expected=dict(activation=authority['expected_activation_sha256'],transition=_identity(p['transition']),
        scores={l:_identity(p['private']/(l+'.score.json')) for l in value['presentation_order']})
    if scores!=expected: _fail()
    payloads={x['presentation_key']:json.loads(x['output_payload']) for x in value['outputs']}
    for label in value['presentation_order']:
        _validate_score(_raw(p['private']/(label+'.score.json')),label,payloads[label])
    permission_raw=_raw(p['private']/'opening-authorization.json')
    if _sha(permission_raw)!=expected_opening_authorization_sha256: _fail()
    if _parse(permission_raw)!=dict(decision='OWNER_AUTHORIZES_OPENING',activation=authority['expected_activation_sha256'],scores_sha256=expected_scores_sha256): _fail()
    _write(p['opening'],dict(activation=authority['expected_activation_sha256'],scores_sha256=expected_scores_sha256,
        authorization_sha256=expected_opening_authorization_sha256,checkpoint=t['checkpoint']))
    arms={x['attempt_handle']:x['arm'] for x in state['attempt_bindings']}
    return tuple((x['scoring_label'],arms[x['attempt_handle']]) for x in state['scoring_bindings'])
