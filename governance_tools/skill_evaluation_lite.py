"""Synthetic-only Lite wiring. No subprocess, model, sandbox or real allocation.

Later real integration must supply authorized arm evidence to the existing
future scoring consumer and send ONLY scorer_input to a fresh scorer context.
Neither real adapter is provided here. The built-in scorer is a fixture stub,
not an automated quality judge. Strict Solo R2 is not an execution dependency.
"""
import argparse
import hashlib
import json
import secrets
from pathlib import Path

from governance_tools import solo_r2_blind_scoring_bundle as blind
from governance_tools.solo_r2_future_scoring_consumer import (
    ScoringInput, prepare_scoring_delivery,
)

NA = 'NOT_ASSESSABLE'
DIMENSIONS = ('causal_explanation', 'regression_safety', 'patch_focus', 'evidence_quality')
CLAIMS = ('NON_COUNTED', 'SOLO_CONTROLLED', 'DECISION_SUPPORT_ONLY')
NOT_CLAIMED = ('OS-level scorer isolation', 'strict Solo R2 equivalence',
               'Formal/counted evidence', 'real Skill effectiveness',
               'production-ready real-model evaluation')
RUBRIC = b'Synthetic rubric: each dimension 0/1/2 with evidence; insufficient evidence is NOT_ASSESSABLE. Oracle correctness is separate.'


class LiteError(ValueError):
    pass


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True)+'\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise LiteError('Duplicate field')
        value[key] = item
    return value


def _parse(raw):
    try:
        return json.loads(raw, object_pairs_hook=_unique)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LiteError('Invalid JSON') from exc


def _available(row, dimension):
    if dimension == 'regression_safety':
        evidence = row['regression_evidence']
        return bool(evidence['test_source']) and any(
            e['version_binding'] == 'EXECUTED_FOR_CURRENT_VERSION'
            and e['execution_status'] == 'EXECUTED'
            and type(e['exit_code']) is int and bool(e['diagnostic'])
            for e in evidence['executions'])
    if dimension == 'patch_focus':
        return bool(row['source'])
    return bool(row['final_response'].get('summary'))


class LiteSession:
    """In-memory synthetic coordinator; byte snapshots never expose live state.

    Freeze is an immutable byte snapshot within this instance. There is no
    restore/resume interface or OS isolation claim. CLI archives the snapshot
    before invoking unblind; a later real adapter needs its own durable host.
    """
    def __init__(self, inputs_by_arm, *, rubric_bytes, run_id, synthetic):
        if type(synthetic) is not bool or type(run_id) is not str or not run_id:
            raise LiteError('Explicit run mode and identity required')
        self._synthetic = synthetic
        if type(inputs_by_arm) is not dict or set(inputs_by_arm) != {'CONTROL', 'TREATMENT'}:
            raise LiteError('Exactly two fixture arms required')
        # Synthetic opaque labels, deliberately unrelated to arm names or order.
        labels = (secrets.token_hex(32), secrets.token_hex(32))
        self._mapping = dict(zip(labels, ('CONTROL', 'TREATMENT')))
        delivery = prepare_scoring_delivery(
            inputs_by_label={key: inputs_by_arm[arm] for key, arm in self._mapping.items()},
            evaluation_id=run_id,
            pair_id='synthetic-lite-only' if synthetic else 'lite-only', slot='R2-SHAKEDOWN',
            rubric_id='synthetic-lite-rubric' if synthetic else 'lite-rubric', rubric_bytes=rubric_bytes,
            expected_rubric_sha256=digest(rubric_bytes), presentation_entropy=secrets.token_bytes(32))
        self._input = delivery.scorer_input_bytes
        # Consumer validates rubric/payloads. Opaque presentation keys are the
        # permitted 64-hex metadata, not free-text lifecycle identities.
        self._freeze = None
        self._opened = False

    @property
    def scorer_input(self):
        return self._input

    @property
    def frozen_scores(self):
        if self._freeze is None:
            raise LiteError('Scores not frozen')
        return self._freeze

    def freeze(self, response):
        if self._freeze is not None:
            raise LiteError('Already frozen')
        value = _parse(response)
        if type(value) is not dict or set(value) != {'scores'} or type(value['scores']) is not dict:
            raise LiteError('Quality scores only; oracle/mapping fields forbidden')
        rows = {r['presentation_key']: r for r in _parse(self._input)['outputs']}
        if set(value['scores']) != set(rows):
            raise LiteError('Both opaque scores required')
        for key, dimensions in value['scores'].items():
            if type(dimensions) is not dict or set(dimensions) != set(DIMENSIONS):
                raise LiteError('Exact rubric dimensions required')
            for name, rating in dimensions.items():
                if type(rating) is not dict or set(rating) != {'score', 'evidence'}:
                    raise LiteError('Score and evidence required')
                score = rating['score']
                if not (type(score) is int and score in (0, 1, 2) or score == NA):
                    raise LiteError('Out-of-rubric score')
                if type(rating['evidence']) is not str or not rating['evidence'].strip():
                    raise LiteError('Evidence explanation required')
                if blind._contains_scorer_forbidden_identity(rating['evidence']):
                    raise LiteError('Scorer identity leakage')
                if not _available(rows[key], name) and score != NA:
                    raise LiteError('Insufficient evidence must remain NOT_ASSESSABLE')
        frozen = encode({'scorer_input_sha256': digest(self._input), 'scores': value['scores']})
        self._freeze = frozen
        return frozen

    def unblind(self, *, authorized_freeze_sha256):
        if self._freeze is None:
            raise LiteError('Freeze both scores before unblinding')
        if self._opened or authorized_freeze_sha256 != digest(self._freeze):
            raise LiteError('Exact freeze authorization required; no replay')
        frozen = _parse(self._freeze)
        visible = {r['presentation_key']: r for r in _parse(self._input)['outputs']}
        arms = {}
        for key, arm in self._mapping.items():
            scores = frozen['scores'][key]
            values = [r['score'] for r in scores.values()]
            arms[arm] = {'presentation_key': key, 'quality': scores,
                         'quality_total': NA if NA in values else sum(values),
                         'oracle': visible[key]['correctness']}
        totals = [v['quality_total'] for v in arms.values()]
        comparison = 'NOT_DETERMINED' if NA in totals else (
            'EQUAL' if len(set(totals)) == 1 else max(arms, key=lambda a: arms[a]['quality_total']))
        report = {'result': ('LITE_SYNTHETIC_END_TO_END_WIRING_VALIDATED' if self._synthetic
                             else 'LITE_SCORES_UNBLINDED'),
                  'synthetic': self._synthetic, 'claim_ceiling': CLAIMS, 'not_claimed': NOT_CLAIMED,
                  'freeze_sha256': digest(self._freeze), 'arms': arms,
                  'quality_comparison': comparison}
        self._opened = True
        return encode(report)


