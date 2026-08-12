from __future__ import annotations

from pathlib import Path

import pytest

from governance_tools.copilot_instructions_projection import (
    CANONICAL_SECTION_HEADING,
    PROJECTION_TARGETS,
    build_parser,
    check_all_projections,
    canonical_source_token,
    extract_projection_region,
    main,
    CHECKPOINT_PROJECTION_VERSION,
    PROJECTION_BEGIN_PREFIX,
    PROJECTION_END,
    check_projection,
    extract_canonical_section,
    parse_projection_header,
    render_projection_block,
    render_template,
    section_digest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

_SYSTEM_PROMPT = f"""# SYSTEM_PROMPT.md

## 2. Something

{CANONICAL_SECTION_HEADING}

在以下時點輸出此 block：
- task 開始
- milestone 完成

```text
[Governance Contract]
LANG     = <value>
```

格式錯誤的 contract block 屬於 governance failure。

---

## 3. Document Priority
"""

_TEMPLATE = f"""<!-- AI Governance Framework: copilot-instructions BEGIN -->
# Copilot Workspace Instructions

## Governance Contract Output (MANDATORY)

{PROJECTION_BEGIN_PREFIX} version=0.0 source=governance/SYSTEM_PROMPT.md#2.8 sha256={'0' * 64} -->
stale content
{PROJECTION_END}

### Surface adaptation: incomplete governance context

trailing framework prose
<!-- AI Governance Framework: copilot-instructions END -->
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_framework(root: Path) -> Path:
    _write(root / "governance" / "SYSTEM_PROMPT.md", _SYSTEM_PROMPT)
    _write(root / "governance" / "copilot-instructions-template.md", _TEMPLATE)
    return root


def test_extract_canonical_section_stops_at_next_boundary() -> None:
    section = extract_canonical_section(_SYSTEM_PROMPT)

    assert section.startswith(CANONICAL_SECTION_HEADING)
    assert "milestone 完成" in section
    assert "[Governance Contract]" in section
    assert section.endswith("格式錯誤的 contract block 屬於 governance failure。")
    assert "Document Priority" not in section


def test_extract_canonical_section_rejects_missing_heading() -> None:
    with pytest.raises(ValueError, match="canonical section not found"):
        extract_canonical_section("# SYSTEM_PROMPT.md\n\n## 3. Elsewhere\n")


def test_projection_header_carries_version_and_canonical_digest() -> None:
    section = extract_canonical_section(_SYSTEM_PROMPT)
    header = parse_projection_header(render_projection_block(section))

    assert header is not None
    assert header["version"] == CHECKPOINT_PROJECTION_VERSION
    assert header["source"] == "governance/SYSTEM_PROMPT.md#2.8"
    assert header["sha256"] == section_digest(section)


def test_render_template_replaces_only_the_projection_region() -> None:
    rendered = render_template(_TEMPLATE, _SYSTEM_PROMPT)

    assert "stale content" not in rendered
    assert "milestone 完成" in rendered
    # Hand-written parts of the template survive the projection.
    assert "### Surface adaptation: incomplete governance context" in rendered
    assert "trailing framework prose" in rendered
    assert rendered.count(PROJECTION_END) == 1


def test_render_template_is_idempotent() -> None:
    once = render_template(_TEMPLATE, _SYSTEM_PROMPT)
    twice = render_template(once, _SYSTEM_PROMPT)

    assert once == twice


def test_render_template_rejects_ambiguous_projection_region() -> None:
    doubled = _TEMPLATE + f"\n{PROJECTION_BEGIN_PREFIX} version=1.1 source=x sha256={'0' * 64} -->\n{PROJECTION_END}\n"

    with pytest.raises(ValueError, match="exactly one checkpoint projection region"):
        render_template(doubled, _SYSTEM_PROMPT)


def test_check_projection_reports_drift_then_write_fixes_it(tmp_path: Path) -> None:
    framework = _make_framework(tmp_path / "framework")

    before = check_projection(framework)
    assert before.ok is False
    assert before.drift is True
    assert before.found_version == "0.0"
    assert before.found_sha256 != before.expected_sha256

    written = check_projection(framework, write=True)
    assert written.written is True
    assert written.ok is True

    after = check_projection(framework)
    assert after.ok is True
    assert after.drift is False
    assert after.written is False
    assert after.found_sha256 == after.expected_sha256


def test_check_projection_detects_canonical_edits(tmp_path: Path) -> None:
    framework = _make_framework(tmp_path / "framework")
    check_projection(framework, write=True)

    source = framework / "governance" / "SYSTEM_PROMPT.md"
    source.write_text(
        _SYSTEM_PROMPT.replace("- milestone 完成", "- milestone 完成\n- scope 改變"),
        encoding="utf-8",
    )

    assert check_projection(framework).drift is True


def test_shipped_template_projection_matches_canonical_source() -> None:
    """The checked-in template must not drift from governance/SYSTEM_PROMPT.md."""
    result = check_projection(REPO_ROOT)

    assert result.errors == []
    assert result.drift is False
    assert result.found_version == CHECKPOINT_PROJECTION_VERSION
    assert result.found_sha256 == result.expected_sha256


def test_check_flag_is_explicit_and_does_not_write(tmp_path: Path) -> None:
    framework = _make_framework(tmp_path / "framework")
    template = framework / "governance" / "copilot-instructions-template.md"
    before = template.read_bytes()

    exit_code = main(["--framework-root", str(framework), "--check", "--format", "json"])

    assert exit_code == 1  # drifted
    assert template.read_bytes() == before


def test_check_and_write_are_mutually_exclusive(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--check", "--write"])


def test_extract_projection_region_returns_body_for_digest_recomputation() -> None:
    rendered = render_template(_TEMPLATE, _SYSTEM_PROMPT)

    header, body, begin, end = extract_projection_region(rendered)

    assert begin < end
    assert header["sha256"] == section_digest(body)
    assert header["source"] == canonical_source_token()
    assert PROJECTION_BEGIN_PREFIX not in body
    assert PROJECTION_END not in body


def test_extract_projection_region_rejects_reversed_markers() -> None:
    reversed_region = f"{PROJECTION_END}\nbody\n{PROJECTION_BEGIN_PREFIX} version=1.1 source=x sha256={'0' * 64} -->\n"

    with pytest.raises(ValueError, match="END marker precedes BEGIN"):
        extract_projection_region(reversed_region)


def test_every_declared_surface_carries_the_projection() -> None:
    """Cross-agent parity: each agent reads a different file; all must carry the rules."""
    results = check_all_projections(REPO_ROOT)

    assert {r.surface for r in results} == {"copilot", "codex"}
    for result in results:
        assert result.ok is True, (result.surface, result.errors)
        assert result.drift is False, result.surface
        assert result.found_version == CHECKPOINT_PROJECTION_VERSION, result.surface


def test_all_surfaces_project_the_same_canonical_digest() -> None:
    """Parity is the same rules, not merely each file having some rules."""
    digests = {r.found_sha256 for r in check_all_projections(REPO_ROOT)}

    assert len(digests) == 1
    assert digests.pop() == section_digest(
        extract_canonical_section((REPO_ROOT / "governance" / "SYSTEM_PROMPT.md").read_text(encoding="utf-8"))
    )


def test_agents_md_is_a_declared_surface() -> None:
    """Codex reads AGENTS.md; before this it carried no contract rules at all."""
    assert ("AGENTS.md", "codex") in PROJECTION_TARGETS


def test_a_surface_missing_its_region_is_an_error_not_a_skip(tmp_path: Path) -> None:
    framework = _make_framework(tmp_path / "framework")
    _write(framework / "AGENTS.md", "# AGENTS\n\nno projection region here\n")

    results = check_all_projections(framework)
    codex = next(r for r in results if r.surface == "codex")

    assert codex.ok is False
    assert any("projection region" in e for e in codex.errors)
