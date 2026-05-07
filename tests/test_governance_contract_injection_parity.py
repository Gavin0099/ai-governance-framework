from governance_tools.contract_renderer import GovernanceContract
from governance_tools.governed_prompt import build_governed_prompt


def _contract() -> GovernanceContract:
    return GovernanceContract(
        lang="C++",
        level="L0",
        scope="review",
        plan="Phase 1 / Offer packet review",
        loaded="SYSTEM_PROMPT, HUMAN-OVERSIGHT, AGENT",
        context="offer packet review -> check format; NOT: protocol rewrite",
        pressure="SAFE (40/200)",
    )


def test_all_provider_paths_inject_same_contract_prefix() -> None:
    prompt = "Please review the offer packet."
    contract = _contract()
    outputs = {
        provider: build_governed_prompt(contract, prompt)
        for provider in ("copilot", "chatgpt", "claude", "gemini")
    }

    first = outputs["copilot"]
    for provider, rendered in outputs.items():
        assert rendered.startswith("[Governance Contract]\n"), provider
        for field_name in ("LANG", "LEVEL", "SCOPE", "PLAN", "LOADED", "CONTEXT", "PRESSURE"):
            assert f"{field_name} = " in rendered, (provider, field_name)
        assert rendered == first, f"{provider} path drifted from canonical injection"

