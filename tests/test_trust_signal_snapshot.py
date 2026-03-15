import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.trust_signal_snapshot import (
    build_trust_signal_snapshot,
    format_index,
    write_snapshot_bundle,
)


def test_build_trust_signal_snapshot_passes_on_repo_root():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    assert snapshot["ok"] is True
    assert snapshot["overview"]["release"]["ok"] is True
    assert snapshot["overview"]["auditor"]["ok"] is True


def test_write_snapshot_bundle_creates_latest_history_and_index(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    bundle = write_snapshot_bundle(snapshot, tmp_path / "status")

    assert Path(bundle["latest_json"]).is_file()
    assert Path(bundle["latest_txt"]).is_file()
    assert Path(bundle["latest_md"]).is_file()
    assert Path(bundle["history_json"]).is_file()
    assert Path(bundle["history_txt"]).is_file()
    assert Path(bundle["history_md"]).is_file()
    assert Path(bundle["index_md"]).is_file()

    latest_payload = json.loads(Path(bundle["latest_json"]).read_text(encoding="utf-8"))
    assert latest_payload["ok"] is True
    index_text = Path(bundle["index_md"]).read_text(encoding="utf-8")
    assert "[trust_signal_snapshot_index]" in index_text
    assert "release_version=v1.0.0-alpha" in index_text


def test_format_index_handles_empty_history(tmp_path):
    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    rendered = format_index(history_dir)

    assert "[trust_signal_snapshot_index]" in rendered
    assert "reports=0" in rendered
