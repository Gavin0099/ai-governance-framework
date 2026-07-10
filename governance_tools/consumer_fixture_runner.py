#!/usr/bin/env python3
"""
Report-only runner for consumer/domain-contract validator fixtures.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.domain_contract_loader import load_domain_contract, resolve_domain_contract
from governance_tools.domain_validator_loader import build_domain_validation_payload, discover_domain_validators
from governance_tools.test_signal_quality_audit import _fixture_matches_alias, _validator_aliases
from governance_tools.validator_interface import ValidatorResult


SCHEMA = "consumer_fixture_runner.v0.1"
STATUS = "report_only"
REQUIRED_CANNOT_CLAIM = [
    "fixture expectations are domain truth",
    "validators are semantically complete",
    "test suite is industry-grade",
    "CI, hook, readiness, or release gates enforce this result",
    "mutation resistance is proven",
]


@dataclass
class FixtureEntry:
    manifest: Path
    fixture: Path
    entry: dict[str, Any]


@dataclass
class RunnerReport:
    repo_root: Path
    contract_path: Path | None
    overall_status: str
    fixtures_total: int
    observations_total: int
    matched_expectations: int
    mismatched_expectations: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    cannot_claim: list[str] = field(default_factory=lambda: list(REQUIRED_CANNOT_CLAIM))


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_git_worktree_root(repo_root: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return False
    try:
        return Path(completed.stdout.strip()).resolve() == repo_root.resolve()
    except OSError:
        return False


def _gitignored_paths(repo_root: Path, paths: list[Path]) -> set[str]:
    if not paths or not _is_git_worktree_root(repo_root):
        return set()
    rel_paths = [_repo_rel(repo_root, path) for path in paths]
    payload = b"".join(path.encode("utf-8") + b"\0" for path in rel_paths)
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "-z", "--stdin"],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return set()
    if completed.returncode not in {0, 1}:
        return set()
    return {
        item.decode("utf-8", errors="replace")
        for item in completed.stdout.split(b"\0")
        if item
    }


def _git_visible_paths(repo_root: Path, paths: list[Path]) -> list[Path]:
    ignored = _gitignored_paths(repo_root, paths)
    if not ignored:
        return paths
    return [path for path in paths if _repo_rel(repo_root, path) not in ignored]


def _load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON: {exc.msg}"
    except OSError as exc:
        return None, f"{path}: unable to read file: {exc}"


def _manifest_items(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("fixtures"), list):
        items = payload["fixtures"]
    else:
        return None
    return [item for item in items if isinstance(item, dict) and item.get("file")]


def _manifest_paths(repo_root: Path) -> list[Path]:
    return _git_visible_paths(repo_root, sorted(repo_root.rglob("fixture_manifest.json")))


def _checks_fixture_candidates(repo_root: Path) -> list[Path]:
    return _git_visible_paths(repo_root, sorted(repo_root.rglob("fixtures/*.checks.json")))


def _load_fixture_entries(repo_root: Path) -> tuple[list[FixtureEntry], list[str], list[str]]:
    entries: list[FixtureEntry] = []
    warnings: list[str] = []
    errors: list[str] = []
    for manifest in _manifest_paths(repo_root):
        payload, error = _load_json(manifest)
        if error:
            errors.append(f"fixture_manifest_error: {_repo_rel(repo_root, manifest)}: {error}")
            continue
        items = _manifest_items(payload)
        if items is None:
            warnings.append(f"fixture_manifest_unrecognized_shape: {_repo_rel(repo_root, manifest)}")
            continue
        for item in items:
            fixture = (manifest.parent / str(item["file"])).resolve()
            if not fixture.exists() or not fixture.is_file():
                errors.append(
                    "fixture_missing: "
                    f"{_repo_rel(repo_root, fixture)} referenced by {_repo_rel(repo_root, manifest)}"
                )
                continue
            try:
                fixture.relative_to(repo_root.resolve())
            except ValueError:
                errors.append(
                    "fixture_outside_repo: "
                    f"{fixture} referenced by {_repo_rel(repo_root, manifest)}"
                )
                continue
            entries.append(FixtureEntry(manifest=manifest, fixture=fixture, entry=item))
    return entries, warnings, errors


def _entry_expected_ok(entry: dict[str, Any]) -> bool | None:
    return entry.get("expected_ok") if isinstance(entry.get("expected_ok"), bool) else None


def _entry_rule_ids(entry: dict[str, Any]) -> list[str]:
    value = entry.get("expected_rule_ids")
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _explicit_validator_matches(entry: dict[str, Any], validators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    explicit = str(entry.get("validator") or "").strip()
    if not explicit:
        return []
    matches = []
    for validator in validators:
        name = str(validator.get("name") or "")
        path = str(validator.get("path") or "")
        if explicit in {name, path, Path(path).name, Path(path).stem}:
            matches.append(validator)
    return matches


def _rule_id_matches(entry: dict[str, Any], validators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected_rule_ids = set(_entry_rule_ids(entry))
    if not expected_rule_ids:
        return []
    return [
        validator
        for validator in validators
        if expected_rule_ids.intersection(str(rule_id) for rule_id in validator.get("rule_ids", []))
    ]


def _alias_matches(repo_root: Path, fixture: Path, validators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rel = _repo_rel(repo_root, fixture)
    matches = []
    for validator in validators:
        name = str(validator.get("name") or Path(str(validator.get("path") or "")).stem)
        if _fixture_matches_alias(rel, _validator_aliases(name)):
            matches.append(validator)
    return matches


def _matching_validators(
    repo_root: Path,
    fixture_entry: FixtureEntry,
    validators: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    if _entry_rule_ids(fixture_entry.entry):
        matches = _rule_id_matches(fixture_entry.entry, validators)
        if matches:
            return "expected_rule_ids", matches
        return "unmatched_expected_rule_ids", []

    matches = _explicit_validator_matches(fixture_entry.entry, validators)
    if matches:
        return "explicit_validator", matches

    matches = _alias_matches(repo_root, fixture_entry.fixture, validators)
    if len(matches) == 1:
        return "alias", matches
    if len(matches) > 1:
        return "ambiguous_alias", matches
    return "unmatched", []


def _run_validator(
    *,
    validator_entry: dict[str, Any],
    fixture_entry: FixtureEntry,
    fixture_json: dict[str, Any],
    contract: dict[str, Any] | None,
    contract_path: Path | None,
) -> dict[str, Any]:
    validator = validator_entry.get("validator")
    if validator is None:
        raise RuntimeError("validator instance unavailable")
    resolved_rules = _entry_rule_ids(fixture_entry.entry) or list(validator_entry.get("rule_ids", []))
    payload = build_domain_validation_payload(
        response_text="",
        checks=fixture_json,
        fields={},
        resolved_rules=resolved_rules,
        domain_contract=contract,
        contract_file=contract_path,
    )
    result = validator.validate(payload)
    if not isinstance(result, ValidatorResult):
        raise TypeError(f"{validator_entry.get('name')} returned unsupported result type")
    return result.to_dict()


def build_consumer_fixture_report(
    repo_root: str | Path,
    *,
    contract: str | Path | None = None,
) -> RunnerReport:
    repo = Path(repo_root).resolve()
    warnings: list[str] = []
    errors: list[str] = []

    contract_path = resolve_domain_contract(contract, project_root=repo)
    loaded_contract = load_domain_contract(contract_path) if contract_path else None
    validators = discover_domain_validators(contract_path) if contract_path else []
    runnable_validators = [item for item in validators if item.get("ok") and item.get("validator") is not None]

    if contract_path is None:
        errors.append("contract_not_found")
    for item in validators:
        for error in item.get("errors", []):
            errors.append(f"validator_load_error: {item.get('name')}: {error}")

    manifest_paths = _manifest_paths(repo)
    fixtures, manifest_warnings, manifest_errors = _load_fixture_entries(repo)
    warnings.extend(manifest_warnings)
    errors.extend(manifest_errors)
    manifest_missing = False
    if not manifest_paths:
        checks_fixtures = _checks_fixture_candidates(repo)
        if checks_fixtures:
            manifest_missing = True
            warnings.append(
                "fixture_manifest_missing: "
                f"found {len(checks_fixtures)} fixtures/*.checks.json candidate(s) "
                "but no fixture_manifest.json"
            )

    observations: list[dict[str, Any]] = []
    matched = 0
    mismatched = 0

    for item in fixtures:
        expected_ok = _entry_expected_ok(item.entry)
        if expected_ok is None:
            errors.append(f"fixture_expected_ok_missing: {_repo_rel(repo, item.fixture)}")
            continue

        route, matches = _matching_validators(repo, item, runnable_validators)
        if route == "ambiguous_alias":
            warnings.append(
                "ambiguous_fixture_validator_match: "
                f"{_repo_rel(repo, item.fixture)} matched "
                f"{', '.join(str(match.get('name')) for match in matches)}"
            )
            continue
        if not matches:
            warnings.append(f"fixture_unmatched: {_repo_rel(repo, item.fixture)}")
            continue

        fixture_payload, load_error = _load_json(item.fixture)
        if load_error or not isinstance(fixture_payload, dict):
            errors.append(f"fixture_load_error: {_repo_rel(repo, item.fixture)}")
            continue

        for validator in matches:
            try:
                result = _run_validator(
                    validator_entry=validator,
                    fixture_entry=item,
                    fixture_json=fixture_payload,
                    contract=loaded_contract,
                    contract_path=contract_path,
                )
            except Exception as exc:  # pragma: no cover - defensive path is still surfaced.
                errors.append(f"validator_execution_error: {validator.get('name')}: {_repo_rel(repo, item.fixture)}: {exc}")
                continue

            observed_ok = bool(result.get("ok"))
            is_match = observed_ok == expected_ok
            if is_match:
                matched += 1
            else:
                mismatched += 1
            observations.append(
                {
                    "fixture": _repo_rel(repo, item.fixture),
                    "manifest": _repo_rel(repo, item.manifest),
                    "validator": validator.get("name"),
                    "validator_path": _repo_rel(repo, Path(str(validator.get("path")))),
                    "route": route,
                    "expected_ok": expected_ok,
                    "observed_ok": observed_ok,
                    "matched": is_match,
                    "rule_ids": result.get("rule_ids", []),
                    "violations": result.get("violations", []),
                    "warnings": result.get("warnings", []),
                    "evidence_summary": result.get("evidence_summary", ""),
                    "metadata": result.get("metadata", {}),
                }
            )

    if errors:
        overall = "error"
    elif not validators:
        overall = "no_validators"
    elif manifest_missing:
        overall = "manifest_missing"
    elif not fixtures:
        overall = "no_fixtures"
    elif mismatched:
        overall = "mismatch"
    elif observations:
        overall = "all_expected"
    else:
        overall = "error"

    return RunnerReport(
        repo_root=repo,
        contract_path=contract_path,
        overall_status=overall,
        fixtures_total=len(fixtures),
        observations_total=len(observations),
        matched_expectations=matched,
        mismatched_expectations=mismatched,
        errors=errors,
        warnings=warnings,
        observations=observations,
    )


def report_to_dict(report: RunnerReport) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "repo_root": str(report.repo_root),
        "contract_path": str(report.contract_path) if report.contract_path else None,
        "overall_status": report.overall_status,
        "fixtures_total": report.fixtures_total,
        "observations_total": report.observations_total,
        "matched_expectations": report.matched_expectations,
        "mismatched_expectations": report.mismatched_expectations,
        "errors": report.errors,
        "warnings": report.warnings,
        "observations": report.observations,
        "cannot_claim": report.cannot_claim,
    }


def format_human(report: RunnerReport) -> str:
    lines = [
        "[consumer_fixture_runner]",
        f"schema={SCHEMA}",
        f"status={STATUS}",
        f"overall_status={report.overall_status}",
        f"fixtures_total={report.fixtures_total}",
        f"observations_total={report.observations_total}",
        f"matched_expectations={report.matched_expectations}",
        f"mismatched_expectations={report.mismatched_expectations}",
    ]
    if report.contract_path:
        lines.append(f"contract_path={report.contract_path}")
    if report.observations:
        lines.append("observations:")
        for item in report.observations:
            lines.append(
                "  - "
                f"{item['fixture']} -> {item['validator']} "
                f"expected_ok={str(item['expected_ok']).lower()} "
                f"observed_ok={str(item['observed_ok']).lower()} "
                f"matched={str(item['matched']).lower()}"
            )
    if report.warnings:
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in report.warnings)
    if report.errors:
        lines.append("errors:")
        lines.extend(f"  - {error}" for error in report.errors)
    lines.append("cannot_claim:")
    lines.extend(f"  - {claim}" for claim in report.cannot_claim)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run report-only consumer validator fixtures.")
    parser.add_argument("--repo", default=".", help="Consumer repo root.")
    parser.add_argument("--contract", help="Optional path to contract.yaml.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"ERROR: repo root not found: {repo}", file=sys.stderr)
        return 2

    report = build_consumer_fixture_report(repo, contract=args.contract)
    if args.format == "json":
        print(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
