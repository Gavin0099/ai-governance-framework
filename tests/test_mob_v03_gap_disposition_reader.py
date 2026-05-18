"""
MOB Verifier v0.3 — gap_disposition_reader.py failure condition tests.

Test-first order per spec Section 10 Step 1:
  Failure conditions are locked before happy path.
  All tests use in-memory fixtures — no real ndjson or YAML files required.

Failure modes covered:
  FM-01  reader has no YAML write path (code inspection)
  FM-02  disposition=confirmed + empty rationale → needs_more_evidence
  FM-03  consequence_eligible=true + disposition≠confirmed → validation error
  FM-05  reader opens ndjson read-only; no write operations on Layer 1/2
  *      unmatched observed_gap_id → disposition_pending=true, consequence_eligible=false
"""
from __future__ import annotations

import inspect
import json
import re
import stat
import textwrap
from pathlib import Path

import pytest

from governance_tools.gap_disposition_reader import (
    derive_status_records,
    load_observations,
    load_yaml_annotations,
    validate_annotation,
    write_status_report,
)


# ── Fixture helpers ───────────────────────────────────────────────────────────


def _write_ndjson(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    return path


def _write_yaml(path: Path, entries: list[dict]) -> Path:
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": "1.0", "entries": entries}
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _gap_obs(
    *,
    mob_id: str = "MOB-05",
    observed_gap_id: str = "hearth::2026-05-07::MOB-05::pkg/supabase",
    trigger_path: str = "pkg/supabase",
) -> dict:
    return {
        "record_type": "gap_observed",
        "mob_id": mob_id,
        "observed_gap_id": observed_gap_id,
        "date": "2026-05-07",
        "trigger_path": trigger_path,
        "trigger_commit": "abc1234",
        "pre_convention": False,
        "reconstruction_ambiguous": False,
    }


def _annotation(
    *,
    mob_id: str = "MOB-05",
    observed_gap_id: str = "hearth::2026-05-07::MOB-05::pkg/supabase",
    disposition: str = "needs_more_evidence",
    rationale: str = "Verified in git log — submodule bump with no memory update.",
    consequence_eligible: bool = False,
    reviewer: str = "GavinWu",
) -> dict:
    return {
        "mob_id": mob_id,
        "observed_gap_id": observed_gap_id,
        "source_artifact": "artifacts/observations/2026-05-07.ndjson",
        "reviewer": reviewer,
        "reviewed_at": "2026-05-18T00:00:00Z",
        "disposition": disposition,
        "rationale": rationale,
        "consequence_eligible": consequence_eligible,
    }


# ── FM-01: No YAML write path in reader source ───────────────────────────────


def test_fm01_reader_has_no_yaml_write_path() -> None:
    """FM-01: mob_verifier.py / gap_disposition_reader.py must not write YAML.

    Verifies by source inspection that the reader has no yaml.dump call and no
    open(..., 'w') call targeting the YAML layer. The reader is Layer 3 only —
    it must never write back to Layer 1 or Layer 2.
    """
    import governance_tools.gap_disposition_reader as mod
    source = inspect.getsource(mod)

    # No yaml.dump / yaml.safe_dump (write back to Layer 2)
    assert "yaml.dump" not in source, "FM-01: reader must not call yaml.dump"
    assert "yaml.safe_dump" not in source, "FM-01: reader must not call yaml.safe_dump"

    # load_yaml_annotations must use read mode
    load_ann_src = inspect.getsource(load_yaml_annotations)
    assert '"w"' not in load_ann_src and "'w'" not in load_ann_src, (
        "FM-01: load_yaml_annotations must not open files in write mode"
    )


# ── FM-02: confirmed + empty rationale → needs_more_evidence ─────────────────


def test_fm02_confirmed_with_empty_rationale_downgraded() -> None:
    entry = _annotation(disposition="confirmed", rationale="", consequence_eligible=False)
    result = validate_annotation(entry)
    assert result["disposition"] == "needs_more_evidence", (
        "FM-02: confirmed + empty rationale must be downgraded to needs_more_evidence"
    )
    assert result["consequence_eligible"] is False


def test_fm02_confirmed_with_whitespace_only_rationale_downgraded() -> None:
    entry = _annotation(disposition="confirmed", rationale="   ", consequence_eligible=False)
    result = validate_annotation(entry)
    assert result["disposition"] == "needs_more_evidence"
    assert result["consequence_eligible"] is False


def test_fm02_confirmed_with_real_rationale_kept() -> None:
    entry = _annotation(
        disposition="confirmed",
        rationale="Submodule bump at pkg/supabase on 2026-05-07. Verified in git log.",
        consequence_eligible=False,
    )
    result = validate_annotation(entry)
    assert result["disposition"] == "confirmed"


# ── FM-03: consequence_eligible=true + disposition≠confirmed → error ──────────


def test_fm03_eligible_true_with_rejected_raises() -> None:
    entry = _annotation(disposition="rejected", consequence_eligible=True)
    with pytest.raises(ValueError, match="FM-03"):
        validate_annotation(entry)


def test_fm03_eligible_true_with_needs_more_evidence_raises() -> None:
    entry = _annotation(disposition="needs_more_evidence", consequence_eligible=True)
    with pytest.raises(ValueError, match="FM-03"):
        validate_annotation(entry)


def test_fm03_eligible_true_with_confirmed_valid() -> None:
    entry = _annotation(
        disposition="confirmed",
        rationale="Verified genuine lineage gap.",
        consequence_eligible=True,
    )
    result = validate_annotation(entry)
    assert result["consequence_eligible"] is True
    assert result["disposition"] == "confirmed"


def test_fm03_eligible_false_with_rejected_valid() -> None:
    entry = _annotation(disposition="rejected", consequence_eligible=False)
    result = validate_annotation(entry)
    assert result["consequence_eligible"] is False


# ── FM-05: Reader opens ndjson read-only; no write to Layer 1 ─────────────────


def test_fm05_load_observations_source_uses_read_mode() -> None:
    """FM-05: load_observations must open ndjson in read mode only."""
    source = inspect.getsource(load_observations)
    # Must contain open(..., "r") or open(..., mode="r")
    has_read_open = re.search(r'open\s*\(.*?["\']r["\']', source)
    assert has_read_open, 'FM-05: load_observations must open files with mode "r"'
    # Must not contain open(..., "w")
    has_write_open = re.search(r'open\s*\(.*?["\']w["\']', source)
    assert not has_write_open, "FM-05: load_observations must not open files with write mode"


def test_fm05_read_only_ndjson_is_readable(tmp_path: Path) -> None:
    """FM-05: reader can read a read-only ndjson file (functional enforcement)."""
    ndjson = _write_ndjson(tmp_path / "obs.ndjson", [_gap_obs()])

    # Make file read-only (no write permission)
    ndjson.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    try:
        records = load_observations(ndjson)
        assert len(records) == 1
        assert records[0]["record_type"] == "gap_observed"
    finally:
        # Restore permissions so tmp_path cleanup works
        ndjson.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_fm05_write_status_report_is_only_permitted_write(tmp_path: Path) -> None:
    """FM-05: only write_status_report may produce output; it targets Layer 3 only."""
    import governance_tools.gap_disposition_reader as mod
    source = inspect.getsource(mod)

    # The only .write_text call in the module should be in write_status_report
    write_text_calls = re.findall(r"\.write_text\s*\(", source)
    assert len(write_text_calls) == 1, (
        f"FM-05: exactly one .write_text() expected (in write_status_report), "
        f"found {len(write_text_calls)}"
    )

    # That write_text should only appear inside write_status_report
    write_fn_src = inspect.getsource(write_status_report)
    assert ".write_text(" in write_fn_src


# ── Unmatched observed_gap_id → disposition_pending ───────────────────────────


def test_unmatched_gap_id_produces_disposition_pending() -> None:
    obs = [_gap_obs(observed_gap_id="hearth::2026-05-07::MOB-05::pkg/supabase")]
    annotations: list[dict] = []  # no YAML entries

    records = derive_status_records(obs, annotations)
    assert len(records) == 1
    r = records[0]
    assert r["disposition"] is None
    assert r["consequence_eligible"] is False
    assert r.get("disposition_pending") is True


def test_unmatched_gap_never_consequence_eligible() -> None:
    obs = [_gap_obs(observed_gap_id="hearth::2026-05-07::MOB-01::apps/web/db/migrations")]
    # Annotation exists but for a different gap_id → still unmatched for MOB-01
    annotations = [_annotation(observed_gap_id="hearth::2026-05-07::MOB-05::pkg/supabase")]

    records = derive_status_records(obs, annotations)
    assert records[0]["consequence_eligible"] is False
    assert records[0].get("disposition_pending") is True


# ── Happy path: matched, confirmed, consequence_eligible ──────────────────────


def test_matched_confirmed_gap_is_consequence_eligible(tmp_path: Path) -> None:
    ndjson = _write_ndjson(
        tmp_path / "obs.ndjson",
        [_gap_obs(observed_gap_id="hearth::2026-05-07::MOB-05::pkg/supabase")],
    )
    yaml_file = _write_yaml(
        tmp_path / "disposition.yaml",
        [
            _annotation(
                observed_gap_id="hearth::2026-05-07::MOB-05::pkg/supabase",
                disposition="confirmed",
                rationale="Verified genuine lineage gap in git log.",
                consequence_eligible=True,
            )
        ],
    )
    output = tmp_path / "gap_status_report.json"

    from governance_tools.gap_disposition_reader import run
    result = run(ndjson_path=ndjson, yaml_path=yaml_file, output_path=output)

    assert result["observation_count"] == 1
    assert result["annotation_count"] == 1
    assert result["record_count"] == 1

    payload = json.loads(output.read_text(encoding="utf-8"))
    rec = payload["records"][0]
    assert rec["disposition"] == "confirmed"
    assert rec["consequence_eligible"] is True
    assert "disposition_pending" not in rec


def test_no_yaml_file_all_pending(tmp_path: Path) -> None:
    ndjson = _write_ndjson(tmp_path / "obs.ndjson", [_gap_obs(), _gap_obs(mob_id="MOB-01",
        observed_gap_id="hearth::2026-05-07::MOB-01::apps/web/db/migrations")])
    yaml_file = tmp_path / "nonexistent.yaml"
    output = tmp_path / "out.json"

    from governance_tools.gap_disposition_reader import run
    result = run(ndjson_path=ndjson, yaml_path=yaml_file, output_path=output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert all(r["consequence_eligible"] is False for r in payload["records"])
    assert all(r.get("disposition_pending") is True for r in payload["records"])
