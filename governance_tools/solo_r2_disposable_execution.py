"""One-shot disposable Pair-to-arm integration; calling requires owner execution authority.

No CLI, creation, oracle execution, scoring or unblinding is performed here.
Existing runtime readiness and native containment remain mandatory.
"""

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import time

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_disposable_binding as binding
from governance_tools import solo_r2_disposable_profile as profile
from governance_tools import solo_r2_lifecycle_integration as lifecycle
from governance_tools import solo_r2_pair_creation as pairs
from governance_tools import solo_r2_attempt_materialization as material
from governance_tools.solo_r2_attempt_execution import PreAttemptExecutionCoordinator
from governance_tools.solo_r2_disposable_materialization import DisposableGitMaterializer
from governance_tools.solo_r2_runtime_window import (PreAttemptFrozenRuntimeWindow, GitRepositoryFreezeProbe,
    PreAttemptRuntimeReadiness, READY_BEFORE_ATTEMPT)
from governance_tools.solo_r2_codex_runner import derive_trace_metrics

SCORING_ADOPTION_COMMIT = '7a23b95afa09485d8321b638227bf631e2ddad12'
SCORING_ADOPTION_PATH = 'memory/evidence/solo-r2-final-scoring-continuation-adoption-20260907/owner-adoption.json'
SCORING_ADOPTION_SHA256 = '6d93cbb66eafdb13d9da7a3572a263a3625faa60f2da01c032f8993a2e614066'


def load_scoring_continuation_authority(*, git, repository, temp_root):
    """Read the one prospective adoption; never infer historical custody."""
    root = binding._root(repository)
    material.verify_repository_binding(git, repository, temp_root=temp_root)
    raw = material._run_git(git, repository,
        ('--no-replace-objects', 'cat-file', 'blob',
         SCORING_ADOPTION_COMMIT + ':' + SCORING_ADOPTION_PATH), temp_root=temp_root)
    material._regular_unlinked_path(root / SCORING_ADOPTION_PATH)
    if (hashlib.sha256(raw).hexdigest() != SCORING_ADOPTION_SHA256
            or (root / SCORING_ADOPTION_PATH).read_bytes() != raw):
        _fail()
    return binding._json(raw)


def _continuation_inputs(record, root):
    """Verify every adopted artifact before opening any sealed mapping."""
    captured = {}
    def walk(value):
        if isinstance(value, dict):
            if {'path', 'bytes', 'sha256'} <= value.keys():
                path = Path(value['path'])
                if not path.is_absolute():
                    path = root / path
                if not (path.is_relative_to(root) or path.is_relative_to(profile.FINAL_RUNTIME_ROOT)):
                    _fail()
                material._regular_unlinked_path(path)
                raw = path.read_bytes()
                if len(raw) != value['bytes'] or hashlib.sha256(raw).hexdigest() != value['sha256']:
                    _fail()
                captured[path] = raw
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(record)
    if len(captured) != 22:
        _fail()
    return captured


def prepare_final_scoring_continuation(*, git, repository, temp_root):
    """OWNER-EXECUTION-ONLY. No CLI, scoring, unblinding, or arm resume.

    Calling consumes the prospective adoption to seal exactly once. Merely
    adopting inputs or importing this function never authorizes that operation.
    """
    record = load_scoring_continuation_authority(git=git, repository=repository, temp_root=temp_root)
    root = binding._root(repository)
    captured = _continuation_inputs(record, root)
    # Final creation binding has its own previously committed custody identity.
    bound = binding.load_final_ledger_binding(git=git, repository=repository,
        temp_root=temp_root, expected_binding_sha256='82fd9e09f9f83e02f2cc5183d0f97098e650ede893e9f723f3de9b9c4c55ae10',
        expected_evaluation_id=record['evaluation_id'])
    return _prepare_final_scoring(record, captured, bound, root)


