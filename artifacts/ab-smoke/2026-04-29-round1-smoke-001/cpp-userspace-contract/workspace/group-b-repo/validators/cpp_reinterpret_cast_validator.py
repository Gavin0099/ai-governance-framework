#!/usr/bin/env python3
"""
Advisory validator for CPP_REINTERPRET_CAST_CALLBACK.

Detects `reinterpret_cast<>` in C++ implementation files.  This cast
bypasses the type system entirely.  At callback boundaries (WinAPI, COM,
function pointers) it is especially dangerous if the target type is not
validated before dereferencing.

Enforcement: advisory.  Promote to hard_stop after 20 evaluations with
FP-rate = 0.0.
"""

import re
from pathlib import Path

from governance_tools.validator_interface import DomainValidator, ValidatorResult

_CPP_IMPL_EXTENSIONS = {".cpp", ".cxx", ".cc"}

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT  = re.compile(r"//.*$", re.MULTILINE)

# reinterpret_cast<SomeType*>(expr)
_REINTERPRET_CAST = re.compile(r"\breinterpret_cast\s*<")


def _strip_comments(source: str) -> str:
    clean = _BLOCK_COMMENT.sub("", source)
    clean = _LINE_COMMENT.sub("", clean)
    return clean


def _is_cpp_impl_file(file_path: str) -> bool:
    return Path(file_path.replace("\\", "/")).suffix.lower() in _CPP_IMPL_EXTENSIONS


class CppReinterpretCastValidator(DomainValidator):
    """
    CPP_REINTERPRET_CAST_CALLBACK — advisory.

    Payload keys consumed:
      - file_path   (str): path of the file being reviewed
      - source_code (str): full source text
    """

    @property
    def rule_ids(self) -> list[str]:
        return ["CPP_REINTERPRET_CAST_CALLBACK"]

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
        hits = _REINTERPRET_CAST.findall(clean)

        if not hits:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary=f"No reinterpret_cast in '{file_path}'.",
                metadata={"mode": "advisory", "is_cpp_impl": True},
            )

        return ValidatorResult(
            ok=False,
            rule_ids=self.rule_ids,
            violations=[
                f"CPP_REINTERPRET_CAST_CALLBACK: '{file_path}' contains "
                f"{len(hits)} reinterpret_cast<> occurrence(s).  "
                f"At callback boundaries, validate the pointer (null-check, type tag) "
                f"before dereferencing.  Consider static_cast or a type-safe wrapper."
            ],
            evidence_summary=(
                f"reinterpret_cast<> found in '{file_path}': {len(hits)} occurrence(s)."
            ),
            metadata={"mode": "advisory", "is_cpp_impl": True, "cast_count": len(hits)},
        )
