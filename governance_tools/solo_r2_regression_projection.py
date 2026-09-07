"""Evidence-only projection for a separately authorized future scoring round.

No execution, scoring, custody writes, or historical round updates. Trace bytes
must be bound by the caller's authority, not hashed to manufacture an expected ID.
Only the existing queue-range unittest/readback command shapes are supported.
"""
import hashlib
import json
import re

from governance_tools.solo_r2_blind_scoring_bundle import (
    BlindScoringBundleError, _contains_scorer_forbidden_identity,
)


def _reject():
    raise BlindScoringBundleError() from None


def _command(text):
    # Remove only the transport wrapper, never arbitrary command/path content.
    match = re.fullmatch(
        r'"C:\\+Windows\\+System32\\+WindowsPowerShell\\+v1\.0\\+powershell\.exe" -Command ([\s\S]+)',
        text, re.IGNORECASE)
    if match:
        text = match[1]
        if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
            text = text[1:-1]
    return text.strip()


def project_regression_evidence(trace_bytes, *, expected_trace_sha256, expected_subject_source=None):
    """Retain observed test source and command diagnostics; never infer test PASS.

    execution_status describes command startup, not oracle correctness or a
    regression-safety score. Unrecognized/compound commands remain UNRESOLVED.
    """
    if (type(trace_bytes) is not bytes or type(expected_trace_sha256) is not str
            or not re.fullmatch('[0-9a-f]{64}', expected_trace_sha256)
            or hashlib.sha256(trace_bytes).hexdigest() != expected_trace_sha256):
        _reject()
    source = None
    source_current = False
    executions = []
    known = {'test_queue_range.py': None, 'queue_range.py': None}
    revision = 0
    starts = {}
    used_ids = set()
    versions = []
    integrity = True
    def version():
        if any(value is None for value in known.values()):
            return None
        # Internal only: content identity, never an event index or scorer join key.
        return hashlib.sha256(json.dumps(known, sort_keys=True).encode()).hexdigest()
    try:
        events = [json.loads(line) for line in trace_bytes.splitlines()]
        for event in events:
            item = event.get('item', {})
            phase = event.get('type')
            if phase not in ('item.started', 'item.updated', 'item.completed'):
                continue
            kind = item.get('type')
            if kind not in ('file_change', 'command_execution'):
                continue
            command = _command(item['command']) if kind == 'command_execution' else ''
            readback = re.fullmatch(
                r'Get-Content -Raw -LiteralPath \.\\+test_queue_range\.py'
                r'(?:; Get-Command python,python3,py -ErrorAction SilentlyContinue \| Format-Table -AutoSize)?', command)
            subject_readback = re.fullmatch(r'Get-Content -Raw -LiteralPath \.\\+queue_range\.py', command)
            simple = re.fullmatch(r'(python(?:3|\.exe)?|py) -m unittest(?: -v)?', command)
            safe_command = kind == 'command_execution' and (readback or subject_readback or simple)
            signature = (kind, item['command'] if kind == 'command_execution' else item.get('changes'))
            item_id = item.get('id')
            # All file-change events and non-allowlisted commands may mutate
            # relevant bytes. Invalidate at BOTH edges, including partial events.
            if not safe_command:
                known = dict.fromkeys(known)
                source_current = False
                revision += 1
            if phase == 'item.started':
                if type(item_id) is not str or not item_id or item_id in used_ids:
                    integrity = False
                else:
                    used_ids.add(item_id)
                    starts[item_id] = (signature, version(), revision)
                continue
            if phase == 'item.updated':
                if item_id not in starts or starts[item_id][0] != signature:
                    integrity = False
                continue
            started = starts.pop(item_id, None)
            paired = started is not None and started[0] == signature
            if not paired:
                integrity = False
            if kind == 'file_change':
                if not isinstance(item.get('changes'), list) or not item['changes']:
                    integrity = False
                continue
            output = item['aggregated_output']
            code = item['exit_code']
            if type(output) is not str or (code is not None and type(code) is not int):
                _reject()
            stable_read = paired and started[2] == revision and code == 0
            # Whole test-file stdout only: do not extract guessed snippets from
            # patches, prose, or a mixed stdout stream.
            if readback and output.startswith('import unittest') and output.rstrip().endswith('unittest.main()'):
                source = output
                source_current = True
                if known['test_queue_range.py'] != output:
                    revision += 1
                known['test_queue_range.py'] = output if stable_read else None
            elif readback:
                # A later read that cannot establish the complete current bytes
                # must not leave the previous successful observation current.
                known['test_queue_range.py'] = None
                source_current = False
                revision += 1
            if subject_readback:
                if known['queue_range.py'] != output:
                    revision += 1
                known['queue_range.py'] = output if stable_read else None
            if re.search(r'\b(?:python(?:3|\.exe)?|py)\s+-m\s+unittest\b', command):
                status = 'UNRESOLVED'
                if simple:
                    missing = simple[1] + " : The term '" + simple[1] + "' is not recognized"
                    if code is not None and code != 0 and output.startswith(missing) and 'CommandNotFoundException' in output:
                        status = 'NOT_EXECUTED'
                    elif re.search(r'(?m)^Ran \d+ tests? in .+$', output) and re.search(r'(?m)^(?:OK|FAILED \([^\n]+\))\r?$', output):
                        status = 'EXECUTED'
                executions.append(dict(command=command, execution_status=status,
                                       exit_code=code, diagnostic=output))
                versions.append(started[1] if paired and started[2] == revision
                                and simple and code is not None else None)
    except (ValueError, TypeError, KeyError, AttributeError):
        _reject()
    current = version()
    if not integrity or starts or (expected_subject_source is not None and known['queue_range.py'] != expected_subject_source):
        current = None
    for execution, observed in zip(executions, versions):
        binding = 'NOT_CONFIRMED'
        if execution['execution_status'] == 'EXECUTED' and observed and current:
            binding = ('EXECUTED_FOR_CURRENT_VERSION' if observed == current
                       else 'EXECUTED_FOR_STALE_VERSION')
        execution['version_binding'] = binding
    result = dict(test_source=source,
                  source_status=('OBSERVED_AFTER_LAST_RECORDED_CHANGE' if source_current
                                 else 'MISSING' if source is None else 'STALE_OBSERVATION'),
                  executions=executions,
                  execution_evidence_status='RECORDED' if executions else 'MISSING')
    if _contains_scorer_forbidden_identity(json.dumps(result)):
        _reject()
    return result


def project_scoring_input(base_payload, trace_bytes, *, expected_trace_sha256):
    """Future-round entry: enrich payload before the existing blind bundle builder.

    This is deliberately not called by the already-frozen continuation route.
    It neither changes correctness/cost nor scores the additional evidence.
    """
    payload = json.loads(base_payload)
    if type(payload) is not dict or set(payload) != {'source', 'final_response', 'correctness', 'cost'}:
        _reject()
    payload['regression_evidence'] = project_regression_evidence(
        trace_bytes, expected_trace_sha256=expected_trace_sha256,
        expected_subject_source=payload['source'])
    result = json.dumps(payload, ensure_ascii=True)
    if _contains_scorer_forbidden_identity(result):
        _reject()
    return result
