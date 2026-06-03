"""CE-1C.2: dual-write — compact receipt written alongside raw claim-enforcement packet.

Validates:
- After run_session_end, claim-enforcement-receipts.ndjson exists.
- The receipt row has all CE-1B required fields.
- The raw claim-enforcement-check.json is still written (unchanged).
- Existing audit consumers are not broken (runtime_completeness_audit still
  expects raw packet path, which must still be present).
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.claim_enforcement_receipt_writer import CE1B_REQUIRED_FIELDS, validate_receipt_fields
from runtime_hooks.core.session_end import run_session_end


RECEIPTS_RELATIVE = "artifacts/claim-enforcement/claim-enforcement-receipts.ndjson"


@pytest.fixture
def tmp_project(tmp_path):
    """Minimal project root for dual-write tests."""
    (tmp_path / "memory").mkdir()
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def _base_contract(**overrides):
    contract = {
        "task": "CE-1C.2 dual-write test",
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "stateless",
    }
    contract.update(overrides)
    return contract


def _run(tmp_project):
    return run_session_end(
        project_root=tmp_project,
        session_id="ce1c2-test-session",
        runtime_contract=_base_contract(),
        summary="CE-1C.2 dual-write smoke test",
    )


# ---------------------------------------------------------------------------
# CE-1C.2: compact receipt is written
# ---------------------------------------------------------------------------


def test_compact_receipt_file_exists_after_session_end(tmp_project):
    _run(tmp_project)
    receipts = tmp_project / RECEIPTS_RELATIVE
    assert receipts.exists(), "claim-enforcement-receipts.ndjson not created by dual-write"


def test_compact_receipt_has_required_fields(tmp_project):
    _run(tmp_project)
    receipts = tmp_project / RECEIPTS_RELATIVE
    lines = receipts.read_text(encoding="utf-8").splitlines()
    assert lines, "receipts.ndjson is empty"
    row = json.loads(lines[-1])
    missing = validate_receipt_fields(row)
    assert missing == [], f"CE-1B fields missing from compact receipt: {missing}"


def test_compact_receipt_session_id_matches(tmp_project):
    _run(tmp_project)
    receipts = tmp_project / RECEIPTS_RELATIVE
    row = json.loads(receipts.read_text(encoding="utf-8").splitlines()[-1])
    assert row["session_id"] == "ce1c2-test-session"


def test_compact_receipt_is_valid_ndjson(tmp_project):
    _run(tmp_project)
    receipts = tmp_project / RECEIPTS_RELATIVE
    for line in receipts.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        assert isinstance(obj, dict)


# ---------------------------------------------------------------------------
# CE-1C.2: raw packet is still written (existing behaviour unchanged)
# ---------------------------------------------------------------------------


def test_raw_claim_enforcement_packet_still_written(tmp_project):
    # CE-1D.2: raw packet is now written to the runtime-ignored path.
    _run(tmp_project)
    raw_packet = (
        tmp_project
        / "artifacts"
        / "session"
        / "claim-enforcement"
        / "ce1c2-test-session"
        / "claim-enforcement-check.json"
    )
    assert raw_packet.exists(), "raw claim-enforcement-check.json was not written"


def test_raw_packet_is_valid_json(tmp_project):
    # CE-1D.2: raw packet is now written to the runtime-ignored path.
    _run(tmp_project)
    raw_packet = (
        tmp_project
        / "artifacts"
        / "session"
        / "claim-enforcement"
        / "ce1c2-test-session"
        / "claim-enforcement-check.json"
    )
    data = json.loads(raw_packet.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "enforcement_action" in data or "claim_source" in data


# ---------------------------------------------------------------------------
# CE-1C.2: receipt presence flag reflects raw packet state
# ---------------------------------------------------------------------------


def test_compact_receipt_presence_flag_true_when_packet_present(tmp_project):
    _run(tmp_project)
    receipts = tmp_project / RECEIPTS_RELATIVE
    row = json.loads(receipts.read_text(encoding="utf-8").splitlines()[-1])
    # After run_session_end, raw packet exists — presence must be True
    assert row["claim_enforcement_check_present"] is True
