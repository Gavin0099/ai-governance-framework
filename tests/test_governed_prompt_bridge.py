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



def test_normalize_provider_accepts_copilot() -> None:
    """AGR-09 §3.2: governed_prompt supports copilot, so the bridge must too."""
    assert normalize_provider("copilot") == "copilot"
    assert normalize_provider("Copilot") == "copilot"


def test_bridge_provider_set_matches_governed_prompt() -> None:
    """The two surfaces must not disagree about which providers exist."""
    from governance_tools.governed_prompt import VALID_PROVIDERS
    from governance_tools.governed_prompt_bridge import PROVIDER_ALIASES

    assert VALID_PROVIDERS <= set(PROVIDER_ALIASES.values())
