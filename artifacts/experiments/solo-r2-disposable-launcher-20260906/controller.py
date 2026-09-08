"""Single disposable launcher; arms require explicit live terminal authorization."""
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
BASE = Path('D:/r2-disposable-shakedown-20260906')
HOME = Path('C:/Users/daish/.codex-r2-canary')
OWNER = 'S-1-5-21-4017902291-1272973841-664929404-1001'
HERE = Path(__file__).resolve().parent


def stop(message):
    raise RuntimeError('DISPOSABLE_LAUNCHER_STOP: ' + message)


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
    p = paths()
    # Quiescence runs before any allocation, key or durable runtime root creation.
    runtime = modules['runtime']
    runtime.WindowsCodexRuntimeQuiescence(temp_root=Path(os.environ['TEMP']))()
    modules['runner']._windows_process_identity().validate(OWNER)
    if os.path.lexists(BASE):
        stop('dedicated namespace already exists; no retry')
    check_pin(manifest['candidate_payload'])
    git, repo = context(modules, manifest)
    authority = modules['binding'].load_input_authority(
        git=git, repository=repo, temp_root=Path(os.environ['TEMP']))
    modules['de'].DisposableRepositoryFreezeProbe(
        git=git, repository=repo, temp_root=Path(os.environ['TEMP'])).capture()
    for relative in (modules['profile'].LEDGER_PATH, modules['profile'].BINDING_PATH):
        if (ROOT / relative).parent.exists():
            stop('disposable allocation already reserved')
    BASE.mkdir()
    for directory in p.values():
        directory.mkdir()
    boundary = modules['custody'].CustodyBoundary(
        ROOT, p['consumer'], p['materialization'], p['execution'], p['scoring'])
    key = p['keys'] / 'controller-key.json'
    commitment = p['commitments'] / 'sealed-package-digest.commitment'
    modules['pairs'].validate_replacement_targets(controller_root=p['controller'],
        key_path=key, commitment_path=commitment, custody_boundary=boundary)
    modules['custody'].create_controller_key(key, custody_boundary=boundary)
    creation = modules['binding'].create_disposable_evaluation(
        git=git, repository=repo, temp_root=p['temp'])
    public, genesis, verified = modules['binding'].validate_disposable_pair_preconditions(
        git=git, repository=repo, temp_root=p['temp'],
        expected_binding_sha256=creation.binding_sha256,
        expected_evaluation_id=creation.evaluation_id)
    if verified != authority:
        stop('authority changed')
    pair = modules['pairs'].create_disposable_shakedown_pair(
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
    state = dict(evaluation_id=creation.evaluation_id, pair_id=pair.pair_id,
        genesis_sha256=creation.genesis_sha256, binding_sha256=creation.binding_sha256,
        ledger_sha256=pair.ledger_sha256, sealed_package_digest=pair.sealed_package_digest,
        checkpoint_path=str(pair.checkpoint_path), payload_record_sha256=digest(record),
        payload_record_bytes=len(record), manifest_sha256=digest(regular(HERE/'manifest.json')))
    raw = canonical(state)
    write_once(BASE / 'phase-a.json', raw)
    verify_zero(modules, state)
    print('PHASE_A_COMPLETE / STOP — readiness NOT RUN; Attempt 0; exposure NONE')
    print(record.decode(), end='')
    print('PAYLOAD_RECORD_BYTES:', len(record), 'PAYLOAD_RECORD_SHA256:', digest(record))
    print('STATE_SHA256:', digest(raw))


def verify_zero(modules, state):
    public = ROOT / modules['profile'].LEDGER_PATH
    raw = regular(public)
    if digest(raw) != state['ledger_sha256']:
        stop('ledger changed')
    events = modules['ledger'].read_ledger(public)
    summary = modules['ledger'].validate_ledger_events(events)
    if len(events) != 2 or summary.admitted_attempt_count or summary.initiated_attempt_count:
        stop('nonzero Attempt or wrong ledger')
    if events[0]['evaluation_id'] != state['evaluation_id'] or events[1]['pair_id'] != state['pair_id']:
        stop('evaluation/Pair mismatch')
    binding = regular(ROOT / modules['profile'].BINDING_PATH)
    if digest(binding) != state['binding_sha256']:
        stop('genesis binding changed')
    if digest(raw.splitlines(keepends=True)[0]) != state['genesis_sha256']:
        stop('genesis bytes changed')


def adopt_record(state, answer, directory=None):
    directory = BASE if directory is None else directory
    raw = regular(directory / 'payload-pin.candidate.json')
    if digest(raw) != state['payload_record_sha256'] or len(raw) != state['payload_record_bytes']:
        stop('candidate changed')
    value = json.loads(raw)
    if canonical(value) != raw or value['evaluation_id'] != state['evaluation_id'] or value['pair_id'] != state['pair_id']:
        stop('canonical record/Pair mismatch')
    if answer != 'ADOPT ' + digest(raw):
        stop('owner did not adopt exact record')
    write_once(directory / 'payload-pin.adopted.json', raw)
    write_once(directory / 'payload-pin.owner-adoption.json', canonical(dict(
        authority_source='explicit external-terminal owner input; self-reported, not independent attestation',
        exact_input=answer, record_bytes=len(raw), record_sha256=digest(raw))))
    return raw


def load_state(modules, state_sha):
    raw = regular(BASE / 'phase-a.json')
    if digest(raw) != state_sha:
        stop('state identity; use exact Phase A displayed digest')
    state = json.loads(raw)
    if canonical(state) != raw or state['manifest_sha256'] != digest(regular(HERE/'manifest.json')):
        stop('state/launcher changed')
    verify_zero(modules, state)
    return state


def require_not_started():
    # Conservative: even preparation debris forbids refreshing this Pair.
    for name in ('execution', 'materialization', 'scoring', 'consumer'):
        directory = BASE/name
        if directory.resolve(strict=True) != directory or directory.is_symlink():
            stop('redirected runtime directory')
        if getattr(directory.stat(), 'st_file_attributes', 0) & 0x400 or any(directory.iterdir()):
            stop('readiness preparation already started')
    if os.path.lexists(BASE/'readiness-result.json'):
        stop('readiness already completed')


def old_adoption(state):
    raw = regular(BASE/'payload-pin.adopted.json')
    if digest(raw) != state['payload_record_sha256'] or len(raw) != state['payload_record_bytes']:
        stop('old adopted record changed')
    adoption = json.loads(regular(BASE/'payload-pin.owner-adoption.json'))
    if (adoption.get('record_sha256') != digest(raw) or adoption.get('record_bytes') != len(raw)
            or adoption.get('exact_input') != 'ADOPT '+digest(raw)):
        stop('old adoption mismatch')
    return json.loads(raw)


def refresh_candidate(modules, manifest, state_sha):
    state = load_state(modules, state_sha)
    require_not_started()
    previous = old_adoption(state)
    directory = BASE/'payload-pin-refresh'
    if os.path.lexists(directory):
        stop('refresh candidate already exists; preserve it')
    runner = modules['runner']
    root = runner._closed_directory(runner._windows_local_app_data_path()/'OpenAI'/'Codex'/'bin')
    candidates = []
    for child in sorted(root.iterdir()):
        child = runner._closed_directory(child)
        if runner._PAYLOAD_DIRECTORY_NAME.fullmatch(child.name) and (child/'codex.exe').exists():
            candidates.append(modules['material'].PinnedExecutable.capture(child/'codex.exe'))
    if len(candidates) != 1:
        stop('installed payload ambiguous or missing')
    payload = candidates[0]
    if (payload.byte_length, payload.sha256) == (previous['payload_byte_length'], previous['payload_sha256']):
        stop('payload unchanged; refresh not applicable')
    value = dict(previous, payload_byte_length=payload.byte_length, payload_sha256=payload.sha256)
    raw = canonical(value)
    verify_zero(modules, state)
    require_not_started()
    payload.verify()
    directory.mkdir()
    write_once(directory/'payload-pin.candidate.json', raw)
    write_once(directory/'refresh-binding.json', canonical(dict(
        state_sha256=state_sha, previous_record_sha256=state['payload_record_sha256'],
        candidate_sha256=digest(raw), candidate_bytes=len(raw),
        disposition='PROPOSED_SUPERSESSION_BY_PAYLOAD_CHANGE; not adopted')))
    print(raw.decode(), end='')
    print('REFRESHED_PIN_SHA256:', digest(raw), 'BYTES:', len(raw))
    print('STOP — same Pair; candidate only; readiness NOT RUN; owner adoption required')


def archive_readiness(state):
    archive = BASE/'historical-readiness-live-continuity-lost'
    if os.path.lexists(archive):
        stop('controlled readiness rerun already reserved')
    result = regular(BASE/'readiness-result.json')
    if digest(result) != '1f9459c281ae507ed19b16d47d153e3b8ae3f0b2c36872d68f94220e2bfde244':
        stop('reviewed historical readiness bytes changed')
    value = json.loads(result)
    if (value.get('evaluation_id') != state['evaluation_id'] or value.get('pair_id') != state['pair_id']
            or value.get('status') != 'R2_READY_BEFORE_ATTEMPT_HANDLE_CREATION'
            or value.get('attempt') != 0 or value.get('task_exposure_state') != 'NONE'):
        stop('historical readiness identity mismatch')
    names = ('execution','materialization','scoring','consumer','temp')
    # Verify every resolved target before any move. Keys/controller are excluded.
    for name in names:
        path = BASE/name
        if path.resolve(strict=True) != path or not path.is_dir() or getattr(path.stat(),'st_file_attributes',0) & 0x400:
            stop('noncanonical archive target')
    if archive.parent.resolve(strict=True) != BASE:
        stop('noncanonical archive parent')
    archive.mkdir()
    for name in names:
        (BASE/name).rename(archive/name)
        (BASE/name).mkdir()
    (BASE/'readiness-result.json').rename(archive/'readiness-result.json')
    write_once(archive/'disposition.json',canonical(dict(
        disposition='HISTORICAL_READINESS_PASS / NOT_CONSUMABLE_FOR_EXECUTION',
        reason='live continuity lost',readiness_sha256=digest(result),
        evaluation_id=state['evaluation_id'],pair_id=state['pair_id'])))


def await_execution(modules, state, window, readiness, boundary, p):
    nonce = secrets.token_hex(16)
    command = 'EXECUTE '+state['pair_id']+' '+nonce
    print('Awaiting owner execution authorization. Blank input does NOT exit.')
    print('This authorizes both CONTROL/TREATMENT arms only; no oracle/scoring/unblinding.')
    print(command, flush=True)
    while True:
        try:
            answer = input().strip()
        except EOFError:
            stop('terminal disconnected; no execution authorization received')
        if answer == command:
            break
        print('Not authorized. Still waiting; Ctrl+C stops without execution.', flush=True)
    verify_zero(modules,state)
    write_once(p['execution']/'owner-execution-authorization.json',canonical(dict(
        authority_source='explicit external-terminal owner input; not independently attested',
        exact_input=answer,evaluation_id=state['evaluation_id'],pair_id=state['pair_id'],
        scope='both disposable arms only; no oracle scoring or unblinding')))
    execution = modules['de'].DisposableArmExecution(window=window,
        controller_root=p['controller'],scoring_root=p['scoring'],key_path=p['keys']/'controller-key.json',
        custody_boundary=boundary,expected_genesis_binding_sha256=state['binding_sha256'],
        expected_order_sha256=state['sealed_package_digest'])
    execution.run(previously_verified_readiness=readiness)
    print('ARM_EXECUTION_RETURNED / STOP — inspect terminal evidence; no scoring or effectiveness claim.')


def execution_catalog(runner):
    return runner.ToolCatalog.project((runner.ToolDescriptor('command_execution'), runner.ToolDescriptor('file_change')))


def phase_b(modules, manifest, state_sha, refreshed_pin_sha=None, controlled_rerun=False):
    state = load_state(modules, state_sha)
    directory = BASE
    if refreshed_pin_sha is not None:
        if not controlled_rerun:
            require_not_started()
        previous = old_adoption(state)
        directory = BASE/'payload-pin-refresh'
        record = regular(directory/'payload-pin.candidate.json')
        binding = json.loads(regular(directory/'refresh-binding.json'))
        expected = dict(state_sha256=state_sha, previous_record_sha256=state['payload_record_sha256'],
            candidate_sha256=digest(record), candidate_bytes=len(record),
            disposition='PROPOSED_SUPERSESSION_BY_PAYLOAD_CHANGE; not adopted')
        value = json.loads(record)
        if binding != expected or digest(record) != refreshed_pin_sha or canonical(value) != record:
            stop('refresh binding mismatch')
        if {k:v for k,v in value.items() if k not in ('payload_byte_length','payload_sha256')} != {k:v for k,v in previous.items() if k not in ('payload_byte_length','payload_sha256')}:
            stop('refresh changed Pair or record schema')
        state = dict(state, payload_record_sha256=digest(record), payload_record_bytes=len(record))
    record = regular(directory/'payload-pin.candidate.json')
    if controlled_rerun:
        if refreshed_pin_sha is None:
            stop('controlled rerun requires explicit refreshed adopted pin')
        adopted_bytes = regular(directory/'payload-pin.adopted.json')
        adoption = json.loads(regular(directory/'payload-pin.owner-adoption.json'))
        if (adopted_bytes != record or adoption.get('record_sha256') != digest(record)
                or adoption.get('record_bytes') != len(record) or adoption.get('exact_input') != 'ADOPT '+digest(record)):
            stop('existing refreshed adoption mismatch')
        # No second execution context may attach to already-started controller state.
        if tuple(paths()['controller'].iterdir()) != (Path(state['checkpoint_path']),):
            stop('execution already started')
    else:
        print('Review the ENTIRE canonical record below; adoption does not authorize Attempts:')
        print(record.decode(), end='')
        print('Bytes:', len(record), 'SHA256:', digest(record))
        print('STOP — type ADOPT followed by the full record SHA256, or Enter to stop.')
        adopt_record(state, input().strip(), directory)
    if refreshed_pin_sha is not None and not controlled_rerun:
        write_once(directory/'supersession.json', canonical(dict(
            previous_record_sha256=binding['previous_record_sha256'],
            adopted_record_sha256=refreshed_pin_sha, state_sha256=state_sha,
            previous_disposition='SUPERSEDED_BY_PAYLOAD_CHANGE',
            current_disposition='OWNER_ADOPTED; runtime payload verification still required')))
    runner, runtime, material = modules['runner'], modules['runtime'], modules['material']
    adopted = material.PinnedExecutable(directory/'payload-pin.adopted.json', len(record), state['payload_record_sha256'])
    owner_pin = runner.OwnerPayloadPin(adopted, state['evaluation_id'], state['pair_id'], 'R2-SHAKEDOWN')
    # Resolve and hash installed payload AFTER adoption. Never reuse Phase A observation.
    codex = runner.resolve_codex_payload(owner_pin=owner_pin)
    quiescence = runtime.WindowsCodexRuntimeQuiescence(temp_root=paths()['temp'])
    quiescence()
    runner._windows_process_identity().validate(OWNER)
    verify_zero(modules, state)
    git, repo = context(modules, manifest)
    authority = modules['binding'].load_input_authority(git=git,repository=repo,temp_root=paths()['temp'])
    if controlled_rerun:
        modules['de'].DisposableRepositoryFreezeProbe(git=git,repository=repo,temp_root=paths()['temp']).capture()
    pin = modules['profile']
    events = modules['ledger'].read_ledger(ROOT/pin.LEDGER_PATH)
    pair_binding = modules['attempt'].PairBinding(state['evaluation_id'], state['pair_id'],
        'R2-SHAKEDOWN', events[1]['category'], authority.repository, authority.pair_identities(), authority)
    p = paths()
    boundary = modules['custody'].CustodyBoundary(ROOT,p['consumer'],p['materialization'],p['execution'],p['scoring'])
    lock = modules['attempt'].PairLedgerLock(ledger_path=ROOT/pin.LEDGER_PATH,
        lock_path=p['execution']/'pair.lock',binding=pair_binding,expected_ledger_sha256=state['ledger_sha256'])
    order = runtime.SealedArmOrder.from_sealed_package(Path(state['checkpoint_path']),key_path=p['keys']/'controller-key.json',
        custody_boundary=boundary,expected_digest=state['sealed_package_digest'],pair_lock=lock)
    if controlled_rerun:
        archive_readiness(state)
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
    readiness=window.run()
    verify_zero(modules,state)
    if readiness.disposition!=runtime.READY_BEFORE_ATTEMPT or readiness.task_exposure_state!='NONE' or readiness.attempt_handle is not None:
        stop('readiness boundary')
    write_once(BASE/'readiness-result.json',canonical(dict(status=readiness.disposition,evaluation_id=state['evaluation_id'],
        pair_id=state['pair_id'],attempt=0,task_exposure_state='NONE',claim='readiness only; not transferable execution authority')))
    print(readiness.disposition, 'PAUSE — Attempt 0; exposure NONE.')
    # Preserve the real in-process objects; JSON is not a resume token.
    global LIVE_WINDOW, LIVE_READINESS
    LIVE_WINDOW, LIVE_READINESS = window, readiness
    if controlled_rerun:
        await_execution(modules,state,window,readiness,boundary,p)
    else:
        input('Leave this controller open. Enter closes it and discards in-process handoff; no resume is provided: ')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--mode',choices=['check','phase-a','phase-b','refresh-payload-pin-candidate','controlled-readiness-and-wait'],required=True)
    parser.add_argument('--state-sha256')
    parser.add_argument('--refreshed-pin-sha256')
    args=parser.parse_args()
    manifest,modules=bootstrap(args.manifest_sha256)
    if args.mode=='check':
        print('STATIC_BINDINGS_PASS; no creation, credentials, or readiness invoked')
    elif args.mode=='phase-a': phase_a(modules,manifest)
    elif args.state_sha256 and args.mode=='refresh-payload-pin-candidate': refresh_candidate(modules,manifest,args.state_sha256)
    elif args.state_sha256: phase_b(modules,manifest,args.state_sha256,args.refreshed_pin_sha256,args.mode=='controlled-readiness-and-wait')
    else: stop('Phase B requires Phase A state digest')


if __name__=='__main__':
    try: main()
    except BaseException as exc:
        if isinstance(exc,SystemExit): raise
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)
