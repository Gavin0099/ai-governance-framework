from pathlib import Path

from governance_tools.memory_emergency_event import MAX_EVENT_BYTES, MAX_EVIDENCE_BYTES

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_canonical_emergency_rule_has_only_daily_event_exception() -> None:
    text = (REPO_ROOT / "governance" / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
    section = text.split("### Emergency Event Journal exception", 1)[1].split("## 8. Definition of Done", 1)[0]
    bounded = text.split("僅當以下條件**全部成立**", 1)[1].split("### Emergency Event Journal exception", 1)[0]
    assert "不修改 memory" in bounded
    assert "governance_tools.memory_record --emergency-event" in section
    assert "memory/YYYY-MM-DD.md" in section
    assert "不得改寫 `memory/01_active_task.md`" in section
    assert "不得 cleanup、壓縮、替換 active state、降低 pressure" in section
    assert "執行 memory workflow guard" in section
    assert "不得用本例外記錄並繼續該決策" in section


def test_protocol_and_starter_pack_describe_same_narrow_exception() -> None:
    protocol = (REPO_ROOT / "governance" / "MEMORY_PROTOCOL.md").read_text(encoding="utf-8")
    starter = (REPO_ROOT / "examples" / "starter-pack" / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
    assert "### Emergency Event Journal exception" in protocol
    assert "--emergency-event" in protocol
    assert "active-source SHA-256" in protocol
    assert "canonical daily file only" in starter
    assert "does not lower pressure" in starter


def test_event_limits_match_canonical_policy() -> None:
    assert MAX_EVENT_BYTES == 4096
    assert MAX_EVIDENCE_BYTES == 10 * 1024 * 1024


def test_ordinary_writer_pressure_gate_is_not_an_emergency_override() -> None:
    writer_text = (REPO_ROOT / "governance_tools" / "memory_record.py").read_text(encoding="utf-8")
    assert "def _require_non_emergency_memory_write" in writer_text
    assert "status == \"EMERGENCY\"" in writer_text
    assert "append_emergency_event_with_outcome" in writer_text
    assert "ordinary memory writes" in writer_text
