"""Tests for the read-only G4 Work Item Observer (scripts/g4_work_item_observer.py)."""
from __future__ import annotations

import json
import os
from pathlib import Path
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
