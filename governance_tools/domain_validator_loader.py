#!/usr/bin/env python3
"""
Discovery and execution helpers for external domain validators.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from governance_tools.domain_contract_loader import load_domain_contract
from governance_tools.validator_interface import DomainValidator, ValidatorResult


def _normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    rendered = str(value).strip()
    return [rendered] if rendered else []


def _extract_isr_code(checks: dict) -> str:
    for key in ("isr_code", "interrupt_handler_code", "irq_code"):
        value = checks.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _load_module_from_path(module_path: Path):
    module_name = f"domain_validator_{module_path.stem}_{abs(hash(str(module_path)))}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def discover_domain_validators(contract_file: str | Path | None) -> list[dict]:
    contract = load_domain_contract(contract_file)
    if not contract:
        return []

    discovered = []
    for item in contract.get("validators", []):
        validator_path = Path(item["path"])
        entry = {
            "name": item["name"],
            "path": item["path"],
            "exists": item["exists"],
            "ok": False,
            "rule_ids": [],
            "errors": [],
            "validator": None,
        }
        if not validator_path.exists():
            entry["errors"].append("validator file not found")
            discovered.append(entry)
            continue

        try:
            module = _load_module_from_path(validator_path)
            validator_instance = None
            for value in module.__dict__.values():
                if isinstance(value, type) and issubclass(value, DomainValidator) and value is not DomainValidator:
                    validator_instance = value()
                    break
            if validator_instance is None:
                entry["errors"].append("no DomainValidator implementation found")
            else:
                entry["ok"] = True
                entry["validator"] = validator_instance
                entry["rule_ids"] = list(validator_instance.rule_ids)
        except Exception as exc:  # pragma: no cover
            entry["errors"].append(str(exc))
        discovered.append(entry)
    return discovered


def preflight_domain_validators(contract_file: str | Path | None) -> dict | None:
    contract = load_domain_contract(contract_file)
    if not contract:
        return None

    validators = discover_domain_validators(contract_file)
    return {
        "ok": all(item["ok"] for item in validators),
        "count": len(validators),
        "validators": [
            {
                "name": item["name"],
                "path": item["path"],
                "ok": item["ok"],
                "rule_ids": item["rule_ids"],
                "errors": item["errors"],
            }
            for item in validators
        ],
    }


def build_domain_validation_payload(
    *,
    response_text: str,
    checks: dict | None,
    fields: dict,
    resolved_rules: list[str],
    domain_contract: dict | None,
) -> dict:
    effective_checks = checks or {}
    return {
        "rule_ids": resolved_rules,
        "checks": effective_checks,
        "response_text": response_text,
        "contract_fields": fields,
        "isr_code": _extract_isr_code(effective_checks),
        "changed_functions": _normalize_string_list(effective_checks.get("changed_functions")),
        "changed_files": _normalize_string_list(effective_checks.get("changed_files") or effective_checks.get("files")),
        "domain_documents": (domain_contract or {}).get("documents", []),
        "ai_behavior_override": (domain_contract or {}).get("ai_behavior_override", []),
    }


def run_domain_validators(
    *,
    contract_file: str | Path | None,
    payload: dict,
    active_rule_ids: list[str],
) -> list[dict]:
    results = []
    for item in discover_domain_validators(contract_file):
        validator = item.get("validator")
        if not item["ok"] or validator is None:
            results.append(
                {
                    "name": item["name"],
                    "ok": False,
                    "rule_ids": item["rule_ids"],
                    "violations": [],
                    "warnings": [],
                    "evidence_summary": "",
                    "metadata": {},
                    "errors": item["errors"],
                }
            )
            continue

        if not (set(item["rule_ids"]) & set(active_rule_ids)):
            continue

        result = validator.validate(payload)
        if not isinstance(result, ValidatorResult):
            raise TypeError(f"{item['name']} returned unsupported result type")
        rendered = result.to_dict()
        rendered["name"] = item["name"]
        results.append(rendered)
    return results
