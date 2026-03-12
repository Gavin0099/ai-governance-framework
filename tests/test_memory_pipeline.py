import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_pipeline.memory_promoter import promote_candidate
from memory_pipeline.session_snapshot import create_session_snapshot


@pytest.fixture
def local_memory_root():
    path = Path("tests") / "_tmp_memory_pipeline"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_create_session_snapshot_writes_candidate_file(local_memory_root):
    result = create_session_snapshot(
        memory_root=local_memory_root,
        task="Runtime governance",
        summary="Added session snapshot support",
        source_text="example output",
        risk="medium",
        oversight="review-required",
    )
    snapshot_path = Path(result["snapshot_path"])
    assert snapshot_path.exists()
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["status"] == "candidate"
    assert payload["task"] == "Runtime governance"


def test_promote_candidate_appends_knowledge_base_and_manifest(local_memory_root):
    snapshot = create_session_snapshot(
        memory_root=local_memory_root,
        task="Runtime governance",
        summary="Added promotion support",
        source_text="example output",
        risk="medium",
        oversight="review-required",
    )
    result = promote_candidate(
        memory_root=local_memory_root,
        candidate_file=Path(snapshot["snapshot_path"]),
        approved_by="reviewer-01",
        title="Runtime governance promotion",
    )

    active_task = Path(result["active_task"])
    knowledge_base = Path(result["knowledge_base"])
    review_log = Path(result["review_log"])
    manifest_path = Path(result["manifest_path"])
    assert active_task.exists()
    assert knowledge_base.exists()
    assert review_log.exists()
    assert manifest_path.exists()
    assert "Promoted memory" in active_task.read_text(encoding="utf-8")
    assert "Runtime governance promotion" in knowledge_base.read_text(encoding="utf-8")
    assert "Approved by: reviewer-01" in review_log.read_text(encoding="utf-8")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["promotions"][0]["approved_by"] == "reviewer-01"

    payload = json.loads(Path(snapshot["snapshot_path"]).read_text(encoding="utf-8"))
    assert payload["status"] == "promoted"
