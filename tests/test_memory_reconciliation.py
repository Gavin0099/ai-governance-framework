from __future__ import annotations

import json
import re
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from governance_tools.memory_reconciliation import (
    KnowledgeIdentityObservation,
    MemoryRecordBytes,
    detect_exact_byte_duplicate,
    detect_knowledge_identity_collision,
    detect_memory_encoding_integrity,
    render_report_json,
)
from governance_tools.authority_loader import parse_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "memory_reconciliation_exact_duplicate"
MANIFEST = FIXTURE_ROOT / "fixture.json"
CONTRACT = (
    REPO_ROOT
    / "governance"
    / "MEMORY_RECONCILIATION_EXACT_BYTE_DETECTOR_CONTRACT.md"
)
ENCODING_CONTRACT = (
    REPO_ROOT
    / "governance"
    / "MEMORY_RECONCILIATION_ENCODING_INTEGRITY_CONTRACT.md"
)
IDENTITY_CONTRACT = (
    REPO_ROOT
    / "governance"
    / "MEMORY_RECONCILIATION_KNOWLEDGE_IDENTITY_CONTRACT.md"
)
AUTHORITY = REPO_ROOT / "governance" / "AUTHORITY.md"


def _detector_contract() -> dict[str, object]:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- mrcsp-m1a-exact-byte-detector:begin -->\s*"
        r"```json\s*(.*?)\s*```\s*"
        r"<!-- mrcsp-m1a-exact-byte-detector:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _encoding_contract() -> dict[str, object]:
    text = ENCODING_CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- mrcsp-m1b-encoding-integrity:begin -->\s*"
        r"```json\s*(.*?)\s*```\s*"
        r"<!-- mrcsp-m1b-encoding-integrity:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _identity_contract() -> dict[str, object]:
    text = IDENTITY_CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- mrcsp-m1b-knowledge-identity:begin -->\s*"
        r"```json\s*(.*?)\s*```\s*"
        r"<!-- mrcsp-m1b-knowledge-identity:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _fixture_records() -> tuple[MemoryRecordBytes, MemoryRecordBytes]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = MemoryRecordBytes(
        record_id="m0-source-record",
        surface="04_review_log",
        content=(FIXTURE_ROOT / manifest["source_path"]).read_bytes(),
    )
    candidate = MemoryRecordBytes(
        record_id="m0-candidate-record",
        surface="04_review_log",
        content=(FIXTURE_ROOT / manifest["candidate_path"]).read_bytes(),
    )
    return source, candidate


def test_detector_contract_is_registered_canonical_on_demand_authority() -> None:
    assert parse_frontmatter(CONTRACT) == {
        "audience": "agent-on-demand",
        "authority": "canonical",
        "can_override": False,
        "overridden_by": "AGENT.md",
        "default_load": "on-demand",
    }
    authority = AUTHORITY.read_text(encoding="utf-8")
    assert (
        "| `governance/MEMORY_RECONCILIATION_EXACT_BYTE_DETECTOR_CONTRACT.md` "
        "| agent-on-demand | canonical | false | AGENT.md | on-demand |"
    ) in authority


def test_normative_contract_matches_owner_authorized_done() -> None:
    assert _detector_contract() == {
        "contract_version": "mrcsp-exact-byte-detector.v0.1",
        "input_count": 2,
        "input_requirement": "distinct_identified_records_already_admitted_by_caller",
        "comparison": "raw_bytes_sha256",
        "finding_code": "duplicate_memory_entry",
        "finding_severity": "warning",
        "mode": "report_only",
        "equal_bytes_finding_count": 1,
        "different_bytes_finding_count": 0,
        "serialization": "utf8_sorted_compact_json_with_trailing_lf",
    }


