#!/usr/bin/env python3
"""
Runtime ledger milestone export (Option B follow-up).

Creates a bounded, reviewable snapshot of the ignored runtime ledgers at a
specific commit/time, so durable audit evidence does not depend on the live
ledger files being tracked.

Spec: artifacts/governance/runtime-ledger-milestone-export-design-2026-06-18.md
Manifest-only mode is the default; raw ndjson snapshots are opt-in (--include-raw).

CLAIM CEILING: an export bundle captures local ledger state at a commit/time
with presence, hashes, and counts recorded. It does NOT prove historical
completeness, per-session receipt validity, semantic correctness, or that the
ignored live ledgers are themselves durable evidence. It opens no gate and adds
no CI/hook/closeout behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TOOL_NAME = "runtime_ledger_export"
GENERATED_BY = "governance_tools.runtime_ledger_export"

# The two Option-B-ignored runtime ledgers this exporter snapshots.
LEDGER_SOURCES = (
    "artifacts/claim-enforcement/claim-enforcement-receipts.ndjson",
    "artifacts/session-index.ndjson",
)

EXPORT_ROOT = "artifacts/governance/runtime-ledger-exports"

CLAIM_CEILING_SUPPORTED = [
    "this bundle captures local runtime ledger state at a specific commit and time",
    "source presence, sha256 hashes, line/record counts, and inclusion status are recorded",
    "reviewer/audit can inspect the exported bundle without tracking the live ignored ledgers",
]
CLAIM_CEILING_NOT_SUPPORTED = [
    "full historical runtime evidence is complete",
    "every session has a valid receipt",
    "the ignored live ledgers are themselves durable reviewer evidence",
    "runtime ledger schema is validated beyond exporter presence/parse checks",
    "semantic correctness of claims is proven",
    "Gate 3 is opened",
    "any new CI, hook, closeout, or enforcement behavior exists",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(project_root: Path, args: list[str]) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=project_root, capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip()
    except Exception:
        return ""


def _inspect_source(path: Path) -> dict:
    """Presence, hash, counts, and parse failures for one ledger. Never raises."""
    if not path.is_file():
        return {
            "present": False,
            "sha256": None,
            "line_count": None,
            "record_count": None,
            "parse_failures": [],
        }
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {
            "present": True,
            "sha256": None,
            "line_count": None,
            "record_count": None,
            "parse_failures": [f"unreadable: {exc}"],
        }
    sha = hashlib.sha256(raw).hexdigest()
    # BOM-safe decode; lesson from the advisory exit-1 defect.
    text = raw.decode("utf-8-sig", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    record_count = 0
    parse_failures: list[str] = []
    for idx, ln in enumerate(lines, start=1):
        try:
            json.loads(ln)
            record_count += 1
        except json.JSONDecodeError as exc:
            parse_failures.append(f"line {idx}: {exc.msg}")
    return {
        "present": True,
        "sha256": sha,
        "line_count": len(lines),
        "record_count": record_count,
        "parse_failures": parse_failures,
    }


def build_manifest(
    *,
    project_root: Path,
    export_id: str,
    export_reason: str,
    reviewer_scope: str,
    include_raw: bool,
) -> tuple[dict, list[str]]:
    """Return (manifest, warnings). Pure: writes nothing."""
    warnings: list[str] = []
    source_present: dict[str, bool] = {}
    source_sha256: dict[str, str | None] = {}
    source_line_count: dict[str, int | None] = {}
    source_record_count: dict[str, int | None] = {}

    for rel in LEDGER_SOURCES:
        info = _inspect_source(project_root / rel)
        source_present[rel] = info["present"]
        source_sha256[rel] = info["sha256"]
        source_line_count[rel] = info["line_count"]
        source_record_count[rel] = info["record_count"]
        if not info["present"]:
            warnings.append(f"source absent: {rel} (source_present=false; not fabricated)")
        for pf in info["parse_failures"]:
            label = "unreadable source" if pf.startswith("unreadable") else "parse failure"
            warnings.append(f"{label} in {rel}: {pf}")

    manifest = {
        "export_id": export_id,
        "created_at_utc": _utc_now(),
        "repo_head": _git(project_root, ["rev-parse", "HEAD"]) or "UNKNOWN",
        "repo_branch": _git(project_root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "UNKNOWN",
        "export_reason": export_reason,
        "reviewer_scope": reviewer_scope,
        "source_files": list(LEDGER_SOURCES),
        "source_present": source_present,
        "source_sha256": source_sha256,
        "source_line_count": source_line_count,
        "source_record_count": source_record_count,
        "included_raw_snapshots": bool(include_raw),
        "claim_ceiling_supported": CLAIM_CEILING_SUPPORTED,
        "claim_ceiling_not_supported": CLAIM_CEILING_NOT_SUPPORTED,
        "generated_by": GENERATED_BY,
    }
    return manifest, warnings


def render_summary(manifest: dict, warnings: list[str]) -> str:
    present = manifest["source_present"]
    lines = [
        f"# Runtime Ledger Milestone Export {manifest['export_id']}",
        "",
        f"- created_at_utc: {manifest['created_at_utc']}",
        f"- repo_head: {manifest['repo_head']}",
        f"- repo_branch: {manifest['repo_branch']}",
        f"- export_reason: {manifest['export_reason']}",
        f"- reviewer_scope: {manifest['reviewer_scope']}",
        f"- included_raw_snapshots: {manifest['included_raw_snapshots']}",
        "",
        "## Source ledgers",
    ]
    for rel in manifest["source_files"]:
        state = "present" if present.get(rel) else "ABSENT"
        rc = manifest["source_record_count"].get(rel)
        lines.append(f"- {rel}: {state}" + (f" ({rc} records)" if rc is not None else ""))
    lines += ["", "## Can support", *[f"- {c}" for c in manifest["claim_ceiling_supported"]]]
    lines += ["", "## Cannot support", *[f"- {c}" for c in manifest["claim_ceiling_not_supported"]]]
    if warnings:
        lines += ["", "## Warnings", *[f"- {w}" for w in warnings]]
    return "\n".join(lines) + "\n"


def run_export(
    *,
    project_root: Path,
    export_id: str,
    export_reason: str,
    reviewer_scope: str,
    include_raw: bool,
) -> tuple[Path, dict, list[str]]:
    manifest, warnings = build_manifest(
        project_root=project_root,
        export_id=export_id,
        export_reason=export_reason,
        reviewer_scope=reviewer_scope,
        include_raw=include_raw,
    )
    export_dir = project_root / EXPORT_ROOT / export_id
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (export_dir / "summary.md").write_text(render_summary(manifest, warnings), encoding="utf-8")
    if include_raw:
        for rel in LEDGER_SOURCES:
            src = project_root / rel
            if src.is_file():
                (export_dir / Path(rel).name).write_text(
                    src.read_text(encoding="utf-8-sig", errors="replace"), encoding="utf-8"
                )
    return export_dir, manifest, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a milestone snapshot of the ignored runtime ledgers."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--export-id", default=None, help="Default: timestamp-based.")
    parser.add_argument("--reason", default="unspecified", help="export_reason")
    parser.add_argument("--reviewer-scope", default="unspecified")
    parser.add_argument("--include-raw", action="store_true", help="Include raw ndjson snapshots.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any source ledger is absent or malformed.",
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    export_id = args.export_id or f"export-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    export_dir, manifest, warnings = run_export(
        project_root=project_root,
        export_id=export_id,
        export_reason=args.reason,
        reviewer_scope=args.reviewer_scope,
        include_raw=args.include_raw,
    )

    # Structured strict detection from manifest fields (NOT substring-matching
    # warning text — that would be a fragile lexical tripwire). Covers three
    # problem classes explicitly: absent, unreadable (present but no hash),
    # malformed (fewer valid records than non-empty lines).
    files = manifest["source_files"]
    present = manifest["source_present"]
    sha = manifest["source_sha256"]
    lc = manifest["source_line_count"]
    rc = manifest["source_record_count"]
    any_absent = not all(present.values())
    any_unreadable = any(present[f] and sha[f] is None for f in files)
    any_malformed = any(
        lc[f] is not None and rc[f] is not None and rc[f] < lc[f] for f in files
    )
    strict_fail = args.strict and (any_absent or any_unreadable or any_malformed)

    if args.format == "json":
        print(json.dumps({
            "tool": TOOL_NAME,
            "ok": not strict_fail,
            "export_id": export_id,
            "export_dir": str(export_dir),
            "warnings": warnings,
            "strict": args.strict,
        }, indent=2))
    else:
        print(f"[{TOOL_NAME}]")
        print(f"export_id={export_id}")
        print(f"export_dir={export_dir}")
        for rel in manifest["source_files"]:
            print(f"source={rel} present={manifest['source_present'][rel]} "
                  f"records={manifest['source_record_count'][rel]}")
        for w in warnings:
            print(f"warning={w}")
        print(f"ok={not strict_fail}")

    # Ordinary missing/malformed ledgers do NOT fail (design: advisory by default).
    # Only --strict converts them to a non-zero exit.
    return 1 if strict_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
