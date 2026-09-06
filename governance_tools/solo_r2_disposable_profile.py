"""Exact adopted disposable profile; not a configurable ledger registry."""

from pathlib import Path

ROOT = Path("D:/ai-governance-framework")
LEDGER_PATH = Path("artifacts/evidence/solo-r2-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson")
BINDING_PATH = Path("memory/evidence/solo-r2-disposable-mechanism-shakedown-20260906/genesis-binding.json")
SCHEMA = "solo_attempt_ledger.v2.1"
AMENDMENT_SHA256 = "ced964f9166aa59a878faa3afdd96c19fe8accaf60a2788c4aaf5a8dbb4680ab"
SCHEMA_ID = f"{SCHEMA}@sha256:{AMENDMENT_SHA256}"
INPUT_SHA256 = "5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb"
INPUT_COMMIT = "d4d8e0f6b41d7c1837edd70f77214212d99ae372"
INPUT_PATH = "artifacts/experiments/solo-r2-disposable-input-definition-20260906/input-authority.owner-adopted.json"
PLACEMENT_SHA256 = "7300ab4c958d1569a64f3574cf26a3c9ac8489ed1ad1df89afea70429a689246"
ALLOCATION_SHA256 = "8a7e8cd74d883a733a5df887923b5eccf31ffe2ed0ed462446f15ae1066192b6"

# Trust anchors for the adopted documents, not duplicate descriptions of inputs.
ADOPTED_DOCUMENTS = (
    ("a081eb1ff4fa91e4b9932b5a3164ad118d5ddba4", "docs/governance/solo-r2-input-authority-schema-amendment-20260906.md", AMENDMENT_SHA256),
    ("a081eb1ff4fa91e4b9932b5a3164ad118d5ddba4", "docs/governance/solo-r2-v2.1-schema-owner-adoption-20260906.json", "d965066ad1d4ef4a0fe00e53c82f38fc31a8673f8f436a40e806b55afcb00b64"),
    ("744ba9973f70bede1eb93137f12e1b8110b0e5c7", "docs/governance/solo-r2-d2-allocation-owner-decision-20260906.json", ALLOCATION_SHA256),
    ("cab2c62d135dd220d0aa7f9f143a19b23cd6cc0a", "docs/governance/solo-r2-disposable-ledger-placement-contract-20260906.md", PLACEMENT_SHA256),
    ("cab2c62d135dd220d0aa7f9f143a19b23cd6cc0a", "docs/governance/solo-r2-disposable-placement-owner-adoption-20260906.json", "0bac2f52e3fe3e4c990efecfd83b332627f5742b82efa38b032de09cdacaac9c"),
)
