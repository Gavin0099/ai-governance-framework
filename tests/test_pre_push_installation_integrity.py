"""P5 isolated repos: invoke the actual derived hook and historical scanner."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from governance_tools import pre_push_installation_integrity as p5

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which('git')
BASH = Path('C:/Program Files/Git/bin/bash.exe') if os.name == 'nt' else Path(shutil.which('bash'))
REPOSITORY = 'https://github.com/Gavin0099/ai-governance-framework.git'


def command(*args, cwd=None):
    return subprocess.check_output([GIT, *args], cwd=cwd, stderr=subprocess.PIPE)


@pytest.fixture
def installation(tmp_path):
    repo=tmp_path/'repo'; repo.mkdir()
    command('init',str(repo)); command('config','user.name','Fixture',cwd=repo)
    command('config','user.email','fixture@example.invalid',cwd=repo)
    command('remote','add','origin',REPOSITORY,cwd=repo)
    config=repo/p5.CONFIG; config.parent.mkdir()
    config.write_bytes(p5.encode(dict(schema='external-tree-inventory-guard-identities.v1',
        repository_identities=[REPOSITORY,'@repository-root'])))
    config_sha=p5.digest(config.read_bytes())
    framework=tmp_path/'framework'; (framework/'governance_tools/profiles').mkdir(parents=True)
    for rel in (p5.VERIFIER,p5.TEMPLATE): shutil.copyfile(ROOT/rel,framework/rel)
    scanner=(ROOT/'tests/fixtures/p5_pre_push_195a204f/external_tree_inventory_guard.py').read_bytes()
    assert p5.digest(scanner)==p5.SCANNER_SHA
    (framework/p5.SCANNER).write_bytes(scanner)
    lib=framework/'scripts/lib';lib.mkdir(parents=True)
    # Native hook Python resolver is preserved; only test env selects executable.
    shutil.copyfile(ROOT/'scripts/lib/python.sh',lib/'python.sh')
    (framework/'scripts/run-runtime-governance.sh').write_text('#!/bin/bash\necho RUNTIME_AFTER_CLOSURE\nexit 0\n')
    hooks=repo/'.git/hooks'
    (hooks/'ai-governance-framework-root').write_text(framework.as_posix()+'\n')
    output=tmp_path/'candidate'
    p5.prepare(repo,framework,REPOSITORY,config_sha,output)
    for name in ('pre-push',p5.RECEIPT):shutil.copyfile(output/name,hooks/name)
    (hooks/'pre-push').chmod(0o755)
    return dict(repo=repo,framework=framework,hook=hooks/'pre-push',receipt=hooks/p5.RECEIPT,
                config=config,config_sha=config_sha,output=output)


def verify(i, repository_id=REPOSITORY):
    return p5.verify(i['repo'],i['framework'],i['hook'],i['receipt'],repository_id,REPOSITORY,i['config_sha'])


def invoke(i, updates=b''):
    env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','PYTHON'))
         and k not in ('AI_GOVERNANCE_FRAMEWORK_ROOT','AI_GOVERNANCE_PYTHON')}
    env['AI_GOVERNANCE_PYTHON']=Path(sys.executable).as_posix()
    env['PATH']=str(Path(GIT).parent)+os.pathsep+env.get('PATH','')
    return subprocess.run([str(BASH),i['hook'].as_posix()],cwd=i['repo'],env=env,input=updates,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)


def commit(i, name, value):
    path=i['repo']/name;path.write_text(json.dumps(value))
    command('add',name,cwd=i['repo']);command('commit','-m','fixture',cwd=i['repo'])
    return command('rev-parse','HEAD',cwd=i['repo']).decode().strip()


def update(oid, old='0'*40):
    return f'refs/heads/main {oid} refs/heads/main {old}\n'.encode()


def test_full_profile_and_real_closure_pass(installation):
    i=installation
    assert verify(i)['installer_generation']==p5.GENERATION
    oid=commit(i,'ordinary.json',{'result':'ok'})
    result=invoke(i,update(oid))
    assert result.returncode==0,(result.stdout,result.stderr)
    assert b'P5_INSTALLATION_MATCH' in result.stdout
    assert b'json_blobs=1' in result.stdout
    assert b'RUNTIME_AFTER_CLOSURE' in result.stdout
    assert result.stdout.index(b'P5_INSTALLATION_MATCH') < result.stdout.index(b'scanning pre-push')


@pytest.mark.parametrize('failure',['wrong_scanner','alter_scanner','config','repository','missing','stale','hook','generation','verifier'])
def test_mismatch_stops_before_scanner(installation,failure):
    i=installation
    if failure=='wrong_scanner':
        (i['framework']/p5.SCANNER).write_bytes(b'# Synthetic incompatible scanner generation\nraise SystemExit(2)\n')
    elif failure=='alter_scanner':
        p=i['framework']/p5.SCANNER;p.write_bytes(p.read_bytes()+b'\n')
    elif failure=='config': i['config'].write_bytes(i['config'].read_bytes()+b'\n')
    elif failure=='repository':command('remote','set-url','origin','https://example.invalid/wrong.git',cwd=i['repo'])
    elif failure=='missing':i['receipt'].unlink()
    elif failure in ('stale','generation'):
        receipt=json.loads(i['receipt'].read_bytes())
        receipt['receipt_sha256' if failure=='stale' else 'installer_generation']='0'*64
        i['receipt'].write_bytes(p5.encode(receipt))
    elif failure=='hook':i['hook'].write_bytes(i['hook'].read_bytes()+b'\n# changed\n')
    elif failure=='verifier':
        p=i['framework']/p5.VERIFIER;p.write_bytes(p.read_bytes()+b'\n# changed\n')
    result=invoke(i)
    assert result.returncode!=0
    assert b'INSTALLATION_MISMATCH' in result.stdout+result.stderr
    assert b'scanning pre-push' not in result.stdout
    assert b'RUNTIME_AFTER_CLOSURE' not in result.stdout


def test_wrong_schema_cannot_be_enrolled_even_with_explicit_new_hash(installation):
    i=installation;i['config'].write_bytes(p5.encode({'schema':'wrong','repository_identities':[REPOSITORY,'@repository-root']}))
    with pytest.raises(p5.InstallationMismatch):
        p5.prepare(i['repo'],i['framework'],REPOSITORY,p5.digest(i['config'].read_bytes()),i['output'].parent/'bad')
    assert not (i['output'].parent/'bad').exists()


def test_wrong_config_identity_cannot_be_enrolled(installation):
    i=installation;i['config'].write_bytes(p5.encode({'schema':'external-tree-inventory-guard-identities.v1','repository_identities':['wrong/repo','@repository-root']}))
    with pytest.raises(p5.InstallationMismatch):
        p5.prepare(i['repo'],i['framework'],REPOSITORY,p5.digest(i['config'].read_bytes()),i['output'].parent/'bad')


def test_closure_failure_not_masked_even_if_worktree_cleaned(installation):
    i=installation
    entries=[{'path':f'source/{n}.py','oid':f'{n:040x}'} for n in range(101)]
    commit(i,'inventory.json',{'repository':'other/external','tree':entries})
    # A later commit removes the offending file. Closure must still inspect it.
    command('rm','inventory.json',cwd=i['repo']);command('commit','-m','remove',cwd=i['repo'])
    oid=command('rev-parse','HEAD',cwd=i['repo']).decode().strip()
    result=invoke(i,update(oid))
    assert result.returncode!=0,(result.stdout,result.stderr)
    assert b'P5_INSTALLATION_MATCH' in result.stdout
    assert b'blocked the push' in result.stderr
    assert b'RUNTIME_AFTER_CLOSURE' not in result.stdout


def test_bad_object_range_remains_failure(installation):
    result=invoke(installation,update('1'*40))
    assert result.returncode!=0
    assert b'P5_INSTALLATION_MATCH' in result.stdout
    assert b'RUNTIME_AFTER_CLOSURE' not in result.stdout


def test_prepare_is_explicit_create_once_not_deployment(installation):
    i=installation
    with pytest.raises(FileExistsError):p5.prepare(i['repo'],i['framework'],REPOSITORY,i['config_sha'],i['output'])
    with pytest.raises(p5.InstallationMismatch):p5.prepare(i['repo'],i['framework'],REPOSITORY,i['config_sha'],i['repo']/'.git/hooks/new')
    with pytest.raises(p5.InstallationMismatch):p5.prepare(i['repo'],i['framework'],REPOSITORY,'',i['output'].parent/'bad')


def test_receipt_is_closed_and_repo_placement_bound(installation):
    i=installation;raw=i['receipt'].read_bytes()
    i['receipt'].write_bytes(raw[:-2]+b',"extra":true}\n')
    with pytest.raises(p5.InstallationMismatch):verify(i)


def test_exact_template_retains_whole_original_scan_and_tail():
    original=(ROOT/p5.TEMPLATE).read_bytes()
    derived=p5.render_hook(original,REPOSITORY,'a'*64)
    assert original.split(p5.MARKER,1)[1]==derived.split(p5.MARKER,1)[1]
    assert original.split(p5.MARKER,1)[0]==derived.split(b'# P5 fixed-generation',1)[0]
