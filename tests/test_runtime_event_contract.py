import json
from pathlib import Path


def test_event_contract_docs_exist():
    assert Path("runtime_hooks/event_contract.md").exists()
    assert Path("runtime_hooks/event_schema.json").exists()


def test_event_schema_has_required_runtime_fields():
    schema = json.loads(Path("runtime_hooks/event_schema.json").read_text(encoding="utf-8"))
    required = set(schema["required"])
    assert {"event_type", "project_root", "risk", "oversight", "memory_mode"} <= required
    assert schema["properties"]["event_type"]["enum"] == ["pre_task", "post_task"]


def test_adapter_contract_references_shared_schema():
    text = Path("runtime_hooks/ADAPTER_CONTRACT.md").read_text(encoding="utf-8")
    assert "event_contract.md" in text
    assert "event_schema.json" in text
