#!/usr/bin/env python3
"""
Advisory validator for CPP_MUTEX_BARE_LOCK.

Detects explicit .lock() / .unlock() calls on mutex-like objects in C++
source files.  Bare locks are prone to missing unlock on exception or early
return paths.  The preferred pattern is RAII wrappers (std::scoped_lock,
std::lock_guard, std::unique_lock).

Enforcement: advisory.  Promote to hard_stop after 20 evaluations with
FP-rate = 0.0.
"""

import re
from pathlib import Path

from governance_tools.validator_interface import DomainValidator, ValidatorResult

_CPP_EXTENSIONS = {".cpp", ".cxx", ".cc", ".h", ".hpp"}

# Strip C-style block comments and // line comments before pattern matching.
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT  = re.compile(r"//.*$", re.MULTILINE)

# Bare .lock() / .unlock() as a statement expression.
# Matches: m_mutex.lock(); or this->cs.lock(); (any identifier chain ending in .lock()).
# Does NOT match constructor calls like lock_guard<mutex> g(m_mutex).
_BARE_LOCK   = re.compile(r"\.\s*lock\s*\(\s*\)\s*;")
_BARE_UNLOCK = re.compile(r"\.\s*unlock\s*\(\s*\)\s*;")


def _strip_comments(source: str) -> str:
    clean = _BLOCK_COMMENT.sub("", source)
    clean = _LINE_COMMENT.sub("", clean)
    return clean


def _is_cpp_file(file_path: str) -> bool:
    return Path(file_path.replace("\\", "/")).suffix.lower() in _CPP_EXTENSIONS


class CppMutexSafetyValidator(DomainValidator):
    """
    CPP_MUTEX_BARE_LOCK — advisory.

    Payload keys consumed:
      - file_path   (str): path of the file being reviewed
      - source_code (str): full source text
    """

    @property
    def rule_ids(self) -> list[str]:
        return ["CPP_MUTEX_BARE_LOCK"]

    def validate(self, payload: dict) -> ValidatorResult:
        file_path: str = payload.get("file_path", "")
        source_code: str = payload.get("source_code", "")

        if not _is_cpp_file(file_path):
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"File '{file_path}' is not a C++ source file — skip.",
                metadata={"mode": "advisory", "is_cpp": False},
            )

        clean = _strip_comments(source_code)

        lock_hits   = _BARE_LOCK.findall(clean)
        unlock_hits = _BARE_UNLOCK.findall(clean)

        if not lock_hits and not unlock_hits:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"No bare .lock()/.unlock() calls in '{file_path}'.",
                metadata={"mode": "advisory", "is_cpp": True},
            )

        violations = []
        if lock_hits:
            violations.append(
                f"CPP_MUTEX_BARE_LOCK: '{file_path}' calls .lock() directly "
                f"({len(lock_hits)} occurrence(s)).  Use std::scoped_lock or "
                f"std::lock_guard to ensure unlock on all code paths."
            )
        if unlock_hits:
            violations.append(
                f"CPP_MUTEX_BARE_LOCK: '{file_path}' calls .unlock() directly "
                f"({len(unlock_hits)} occurrence(s)).  RAII wrappers handle "
                f"unlock automatically — explicit .unlock() indicates a bare-lock pattern."
            )

        return ValidatorResult(
            ok=False,
            rule_ids=self.rule_ids,
            violations=violations,
            evidence_summary=(
                f"Bare mutex calls in '{file_path}': "
                f"{len(lock_hits)} .lock(), {len(unlock_hits)} .unlock()."
            ),
            metadata={"mode": "advisory", "is_cpp": True,
                      "lock_count": len(lock_hits), "unlock_count": len(unlock_hits)},
        )