def test_encoding_contract_is_registered_canonical_on_demand_authority() -> None:
    assert parse_frontmatter(ENCODING_CONTRACT) == {
        "audience": "agent-on-demand",
        "authority": "canonical",
        "can_override": False,
        "overridden_by": "AGENT.md",
        "default_load": "on-demand",
    }
    authority = AUTHORITY.read_text(encoding="utf-8")
    assert (
        "| `governance/MEMORY_RECONCILIATION_ENCODING_INTEGRITY_CONTRACT.md` "
        "| agent-on-demand | canonical | false | AGENT.md | on-demand |"
    ) in authority


def test_encoding_contract_matches_owner_authorized_done() -> None:
    assert _encoding_contract() == {
        "contract_version": "mrcsp-encoding-integrity.v0.1",
        "input_count": 1,
        "input_requirement": "one_caller_admitted_memory_record_bytes",
        "decoding": "utf8_strict",
        "finding_code": "memory_encoding_integrity_anomaly",
        "finding_reasons": ["invalid_utf8", "replacement_character_present"],
        "finding_severity": "warning",
        "mode": "report_only",
        "anomalous_input_finding_count": 1,
        "clean_input_finding_count": 0,
        "serialization": "utf8_sorted_compact_json_with_trailing_lf",
    }


def test_identity_contract_is_registered_canonical_on_demand_authority() -> None:
    assert parse_frontmatter(IDENTITY_CONTRACT) == {
        "audience": "agent-on-demand",
        "authority": "canonical",
        "can_override": False,
        "overridden_by": "AGENT.md",
        "default_load": "on-demand",
    }
    authority = AUTHORITY.read_text(encoding="utf-8")
    assert (
        "| `governance/MEMORY_RECONCILIATION_KNOWLEDGE_IDENTITY_CONTRACT.md` "
        "| agent-on-demand | canonical | false | AGENT.md | on-demand |"
    ) in authority


def test_identity_contract_matches_owner_authorized_done() -> None:
    assert _identity_contract() == {
        "contract_version": "mrcsp-knowledge-identity-collision.v0.1",
        "input_count": 2,
        "input_requirement": (
            "distinct_caller_admitted_knowledge_identity_observations"
        ),
        "comparison": "case_sensitive_exact_knowledge_id",
        "qualified_identity_namespace": "knowledge",
        "finding_code": "knowledge_identity_collision",
        "finding_severity": "warning",
        "mode": "report_only",
        "equal_identity_finding_count": 1,
        "different_identity_finding_count": 0,
        "serialization": "utf8_sorted_compact_json_with_trailing_lf",
    }


def _identity_observation(
    record_id: str,
    knowledge_id: str,
    surface: str = "03_knowledge_base",
) -> KnowledgeIdentityObservation:
    return KnowledgeIdentityObservation(
        record_id=record_id,
        surface=surface,
        knowledge_id=knowledge_id,
    )


def test_same_exact_knowledge_identity_produces_one_report_only_finding() -> None:
    observations = (
        _identity_observation("record-b", "T-012"),
        _identity_observation("record-a", "T-012", "03_decisions"),
    )

    report = detect_knowledge_identity_collision(observations)

    assert report == {
        "detector": "knowledge_identity_collision",
        "findings": [
            {
                "code": "knowledge_identity_collision",
                "knowledge_id": "T-012",
                "mode": "report_only",
                "namespace": "knowledge",
                "occurrences": 2,
                "qualified_identity": "knowledge:T-012",
                "record_ids": ["record-a", "record-b"],
                "severity": "warning",
                "surfaces": ["03_decisions", "03_knowledge_base"],
            }
        ],
        "mode": "report_only",
        "report_version": "mrcsp-knowledge-identity-collision.v0.1",
    }


@pytest.mark.parametrize("different_id", ["T-013", "t-012"])
def test_different_or_case_changed_identity_produces_zero_findings(
    different_id: str,
) -> None:
    observations = (
        _identity_observation("record-a", "T-012"),
        _identity_observation("record-b", different_id),
    )

    assert detect_knowledge_identity_collision(observations)["findings"] == []


