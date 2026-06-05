from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parent.parent
CONTRACT = (
    ROOT
    / "codeburn"
    / "phase2"
    / "CODEBURN_SAME_PROVIDER_VISIBLE_IO_TOKEN_SUM_CONTRACT_2026-06-05.md"
)
SCHEMA = ROOT / "codeburn" / "phase1" / "schema.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_visible_io_contract_declares_required_guardrails():
    text = _read(CONTRACT)

    required_terms = [
        "visible_io_token_sum",
        "visible_io_token_sum = prompt_tokens + completion_tokens",
        "evidence_class = Class C",
        "visible_io_token_sum_authority = observation_only",
        "billing_truth = false",
        "decision_usage_allowed = false",
        "analysis_safe_for_decision = false",
        "cross_provider_comparable = false",
        "efficiency_inference_allowed = false",
        "missing_field_policy = null_not_zero",
    ]

    for term in required_terms:
        assert term in text


def test_visible_io_contract_keeps_scope_same_provider_only():
    text = _read(CONTRACT)

    required_scope_terms = [
        'provider = "codex"',
        'provider = "claude-code"',
        "Codex + Claude Code combined summaries",
        "Provider-agnostic token totals",
        "Cross-provider averages",
        "Any query that groups multiple providers into one token value",
    ]

    for term in required_scope_terms:
        assert term in text


def test_visible_io_contract_forbids_misleading_total_names():
    text = _read(CONTRACT)

    forbidden_name_terms = [
        "`total_tokens`",
        "`session_total_tokens`",
        "`billing_tokens`",
        "`cost_tokens`",
        "`combined_tokens`",
        "`normalized_tokens`",
        "`equivalent_tokens`",
    ]

    for term in forbidden_name_terms:
        assert term in text


def test_visible_io_contract_blocks_cache_reasoning_and_billing_folding():
    text = _read(CONTRACT)

    blocked_fields = [
        "Codex `reasoning_output_tokens`",
        "Codex `cached_input_tokens`",
        "Codex `total_token_usage.*`",
        "Claude Code `cache_creation_input_tokens`",
        "Claude Code `cache_read_input_tokens`",
        "Service tier, model, routing, billing, or cost metadata",
    ]

    for term in blocked_fields:
        assert term in text


def test_visible_io_contract_is_not_schema_or_report_implementation():
    assert "visible_io_token_sum" not in _read(SCHEMA)

    report_or_cli_files = [
        ROOT / "codeburn" / "phase1" / "codeburn_session_display.py",
        ROOT / "codeburn" / "phase1" / "codeburn_run.py",
        ROOT / "codeburn" / "phase2" / "codeburn_codex_smoke.py",
        ROOT / "codeburn" / "phase2" / "codeburn_copilot_smoke.py",
        ROOT / "codeburn" / "phase2" / "codeburn_manual_usage_ingest.py",
    ]

    offenders = [
        str(path.relative_to(ROOT))
        for path in report_or_cli_files
        if "visible_io_token_sum" in _read(path)
    ]

    assert offenders == []
