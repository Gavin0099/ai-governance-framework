"""Future-round scoring input consumer; no historical replay or scorer launch.

The caller supplies already-authorized anonymous labels and expected identities.
This entry owns projection -> bundle -> scorer-input serialization. A future
round still needs its separate allocation, custody and execution authorization.
"""
from dataclasses import dataclass
import hashlib
import json

from governance_tools import solo_r2_blind_scoring_bundle as bundle
from governance_tools.solo_r2_regression_projection import project_scoring_input


@dataclass(frozen=True)
class ScoringInput:
    payload: bytes
    trace: bytes
    expected_payload_sha256: str
    expected_trace_sha256: str


@dataclass(frozen=True)
class ScoringDelivery:
    bundle_bytes: bytes
    scorer_input_bytes: bytes


def prepare_scoring_delivery(*, inputs_by_label, evaluation_id, pair_id, slot,
                             rubric_id, rubric_bytes, expected_rubric_sha256,
                             presentation_entropy):
    """Verify inputs, enrich both outputs, then deliver only rubric/opaque data.

    Expected digests must come from the caller's authority, not be recomputed
    from whatever files currently happen to exist. No filesystem side effects.
    """
    if (type(inputs_by_label) is not dict or len(inputs_by_label) != 2
            or type(rubric_bytes) is not bytes
            or hashlib.sha256(rubric_bytes).hexdigest() != expected_rubric_sha256):
        raise bundle.BlindScoringBundleError()
    projected = {}
    for label, item in inputs_by_label.items():
        if (type(item) is not ScoringInput or type(item.payload) is not bytes
                or hashlib.sha256(item.payload).hexdigest() != item.expected_payload_sha256):
            raise bundle.BlindScoringBundleError()
        projected[label] = project_scoring_input(item.payload, item.trace,
            expected_trace_sha256=item.expected_trace_sha256)
    value = bundle.build_blind_scoring_bundle(evaluation_id=evaluation_id,
        pair_id=pair_id, slot=slot, rubric_id=rubric_id,
        outputs_by_label=projected, presentation_entropy=presentation_entropy)
    encoded = bundle.encode_blind_scoring_bundle(value)
    decoded = bundle.parse_blind_scoring_bundle(encoded)
    # Metadata is retained in the bundle, never forwarded as scorer input.
    rubric = rubric_bytes.decode('utf-8')
    if bundle._contains_scorer_forbidden_identity(rubric):
        raise bundle.BlindScoringBundleError()
    visible = dict(rubric=rubric, outputs=[dict(presentation_key=row['presentation_key'],
        **json.loads(row['output_payload'])) for row in decoded['outputs']])
    return ScoringDelivery(encoded, (json.dumps(visible, ensure_ascii=True)+'\n').encode())
