#!/usr/bin/env python3
"""
Check whether a repo's governance files have drifted from the recorded baseline.

16 named checks across 4 categories:

  Category 1 — Baseline Metadata (4 checks):
    baseline_yaml_present       .governance/baseline.yaml exists and is parseable
    baseline_version_known      baseline_version field present and parseable
    framework_version_current   recorded version matches current framework baseline
    source_commit_recorded      source_commit is a valid git SHA (provenance enforcement)

  Category 2 — Protected File Integrity (3 checks):
    protected_files_present     all protected files exist on disk
    protected_files_unmodified  sha256 of protected files matches recorded hash
    protected_file_sentinel_present  AGENTS.base.md contains governance sentinel comment

  Category 3 — Overridable File Required Fields (6 checks):
    contract_required_fields_present  contract.yaml has all required fields
    contract_agents_base_referenced   AGENTS.base.md wired into contract documents
    contract_no_placeholders          contract.yaml values contain no <...> template tokens
    contract_not_framework_copy       contract.yaml is not a verbatim copy of the framework's own contract
    plan_required_sections_present    PLAN.md contains required section headings
    agents_sections_filled            AGENTS.md governance:key sections have real content

  Category 4 — Freshness (3 checks):
    plan_freshness              PLAN.md freshness via plan_freshness.py
    plan_inventory_current      plan_section_inventory in baseline matches current PLAN.md headings
    baseline_yaml_freshness     baseline.yaml age within --freshness-threshold days

Usage:
    python governance_tools/governance_drift_checker.py --repo /path/to/repo
    python governance_tools/governance_drift_checker.py --repo . --format json
    python governance_tools/governance_drift_checker.py --repo . --skip-hash

Exit codes: 0=ok, 1=warning, 2=critical
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.domain_contract_loader import _parse_contract_yaml
from governance_tools.framework_versioning import (
    compare_versions,
    discover_framework_root,
    repo_root_from_tooling,
)
from governance_tools.plan_freshness import check_freshness


BASELINE_YAML_RELPATH = ".governance/baseline.yaml"
BASELINE_SOURCE_RELPATH = "baselines/repo-min"
FRAMEWORK_DEFAULT_FRESHNESS_DAYS = 14

_PLACEHOLDER_RE = __import__("re").compile(r"<[A-Za-z][^>]+>")
_GOVERNANCE_KEY_RE = __import__("re").compile(r"<!--\s*governance:key=(\S+)\s*-->")


@dataclass
class BaselineDriftResult:
    ok: bool
    severity: str                         # "ok" | "warning" | "critical"
    repo_root: str
    baseline_yaml: str | None
    baseline_version: str | None
    framework_version: str | None
    checks: dict[str, bool] = field(default_factory=dict)
    findings: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    remediation_hints: list[str] = field(default_factory=list)
    plan_section_inventory: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _find_placeholders_in_contract(contract_data: dict) -> list[str]:
    """Return field names whose string values still contain <...> template tokens."""
    found: list[str] = []
    for key, value in contract_data.items():
        if isinstance(value, str) and _PLACEHOLDER_RE.search(value):
            found.append(key)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and _PLACEHOLDER_RE.search(item):
                    found.append(key)
                    break
    return found


def _detect_plan_sections(plan_text: str) -> list[str]:
    """Return all '## ' headings from PLAN.md, in order."""
    return [
        line.rstrip()
        for line in plan_text.splitlines()
        if line.startswith("## ")
    ]


def _find_empty_governance_sections(agents_text: str) -> list[str]:
    """Return governance:key names whose sections contain no real content.

    A section is considered empty if every non-blank line between the
    governance:key anchor and the next ## heading (or EOF) is inside
    an HTML comment block (single-line or multi-line <!-- ... -->).
    """
    lines = agents_text.splitlines()
    empty_keys: list[str] = []
    i = 0
    while i < len(lines):
        m = _GOVERNANCE_KEY_RE.match(lines[i].strip())
        if m:
            key = m.group(1)
            i += 1
            has_content = False
            in_comment = False
            while i < len(lines) and not lines[i].strip().startswith("##"):
                stripped = lines[i].strip()
                i += 1
                if not stripped:
                    continue
                if in_comment:
                    if "-->" in stripped:
                        in_comment = False
                    continue
                if stripped.startswith("<!--"):
                    if "-->" not in stripped:
                        in_comment = True  # multi-line comment opened
                    continue
                # Non-blank line outside any comment — real content
                has_content = True
                break
            if not has_content:
                empty_keys.append(key)
        else:
            i += 1
    return empty_keys


def _read_baseline_yaml(repo_root: Path) -> dict | None:
    path = repo_root / BASELINE_YAML_RELPATH
    if not path.exists():
        return None
    try:
        return _parse_contract_yaml(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _current_baseline_version(framework_root: Path) -> str | None:
    """Read baseline_version from the protected file sentinel comment."""
    agents_base = framework_root / BASELINE_SOURCE_RELPATH / "AGENTS.base.md"
    if not agents_base.exists():
        return None
    for line in agents_base.read_text(encoding="utf-8").splitlines():
        if "baseline_version:" in line and "<!--" in line:
            parts = line.split("baseline_version:")
            if len(parts) == 2:
                return parts[1].strip().rstrip("-->").strip()
    return None


def check_governance_drift(
    repo_root: Path,
    framework_root: Path | None = None,
    freshness_threshold_days: int = 90,
    skip_hash: bool = False,
) -> BaselineDriftResult:
    repo_root = repo_root.resolve()
    if framework_root is not None:
        # Explicit caller-supplied path — highest priority, no discovery needed.
        framework_root = framework_root.resolve()
    else:
        import os
        _env_root = os.environ.get("GOVERNANCE_FRAMEWORK_ROOT", "").strip()
        if _env_root:
            # ENV var — user-controlled implicit; second priority.
            framework_root = Path(_env_root).resolve()
        else:
            # Upward scan — best-effort; starts from repo_root.
            framework_root = discover_framework_root(repo_root)
            if framework_root is None:
                # Last resort: __file__-based default (running from inside the framework).
                framework_root = repo_root_from_tooling()

    checks: dict[str, bool] = {}
    findings: list[dict] = []
    warnings: list[str] = []
    errors: list[str] = []
    hints: list[str] = []

    def _fail(check_name: str, severity: str, detail: str) -> None:
        findings.append({"check": check_name, "severity": severity, "detail": detail})
        checks[check_name] = False
        if severity == "critical":
            errors.append(f"{check_name}: {detail}")
        else:
            warnings.append(f"{check_name}: {detail}")

    def _pass(check_name: str) -> None:
        checks.setdefault(check_name, True)
        if checks[check_name] is not False:
            checks[check_name] = True

    # ── Category 1: Baseline Metadata ────────────────────────────────────────

    baseline_data = _read_baseline_yaml(repo_root)
    current_fw_version = _current_baseline_version(framework_root)

    if baseline_data is None:
        _fail(
            "baseline_yaml_present",
            "critical",
            f"{BASELINE_YAML_RELPATH} not found — run: "
            f"bash scripts/init-governance.sh --target {repo_root}",
        )
        hints.append(f"bash scripts/init-governance.sh --target {repo_root}")
        return BaselineDriftResult(
            ok=False,
            severity="critical",
            repo_root=str(repo_root),
            baseline_yaml=None,
            baseline_version=None,
            framework_version=current_fw_version,
            checks=checks,
            findings=findings,
            warnings=warnings,
            errors=errors,
            remediation_hints=hints,
        )
    _pass("baseline_yaml_present")

    baseline_version = baseline_data.get("baseline_version")

    if not baseline_version:
        _fail("baseline_version_known", "warning", "baseline_version field missing from baseline.yaml")
    else:
        _pass("baseline_version_known")
        if current_fw_version:
            cmp = compare_versions(baseline_version, current_fw_version)
            if cmp is None:
                _fail(
                    "framework_version_current",
                    "warning",
                    f"cannot compare baseline {baseline_version} to framework {current_fw_version}",
                )
            elif cmp < 0:
                _fail(
                    "framework_version_current",
                    "warning",
                    f"baseline {baseline_version} is older than framework {current_fw_version} — upgrade recommended",
                )
                hints.append(f"bash scripts/init-governance.sh --target {repo_root} --upgrade")
            else:
                _pass("framework_version_current")

    # source_commit provenance enforcement (12th check)
    source_commit = baseline_data.get("source_commit", "")
    _VALID_COMMIT_RE = __import__("re").compile(r"^[0-9a-f]{7,40}$")
    if not source_commit or source_commit.strip().lower() == "unknown":
        _fail(
            "source_commit_recorded",
            "warning",
            "source_commit is missing or 'unknown' in baseline.yaml — "
            "provenance cannot be traced; re-run init-governance.sh to record",
        )
        hints.append(f"bash scripts/init-governance.sh --target {repo_root}")
    elif not _VALID_COMMIT_RE.match(source_commit.strip()):
        _fail(
            "source_commit_recorded",
            "warning",
            f"source_commit '{source_commit[:20]}' is not a valid git SHA — "
            "baseline provenance may be unreliable",
        )
    else:
        _pass("source_commit_recorded")

    # ── Category 2: Protected File Integrity ─────────────────────────────────

    overridability = {
        k[len("overridable."):]: v
        for k, v in baseline_data.items()
        if k.startswith("overridable.")
    }
    recorded_hashes = {
        k[len("sha256."):]: v
        for k, v in baseline_data.items()
        if k.startswith("sha256.")
    }

    protected_files = [fname for fname, mode in overridability.items() if mode == "protected"]
    all_present = True
    for fname in protected_files:
        fpath = repo_root / fname
        if not fpath.exists():
            _fail("protected_files_present", "critical", f"protected file missing: {fname}")
            all_present = False
    if all_present and protected_files:
        _pass("protected_files_present")

    if not skip_hash and all_present and protected_files:
        all_match = True
        for fname in protected_files:
            fpath = repo_root / fname
            recorded = recorded_hashes.get(fname)
            if not recorded:
                _fail(
                    "protected_files_unmodified",
                    "warning",
                    f"no recorded hash for {fname} — re-run init to record hash",
                )
                all_match = False
                continue
            current_hash = _sha256_file(fpath)
            if current_hash != recorded:
                _fail(
                    "protected_files_unmodified",
                    "critical",
                    f"{fname} has been modified "
                    f"(recorded={recorded[:12]}..., current={current_hash[:12]}...)",
                )
                all_match = False
        if all_match:
            _pass("protected_files_unmodified")

    # Sentinel check for AGENTS.base.md
    agents_path = repo_root / "AGENTS.base.md"
    if agents_path.exists():
        if "governance-baseline: protected" in agents_path.read_text(encoding="utf-8"):
            _pass("protected_file_sentinel_present")
        else:
            _fail(
                "protected_file_sentinel_present",
                "warning",
                "AGENTS.base.md is missing the <!-- governance-baseline: protected --> sentinel",
            )

    # ── Category 3: Overridable File Required Fields ──────────────────────────

    contract_path = repo_root / "contract.yaml"
    if not contract_path.exists():
        _fail("contract_required_fields_present", "critical", "contract.yaml not found")
    else:
        required_contract_fields = _as_list(baseline_data.get("contract_required_fields"))
        if not required_contract_fields:
            required_contract_fields = [
                "name",
                "framework_interface_version",
                "framework_compatible",
                "domain",
            ]
        try:
            contract_data = _parse_contract_yaml(contract_path.read_text(encoding="utf-8"))
            all_fields_ok = True
            for f in required_contract_fields:
                if not contract_data.get(f):
                    _fail(
                        "contract_required_fields_present",
                        "critical",
                        f"contract.yaml missing required field: {f}",
                    )
                    all_fields_ok = False
            if all_fields_ok:
                _pass("contract_required_fields_present")

            # AGENTS.base.md must be referenced in contract
            docs = (
                _as_list(contract_data.get("documents"))
                + _as_list(contract_data.get("ai_behavior_override"))
            )
            if any("AGENTS.base.md" in d for d in docs):
                _pass("contract_agents_base_referenced")
            else:
                _fail(
                    "contract_agents_base_referenced",
                    "warning",
                    "AGENTS.base.md is not listed in contract.yaml documents or ai_behavior_override",
                )

            placeholder_fields = _find_placeholders_in_contract(contract_data)
            if placeholder_fields:
                _fail(
                    "contract_no_placeholders",
                    "warning",
                    "contract.yaml still contains template placeholder values in: "
                    + ", ".join(placeholder_fields)
                    + " — replace <...> tokens with repo-specific values",
                )
            else:
                _pass("contract_no_placeholders")

            # contract_not_framework_copy — warn if contract appears to be the framework's own
            framework_contract_path = framework_root / "contract.yaml"
            if repo_root != framework_root and framework_contract_path.exists():
                try:
                    fw_contract = _parse_contract_yaml(
                        framework_contract_path.read_text(encoding="utf-8")
                    )
                    repo_name = contract_data.get("name", "")
                    fw_name = fw_contract.get("name", "")
                    if repo_name and fw_name and repo_name == fw_name:
                        _fail(
                            "contract_not_framework_copy",
                            "warning",
                            f"contract.yaml 'name' matches the framework's own contract "
                            f"('{repo_name}') — update name and domain to identify this repo",
                        )
                    else:
                        _pass("contract_not_framework_copy")
                except (ValueError, OSError):
                    _pass("contract_not_framework_copy")
            else:
                # Framework validating itself, or framework contract not available — skip
                _pass("contract_not_framework_copy")
        except (ValueError, OSError) as exc:
            _fail("contract_required_fields_present", "critical", f"failed to parse contract.yaml: {exc}")

    # PLAN.md required sections
    # plan_required_sections = governance mandate (only enforced when explicitly set)
    # plan_section_inventory = observed snapshot (informational, not enforced)
    # plan_path may be non-standard (e.g. governance/PLAN.md) — read from baseline
    plan_rel = baseline_data.get("plan_path", "PLAN.md")
    plan_path = repo_root / str(plan_rel)
    required_plan_sections = _as_list(baseline_data.get("plan_required_sections"))
    plan_section_inventory = _as_list(baseline_data.get("plan_section_inventory"))

    if not required_plan_sections:
        # No mandate configured — pass trivially (adopt-existing repos start here)
        _pass("plan_required_sections_present")
    elif plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8")
        all_sections_ok = True
        for section in required_plan_sections:
            if section not in plan_text:
                _fail(
                    "plan_required_sections_present",
                    "warning",
                    f"PLAN.md missing required section: {section}",
                )
                all_sections_ok = False
        if all_sections_ok:
            _pass("plan_required_sections_present")
    else:
        _fail("plan_required_sections_present", "warning", "PLAN.md not found")

    # agents_sections_filled — governance:key sections in AGENTS.md have real content
    agents_md_path = repo_root / "AGENTS.md"
    if agents_md_path.exists():
        empty_sections = _find_empty_governance_sections(
            agents_md_path.read_text(encoding="utf-8")
        )
        if empty_sections:
            _fail(
                "agents_sections_filled",
                "warning",
                "AGENTS.md governance:key sections have no repo-specific content yet: "
                + ", ".join(empty_sections)
                + " — fill in or remove the section if not applicable",
            )
        else:
            _pass("agents_sections_filled")
    else:
        # AGENTS.md is optional (overridable) — skip rather than fail
        _pass("agents_sections_filled")

    # ── Category 4: Freshness ─────────────────────────────────────────────────

    if plan_path.exists():
        _plan_freshness_override_raw = baseline_data.get("plan_freshness_threshold_days")
        _plan_freshness_override: int | None = None
        if _plan_freshness_override_raw is not None:
            try:
                _plan_freshness_override = int(_plan_freshness_override_raw)
            except (TypeError, ValueError):
                warnings.append(
                    "plan_freshness: plan_freshness_threshold_days in baseline.yaml is not a valid integer"
                    f" (got: {_plan_freshness_override_raw!r}) — using PLAN.md policy or framework default"
                )
        # When no CONTRACT override and PLAN.md has no Freshness header, apply
        # the framework default (14d). Pass it as threshold_override so
        # plan_freshness.py uses it instead of its own internal 7d fallback.
        _effective_override = _plan_freshness_override
        # Probe whether PLAN.md has an *explicit* Freshness policy header.
        # check_freshness() always returns a threshold_days (it falls back to 7),
        # so we inspect .policy (the raw header value) to detect presence.
        _probe = check_freshness(plan_path)
        _plan_has_own_policy = (
            _probe.policy is not None
            and _plan_freshness_override is None
        )
        if _effective_override is None and not _plan_has_own_policy:
            _effective_override = FRAMEWORK_DEFAULT_FRESHNESS_DAYS

        freshness = check_freshness(plan_path, threshold_override=_effective_override)

        if _plan_freshness_override is not None:
            _threshold_source = f"contract override: {_plan_freshness_override}d"
            if _plan_freshness_override > FRAMEWORK_DEFAULT_FRESHNESS_DAYS:
                warnings.append(
                    f"plan_freshness: threshold override ({_plan_freshness_override}d) exceeds"
                    f" framework default ({FRAMEWORK_DEFAULT_FRESHNESS_DAYS}d)"
                    " — verify this is an intentional governance policy decision"
                )
        elif _plan_has_own_policy:
            _threshold_source = f"PLAN.md policy: {freshness.threshold_days}d"
        else:
            _threshold_source = f"framework default: {FRAMEWORK_DEFAULT_FRESHNESS_DAYS}d"

        if freshness.status == "FRESH":
            _pass("plan_freshness")
        elif freshness.status == "STALE":
            checks["plan_freshness"] = False
            warnings.append(
                f"plan_freshness: PLAN.md is stale ({freshness.days_since_update} days old,"
                f" threshold {_threshold_source})"
            )
        else:
            _fail(
                "plan_freshness",
                "critical",
                f"PLAN.md freshness check returned {freshness.status} ({_threshold_source})",
            )

    # plan_inventory_current — recorded inventory matches current PLAN.md headings
    # Signals that --refresh-baseline should be run after PLAN.md restructuring.
    if plan_path.exists():
        current_sections = _detect_plan_sections(plan_path.read_text(encoding="utf-8"))
        recorded_sections = plan_section_inventory  # already read above
        if set(current_sections) == set(recorded_sections):
            _pass("plan_inventory_current")
        else:
            added = sorted(set(current_sections) - set(recorded_sections))
            removed = sorted(set(recorded_sections) - set(current_sections))
            parts: list[str] = []
            if added:
                parts.append(f"new: {', '.join(added)}")
            if removed:
                parts.append(f"removed: {', '.join(removed)}")
            _fail(
                "plan_inventory_current",
                "warning",
                "plan_section_inventory is stale — PLAN.md has changed since last refresh"
                + (f" ({'; '.join(parts)})" if parts else "")
                + " — run: bash scripts/init-governance.sh --target "
                + str(repo_root)
                + " --refresh-baseline",
            )
            hints.append(
                f"bash scripts/init-governance.sh --target {repo_root} --refresh-baseline"
            )

    initialized_at_str = baseline_data.get("initialized_at", "")
    if initialized_at_str:
        try:
            initialized_at = datetime.fromisoformat(initialized_at_str.replace("Z", "+00:00"))
            days_since_init = (datetime.now(timezone.utc) - initialized_at).days
            if days_since_init > freshness_threshold_days:
                _fail(
                    "baseline_yaml_freshness",
                    "warning",
                    f"baseline.yaml is {days_since_init} days old (threshold: {freshness_threshold_days}d) "
                    "— re-run drift check and consider upgrading",
                )
                hints.append(
                    f"python governance_tools/governance_drift_checker.py "
                    f"--repo {repo_root} --framework-root {framework_root}"
                )
            else:
                _pass("baseline_yaml_freshness")
        except ValueError:
            _fail("baseline_yaml_freshness", "warning", f"cannot parse initialized_at: {initialized_at_str}")

    # ── Severity Roll-Up ─────────────────────────────────────────────────────

    has_critical = any(f["severity"] == "critical" for f in findings)
    has_warning = any(f["severity"] == "warning" for f in findings)
    severity = "critical" if has_critical else ("warning" if has_warning else "ok")

    return BaselineDriftResult(
        ok=not has_critical,
        severity=severity,
        repo_root=str(repo_root),
        baseline_yaml=str(repo_root / BASELINE_YAML_RELPATH),
        baseline_version=baseline_version,
        framework_version=current_fw_version,
        checks=checks,
        findings=findings,
        warnings=warnings,
        errors=errors,
        remediation_hints=hints,
        plan_section_inventory=plan_section_inventory,
    )


def format_human(result: BaselineDriftResult) -> str:
    lines = [
        "[governance_drift_check]",
        f"ok                 = {result.ok}",
        f"severity           = {result.severity}",
        f"repo_root          = {result.repo_root}",
        f"baseline_version   = {result.baseline_version or '<unknown>'}",
        f"framework_version  = {result.framework_version or '<unknown>'}",
        f"baseline_yaml      = {result.baseline_yaml or '<missing>'}",
        "",
        "[checks]",
    ]
    for key in sorted(result.checks):
        status = "PASS" if result.checks[key] else "FAIL"
        lines.append(f"  {key:<38} {status}")

    if result.plan_section_inventory:
        lines.append("")
        lines.append(f"plan_section_inventory ({len(result.plan_section_inventory)} sections):")
        for s in result.plan_section_inventory:
            lines.append(f"  {s}")

    if result.findings:
        lines.append("")
        lines.append(f"findings ({len(result.findings)}):")
        for item in result.findings:
            lines.append(f"  [{item['severity']}] {item['check']}: {item['detail']}")

    if result.errors:
        lines.append("")
        lines.append(f"errors ({len(result.errors)}):")
        for item in result.errors:
            lines.append(f"  - {item}")

    if result.warnings:
        lines.append("")
        lines.append(f"warnings ({len(result.warnings)}):")
        for item in result.warnings:
            lines.append(f"  - {item}")

    if result.remediation_hints:
        lines.append("")
        lines.append("remediation:")
        for hint in result.remediation_hints:
            lines.append(f"  $ {hint}")

    return "\n".join(lines)


def format_json(result: BaselineDriftResult) -> str:
    d = result.to_dict()
    # Ensure plan_section_inventory is always present in JSON output
    if "plan_section_inventory" not in d:
        d["plan_section_inventory"] = []
    return json.dumps(d, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether a repo's governance files have drifted from the recorded baseline."
    )
    parser.add_argument("--repo", default=".", help="Target repo root (default: .)")
    parser.add_argument("--framework-root", help="Explicit framework root path (default: auto-detect)")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument(
        "--freshness-threshold",
        type=int,
        default=90,
        help="Days before baseline.yaml is considered stale (default: 90)",
    )
    parser.add_argument("--skip-hash", action="store_true", help="Skip SHA256 comparison")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = check_governance_drift(
        repo_root=Path(args.repo),
        framework_root=Path(args.framework_root) if args.framework_root else None,
        freshness_threshold_days=args.freshness_threshold,
        skip_hash=args.skip_hash,
    )
    if args.format == "json":
        print(format_json(result))
    else:
        print(format_human(result))
    # Exit codes: 0=ok, 1=warning, 2=critical
    if result.severity == "critical":
        return 2
    if result.severity == "warning":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
