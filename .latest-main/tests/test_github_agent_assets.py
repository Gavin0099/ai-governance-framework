from pathlib import Path


ROOT = Path(__file__).parent.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_copilot_instructions_exists():
    path = ROOT / ".github" / "copilot-instructions.md"
    content = _read(path)
    assert "AI Coding Runtime Governance Framework" in content
    assert "Prefer minimal, reviewable changes" in content


def test_agent_definitions_exist():
    agent_paths = [
        ROOT / ".github" / "agents" / "advanced-agent.agent.md",
        ROOT / ".github" / "agents" / "python-agent.agent.md",
        ROOT / ".github" / "agents" / "cli-agent.agent.md",
    ]
    for path in agent_paths:
        content = _read(path)
        assert content.startswith("---\nname:")
        assert "model: gpt-5" in content


def test_skill_definitions_exist():
    skill_paths = [
        ROOT / ".github" / "skills" / "code-style" / "skill.md",
        ROOT / ".github" / "skills" / "python" / "skill.md",
        ROOT / ".github" / "skills" / "governance-runtime" / "skill.md",
        ROOT / ".github" / "skills" / "human-readable-cli" / "skill.md",
    ]
    for path in skill_paths:
        content = _read(path)
        assert content.startswith("---\nname:")
        assert "description:" in content
