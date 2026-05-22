from governance_tools.daily_memory_gate import validate_structural_traceability


def _base_lines(branch: str = "feature/x", commit: str = "abc1234") -> list[str]:
    return [
        f"branch: {branch}",
        f"commits: {commit}",
        "changed_files_summary: updated memory pipeline and tests",
        "test_evidence: python -m pytest tests/test_memory_pipeline.py -q => 5 passed",
        "open_risks: none",
        "next_step: monitor next session_end behavior",
    ]


def test_pass_required_sections_branch_match_outgoing_commit_mentioned():
    result = validate_structural_traceability(
        added_lines=_base_lines(),
        branch_name="feature/x",
        outgoing_commit_hashes=["abc1234deadbeef"],
    )
    assert result.ok is True


def test_fail_missing_required_section():
    lines = _base_lines()
    lines = [x for x in lines if not x.startswith("next_step:")]
    result = validate_structural_traceability(
        added_lines=lines,
        branch_name="feature/x",
        outgoing_commit_hashes=["abc1234deadbeef"],
    )
    assert result.ok is False
    assert result.code == "DAILY_MEMORY_MISSING_REQUIRED_SECTION"


def test_fail_branch_mismatch():
    result = validate_structural_traceability(
        added_lines=_base_lines(branch="feature/y"),
        branch_name="feature/x",
        outgoing_commit_hashes=["abc1234deadbeef"],
    )
    assert result.ok is False
    assert result.code == "DAILY_MEMORY_MISSING_REQUIRED_SECTION"


def test_fail_placeholder_tokens():
    lines = _base_lines()
    lines[2] = "changed_files_summary: TODO"
    result = validate_structural_traceability(
        added_lines=lines,
        branch_name="feature/x",
        outgoing_commit_hashes=["abc1234deadbeef"],
    )
    assert result.ok is False
    assert result.code == "DAILY_MEMORY_PLACEHOLDER_PRESENT"


def test_fail_required_section_na_only():
    lines = _base_lines()
    lines[4] = "open_risks: N/A"
    result = validate_structural_traceability(
        added_lines=lines,
        branch_name="feature/x",
        outgoing_commit_hashes=["abc1234deadbeef"],
    )
    assert result.ok is False
    assert result.code == "DAILY_MEMORY_PLACEHOLDER_PRESENT"


def test_fail_memory_commit_not_in_outgoing_range():
    result = validate_structural_traceability(
        added_lines=_base_lines(commit="fffffff"),
        branch_name="feature/x",
        outgoing_commit_hashes=["abc1234deadbeef"],
    )
    assert result.ok is False
    assert result.code == "DAILY_MEMORY_COMMIT_NOT_IN_OUTGOING_RANGE"


def test_fail_outgoing_exists_but_memory_mentions_no_commit():
    lines = _base_lines()
    lines[1] = "commits: listed in PR only"
    result = validate_structural_traceability(
        added_lines=lines,
        branch_name="feature/x",
        outgoing_commit_hashes=["abc1234deadbeef"],
    )
    assert result.ok is False
    assert result.code == "DAILY_MEMORY_OUTGOING_COMMIT_NOT_DESCRIBED"

