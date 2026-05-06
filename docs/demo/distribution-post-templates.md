# Distribution Post Templates

## X / Twitter (short)
We built an AI governance runtime that turns AI coding work from black-box output into reviewable evidence.

What it does:
- pre/post task checks
- contract-aware violation detection
- reviewer handoff artifacts

Not a decision engine.
It gives humans better evidence for decisions.

Repo: https://github.com/Gavin0099/ai-governance-framework

## Reddit / HN (longer)
When using Claude/Cursor/Copilot for coding, the hard part is not getting output — it's verifying whether that output respected project constraints.

This repo implements a governance layer between AI execution and human review:
- session lifecycle hooks (start / pre / post / end)
- contract-aware checks
- evidence artifacts + reviewer handoff surfaces
- non-authoritative token observability (explicitly not for automated decision)

Example blocked case:
AI directly calls DB in a handler, violating architecture contract; runtime returns structured violation + remediation.

README and demo:
- https://github.com/Gavin0099/ai-governance-framework
- docs/demo/before-after.md
