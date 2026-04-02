> **最後更新**: 2026-04-02
> **Owner**: framework-example
> **Freshness**: Sprint (7d)

# Active Task

Validate USB hub firmware governance onboarding through contract-aware runtime checks.

# Scope

- confirm contract discovery works from contract root
- confirm external rule packs are discoverable
- confirm session_start and pre_task_check run without hardcoded paths

# Evidence

- `governance_tools/domain_contract_loader.py`
- `runtime_hooks/core/session_start.py`
- `runtime_hooks/core/pre_task_check.py`
- `governance_tools/external_repo_smoke.py`
