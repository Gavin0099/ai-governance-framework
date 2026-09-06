"""Replacement creation launcher. Separate owner creation authorization required; no readiness or execution modes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import stat
import sys
import secrets
import importlib.abc
import importlib.machinery

ROOT = Path('D:/ai-governance-framework')
BASE = Path('D:/r2-replacement-disposable-shakedown-20260906')
OWNER = 'S-1-5-21-4017902291-1272973841-664929404-1001'
HERE = Path(__file__).resolve().parent


def stop(message):
    raise RuntimeError('REPLACEMENT_LAUNCHER_STOP: ' + message)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode() + b'\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path, *, allow_hardlinks=False):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        stop('noncanonical path')
    for entry in (path, *path.parents):
        info = entry.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            stop('redirected path')
    if not path.is_file() or (not allow_hardlinks and path.stat().st_nlink != 1):
        stop('nonregular file')
    return path.read_bytes()


def check_pin(item):
    # Installed dependencies may use content-store hardlinks; verify exact bytes
    # on every import. Custody/state records still require a single link.
    raw = regular(item['path'], allow_hardlinks=True)
    if len(raw) != item['bytes'] or digest(raw) != item['sha256']:
        stop('identity mismatch: ' + item['path'])
    return raw


def write_once(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if regular(path) != raw:
        stop('write verification')


def bootstrap(manifest_sha):
    raw = regular(HERE / 'manifest.json')
    if digest(raw) != manifest_sha:
        stop('manifest identity')
    manifest = json.loads(raw)
    for item in manifest['pins']:
        check_pin(item)
    check_pin(manifest['candidate_payload'])
    # Reject unlisted repository/site imports and ignore cached bytecode entirely.
    pins = {os.path.normcase(str(Path(i['path']))): i for i in manifest['pins']}
    class Source(importlib.machinery.SourceFileLoader):
        def get_code(self, fullname):
            return compile(check_pin(pins[os.path.normcase(self.path)]), self.path, 'exec')
    class Imports(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            if spec is None or spec.origin is None:
                return spec
            origin = Path(spec.origin)
            if ROOT in origin.parents:
                item = pins.get(os.path.normcase(str(origin)))
                if item is None:
                    stop('unlisted import: ' + fullname)
                check_pin(item)
                if origin.suffix == '.py':
                    spec.loader = Source(fullname, str(origin))
            return spec
    sys.meta_path.insert(0, Imports())
    # -I -S prevents startup hooks; add only pinned repository/dependency roots.
    sys.path[:0] = [str(ROOT), str(ROOT / '.venv/Lib/site-packages')]
    from governance_tools import solo_r2_disposable_binding as binding
    from governance_tools import solo_r2_disposable_profile as profile
    from governance_tools import solo_r2_pair_creation as pairs
    from governance_tools import solo_r2_controller_state as custody
    from governance_tools import solo_r2_codex_runner as runner
    from governance_tools import solo_r2_runtime_window as runtime
    from governance_tools import solo_r2_attempt_materialization as material
    from governance_tools import solo_r2_attempt_execution as attempt
    from governance_tools import solo_r2_disposable_materialization as dm
    from governance_tools import solo_r2_disposable_execution as de
    from governance_tools import solo_attempt_ledger_v2 as ledger
    modules = dict(binding=binding, profile=profile, pairs=pairs, custody=custody,
                   runner=runner, runtime=runtime, material=material, attempt=attempt,
                   dm=dm, de=de, ledger=ledger)
    return manifest, modules


def paths():
    return {name: BASE / name for name in (
        'consumer', 'materialization', 'execution', 'scoring', 'controller', 'keys',
        'commitments', 'temp')}


def context(modules, manifest):
    m = modules['material']
    git_item = manifest['executables']['git']
    git = m.PinnedExecutable(Path(git_item['path']), git_item['bytes'], git_item['sha256'])
    repo = m.RepositoryBinding(ROOT, ROOT / '.git', ROOT / '.git')
    return git, repo


def phase_a(modules, manifest):
    if BASE != modules['profile'].REPLACEMENT_RUNTIME_ROOT or ROOT != modules['profile'].ROOT:
        stop('replacement placement mismatch')
    p = paths()
    # Quiescence runs before any allocation, key or durable runtime root creation.
    runtime = modules['runtime']
    runtime.WindowsCodexRuntimeQuiescence(temp_root=Path(os.environ['TEMP']))()
    modules['runner']._windows_process_identity().validate(OWNER)
    if os.path.lexists(BASE):
        stop('dedicated namespace already exists; no retry')
    check_pin(manifest['candidate_payload'])
    git, repo = context(modules, manifest)
    modules['binding'].load_replacement_authority(
        git=git, repository=repo, temp_root=Path(os.environ['TEMP']))
    modules['binding']._failed_evaluation(ROOT)
    authority = modules['binding'].load_input_authority(
        git=git, repository=repo, temp_root=Path(os.environ['TEMP']))
    modules['de'].DisposableRepositoryFreezeProbe(
        git=git, repository=repo, temp_root=Path(os.environ['TEMP'])).capture()
    for relative in (modules['profile'].REPLACEMENT_LEDGER_PATH, modules['profile'].REPLACEMENT_BINDING_PATH):
        if (ROOT / relative).parent.exists():
            stop('disposable allocation already reserved')
    for candidate in (BASE, *BASE.parents):
        if candidate.exists() and (candidate.resolve(strict=True) != candidate
                or getattr(candidate.lstat(), 'st_file_attributes', 0) & 0x400):
            stop('redirected runtime root')
    BASE.mkdir()
    for directory in p.values():
        directory.mkdir()
    boundary = modules['custody'].CustodyBoundary(
        ROOT, p['consumer'], p['materialization'], p['execution'], p['scoring'])
    key = p['keys'] / 'controller-key.json'
    commitment = p['commitments'] / 'sealed-package-digest.commitment'
    modules['pairs'].validate_replacement_targets(controller_root=p['controller'],
        key_path=key, commitment_path=commitment, custody_boundary=boundary)
    modules['binding'].verify_replacement_custody(controller_root=p['controller'],
        key_path=key, commitment_path=commitment, custody_boundary=boundary)
    modules['custody'].create_controller_key(key, custody_boundary=boundary)
    creation = modules['binding'].create_replacement_disposable_evaluation(
        git=git, repository=repo, temp_root=p['temp'])
    bound = modules['binding'].load_replacement_ledger_binding(
        git=git, repository=repo, temp_root=p['temp'],
        expected_binding_sha256=creation.binding_sha256,
        expected_evaluation_id=creation.evaluation_id)
    if bound.input_authority != authority:
        stop('authority changed')
    pair = modules['pairs'].create_replacement_disposable_shakedown_pair(
        git=git, repository=repo, temp_root=p['temp'],
        expected_binding_sha256=creation.binding_sha256,
        expected_evaluation_id=creation.evaluation_id,
        controller_root=p['controller'], key_path=key, commitment_path=commitment,
        custody_boundary=boundary)
    payload = manifest['candidate_payload']
    check_pin(payload)
    record = canonical(dict(schema='solo-r2-owner-payload-pin/v1', authority_class='OWNER_ATTESTED',
        evaluation_id=creation.evaluation_id, pair_id=pair.pair_id, slot='R2-SHAKEDOWN',
        payload_byte_length=payload['bytes'], payload_sha256=payload['sha256']))
    write_once(BASE / 'payload-pin.candidate.json', record)
    state = dict(profile='replacement-disposable', runtime_root=str(BASE),
        allocation_sha256=modules['profile'].REPLACEMENT_DECISION_SHA256, evaluation_id=creation.evaluation_id, pair_id=pair.pair_id,
        genesis_sha256=creation.genesis_sha256, binding_sha256=creation.binding_sha256,
        ledger_sha256=pair.ledger_sha256, sealed_package_digest=pair.sealed_package_digest,
        checkpoint_path=str(pair.checkpoint_path), payload_record_sha256=digest(record),
        payload_record_bytes=len(record), manifest_sha256=digest(regular(HERE/'manifest.json')))
    raw = canonical(state)
    write_once(BASE / 'phase-a.json', raw)
    verify_zero(modules, state, bound=bound)
    print('PHASE_A_COMPLETE / STOP — readiness NOT RUN; Attempt 0; exposure NONE')
    print(record.decode(), end='')
    print('PAYLOAD_RECORD_BYTES:', len(record), 'PAYLOAD_RECORD_SHA256:', digest(record))
    print('STATE_SHA256:', digest(raw))


def verify_zero(modules, state, *, bound):
    public = ROOT / modules['profile'].REPLACEMENT_LEDGER_PATH
    raw = regular(public)
    bound.verify(public, raw)
    if (state['profile'] != 'replacement-disposable' or state['runtime_root'] != str(BASE)
            or state['allocation_sha256'] != modules['profile'].REPLACEMENT_DECISION_SHA256):
        stop('wrong replacement state')
    if digest(raw) != state['ledger_sha256']:
        stop('ledger changed')
    events = modules['ledger'].read_ledger(public)
    summary = modules['ledger'].validate_ledger_events(events)
    if len(events) != 2 or summary.admitted_attempt_count or summary.initiated_attempt_count:
        stop('nonzero Attempt or wrong ledger')
    bound.verify_append(public, raw.splitlines(keepends=True)[0], events[1])
    if events[0]['evaluation_id'] != state['evaluation_id'] or events[1]['pair_id'] != state['pair_id']:
        stop('evaluation/Pair mismatch')
    binding = regular(ROOT / modules['profile'].REPLACEMENT_BINDING_PATH)
    if digest(binding) != state['binding_sha256']:
        stop('genesis binding changed')
    if digest(raw.splitlines(keepends=True)[0]) != state['genesis_sha256']:
        stop('genesis bytes changed')



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--mode', choices=['check', 'phase-a'], required=True)
    args = parser.parse_args()
    manifest, modules = bootstrap(args.manifest_sha256)
    if args.mode == 'check':
        print('STATIC_BINDINGS_PASS; no creation, credentials, or readiness invoked')
    else:
        phase_a(modules, manifest)


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