class SyntheticLite(LiteSession):
    """Backwards-compatible fixture entry; never invokes a real adapter."""
    def __init__(self, inputs_by_arm):
        super().__init__(inputs_by_arm, rubric_bytes=RUBRIC,
                         run_id='00000000-0000-4000-8000-000000000001', synthetic=True)


def synthetic_inputs():
    """Fixed queue-range example; no real evaluation identity is generated."""
    payload = encode({'source':'def queue_range(entries, lower, upper):\n    return [e for e in entries if lower <= e[0] <= upper]',
                      'final_response':{'summary':'Inclusive endpoints; regression execution evidence unavailable.'},
                      'correctness':{'oracle_status':'PASS', 'passed_case_count':10,
                                     'required_case_count':10, 'regression_status':'NOT_EVALUATED'},
                      'cost':{'tool_calls':0}})
    trace = b''
    item = ScoringInput(payload, trace, digest(payload), digest(trace))
    return {'CONTROL': item, 'TREATMENT': item}


def synthetic_scorer(scorer_input):
    """Canned fixture ratings prove transport/order only, never quality judging."""
    scores = {}
    for row in _parse(scorer_input)['outputs']:
        scores[row['presentation_key']] = {
            name: {'score': 2 if _available(row, name) else NA,
                   'evidence': 'Synthetic fixture evidence only.' if _available(row, name)
                   else 'Required evidence absent; no score inferred from oracle.'}
            for name in DIMENSIONS}
    return encode({'scores': scores})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--authorize-synthetic-unblinding', action='store_true')
    args = parser.parse_args(argv)
    # Never overwrite or reuse a historical/output directory.
    args.output.mkdir(parents=True, exist_ok=False)
    session = SyntheticLite(synthetic_inputs())
    (args.output/'scorer-input.json').write_bytes(session.scorer_input)
    frozen = session.freeze(synthetic_scorer(session.scorer_input))
    (args.output/'scores-frozen.json').write_bytes(frozen)
    if (args.output/'scores-frozen.json').read_bytes() != frozen:
        raise LiteError('Freeze readback failed')
    if not args.authorize_synthetic_unblinding:
        print('SYNTHETIC_SCORES_FROZEN; unblinding not authorized')
        return 0
    report = session.unblind(authorized_freeze_sha256=digest(frozen))
    (args.output/'report.json').write_bytes(report)
    print('LITE_SYNTHETIC_END_TO_END_WIRING_VALIDATED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
