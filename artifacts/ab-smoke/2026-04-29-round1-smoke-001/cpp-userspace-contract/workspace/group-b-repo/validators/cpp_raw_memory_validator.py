#!/usr/bin/env python3
"""
Advisory validator for CPP_RAW_MEMORY_ALLOC.

Detects raw `new` allocation patterns (e.g., `= new uint8_t[size]`) in C++
source files.  Raw `new` allocations require a matching `delete` / `delete[]`
on every exit path, including exceptions and early returns.  The preferred
pattern is RAII smart pointers (std::make_unique, std::make_shared).

Enforcement: advisory.  Promote to hard_stop after 20 evaluations with
FP-rate = 0.0.
"""

import re
from pathlib import Path

from governance_tools.validator_interface import DomainValidator, ValidatorResult

# Only check implementation files (not headers — raw new in a declaration is unusual).
_CPP_IMPL_EXTENSIONS = {".cpp", ".cxx", ".cc"}

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT  = re.compile(r"//.*$", re.MULTILINE)

# Matches: = new Type, return new Type, throw new Type
# This catches the common resource-leak patterns.
_RAW_NEW = re.compile(r"(?:=|\breturn\b)\s*new\s+[\w:]+")


def _strip_comments(source: str) -> str:
    clean = _BLOCK_COMMENT.sub("", source)
    clean = _LINE_COMMENT.sub("", clean)
    return clean


def _is_cpp_impl_file(file_path: str) -> bool:
    return Path(file_path.replace("\\", "/")).suffix.lower() in _CPP_IMPL_EXTENSIONS


class CppRawMemoryValidator(DomainValidator):
    """
    CPP_RAW_MEMORY_ALLOC — advisory.

    Payload keys consumed:
      - file_path   (str): path of the file being reviewed
      - source_code (str): full source text
    """

    @property
    def rule_ids(self) -> list[str]:
        return ["CPP_RAW_MEMORY_ALLOC"]

    def validate(self, payload: dict) -> ValidatorResult:
        file_path: str = payload.get("file_path", "")
        source_code: str = payload.get("source_code", "")

        if not _is_cpp_impl_file(file_path):
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"File '{file_path}' is not a C++ implementation file — skip.",
                metadata={"mode": "advisory", "is_cpp_impl": False},
            )

        clean = _strip_comments(source_code)
        hits = _RAW_NEW.findall(clean)

        if not hits:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"No raw `new` allocations in '{file_path}'.",
                metadata={"mode": "advisory", "is_cpp_impl": True},
            )

        return ValidatorResult(
            ok=False,
            rule_ids=self.rule_ids,
            violations=[
                f"CPP_RAW_MEMORY_ALLOC: '{file_path}' contains {len(hits)} raw `new` "
                f"allocation(s).  Replace with std::make_unique<T>() or "
                f"std::make_shared<T>() to ensure automatic memory management."
            ],
            evidence_summary=(
                f"Raw `new` found in '{file_path}': {len(hits)} occurrence(s)."
            ),
            metadata={"mode": "advisory", "is_cpp_impl": True, "raw_new_count": len(hits)},
        )
