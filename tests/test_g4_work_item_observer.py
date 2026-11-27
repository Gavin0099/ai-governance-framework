"""Tests for the read-only G4 Work Item Observer (scripts/g4_work_item_observer.py)."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import g4_work_item_observer as observer  # noqa: E402

_SAMPLE_003_ENV = os.environ.get("G4_SAMPLE_003_DIR", "").strip()
SAMPLE_003_DIR = Path(_SAMPLE_003_ENV) if _SAMPLE_003_ENV else None
SAMPLE_003_PROBE_SESSION_ID = "01a20c45-b1e6-7b51-b895-953e1f18f566"


def _write_jsonl(path: Path, rows: list[dict | str]) -> Path:
    lines = [row if isinstance(row, str) else json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _token_event(input_tokens: int, cached: int, output: int, reasoning: int = 0) -> dict:
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached,
                    "cache_write_input_tokens": 0,
                    "output_tokens": output,
                    "reasoning_output_tokens": reasoning,
                    "total_tokens": input_tokens + output,
                }
            },
        },
    }


def test_parse_separates_main_guardian_subagent_and_deduplicates_cumulative_events(tmp_path: Path):
    # session_index.jsonl must be ignored rather than treated as corrupt rollout.
    _write_jsonl(tmp_path / "session_index.jsonl", [{"id": "idx-1"}])

    # Main session with multiple cumulative token_count events (must take latest, not sum).
    _write_jsonl(
        tmp_path / "rollout-main.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-main", "source": "exec", "cwd": "/repo/app"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(1000, 400, 50, 10),
            _token_event(2500, 1500, 200, 30),
        ],
    )
    # Guardian subagent
    _write_jsonl(
        tmp_path / "rollout-guardian.jsonl",
        [
            {
                "type": "session_meta",
                "payload": {"id": "sess-guard", "source": {"subagent": {"other": "guardian"}}, "cwd": "/repo/app"},
            },
            {"type": "turn_context", "payload": {"model": "codex-auto-review"}},
            _token_event(600, 300, 40, 15),
        ],
    )
    # Generic subagent
    _write_jsonl(
        tmp_path / "rollout-sub.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-sub", "source": {"subagent": "reviewer"}, "cwd": "/repo/app"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-mini"}},
            _token_event(300, 100, 20, 5),
        ],
    )

    result = observer.parse_codex_rollout_dirs(
        [tmp_path],
        expected_session_ids={"sess-main", "sess-guard", "sess-sub"},
    )
    assert result["parsed_files_valid"] is True
    assert result["work_item_cost_complete"] is True
    assert result["cost_completeness"] == "complete"
    assert result["comparability_token"] == 1
    assert result["known_totals"]["total_tokens"] == 2700 + 640 + 320
    assert result["verified_complete_totals"]["total_tokens"] == 2700 + 640 + 320
    assert result["by_role"]["main"]["total_tokens"] == 2700
    assert result["by_role"]["main"]["uncached_input_tokens"] == 1000
    assert result["by_role"]["main"]["cached_input_tokens"] == 1500
    assert result["by_role"]["guardian"]["total_tokens"] == 640
    assert result["by_role"]["subagent"]["total_tokens"] == 320
    # Privacy: source references must be redacted to basename + sha256 prefix, no full local paths.
    serialized = json.dumps(result)
    assert str(tmp_path) not in serialized


def test_missing_guardian_or_unverified_inventory_never_claims_work_item_cost_complete(tmp_path: Path):
    _write_jsonl(
        tmp_path / "rollout-main.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-main", "source": "exec"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(1000, 400, 100),
        ],
    )
    # 1) Without an explicit session inventory, parsed_files_valid is True but work_item_cost_complete MUST be False.
    no_inventory = observer.parse_codex_rollout_dirs([tmp_path])
    assert no_inventory["parsed_files_valid"] is True
    assert no_inventory["work_item_cost_complete"] is False
    assert no_inventory["cost_completeness"] == "incomplete"
    assert no_inventory["comparability_token"] == 0
    assert no_inventory["verified_complete_totals"] is None
    assert no_inventory["known_totals"]["total_tokens"] == 1100

    # 2) When an expected Guardian session is missing from the directory, fail closed as incomplete.
    missing_guardian = observer.parse_codex_rollout_dirs(
        [tmp_path],
        expected_session_ids={"sess-main", "sess-guardian-missing"},
    )
    assert missing_guardian["parsed_files_valid"] is True
    assert missing_guardian["work_item_cost_complete"] is False
    assert missing_guardian["cost_completeness"] == "incomplete"
    assert missing_guardian["missing_expected_sessions"] == ["sess-guardian-missing"]
    assert any("missing_expected_session:sess-guardian-missing" in a for a in missing_guardian["anomalies"])


def test_cross_file_resumed_session_takes_highest_cumulative_without_double_counting(tmp_path: Path):
    _write_jsonl(
        tmp_path / "rollout-part1.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-resumed", "source": "exec"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(1000, 500, 100),
        ],
    )
    _write_jsonl(
        tmp_path / "rollout-part2.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-resumed", "source": "exec"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(1000, 500, 100),
            _token_event(1800, 1000, 250),
        ],
    )

    result = observer.parse_codex_rollout_dirs([tmp_path], expected_session_ids={"sess-resumed"})
    assert result["parsed_files_valid"] is True
    assert result["work_item_cost_complete"] is True
    assert result["cost_completeness"] == "complete"
    assert result["known_totals"]["total_tokens"] == 2050
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["resumed_across_files"] is True


def test_non_monotonic_reset_or_corrupt_jsonl_marks_cost_incomplete(tmp_path: Path):
    _write_jsonl(
        tmp_path / "rollout-broken.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-bad", "source": "exec"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(2000, 1000, 100),
            _token_event(500, 100, 20),  # non-monotonic reset within same session
            "{not-valid-json",
        ],
    )

    result = observer.parse_codex_rollout_dirs([tmp_path])
    assert result["cost_completeness"] == "incomplete"
    assert result["comparability_token"] == 0
    assert result["verified_complete_totals"] is None
    assert result["known_totals"]["total_tokens"] == 2100
    assert any("non_monotonic" in a for a in result["anomalies"])
    assert any("corrupt_json_line" in a for a in result["anomalies"])


def test_missing_intervention_log_reports_unknown_not_zero_and_never_uses_wall_clock():
    human = observer.summarize_human_interventions(None, confirmed_minutes=None)
    assert human["planned_owner_decisions"] == "UNKNOWN"
    assert human["unplanned_rescues"] == "UNKNOWN"
    assert human["human_minutes"] == "UNKNOWN"
    assert human["wall_clock_excluded"] is True


def test_delivery_never_equates_ci_pass_to_product_verified_or_prod_enabled():
    def fake_gh(args: list[str]) -> str:
        if args[:2] == ["pr", "view"]:
            return json.dumps(
                {
                    "number": 25,
                    "title": "feat: DB-04",
                    "state": "MERGED",
                    "headRefOid": "0e1ad7f1",
                    "mergeCommit": {"oid": "55a17b3c"},
                    "url": "https://github.com/org/repo/pull/25",
                }
            )
        if args[:2] == ["run", "list"]:
            return json.dumps([{"databaseId": 1001, "status": "completed", "conclusion": "success", "name": "Governance"}])
        raise AssertionError(f"Unexpected gh args: {args}")

    delivery = observer.collect_delivery_evidence(
        repo="org/repo",
        pr_numbers=[25],
        product_verification_status=None,
        deployed_status=None,
        gh_runner=fake_gh,
    )
    assert delivery["code_completed"] == "YES"
    assert delivery["merged_and_ci"] == "YES"
    assert delivery["product_verified"] == "NOT_VERIFIED"
    assert delivery["deployed_or_enabled"] == "UNKNOWN"


def test_end_to_end_report_includes_observer_self_cost_and_redacts_paths(tmp_path: Path):
    rollout_dir = tmp_path / "sessions"
    rollout_dir.mkdir()
    _write_jsonl(
        rollout_dir / "rollout-1.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-1", "source": "exec"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(1000, 600, 100),
        ],
    )
    out_dir = tmp_path / "out"
    report_md, index_path = observer.run_observer(
        work_item_id="WI-TEST-1",
        title="Test Work Item",
        repo=None,
        pr_numbers=[],
        rollout_dirs=[rollout_dir],
        output_dir=out_dir,
    )
    md_text = report_md.read_text(encoding="utf-8")
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    assert "Observer 自身成本" in md_text
    assert "UNKNOWN" in md_text
    assert str(tmp_path) not in md_text
    assert str(tmp_path) not in json.dumps(index_data)
    assert index_data["observer_self_cost"]["duration_ms"] >= 0
    assert index_data["observer_self_cost"]["ai_usage_available"] is False


def test_partial_pr_lookup_failure_downgrades_merged_and_ci_and_unknown_role_is_rendered(tmp_path: Path):
    def fake_gh(args: list[str]) -> str:
        if args[:3] == ["pr", "view", "25"]:
            return json.dumps(
                {
                    "number": 25,
                    "title": "feat: DB-04",
                    "state": "MERGED",
                    "headRefOid": "0e1ad7f1",
                    "mergeCommit": {"oid": "55a17b3c"},
                    "url": "https://github.com/org/repo/pull/25",
                }
            )
        if args[:3] == ["pr", "view", "999"]:
            raise RuntimeError("PR lookup failed")
        if args[:2] == ["run", "list"]:
            return json.dumps([{"databaseId": 1001, "status": "completed", "conclusion": "success", "name": "Governance"}])
        raise AssertionError(f"Unexpected gh args: {args}")

    delivery = observer.collect_delivery_evidence(repo="org/repo", pr_numbers=[25, 999], gh_runner=fake_gh)
    assert delivery["merged_and_ci"] == "PARTIAL"

    _write_jsonl(
        tmp_path / "rollout-unk.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-unk", "source": "custom-unknown"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(400, 100, 50),
        ],
    )
    out_dir = tmp_path / "out"
    report_md, _ = observer.run_observer(
        work_item_id="WI-UNK",
        title="Unknown Role Check",
        repo=None,
        pr_numbers=[],
        rollout_dirs=[tmp_path],
        output_dir=out_dir,
    )
    assert "Unknown 450" in report_md.read_text(encoding="utf-8")


def test_open_pr_and_unbacked_product_flag_remain_not_verified(tmp_path: Path):
    def fake_gh(args: list[str]) -> str:
        if args[:2] == ["pr", "view"]:
            return json.dumps(
                {
                    "number": 99,
                    "title": "wip: draft",
                    "state": "OPEN",
                    "headRefOid": "abc1234",
                    "mergeCommit": None,
                    "url": "https://github.com/org/repo/pull/99",
                }
            )
        raise AssertionError(f"Unexpected gh args: {args}")

    # OPEN PR without code evidence file + unbacked product_verification_status string -> both NOT_VERIFIED.
    unbacked = observer.collect_delivery_evidence(
        repo="org/repo",
        pr_numbers=[99],
        product_verification_status="4/4 PASS",
        gh_runner=fake_gh,
    )
    assert unbacked["code_completed"] == "NOT_VERIFIED"
    assert unbacked["merged_and_ci"] == "NO"
    assert unbacked["product_verified"] == "NOT_VERIFIED"

    # Providing real non-empty evidence files unlocks verified claims with redacted refs.
    ev = tmp_path / "qa-evidence.json"
    ev.write_text('{"pass": true}\n', encoding="utf-8")
    backed = observer.collect_delivery_evidence(
        repo="org/repo",
        pr_numbers=[99],
        code_evidence_file=ev,
        product_evidence_file=ev,
        product_verification_status="4/4 PASS",
        gh_runner=fake_gh,
    )
    assert backed["code_completed"] == "YES"
    assert backed["product_verified"] == "4/4 PASS"
    assert backed["product_evidence_ref"].startswith("qa-evidence.json#sha256:")


def test_llm_assisted_observer_never_reports_zero_tokens_when_unmeasured(tmp_path: Path):
    out_dir = tmp_path / "out"
    _, index_path = observer.run_observer(
        work_item_id="WI-LLM",
        title="LLM Assisted Cost Boundary",
        repo=None,
        pr_numbers=[],
        rollout_dirs=[tmp_path],
        output_dir=out_dir,
        observer_mode="llm_assisted",
    )
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_data["observer_self_cost"]["observer_ai_tokens"] == "UNKNOWN"
    assert index_data["observer_self_cost"]["ai_usage_available"] is False


def test_archive_root_writes_redacted_chinese_report_and_updates_index_with_unknowns(tmp_path: Path):
    rollout_dir = tmp_path / "private-rollouts"
    rollout_dir.mkdir()
    _write_jsonl(
        rollout_dir / "rollout-wi.jsonl",
        [
            {"type": "session_meta", "payload": {"id": "sess-wi", "source": "exec"}},
            {"type": "turn_context", "payload": {"model": "gpt-6.2-sol"}},
            _token_event(1200, 800, 150, 40),
        ],
    )
    archive_root = tmp_path / "docs" / "status" / "g4-observer"
    report_md, index_json = observer.run_observer(
        work_item_id="WI-ARCH-1",
        title="中文歸檔測試",
        repo="org/repo",
        pr_numbers=[],
        rollout_dirs=[rollout_dir],
        expected_session_ids={"sess-wi"},
        archive_root=archive_root,
    )
    assert report_md == archive_root / "WI-ARCH-1" / "report.md"
    assert index_json == archive_root / "WI-ARCH-1" / "evidence_index.json"
    index_md = archive_root / "INDEX.md"
    assert index_md.is_file()

    md_text = report_md.read_text(encoding="utf-8")
    index_md_text = index_md.read_text(encoding="utf-8")
    # Chinese explanations and token breakdown must be present, and unknowns must be preserved honestly.
    assert "快取命中 800" in md_text
    assert "含推理 40" in md_text
    assert "紀錄檔解析有效" in md_text
    assert "UNKNOWN" in md_text
    assert "WI-ARCH-1" in index_md_text
    assert "中文歸檔測試" in index_md_text
    # Privacy: raw JSONL must never be copied into archive_root and local paths must never leak.
    assert not list(archive_root.rglob("*.jsonl"))
    assert str(tmp_path) not in md_text
    assert str(tmp_path) not in index_md_text
    assert str(tmp_path) not in index_json.read_text(encoding="utf-8")


@pytest.mark.skipif(
    SAMPLE_003_DIR is None or not SAMPLE_003_DIR.is_dir(),
    reason="G4_SAMPLE_003_DIR not set or local Sample 003 raw Codex rollout JSONL directory is absent",
)
def test_sample_003_real_rollout_regression_matches_verified_3025249_tokens():
    """Real Sample 003 raw JSONL regression (never hardcoded if files are absent)."""
    expected_ab = {
        "01a20c46-e6bb-77e0-b923-a13fa9965aa9",
        "01a20c46-e76a-7e93-af4a-a607104e322f",
        "01a20c53-1e4c-7430-8e64-4a2ed7306a09",
        "01a20c53-23cd-7e10-a273-d4501f500e52",
    }
    # Without expected_session_ids, totals are known but completeness is conservatively incomplete.
    unverified_inv = observer.parse_codex_rollout_dirs(
        [SAMPLE_003_DIR],
        exclude_session_ids={SAMPLE_003_PROBE_SESSION_ID},
    )
    assert unverified_inv["parsed_files_valid"] is True
    assert unverified_inv["work_item_cost_complete"] is False
    assert unverified_inv["known_totals"]["total_tokens"] == 3_025_249

    # With the verified A+B session inventory, completeness is complete and exact.
    result = observer.parse_codex_rollout_dirs(
        [SAMPLE_003_DIR],
        exclude_session_ids={SAMPLE_003_PROBE_SESSION_ID},
        expected_session_ids=expected_ab,
    )
    assert result["parsed_files_valid"] is True
    assert result["work_item_cost_complete"] is True
    assert result["cost_completeness"] == "complete"
    assert result["comparability_token"] == 1
    assert result["known_totals"]["total_tokens"] == 3_025_249
    assert result["verified_complete_totals"]["total_tokens"] == 3_025_249
    assert result["by_role"]["main"]["total_tokens"] == 2_019_605
    assert result["by_role"]["guardian"]["total_tokens"] == 1_005_644

    # Including the pre-run probe session accounts for all 5 rollout files cleanly.
    full = observer.parse_codex_rollout_dirs(
        [SAMPLE_003_DIR],
        expected_session_ids=expected_ab | {SAMPLE_003_PROBE_SESSION_ID},
    )
    assert full["work_item_cost_complete"] is True
    assert full["known_totals"]["total_tokens"] == 3_047_300


def _claude_message(session_id: str | None, message_id: str | None, **usage) -> dict:
    return {"type": "assistant", "sessionId": session_id, "message": {"id": message_id, "usage": usage}}


def _gemini_message(message_id: str | None, **tokens) -> dict:
    return {"type": "gemini", "id": message_id, "tokens": tokens}


def _expected_ref(path: Path) -> str:
    return f"{path.name}#sha256:{hashlib.sha256(path.read_bytes()).hexdigest()[:12]}"


def test_claude_uses_final_snapshot_and_scopes_message_id_to_session(tmp_path: Path):
    nested = tmp_path / "private" / "nested"
    nested.mkdir(parents=True)
    first = _claude_message(
        "claude-one", "repeated",
        input_tokens=10, cache_creation_input_tokens=6, cache_read_input_tokens=20, output_tokens=2,
        costUSD="private-cost", service_tier="private-tier", inference_geo="private-geo",
    )
    last = _claude_message(
        "claude-one", "repeated",
        input_tokens=14, cache_creation_input_tokens=6, cache_read_input_tokens=20, output_tokens=13,
    )
    original = _write_jsonl(nested / "first.jsonl", [first, first, {"type": "user", "message": first["message"]}])
    resumed = _write_jsonl(tmp_path / "second.jsonl", [last])
    other = _write_jsonl(
        nested / "claude-two.jsonl",
        [_claude_message(None, "repeated", input_tokens=3, cache_creation_input_tokens=0,
                         cache_read_input_tokens=0, output_tokens=4)],
    )
    provider = observer.parse_claude_transcripts(
        [nested.parent, original, resumed], expected_session_ids={"claude-one", "claude-two"},
    )
    assert provider["presence_state"] == "measured"
    assert provider["unit"] == "tokens"
    assert provider["completeness_scope"] == "provider_sessions_only"
    assert provider["cost_completeness"] == "complete"
    assert provider["missing_expected_sessions"] == provider["anomalies"] == []
    assert provider["known_totals"] == {
        "input_tokens": 17, "cache_creation_input_tokens": 6, "cache_read_input_tokens": 20, "output_tokens": 17,
    }
    assert provider["source_refs"] == sorted(map(_expected_ref, [original, resumed, other]))
    for forbidden in ("costUSD", "service_tier", "inference_geo", "private-"):
        assert forbidden not in json.dumps(provider)


def test_claude_decreasing_updates_keep_field_maxima_without_counting_anonymous_message(tmp_path: Path):
    path = _write_jsonl(tmp_path / "claude.jsonl", [
        _claude_message("sess", "one", input_tokens=12, output_tokens=5, cache_read_input_tokens=10),
        _claude_message("sess", "one", input_tokens=10, output_tokens=8, cache_creation_input_tokens=3),
        _claude_message("sess", "one", input_tokens=14, output_tokens=7, cache_creation_input_tokens=5),
        _claude_message("sess", None, input_tokens=1000, output_tokens=1000),
    ])
    provider = observer.parse_claude_transcripts([path], expected_session_ids={"sess"})
    assert provider["presence_state"] == "measured"
    assert provider["cost_completeness"] == "incomplete"
    assert provider["missing_expected_sessions"] == []
    assert provider["anomalies"] == ["claude_missing_message_id", "claude_non_monotonic_usage_update"]
    assert provider["known_totals"] == {
        "input_tokens": 14, "cache_creation_input_tokens": 5, "cache_read_input_tokens": 10, "output_tokens": 8,
    }


def test_claude_retains_final_missing_fields_and_detects_invalid_data(tmp_path: Path):
    path = _write_jsonl(tmp_path / "claude.jsonl", [
        _claude_message("sess", "one", input_tokens=4, output_tokens=3, cache_read_input_tokens=2),
        _claude_message("sess", "one", input_tokens=8, output_tokens=5, cache_creation_input_tokens=False),
        _claude_message("other-sess", "one", input_tokens=1000, output_tokens=1000),
        "{broken",
    ])
    provider = observer.parse_claude_transcripts([path], expected_session_ids={"sess", "missing"})
    assert provider["known_totals"] == {
        "input_tokens": 8, "cache_creation_input_tokens": None, "cache_read_input_tokens": None, "output_tokens": 5,
    }
    assert provider["cost_completeness"] == "incomplete"
    assert provider["missing_expected_sessions"] == ["missing"]
    assert provider["anomalies"] == ["claude_invalid_token_count", "invalid_transcript_jsonl_line"]
    unattributable = observer.parse_claude_transcripts([path], expected_session_ids={"claude"})
    assert unattributable["presence_state"] == "unknown"
    assert unattributable["known_totals"] is None


def test_gemini_reads_json_and_jsonl_and_coalesces_by_message_id(tmp_path: Path):
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"sessionId": "g1", "messages": [
        {"type": "user", "id": "turn", "tokens": {"input": 500}},
        _gemini_message("turn", input=20, cached=6, output=6, thoughts=2, tool=1),
        _gemini_message("turn", input=18, output=7, cached=None),
    ]}), encoding="utf-8")
    log = _write_jsonl(tmp_path / "g2.jsonl", [
        _gemini_message("turn", input=9, cached=0, output=5, thoughts=0, tool=3),
        _gemini_message("turn", output=2, thoughts=1),
    ])
    provider = observer.parse_gemini_transcripts([tmp_path, log], expected_session_ids={"g1", "g2"})
    assert provider["presence_state"] == "measured"
    assert provider["completeness_scope"] == "provider_sessions_only"
    assert provider["cost_completeness"] == "complete"
    assert provider["anomalies"] == []
    assert provider["known_totals"] == {
        "input_tokens": 27, "cached_tokens": 6, "uncached_input_tokens": 21,
        "output_tokens": 9, "thoughts_tokens": 3, "tool_tokens": 4,
    }
    assert provider["source_refs"] == sorted(map(_expected_ref, [log, path]))


@pytest.mark.parametrize("cached", [None, 11])
def test_gemini_uncached_is_unknown_when_a_counted_turn_lacks_valid_cached_breakdown(tmp_path: Path, cached):
    path = _write_jsonl(tmp_path / "gemini.jsonl", [
        _gemini_message("valid", input=10, cached=2, output=4, thoughts=1, tool=0),
        _gemini_message("partial", input=10, cached=cached, output=2, thoughts=0, tool=0),
    ])
    provider = observer.parse_gemini_transcripts([path], expected_session_ids={"gemini"})
    assert provider["presence_state"] == "measured"
    assert provider["cost_completeness"] == "incomplete"
    assert provider["known_totals"]["input_tokens"] == 20
    assert provider["known_totals"]["cached_tokens"] == (None if cached is None else 13)
    assert provider["known_totals"]["uncached_input_tokens"] is None
    assert provider["anomalies"] == ([] if cached is None else ["gemini_cached_tokens_exceed_input"])


@pytest.mark.parametrize("field,value", [
    ("input", True), ("cached", -1), ("output", 1.5), ("thoughts", "2"), ("tool", False),
])
def test_gemini_strict_validation_rejects_invalid_token_rows(tmp_path: Path, field, value):
    path = _write_jsonl(tmp_path / "invalid.jsonl", [_gemini_message("bad", **{field: value})])
    provider = observer.parse_gemini_transcripts([path])
    assert provider["presence_state"] == "unknown"
    assert provider["known_totals"] is None
    assert provider["anomalies"] == ["gemini_invalid_token_count"]


def test_gemini_accepts_exact_zero_and_large_integers_and_marks_unkeyed_turns_incomplete(tmp_path: Path):
    log = _write_jsonl(tmp_path / "g1.jsonl", [
        _gemini_message("turn", input=2**70, cached=2**70, output=0, thoughts=0, tool=0),
        _gemini_message(None, input=0, cached=0, output=0, thoughts=0, tool=0),
    ])
    provider = observer.parse_gemini_transcripts([log], expected_session_ids={"g1"}, confirmed_unused=True)
    assert provider["presence_state"] == "measured"
    assert provider["known_totals"]["input_tokens"] == 2**70
    assert provider["known_totals"]["uncached_input_tokens"] == 0
    assert provider["known_totals"]["output_tokens"] == 0
    assert provider["cost_completeness"] == "incomplete"
    assert provider["anomalies"] == ["gemini_missing_message_id", "provider_evidence_conflicts_with_confirmed_unused"]


@pytest.mark.parametrize("parse", [observer.parse_claude_transcripts, observer.parse_gemini_transcripts])
def test_provider_presence_does_not_infer_unused_from_missing_or_empty_files(tmp_path: Path, parse):
    empty = _write_jsonl(tmp_path / "empty.jsonl", [{"type": "user"}])
    invalid_utf8 = tmp_path / "invalid.jsonl"
    invalid_utf8.write_bytes(b"\xff")
    missing = tmp_path / "missing"
    provider = parse([missing, invalid_utf8, empty], expected_session_ids={"empty"})
    assert provider["presence_state"] == "unknown"
    assert provider["known_totals"] is None
    assert provider["cost_completeness"] == "incomplete"
    assert provider["missing_expected_sessions"] == ["empty"]
    assert provider["source_refs"] == [_expected_ref(empty)]
    assert provider["anomalies"] == ["no_provider_source:missing", "unreadable_provider_source:invalid.jsonl"]
    confirmed = parse([], confirmed_unused=True)
    assert confirmed["presence_state"] == "confirmed_unused"
    assert confirmed["known_totals"] is None
    assert confirmed["source_refs"] == []


def test_copilot_aggregates_daily_credits_by_model_and_excludes_money(tmp_path: Path):
    first = tmp_path / "first.csv"
    first.write_text(
        "REPORT_DATE,login,model_name,AI_Credits,aic_gross_amount,Amount_USD,COST,gross_amount\n"
        "11/27/2026,private-user,model-a,1.25,private-dollar,private-dollar,private-dollar,private-dollar\n"
        "2026/11/26,private-user,model-b,2.5,,,,\n"
        "2026-11-26,private-user,model-a,1.5,,,,\n",
        encoding="utf-8-sig",
    )
    second = tmp_path / "second.csv"
    second.write_text(
        "date,model,aic_quantity\n2026-11-28,model-a,2\n2026-11-28,model-a,3\n2026-11-28,zero,0\n",
        encoding="utf-8",
    )
    provider = observer.parse_copilot_billing([first, second, first])
    assert provider == {
        "presence_state": "billing_reference_only",
        "unit": "aic_quantity",
        "completeness_scope": "billing_window_only",
        "cost_completeness": "not_applicable",
        "completions_excluded": True,
        "work_item_attributable": False,
        "billing_window": {"start_date": "2026-11-26", "end_date": "2026-11-28"},
        "by_model_aic": {"model-a": 7.75, "model-b": 2.5, "zero": 0.0},
        "ignored_columns": ["aic_gross_amount", "amount_usd", "cost", "gross_amount"],
        "source_refs": list(map(_expected_ref, [first, second])),
        "anomalies": [],
    }


def test_copilot_detects_invalid_and_conflicting_rows_without_disclosing_raw_values(tmp_path: Path):
    first = tmp_path / "first.csv"
    first.write_text(
        "date,user_login,model,aic_quantity\n"
        "2026-11-27,private-user,model-a,1\n"
        "2026-11-27,private-user,model-a,1\n"
        "2026-11-27,private-user,model-b,4\n"
        "2026-11-27,private-user,model-c,nan\n"
        "2026-11-27,private-user,model-c,inf\n"
        "2026-11-27,private-user,model-c,-2\n"
        "2026-13-27,private-user,model-c,2\n"
        "2026-11-27,private-user,model-c\n",
        encoding="utf-8",
    )
    second = tmp_path / "second.csv"
    second.write_text(
        "date,username,model,credits\n"
        "2026-11-27,private-user,model-a,2\n"
        "2026-11-27,private-user,model-b,4\n",
        encoding="utf-8",
    )
    provider = observer.parse_copilot_billing([first, second], confirmed_unused=True)
    assert provider["presence_state"] == "billing_reference_only"
    assert provider["by_model_aic"] == {"model-b": 4.0}
    assert provider["anomalies"] == [
        "copilot_conflicting_daily_quantity", "copilot_invalid_billing_row",
        "provider_evidence_conflicts_with_confirmed_unused",
    ]
    assert "private-user" not in json.dumps(provider)


def test_copilot_unknown_and_confirmed_unused_are_distinct(tmp_path: Path):
    invalid = tmp_path / "invalid.csv"
    invalid.write_text("date,model,cost\n2026-11-27,a,17\n", encoding="utf-8")
    provider = observer.parse_copilot_billing([invalid, tmp_path / "missing.csv"])
    assert provider["presence_state"] == "unknown"
    assert provider["by_model_aic"] == {}
    assert provider["billing_window"] == {"start_date": None, "end_date": None}
    assert provider["ignored_columns"] == ["cost"]
    assert provider["anomalies"] == ["copilot_missing_required_columns", "no_provider_source:missing.csv"]
    assert observer.parse_copilot_billing([], confirmed_unused=True)["presence_state"] == "confirmed_unused"


@pytest.mark.parametrize("events,refs,confirmed,expected", [
    (None, [], False, "unknown"),
    ([], [], False, "unknown"),
    ([{"category": "planned_owner_decision"}], [], False, "unknown"),
    ([], [], True, "no"),
    (None, [], True, "no"),
    (None, ["PR#123"], False, "yes"),
    ([], ["PR#123"], True, "yes"),
    ([{"category": "unplanned_rescue"}], [], False, "yes"),
    ([{"category": "unplanned_rescue"}], [], True, "yes"),
])
def test_rescue_truth_table_preserves_original_counts(tmp_path: Path, events, refs, confirmed, expected):
    path = None
    if events is not None:
        path = tmp_path / "interventions.json"
        path.write_text(json.dumps({"events": events}), encoding="utf-8")
    human = observer.summarize_human_interventions(
        path, confirmed_minutes=4.5, rescue_evidence_refs=refs, rescue_confirmed_none=confirmed,
    )
    assert human["unexpected_rescue_observed"] == expected
    assert human["human_minutes"] == 4.5
    assert ("rescue_evidence_conflicts_with_confirmed_none" in human["notes"]) == (confirmed and expected == "yes")
    if events is None:
        assert human["unplanned_rescues"] == "UNKNOWN"
        assert human["rescue_evidence_refs"] == refs
    elif events and events[0]["category"] == "unplanned_rescue":
        assert human["unplanned_rescues"] == 1
        assert human["rescue_evidence_refs"] == [_expected_ref(path)]
    else:
        assert human["unplanned_rescues"] == 0
        assert human["rescue_evidence_refs"] == refs


def test_rescue_redacts_explicit_paths_and_invalid_event_log_stays_unknown(tmp_path: Path):
    broken = tmp_path / "events.json"
    broken.write_text("{bad", encoding="utf-8")
    assert observer.summarize_human_interventions(broken)["unexpected_rescue_observed"] == "unknown"
    private_ref = str(tmp_path / "private.log")
    human = observer.summarize_human_interventions(
        broken, rescue_evidence_refs=[private_ref, private_ref, "PR#25"],
    )
    assert human["unexpected_rescue_observed"] == "yes"
    assert human["rescue_evidence_refs"] == [
        "PR#25", f"rescue-ref#sha256:{hashlib.sha256(private_ref.encode()).hexdigest()[:12]}",
    ]
    assert private_ref not in json.dumps(human)


def test_multi_provider_cli_preserves_codex_evidence_and_renders_separate_rows(tmp_path: Path):
    sources = tmp_path / "inputs"
    sources.mkdir()
    codex = _write_jsonl(sources / "codex.jsonl", [
        {"type": "session_meta", "payload": {"id": "codex-session", "source": "exec"}},
        {"type": "turn_context", "payload": {"model": "codex"}},
        _token_event(100, 25, 30, 5),
    ])
    claude = _write_jsonl(sources / "claude.jsonl", [
        _claude_message("cs", "message", input_tokens=12, cache_creation_input_tokens=0,
                         cache_read_input_tokens=3, output_tokens=4),
    ])
    gemini = _write_jsonl(sources / "gemini.jsonl", [_gemini_message("turn", input=12, output=2)])
    copilot = sources / "billing.csv"
    copilot.write_text("date,model,aic_quantity\n2026-11-27,model-a,7\n", encoding="utf-8")
    events = sources / "events.json"
    events.write_text('[{"category":"unplanned_rescue"}]', encoding="utf-8")
    before = {file.name: file.read_bytes() for file in sources.iterdir()}
    common = [
        sys.executable, "-I", "-S", str(REPO_ROOT / "scripts" / "g4_work_item_observer.py"),
        "--work-item-id", "WI-S0", "--title", "Multi-provider", "--rollout-dir", str(codex),
        "--expected-session-id", "codex-session",
    ]
    base, extended = tmp_path / "base", tmp_path / "extended"
    subprocess.run([*common, "--output-dir", str(base)], check=True, capture_output=True)
    subprocess.run([
        *common, "--output-dir", str(extended),
        "--claude-dir", str(claude), "--claude-dir", str(claude),
        "--claude-expected-session-id", "cs", "--claude-expected-session-id", "cs",
        "--gemini-dir", str(gemini), "--gemini-dir", str(gemini), "--gemini-expected-session-id", "gemini",
        "--copilot-csv", str(copilot), "--copilot-csv", str(copilot),
        "--outer-orchestrator", "owner-observed-orchestrator",
        "--events-file", str(events), "--rescue-evidence-ref", "PR#21", "--rescue-evidence-ref", "owner-note#1",
        "--rescue-confirmed-none",
    ], check=True, capture_output=True)
    baseline = json.loads((base / "evidence_index.json").read_text(encoding="utf-8"))
    extended_json = (extended / "evidence_index.json").read_text(encoding="utf-8")
    result = json.loads(extended_json)
    assert result["read_only"] is True
    assert result["schema_version"] == baseline["schema_version"]
    assert baseline["ai_cost"]["cross_provider_summation_allowed"] is False
    assert "providers" not in baseline["ai_cost"]
    assert {key: value for key, value in result["ai_cost"].items() if key != "providers"} == baseline["ai_cost"]
    assert result["ai_cost"]["verified_complete_totals"]["total_tokens"] == 130
    assert result["ai_cost"]["comparability_token"] == 1
    providers = result["ai_cost"]["providers"]
    assert set(providers) == {"claude", "gemini", "copilot", "outer_orchestrator"}
    assert providers["claude"]["cost_completeness"] == "complete"
    assert providers["gemini"]["cost_completeness"] == "incomplete"
    assert providers["gemini"]["known_totals"]["uncached_input_tokens"] is None
    assert providers["copilot"]["by_model_aic"] == {"model-a": 7.0}
    assert providers["outer_orchestrator"] == {
        "provider": "owner-observed-orchestrator",
        "presence_state": "unknown",
        "unit": None,
        "reason": "no_verifiable_local_token_rollout",
    }
    assert "human_intervention" not in result
    assert result["human_interventions"]["unexpected_rescue_observed"] == "yes"
    assert result["human_interventions"]["rescue_evidence_refs"] == ["PR#21", _expected_ref(events), "owner-note#1"]
    assert result["human_interventions"]["notes"] == ["rescue_evidence_conflicts_with_confirmed_none"]
    assert baseline["human_interventions"]["unexpected_rescue_observed"] == "unknown"
    base_md, report = [(directory / "report.md").read_text(encoding="utf-8") for directory in (base, extended)]
    assert "現有證據不足以確認是否曾發生救援" in base_md
    assert "antigravity" not in base_md
    assert "| 是否觀察到意外人工救援 | `yes`" in report
    codex_line = next(line for line in base_md.splitlines() if line.startswith("| 完整 AI Tokens / 成本 |"))
    assert codex_line in report and "130" in codex_line
    assert "| Claude Code | `measured`；單位 `tokens`；完整度 `complete`（範圍 `provider_sessions_only`）" in report
    assert "| Gemini CLI | `measured`；單位 `tokens`；完整度 `incomplete`" in report
    assert "| Copilot Billing Reference | `billing_reference_only`；單位 `aic_quantity`" in report
    assert "| Outer Orchestrator（owner-observed-orchestrator） | `unknown`；單位未知；未評估完整度" in report
    assert str(tmp_path) not in report
    assert str(tmp_path) not in extended_json
    assert tmp_path.as_posix() not in extended_json
    assert {file.name: file.read_bytes() for file in sources.iterdir()} == before


def test_provider_opt_in_and_confirmed_no_rescue_through_cli(tmp_path: Path):
    args = ["--work-item-id", "WI-UNUSED", "--title", "Opt in", "--output-dir", str(tmp_path)]
    assert observer.main([*args, "--gemini-dir", str(tmp_path / "missing")]) == 0
    evidence = json.loads((tmp_path / "evidence_index.json").read_text(encoding="utf-8"))
    assert set(evidence["ai_cost"]["providers"]) == {"gemini"}
    assert evidence["ai_cost"]["providers"]["gemini"]["presence_state"] == "unknown"
    assert "| Gemini CLI | `unknown`" in (tmp_path / "report.md").read_text(encoding="utf-8")

    assert observer.main([
        *args, "--claude-confirmed-unused", "--gemini-confirmed-unused", "--copilot-confirmed-unused",
        "--rescue-confirmed-none",
    ]) == 0
    confirmed = json.loads((tmp_path / "evidence_index.json").read_text(encoding="utf-8"))
    assert {key: item["presence_state"] for key, item in confirmed["ai_cost"]["providers"].items()} == {
        "claude": "confirmed_unused", "gemini": "confirmed_unused", "copilot": "confirmed_unused",
    }
    assert confirmed["human_interventions"]["unexpected_rescue_observed"] == "no"
    assert "| 是否觀察到意外人工救援 | `no`" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_observer_has_no_database_imports():
    tree = ast.parse(Path(observer.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    if hasattr(sys, "stdlib_module_names"):
        assert imported <= sys.stdlib_module_names
    assert not {"sqlite3", "_sqlite3", "codeburn"} & imported
