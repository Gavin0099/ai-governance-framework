#!/usr/bin/env python3
"""
Validate machine-readable [Governance Contract] blocks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.rule_pack_loader import available_rule_packs, parse_rule_list


VALID_LANG = {"C", "C++", "C#", "ObjC", "Swift", "JS", "Python", "Verilog", "SystemVerilog"}
VALID_LEVEL = {"L0", "L1", "L2"}
VALID_SCOPE = {"feature", "refactor", "bugfix", "I/O", "tooling", "review", "governance", "kernel-driver"}
VALID_PRESSURE_LEVELS = {"SAFE", "WARNING", "CRITICAL", "EMERGENCY"}
VALID_RISK_LEVELS = {"low", "medium", "high"}
VALID_OVERSIGHT_LEVELS = {"auto", "review-required", "human-approval"}
VALID_MEMORY_MODES = {"stateless", "candidate", "durable"}

# SYSTEM_PROMPT.md §2.8 is canonical and can_override:false: LOADED must name
# documents actually loaded, must include SYSTEM_PROMPT, and must NOT list
# HUMAN-OVERSIGHT.md unless a human explicitly provided it. Requiring
# HUMAN-OVERSIGHT here made the two rules impossible to satisfy together for an
# agent that was never handed it, so the requirement is dropped rather than
# weakening the authority boundary to match the tool.
REQUIRED_LOADED = {"SYSTEM_PROMPT"}

# Two contracts, two authorities. SYSTEM_PROMPT.md §2.8 defines the display
# fields a human sees at task start; governance/RUNTIME_CONTRACT.md defines the
# fields runtime_hooks/ gates on. They were one list for five months only because
# 8994a5e1 removed the runtime fields from the codex without migrating the tool.
DISPLAY_CONTRACT_FIELDS = [
    "LANG",
    "LEVEL",
    "SCOPE",
    "PLAN",
    "LOADED",
    "CONTEXT",
    "PRESSURE",
    "AGENT_ID",
    "SESSION",
]
RUNTIME_CONTRACT_FIELDS = [
    "RULES",
    "RISK",
    "OVERSIGHT",
    "MEMORY_MODE",
]
DISPLAY_FIELDS = DISPLAY_CONTRACT_FIELDS + RUNTIME_CONTRACT_FIELDS


@dataclass
class ValidationResult:
    compliant: bool
    contract_found: bool
    fields: dict
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def extract_contract_block(text: str) -> Optional[str]:
    code_match = re.search(r"```[^\n]*\n\[Governance Contract\]\n(.*?)```", text, re.DOTALL)
    if code_match:
        return code_match.group(0)

    plain_match = re.search(r"\[Governance Contract\]\n((?:[A-Z_]+\s*=\s*.*\n?)*)", text)
    if plain_match and plain_match.group(1).strip():
        return plain_match.group(0)
    return None


def parse_contract_fields(block: str) -> dict:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if "=" not in line or stripped.startswith("[") or stripped.startswith("`"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def _validate_choice(fields: dict, key: str, valid_values: set[str], errors: list[str]) -> None:
    value = fields.get(key, "").strip()
    if not value:
        errors.append(f"{key} field is required")
        return
    if value not in valid_values:
        errors.append(f"{key} invalid: '{value}'. Allowed: {sorted(valid_values)}")


PRESSURE_LINE_LIMIT = 200
# Two accepted shapes, per §2.8:
#   SAFE (45/200)
#   WARNING (87/200 lines; 9642 chars)
#
# The second exists because §7.4 escalates on lines *or* characters. An agent
# that reports WARNING at 87 lines is right only if the character count crossed
# 8000, and with the short form that reasoning is invisible. Rejecting the richer
# form punished the output that best evidenced its own level.
_PRESSURE_PATTERN = re.compile(
    r"^(?P<level>[A-Za-z]+)\s*\(\s*(?P<count>\d+)\s*/\s*(?P<limit>\d+)"
    r"(?:\s*lines\s*;\s*(?P<chars>\d+)\s*chars)?\s*\)$"
)


def _validate_pressure(fields: dict, errors: list[str]) -> None:
    """Require a real line count, not something shaped like one.

    §2.8 already says PRESSURE must carry a label and a line count, and that a
    malformed contract block is a governance failure. The previous check only
    read the label and downgraded a missing count to a warning, so an unfilled
    template (`SAFE (<line count>/200)`), a placeholder
    (`SAFE (pending exact line count/200)`), a non-number, a negative value and a
    wrong denominator all validated as compliant. A number that cannot be read
    is not evidence of memory pressure, and this field is one of the inputs a
    reviewer uses to judge whether cleanup was due.

    This enforces the existing rule; it does not change the thresholds in §7.4.
    """
    pressure = fields.get("PRESSURE", "").strip()
    if not pressure:
        errors.append("PRESSURE field is required")
        return

    match = _PRESSURE_PATTERN.match(pressure)
    if match is None:
        errors.append(
            f"PRESSURE invalid: '{pressure}'. Expected "
            f"<{'|'.join(sorted(VALID_PRESSURE_LEVELS))}> (<line count>/{PRESSURE_LINE_LIMIT}) "
            f"with an actual integer line count, e.g. 'SAFE (45/{PRESSURE_LINE_LIMIT})'"
        )
        return

    level_name = match.group("level")
    if level_name not in VALID_PRESSURE_LEVELS:
        errors.append(
            f"PRESSURE invalid: '{level_name}'. Allowed: {sorted(VALID_PRESSURE_LEVELS)}"
        )

    limit = int(match.group("limit"))
    if limit != PRESSURE_LINE_LIMIT:
        errors.append(
            f"PRESSURE denominator invalid: '{limit}'. Expected {PRESSURE_LINE_LIMIT}"
        )


def normalize_loaded_identifier(raw: str) -> str:
    """Reduce a LOADED entry to its canonical document identifier.

    SYSTEM_PROMPT.md §2.8: take the last path segment, treating `\\` as `/`, and
    allow `.md` alone to be omitted. Matching is case-sensitive.

    An agent that writes the full path it actually read carries more auditable
    information than a bare token, and used to fail this check for it — the rule
    named `SYSTEM_PROMPT` without saying whether that was a token or a path.
    Only `.md` is optional, and only the final segment is compared, so
    `SYSTEM_PROMPT.txt` and `MY_SYSTEM_PROMPT.md` remain different documents.
    """
    segment = raw.strip().replace("\\", "/").rsplit("/", 1)[-1]
    if segment.endswith(".md"):
        segment = segment[: -len(".md")]
    return segment


def parse_lang_list(raw: str) -> list[str]:
    """Split a LANG field into its declared languages, preserving order."""
    return [item.strip() for item in raw.split(",") if item.strip()]


def _validate_lang(fields: dict, errors: list[str]) -> None:
    """Validate LANG as a comma-separated list of canonical language values.

    SYSTEM_PROMPT.md §2.8 allows a cross-language task to declare more than one
    language. The separator is a comma, matching LOADED: `/` cannot serve as one
    because it is already part of the `I/O` SCOPE value, so `C/C++` is a single
    unrecognised token rather than two languages.
    """
    raw = fields.get("LANG", "").strip()
    if not raw:
        errors.append("LANG field is required")
        return

    langs = parse_lang_list(raw)
    if not langs:
        errors.append("LANG must name at least one language")
        return

    invalid = [item for item in langs if item not in VALID_LANG]
    if invalid:
        hint = ""
        if any("/" in item for item in invalid):
            suggestion = ", ".join(
                part.strip()
                for item in invalid
                for part in item.split("/")
                if part.strip() in VALID_LANG
            )
            if suggestion:
                hint = f" Use a comma-separated list instead, e.g. '{suggestion}'."
        errors.append(
            f"LANG invalid: {invalid}. Allowed: {sorted(VALID_LANG)}.{hint}"
        )
        return

    duplicates = sorted({item for item in langs if langs.count(item) > 1})
    if duplicates:
        errors.append(f"LANG lists duplicate language(s): {duplicates}")


def _validate_rules(fields: dict, errors: list[str], available: set[str] | None = None) -> None:
    rules_raw = fields.get("RULES", "").strip()
    if not rules_raw:
        errors.append("RULES field is required")
        return

    rule_names = parse_rule_list(rules_raw)
    if not rule_names:
        errors.append("RULES must contain at least one rule pack")
        return

    available = available or available_rule_packs()
    invalid = [name for name in rule_names if name not in available]
    if invalid:
        errors.append(
            f"RULES contains unknown rule pack(s): {invalid}. Available: {sorted(available)}"
        )


def _validate_runtime_fields(
    fields: dict,
    errors: list[str],
    available_rules: set[str] | None = None,
) -> None:
    """Validate the runtime contract fields defined by governance/RUNTIME_CONTRACT.md."""
    _validate_rules(fields, errors, available=available_rules)
    _validate_choice(fields, "RISK", VALID_RISK_LEVELS, errors)
    _validate_choice(fields, "OVERSIGHT", VALID_OVERSIGHT_LEVELS, errors)
    _validate_choice(fields, "MEMORY_MODE", VALID_MEMORY_MODES, errors)


def validate_display_contract(text: str) -> ValidationResult:
    """Validate only the SYSTEM_PROMPT.md §2.8 display fields.

    A display pass says nothing about whether a task may execute. Do not report
    it as runtime compliance — see governance/RUNTIME_CONTRACT.md.
    """
    return validate_contract(text, include_runtime=False)


def validate_runtime_contract(
    text: str,
    available_rules: set[str] | None = None,
) -> ValidationResult:
    """Validate only the governance/RUNTIME_CONTRACT.md fields."""
    block = extract_contract_block(text)
    if block is None:
        return ValidationResult(
            compliant=False,
            contract_found=False,
            fields={},
            errors=["[Governance Contract] block not found"],
        )
    fields = parse_contract_fields(block)
    errors: list[str] = []
    _validate_runtime_fields(fields, errors, available_rules=available_rules)
    return ValidationResult(
        compliant=not errors,
        contract_found=True,
        fields=fields,
        errors=errors,
    )


def validate_contract(
    text: str,
    available_rules: set[str] | None = None,
    include_runtime: bool = True,
) -> ValidationResult:
    block = extract_contract_block(text)
    if block is None:
        return ValidationResult(
            compliant=False,
            contract_found=False,
            fields={},
            errors=["[Governance Contract] block not found"],
        )

    fields = parse_contract_fields(block)
    errors: list[str] = []
    warnings: list[str] = []

    _validate_lang(fields, errors)

    level = fields.get("LEVEL", "").strip()
    if not level:
        errors.append("LEVEL field is required")
    elif level not in VALID_LEVEL:
        errors.append(f"LEVEL invalid: '{level}'. Allowed: {sorted(VALID_LEVEL)}")

    # SCOPE is single-valued per SYSTEM_PROMPT.md §2.8: it drives review, testing
    # and governance routing, and a list would need precedence rules that do not
    # exist. LANG has no such consequence, which is why only LANG takes a list.
    scope = fields.get("SCOPE", "").strip()
    if not scope:
        errors.append("SCOPE field is required")
    elif scope not in VALID_SCOPE:
        if "," in scope:
            errors.append(
                f"SCOPE invalid: '{scope}'. SCOPE is single-valued; split the task or pick the "
                f"dominant scope. Allowed: {sorted(VALID_SCOPE)}"
            )
        else:
            errors.append(f"SCOPE invalid: '{scope}'. Allowed: {sorted(VALID_SCOPE)}")

    if not fields.get("PLAN", "").strip():
        warnings.append("PLAN missing; recommended to bind responses to PLAN.md")

    loaded_raw = fields.get("LOADED", "").strip()
    if not loaded_raw:
        errors.append("LOADED field is required")
    else:
        loaded_docs = {
            normalize_loaded_identifier(doc) for doc in loaded_raw.split(",") if doc.strip()
        }
        missing_required = REQUIRED_LOADED - loaded_docs
        if missing_required:
            errors.append(f"LOADED missing required documents: {sorted(missing_required)}")

    context = fields.get("CONTEXT", "").strip()
    if not context:
        errors.append("CONTEXT field is required")
    else:
        if "->" not in context and "--" not in context:
            errors.append("CONTEXT must include active scope using '->' or '--'")
        if "NOT:" not in context:
            errors.append("CONTEXT must include a 'NOT:' exclusion clause")

    _validate_pressure(fields, errors)

    if include_runtime:
        _validate_runtime_fields(fields, errors, available_rules=available_rules)

    agent_id = fields.get("AGENT_ID", "").strip()
    session = fields.get("SESSION", "").strip()
    if agent_id:
        if not session:
            errors.append("AGENT_ID requires SESSION in YYYY-MM-DD-NN format")
        elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d+", session):
            errors.append(f"SESSION invalid: '{session}'. Expected YYYY-MM-DD-NN format")
    elif session:
        warnings.append("SESSION provided without AGENT_ID")

    return ValidationResult(
        compliant=len(errors) == 0,
        contract_found=True,
        fields=fields,
        errors=errors,
        warnings=warnings,
    )


def format_human(result: ValidationResult) -> str:
    if not result.contract_found:
        return "ERROR: [Governance Contract] block not found"

    lines = ["[Governance Contract] validation", ""]
    for key in DISPLAY_FIELDS:
        lines.append(f"{key:<12} = {result.fields.get(key, '<missing>')}")

    lines.append("")
    lines.append(f"errors: {len(result.errors)}")
    for err in result.errors:
        lines.append(f"- {err}")

    if result.warnings:
        lines.append("")
        lines.append(f"warnings: {len(result.warnings)}")
        for warning in result.warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines)


def format_json(result: ValidationResult) -> str:
    return json.dumps(
        {
            "compliant": result.compliant,
            "contract_found": result.contract_found,
            "fields": result.fields,
            "errors": result.errors,
            "warnings": result.warnings,
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a machine-readable [Governance Contract] block."
    )
    parser.add_argument("--file", "-f", help="Text file containing the AI response.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    if args.file:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"ERROR: file not found: {args.file}", file=sys.stderr)
            sys.exit(2)
    else:
        text = sys.stdin.read()

    result = validate_contract(text)
    print(format_json(result) if args.format == "json" else format_human(result))

    if not result.contract_found:
        sys.exit(2)
    if not result.compliant:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
