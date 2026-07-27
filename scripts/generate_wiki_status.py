"""Generate the public repository-status Wiki page from an explicit allowlist."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "docs" / "wiki" / "generated" / "repository-status.md"

# Public-data boundary: do not broaden this list to memory/, artifacts/,
# receipts, transcripts, or consumer-specific evidence.
PUBLIC_TEXT_SOURCES = {
    "README": REPO_ROOT / "README.md",
    "PLAN": REPO_ROOT / "PLAN.md",
    "CHANGELOG": REPO_ROOT / "CHANGELOG.md",
}
PUBLIC_SKILL_GLOBS = (
    ".agents/skills/*/SKILL.md",
    ".claude/skills/*/SKILL.md",
)


def read_public_source(name: str) -> str:
    path = PUBLIC_TEXT_SOURCES[name]
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8-sig")


def first_match(pattern: str, text: str, fallback: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else fallback


def git_value(*args: str, fallback: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return fallback
    return result.stdout.strip() or fallback


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return {}
    _, frontmatter, *_ = text.split("---", maxsplit=2)
    result: dict[str, str] = {}
    for raw_line in frontmatter.splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", maxsplit=1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def discover_skills() -> list[tuple[str, str, str]]:
    discovered: dict[str, tuple[str, str, str]] = {}
    for pattern in PUBLIC_SKILL_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            metadata = parse_frontmatter(path)
            name = metadata.get("name", path.parent.name)
            description = metadata.get("description", "未提供 description")
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            discovered.setdefault(name, (name, description, relative_path))
    return sorted(discovered.values(), key=lambda item: item[0].lower())


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def main() -> int:
    readme = read_public_source("README")
    plan = read_public_source("PLAN")
    changelog = read_public_source("CHANGELOG")

    version = first_match(r"\*\*Version\s+([^*]+)\*\*", readme, "未辨識")
    test_count = first_match(r"([\d,]+\+)\s+tests", readme, "未辨識")
    plan_updated = first_match(r">\s*\*\*最後更新\*\*:\s*([^\n]+)", plan, "未辨識")
    latest_change = first_match(r"^##\s+(.+)$", changelog, "未辨識")
    commit = git_value("rev-parse", "HEAD", fallback="無 Git context")
    short_commit = commit[:12] if commit != "無 Git context" else commit
    if commit == "無 Git context":
        source_commit = short_commit
    else:
        source_commit = (
            f"[`{short_commit}`]"
            "(https://github.com/Gavin0099/ai-governance-framework/"
            f"commit/{commit})"
        )
    commit_time = git_value(
        "show",
        "-s",
        "--format=%cI",
        "HEAD",
        fallback=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    )
    skills = discover_skills()

    lines = [
        "# Repository 自動摘要",
        "",
        "> 此頁由公開 allowlist 在 build time 產生；它是導覽，不是 framework correctness 證明。",
        "",
        "## 建置來源",
        "",
        "| 欄位 | 值 |",
        "|---|---|",
        f"| Source commit | {source_commit} |",
        f"| Commit time | {markdown_escape(commit_time)} |",
        f"| README version | {markdown_escape(version)} |",
        f"| README test count | {markdown_escape(test_count)} |",
        f"| PLAN last updated | {markdown_escape(plan_updated)} |",
        f"| Latest CHANGELOG heading | {markdown_escape(latest_change)} |",
        f"| Skill metadata detected | {len(skills)} |",
        "",
        "## 公開 Skill metadata",
        "",
    ]

    if skills:
        lines.extend(
            [
                "| Skill | Description | Source |",
                "|---|---|---|",
            ]
        )
        for name, description, relative_path in skills:
            source_url = (
                "https://github.com/Gavin0099/ai-governance-framework/blob/"
                f"main/{relative_path}"
            )
            lines.append(
                f"| {markdown_escape(name)} | {markdown_escape(description)} | "
                f"[`{relative_path}`]({source_url}) |"
            )
    else:
        lines.append("目前 allowlist 路徑下未偵測到 Skill metadata。")

    lines.extend(
        [
            "",
            "## 來源邊界",
            "",
            "Generator 只讀取：",
            "",
            "- `README.md`",
            "- `PLAN.md`",
            "- `CHANGELOG.md`",
            "- `.agents/skills/*/SKILL.md` 的 frontmatter",
            "- `.claude/skills/*/SKILL.md` 的 frontmatter",
            "",
            "它不讀取或發布：",
            "",
            "- `memory/`",
            "- `artifacts/`",
            "- receipts 或 transcripts",
            "- consumer 私有資料",
            "- 其他未列入 allowlist 的 repo 內容",
            "",
            "## 不能從此頁宣稱",
            "",
            "- 版本字串代表 release 已完成；",
            "- test 數量代表 code quality；",
            "- Skill 數量代表 coding outcome 改善；",
            "- PLAN 更新日代表所有工作都已同步；",
            "- GitHub Pages build 成功代表治理機制有效。",
            "",
        ]
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
