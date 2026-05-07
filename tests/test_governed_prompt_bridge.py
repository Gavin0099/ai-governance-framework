import pytest

from governance_tools.governed_prompt_bridge import normalize_provider


def test_normalize_provider_accepts_primary_names() -> None:
    assert normalize_provider("chatgpt") == "chatgpt"
    assert normalize_provider("claude") == "claude"
    assert normalize_provider("gemini") == "gemini"


def test_normalize_provider_accepts_common_aliases() -> None:
    assert normalize_provider("chatgot") == "chatgpt"
    assert normalize_provider("gemnin") == "gemini"


def test_normalize_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError):
        normalize_provider("openrouter")

