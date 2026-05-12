from governance_tools.ab_cost_hygiene import normalize_ledger_cost_fields, validate_ledger_cost_hygiene


def test_normalize_replaces_tbd_in_cost_fields() -> None:
    sample = (
        '| 2026-05-07-fsr-A | A | t | false | false | merge | 4 | TBD | TBD |\n'
        '  actionable_fix_latency_sec: "TBD"\n'
        '  tokens_per_reviewer_accepted_fix: "TBD"\n'
    )
    normalized, replacements = normalize_ledger_cost_fields(sample)
    assert replacements == 3
    assert "insufficient_data" in normalized
    assert "| insufficient_data | TBD |" in normalized
    assert 'actionable_fix_latency_sec: "insufficient_data"' in normalized
    assert 'tokens_per_reviewer_accepted_fix: "insufficient_data"' in normalized


def test_validator_flags_zero_values() -> None:
    sample = (
        "| 2026-05-07-fsr-A | A | t | false | false | merge | 4 | 0 | TBD |\n"
        "  actionable_fix_latency_sec: 0\n"
        '  tokens_per_reviewer_accepted_fix: "insufficient_data"\n'
    )
    issues = validate_ledger_cost_hygiene(sample)
    reasons = {issue.reason for issue in issues}
    assert "zero_value_requires_explicit_measurement_context" in reasons