def _prepare_final_scoring(record, captured, bound, root):
    if type(bound) is not binding.FinalLedgerBinding:
        _fail()
    base = profile.FINAL_RUNTIME_ROOT
    public = root / profile.FINAL_LEDGER_PATH
    prefix = captured[public]
    bound.verify(public, prefix)
    events = ledger.read_ledger(public)
    ledger.validate_ledger_events(events)
    if ([e['event_type'] for e in events] != ['V2_GENESIS', 'PAIR_CREATED'] +
            ['ATTEMPT_ADMITTED', 'TASK_EXPOSED', 'EXECUTION_TERMINAL'] * 2
            or events[0]['evaluation_id'] != record['evaluation_id']
            or events[1]['pair_id'] != record['pair_id']):
        _fail()
    pair = events[1]
    if (pair['frozen_identities'] != bound.input_authority.pair_identities()
            or record['frozen_rubric'] != bound.input_authority.document()['rubric']):
        _fail()
    boundary = controller.CustodyBoundary(root, *(base / n for n in
        ('consumer', 'materialization', 'execution', 'scoring')))
    key = base / 'keys/controller-key.json'
    binding.verify_final_custody(controller_root=base/'controller', key_path=key, custody_boundary=boundary)
    coord = _ScoringOnlyLifecycle(lifecycle._START_TOKEN, ledger_path=public,
        controller_root=base/'controller', scoring_root=base/'scoring', key_path=key,
        custody_boundary=boundary, evaluation_id=record['evaluation_id'], pair_id=record['pair_id'],
        category=pair['category'], repository=pair['repository'], frozen_identities=pair['frozen_identities'],
        preflight_ids=['R2_PRE_ID_EXECUTION_SURFACE_VALIDATED'], rubric_id=record['frozen_rubric']['sha256'])
    coord._pair_prefix = prefix
    coord._ledger_digest = hashlib.sha256(prefix).hexdigest()
    coord._replacement_binding = bound
    coord._captured = captured
    for path in (coord._bundle_path(), coord._checkpoint_path(controller.SCORING_BOUND)):
        if os.path.lexists(path):
            _fail()
    cp = record['attempt_bound_checkpoint']
    if Path(cp['path']) != coord._checkpoint_path(controller.ATTEMPT_BOUND):
        _fail()
    coord._checkpoint_digests[controller.ATTEMPT_BOUND] = cp['sha256']
    previous = coord._read_checkpoint(controller.ATTEMPT_BOUND)
    handles = [e['attempt_handle'] for e in events if e['event_type'] == 'ATTEMPT_ADMITTED']
    if [x['attempt_handle'] for x in previous['attempt_bindings']] != handles:
        _fail()
    # Preserve the existing evaluation-local collision boundary across handoff.
    coord._identifier_registry._seen.update(handles)
    coord._sealed_nonces.add(controller.parse_sealed_package(captured[Path(cp['path'])])['nonce_b64'])
    for handle, row, terminal in zip(handles, record['terminal_outputs'], (events[4], events[7])):
        if row['attempt_handle'] != handle or terminal.get('terminal_classification') is not None:
            _fail()
        def content(name):
            path = Path(row[name]['path'])
            return captured[path if path.is_absolute() else root/path]
        source = content('terminal_output')
        runtime = binding._json(content('runtime_evidence'))
        oracle = binding._json(content('verified_oracle'))
        if (runtime['source_sha256'] != hashlib.sha256(source).hexdigest()
                or runtime['runtime_result']['disposition'] != 'SUCCESS'
                or oracle['evaluation_id'] != record['evaluation_id'] or oracle['pair_id'] != record['pair_id']
                or oracle['attempt_handle'] != handle or oracle['output_sha256'] != runtime['source_sha256']
                or oracle['oracle_status'] != 'PASS' or oracle['passed_case_count'] != 10
                or oracle['required_case_count'] != 10):
            _fail()
        # No paths, handles, output hashes, traces or oracle internals enter payload.
        payload = json.dumps({'source': source.decode('utf-8'),
            'final_response': binding._json(content('final_message')),
            'correctness': {**terminal['correctness_result'], 'oracle_status': 'PASS', 'passed_case_count': 10},
            'cost': terminal['cost_metrics']}, ensure_ascii=True)
        if lifecycle.scoring_bundle._contains_scorer_forbidden_identity(payload):
            _fail()
        # Distinct preserved artifacts may have identical contents. This locator
        # stays sealed; never salt content hashes or expose custody to the scorer.
        output_ref = row['terminal_output']['path'] + '@sha256:' + row['terminal_output']['sha256']
        coord._terminal_outputs[handle] = (output_ref, payload)
    if len(coord._terminal_outputs) != 2:
        _fail()
    return coord.prepare_scoring()


