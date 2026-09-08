"""Replacement creation and readiness/wait launcher; each live operation requires owner authority."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import stat
import sys
import secrets
import time
import importlib.abc
import importlib.machinery

ROOT = Path('D:/ai-governance-framework')
BASE = Path('D:/r2-replacement-disposable-shakedown-20260906')
OWNER = 'S-1-5-21-4017902291-1272973841-664929404-1001'
HERE = Path(__file__).resolve().parent
HOME = Path('C:/Users/daish/.codex-r2-replacement-canary')
ADOPTION_COMMIT = '10840d57d6220990ae98e0c64d4f7d6f73d0fd25'
ADOPTION_DIR = Path('memory/evidence/solo-r2-replacement-payload-pin-adoption-20260907')
ADOPTION_SHA = '9efd6fc3e4021c9ca9130c33f07b1da434f8b74b8d15a8f256929cc77b83c848'
PIN_SHA = '0edfdabdb50094e0fa72eb6edd6ab9c17987c917bd2f530908920cf7f2ef99e8'
STATE_SHA = '752f2a1bc14fa00ad85cb0172f02432072c25f680722b28dce674dec214a8c16'
EVALUATION = '8e3fb9fe-d94b-45d5-897c-3a3e75849bd8'
PAIR = 'eef1c2f5-91d7-4d8d-b765-251340f35d67'


def committed_blob(modules, manifest, path):
    git, repo = context(modules, manifest)
    material = modules['material']
    material.verify_repository_binding(git, repo, temp_root=paths()['temp'])
    return material._run_git(git, repo,
        ('--no-replace-objects', 'cat-file', 'blob', ADOPTION_COMMIT + ':' + path.as_posix()),
        temp_root=paths()['temp'])


def load_phase_b_inputs(modules, manifest, *, before_readiness=True):
    """External state is digest-bound by committed adoption, not itself committed."""
    if BASE != modules['profile'].REPLACEMENT_RUNTIME_ROOT or ROOT != modules['profile'].ROOT:
        stop('replacement placement mismatch')
    record = committed_blob(modules, manifest, ADOPTION_DIR / 'payload-pin.adopted.json')
    adoption_raw = committed_blob(modules, manifest, ADOPTION_DIR / 'owner-adoption.json')
    if len(record) != 319 or digest(record) != PIN_SHA or digest(adoption_raw) != ADOPTION_SHA:
        stop('committed adoption identity')
    if (regular(ROOT / ADOPTION_DIR / 'payload-pin.adopted.json') != record
            or regular(ROOT / ADOPTION_DIR / 'owner-adoption.json') != adoption_raw):
        stop('adoption working bytes changed')
    adoption = json.loads(adoption_raw)
    if (adoption['status'] != 'OWNER_ADOPTED' or adoption['record_sha256'] != PIN_SHA
            or adoption['record_bytes'] != 319 or adoption['evaluation_id'] != EVALUATION
            or adoption['pair_id'] != PAIR or adoption['phase_a_state_sha256'] != STATE_SHA):
        stop('adoption binding')
    state_raw = regular(BASE / 'phase-a.json')
    if digest(state_raw) != STATE_SHA:
        stop('Phase A state identity')
    state = json.loads(state_raw)
    if (state['evaluation_id'] != EVALUATION or state['pair_id'] != PAIR
            or state['payload_record_sha256'] != PIN_SHA or state['payload_record_bytes'] != 319
            or state['ledger_sha256'] != adoption['verified_ledger_sha256']):
        stop('state/adoption binding')
    if regular(BASE / 'payload-pin.candidate.json') != record:
        stop('candidate changed')
    git, repo = context(modules, manifest)
    bound = modules['binding'].load_replacement_ledger_binding(git=git, repository=repo,
        temp_root=paths()['temp'], expected_binding_sha256=state['binding_sha256'],
        expected_evaluation_id=EVALUATION)
    verify_zero(modules, state, bound=bound)
    # Actual fixed filename comes from the committed-state digest, not caller input.
    checkpoint = Path(state['checkpoint_path'])
    if checkpoint.parent != paths()['controller'] or checkpoint.resolve(strict=True) != checkpoint:
        stop('checkpoint placement')
    if tuple(paths()['controller'].iterdir()) != (checkpoint,):
        stop('controller already started')
    regular(checkpoint)
    if before_readiness and (tuple(paths()['execution'].iterdir()) or (BASE / 'readiness-result.json').exists()):
        stop('readiness already started; no resume')
    return state, bound, record


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




def execution_catalog(runner):
    return runner.ToolCatalog.project((runner.ToolDescriptor("command_execution"), runner.ToolDescriptor("file_change")))


def build_readiness_window(modules, manifest, state, bound, record):
    if not HOME.is_dir() or HOME.resolve(strict=True) != HOME:
        stop('dedicated Codex HOME missing or noncanonical; provision separately')
    for entry in (HOME, *HOME.parents):
        if getattr(entry.lstat(), 'st_file_attributes', 0) & 0x400:
            stop('redirected Codex HOME')
    runner, runtime, material = modules['runner'], modules['runtime'], modules['material']
    adopted = material.PinnedExecutable(ROOT / ADOPTION_DIR / 'payload-pin.adopted.json', len(record), state['payload_record_sha256'])
    owner_pin = runner.OwnerPayloadPin(adopted, state['evaluation_id'], state['pair_id'], 'R2-SHAKEDOWN')
    # Resolve and hash installed payload AFTER adoption. Never reuse Phase A observation.
    codex = runner.resolve_codex_payload(owner_pin=owner_pin)
    quiescence = runtime.WindowsCodexRuntimeQuiescence(temp_root=paths()['temp'])
    quiescence()
    runner._windows_process_identity().validate(OWNER)
    verify_zero(modules, state, bound=bound)
    git, repo = context(modules, manifest)
    authority = modules['binding'].load_input_authority(git=git,repository=repo,temp_root=paths()['temp'])
    pin = modules['profile']
    events = modules['ledger'].read_ledger(ROOT/pin.REPLACEMENT_LEDGER_PATH)
    pair_binding = modules['attempt'].PairBinding(state['evaluation_id'], state['pair_id'],
        'R2-SHAKEDOWN', events[1]['category'], authority.repository, authority.pair_identities(), authority)
    p = paths()
    boundary = modules['custody'].CustodyBoundary(ROOT,p['consumer'],p['materialization'],p['execution'],p['scoring'])
    lock = modules['attempt'].PairLedgerLock(ledger_path=ROOT/pin.REPLACEMENT_LEDGER_PATH,
        lock_path=p['execution']/'pair.lock',binding=pair_binding,expected_ledger_sha256=state['ledger_sha256'])
    order = runtime.SealedArmOrder.from_sealed_package(Path(state['checkpoint_path']),key_path=p['keys']/'controller-key.json',
        custody_boundary=boundary,expected_digest=state['sealed_package_digest'],pair_lock=lock)
    modules['binding'].verify_replacement_custody(controller_root=p['controller'], key_path=p['keys']/'controller-key.json', custody_boundary=boundary)
    dirs = {name:p['execution']/name for name in ('provision-workspace','provision-output','qualification-workspace','qualification-output')}
    for directory in dirs.values(): directory.mkdir(exist_ok=False)
    catalog = execution_catalog(runner)
    identity = runner.RuntimeIdentity('gpt-5.6-sol','high','UNAVAILABLE_NOT_INDEPENDENTLY_ATTESTED',
        'sha256:'+codex.sha256,'host-bound-by-exclusive-window',runner.IDENTITY_DISPOSITION)
    generation = lambda: runner.capture_sandbox_generation(codex_home=HOME,temp_root=p['temp'])
    native = runner.NativeCodexExecBackend(executable=codex,configured_catalog=catalog,expected_launcher_sid=OWNER,owner_payload_pin=owner_pin)
    who = manifest['executables']['whoami']; whoami=material.PinnedExecutable(Path(who['path']),who['bytes'],who['sha256'])
    backend = runtime.NativePreExposureObservationBackend(native_backend=native,codex_home=HOME,
        provisioning_workspace=dirs['provision-workspace'],provisioning_output=dirs['provision-output'],
        qualification_workspace=dirs['qualification-workspace'],qualification_output=dirs['qualification-output'],
        whoami=whoami,runtime_identity=identity,
        boundary_producer=runtime.PreExposureBoundaryEvidenceProducer(evidence_path=p['execution']/'pre-exposure-boundary.v3.json'),
        boundary_probe=runtime.MachineBackedBoundaryProbe(off_host_control_endpoint=runtime.OffHostControlEndpoint('192.168.31.1',443),
            credential_sentinel_path=HOME/'.sandbox-secrets/qualification-credential-sentinel.txt'),generation_probe=generation)
    adapter=runner.CodexRunnerAdapter(executable=codex,backend=backend,expected_catalog=catalog,codex_home=HOME,
        temp_root=p['temp'],sandbox_generation_probe=generation,expected_launcher_sid=OWNER)
    repository_probe=modules['de'].DisposableRepositoryFreezeProbe(git=git,repository=repo,temp_root=p['temp'])
    freeze_probe=runtime.RuntimeFreezeProbe(backend=native,repository_probe=repository_probe,qualification_helper=whoami,
        generation_probe=generation,pair_lock=lock,assert_runtime_quiescent=quiescence)
    ps=manifest['executables']['powershell'];powershell=material.PinnedExecutable(Path(ps['path']),ps['bytes'],ps['sha256'])
    leaves=material.LeafWorkspaceManager.for_windows_runtime(p['materialization'],powershell=powershell,launcher_sid=OWNER,
        generation_probe=generation,credentials_denied=lambda observed: backend.require_boundary_evidence().credential_sentinel_visible is False and observed==generation(),temp_root=p['temp'])
    mat=modules['dm'].DisposableGitMaterializer(authority=authority,git=git,repository=repo,leaves=leaves,
        packet=material.TreatmentInstruction.load(ROOT/'artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md'))
    window=runtime.PreAttemptFrozenRuntimeWindow(backend=backend,adapter=adapter,freeze_probe=freeze_probe,materializer=mat,pair_lock=lock,sealed_order=order)
    return window, boundary, p


def execution_transition(modules, manifest, state, window, readiness, boundary, p, bound):
    """One controller-local authorization; never reconstructed from saved JSON."""
    original_state = canonical(state)
    issued = getattr(window, '_issued_readiness', None)
    if issued is None or issued[0] is not readiness:
        stop('missing live readiness provenance')
    command = 'EXECUTE ' + state['evaluation_id'] + ' ' + state['pair_id'] + ' ' + secrets.token_hex(16)
    consumed = False

    def execute(answer, current_window, current_readiness):
        nonlocal consumed
        if consumed:
            stop('authorization already consumed')
        if answer != command:
            return False
        consumed = True  # A failed authorized transition is not retryable.
        if (current_window is not window or current_readiness is not readiness
                or getattr(window, '_issued_readiness', None) is not issued
                or issued[0] is not readiness or getattr(window, '_readiness_consumed', False)):
            stop('lost or reconstructed live handoff')
        objects = (window.backend, window.adapter, window.freeze_probe,
            window.materializer, window.pair_lock, window.sealed_order,
            window.backend.native_backend, window.materializer.leaves)
        if len(issued[3]) != len(objects) or any(a is not b for a, b in zip(objects, issued[3])):
            stop('live runtime objects changed')
        current, current_bound, record = load_phase_b_inputs(modules, manifest, before_readiness=False)
        if canonical(current) != original_state or current_bound.raw != bound.raw:
            stop('execution state drift')
        runner, material = modules['runner'], modules['material']
        owner_pin = runner.OwnerPayloadPin(material.PinnedExecutable(
            ROOT / ADOPTION_DIR / 'payload-pin.adopted.json', len(record), PIN_SHA),
            current['evaluation_id'], current['pair_id'], 'R2-SHAKEDOWN')
        runner.resolve_codex_payload(owner_pin=owner_pin)
        write_once(p['execution'] / 'owner-execution-authorization.json', canonical(dict(
            authority_source='explicit external-terminal owner input; not independently signed',
            exact_input=answer, evaluation_id=current['evaluation_id'], pair_id=current['pair_id'],
            scope='both replacement arms only; no oracle/scoring/unblinding')))
        execution = modules['de'].DisposableArmExecution(window=window,
            controller_root=p['controller'], scoring_root=p['scoring'],
            key_path=p['keys']/'controller-key.json', custody_boundary=boundary,
            expected_genesis_binding_sha256=current['binding_sha256'],
            expected_order_sha256=current['sealed_package_digest'], replacement_binding=current_bound)
        execution.run(previously_verified_readiness=readiness)
        return True
    return command, execute


def wait_for_owner(state, window, readiness, boundary, p, bound, transition):
    """Keep live references; only exact one-use input invokes the existing API."""
    command, execute = transition
    print('Awaiting owner execution authorization. Blank input does NOT exit.', flush=True)
    print('Both replacement arms only; no oracle/scoring/unblinding. ABORT or Ctrl+C stops.', flush=True)
    print(command, flush=True)
    while True:
        try:
            answer = input()
        except EOFError:
            time.sleep(1)
            continue
        if answer == 'ABORT':
            stop('explicit owner abort; live handoff discarded')
        if execute(answer, window, readiness):
            print('ARM_EXECUTION_RETURNED / STOP; no scoring or effectiveness claim.', flush=True)
            return
        print('Not authorized. Still waiting.', flush=True)


def phase_b(modules, manifest):
    state, bound, record = load_phase_b_inputs(modules, manifest)
    window, boundary, p = build_readiness_window(modules, manifest, state, bound, record)
    readiness = window.run()
    verify_zero(modules, state, bound=bound)
    if (readiness.disposition != modules['runtime'].READY_BEFORE_ATTEMPT
            or readiness.task_exposure_state != 'NONE' or readiness.attempt_handle is not None):
        stop('readiness boundary')
    write_once(BASE / 'readiness-result.json', canonical(dict(
        status=readiness.disposition, evaluation_id=state['evaluation_id'], pair_id=state['pair_id'],
        attempt=0, task_exposure_state='NONE',
        claim='readiness only; historical evidence cannot resume live handoff')))
    print(readiness.disposition, 'PAUSE — Attempt 0; exposure NONE.', flush=True)
    transition = execution_transition(modules, manifest, state, window, readiness, boundary, p, bound)
    wait_for_owner(state, window, readiness, boundary, p, bound, transition)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--mode', choices=['check', 'phase-a', 'phase-b'], required=True)
    args = parser.parse_args()
    manifest, modules = bootstrap(args.manifest_sha256)
    if args.mode == 'check':
        print('STATIC_BINDINGS_PASS; no creation, credentials, or readiness invoked')
    elif args.mode == 'phase-a':
        phase_a(modules, manifest)
    else:
        phase_b(modules, manifest)


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
