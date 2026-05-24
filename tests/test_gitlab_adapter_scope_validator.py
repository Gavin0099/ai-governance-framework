from __future__ import annotations

from pathlib import Path

from governance_tools.gitlab_adapter_scope_validator import validate_adapter_file


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_detects_override_fetch_scope_mismatch(tmp_path: Path) -> None:
    adapter = tmp_path / "gitlab-wiki-adapter.ts"
    _write(
        adapter,
        """
export class GitLabWikiAdapter {
  async listPages(opts = {}) {
    const projectId = opts.projectId?.toString() ?? this.projectId;
  }
  private async _fetchPage(slug: string) {
    const url = `${this.baseUrl}/api/v4/projects/${encodeURIComponent(this.projectId)}/wikis/${encodeURIComponent(slug)}`;
  }
}
""".strip(),
    )

    result = validate_adapter_file(adapter)
    assert result.valid is False
    assert any("opts.projectId" in msg for msg in result.errors)


def test_accepts_project_aware_fetch_scope(tmp_path: Path) -> None:
    adapter = tmp_path / "gitlab-wiki-adapter.ts"
    _write(
        adapter,
        """
export class GitLabWikiAdapter {
  private slugToProject = new Map<string, string>();
  async listPages(opts = {}) {
    const projectId = opts.projectId?.toString() ?? this.projectId;
    this.slugToProject.set("abc", projectId);
  }
  private async _fetchPage(slug: string) {
    const projectId = this.slugToProject.get(slug) ?? this.projectId;
    const url = `${this.baseUrl}/api/v4/projects/${encodeURIComponent(projectId)}/wikis/${encodeURIComponent(slug)}`;
  }
}
""".strip(),
    )

    result = validate_adapter_file(adapter)
    assert result.valid is True
    assert result.errors == []


def test_warns_when_override_not_supported(tmp_path: Path) -> None:
    adapter = tmp_path / "gitlab-wiki-adapter.ts"
    _write(
        adapter,
        """
export class GitLabWikiAdapter {
  async listPages() { return []; }
}
""".strip(),
    )

    result = validate_adapter_file(adapter)
    assert result.valid is True
    assert any("not detected" in msg for msg in result.warnings)
