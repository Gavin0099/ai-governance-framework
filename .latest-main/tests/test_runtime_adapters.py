from pathlib import Path


ADAPTERS = [
    Path("runtime_hooks/adapters/claude_code/pre_task.py"),
    Path("runtime_hooks/adapters/claude_code/post_task.py"),
    Path("runtime_hooks/adapters/claude_code/normalize_event.py"),
    Path("runtime_hooks/adapters/codex/pre_task.py"),
    Path("runtime_hooks/adapters/codex/post_task.py"),
    Path("runtime_hooks/adapters/codex/normalize_event.py"),
    Path("runtime_hooks/adapters/gemini/pre_task.py"),
    Path("runtime_hooks/adapters/gemini/post_task.py"),
    Path("runtime_hooks/adapters/gemini/normalize_event.py"),
]


def test_adapter_files_exist():
    for adapter in ADAPTERS:
        assert adapter.exists(), f"missing adapter: {adapter}"


def test_adapter_sources_reference_core_entrypoints():
    expectations = {
        "pre_task.py": "shared_adapter_runner",
        "post_task.py": "shared_adapter_runner",
        "normalize_event.py": "shared_normalizer",
    }
    for adapter in ADAPTERS:
        text = adapter.read_text(encoding="utf-8")
        assert expectations[adapter.name] in text
