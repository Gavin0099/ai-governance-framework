# Hermes Side No-Tool Evidence Design Disposition - 2026-06-30

Status: disposition note
Scope: cross-repo evidence status for future Hermes real provider evidence

## Summary

Hermes real provider evidence remains blocked.

The AI Governance repository has a documented evidence plan and blocker
disposition for a future Hermes model/provider run, but a real run must not be
treated as governance evidence until Hermes has a reviewed no-tool/no-MCP
execution constraint.

The Hermes-side design proposal now exists in the user's fork:

- Repository: `Gavin0099/hermes-agent`
- Fork main: `8603826e4`
- Original design branch commit: `3a954a3`
- Design file: `docs/design/acp-no-tool-no-mcp-evidence-mode.md`

This records that the design proposal exists. It does not unblock provider
execution.

## Evidence

Read-only remote verification on 2026-06-30 showed:

```text
refs/heads/main = 8603826e490dee087920f357b4d0fc3550de6f4a
refs/heads/codex/acp-no-tool-evidence-mode = 3a954a3a48a2ba6b0ccee69180b420f320b3489b
```

The fork main commit is a cherry-pick of the original Hermes-side docs-only
design commit onto the user's fork main. Upstream
`NousResearch/hermes-agent:main` was not updated by this work.

## Current Claim

Allowed claim:

- A Hermes-side design proposal exists for an ACP no-tool/no-MCP evidence mode.
- The proposal is available in the user's fork main.
- Real Hermes provider evidence remains blocked until implementation and review.

Not allowed:

- Hermes has implemented no-tool/no-MCP evidence mode.
- A provider/model run has been performed.
- Provider credentials have been used or validated.
- The future evidence packet is provider-safe.
- The evidence mode is non-bypassable.
- Upstream Hermes has accepted or merged the design.
- AI Governance now enforces Hermes runtime behavior.

## Next Required Work Before Any Real Provider Run

The next meaningful work is Hermes-side implementation, not more AI Governance
packet wording.

Minimum future sequence:

1. Implement an ACP no-tool/no-MCP execution constraint in Hermes.
2. Prove, with focused tests, that the provider request receives no tool
   schemas and no MCP discovery occurs.
3. Review that implementation separately.
4. Produce a concrete preflight packet for the selected provider, model, prompt,
   and artifact paths.
5. Obtain explicit operator authorization before any credential use or provider
   execution.

Until those steps exist, AI Governance should keep the status as design-only /
blocked for real provider evidence.
