import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.retrieval_authority_observer import observe  # noqa: E402


def test_used_superseded_requires_human_review() -> None:
    payload = {
        "session_id": "s-001",
        "response_text": "According to superseded memory, behavior was X.",
        "memory_refs": [
            {"source_type": "canonical", "validity_state": "superseded"},
        ],
    }
    out = observe(payload)
    assert out["observation"]["used_superseded"] is True
    assert out["observation"]["needs_human_review"] is True


def test_candidate_with_explicit_context_is_not_auto_conflict() -> None:
    payload = {
        "session_id": "s-002",
        "response_text": "Candidate memory suggests a hypothesis; canonical memory remains authoritative.",
        "memory_refs": [
            {"source_type": "candidate", "validity_state": "active"},
            {"source_type": "canonical", "validity_state": "active"},
        ],
    }
    out = observe(payload)
    assert out["observation"]["used_candidate"] is True
    assert out["observation"]["explicit_candidate_context"] is True
    assert out["observation"]["authority_conflict"] is False


def test_candidate_overrides_canonical_sets_conflict() -> None:
    payload = {
        "session_id": "s-003",
        "response_text": "Ignore canonical; candidate memory is authoritative for this conclusion.",
        "memory_refs": [
            {"source_type": "candidate", "validity_state": "active"},
            {"source_type": "canonical", "validity_state": "active"},
        ],
    }
    out = observe(payload)
    assert out["observation"]["used_candidate"] is True
    assert out["observation"]["used_canonical"] is True
    assert out["observation"]["authority_conflict"] is True
    assert out["observation"]["needs_human_review"] is True


def test_advisory_only_is_always_true() -> None:
    payload = {
        "session_id": "s-004",
        "response_text": "No memory reference in this response.",
        "memory_refs": [],
    }
    out = observe(payload)
    assert out["advisory_only"] is True

