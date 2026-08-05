#!/usr/bin/env python3
"""Bind strong claims to receipts from registered domain validators.

The division of labour
----------------------
The framework does not and must not understand any domain. It cannot tell
whether a driver installed, a device enumerated, or a scrape succeeded. What it
can and must decide is a different question:

    Was this PASS produced by an authorised semantic judgement, or is it prose?

So the domain owns the semantics — parse the tool output, decide what actually
happened, emit a receipt. The framework owns the binding — the claim kind is
registered, the receipt came from the registered validator, the validator ran,
the receipt is anchored to this session and commit, and its verdict is not
merely an exit code.

Without that binding, a strong claim has no standing. This module reports the
downgrade (``observed_unverified``); whether an unbound claim also blocks is a
policy decision, not this module's.

Claim ceiling — read this before quoting a ``bound`` result
-----------------------------------------------------------
``bound`` means the receipt *declares* a registered producer, is anchored to
this session and commit, cites resolvable evidence, and does not rest on an
exit code alone.

It does NOT prove the named validator ever ran. Every field checked here is
self-reported by the receipt, so an agent that writes the JSON by hand with
correct values passes this check. Producer authenticity needs things this
module does not yet have: an invocation id issued by a canonical runner, a
validator code digest, and a create-once entry in an invocation ledger the
producer cannot write to. Until those exist, the honest reading of ``bound``
is *schema-and-anchor consistent with a registered producer*, not *validated
by a registered validator*.

It also does not mean the validator's judgement is correct, that its coverage
is adequate, or that the underlying claim is true. The framework cannot know
any of those.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # pragma: no cover - direct-script fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.evidence_roots import (
    classify_evidence_path,
    load_evidence_root_policy,
)

REGISTRY_RELPATH = "governance/claim_binding_registry.json"
REGISTRY_SCHEMA = "claim_binding_registry.v0.1"
RECEIPT_SCHEMA = "domain_validator_receipt.v0.1"

STRENGTH_STRONG = "strong"
STRENGTH_OBSERVED = "observed"

VERDICT_BOUND = "bound"
VERDICT_UNBOUND = "unbound"
VERDICT_NOT_REQUIRED = "not_required"
DOWNGRADE_TO = "observed_unverified"

# What a `bound` verdict is actually built from. Named so a reader cannot
# mistake self-reported provenance for proof of execution.
BINDING_STRENGTH = "declared_producer_schema_and_anchor"

NOT_CLAIMED = (
    "that the named validator was ever executed",
    "that the receipt was produced by the validator rather than written by hand",
    "that the validator's judgement is correct",
    "that the validator's coverage is adequate",
    "that the underlying domain claim is true",
)

_REQUIRED_STR_FIELDS = (
    "claim_kind",
    "validator",
    "verdict",
    "verdict_basis",
    "command",
    "started_at",
    "finished_at",
    "session_id",
    "linked_commit",
)
_VALID_VERDICTS = frozenset({"pass", "fail", "inconclusive"})

# A verdict basis that only restates the process result is not a semantic
# judgement. This is the framework-level expression of "pnputil exit 0 is not a
# passing test": the domain must say what it checked, not that the tool exited.
_EXIT_CODE_ONLY = re.compile(
    r"^\s*(exit[_\s-]?code(\s*(==|=|:|is)?\s*0)?|returncode\s*0?|rc\s*0?|"
    r"exit(ed)?\s*(with\s*)?0|process\s+succeeded|no\s+error)\s*\.?\s*$",
    re.IGNORECASE,
)

_COMMIT_RE = re.compile(r"^[a-f0-9]{5,40}$", re.IGNORECASE)


@dataclass
class BindingResult:
    claim_kind: str
    verdict: str
    reasons: list[str] = field(default_factory=list)
    receipt_path: str | None = None
    validator: str | None = None
    claimed_strength: str = STRENGTH_STRONG
    effective_strength: str = STRENGTH_STRONG

    @property
    def bound(self) -> bool:
        return self.verdict == VERDICT_BOUND

    @property
    def satisfied(self) -> bool:
        """Whether the claim may retain its requested strength.

        Observed claims are accepted because binding is not required, not
        because a producer was bound to them.
        """
        return self.verdict in {VERDICT_BOUND, VERDICT_NOT_REQUIRED}

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_kind": self.claim_kind,
            "verdict": self.verdict,
            "reasons": self.reasons,
            "receipt_path": self.receipt_path,
            "validator": self.validator,
            "claimed_strength": self.claimed_strength,
            "effective_strength": self.effective_strength,
            "binding_strength": BINDING_STRENGTH if self.bound else None,
            "claim_ceiling": (
                "binding is not required for this observed-strength claim"
                if self.verdict == VERDICT_NOT_REQUIRED
                else (
                    "every checked field is self-reported by the receipt; binding "
                    "shows schema and anchor consistency with a registered "
                    "producer, not that the validator ran"
                )
            ),
            "not_claimed": (
                ["any producer or validator binding"]
                if self.verdict == VERDICT_NOT_REQUIRED
                else list(NOT_CLAIMED)
            ),
        }


# ── registry ──────────────────────────────────────────────────────────────────

def load_binding_registry(
    project_root: Path, registry_path: Path | None = None
) -> dict[str, Any]:
    """Load the claim→validator registry.

    A missing registry means no claim kind is registered, so every strong claim
    is unbound. It never means "everything is fine".
    """
    path = registry_path or (project_root / REGISTRY_RELPATH)
    if not path.is_file():
        return {"error": "registry_not_found", "bindings": {}, "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": f"registry_unreadable: {exc}", "bindings": {}, "path": str(path)}
    if not isinstance(payload, dict) or payload.get("registry_schema") != REGISTRY_SCHEMA:
        return {"error": "registry_schema_mismatch", "bindings": {}, "path": str(path)}

    bindings: dict[str, dict[str, Any]] = {}
    for entry in payload.get("bindings") or []:
        if not isinstance(entry, dict):
            continue
        claim_kind = str(entry.get("claim_kind") or "").strip()
        validator = str(entry.get("validator") or "").strip()
        if not claim_kind or not validator:
            continue
        bindings[claim_kind] = {
            "validator": validator,
            "strength": str(entry.get("strength") or STRENGTH_STRONG),
            "receipt_schema": str(entry.get("receipt_schema") or RECEIPT_SCHEMA),
        }
    return {"error": None, "bindings": bindings, "path": str(path)}


# ── receipt validation ────────────────────────────────────────────────────────

def validate_receipt_shape(payload: Any) -> list[str]:
    """Shape errors only. Says nothing about whether the recorded run happened."""
    if not isinstance(payload, dict):
        return ["receipt_not_an_object"]

    errors: list[str] = []
    if payload.get("receipt_schema") != RECEIPT_SCHEMA:
        errors.append("receipt_schema_mismatch")
    for name in _REQUIRED_STR_FIELDS:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"receipt_field_invalid:{name}")

    verdict = payload.get("verdict")
    if isinstance(verdict, str) and verdict.strip().lower() not in _VALID_VERDICTS:
        errors.append("receipt_field_invalid:verdict")

    exit_code = payload.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        errors.append("receipt_field_invalid:exit_code")

    evidence_paths = payload.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not all(
        isinstance(item, str) and item.strip() for item in evidence_paths
    ):
        errors.append("receipt_field_invalid:evidence_paths")

    cannot_claim = payload.get("cannot_claim")
    if (
        not isinstance(cannot_claim, list)
        or not cannot_claim
        or not all(isinstance(item, str) and item.strip() for item in cannot_claim)
    ):
        errors.append("receipt_field_invalid:cannot_claim")

    linked_commit = payload.get("linked_commit")
    if isinstance(linked_commit, str) and linked_commit.strip():
        candidate = linked_commit.strip()
        if candidate != "no_git_worktree" and not _COMMIT_RE.fullmatch(candidate):
            errors.append("receipt_field_invalid:linked_commit")

    return errors


def _commits_consistent(receipt_commit: str, claim_commit: str) -> bool:
    left = receipt_commit.strip().lower()
    right = claim_commit.strip().lower()
    if not left or not right:
        return False
    return left.startswith(right) or right.startswith(left)


# ── the binding check ─────────────────────────────────────────────────────────

def check_claim_binding(
    project_root: Path,
    *,
    claim_kind: str,
    receipt_path: str | None,
    session_id: str | None = None,
    commit: str | None = None,
    claimed_strength: str = STRENGTH_STRONG,
    registry: dict[str, Any] | None = None,
) -> BindingResult:
    """Decide whether a claim of the given strength is backed by a valid receipt.

    Every failure path downgrades rather than silently passing: an unbound
    strong claim becomes ``observed_unverified``.
    """
    result = BindingResult(
        claim_kind=claim_kind,
        verdict=VERDICT_UNBOUND,
        receipt_path=receipt_path,
        claimed_strength=claimed_strength,
        effective_strength=DOWNGRADE_TO,
    )

    # Observed-strength claims assert nothing a validator could confirm, so
    # they need no receipt and are left exactly as claimed.
    if claimed_strength != STRENGTH_STRONG:
        result.verdict = VERDICT_NOT_REQUIRED
        result.effective_strength = claimed_strength
        result.reasons.append("non_strong_claim_requires_no_receipt")
        return result

    registry_data = registry if registry is not None else load_binding_registry(project_root)
    if registry_data.get("error"):
        result.reasons.append(f"registry_unusable:{registry_data['error']}")
        return result

    binding = registry_data["bindings"].get(claim_kind)
    if binding is None:
        result.reasons.append("claim_kind_not_registered")
        return result
    result.validator = binding["validator"]

    validator_path = project_root / binding["validator"]
    if not validator_path.is_file():
        result.reasons.append(f"registered_validator_missing:{binding['validator']}")
        return result

    if not receipt_path:
        result.reasons.append("no_receipt_cited")
        return result

    # The receipt must live where this repo declared evidence lives. That reuses
    # the same path hardening as provenance checks, so a receipt cannot be
    # smuggled in from outside the repo.
    policy = load_evidence_root_policy(project_root)
    verdict = classify_evidence_path(project_root, receipt_path, policy)
    if not verdict.ok:
        result.reasons.append(f"receipt_path_rejected:{verdict.status}")
        return result

    try:
        payload = json.loads(verdict.resolved_path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.reasons.append(f"receipt_unreadable:{exc}")
        return result

    shape_errors = validate_receipt_shape(payload)
    if shape_errors:
        result.reasons.extend(shape_errors)
        return result

    if payload["claim_kind"].strip() != claim_kind:
        result.reasons.append("receipt_claim_kind_mismatch")
        return result

    if payload["validator"].strip() != binding["validator"]:
        # A receipt from an unregistered producer proves nothing about
        # authority, however well-formed it is.
        result.reasons.append("receipt_validator_not_registered_for_claim_kind")
        return result

    if payload["verdict"].strip().lower() != "pass":
        result.reasons.append(f"receipt_verdict_is_{payload['verdict'].strip().lower()}")
        return result

    if _EXIT_CODE_ONLY.match(payload["verdict_basis"].strip()):
        # This is the pnputil rule, stated domain-agnostically: a tool exiting 0
        # is not a semantic judgement about what it did.
        result.reasons.append("verdict_basis_is_exit_code_only")
        return result

    if session_id and payload["session_id"].strip() != session_id.strip():
        result.reasons.append("receipt_session_mismatch")
        return result

    receipt_commit = payload["linked_commit"].strip()
    if commit:
        if receipt_commit == "no_git_worktree":
            result.reasons.append("receipt_not_commit_anchored")
            return result
        if not _commits_consistent(receipt_commit, commit):
            result.reasons.append("receipt_commit_mismatch")
            return result

    for cited in payload["evidence_paths"]:
        cited_verdict = classify_evidence_path(project_root, cited, policy)
        if not cited_verdict.ok:
            result.reasons.append(
                f"receipt_evidence_path_rejected:{cited}:{cited_verdict.status}"
            )
            return result

    result.verdict = VERDICT_BOUND
    result.effective_strength = STRENGTH_STRONG
    result.reasons.append("receipt_declares_registered_producer_and_is_anchored")
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that a strong claim is backed by a registered validator receipt."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--claim-kind", required=True)
    parser.add_argument("--receipt")
    parser.add_argument("--session-id")
    parser.add_argument("--commit")
    parser.add_argument(
        "--strength", choices=[STRENGTH_STRONG, STRENGTH_OBSERVED], default=STRENGTH_STRONG
    )
    parser.add_argument("--registry")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument(
        "--fail-on-unbound",
        action="store_true",
        help="Exit non-zero when the claim is unbound. Off by default: report first.",
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    registry = (
        load_binding_registry(project_root, Path(args.registry).resolve())
        if args.registry
        else None
    )
    result = check_claim_binding(
        project_root,
        claim_kind=args.claim_kind,
        receipt_path=args.receipt,
        session_id=args.session_id,
        commit=args.commit,
        claimed_strength=args.strength,
        registry=registry,
    )

    if args.format == "json":
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"[claim_validator_binding] {result.claim_kind}: {result.verdict}")
        print(f"  effective_strength: {result.effective_strength}")
        for reason in result.reasons:
            print(f"  - {reason}")

    return 1 if (args.fail_on_unbound and not result.satisfied) else 0


if __name__ == "__main__":
    raise SystemExit(main())
