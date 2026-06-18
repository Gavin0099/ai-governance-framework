from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from governance_tools.runtime_ledger_export import (
    EXPORT_ROOT,
    LEDGER_SOURCES,
    build_manifest,
    run_export,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_REL, INDEX_REL = LEDGER_SOURCES


def _write_ledger(root: Path, rel: str, lines: list[str]) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _manifest(root: Path) -> dict:
    m, _ = build_manifest(
        project_root=root,
        export_id="export-test",
        export_reason="test",
        reviewer_scope="test",
        include_raw=False,
    )
    return m


# 1. both source ledgers absent
def test_both_absent_records_absence_not_fabricated(tmp_path: Path) -> None:
    m, warnings = build_manifest(
        project_root=tmp_path, export_id="e", export_reason="r",
        reviewer_scope="s", include_raw=False,
    )
    assert m["source_present"][RECEIPTS_REL] is False
    assert m["source_present"][INDEX_REL] is False
    assert m["source_sha256"][RECEIPTS_REL] is None
    assert m["source_record_count"][INDEX_REL] is None
    assert any("source absent" in w for w in warnings)


# 2. one present, one absent
def test_one_present_one_absent(tmp_path: Path) -> None:
    _write_ledger(tmp_path, RECEIPTS_REL, ['{"a": 1}', '{"b": 2}'])
    m = _manifest(tmp_path)
    assert m["source_present"][RECEIPTS_REL] is True
    assert m["source_record_count"][RECEIPTS_REL] == 2
    assert m["source_present"][INDEX_REL] is False


# 3. both present
def test_both_present_hashes_and_counts(tmp_path: Path) -> None:
    _write_ledger(tmp_path, RECEIPTS_REL, ['{"a": 1}'])
    _write_ledger(tmp_path, INDEX_REL, ['{"s": 1}', '{"s": 2}', '{"s": 3}'])
    m = _manifest(tmp_path)
    assert m["source_present"][RECEIPTS_REL] is True
    assert m["source_present"][INDEX_REL] is True
    assert m["source_record_count"][INDEX_REL] == 3
    assert len(m["source_sha256"][RECEIPTS_REL]) == 64  # sha256 hex


# 4. malformed ndjson line reported, not silent success
def test_malformed_line_reported(tmp_path: Path) -> None:
    _write_ledger(tmp_path, RECEIPTS_REL, ['{"ok": 1}', '{bad json'])
    m, warnings = build_manifest(
        project_root=tmp_path, export_id="e", export_reason="r",
        reviewer_scope="s", include_raw=False,
    )
    assert m["source_record_count"][RECEIPTS_REL] == 1  # only the valid line counts
    assert m["source_line_count"][RECEIPTS_REL] == 2
    assert any("parse failure" in w for w in warnings)


# 5. manifest hashes and counts stable across runs on same input
def test_hashes_and_counts_stable(tmp_path: Path) -> None:
    _write_ledger(tmp_path, INDEX_REL, ['{"s": 1}', '{"s": 2}'])
    m1 = _manifest(tmp_path)
    m2 = _manifest(tmp_path)
    assert m1["source_sha256"][INDEX_REL] == m2["source_sha256"][INDEX_REL]
    assert m1["source_record_count"][INDEX_REL] == m2["source_record_count"][INDEX_REL] == 2


# 6. live ignored ledger files remain untouched by the exporter
def test_export_does_not_modify_live_ledgers(tmp_path: Path) -> None:
    _write_ledger(tmp_path, RECEIPTS_REL, ['{"a": 1}'])
    before = (tmp_path / RECEIPTS_REL).read_bytes()
    export_dir, _, _ = run_export(
        project_root=tmp_path, export_id="e", export_reason="r",
        reviewer_scope="s", include_raw=False,
    )
    after = (tmp_path / RECEIPTS_REL).read_bytes()
    assert before == after  # source untouched
    assert (export_dir / "manifest.json").is_file()
    assert (export_dir / "summary.md").is_file()
    # manifest-only mode: no raw snapshot copied
    assert not (export_dir / Path(RECEIPTS_REL).name).exists()
    # bundle is under the dedicated export root, distinct from live ledgers
    # (slash-agnostic: check path components, not the joined string).
    assert "runtime-ledger-exports" in export_dir.parts
    assert export_dir.parent == tmp_path / EXPORT_ROOT


# include-raw opt-in actually copies snapshots
def test_include_raw_copies_snapshot(tmp_path: Path) -> None:
    _write_ledger(tmp_path, RECEIPTS_REL, ['{"a": 1}'])
    export_dir, manifest, _ = run_export(
        project_root=tmp_path, export_id="e", export_reason="r",
        reviewer_scope="s", include_raw=True,
    )
    assert manifest["included_raw_snapshots"] is True
    assert (export_dir / Path(RECEIPTS_REL).name).is_file()


# exit codes: ordinary missing -> 0; strict missing -> non-zero (lesson from advisory exit-1)
def test_cli_missing_is_exit_0_strict_is_nonzero(tmp_path: Path) -> None:
    def _run(extra: list[str]) -> int:
        return subprocess.run(
            [sys.executable, "-m", "governance_tools.runtime_ledger_export",
             "--project-root", str(tmp_path), "--export-id", "e",
             "--reason", "t", "--format", "json", *extra],
            capture_output=True, text=True, cwd=REPO_ROOT,
        ).returncode

    assert _run([]) == 0           # ordinary missing ledgers: advisory, exit 0
    assert _run(["--strict"]) != 0  # strict mode: missing -> non-zero


# reviewer warning #1: strict must treat an unreadable (present but no hash)
# source as a hard failure, via structured detection (not warning-text matching).
def test_strict_unreadable_source_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    from governance_tools.runtime_ledger_export import main
    _write_ledger(tmp_path, RECEIPTS_REL, ['{"a": 1}'])
    _write_ledger(tmp_path, INDEX_REL, ['{"s": 1}'])  # present + readable
    orig_read = Path.read_bytes

    def boom(self: Path):
        if self.name.endswith("claim-enforcement-receipts.ndjson"):
            raise OSError("simulated unreadable")
        return orig_read(self)

    monkeypatch.setattr(Path, "read_bytes", boom)
    # one present-but-unreadable, one present-readable => not 'absent', is 'unreadable'
    rc = main(["--project-root", str(tmp_path), "--export-id", "e",
               "--reason", "t", "--strict", "--format", "json"])
    assert rc != 0  # structured detection catches unreadable under --strict
    rc_nonstrict = main(["--project-root", str(tmp_path), "--export-id", "e2",
                         "--reason", "t", "--format", "json"])
    assert rc_nonstrict == 0  # advisory by default


# reviewer warning #2: strict + malformed ndjson -> non-zero, with a warning emitted.
def test_strict_malformed_exits_nonzero_with_warning(tmp_path: Path) -> None:
    _write_ledger(tmp_path, RECEIPTS_REL, ['{"ok": 1}', '{bad json'])
    _write_ledger(tmp_path, INDEX_REL, ['{"s": 1}'])
    result = subprocess.run(
        [sys.executable, "-m", "governance_tools.runtime_ledger_export",
         "--project-root", str(tmp_path), "--export-id", "e", "--reason", "t",
         "--strict", "--format", "json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode != 0  # strict + malformed -> non-zero
    assert "parse failure" in result.stdout  # warning is emitted, not silent


# reviewer warning #3: --include-raw with a BOM'd source copies without crashing.
def test_include_raw_handles_bom_source(tmp_path: Path) -> None:
    p = tmp_path / RECEIPTS_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}\n')  # UTF-8 BOM prefix
    m = _manifest(tmp_path)
    assert m["source_record_count"][RECEIPTS_REL] == 1  # BOM-safe parse
    export_dir, _, _ = run_export(
        project_root=tmp_path, export_id="e", export_reason="r",
        reviewer_scope="s", include_raw=True,
    )
    copied = export_dir / Path(RECEIPTS_REL).name
    assert copied.is_file()
    assert '{"a": 1}' in copied.read_text(encoding="utf-8")  # content preserved, no crash


def test_manifest_has_all_required_fields(tmp_path: Path) -> None:
    required = {
        "export_id", "created_at_utc", "repo_head", "repo_branch", "export_reason",
        "reviewer_scope", "source_files", "source_present", "source_sha256",
        "source_line_count", "source_record_count", "included_raw_snapshots",
        "claim_ceiling_supported", "claim_ceiling_not_supported", "generated_by",
    }
    assert required <= set(_manifest(tmp_path).keys())