class _ScoringOnlyLifecycle(lifecycle.SyntheticLifecycleCoordinator):
    """Private one-transition controller; never returned to a caller."""

    def _event_schema(self):
        return profile.SCHEMA

    def _append_event(self, event_type, **kwargs):
        if event_type != 'CONTROLLER_STATE_SEALED':
            _fail()
        for path, raw in self._captured.items():
            material._regular_unlinked_path(path)
            if path.read_bytes() != raw:
                _fail()
        actual = self._bundle_path().read_bytes()
        if actual != self._bundle_bytes:
            _fail()
        lifecycle.scoring_bundle.parse_blind_scoring_bundle(actual)
        self._read_checkpoint(controller.SCORING_BOUND)
        return super()._append_event(event_type, **kwargs)


def _fail():
    material._fail(material.PAIR_INVALID)


def _write_once(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        _fail()


class DisposableRepositoryFreezeProbe(GitRepositoryFreezeProbe):
    """Fixed active disposable sources, in addition to the unchanged legacy pins."""

    SOURCES = tuple('governance_tools/' + name + '.py' for name in (
        'solo_r2_disposable_materialization', 'solo_r2_disposable_execution',
        'solo_r2_disposable_binding', 'solo_r2_disposable_profile',
        'solo_r2_attempt_execution', 'solo_r2_lifecycle_integration',
        'solo_r2_runtime_window', 'solo_attempt_ledger_v2',
    ))

    def capture(self):
        original = super().capture()
        sources = tuple(self._blob(original.head_commit, path) for path in self.SOURCES)
        self.git.verify()
        return replace(original, disposable_sources=sources)


class DisposableLifecycle(lifecycle.SyntheticLifecycleCoordinator):
    """Attach only to the externally pinned, never-attempted disposable Pair."""

    @classmethod
    def start(cls, **kwargs):
        _fail()  # Never inherit synthetic genesis/Pair creation.

    def _event_schema(self):
        return profile.SCHEMA

    def _validated_events(self):
        raw = self._ledger_path.read_bytes()
        if (not raw.startswith(self._pair_prefix)
                or hashlib.sha256(raw).hexdigest() != self._ledger_digest):
            _fail()
        events, summary = super()._validated_events()
        if summary.schema_version != profile.SCHEMA:
            _fail()
        return events, summary

    def _append_event(self, event_type, **kwargs):
        self._validated_events()
        result = super()._append_event(event_type, **kwargs)
        self._ledger_digest = hashlib.sha256(self.ledger_path.read_bytes()).hexdigest()
        return result

    @classmethod
    def attach(cls, *, pair_lock, materializer, controller_root, scoring_root,
               key_path, custody_boundary, expected_genesis_binding_sha256,
               expected_order_sha256, replacement_binding=None):
        pair_lock.assert_unchanged()
        authority = materializer.authority
        data = materializer.verify_authority()
        if pair_lock.binding.input_authority != authority:
            _fail()
        root = binding._root(materializer.repository)
        replacement = replacement_binding is not None
        if replacement and type(replacement_binding) not in (binding.ReplacementLedgerBinding, binding.FinalLedgerBinding):
            _fail()
        final = type(replacement_binding) is binding.FinalLedgerBinding
        public = binding._fixed_path(root, replacement_binding.ledger_relative_path if replacement else profile.LEDGER_PATH)
        if replacement:
            replacement_binding.verify(public, public.read_bytes())
            (binding.verify_final_custody if final else binding.verify_replacement_custody)(controller_root=controller_root,
                key_path=key_path, custody_boundary=custody_boundary)
        if pair_lock.ledger_path != public or custody_boundary.governance_root != root:
            _fail()
        raw = public.read_bytes()
        events = ledger.read_ledger(public)
        ledger.validate_ledger_events(events)
        if len(events) != 2 or events[0]['schema_version'] != profile.SCHEMA:
            _fail()
        pair_lock.binding.validate_event(events[0], events[1])
        genesis_bytes = raw.splitlines(keepends=True)[0]
        bound = binding._fixed_path(root, replacement_binding.binding_relative_path if replacement else profile.BINDING_PATH).read_bytes()
        if (hashlib.sha256(bound).hexdigest() != expected_genesis_binding_sha256
                or binding._json(bound) != binding._binding(root, events[0], genesis_bytes, replacement=replacement and not final, final=final)):
            _fail()
        private = pairs._canonical_directory(controller_root, reject_alias=True)
        scorer = pairs._canonical_directory(scoring_root, reject_alias=True)
        roots = pairs._resolved_boundary_roots(custody_boundary)
        if (scorer != custody_boundary.scoring_root
                or any(pairs._is_within(private, r) or pairs._is_within(r, private) for r in roots)
                or pairs._is_within(Path(key_path).resolve(), private)
                or pairs._contains_git_marker(private)):
            _fail()
        instance = cls(lifecycle._START_TOKEN, ledger_path=public,
            controller_root=private, scoring_root=scorer, key_path=key_path,
            custody_boundary=custody_boundary, evaluation_id=events[0]['evaluation_id'],
            pair_id=events[1]['pair_id'], category=events[1]['category'],
            repository=authority.repository, frozen_identities=authority.pair_identities(),
            preflight_ids=['R2_PRE_ID_EXECUTION_SURFACE_VALIDATED'],
            rubric_id=data['rubric']['sha256'])
        instance._pair_prefix = raw
        instance._replacement_binding = replacement_binding
        instance._ledger_digest = hashlib.sha256(raw).hexdigest()
        checkpoint = instance._checkpoint_path(controller.ORDER_FROZEN)
        material._regular_unlinked_path(checkpoint)
        package = checkpoint.read_bytes()
        state = controller.open_controller_package(package, key_path=key_path,
            custody_boundary=custody_boundary, expected_digest=expected_order_sha256,
            expected_evaluation_id=instance._evaluation_id,
            expected_pair_id=instance._pair_id, expected_slot='R2-SHAKEDOWN')
        if state['state_phase'] != controller.ORDER_FROZEN or state['attempt_bindings']:
            _fail()
        for phase in (controller.ATTEMPT_BOUND, controller.SCORING_BOUND):
            if os.path.lexists(instance._checkpoint_path(phase)):
                _fail()
        if os.path.lexists(instance._bundle_path()):
            _fail()
        instance._checkpoint_digests[controller.ORDER_FROZEN] = expected_order_sha256
        instance._sealed_nonces.add(controller.parse_sealed_package(package)['nonce_b64'])
        instance._validated_events()
        pair_lock.assert_unchanged()
        # Durable no-resume marker is never deleted, including failures before exposure.
        _write_once(private / (instance._pair_token()+'.execution-started'), raw)
        return instance


class DisposableArmExecution:
    """Run the already-created Pair once, through the unchanged readiness window."""

    def __init__(self, *, window, controller_root, scoring_root, key_path,
                 custody_boundary, expected_genesis_binding_sha256,
                 expected_order_sha256, replacement_binding=None):
        self._validate_wiring(window, custody_boundary)
        self.window = window
        self.attach_args = dict(controller_root=controller_root, scoring_root=scoring_root,
            key_path=key_path, custody_boundary=custody_boundary,
            expected_genesis_binding_sha256=expected_genesis_binding_sha256,
            expected_order_sha256=expected_order_sha256)
        if replacement_binding is not None:
            self.attach_args['replacement_binding'] = replacement_binding
        self._used = False

    @staticmethod
    def _validate_wiring(window, custody_boundary):
        if (type(window) is not PreAttemptFrozenRuntimeWindow
                or type(window.materializer) is not DisposableGitMaterializer
                or type(window.freeze_probe.repository_probe) is not DisposableRepositoryFreezeProbe
                or window.freeze_probe.backend is not window.backend.native_backend
                or pairs._canonical_directory(window.materializer.leaves.root, reject_alias=True)
                != pairs._canonical_directory(custody_boundary.materialization_root, reject_alias=True)):
            _fail()

    def run(self, *, previously_verified_readiness=None):
        if self._used:
            _fail()
        self._used = True
        window = self.window
        readiness = previously_verified_readiness
        if (type(readiness) is not PreAttemptRuntimeReadiness
                or readiness.disposition != READY_BEFORE_ATTEMPT
                or readiness.task_exposure_state != 'NONE'
                or readiness.attempt_handle is not None
                or readiness.target_pair_attempt_events != 0):
            _fail()
        self._freeze = readiness.freeze
        mat = window.materializer
        with window.pair_lock:
            self._validate_wiring(window, self.attach_args['custody_boundary'])
            window.consume_readiness(readiness)
            identity = window.pair_lock.binding
            if (readiness.freeze.evaluation_id != identity.evaluation_id
                    or readiness.freeze.pair_id != identity.pair_id
                    or readiness.freeze.slot != identity.slot
                    or readiness.freeze.ledger_sha256 != window.pair_lock._digest
                    or readiness.materialization.input_authority != mat.authority):
                _fail()
            window.freeze_probe.assert_unchanged(readiness.freeze)
            current_validation = PreAttemptExecutionCoordinator(window.pair_lock).validate(
                materialization=readiness.materialization, canary=readiness.qualification,
                control=readiness.prepared_control, treatment=readiness.prepared_treatment)
            if current_validation != readiness.validation:
                _fail()
            coordinator = DisposableLifecycle.attach(pair_lock=window.pair_lock,
                materializer=mat, **self.attach_args)
            state = coordinator._read_checkpoint(controller.ORDER_FROZEN)
            if tuple(state['realized_order']) != window.sealed_order.order:
                _fail()
            prepared = {'CONTROL': readiness.prepared_control, 'TREATMENT': readiness.prepared_treatment}
            for arm in state['realized_order']:
                self._one(coordinator, arm, prepared[arm])
            # Outputs are now persisted. Separate oracle/scorer operations own judgments.
            return coordinator

    def _one(self, coordinator, arm, prepared):
        window = self.window
        mat = window.materializer
        handle = None
        leaf = None
        started = None
        output = None
        try:
            task = mat.task_bytes()  # Controller-only; never written to a leaf.
            leaf = mat.materialize(f'{coordinator._pair_id}-execution-{prepared.arm_ordinal}')
            if (leaf.acl.sandbox_principal != prepared.sandbox_principal
                    or leaf.acl.sandbox_account_generation != prepared.sandbox_account_generation):
                _fail()
            prepared.execution_policy.validate()
            window.backend.native_backend.executable.verify()
            window.freeze_probe.assert_execution_unchanged(self._freeze, coordinator)
            handle = coordinator.admit_attempt()
            output = coordinator._controller_root / handle
            output.mkdir(exist_ok=False)
            prompt = task if arm == 'CONTROL' else task + b'\n' + mat.packet.payload
            window.freeze_probe.assert_execution_unchanged(self._freeze, coordinator)
            coordinator.expose_task(handle)
            # No backend sees a prompt until TASK_EXPOSED is durable.
            started = time.monotonic()
            result = window.backend.native_backend.execute(prepared_arm=prepared,
                workspace_root=leaf.path, codex_home=window.backend.codex_home,
                output_root=output, prompt=prompt,
                output_schema={'type': 'object', 'properties': {'summary': {'type': 'string'}},
                               'required': ['summary'], 'additionalProperties': False},
                allow_non_git_workdir=True)
            elapsed = int((time.monotonic() - started) * 1000)
            PreAttemptExecutionCoordinator.validate_terminal_execution(prepared_arm=prepared, result=result)
            inventory = material.workspace_inventory(leaf.path)
            original = {item['path'].rsplit('/',1)[1]: item for item in mat.authority.document()['base_snapshot']['files']}
            if {row[0] for row in inventory} != set(original):
                _fail()
            for name in original:
                material._regular_unlinked_path(leaf.path / name)
                raw = (leaf.path / name).read_bytes()
                # The digest-bound disposable task permits this source and its
                # existing regression test; never generalize to test_* paths.
                if name not in {'queue_range.py', 'test_queue_range.py'}:
                    mat._verify_blob(raw, original[name])
            patch = (leaf.path / 'queue_range.py').read_bytes()
            _write_once(output / 'queue_range.py', patch)
            evidence = dict(input_authority_sha256=profile.INPUT_SHA256,
                snapshot_tree=mat.authority.document()['base_snapshot']['tree_oid'],
                task_sha256=hashlib.sha256(task).hexdigest(),
                source_sha256=hashlib.sha256(patch).hexdigest(),
                runtime_result={k: str(v) if isinstance(v, Path) else v for k,v in asdict(result).items()})
            _write_once(output / 'runtime-evidence.json', json.dumps(evidence, sort_keys=True).encode()+b'\n')
            coordinator.record_terminal(handle,
                correctness_result={'oracle_status':'NOT_RUN', 'required_case_count':10,
                    'passed_case_count':0, 'regression_status':'NOT_EVALUATED', 'scope_status':'WITHIN_SCOPE'},
                cost_metrics={'elapsed_ms':elapsed, 'tool_calls':result.tool_call_count},
                output_ref=hashlib.sha256(patch).hexdigest(),
                output_payload=json.dumps({'source':patch.decode('utf-8', errors='strict')}, ensure_ascii=True))
        except BaseException as failure:
            try:
                if handle is not None:
                    events = ledger.read_ledger(coordinator.ledger_path)
                    state = coordinator._attempt_states(events).get(handle)
                    if state == 'ADMITTED':
                        coordinator.record_admitted_not_exposed(handle)
                    elif state == 'TASK_EXPOSED':
                        self._record_exposed_failure(coordinator, handle, output, started, failure)
            finally:
                coordinator._stopped = True
            raise
        finally:
            if leaf is not None:
                mat.leaves.release(leaf)

    @staticmethod
    def _record_exposed_failure(coordinator, handle, output, started, failure):
        """Retain the failure before terminal append; never retry or invent costs."""
        costs = {}
        if started is not None:
            costs['elapsed_ms'] = max(0, int((time.monotonic()-started)*1000))
        try:
            material._regular_unlinked_path(output/'codex-trace.jsonl')
            metrics = derive_trace_metrics((output/'codex-trace.jsonl').read_bytes())
            costs['tool_calls'] = metrics.tool_call_count
        except Exception:
            pass  # Missing/unparseable trace is not zero observed tool calls.
        evidence = dict(disposition='UNCLASSIFIED', failure_type=type(failure).__name__,
            task_exposure_state='EXPOSED', cost_metrics=costs,
            unavailable_metrics=sorted({'elapsed_ms','tool_calls'}-costs.keys()),
            terminal_event_ready={'elapsed_ms','tool_calls'} <= costs.keys(),
            claim='No oracle, regression, scope or correctness judgment; no retry authorized')
        raw = json.dumps(evidence,sort_keys=True).encode()+b'\n'
        _write_once(output/'execution-failure.json',raw)
        if not evidence['terminal_event_ready']:
            return  # Retain evidence and re-raise original failure; do not invent required costs.
        # Failure accounting is not result sealing. Preserve the same validated
        # ledger boundary without inserting diagnostic prose into scoring inputs.
        coordinator._append_event('EXECUTION_TERMINAL', attempt_handle=handle,
            attempt_state='TERMINAL',
            correctness_result={'oracle_status':'NOT_RUN','required_case_count':10,
                'passed_case_count':0,'regression_status':'NOT_EVALUATED','scope_status':'NOT_EVALUATED'},
            cost_metrics=costs)
