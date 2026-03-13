#!/usr/bin/env python3
"""
Normalize test runner output into runtime-governance check payloads.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from governance_tools.failure_test_validator import validate_failure_test_coverage


def _base_result(source: str, passed: int = 0, failed: int = 0, skipped: int = 0) -> dict:
    return {
        "source": source,
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "test_names": [],
        "failure_test_validation": None,
        "warnings": [],
        "errors": [],
        "ok": failed == 0,
    }


def _finalize_result(result: dict, require_rollback: bool = False) -> dict:
    failure_validation = validate_failure_test_coverage(
        result.get("test_names", []),
        require_rollback=require_rollback,
    )
    result["failure_test_validation"] = failure_validation
    result["warnings"].extend(failure_validation["warnings"])
    result["errors"].extend(failure_validation["errors"])
    result["ok"] = result["summary"]["failed"] == 0 and len(result["errors"]) == 0
    return result


def ingest_pytest_text(text: str, require_rollback: bool = False) -> dict:
    result = _base_result("pytest-text")
    normalized = text.replace("\r\n", "\n")

    passed_match = re.search(r"(\d+)\s+passed\b", normalized, re.IGNORECASE)
    failed_match = re.search(r"(\d+)\s+failed\b", normalized, re.IGNORECASE)
    skipped_match = re.search(r"(\d+)\s+skipped\b", normalized, re.IGNORECASE)
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    result["summary"] = {"passed": passed, "failed": failed, "skipped": skipped}
    result["ok"] = failed == 0

    for line in normalized.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("FAILED ") or stripped.startswith("ERROR "):
            result["errors"].append(stripped)
            case_id = stripped.split(" ", 1)[1].split(" - ", 1)[0].strip()
            if case_id not in result["test_names"]:
                result["test_names"].append(case_id)
        elif "PytestCacheWarning" in stripped or stripped.startswith("warning:"):
            result["warnings"].append(stripped)
        elif stripped.startswith("tests/") and "::" in stripped:
            case_id = stripped.split()[0].strip()
            if case_id not in result["test_names"]:
                result["test_names"].append(case_id)

    if result["summary"]["failed"] > 0 and not result["errors"]:
        result["errors"].append(f"pytest reported {result['summary']['failed']} failing test(s)")

    return _finalize_result(result, require_rollback=require_rollback)


def ingest_junit_xml(text: str, require_rollback: bool = False) -> dict:
    root = ET.fromstring(text)
    suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
    if not suites and root.tag == "testsuites":
        suites = list(root)

    passed = 0
    failed = 0
    skipped = 0
    errors = []

    for suite in suites:
        tests = int(suite.attrib.get("tests", "0") or 0)
        failures = int(suite.attrib.get("failures", "0") or 0)
        suite_errors = int(suite.attrib.get("errors", "0") or 0)
        suite_skipped = int(
            suite.attrib.get("skipped", suite.attrib.get("skip", "0")) or 0
        )
        passed += max(tests - failures - suite_errors - suite_skipped, 0)
        failed += failures + suite_errors
        skipped += suite_skipped

        for testcase in suite.findall(".//testcase"):
            name = testcase.attrib.get("name", "unnamed-test")
            classname = testcase.attrib.get("classname", "").strip()
            label = f"{classname}::{name}" if classname else name
            for node in list(testcase.findall("failure")) + list(testcase.findall("error")):
                message = (node.attrib.get("message") or node.text or "").strip()
                errors.append(f"{label} - {message}" if message else label)

    result = _base_result("junit-xml", passed=passed, failed=failed, skipped=skipped)
    # test names are collected from every testcase label for downstream failure-path validation
    for suite in suites:
        for testcase in suite.findall(".//testcase"):
            name = testcase.attrib.get("name", "unnamed-test")
            classname = testcase.attrib.get("classname", "").strip()
            label = f"{classname}::{name}" if classname else name
            if label not in result["test_names"]:
                result["test_names"].append(label)
    result["errors"] = errors
    return _finalize_result(result, require_rollback=require_rollback)


def ingest_test_results(path: Path, kind: str, require_rollback: bool = False) -> dict:
    text = path.read_text(encoding="utf-8")
    if kind == "pytest-text":
        return ingest_pytest_text(text, require_rollback=require_rollback)
    if kind == "junit-xml":
        return ingest_junit_xml(text, require_rollback=require_rollback)
    raise ValueError(f"Unsupported test result kind: {kind}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize test results for runtime governance.")
    parser.add_argument("--file", required=True)
    parser.add_argument("--kind", choices=["pytest-text", "junit-xml"], required=True)
    parser.add_argument("--require-rollback", action="store_true")
    args = parser.parse_args()

    result = ingest_test_results(Path(args.file), args.kind, require_rollback=args.require_rollback)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
