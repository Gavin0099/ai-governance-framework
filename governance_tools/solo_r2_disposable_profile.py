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

# Exactly one separately adopted replacement; never replace the historical pins.
REPLACEMENT_LEDGER_PATH = Path("artifacts/evidence/solo-r2-replacement-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson")
REPLACEMENT_BINDING_PATH = Path("memory/evidence/solo-r2-replacement-disposable-mechanism-shakedown-20260906/genesis-binding.json")
REPLACEMENT_RUNTIME_ROOT = Path("D:/r2-replacement-disposable-shakedown-20260906")
REPLACEMENT_DECISION_SHA256 = "bbc12627300df01f0145ba0b76aa75191291b3974ccf95dd1255fb4f031bafd3"
FAILED_LEDGER_SHA256 = "649b2d40c25460647247601ea18e7f2465a07280d58fad8ff7e96c003e0a0836"
REPLACEMENT_DOCUMENTS = (
    ("f75a78eeb32bf79e58a91898d0775fd3f58854b8", "docs/governance/solo-r2-replacement-disposable-owner-decision-candidate-20260906.md", REPLACEMENT_DECISION_SHA256),
    ("f75a78eeb32bf79e58a91898d0775fd3f58854b8", "docs/governance/solo-r2-replacement-disposable-owner-adoption-20260906.json", "cec44fbd4193e9fed85dbfce6f3824d11f49251c69c45c9d45fabeebe9f7e980"),
    ("622e1d9def23af1eac2ea1fbea7b5eadf136d7b0", "docs/governance/solo-r2-replacement-binding-proposal-20260906.md", "e3e593376f0c4ead5a837f5127393d55e625f09aa9399c2778801f71395227f9"),
    ("622e1d9def23af1eac2ea1fbea7b5eadf136d7b0", "docs/governance/solo-r2-replacement-binding-owner-adoption-20260906.json", "544bbe976edc4eab9b77fee0411651324889be6b816ff6db5a1ed49a01d0d799"),
)

COST_ADOPTION_COMMIT = "eb70b863d53eb68c6ee692f84634604877a60b17"
COST_AMENDMENT_PATH = "docs/governance/solo-r2-v2.1-unavailable-cost-amendment-candidate-20260906.md"
COST_AMENDMENT_SHA256 = "c9829c719c5a73736559819c6f8c6fac257c1ae012eda47a4e505aa064f12fad"
COST_ADOPTION_PATH = "docs/governance/solo-r2-v2.1-unavailable-cost-owner-adoption-20260906.json"
COST_ADOPTION_SHA256 = "be92d5d1b670dd9aa04db2076de653eb8a89d87a689a57ba1c44383f364a5b7e"
# Existing external launcher's controller namespace; not caller-selected custody.
COST_CONTROLLER_ROOT = Path("D:/r2-disposable-shakedown-20260906/controller")

# Trust anchors for the adopted documents, not duplicate descriptions of inputs.
ADOPTED_DOCUMENTS = (
    ("a081eb1ff4fa91e4b9932b5a3164ad118d5ddba4", "docs/governance/solo-r2-input-authority-schema-amendment-20260906.md", AMENDMENT_SHA256),
    ("a081eb1ff4fa91e4b9932b5a3164ad118d5ddba4", "docs/governance/solo-r2-v2.1-schema-owner-adoption-20260906.json", "d965066ad1d4ef4a0fe00e53c82f38fc31a8673f8f436a40e806b55afcb00b64"),
    ("744ba9973f70bede1eb93137f12e1b8110b0e5c7", "docs/governance/solo-r2-d2-allocation-owner-decision-20260906.json", ALLOCATION_SHA256),
    ("cab2c62d135dd220d0aa7f9f143a19b23cd6cc0a", "docs/governance/solo-r2-disposable-ledger-placement-contract-20260906.md", PLACEMENT_SHA256),
    ("cab2c62d135dd220d0aa7f9f143a19b23cd6cc0a", "docs/governance/solo-r2-disposable-placement-owner-adoption-20260906.json", "0bac2f52e3fe3e4c990efecfd83b332627f5742b82efa38b032de09cdacaac9c"),
)
