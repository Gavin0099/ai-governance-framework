#!/usr/bin/env python3
"""
Report-only test-signal quality audit for domain contract repositories.

This tool surfaces lexical and fixture-shape signals from a consumer repo. It
does not prove test quality, execute validators, gate CI, or enforce policy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.contract_resolver import resolve_contract
from governance_tools.domain_contract_loader import load_domain_contract


REPORT_VERSION = "0.1"
MAX_EVIDENCE_PER_SIGNAL = 20

POSITIVE_TOKENS = (
    "positive",
    "valid",
    "pass",
    "passes",
    "passing",
    "compliant",
    "ok",
    "success",
    "allow",
)
NEGATIVE_TOKENS = (
    "negative",
    "invalid",
    "fail",
    "fails",
    "failing",
    "noncompliant",
    "violation",
    "bad",
    "deny",
    "error",
)
FIXTURE_ROOT_NAMES = {"fixture", "fixtures", "testdata", "test_data", "examples"}
PLACEHOLDER_PATTERNS = (
    "placeholder",
    "notimplemented",
    "not implemented",
    "stub validator",
    "validator stub",
    "fixture pending",
    "fixtures pending",
)
PRODUCTION_DERIVED_PATTERNS = (
    re.compile(r"\bexpected\s*=\s*(actual|result|output|observed)\b"),
    re.compile(r"\bassert\s+([A-Za-z_][\w\.]*)\s*==\s*\1\b"),
    re.compile(r"\bassert\s+([A-Za-z_][\w\.]*)\s*!=\s*\1\b"),
)
MOCK_ONLY_PATTERNS = (
    "assert_called_once",
    "assert_called_once_with",
    ".called",
    "received().",
)
UNCONTROLLED_TIME_PATTERNS = (
    "time.sleep(",
    "sleep(",
    "datetime.now(",
    "datetime.utcnow(",
    "date.today(",
    "time.time(",
    "random.random(",
    "random.randint(",
    "new Date(",
)


@dataclass
class EvidenceRef:
    path: str
    line: int | None = None
    reason: str = ""


@dataclass
class ValidatorFixtureSignal:
    name: str
    path: str
    exists: bool
    placeholder_labeled: bool
    positive_fixtures: list[str] = field(default_factory=list)
    negative_fixtures: list[str] = field(default_factory=list)
    status: str = "unknown"
    reasons: list[str] = field(default_factory=list)


@dataclass
class TestSignalQualityReport:
    report_version: str
    repo_root: str
    contract_path: str | None
    report_only: bool
    overall_status: str
    oracle_independence: str
    mutation_boundary: str
    determinism: str
    mock_signal: str
    legacy_baseline: str
    contract_validator_fixtures: str
    validators: list[ValidatorFixtureSignal] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    cannot_claim: list[str] = field(default_factory=list)
    claim_boundary: str = (
        "This audit is report-only. It does not prove industry-grade testing, "
        "domain correctness, validator correctness, mutation resistance, "
        "or CI/hook enforcement."
    )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _iter_repo_files(repo_root: Path) -> list[Path]:
    skipped_dirs = {
        ".git",
        ".hg",
        ".svn",
        ".pytest_cache",
        ".venv",
        "artifacts",
        "bin",
        "build",
        "coverage",
        "dist",
        "memory",
        "node_modules",
        "obj",
        "target",
        "venv",
        "__pycache__",
    }
    text_suffixes = {
        ".c",
        ".cc",
        ".cpp",
        ".cs",
        ".h",
        ".hpp",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".py",
        ".sv",
        ".ts",
        ".tsx",
        ".txt",
        ".v",
        ".yaml",
        ".yml",
    }
    files: list[Path] = []
    for root, dirs, filenames in os.walk(repo_root):
        dirs[:] = [
            name
            for name in dirs
            if name not in skipped_dirs and not name.startswith(".") and not name.startswith("_tmp")
        ]
        current = Path(root)
        for filename in filenames:
            path = current / filename
            if path.suffix.lower() not in text_suffixes:
                continue
            files.append(path)
    return files


def _is_test_file(repo_root: Path, path: Path) -> bool:
    rel_parts = {_part.lower() for _part in path.relative_to(repo_root).parts}
    name = path.name.lower()
    return (
        "tests" in rel_parts
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".spec.ts")
        or name.endswith(".tests.cs")
        or name.endswith("test.cs")
    )


def _is_fixture_file(repo_root: Path, path: Path) -> bool:
    rel_parts = {_part.lower() for _part in path.relative_to(repo_root).parts}
    name = path.name.lower()
    return bool(FIXTURE_ROOT_NAMES.intersection(rel_parts)) or "fixture" in name


def _split_signal_tokens(text: str) -> set[str]:
    return {item for item in re.split(r"[^a-z0-9]+", text.lower()) if item}


def _has_token(text: str, tokens: tuple[str, ...]) -> bool:
    parts = _split_signal_tokens(text)
    return any(token in parts for token in tokens)


def _looks_placeholder(path: Path) -> bool:
    if not path.exists():
        return False
    for line in _read_text(path).lower().splitlines():
        stripped = line.strip()
        if not stripped.startswith(("#", "//", "/*", "*")):
            continue
        if any(pattern in stripped for pattern in PLACEHOLDER_PATTERNS):
            return True
        if "todo" in stripped and "validator" in stripped:
            return True
    return False


def _candidate_fixture_files(repo_root: Path, validator_name: str, all_files: list[Path]) -> list[Path]:
    stem_tokens = {validator_name.lower()}
    for suffix in ("_validator", "-validator"):
        if validator_name.lower().endswith(suffix):
            stem_tokens.add(validator_name.lower()[: -len(suffix)])

    candidates: list[Path] = []
    for path in all_files:
        if not _is_fixture_file(repo_root, path):
            continue
        haystack = _repo_rel(repo_root, path).lower()
        if any(token and token in haystack for token in stem_tokens):
            candidates.append(path)
    return candidates


def _classify_validator(
    repo_root: Path,
    validator: dict,
    all_files: list[Path],
) -> ValidatorFixtureSignal:
    validator_path = Path(str(validator.get("path", ""))).resolve()
    exists = bool(validator.get("exists"))
    name = str(validator.get("name") or validator_path.stem)
    placeholder = _looks_placeholder(validator_path)
    fixtures = _candidate_fixture_files(repo_root, name, all_files)
    positive: list[str] = []
    negative: list[str] = []
    for path in fixtures:
        rel = _repo_rel(repo_root, path)
        has_negative = _has_token(rel, NEGATIVE_TOKENS)
        has_positive = _has_token(rel, POSITIVE_TOKENS)
        if has_negative:
            negative.append(rel)
        elif has_positive:
            positive.append(rel)

    reasons: list[str] = []
    if not exists:
        status = "validator_missing"
        reasons.append("contract declares a validator path that does not exist")
    elif positive and negative:
        status = "validator_fixture_pair_present"
        reasons.append("positive and negative fixture names were found; validator execution is not proven by this report")
    elif placeholder:
        status = "placeholder_validator_declared"
        reasons.append("validator file is explicitly labeled as placeholder")
    elif positive:
        status = "positive_only_validator_fixture"
        reasons.append("positive fixture filenames were found but no negative fixture filename was found")
    elif negative:
        status = "negative_only_validator_fixture"
        reasons.append("negative fixture filenames were found but no positive fixture filename was found")
    else:
        status = "validator_without_fixture_harness"
        reasons.append("no validator-related fixture filenames were found")

    return ValidatorFixtureSignal(
        name=name,
        path=_repo_rel(repo_root, validator_path),
        exists=exists,
        placeholder_labeled=placeholder,
        positive_fixtures=sorted(positive),
        negative_fixtures=sorted(negative),
        status=status,
        reasons=reasons,
    )


def _scan_lexical_signals(repo_root: Path, test_files: list[Path]) -> tuple[dict[str, list[EvidenceRef]], list[str]]:
    evidence: dict[str, list[EvidenceRef]] = {
        "production_derived_expected_value": [],
        "mock_only_candidate": [],
        "time_or_random_uncontrolled": [],
        "negative_or_boundary_case": [],
        "legacy_characterization": [],
    }
    warnings: list[str] = []

    def add_ref(signal: str, ref: EvidenceRef) -> None:
        if len(evidence[signal]) < MAX_EVIDENCE_PER_SIGNAL:
            evidence[signal].append(ref)

    for path in test_files:
        text = _read_text(path)
        lowered = text.lower()
        for line_no, line in enumerate(text.splitlines(), start=1):
            lowered_line = line.lower()
            if any(pattern.search(line) for pattern in PRODUCTION_DERIVED_PATTERNS):
                add_ref(
                    "production_derived_expected_value",
                    EvidenceRef(_repo_rel(repo_root, path), line_no, "expected value may be derived from observed output")
                )
            if any(pattern in lowered_line for pattern in MOCK_ONLY_PATTERNS):
                add_ref(
                    "mock_only_candidate",
                    EvidenceRef(_repo_rel(repo_root, path), line_no, "mock call assertion candidate")
                )
            if any(pattern in lowered_line for pattern in UNCONTROLLED_TIME_PATTERNS):
                add_ref(
                    "time_or_random_uncontrolled",
                    EvidenceRef(_repo_rel(repo_root, path), line_no, "uncontrolled time/random candidate")
                )
        if _has_token(lowered, ("invalid", "negative", "boundary", "malformed", "forbidden", "fail", "failure")):
            add_ref(
                "negative_or_boundary_case",
                EvidenceRef(_repo_rel(repo_root, path), None, "test file contains negative, boundary, or failure-path vocabulary")
            )
        if _has_token(lowered, ("characterization", "baseline commit", "known-good", "known good", "rollback point")):
            add_ref(
                "legacy_characterization",
                EvidenceRef(_repo_rel(repo_root, path), None, "legacy characterization or baseline vocabulary found")
            )

    if evidence["production_derived_expected_value"]:
        warnings.append("production_derived_expected_value candidate found")
    if evidence["mock_only_candidate"]:
        warnings.append("mock_only_weak_signal candidate found")
    if evidence["time_or_random_uncontrolled"]:
        warnings.append("time_or_random_uncontrolled candidate found")
    return evidence, warnings


def _first_status(statuses: list[str], default: str) -> str:
    return statuses[0] if statuses else default


def _contract_validator_status(validators: list[ValidatorFixtureSignal]) -> str:
    if not validators:
        return "not_applicable"
    statuses = [item.status for item in validators]
    if any(status == "validator_missing" for status in statuses):
        return "validator_missing"
    if any(status == "validator_without_fixture_harness" for status in statuses):
        return "validator_without_fixture_harness"
    if any(status in {"positive_only_validator_fixture", "negative_only_validator_fixture"} for status in statuses):
        return _first_status(
            [status for status in statuses if status in {"positive_only_validator_fixture", "negative_only_validator_fixture"}],
            "unknown",
        )
    if all(status == "placeholder_validator_declared" for status in statuses):
        return "placeholder_validator_declared"
    if any(status == "validator_fixture_pair_present" for status in statuses):
        return "validator_fixture_pair_present"
    return "unknown"


def _overall_status(fields: dict[str, str]) -> str:
    weak_values = {
        "production_derived_expected_value",
        "time_or_random_uncontrolled",
        "mock_only_weak_signal",
        "negative_cases_missing",
        "validator_missing",
        "validator_without_fixture_harness",
        "positive_only_validator_fixture",
        "negative_only_validator_fixture",
    }
    strong_values = {
        "independent_oracle_candidate",
        "negative_or_boundary_cases_present",
        "deterministic_or_no_warning_observed",
        "observable_behavior_or_no_mock_only_warning_observed",
        "validator_fixture_pair_present",
    }
    values = set(fields.values())
    if values & weak_values:
        return "weak"
    if fields.get("contract_validator_fixtures") == "not_applicable":
        return "unknown"
    if values and values.issubset(strong_values | {"not_applicable"}):
        return "strong_candidate"
    return "partial"


def build_test_signal_quality_audit(repo_root: str | Path, contract_file: str | Path | None = None) -> TestSignalQualityReport:
    repo = Path(repo_root).resolve()
    resolution = resolve_contract(contract_file, project_root=repo)
    warnings = list(resolution.warnings)
    evidence_refs: list[EvidenceRef] = []

    if resolution.path is None:
        if resolution.error:
            warnings.append(resolution.error)
        cannot_claim = [
            "test suite is industry-grade",
            "domain contract validator fixtures are present",
            "independent expected values are established",
            "negative, boundary, and failure-path coverage exists",
        ]
        return TestSignalQualityReport(
            report_version=REPORT_VERSION,
            repo_root=str(repo),
            contract_path=None,
            report_only=True,
            overall_status="unknown",
            oracle_independence="unknown",
            mutation_boundary="unknown",
            determinism="unknown",
            mock_signal="unknown",
            legacy_baseline="unknown",
            contract_validator_fixtures="unknown",
            warnings=warnings or ["contract.yaml not found"],
            cannot_claim=cannot_claim,
        )

    contract = load_domain_contract(resolution.path, skip_document_content=True) or {}
    all_files = _iter_repo_files(repo)
    test_files = [path for path in all_files if _is_test_file(repo, path)]
    lexical_evidence, lexical_warnings = _scan_lexical_signals(repo, test_files)
    warnings.extend(lexical_warnings)
    for refs in lexical_evidence.values():
        evidence_refs.extend(refs)

    validators = [
        _classify_validator(repo, item, all_files)
        for item in contract.get("validators", [])
        if isinstance(item, dict)
    ]
    contract_validator_fixtures = _contract_validator_status(validators)

    if lexical_evidence["production_derived_expected_value"]:
        oracle_independence = "production_derived_expected_value"
    elif test_files:
        oracle_independence = "independent_oracle_candidate"
    else:
        oracle_independence = "unknown"

    if lexical_evidence["negative_or_boundary_case"]:
        mutation_boundary = "negative_or_boundary_cases_present"
    elif test_files:
        mutation_boundary = "negative_cases_missing"
    else:
        mutation_boundary = "unknown"

    determinism = (
        "time_or_random_uncontrolled"
        if lexical_evidence["time_or_random_uncontrolled"]
        else ("deterministic_or_no_warning_observed" if test_files else "unknown")
    )
    mock_signal = (
        "mock_only_weak_signal"
        if lexical_evidence["mock_only_candidate"]
        else ("observable_behavior_or_no_mock_only_warning_observed" if test_files else "unknown")
    )
    legacy_baseline = "characterization_baseline_present" if lexical_evidence["legacy_characterization"] else "not_applicable"

    field_values = {
        "oracle_independence": oracle_independence,
        "mutation_boundary": mutation_boundary,
        "determinism": determinism,
        "mock_signal": mock_signal,
        "legacy_baseline": legacy_baseline,
        "contract_validator_fixtures": contract_validator_fixtures,
    }
    cannot_claim = [
        "test suite is industry-grade",
        "test coverage is sufficient",
        "fixtures prove domain truth",
        "validators are semantically correct",
        "CI or hook enforcement is present",
    ]
    if contract_validator_fixtures != "validator_fixture_pair_present":
        cannot_claim.append("all contract validators have pass/fail fixture pairs")
    if oracle_independence == "production_derived_expected_value":
        cannot_claim.append("expected values are independent")
    if mutation_boundary == "negative_cases_missing":
        cannot_claim.append("negative, boundary, and failure-path coverage exists")

    return TestSignalQualityReport(
        report_version=REPORT_VERSION,
        repo_root=str(repo),
        contract_path=str(resolution.path),
        report_only=True,
        overall_status=_overall_status(field_values),
        oracle_independence=oracle_independence,
        mutation_boundary=mutation_boundary,
        determinism=determinism,
        mock_signal=mock_signal,
        legacy_baseline=legacy_baseline,
        contract_validator_fixtures=contract_validator_fixtures,
        validators=validators,
        warnings=warnings,
        evidence_refs=evidence_refs,
        cannot_claim=cannot_claim,
    )


def report_to_dict(report: TestSignalQualityReport) -> dict[str, object]:
    return report.to_dict()


def format_human(report: TestSignalQualityReport) -> str:
    lines = [
        "[test_signal_quality]",
        f"report_only={str(report.report_only).lower()}",
        f"repo_root={report.repo_root}",
        f"contract_path={report.contract_path or 'none'}",
        f"overall_status={report.overall_status}",
        f"oracle_independence={report.oracle_independence}",
        f"mutation_boundary={report.mutation_boundary}",
        f"determinism={report.determinism}",
        f"mock_signal={report.mock_signal}",
        f"legacy_baseline={report.legacy_baseline}",
        f"contract_validator_fixtures={report.contract_validator_fixtures}",
    ]
    if report.validators:
        lines.append("validators:")
        for item in report.validators:
            lines.append(
                "  - "
                f"{item.name}: status={item.status} exists={str(item.exists).lower()} "
                f"positive={len(item.positive_fixtures)} negative={len(item.negative_fixtures)}"
            )
    if report.warnings:
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in report.warnings)
    if report.evidence_refs:
        lines.append("evidence_refs:")
        for ref in report.evidence_refs[:20]:
            suffix = f":{ref.line}" if ref.line is not None else ""
            reason = f" ({ref.reason})" if ref.reason else ""
            lines.append(f"  - {ref.path}{suffix}{reason}")
    lines.append("cannot_claim:")
    lines.extend(f"  - {item}" for item in report.cannot_claim)
    lines.append(f"claim_boundary={report.claim_boundary}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report-only test-signal quality audit for domain contract repos.")
    parser.add_argument("--repo", default=".", help="Repository root to audit.")
    parser.add_argument("--contract", help="Optional explicit contract.yaml path.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    report = build_test_signal_quality_audit(args.repo, args.contract)
    if args.format == "json":
        print(json.dumps(report_to_dict(report), indent=2, ensure_ascii=False))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
