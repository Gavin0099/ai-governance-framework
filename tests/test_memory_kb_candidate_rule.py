"""Knowledge-base candidate rule (slice F1, owner ruling 2026-10-30).

Session-derived records go through `governance_tools.memory_record`; a
root-caused bug-fix gotcha may be written directly to the knowledge base only
as a `CANDIDATE / UNREVIEWED` entry paired with a canonical daily record for
the same fix commit. These tests keep the protocol, the consumer router, the
F-7 router insert and the agent core stating the same rule, and prove that the
existing promotion path neither consumes nor relabels candidate lines.

They do not prove that any agent follows the rule, and they do not change the
promotion behavior; they pin what the current code does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools import f7_full_update
from memory_pipeline.memory_promoter import promote_candidate
from memory_pipeline.promotion_policy import classify_promotion_policy

REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = REPO_ROOT / "governance" / "MEMORY_PROTOCOL.md"
ROUTER = REPO_ROOT / "baselines" / "repo-min" / "AGENTS.md"
CORE_SURFACES = (
    REPO_ROOT / "governance" / "AGENT_CORE_RULES.md",
    REPO_ROOT / "governance" / "agent-contract-template.md",
    REPO_ROOT / "governance" / "copilot-instructions-template.md",
)
MARKER = "CANDIDATE / UNREVIEWED"
OLD_BLANKET = "do not edit memory records as ordinary markdown"


def _text(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _protocol_section() -> str:
    text = _text(PROTOCOL)
    start = text.index("## Knowledge-Base Candidate Rule")
    # The section's own example contains a `## CANDIDATE ...` heading inside a fence.
    return text[start:text.index("\n## Memory Workflow Dispatch Rule", start)]


def _router_line(text: str) -> str:
    lines = [line for line in text.splitlines() if "canonical memory writer (`memory_record`)" in line]
    assert len(lines) == 1
    return lines[0]


def _installer_router_insert(tmp_path: Path) -> str:
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    f7_full_update._ensure_agents_keyed_sections(repo)
    return (repo / "AGENTS.md").read_text(encoding="utf-8")


def test_protocol_states_the_candidate_rule() -> None:
    section = _protocol_section()
    for sentence in (
        "it has no knowledge-base surface.",
        f"as a candidate entry marked `{MARKER}`.",
        "It must contain the root cause, the fix, the fix commit hash and the test\nevidence",
        "for the same fix commit (`--commit <fix-sha>`).",
        "A candidate is not reviewed knowledge: it never claims promotion, never carries\n`Approved by`",
        "becomes authoritative only through the existing promotion\npath.",
        "Candidate entries are not inputs to auto-promotion.",
        "It is never evidence that an agent-written candidate was\n  reviewed.",
        "instead of writing a separate duplicate.",
        "the promoted entry supersedes the\n  candidate.",
        "recognised by the same fix commit hash in both\n  entries",
    ):
        assert sentence in section, sentence
    # The writer rule no longer reads as covering every repo memory file.
    write_it_down = _text(PROTOCOL)
    assert "or\n  the relevant repo memory file through the canonical writer." not in write_it_down
    assert "A knowledge-base gotcha follows the Knowledge-Base\n  Candidate Rule below." in write_it_down


@pytest.mark.parametrize("source", ["baseline", "installer"])
def test_router_states_the_candidate_rule(source: str, tmp_path: Path) -> None:
    text = _text(ROUTER) if source == "baseline" else _installer_router_insert(tmp_path)
    assert OLD_BLANKET not in text
    line = _router_line(text)
    for phrase in (
        "for session-derived records (daily, review log, active-task summary)",
        "written directly to `memory/03_knowledge_base.md`",
        f"only as a `{MARKER}` entry with root cause, fix, fix commit and test evidence",
        "paired with a canonical daily record for the same fix commit",
        "it never claims promotion or `Approved by`.",
    ):
        assert phrase in line, phrase


def test_installer_and_baseline_router_lines_are_identical(tmp_path: Path) -> None:
    assert _router_line(_installer_router_insert(tmp_path)) == _router_line(_text(ROUTER))


@pytest.mark.parametrize("surface", CORE_SURFACES, ids=lambda p: p.name)
def test_core_rule_four_states_the_candidate_rule(surface: Path) -> None:
    text = _text(surface)
    row = next(line for line in text.splitlines() if line.startswith("| Bug fixed with root cause identified"))
    assert f"`memory/03_knowledge_base.md` as a `{MARKER}` entry" in row
    assert "(root cause, fix, fix commit, test evidence)" in row
    assert "paired with a `memory_record` daily record for the same fix commit" in row
    assert "never marked approved, reviewed only through promotion" in row


CANDIDATE_BLOCK = (
    f"## {MARKER}: USB descriptor parse overrun\n"
    "- Root cause: length byte trusted before bounds check\n"
    "- Fix: clamp descriptor length to buffer size\n"
    "- Fix commit: 0123456789abcdef0123456789abcdef01234567\n"
    "- Test evidence: pytest tests/test_descriptor.py 12 passed\n"
    "- Daily record: memory/2026-10-30.md (memory_record, commit 0123456789abcdef0123456789abcdef01234567)\n\n"
)


def _candidate_snapshot(memory_root: Path, task: str) -> Path:
    path = memory_root / "candidates" / "session_fixture.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "captured_at": "2026-10-30T00:00:00+00:00",
        "task": task,
        "summary": "fixed descriptor overrun at 0123456789abcdef0123456789abcdef01234567",
        "risk": "low",
        "oversight": "auto",
        "source_text": "",
        "status": "candidate",
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("kb_name", ["03_knowledge_base.md", "03_decisions.md"])
@pytest.mark.parametrize(
    "task",
    ["USB descriptor parse overrun", f"{MARKER}: USB descriptor parse overrun"],
    ids=["same-short-title", "same-full-heading"],
)
def test_promotion_never_modifies_or_relabels_candidate_lines(
    tmp_path: Path, kb_name: str, task: str
) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    kb = memory_root / kb_name
    kb.write_text("# Knowledge Base\n\n" + CANDIDATE_BLOCK, encoding="utf-8")

    # session_end classifies without a source file; low-risk auto sessions AUTO_PROMOTE.
    policy = classify_promotion_policy({"risk": "low", "oversight": "auto", "memory_mode": "candidate"})
    assert policy["decision"] == "AUTO_PROMOTE"

    result = promote_candidate(
        memory_root=memory_root,
        candidate_file=_candidate_snapshot(memory_root, task),
        approved_by="runtime-auto-promotion",
        title=task,
    )

    assert Path(result["knowledge_base"]) == kb
    after = kb.read_text(encoding="utf-8")
    # The candidate block survives byte-for-byte, once, with nothing inserted into it.
    assert after.startswith("# Knowledge Base\n\n" + CANDIDATE_BLOCK)
    assert after.count(CANDIDATE_BLOCK) == 1
    assert "Approved by" not in CANDIDATE_BLOCK


def test_promotion_appends_its_own_entry_instead_of_absorbing_the_candidate(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    kb = memory_root / "03_knowledge_base.md"
    kb.write_text("# Knowledge Base\n\n" + CANDIDATE_BLOCK, encoding="utf-8")

    promote_candidate(
        memory_root=memory_root,
        candidate_file=_candidate_snapshot(memory_root, "USB descriptor parse overrun"),
        approved_by="runtime-auto-promotion",
        title="USB descriptor parse overrun",
    )

    after = kb.read_text(encoding="utf-8")
    promoted = after[len("# Knowledge Base\n\n" + CANDIDATE_BLOCK):]
    assert promoted.startswith("## USB descriptor parse overrun\n")
    assert "- Approved by: runtime-auto-promotion\n" in promoted
    # The pairing is recognisable only because this summary carries the fix commit.
    assert "0123456789abcdef0123456789abcdef01234567" in promoted
