#!/usr/bin/env python3
"""
Advisory validator for BYOK_INGEST_KEY_PROPAGATION.

Detects ingest API routes that call generateEmbedding() without referencing
a user-provided API key.  When this pattern is absent, all embedding costs
are charged to the application owner's key — BYOK is silently broken.

Enforcement: advisory.  Promote to hard_stop after 20 evaluations with
FP-rate = 0.0.
"""

import re
from governance_tools.validator_interface import DomainValidator, ValidatorResult

# Embedding call that MUST be accompanied by a user key reference
_EMBEDDING_CALL = re.compile(r"generateEmbedding\s*\(")

# Patterns that confirm a user-provided key is in scope.
# Must be specific enough to distinguish an API-key reference from a plain
# auth guard (e.g. `if (!session?.user)` is NOT a key reference).
_USER_KEY_PATTERNS = [
    re.compile(r"\buserKey\b"),
    re.compile(r"\buser(?:\?\.|\.)openaiKey\b"),
    re.compile(r"\buser(?:\?\.|\.)apiKey\b"),
    re.compile(r"\bsession(?:\?\.|\.)user(?:\?\.|\.)(?:openai|api)Key\b"),
    re.compile(r"apiKey\s*:\s*\w"),          # { apiKey: someVar }
    re.compile(r"\bopenaiApiKey\b"),
]

# Used to identify ingest-specific routes
_INGEST_PATH = re.compile(r"ingest", re.IGNORECASE)

_LINE_COMMENT = re.compile(r"^\s*//")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(source: str) -> str:
    clean = _BLOCK_COMMENT.sub("", source)
    return "\n".join(
        line for line in clean.splitlines()
        if not _LINE_COMMENT.match(line)
    )


class ByokKeyPropagationValidator(DomainValidator):
    """
    BYOK_INGEST_KEY_PROPAGATION — advisory.

    Payload keys consumed:
      - file_path       (str)  : path of the file being reviewed
      - source_code     (str)  : full source text
      - api_route_roots (list) : path prefixes for API route files
                                 (default: src/app/api/, pages/api/, app/api/)
    """

    _DEFAULT_API_ROOTS = ["src/app/api/", "pages/api/", "app/api/"]

    @property
    def rule_ids(self) -> list[str]:
        return ["BYOK_INGEST_KEY_PROPAGATION"]

    def validate(self, payload: dict) -> ValidatorResult:
        file_path: str = payload.get("file_path", "")
        source_code: str = payload.get("source_code", "")
        api_roots: list[str] = payload.get("api_route_roots", self._DEFAULT_API_ROOTS)

        normalised = file_path.replace("\\", "/")

        in_api = any(normalised.startswith(root) for root in api_roots)
        if not in_api:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"File '{file_path}' is outside api_route_roots — skip.",
                metadata={"mode": "advisory", "in_api": False},
            )

        if not _INGEST_PATH.search(normalised):
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"File '{file_path}' is not an ingest route — skip.",
                metadata={"mode": "advisory", "in_api": True, "is_ingest": False},
            )

        clean = _strip_comments(source_code)

        if not _EMBEDDING_CALL.search(clean):
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"No generateEmbedding() call in '{file_path}'.",
                metadata={"mode": "advisory", "in_api": True, "is_ingest": True},
            )

        has_user_key = any(p.search(clean) for p in _USER_KEY_PATTERNS)

        if has_user_key:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=(
                    f"generateEmbedding() references user key in '{file_path}'."
                ),
                metadata={"mode": "advisory", "in_api": True, "is_ingest": True},
            )

        return ValidatorResult(
            ok=False,
            rule_ids=self.rule_ids,
            violations=[
                f"BYOK_INGEST_KEY_PROPAGATION: generateEmbedding() in '{file_path}' "
                f"does not reference a user API key — embedding costs are charged "
                f"to the application owner, not the end user."
            ],
            evidence_summary=(
                f"generateEmbedding() without user key in ingest route '{file_path}'."
            ),
            metadata={"mode": "advisory", "in_api": True, "is_ingest": True},
        )
