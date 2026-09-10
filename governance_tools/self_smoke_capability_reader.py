"""Recognize the A4-3L flat manifest subset; this is not a YAML parser.

The entire document must conform before its capability is returned. Metadata
supports numeric/dotted versions, or matching quotes around numeric versions
and dates. No escaping, nesting, inline comments, or implicit recovery exists.
This module only reads target bytes; it grants no installation authority.
"""

from pathlib import Path
import re
from typing import Literal


Capability = Literal["required", "not_applicable", "UNKNOWN"]
_KEY = "default_self_smoke_contract_dependency"
_ENTRY = re.compile(r"([a-z][a-z0-9]*(?:_[a-z0-9]+)+): +([^ ].*?) *")
_METADATA = re.compile(r'''(?:[0-9]+(?:\.[0-9]+)*|"[0-9]+(?:[.-][0-9]+)*"|'[0-9]+(?:[.-][0-9]+)*')''')


def interpret_self_smoke_capability(data: bytes) -> Capability:
    """Return a capability only for a completely recognized UTF-8 document."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "UNKNOWN"
    # Normalize only CRLF. Do not use splitlines/strip, which hide unsupported
    # separators, tabs, bare CR, indentation, and Unicode whitespace.
    text = text.replace("\r\n", "\n")
    if any(
        (ord(c) < 32 and c != "\n")
        or 127 <= ord(c) <= 159
        or c in "\ufeff\ufffe\uffff\u2028\u2029"
        for c in text
    ):
        return "UNKNOWN"
    seen: set[str] = set()
    capability: Capability = "UNKNOWN"
    for line in text.split("\n"):
        if not line.strip(" ") or line.startswith("#"):
            continue
        entry = _ENTRY.fullmatch(line)
        if entry is None:
            return "UNKNOWN"
        key, value = entry.groups()
        if key in seen:
            return "UNKNOWN"
        seen.add(key)
        if key == _KEY:
            if value not in {"required", "not_applicable"}:
                return "UNKNOWN"
            capability = value
        elif _METADATA.fullmatch(value) is None:
            return "UNKNOWN"
    return capability


def read_self_smoke_capability(framework_root: Path) -> Capability:
    """Read the target worktree/plain-directory manifest, without Git or YAML."""
    try:
        data = (framework_root / ".governance/version_manifest.yaml").read_bytes()
    except OSError:
        return "UNKNOWN"
    return interpret_self_smoke_capability(data)
