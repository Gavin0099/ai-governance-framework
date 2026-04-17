from pathlib import Path


def test_root_memory_md_must_not_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert not (repo_root / "MEMORY.md").exists(), (
        "Repo root MEMORY.md is forbidden. Use memory/00_long_term.md instead."
    )
