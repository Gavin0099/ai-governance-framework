from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from governance_tools.memory_reconciliation import (
    MemoryRecordBytes,
    detect_exact_byte_duplicate,
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
