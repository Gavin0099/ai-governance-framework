#!/usr/bin/env python3
"""The tool-channel contract, in one place, loaded by both sides.

The previous design wrote the verb/argument contract twice -- once as regexes
inside the guard, once as a `case` statement inside the adapter -- so the two
could drift apart silently and a review flagged exactly that. Here the contract
is data: one JSON file that the guard (PreToolUse hook) and the adapter both
load. The adapter still owns *execution* (what argv actually runs in the
container); it no longer owns *admissibility*.

A policy file is strict by construction:

    {"policy_id": "...",
     "verbs": {"read": {"summary": "...",
                        "args": [{"name": "path",
                                  "pattern": "^...$",
                                  "forbid": ["\\\\.\\\\."],
                                  "max_len": 120}]}}}

Unknown keys, missing keys, bad regexes and non-anchored patterns all raise
PolicyError -- a policy that cannot be understood must not be used to admit
anything.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

VERB_RE = re.compile(r"^[a-z][a-z0-9_]{0,15}$")

_ARG_KEYS = {"name", "pattern", "forbid", "max_len"}
_VERB_KEYS = {"summary", "args"}
_TOP_KEYS = {"policy_id", "description", "verbs"}


class PolicyError(Exception):
    """The policy could not be loaded or is malformed. Always fatal."""


@dataclass(frozen=True)
class ArgSpec:
    name: str
    pattern: "re.Pattern[str]"
    forbid: tuple["re.Pattern[str]", ...]
    max_len: int


@dataclass(frozen=True)
class Policy:
    policy_id: str
    path: str
    sha256: str
    verbs: dict[str, tuple[ArgSpec, ...]]

    def check(self, verb: str, args: list[str]) -> tuple[bool, str]:
        """Return (ok, reason). Pure -- no side effects, so it is testable."""
        if verb not in self.verbs:
            allowed = ", ".join(sorted(self.verbs))
            return False, f"verb {verb!r} is not in the allowlist ({allowed})"
        specs = self.verbs[verb]
        if len(args) != len(specs):
            want = len(specs)
            return False, f"verb {verb!r} takes exactly {want} argument(s), got {len(args)}"
        for spec, value in zip(specs, args):
            if len(value) > spec.max_len:
                return False, f"argument {spec.name!r} exceeds max_len {spec.max_len}"
            if not spec.pattern.match(value):
                return False, f"argument {spec.name!r} failed the allowlist pattern"
            for bad in spec.forbid:
                if bad.search(value):
                    return False, f"argument {spec.name!r} matched a forbidden pattern"
        return True, "sanctioned adapter call"


def _compile(pattern: str, where: str) -> "re.Pattern[str]":
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise PolicyError(f"{where}: bad regex {pattern!r}: {exc}") from exc


def load_policy(path: str) -> Policy:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise PolicyError(f"cannot read policy {path!r}: {exc}") from exc

    sha = hashlib.sha256(raw).hexdigest()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise PolicyError(f"policy {path!r} is not valid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise PolicyError("policy must be a JSON object")
    if extra := set(doc) - _TOP_KEYS:
        raise PolicyError(f"unknown top-level keys: {sorted(extra)}")
    policy_id = doc.get("policy_id")
    if not isinstance(policy_id, str) or not policy_id:
        raise PolicyError("policy_id is required")
    verbs_doc = doc.get("verbs")
    if not isinstance(verbs_doc, dict) or not verbs_doc:
        raise PolicyError("verbs must be a non-empty object")

    verbs: dict[str, tuple[ArgSpec, ...]] = {}
    for verb, spec in verbs_doc.items():
        if not VERB_RE.match(verb):
            raise PolicyError(f"verb {verb!r} is not a legal verb name")
        if not isinstance(spec, dict):
            raise PolicyError(f"verb {verb!r}: spec must be an object")
        if extra := set(spec) - _VERB_KEYS:
            raise PolicyError(f"verb {verb!r}: unknown keys {sorted(extra)}")
        args_doc = spec.get("args", [])
        if not isinstance(args_doc, list):
            raise PolicyError(f"verb {verb!r}: args must be a list")
        args: list[ArgSpec] = []
        for i, arg in enumerate(args_doc):
            where = f"verb {verb!r} arg {i}"
            if not isinstance(arg, dict):
                raise PolicyError(f"{where}: must be an object")
            if extra := set(arg) - _ARG_KEYS:
                raise PolicyError(f"{where}: unknown keys {sorted(extra)}")
            name = arg.get("name")
            pattern = arg.get("pattern")
            if not isinstance(name, str) or not name:
                raise PolicyError(f"{where}: name is required")
            if not isinstance(pattern, str) or not pattern:
                raise PolicyError(f"{where}: pattern is required")
            # An unanchored pattern would admit anything with a legal prefix.
            if not (pattern.startswith("^") and pattern.endswith("$")):
                raise PolicyError(f"{where}: pattern must be anchored with ^ and $")
            max_len = arg.get("max_len", 256)
            if not isinstance(max_len, int) or not 1 <= max_len <= 1_000_000:
                raise PolicyError(f"{where}: max_len must be an int in [1, 1000000]")
            forbid_doc = arg.get("forbid", [])
            if not isinstance(forbid_doc, list):
                raise PolicyError(f"{where}: forbid must be a list")
            forbid: list["re.Pattern[str]"] = []
            for j, f in enumerate(forbid_doc):
                if not isinstance(f, str):
                    raise PolicyError(f"{where}: forbid entries must be strings")
                forbid.append(_compile(f, f"{where} forbid[{j}]"))
            args.append(ArgSpec(name, _compile(pattern, where), tuple(forbid), max_len))
        verbs[verb] = tuple(args)

    return Policy(policy_id=policy_id, path=path, sha256=sha, verbs=verbs)
