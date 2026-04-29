#!/usr/bin/env python3
"""
CI/CD pipeline runner for nextjs-byok contract validators.

Usage:
  python run_validators.py fixtures/ingest_byok_violation.checks.json
  python run_validators.py fixtures/
  python run_validators.py
  python run_validators.py --json

Exit codes:
  0  All hard-stop validators passed (advisory warnings allowed)
  1  One or more hard-stop violations detected
  2  Usage / file-not-found error

All rules are currently advisory — exit code is always 0 unless promoted.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

VALIDATORS_DIR = Path(__file__).parent / "validators"

_VALIDATOR_MODULES: list[str] = [
    "byok_key_propagation_validator",
    "route_rate_limit_validator",
]

# No hard-stop rules yet — promoted after evaluation threshold is met.
_HARD_STOP_RULES: set[str] = set()


# ── Stub interface ────────────────────────────────────────────────────────────

class _ValidatorResult:
    def __init__(self, ok, rule_ids, violations=None, warnings=None,
                 evidence_summary="", metadata=None):
        self.ok = ok
        self.rule_ids = rule_ids
        self.violations = violations or []
        self.warnings = warnings or []
        self.evidence_summary = evidence_summary
        self.metadata = metadata or {}


class _DomainValidator:
    @property
    def rule_ids(self):
        return []

    def validate(self, payload):
        raise NotImplementedError


def _inject_stubs():
    import types
    if "governance_tools" in sys.modules:
        return
    pkg = types.ModuleType("governance_tools")
    iface = types.ModuleType("governance_tools.validator_interface")
    iface.DomainValidator = _DomainValidator          # type: ignore[attr-defined]
    iface.ValidatorResult = _ValidatorResult          # type: ignore[attr-defined]
    sys.modules["governance_tools"] = pkg
    sys.modules["governance_tools.validator_interface"] = iface


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_validator(module_name):
    path = VALIDATORS_DIR / f"{module_name}.py"
    if not path.exists():
        print(f"  [WARN] validator not found: {path}", file=sys.stderr)
        return None
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in dir(mod):
        obj = getattr(mod, attr)
        try:
            if isinstance(obj, type) and issubclass(obj, _DomainValidator) and obj is not _DomainValidator:
                return obj()
        except TypeError:
            continue
    print(f"  [WARN] No DomainValidator subclass in {path}", file=sys.stderr)
    return None


# ── Runner ────────────────────────────────────────────────────────────────────

def _run_fixture(fixture_path, validators):
    try:
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"fixture": str(fixture_path), "error": str(exc), "passed": False}

    payload = {"checks": raw, **raw}
    results = []
    hard_stop_hit = False

    for name, validator in validators:
        try:
            result = validator.validate(payload)
        except Exception as exc:
            results.append({"validator": name, "error": str(exc), "ok": False})
            continue

        is_hard_stop = bool(set(result.rule_ids) & _HARD_STOP_RULES and not result.ok)
        if is_hard_stop:
            hard_stop_hit = True

        results.append({
            "validator": name,
            "ok": result.ok,
            "hard_stop": is_hard_stop,
            "violations": result.violations,
            "warnings": result.warnings,
            "evidence_summary": result.evidence_summary,
            "metadata": result.metadata,
        })

    return {"fixture": str(fixture_path), "passed": not hard_stop_hit, "results": results}


def _collect_fixtures(target):
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(target.glob("*.checks.json"))
    return sorted(Path(__file__).parent.glob("fixtures/**/*.checks.json"))


def _print_report(fixture_result, verbose, out=None):
    if out is None:
        out = sys.stdout
    fixture = fixture_result.get("fixture", "?")
    status = "PASS" if fixture_result.get("passed") else "FAIL"
    print(f"\n{'='*60}", file=out)
    print(f"  {status}  {fixture}", file=out)
    print(f"{'='*60}", file=out)
    if "error" in fixture_result:
        print(f"  ERROR: {fixture_result['error']}", file=out)
        return
    for r in fixture_result.get("results", []):
        if r.get("error"):
            print(f"  [{r['validator']}] ERROR: {r['error']}", file=out)
            continue
        ok = r.get("ok", True)
        tag = "HARD-STOP" if r.get("hard_stop") else ("WARN(advisory)" if not ok else "ok")
        print(f"  [{r['validator']:48s}] {tag:14s}  {r.get('evidence_summary', '')}", file=out)
        if verbose or not ok:
            for v in r.get("violations", []):
                print(f"      VIOLATION: {v}", file=out)
            for w in r.get("warnings", []):
                print(f"      warning  : {w}", file=out)


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="Next.js BYOK contract validator runner")
    parser.add_argument("target", nargs="?")
    parser.add_argument("--validator", "-V")
    parser.add_argument("--json", "-j", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    _inject_stubs()

    module_names = [args.validator] if args.validator else _VALIDATOR_MODULES
    validators = []
    for name in module_names:
        v = _load_validator(name)
        if v:
            validators.append((name, v))

    if not validators:
        print("ERROR: No validators loaded.", file=sys.stderr)
        return 2

    target = Path(args.target) if args.target else Path(__file__).parent
    fixtures = _collect_fixtures(target)

    if not fixtures:
        print(f"ERROR: No *.checks.json files found at {target}", file=sys.stderr)
        return 2

    all_results = []
    overall_pass = True
    text_out = sys.stderr if args.json else sys.stdout

    for fixture_path in fixtures:
        fr = _run_fixture(fixture_path, validators)
        all_results.append(fr)
        _print_report(fr, verbose=args.verbose, out=text_out)
        if not fr.get("passed"):
            overall_pass = False

    total = len(all_results)
    passed_count = sum(1 for r in all_results if r.get("passed"))
    print(f"\n{'='*60}", file=text_out)
    print(f"  SUMMARY: {passed_count}/{total} fixtures passed", file=text_out)
    print(f"  RESULT : {'ALL HARD-STOP CHECKS PASSED' if overall_pass else 'HARD-STOP VIOLATIONS DETECTED'}", file=text_out)
    print(f"{'='*60}\n", file=text_out)

    if args.json:
        print(json.dumps({"overall_pass": overall_pass, "fixtures": all_results}, indent=2))

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