def test_identity_report_is_order_independent_and_byte_stable() -> None:
    first = _identity_observation("record-a", "T-012")
    second = _identity_observation("record-b", "T-012", "03_decisions")

    forward = render_report_json(
        detect_knowledge_identity_collision((first, second))
    )
    reverse = render_report_json(
        detect_knowledge_identity_collision((second, first))
    )
    repeated = render_report_json(
        detect_knowledge_identity_collision((first, second))
    )

    assert forward == reverse == repeated
    assert forward.endswith(b"\n")
    assert b" " not in forward


@pytest.mark.parametrize(
    "observations, message",
    [
        (None, "KnowledgeIdentityObservation"),
        ((), "exactly two observations"),
        ((_identity_observation("record-a", "T-012"),), "exactly two observations"),
        (("bad", "input"), "KnowledgeIdentityObservation"),
        (
            (_identity_observation("record-a", "T-012"), object()),
            "KnowledgeIdentityObservation",
        ),
    ],
)
def test_identity_detector_rejects_invalid_collection_count_or_elements(
    observations: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        detect_knowledge_identity_collision(observations)  # type: ignore[arg-type]


def test_identity_detector_rejects_same_record_identity() -> None:
    observations = (
        _identity_observation("record-a", "T-012"),
        _identity_observation("record-a", "T-012", "03_decisions"),
    )

    with pytest.raises(ValueError, match="distinct records"):
        detect_knowledge_identity_collision(observations)


@pytest.mark.parametrize(
    "record_id, surface, knowledge_id, message",
    [
        ("", "03_knowledge_base", "T-012", "record_id"),
        ("record-a", "", "T-012", "surface"),
        ("record-a", "03_knowledge_base", "", "knowledge_id"),
        ("record-a", "03_knowledge_base", " T-012", "surrounding whitespace"),
        ("record-a", "03_knowledge_base", 12, "knowledge_id"),
    ],
)
def test_identity_detector_revalidates_forged_observation_invariants(
    record_id: object,
    surface: object,
    knowledge_id: object,
    message: str,
) -> None:
    forged = object.__new__(KnowledgeIdentityObservation)
    object.__setattr__(forged, "record_id", record_id)
    object.__setattr__(forged, "surface", surface)
    object.__setattr__(forged, "knowledge_id", knowledge_id)

    with pytest.raises(ValueError, match=message):
        detect_knowledge_identity_collision(
            (forged, _identity_observation("record-b", "T-012"))
        )


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (
            {
                "record_id": "",
                "surface": "03_knowledge_base",
                "knowledge_id": "T-012",
            },
            "record_id",
        ),
        (
            {
                "record_id": "record-a",
                "surface": "",
                "knowledge_id": "T-012",
            },
            "surface",
        ),
        (
            {
                "record_id": "record-a",
                "surface": "03_knowledge_base",
                "knowledge_id": " ",
            },
            "knowledge_id",
        ),
        (
            {
                "record_id": "record-a",
                "surface": "03_knowledge_base",
                "knowledge_id": "T-012 ",
            },
            "surrounding whitespace",
        ),
    ],
)
def test_identity_observation_constructor_fails_closed(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        KnowledgeIdentityObservation(**kwargs)  # type: ignore[arg-type]


def test_identity_detector_snapshots_each_observation_field_once() -> None:
    class ChangingObservation(KnowledgeIdentityObservation):
        def __getattribute__(self, name: str) -> object:
            if name in {"record_id", "surface", "knowledge_id"}:
                try:
                    counts = object.__getattribute__(self, "access_counts")
                except AttributeError:
                    return super().__getattribute__(name)
                counts[name] += 1
                if name == "knowledge_id" and counts[name] > 1:
                    return "T-999"
            return super().__getattribute__(name)

    changing = ChangingObservation(
        record_id="record-a",
        surface="03_knowledge_base",
        knowledge_id="T-012",
    )
    object.__setattr__(
        changing,
        "access_counts",
        {"record_id": 0, "surface": 0, "knowledge_id": 0},
    )

    report = detect_knowledge_identity_collision(
        (changing, _identity_observation("record-b", "T-012"))
    )

    assert report["findings"][0]["qualified_identity"] == "knowledge:T-012"
    assert changing.access_counts == {
        "record_id": 1,
        "surface": 1,
        "knowledge_id": 1,
    }


class _DeceptiveObservationSequence(Sequence[object]):
    def __init__(self, traversals: list[list[object]], reported_length: int = 2) -> None:
        self._traversals = traversals
        self._reported_length = reported_length
        self.iteration_count = 0

    def __len__(self) -> int:
        return self._reported_length

    def __getitem__(self, index: int) -> object:
        return self._traversals[0][index]

    def __iter__(self) -> Iterator[object]:
        traversal_index = min(self.iteration_count, len(self._traversals) - 1)
        self.iteration_count += 1
        return iter(self._traversals[traversal_index])


def test_identity_detector_rejects_len_iteration_count_disagreement() -> None:
    deceptive = _DeceptiveObservationSequence(
        [
            [
                _identity_observation("record-a", "T-012"),
                _identity_observation("record-b", "T-012"),
                _identity_observation("record-c", "T-012"),
            ]
        ],
        reported_length=2,
    )

    with pytest.raises(ValueError, match="exactly two observations"):
        detect_knowledge_identity_collision(deceptive)

    assert deceptive.iteration_count == 1


def test_identity_detector_rejects_invalid_materialized_element() -> None:
    deceptive = _DeceptiveObservationSequence(
        [[_identity_observation("record-a", "T-012"), "bad"]]
    )

    with pytest.raises(ValueError, match="KnowledgeIdentityObservation"):
        detect_knowledge_identity_collision(deceptive)

    assert deceptive.iteration_count == 1


def test_identity_detector_uses_only_the_first_sequence_traversal() -> None:
    deceptive = _DeceptiveObservationSequence(
        [
            [
                _identity_observation("record-a", "T-012"),
                _identity_observation("record-b", "T-012"),
            ],
            [
                _identity_observation("record-a", "T-012"),
                _identity_observation("record-b", "T-999"),
            ],
        ]
    )

    report = detect_knowledge_identity_collision(deceptive)

    assert len(report["findings"]) == 1
    assert report["findings"][0]["qualified_identity"] == "knowledge:T-012"
    assert deceptive.iteration_count == 1


class _RaisingIterationSequence(Sequence[object]):
    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> object:
        return _identity_observation(f"record-{index}", "T-012")

    def __iter__(self) -> Iterator[object]:
        raise RuntimeError("iteration failed")


class _RaisingGetitemSequence(Sequence[object]):
    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> object:
        if index == 0:
            return _identity_observation("record-a", "T-012")
        raise KeyError("getitem failed")


class _NonIteratorSequence(Sequence[object]):
    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> object:
        return _identity_observation(f"record-{index}", "T-012")

    def __iter__(self) -> Iterator[object]:
        return []  # type: ignore[return-value]


@pytest.mark.parametrize(
    "observations",
    [
        _RaisingIterationSequence(),
        _RaisingGetitemSequence(),
        _NonIteratorSequence(),
    ],
)
def test_identity_detector_converts_materialization_errors_to_value_error(
    observations: Sequence[object],
) -> None:
    with pytest.raises(ValueError, match="safely materializable"):
        detect_knowledge_identity_collision(observations)  # type: ignore[arg-type]


@pytest.mark.parametrize("missing_field", ["record_id", "surface", "knowledge_id"])
def test_identity_detector_rejects_forged_missing_fields(missing_field: str) -> None:
    forged = object.__new__(KnowledgeIdentityObservation)
    values = {
        "record_id": "record-a",
        "surface": "03_knowledge_base",
        "knowledge_id": "T-012",
    }
    for field_name, value in values.items():
        if field_name != missing_field:
            object.__setattr__(forged, field_name, value)

    with pytest.raises(ValueError, match="safely readable"):
        detect_knowledge_identity_collision(
            (forged, _identity_observation("record-b", "T-012"))
        )


def test_identity_detector_converts_dynamic_field_error_to_value_error() -> None:
    class RaisingObservation(KnowledgeIdentityObservation):
        def __getattribute__(self, name: str) -> object:
            state = object.__getattribute__(self, "__dict__")
            if name == "knowledge_id" and state.get("raise_on_access", False):
                raise RuntimeError("field access failed")
            return super().__getattribute__(name)

    raising = RaisingObservation(
        record_id="record-a",
        surface="03_knowledge_base",
        knowledge_id="T-012",
    )
    object.__setattr__(raising, "raise_on_access", True)

    with pytest.raises(ValueError, match="safely readable"):
        detect_knowledge_identity_collision(
            (raising, _identity_observation("record-b", "T-012"))
        )


def test_identity_detector_rejects_hostile_string_subclass() -> None:
    class HostileString(str):
        def strip(self, chars: str | None = None) -> str:
            raise RuntimeError("strip must not run")

    forged = object.__new__(KnowledgeIdentityObservation)
    object.__setattr__(forged, "record_id", "record-a")
    object.__setattr__(forged, "surface", "03_knowledge_base")
    object.__setattr__(forged, "knowledge_id", HostileString("T-012"))

    with pytest.raises(ValueError, match="knowledge_id"):
        detect_knowledge_identity_collision(
            (forged, _identity_observation("record-b", "T-012"))
        )


def _encoding_record(content: bytes) -> MemoryRecordBytes:
    return MemoryRecordBytes(
        record_id="encoding-record",
        surface="03_knowledge_base",
        content=content,
    )


def test_invalid_utf8_produces_exactly_one_report_only_finding() -> None:
    content = b"valid-prefix\xffinvalid-suffix"
    report = detect_memory_encoding_integrity(_encoding_record(content))

    assert report["mode"] == "report_only"
    assert report["findings"] == [
        {
            "code": "memory_encoding_integrity_anomaly",
            "digest": "45a3eef617adc0cf658e2d63493ea9198cdad142f7e71d9795b2fc9bc70b7864",
            "digest_algorithm": "sha256",
            "mode": "report_only",
            "reason": "invalid_utf8",
            "record_id": "encoding-record",
            "severity": "warning",
            "surface": "03_knowledge_base",
        }
    ]


@pytest.mark.parametrize("replacement_count", [1, 3])
def test_literal_replacement_characters_produce_exactly_one_finding(
    replacement_count: int,
) -> None:
    content = ("prefix" + "\ufffd" * replacement_count + "suffix").encode("utf-8")
    report = detect_memory_encoding_integrity(_encoding_record(content))

    assert len(report["findings"]) == 1
    assert report["findings"][0]["reason"] == "replacement_character_present"
    assert report["findings"][0]["mode"] == "report_only"
    assert report["findings"][0]["severity"] == "warning"


def test_clean_valid_utf8_produces_zero_encoding_findings() -> None:
    report = detect_memory_encoding_integrity(
        _encoding_record("乾淨的 UTF-8 memory".encode("utf-8"))
    )

    assert report["findings"] == []


def test_encoding_report_is_byte_stable_for_identical_input() -> None:
    record = _encoding_record(b"invalid\xff")

    first = render_report_json(detect_memory_encoding_integrity(record))
    second = render_report_json(detect_memory_encoding_integrity(record))

    assert first == second
    assert first.endswith(b"\n")


@pytest.mark.parametrize("record", [None, b"bytes", object()])
def test_encoding_detector_rejects_non_record_input(record: object) -> None:
    with pytest.raises(ValueError, match="MemoryRecordBytes"):
        detect_memory_encoding_integrity(record)  # type: ignore[arg-type]


def test_encoding_detector_empty_content_fails_closed() -> None:
    with pytest.raises(ValueError, match="content"):
        _encoding_record(b"")


@pytest.mark.parametrize(
    "record_id, surface, content, message",
    [
        ("", "03_knowledge_base", b"content", "record_id"),
        ("forged-record", "", b"content", "surface"),
        ("forged-record", "03_knowledge_base", b"", "content"),
        ("forged-record", "03_knowledge_base", "not-bytes", "content"),
    ],
)
def test_encoding_detector_revalidates_forged_record_invariants(
    record_id: str,
    surface: str,
    content: object,
    message: str,
) -> None:
    forged = object.__new__(MemoryRecordBytes)
    object.__setattr__(forged, "record_id", record_id)
    object.__setattr__(forged, "surface", surface)
    object.__setattr__(forged, "content", content)

    with pytest.raises(ValueError, match=message):
        detect_memory_encoding_integrity(forged)


def test_admitted_exact_byte_pair_produces_exactly_one_report_only_finding() -> None:
    report = detect_exact_byte_duplicate(_fixture_records())

    assert report["mode"] == "report_only"
    assert len(report["findings"]) == 1
    assert report["findings"][0] == {
        "code": "duplicate_memory_entry",
        "digest": "03b3ddb05dac25dc137041b0ebfa5d5f49dced98a57401e7d12d10e289ac111a",
        "digest_algorithm": "sha256",
        "mode": "report_only",
        "occurrences": 2,
        "record_ids": ["m0-candidate-record", "m0-source-record"],
        "severity": "warning",
        "surfaces": ["04_review_log", "04_review_log"],
    }


def test_one_byte_mutation_produces_zero_findings() -> None:
    source, candidate = _fixture_records()
    mutated = MemoryRecordBytes(
        record_id=candidate.record_id,
        surface=candidate.surface,
        content=candidate.content[:-1] + bytes([candidate.content[-1] ^ 1]),
    )

    assert detect_exact_byte_duplicate((source, mutated))["findings"] == []


def test_identical_input_produces_byte_stable_json() -> None:
    records = _fixture_records()

    first = render_report_json(detect_exact_byte_duplicate(records))
    second = render_report_json(detect_exact_byte_duplicate(records))

    assert first == second
    assert first.endswith(b"\n")
    assert b" " not in first


def test_input_order_does_not_change_json() -> None:
    source, candidate = _fixture_records()

    forward = render_report_json(detect_exact_byte_duplicate((source, candidate)))
    reverse = render_report_json(detect_exact_byte_duplicate((candidate, source)))

    assert forward == reverse


@pytest.mark.parametrize(
    "records, message",
    [
        ((), "exactly two records"),
        ((_fixture_records()[0],), "exactly two records"),
        (_fixture_records() + (_fixture_records()[0],), "exactly two records"),
    ],
)
def test_detector_rejects_wrong_record_count(
    records: tuple[MemoryRecordBytes, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        detect_exact_byte_duplicate(records)


@pytest.mark.parametrize(
    "records",
    [
        None,
        ("not-a-record", "also-not-a-record"),
        (_fixture_records()[0], object()),
    ],
)
def test_detector_rejects_invalid_collection_or_element_types(records: object) -> None:
    with pytest.raises(ValueError, match="MemoryRecordBytes"):
        detect_exact_byte_duplicate(records)  # type: ignore[arg-type]


def test_detector_rejects_same_record_identity() -> None:
    source, candidate = _fixture_records()
    same_identity = MemoryRecordBytes(
        record_id=source.record_id,
        surface=candidate.surface,
        content=candidate.content,
    )

    with pytest.raises(ValueError, match="distinct records"):
        detect_exact_byte_duplicate((source, same_identity))


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"record_id": "", "surface": "04_review_log", "content": b"x"}, "record_id"),
        ({"record_id": "record", "surface": "", "content": b"x"}, "surface"),
        ({"record_id": "record", "surface": "04_review_log", "content": b""}, "content"),
    ],
)
def test_record_input_fails_closed(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        MemoryRecordBytes(**kwargs)  # type: ignore[arg-type]
