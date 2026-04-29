#!/usr/bin/env python3
"""
Advisory validator for ROUTE_RATE_LIMIT_COVERAGE.

Detects API route files that export mutation handlers (POST / PUT / DELETE /
PATCH) without any rate-limiting pattern.  Mutation routes without rate
limits are vulnerable to unbounded cost amplification and abuse.

Enforcement: advisory.
"""

import re
from governance_tools.validator_interface import DomainValidator, ValidatorResult

# Rate-limiting library and pattern indicators
_RATE_LIMIT_PATTERNS = [
    re.compile(r"\bRatelimit\b"),
    re.compile(r"\brateLimit\b"),
    re.compile(r"\brateLimiter\b"),
    re.compile(r"\bwithRateLimit\b"),
    re.compile(r"\blimiter\.limit\b"),
    re.compile(r"\blimiter\.check\b"),
    re.compile(r"status[:\s]+429"),           # explicit 429 response
    re.compile(r"Too Many Requests"),
]

# Next.js App Router export syntax (named handlers)
_NAMED_HANDLER = re.compile(
    r"\bexport\s+(?:async\s+)?function\s+(?P<method>POST|PUT|DELETE|PATCH)\b"
    r"|\bexport\s+const\s+(?P<cmethod>POST|PUT|DELETE|PATCH)\s*="
)
# Next.js Pages Router: default export handler
_DEFAULT_HANDLER = re.compile(
    r"\bexport\s+default\s+(?:async\s+)?function\s+handler\b"
)

_LINE_COMMENT = re.compile(r"^\s*//")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(source: str) -> str:
    clean = _BLOCK_COMMENT.sub("", source)
    return "\n".join(
        line for line in clean.splitlines()
        if not _LINE_COMMENT.match(line)
    )


class RouteRateLimitValidator(DomainValidator):
    """
    ROUTE_RATE_LIMIT_COVERAGE — advisory.

    Payload keys consumed:
      - file_path       (str)  : path of the file being reviewed
      - source_code     (str)  : full source text
      - api_route_roots (list) : path prefixes for API route files
    """

    _DEFAULT_API_ROOTS = ["src/app/api/", "pages/api/", "app/api/"]

    @property
    def rule_ids(self) -> list[str]:
        return ["ROUTE_RATE_LIMIT_COVERAGE"]

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

        clean = _strip_comments(source_code)

        has_mutation = bool(
            _NAMED_HANDLER.search(clean) or _DEFAULT_HANDLER.search(clean)
        )
        if not has_mutation:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=(
                    f"No mutation handler (POST/PUT/DELETE/PATCH) in '{file_path}' — skip."
                ),
                metadata={"mode": "advisory", "in_api": True, "has_mutation": False},
            )

        has_rate_limit = any(p.search(clean) for p in _RATE_LIMIT_PATTERNS)

        if has_rate_limit:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"Rate limiting present in '{file_path}'.",
                metadata={"mode": "advisory", "in_api": True, "has_mutation": True},
            )

        return ValidatorResult(
            ok=False,
            rule_ids=self.rule_ids,
            violations=[
                f"ROUTE_RATE_LIMIT_COVERAGE: '{file_path}' exports a mutation handler "
                f"without rate limiting — vulnerable to cost amplification and abuse."
            ],
            evidence_summary=(
                f"Mutation handler without rate limit in '{file_path}'."
            ),
            metadata={"mode": "advisory", "in_api": True, "has_mutation": True},
        )
