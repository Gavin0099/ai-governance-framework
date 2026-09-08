"""Read preserved results; save exact closeout copies, without executing evaluation."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parent
def sha(data):
    return hashlib.sha256(data).hexdigest()
manifest = []
def preserve(path, name, expected=None, size=None):
    data = Path(path).read_bytes()
    assert expected is None or sha(data) == expected, str(path)
    assert size is None or len(data) == size, str(path)
    target = DEST / name
    if target.exists():
        assert target.read_bytes() == data
    else:
        target.write_bytes(data)
    manifest.append(dict(source=str(path), copy=name, bytes=len(data), sha256=sha(data)))
    return json.loads(data) if name.endswith('.json') else data

scoring = preserve(ROOT/'memory/evidence/solo-r2-simplified-blind-scoring-20260907/result.json', 'scoring-result.json')
opening = preserve(ROOT/'memory/evidence/solo-r2-unblinding-only-20260907/result.json', 'unblinding-result.json')
f = scoring['frozen_identity']
preserve(f['path'], 'scores-frozen.json', f['sha256'], f['bytes'])
assert f['sha256'] == '7fd6c864fc1c806bb015cfc13e234ae3766a911735e031164c6706ac0a07353e'
for entry in opening['results']:
    identity = entry['score_identity']
    score = preserve(identity['path'], entry['arm'].lower()+'-score.json', identity['sha256'], identity['bytes'])
    assert score == entry['frozen_score']
for field in ('opening_authorization', 'opening_receipt'):
    identity = opening[field]
    preserve(identity['path'], field+'.json', identity['sha256'], identity['bytes'])
ledger = preserve(ROOT/'artifacts/evidence/solo-r2-final-disposable-mechanism-shakedown-20260907/attempt-ledger.v2.1.ndjson', 'ledger-snapshot.ndjson', 'e471517f5e6e36e2fdce3f42c8e87edf6b87c2cc4a67e47acbf90352140eac77', 5193)
assert len(ledger.splitlines()) == 9
oracle_root = ROOT/'memory/evidence/solo-r2-final-oracle-20260907'
summary = preserve(oracle_root/'verified-summary.json', 'oracle-verified-summary.json')
preserve(oracle_root/'summary.json', 'oracle-original-summary.json', summary['supersedes_summary_sha256'])
for n, entry in enumerate(summary['results'], 1):
    handle = entry['attempt_handle']
    result = preserve(oracle_root/(handle+'.verified-result.json'), f'oracle-{n}-verified.json', entry['verified_result_sha256'])
    assert result['passed_case_count'] == 10 and result['returncode'] == 0
    preserve(oracle_root/(handle+'.result.json'), f'oracle-{n}-original.json', result['correction']['supersedes_result_sha256'])
    for stream in ('stdout', 'stderr'):
        preserve(oracle_root/(handle+'.'+stream+'.txt'), f'oracle-{n}-{stream}.txt', result[stream+'_sha256'])
for name in ('verification.json', 'timeout-audit.json'):
    preserve(ROOT/'memory/evidence/r2-server-validated-username-probe-20260908'/name, 'post-gate3-'+name)
(DEST/'identities.json').write_text(json.dumps({'verification':'EXACT_COPIES_MATCH','ledger_events':9,'evaluation_rerun':False,'sources':manifest}, indent=2)+'\n', encoding='utf-8')
print(f'PASS: {len(manifest)} exact copies; ledger 9 events; scores and oracle identities verified; no execution.')
