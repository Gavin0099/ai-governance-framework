#!/usr/bin/env python3
"""Contract-driven evidence roots for test_evidence provenance checks.

Why this module exists
----------------------
Provenance checks used to hardcode ``artifacts/`` as the only place evidence
could live. Any consumer repo that stores receipts elsewhere produced a
``test_evidence_success_claim_without_artifact`` finding for every entry —
indistinguishable from a repo that genuinely cited no evidence at all. That
made the finding stream unusable for triage: you could not tell "lying about a
PASS" from "stores receipts in a different directory".

Claim ceiling
-------------
A verdict of ``ok`` means: the cited token is a repo-relative path, it does not
escape the project root, it sits under a declared evidence root, and a regular
file exists there. It does NOT mean the file is a valid receipt, that the
recorded command ran, or that the claimed result is true. Receipt shape is
``memory_authority_guard._validate_evidence_receipt``; claim-to-validator
binding is ``governance_tools.claim_validator_binding``.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

if __package__ in (None, ""):  # pragma: no cover - direct-script fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.contract_resolver import resolve_contract
from governance_tools.domain_contract_loader import _parse_contract_yaml

# Roots the framework itself writes to (runtime closeouts, verdicts, receipts).
# A consumer contract can ADD roots but can never remove these: dropping them
# would make the framework stop recognising its own runtime artifacts, which is
# a real failure mode, not a hypothetical one.
FRAMEWORK_OWNED_ROOTS: tuple[str, ...] = ("artifacts",)
# Retained name for callers that only want the baseline set.
DEFAULT_EVIDENCE_ROOTS: tuple[str, ...] = FRAMEWORK_OWNED_ROOTS
CONTRACT_KEY = "evidence_roots"
SUFFIX_CONTRACT_KEY = "evidence_file_suffixes"

SOURCE_CONTRACT = "contract"
SOURCE_DEFAULT = "framework_default"
# An explicitly empty declaration is not the same as no declaration; it is
# almost always a mistake and must be visible rather than look like a default.
SOURCE_DECLARED_EMPTY = "contract_declared_empty"

# Verdict statuses. Each is a distinct triage bucket; callers must not collapse
# them back into a single "no artifact" code.
OK = "ok"
UNSAFE_ABSOLUTE = "path_unsafe_absolute"
UNSAFE_TRAVERSAL = "path_unsafe_parent_traversal"
UNSAFE_ESCAPES_ROOT = "path_unsafe_escapes_project_root"
OUTSIDE_ROOTS = "outside_declared_roots"
NOT_FOUND = "not_found"
NOT_A_FILE = "not_a_file"

UNSAFE_STATUSES = frozenset({UNSAFE_ABSOLUTE, UNSAFE_TRAVERSAL, UNSAFE_ESCAPES_ROOT})


@dataclass(frozen=True)
class EvidenceRootPolicy:
    """Which repo-relative directories may hold evidence, and where that came from.

    ``roots`` is always ``FRAMEWORK_OWNED_ROOTS`` plus whatever the consumer
    declared. Consumer declarations are additive by design — see
    FRAMEWORK_OWNED_ROOTS.
    """

    roots: tuple[str, ...]
    source: str
    contract_path: str | None = None
    warnings: tuple[str, ...] = ()
    consumer_roots: tuple[str, ...] = ()
    suffixes: frozenset[str] = field(default_factory=lambda: DEFAULT_EVIDENCE_SUFFIXES)

    @property
    def is_framework_default(self) -> bool:
        return self.source == SOURCE_DEFAULT

    @property
    def framework_roots(self) -> tuple[str, ...]:
        return FRAMEWORK_OWNED_ROOTS

    def as_dict(self) -> dict:
        return {
            "roots": list(self.roots),
            "framework_owned_roots": list(FRAMEWORK_OWNED_ROOTS),
            "consumer_roots": list(self.consumer_roots),
            "source": self.source,
            "contract_path": self.contract_path,
            "warnings": list(self.warnings),
            "evidence_file_suffixes": sorted(self.suffixes),
        }


@dataclass(frozen=True)
class EvidencePathVerdict:
    """Result of checking one cited evidence token against a policy."""

    token: str
    status: str
    relative_path: str | None = None
    resolved_path: Path | None = None
    matched_root: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == OK

    @property
    def is_unsafe(self) -> bool:
        return self.status in UNSAFE_STATUSES

    def as_dict(self) -> dict:
        return {
            "token": self.token,
            "status": self.status,
            "relative_path": self.relative_path,
            "matched_root": self.matched_root,
        }


# ── root normalization ────────────────────────────────────────────────────────

def normalize_root(value: str) -> str | None:
    """Return a canonical repo-relative root, or None when it is not usable.

    Rejects absolute paths, drive-qualified paths, and any parent traversal.
    A root that fails here is dropped with a warning rather than silently
    widening the accepted surface.
    """
    text = (value or "").strip().strip("\"'").replace("\\", "/").strip()
    if not text:
        return None
    # Absoluteness must be decided before any stripping: "/etc" would otherwise
    # normalize to the innocent-looking relative root "etc".
    if text.startswith("/") or text.startswith("~") or ":" in text:
        return None
    while text.startswith("./"):
        text = text[2:]
    text = text.strip("/")
    if not text:
        return None
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return None
    return "/".join(parts)


def _normalize_roots(values: Iterable[str]) -> tuple[tuple[str, ...], list[str]]:
    roots: list[str] = []
    warnings: list[str] = []
    for value in values:
        normalized = normalize_root(str(value))
        if normalized is None:
            warnings.append(f"evidence_root_rejected:{str(value).strip()!r}")
            continue
        if normalized not in roots:
            roots.append(normalized)
    return tuple(roots), warnings


def _normalize_suffixes(
    values: Sequence[str] | None,
) -> tuple[frozenset[str], list[str]]:
    """Consumer-declared evidence extensions extend the framework set.

    Domain evidence formats the framework has never heard of (.etl, .evtx,
    .cat) are exactly why this is declarable rather than a fixed constant.
    """
    if not values:
        return DEFAULT_EVIDENCE_SUFFIXES, []
    extra: set[str] = set()
    warnings: list[str] = []
    for value in values:
        text = str(value).strip().strip("\"'").lower()
        if not text:
            continue
        if not text.startswith("."):
            text = f".{text}"
        if "/" in text or "\\" in text or len(text) < 2:
            warnings.append(f"evidence_file_suffix_rejected:{value!r}")
            continue
        extra.add(text)
    if not extra:
        return DEFAULT_EVIDENCE_SUFFIXES, warnings
    return frozenset(DEFAULT_EVIDENCE_SUFFIXES | extra), warnings


# ── policy loading ────────────────────────────────────────────────────────────

def _merge_roots(consumer_roots: Sequence[str]) -> tuple[str, ...]:
    merged = list(FRAMEWORK_OWNED_ROOTS)
    for root in consumer_roots:
        if root not in merged:
            merged.append(root)
    return tuple(merged)


def policy_from_values(
    values: Sequence[str] | None,
    *,
    contract_path: str | None = None,
    declared: bool | None = None,
    suffixes: Sequence[str] | None = None,
) -> EvidenceRootPolicy:
    """Build a policy from raw declared values.

    ``declared`` distinguishes "the key was absent" from "the key was present
    but empty". The second is a misconfiguration and gets its own visible
    source value instead of quietly resembling the first.
    """
    resolved_suffixes, suffix_warnings = _normalize_suffixes(suffixes)
    was_declared = declared if declared is not None else bool(values)

    if not values:
        source = SOURCE_DECLARED_EMPTY if was_declared else SOURCE_DEFAULT
        warnings = list(suffix_warnings)
        if was_declared:
            warnings.append(
                "evidence_roots_declared_but_empty_using_framework_owned_roots_only"
            )
        return EvidenceRootPolicy(
            roots=FRAMEWORK_OWNED_ROOTS,
            source=source,
            contract_path=contract_path,
            warnings=tuple(warnings),
            suffixes=resolved_suffixes,
        )

    consumer_roots, warnings = _normalize_roots(values)
    warnings.extend(suffix_warnings)
    if not consumer_roots:
        warnings.append(
            "evidence_roots_declared_but_all_invalid_using_framework_owned_roots_only"
        )
        return EvidenceRootPolicy(
            roots=FRAMEWORK_OWNED_ROOTS,
            source=SOURCE_DECLARED_EMPTY,
            contract_path=contract_path,
            warnings=tuple(warnings),
            suffixes=resolved_suffixes,
        )
    return EvidenceRootPolicy(
        roots=_merge_roots(consumer_roots),
        source=SOURCE_CONTRACT,
        contract_path=contract_path,
        warnings=tuple(warnings),
        consumer_roots=consumer_roots,
        suffixes=resolved_suffixes,
    )


def load_evidence_root_policy(
    project_root: Path | str | None,
    *,
    contract_path: Path | str | None = None,
) -> EvidenceRootPolicy:
    """Resolve the evidence-root policy for a repo.

    Never raises: an unreadable or malformed contract degrades to the framework
    default with a warning, because a broken contract must not silently disable
    the provenance check.
    """
    if project_root is None:
        return EvidenceRootPolicy(roots=DEFAULT_EVIDENCE_ROOTS, source=SOURCE_DEFAULT)

    root = Path(project_root)
    resolution = resolve_contract(contract_path, project_root=root)
    if resolution.path is None:
        warnings = tuple(resolution.warnings)
        if resolution.error:
            warnings = warnings + (resolution.error,)
        return EvidenceRootPolicy(
            roots=DEFAULT_EVIDENCE_ROOTS,
            source=SOURCE_DEFAULT,
            warnings=warnings,
        )

    # Contract discovery walks upward, so a repo nested under another repo can
    # be handed its parent's contract. Evidence roots are repo-relative, so a
    # contract from outside this project root cannot describe it — fall back to
    # the default rather than accept roots that resolve somewhere else.
    try:
        resolution.path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return EvidenceRootPolicy(
            roots=DEFAULT_EVIDENCE_ROOTS,
            source=SOURCE_DEFAULT,
            warnings=(
                "contract_outside_project_root_ignored: "
                f"{resolution.path}",
            ),
        )

    try:
        data = _parse_contract_yaml(resolution.path.read_text(encoding="utf-8"))
    except Exception as exc:
        return EvidenceRootPolicy(
            roots=DEFAULT_EVIDENCE_ROOTS,
            source=SOURCE_DEFAULT,
            contract_path=str(resolution.path),
            warnings=(f"contract_unreadable_using_framework_default: {exc}",),
        )

    declared = data.get(CONTRACT_KEY)
    key_present = CONTRACT_KEY in data
    if declared is None:
        values: list[str] = []
    elif isinstance(declared, list):
        values = [str(item) for item in declared]
    else:
        values = [str(declared)]

    raw_suffixes = data.get(SUFFIX_CONTRACT_KEY)
    if raw_suffixes is None:
        suffix_values: list[str] = []
    elif isinstance(raw_suffixes, list):
        suffix_values = [str(item) for item in raw_suffixes]
    else:
        suffix_values = [str(raw_suffixes)]

    policy = policy_from_values(
        values,
        contract_path=str(resolution.path),
        declared=key_present,
        suffixes=suffix_values,
    )
    if resolution.warnings:
        policy = EvidenceRootPolicy(
            roots=policy.roots,
            source=policy.source,
            contract_path=policy.contract_path,
            warnings=policy.warnings + tuple(resolution.warnings),
            consumer_roots=policy.consumer_roots,
            suffixes=policy.suffixes,
        )
    return policy


# ── token matching ────────────────────────────────────────────────────────────

@lru_cache(maxsize=32)
def _pattern_for_roots(roots: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = []
    for root in roots:
        # Accept either separator at every boundary so Windows-style citations
        # in prose still match the posix-declared root.
        segments = [re.escape(segment) for segment in root.split("/")]
        alternatives.append(r"[\\/]".join(segments))
    joined = "|".join(alternatives)
    return re.compile(
        rf"(?P<path>(?:\.?[\\/])?(?:{joined})[\\/][^\s,;]+)",
        re.IGNORECASE,
    )


def evidence_path_pattern(policy: EvidenceRootPolicy) -> re.Pattern[str]:
    """Regex that finds citations of declared evidence roots in free prose."""
    return _pattern_for_roots(policy.roots)


# A quoted span is treated as one token so evidence directories containing
# spaces (common on Windows) are not truncated at the first space.
_QUOTED_SPAN = re.compile(r"""["'`]([^"'`\n]+)["'`]""")


def _quoted_candidates(text: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in _QUOTED_SPAN.finditer(text or "")
        if "/" in match.group(1) or "\\" in match.group(1)
    ]


def find_evidence_tokens(text: str, policy: EvidenceRootPolicy) -> list[str]:
    pattern = evidence_path_pattern(policy)
    tokens = [match.group("path") for match in pattern.finditer(text or "")]
    for candidate in _quoted_candidates(text):
        # Quoted spans may contain spaces, which the unquoted pattern stops at,
        # so root membership is checked directly rather than by re-matching.
        normalized = normalize_token(candidate).replace("\\", "/").lstrip("./")
        if (
            _matching_root(normalized, policy.roots) is not None
            and candidate not in tokens
        ):
            tokens.append(candidate)
    return tokens


# Any path-shaped token, regardless of declared roots. Used to tell "cited a
# path we do not accept" apart from "cited no path at all" — the distinction
# the old single-code behaviour destroyed.
_ANY_PATH_TOKEN = re.compile(r"(?P<path>(?:[A-Za-z]:)?(?:\.{0,2}[\\/])?[\w.\-]+(?:[\\/][^\s,;]+)+)")

# A `test_evidence` line names both evidence and the thing that was run:
# "PASS: pytest tests/test_foo.py" cites a test target, not a receipt. Treating
# that as misplaced evidence would relabel unsupported claims as mere contract
# gaps — the opposite of the mistake this module fixes, and just as misleading.
# So a candidate for "evidence in an undeclared location" must look like output
# rather than source. Extensions, not naming conventions: a .py file is not a
# receipt regardless of what it is called.
# Framework-known output formats. Deliberately includes Windows domain evidence
# (.etl, .evtx, .cat, .inf, .dmp) because driver work is a first-class consumer
# case; anything else a domain produces is added via `evidence_file_suffixes:`.
DEFAULT_EVIDENCE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".json", ".ndjson", ".jsonl", ".txt", ".log", ".xml", ".csv", ".tap",
        ".html", ".etl", ".evtx", ".cat", ".inf", ".dmp", ".wer", ".trace",
        ".out", ".err", ".diff", ".patch", ".sarif", ".junit",
    }
)


def find_pathlike_tokens(text: str) -> list[str]:
    tokens = [match.group("path") for match in _ANY_PATH_TOKEN.finditer(text or "")]
    for candidate in _quoted_candidates(text):
        if candidate not in tokens:
            tokens.append(candidate)
    return tokens


def looks_like_evidence_file(
    relative_path: str,
    suffixes: frozenset[str] = DEFAULT_EVIDENCE_SUFFIXES,
    *,
    exists: bool | None = None,
) -> bool:
    """Is this cited path plausibly an artifact rather than a test target?

    An extension-less file that actually exists counts: plenty of real evidence
    is a bare `stdout` or `dump` file, and requiring an extension would push
    those into the "claimed success with no evidence" bucket, which is exactly
    the over-claim this predicate exists to avoid. Source files never count,
    because naming what you ran is not producing evidence of the result.
    """
    suffix = PurePosixPath(relative_path).suffix.lower()
    if suffix in suffixes:
        return True
    if suffix in _SOURCE_SUFFIXES:
        return False
    if not suffix and exists:
        return True
    return False


# Source and build inputs: citing these describes the run, not its outcome.
_SOURCE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".c", ".h", ".cpp", ".hpp",
        ".cs", ".java", ".go", ".rs", ".rb", ".sh", ".ps1", ".bat", ".cmd",
        ".yaml", ".yml", ".toml", ".ini", ".cfg", ".md", ".rst",
    }
)


def normalize_token(token: str) -> str:
    return token.strip().strip('`"\'()[]{}<>').rstrip(".:")


# ── classification ────────────────────────────────────────────────────────────

def classify_evidence_path(
    project_root: Path | str | None,
    token: str,
    policy: EvidenceRootPolicy,
) -> EvidencePathVerdict:
    """Check one cited token: safe, inside a declared root, and present on disk.

    Order matters. Safety is decided before existence so a traversal attempt
    that happens to point at a real file is still rejected, and before root
    membership so an escape is never reported as a mere misplacement.
    """
    normalized = normalize_token(token)
    if not normalized:
        return EvidencePathVerdict(token=token, status=NOT_FOUND)

    text = normalized.replace("\\", "/")
    if text.startswith("~") or re.match(r"^[A-Za-z]:", text) or text.startswith("/"):
        return EvidencePathVerdict(token=token, status=UNSAFE_ABSOLUTE)

    parts = [part for part in text.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return EvidencePathVerdict(token=token, status=UNSAFE_TRAVERSAL)
    relative = "/".join(parts)
    if not relative:
        return EvidencePathVerdict(token=token, status=NOT_FOUND)

    if project_root is None:
        return EvidencePathVerdict(token=token, status=NOT_FOUND, relative_path=relative)

    root = Path(project_root)
    try:
        resolved_root = root.resolve()
        resolved = (root / relative).resolve()
    except OSError:
        return EvidencePathVerdict(
            token=token, status=UNSAFE_ESCAPES_ROOT, relative_path=relative
        )

    try:
        # resolve() follows symlinks, so this also catches a symlinked evidence
        # directory that points outside the repository.
        actual_relative = resolved.relative_to(resolved_root).as_posix()
    except ValueError:
        return EvidencePathVerdict(
            token=token, status=UNSAFE_ESCAPES_ROOT, relative_path=relative
        )

    matched_root = _matching_root(actual_relative, policy.roots)
    if matched_root is None:
        return EvidencePathVerdict(
            token=token,
            status=OUTSIDE_ROOTS,
            relative_path=actual_relative,
            resolved_path=resolved,
        )

    if not resolved.exists():
        return EvidencePathVerdict(
            token=token,
            status=NOT_FOUND,
            relative_path=actual_relative,
            matched_root=matched_root,
        )
    if not resolved.is_file():
        return EvidencePathVerdict(
            token=token,
            status=NOT_A_FILE,
            relative_path=actual_relative,
            resolved_path=resolved,
            matched_root=matched_root,
        )

    return EvidencePathVerdict(
        token=token,
        status=OK,
        relative_path=actual_relative,
        resolved_path=resolved,
        matched_root=matched_root,
    )


def _fold_case(path_text: str) -> str:
    """Apply the filesystem's case rule without touching separators.

    `os.path.normcase` alone is not usable here: on Windows it also rewrites
    `/` to `\\`, which collapses a posix path into a single component and makes
    every root comparison fail.
    """
    return os.path.normcase(path_text).replace("\\", "/")


def _matching_root(relative_path: str, roots: Sequence[str]) -> str | None:
    """Match a path to a declared root, respecting the filesystem's case rules.

    `os.path.normcase` is identity on POSIX and lowercases on Windows, so
    `ARTIFACTS/x.json` resolves against a root declared as `artifacts` on a
    case-insensitive filesystem without loosening matching on a case-sensitive
    one.
    """
    candidate = PurePosixPath(_fold_case(relative_path))
    for root in roots:
        root_path = PurePosixPath(_fold_case(root))
        try:
            candidate.relative_to(root_path)
        except ValueError:
            continue
        if candidate != root_path:
            return root
    return None


def resolve_evidence_file(
    project_root: Path | str | None,
    token: str,
    policy: EvidenceRootPolicy,
) -> Path | None:
    """Back-compatible helper: resolved file path, or None when not acceptable."""
    verdict = classify_evidence_path(project_root, token, policy)
    return verdict.resolved_path if verdict.ok else None
