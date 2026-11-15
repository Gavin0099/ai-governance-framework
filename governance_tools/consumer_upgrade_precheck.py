"""Predict consumer instruction rewrites and trim only proven framework text.

Prediction replays the real writers in an isolated temporary checkout. It never
installs hooks, fetches, or writes to the consumer or source framework. Slimming
is a separate, opt-in AGENTS.md edit; headings/markers alone do not prove ownership.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from governance_tools import external_governance_submodule_updater as updater
from governance_tools import hook_installer as installer
from governance_tools.instruction_context_budget import measure_codex_project_doc


UPDATE_HEADING = "## AI Governance Update Intent Rule"
ROUTER_HEADING = "## AI Governance Memory Workflow Router"
F7_MARKER = "<!-- governance:key=f7_update_boundary -->"
SOURCE_PATHS = (
    "baselines/repo-min/AGENTS.md",
    "baselines/repo-min/AGENTS.base.md",
    "governance/agent-contract-template.md",
)
HISTORY_PATHS = (SOURCE_PATHS[0], SOURCE_PATHS[2], "governance_tools/f7_full_update.py")


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", f"safe.directory={root.resolve().as_posix()}",
         "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def _budget(payload: bytes) -> dict[str, Any]:
    report = measure_codex_project_doc(payload)
    return {**report, "headroom_bytes": max(0, int(report["budget_bytes"]) - len(payload))}


def _snapshot_framework(source: Path, dest: Path, target_ref: str | None) -> str:
    """A detached, read-only-object view; all metadata created here is temporary.

    Protected BASE synchronization verifies HEAD and its source blob even in a
    replay. Object alternates let it do that without fetching, copying history,
    checking out the real framework, or bypassing its source-binding check.
    """
    revision = _git(source, "rev-parse", "--verify", "--end-of-options",
                    f"{target_ref or 'HEAD'}^{{commit}}").decode().strip()
    objects = Path(_git(source, "rev-parse", "--git-path", "objects").decode().strip())
    if not objects.is_absolute():
        objects = source / objects
    git_dir = dest / ".git"
    (git_dir / "objects/info").mkdir(parents=True)
    (git_dir / "refs").mkdir()
    (git_dir / "HEAD").write_bytes((revision + "\n").encode("ascii"))
    (git_dir / "config").write_bytes(b"[core]\nrepositoryformatversion = 0\nbare = false\n")
    (git_dir / "objects/info/alternates").write_bytes((objects.resolve().as_posix() + "\n").encode("utf-8"))
    for relative in SOURCE_PATHS:
        try:
            data = _git(source, "cat-file", "blob", f"{revision}:{relative}")
        except ValueError:
            continue  # An older target may legitimately lack an additive template.
        path = dest / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return revision


def predict_instruction_upgrade(
    repo_root: Path, framework_root: Path, *, repo_role: str = "submodule_consumer",
    target_ref: str | None = None, scratch_dir: Path | None = None,
) -> dict[str, Any]:
    """Measure the bytes the real AGENTS writers would produce, without repo writes.

    This is conditional on the existing update/ownership gates allowing apply;
    it is not a readiness result. Missing target objects never imply a fit.
    """
    report: dict[str, Any] = {
        "status": "not_verified", "report_only": True, "path": "AGENTS.md",
        "repo_role": repo_role, "current": None, "predicted": None,
        "target_ref": target_ref, "source_root": str(framework_root.resolve()), "errors": [],
        "claim_boundary": "instruction rewrite prediction only; existing apply gates still decide whether an update may run",
    }
    try:
        agents = repo_root / "AGENTS.md"
        current = agents.read_bytes() if agents.is_file() else None
        if current is not None:
            current.decode("utf-8")  # Match the real writers' strict decoding.
            report["current"] = _budget(current)
        if repo_role not in {"submodule_consumer", "external_contract_repo"}:
            raise ValueError(f"no instruction rewrite backend for repo role: {repo_role}")
        temp_root = (scratch_dir if scratch_dir is not None else Path(tempfile.gettempdir())).resolve()
        if any(temp_root.is_relative_to(root.resolve()) for root in (repo_root, framework_root)):
            raise ValueError("prediction scratch directory must be outside the consumer and source framework")
        # No consumer files other than AGENTS.md are needed to render instructions.
        # A new temporary BASE is intentional: the real consumer's protected-file
        # and dirty-tree gates are not evaluated or claimed by this byte prediction.
        with tempfile.TemporaryDirectory(prefix="f7-precheck-", dir=temp_root) as temp:
            scratch = Path(temp)
            consumer = scratch / "consumer"
            consumer.mkdir()
            if current is not None:
                (consumer / "AGENTS.md").write_bytes(current)
            source = framework_root
            revision = None
            if repo_role == "submodule_consumer" or target_ref:
                source = scratch / "framework"
                revision = _snapshot_framework(framework_root, source, target_ref)
            report["source_revision"] = revision
            if repo_role == "submodule_consumer":
                refreshed = updater._refresh_repo_local_instructions(
                    consumer, source, framework_commit=revision,
                )
                report["errors"].extend(refreshed["errors"])
            installed: list[str] = []
            installer._apply_agent_contract_surfaces(
                consumer, source, installed=installed, changed=[], backups=[], errors=report["errors"],
            )
            if repo_role == "external_contract_repo":
                # Lazy import avoids a cycle with F-7's preflight wrapper.
                from governance_tools.f7_full_update import _ensure_agents_keyed_sections

                _status, _changed, errors = _ensure_agents_keyed_sections(consumer)
                report["errors"].extend(errors)
            predicted = _budget((consumer / "AGENTS.md").read_bytes())
        report["predicted"] = predicted
        if not report["errors"]:
            report["drift_check_will_fail"] = bool(predicted["over_budget"])
        report["status"] = (
            "not_verified" if report["errors"] else "over_budget" if predicted["over_budget"]
            else "warning" if predicted["over_budget_with_crlf"] else "fits"
        )
    except (OSError, ValueError, UnicodeError) as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    return report


def format_prediction(report: dict[str, Any]) -> list[str]:
    lines = ["[instruction_budget_precheck]"]
    current = report.get("current")
    predicted = report.get("predicted")
    lines.append(f"AGENTS.md current bytes: {current['on_disk_bytes'] if current else 'missing or unreadable'}")
    if predicted:
        lines.append(
            f"Predicted post-upgrade bytes: {predicted['on_disk_bytes']}; limit: {predicted['budget_bytes']}; "
            f"headroom: {predicted['headroom_bytes']}; overflow: {predicted['overflow_bytes']}."
        )
        lines.append(
            f"CRLF worst case: {predicted['crlf_worst_case_bytes']} bytes; "
            f"overflow: {predicted['crlf_worst_case_overflow_bytes']}."
        )
        if report.get("errors"):
            lines.append("These are candidate rewrite bytes; the rewrite did not complete successfully.")
            if predicted["over_budget"]:
                lines.append("The consumer drift check will fail after upgrade if these candidate bytes are written.")
        elif predicted["over_budget"]:
            lines.append("The consumer drift check will fail after upgrade: AGENTS.md exceeds the byte limit.")
        else:
            lines.append("The predicted AGENTS.md fits the on-disk byte limit.")
    if report.get("errors"):
        lines.append("Prediction is not verified; do not infer upgrade compatibility.")
        lines.extend(report["errors"])
    lines.append(str(report.get("claim_boundary", "")))
    return lines


def _normalized(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n").strip(b"\n")


def _section_content(section: Section) -> bytes:
    content = _normalized(section.payload)
    if section.family == "memory_workflow" and content.startswith(ROUTER_HEADING.encode() + b"\n"):
        content = content.split(b"\n", 1)[1].lstrip(b"\n")
    return content


@dataclass
class Section:
    family: str
    start: int
    end: int
    payload: bytes


def _sections(payload: bytes, *, include_nested: bool = False) -> tuple[list[Section], list[str]]:
    """Locate bounded regions, ignoring fenced examples and nested block content."""
    text = payload.decode("utf-8")
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    visible: list[bool] = []
    offset = 0
    fence = ""
    for line in lines:
        offsets.append(offset)
        offset += len(line.encode("utf-8"))
        stripped = line.lstrip("\ufeff").strip()
        marker = re.match(r"^(`{3,}|~{3,})", stripped)
        visible.append(not fence and marker is None)
        if marker:
            token = marker.group(1)
            if not fence:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = ""
    offsets.append(len(payload))
    sections: list[Section] = []
    errors: list[str] = []
    paired: list[tuple[str, int]] = []
    occupied: set[int] = set()
    for i, line in enumerate(lines):
        if not visible[i]:
            continue
        stripped = line.lstrip("\ufeff").strip()
        begin = re.fullmatch(r"<!-- (AI Governance Framework: agent-contract|ai-governance:[\w-]+) BEGIN(?: .*?)? -->", stripped)
        end = re.fullmatch(r"<!-- (AI Governance Framework: agent-contract|ai-governance:[\w-]+) END -->", stripped)
        if begin:
            paired.append((begin.group(1), i))
        elif end:
            if not paired or paired[-1][0] != end.group(1):
                errors.append(f"unmatched managed END marker at line {i + 1}")
                continue
            family, first = paired.pop()
            if not paired or include_nested:
                start = offsets[first] + (3 if lines[first].startswith("\ufeff") else 0)
                sections.append(Section(family, start, offsets[i + 1], payload[start:offsets[i + 1]]))
            if not paired:
                occupied.update(range(first, i + 1))
    if paired:
        errors.append("unmatched managed BEGIN marker; ownership boundary is uncertain")
    for i, line in enumerate(lines):
        if not visible[i] or i in occupied:
            continue
        stripped = line.lstrip("\ufeff").rstrip("\r\n")
        if stripped in {ROUTER_HEADING, updater.MEMORY_WORKFLOW_MARKER}:
            family = "memory_workflow"
            end = i + 1
            has_marker = stripped == updater.MEMORY_WORKFLOW_MARKER
            while end < len(lines):
                part = lines[end].strip()
                if part == updater.MEMORY_WORKFLOW_MARKER:
                    if has_marker:
                        break
                    has_marker = True
                if part and part != updater.MEMORY_WORKFLOW_MARKER and not part.startswith("- "):
                    break
                end += 1
            occupied.update(range(i + 1, end))
        elif stripped == UPDATE_HEADING:
            end = i + 1
            while end < len(lines) and not (visible[end] and lines[end].startswith("## ")):
                if end in occupied:
                    break
                end += 1
            family = "update_intent"
        elif stripped == F7_MARKER:
            family = "f7_update_boundary"
            end = i + 1
            while end < len(lines) and lines[end].startswith("- "):
                end += 1
        else:
            continue
        start = offsets[i] + (3 if line.startswith("\ufeff") else 0)
        sections.append(Section(family, start, offsets[end], payload[start:offsets[end]]))
    return sorted(sections, key=lambda section: section.start), errors


def _boundary_from_source(payload: bytes) -> bytes | None:
    """Read historical string constants without executing historical Python."""
    values: dict[str, str] = {}

    def evaluate(node: ast.AST) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.JoinedStr):
            return "".join(evaluate(part.value) if isinstance(part, ast.FormattedValue) else evaluate(part)
                           for part in node.values)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return evaluate(node.left) + evaluate(node.right)
        raise ValueError("not a string constant")

    try:
        tree = ast.parse(payload.decode("utf-8-sig"))
    except (SyntaxError, UnicodeError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = evaluate(node.value)
            except (ValueError, KeyError):
                continue
    value = values.get("F7_UPDATE_BOUNDARY_BLOCK")
    return value.encode("utf-8") if value else None


@dataclass
class ManagedCatalog:
    known: dict[str, set[bytes]] = field(default_factory=dict)
    replacements: dict[str, bytes] = field(default_factory=dict)

    def add(self, payload: bytes, *, current: bool = False) -> None:
        sections, _errors = _sections(payload, include_nested=True)
        for section in sections:
            self.known.setdefault(section.family, set()).add(_section_content(section))
            if current and section.family in {"update_intent", "f7_update_boundary"}:
                self.replacements[section.family] = _normalized(section.payload)


def load_managed_catalog(framework_root: Path) -> ManagedCatalog:
    """Only exact current or locally recorded framework text establishes ownership."""
    catalog = ManagedCatalog()
    # This process's external-contract writer emits a headingless router.
    # Share that exact constant rather than maintaining a second copy of it.
    from governance_tools.f7_full_update import F7_MEMORY_WORKFLOW_BLOCK

    catalog.add(F7_MEMORY_WORKFLOW_BLOCK.encode("utf-8"))
    seen: set[bytes] = set()
    for relative in HISTORY_PATHS:
        path = framework_root / relative
        if path.is_file():
            payload = path.read_bytes()
            if relative.endswith(".py"):
                payload = _boundary_from_source(payload) or b""
            catalog.add(payload, current=True)
            seen.add(payload)
        try:
            commits = _git(framework_root, "log", "--format=%H", "--", relative).decode().splitlines()
        except ValueError:
            commits = []
        for commit in commits:
            try:
                payload = _git(framework_root, "cat-file", "blob", f"{commit}:{relative}")
            except ValueError:
                continue
            if relative.endswith(".py"):
                payload = _boundary_from_source(payload) or b""
            if payload not in seen:
                catalog.add(payload)
                seen.add(payload)
    return catalog


def plan_slimming(payload: bytes, catalog: ManagedCatalog) -> tuple[dict[str, Any], bytes]:
    """Splice known managed regions; every byte outside them is copied unchanged."""
    report: dict[str, Any] = {
        "status": "unchanged", "current": _budget(payload), "after": _budget(payload),
        "sections": [], "errors": [], "changed_files": [],
    }
    try:
        sections, errors = _sections(payload)
    except UnicodeError as exc:
        report.update(status="refused", errors=[f"invalid UTF-8: {exc}"])
        return report, payload
    report["errors"].extend(errors)
    groups: dict[str, list[Section]] = {}
    for section in sections:
        groups.setdefault(section.family, []).append(section)
    edits: list[tuple[Section, bytes]] = []
    for family, copies in groups.items():
        unknown = [s for s in copies if _section_content(s) not in catalog.known.get(family, set())]
        # A unique unrecognized paired block is left alone. An Update Intent or
        # boundary candidate, or any duplicate, must prove ownership before edits.
        relevant = family in {"update_intent", "f7_update_boundary"} or len(copies) > 1
        if not relevant:
            continue
        if unknown:
            report["errors"].append(f"{family}: text is not an exact known framework section; ownership is uncertain")
        elif family not in catalog.replacements and len({_section_content(s) for s in copies}) > 1:
            report["errors"].append(f"{family}: managed copies differ; manual ownership review required")
        for number, section in enumerate(copies, 1):
            replacement = section.payload
            action = "keep"
            if unknown:
                action = "refuse"
            elif number > 1:
                replacement, action = b"", "remove_duplicate"
            elif family in catalog.replacements:
                new = catalog.replacements[family]
                newline = b"\r\n" if b"\r\n" in section.payload else b"\n"
                # Retain the original separator (and its exact line endings).
                suffix = section.payload[len(section.payload.rstrip(b"\r\n")):]
                candidate = new.replace(b"\n", newline) + suffix
                if len(candidate) < len(section.payload):
                    replacement, action = candidate, "replace_with_current_pointer"
            report["sections"].append({
                "section": family, "occurrence": number, "action": action,
                "before_bytes": len(section.payload), "after_bytes": len(replacement),
            })
            edits.append((section, replacement))
    if report["errors"]:
        report["status"] = "refused"
        return report, payload  # Refusal is all-or-nothing, including otherwise safe edits.
    after = bytearray()
    untouched = bytearray()
    position = 0
    for section, replacement in sorted(edits, key=lambda item: item[0].start):
        if section.start < position:
            report.update(status="refused", errors=["overlapping managed sections; ownership is uncertain"])
            return report, payload
        after.extend(payload[position:section.start])
        untouched.extend(payload[position:section.start])
        after.extend(replacement)
        position = section.end
    after.extend(payload[position:])
    untouched.extend(payload[position:])
    result = bytes(after)
    report.update(
        status="would_change" if result != payload else "unchanged", after=_budget(result),
        preserved_unmanaged_bytes=len(untouched),
        preserved_unmanaged_sha256=hashlib.sha256(untouched).hexdigest(),
    )
    return report, result


def slim_agents(
    repo_root: Path, framework_root: Path, *, apply: bool = False,
    catalog: ManagedCatalog | None = None,
) -> dict[str, Any]:
    path = repo_root / "AGENTS.md"
    try:
        if path.is_symlink() or path.stat().st_nlink > 1:
            raise ValueError("AGENTS.md is a link; refusing an indirect write")
        before = path.read_bytes()
        report, after = plan_slimming(before, catalog if catalog is not None else load_managed_catalog(framework_root))
        report["mode"] = "apply" if apply else "dry_run"
        if apply and report["status"] == "would_change":
            if path.read_bytes() != before:
                raise ValueError("AGENTS.md changed during analysis; rerun the dry-run")
            temporary = None
            try:
                # Publish one complete file, so an interrupted/failed write never
                # truncates the consumer's instructions. No other output remains.
                with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".AGENTS-", suffix=".tmp", delete=False) as output:
                    temporary = Path(output.name)
                    output.write(after)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
                if path.is_symlink() or path.stat().st_nlink > 1 or path.read_bytes() != before:
                    raise ValueError("AGENTS.md changed during analysis; rerun the dry-run")
                os.replace(temporary, path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            report.update(status="applied", changed_files=["AGENTS.md"])
        return report
    except (OSError, ValueError) as exc:
        return {"status": "refused", "mode": "apply" if apply else "dry_run",
                "errors": [f"{type(exc).__name__}: {exc}"], "sections": [], "changed_files": []}


def format_slimming(report: dict[str, Any]) -> list[str]:
    lines = [f"Slimming: {report['status']}",
             "| Framework section | Copy | Before bytes | After bytes | Action |",
             "| --- | ---: | ---: | ---: | --- |"]
    for row in report["sections"]:
        lines.append(f"| {row['section']} | {row['occurrence']} | {row['before_bytes']} | {row['after_bytes']} | {row['action']} |")
    if report.get("after"):
        lines.append(f"Remaining overflow: {report['after']['overflow_bytes']} bytes.")
    lines.extend(report["errors"])
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("predict", "slim"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--framework-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repo-role", choices=("submodule_consumer", "external_contract_repo"), default="submodule_consumer")
    parser.add_argument("--target-ref")
    parser.add_argument("--scratch-dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="Explicitly apply only the slimming edits to AGENTS.md.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)
    if args.command == "predict":
        if args.apply:
            parser.error("predict is read-only; --apply is only valid with slim")
        report = predict_instruction_upgrade(args.repo, args.framework_root, repo_role=args.repo_role,
                                             target_ref=args.target_ref, scratch_dir=args.scratch_dir)
        lines = format_prediction(report)
    else:
        if args.target_ref:
            parser.error("slim proves ownership against --framework-root and its local history, not --target-ref")
        report = slim_agents(args.repo, args.framework_root, apply=args.apply)
        lines = format_slimming(report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else "\n".join(lines))
    # An overflow is a report, never a dry-run gate.
    return 1 if report["status"] in {"refused", "not_verified"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
