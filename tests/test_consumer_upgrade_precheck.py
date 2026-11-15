from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from governance_tools import consumer_upgrade_precheck as precheck
from governance_tools import external_governance_submodule_updater as updater
from governance_tools import f7_full_update as f7
from governance_tools import hook_installer as installer


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root.resolve().as_posix()}", "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return result.stdout.decode("utf-8").strip()


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


@pytest.fixture
def framework(tmp_path: Path) -> Path:
    root = tmp_path / "f"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "core.autocrlf", "false")
    _write(root / precheck.SOURCE_PATHS[1], b"# Framework base\n")
    _write(root / precheck.SOURCE_PATHS[0],
           ("# Framework instructions\n\n" + precheck.UPDATE_HEADING + "\n\n"
            "- Read the update protocol.\n\n" + updater._memory_workflow_router_section()
            + "\n## Repo-Specific Risk Levels\n\n- Consumer rule.\n").encode("utf-8"))
    _write(root / precheck.SOURCE_PATHS[2],
           (installer.AGENT_CONTRACT_BLOCK_BEGIN + "\n- Read the canonical contract.\n"
            + installer.AGENT_CONTRACT_BLOCK_END + "\n").encode("utf-8"))
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fixture")
    return root


@pytest.mark.parametrize("role", ["submodule_consumer", "external_contract_repo"])
@pytest.mark.parametrize("newline,bom", [(b"\n", b""), (b"\r\n", b""), (b"\n", b"\xef\xbb\xbf"), (b"\r\n", b"\xef\xbb\xbf")])
def test_prediction_matches_real_instruction_writes(tmp_path: Path, framework: Path, role: str, newline: bytes, bom: bytes) -> None:
    repo = tmp_path / "c"
    repo.mkdir()
    payload = bom + (
        "# Consumer\n\n" + precheck.UPDATE_HEADING + "\n\n- Obsolete instructions.\n\n"
        "## Repo-Specific Risk Levels\n\n- HIGH: keep this rule.\n\n"
        "## Must-Test Paths\n- Keep exact consumer text.\n"
    ).encode().replace(b"\n", newline)
    (repo / "AGENTS.md").write_bytes(payload)
    prediction = precheck.predict_instruction_upgrade(repo, framework, repo_role=role, scratch_dir=tmp_path)
    assert not prediction["errors"]
    assert (repo / "AGENTS.md").read_bytes() == payload
    if role == "submodule_consumer":
        refreshed = updater._refresh_repo_local_instructions(repo, framework, framework_commit=_git(framework, "rev-parse", "HEAD"))
        assert not refreshed["errors"]
    errors: list[str] = []
    installer._apply_agent_contract_surfaces(repo, framework, installed=[], changed=[], backups=[], errors=errors)
    assert not errors
    if role == "external_contract_repo":
        assert not f7._ensure_agents_keyed_sections(repo)[2]
    actual = (repo / "AGENTS.md").read_bytes()
    assert prediction["predicted"]["on_disk_bytes"] == len(actual)
    assert prediction["predicted"]["crlf_worst_case_bytes"] == len(actual.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert prediction["current"]["on_disk_bytes"] == len(payload)
    assert prediction["source_revision"] == (_git(framework, "rev-parse", "HEAD") if role == "submodule_consumer" else None)


def test_prediction_reads_target_tree_without_checkout_or_source_writes(tmp_path: Path, framework: Path) -> None:
    old = _git(framework, "rev-parse", "HEAD")
    _write(framework / precheck.SOURCE_PATHS[0], (precheck.UPDATE_HEADING + "\n- New pointer.\n\n## Repo-Specific Risk Levels\n").encode())
    _git(framework, "commit", "-am", "target")
    target = _git(framework, "rev-parse", "HEAD")
    _git(framework, "checkout", old)
    repo = tmp_path / "c"
    repo.mkdir()
    _write(repo / "AGENTS.md", b"# Consumer\n")
    before = {p.relative_to(framework): hashlib.sha256(p.read_bytes()).hexdigest() for p in framework.rglob("*") if p.is_file()}
    report = precheck.predict_instruction_upgrade(repo, framework, target_ref=target, scratch_dir=tmp_path)
    assert not report["errors"]
    assert report["source_revision"] == target
    assert before == {p.relative_to(framework): hashlib.sha256(p.read_bytes()).hexdigest() for p in framework.rglob("*") if p.is_file()}
    assert _git(framework, "rev-parse", "HEAD") == old


def test_prediction_missing_target_never_claims_fit(tmp_path: Path, framework: Path) -> None:
    _write(tmp_path / "c/AGENTS.md", b"# Consumer\n")
    report = precheck.predict_instruction_upgrade(tmp_path / "c", framework, target_ref="missing", scratch_dir=tmp_path)
    assert report["status"] == "not_verified"
    assert report["predicted"] is None
    assert "fits" not in "\n".join(precheck.format_prediction(report))


def test_prediction_format_reports_candidate_overflow_without_claiming_success() -> None:
    report = {"current": precheck._budget(b"x" * 34000), "predicted": precheck._budget(b"x" * 33000),
              "status": "not_verified", "errors": ["instruction refresh failed"]}
    text = "\n".join(precheck.format_prediction(report))
    assert "drift check will fail after upgrade if these candidate bytes are written" in text
    assert "not verified" in text
    assert "fits" not in text


def test_prediction_refuses_scratch_inside_consumer_without_writes(tmp_path: Path, framework: Path) -> None:
    repo = tmp_path / "c"
    _write(repo / "AGENTS.md", b"# Consumer\n")
    report = precheck.predict_instruction_upgrade(repo, framework, scratch_dir=repo)
    assert report["status"] == "not_verified"
    assert report["predicted"] is None
    assert list(repo.iterdir()) == [repo / "AGENTS.md"]


@pytest.mark.parametrize("size", [32767, 32768, 32769])
def test_prediction_limit_is_raw_bytes_and_overflow_does_not_block_dry_run(tmp_path: Path, size: int) -> None:
    root = tmp_path / "f"
    root.mkdir()
    repo = tmp_path / "c"
    repo.mkdir()
    # Characterize the full real external rewrite first, then independently pad
    # its fixed suffix to the specified raw-byte limit.
    (repo / "AGENTS.md").write_bytes(b"x\n")
    first = precheck.predict_instruction_upgrade(repo, root, repo_role="external_contract_repo", scratch_dir=tmp_path)
    (repo / "AGENTS.md").write_bytes(b"x" * (size - first["predicted"]["on_disk_bytes"] + 1) + b"\n")
    report = precheck.predict_instruction_upgrade(repo, root, repo_role="external_contract_repo", scratch_dir=tmp_path)
    assert report["predicted"]["on_disk_bytes"] == size
    assert report["predicted"]["overflow_bytes"] == max(0, size - 32768)
    assert report["drift_check_will_fail"] is (size > 32768)
    if size > 32768:
        assert "drift check will fail after upgrade" in "\n".join(precheck.format_prediction(report))


def _catalog() -> precheck.ManagedCatalog:
    catalog = precheck.ManagedCatalog()
    catalog.add((precheck.UPDATE_HEADING + "\n\n- Old managed text.\n\n").encode())
    catalog.add((precheck.UPDATE_HEADING + "\n\n- Protocol.\n\n").encode(), current=True)
    catalog.add(f7.F7_UPDATE_BOUNDARY_BLOCK.encode(), current=True)
    catalog.add(updater._memory_workflow_router_section().encode())
    catalog.add((installer.AGENT_CONTRACT_BLOCK_BEGIN + "\n- Canonical instruction.\n"
                 + installer.AGENT_CONTRACT_BLOCK_END + "\n").encode())
    return catalog


@pytest.mark.parametrize("newline,bom", [(b"\n", b""), (b"\r\n", b""), (b"\n", b"\xef\xbb\xbf"), (b"\r\n", b"\xef\xbb\xbf")])
def test_slimming_preserves_every_consumer_byte_and_is_idempotent(newline: bytes, bom: bytes) -> None:
    managed = (precheck.UPDATE_HEADING + "\n\n- Old managed text.\n\n").encode().replace(b"\n", newline)
    first = b"# Consumer  \n\n"  # Deliberately mixed newline styles and trailing spaces.
    middle = ("## Repo-Specific Risk Levels\r\n<!-- governance:key=risk_levels -->\r\n- HIGH: 保留  \r\n\r\n"
              "## Must-Test Paths\n<!-- governance:key=must_test_paths -->\n- tests/check.py\n\n"
              "## L1 -> L2 Escalation Triggers\r\n<!-- governance:key=escalation_triggers -->\r\n- Review.\r\n\r\n"
              "## Repo-Specific Forbidden Behaviors\n<!-- governance:key=forbidden_behaviors -->\n- Keep.\n\n").encode()
    last = b"## Custom\r\n\r\n- No final newline  "
    payload = bom + first + managed + middle + managed + last
    report, after = precheck.plan_slimming(payload, _catalog())
    expected_pointer = (precheck.UPDATE_HEADING + "\n\n- Protocol.\n\n").encode().replace(b"\n", newline)
    assert report["status"] == "would_change"
    assert after == bom + first + expected_pointer + middle + last
    assert report["preserved_unmanaged_sha256"] == hashlib.sha256(bom + first + middle + last).hexdigest()
    assert [r["action"] for r in report["sections"]] == ["replace_with_current_pointer", "remove_duplicate"]
    second, repeated = precheck.plan_slimming(after, _catalog())
    assert second["status"] == "unchanged"
    assert repeated == after


@pytest.mark.parametrize("family", ["memory_workflow", "AI Governance Framework: agent-contract", "f7_update_boundary"])
def test_slimming_detects_exact_managed_duplicates(family: str) -> None:
    catalog = _catalog()
    block = next(iter(catalog.known[family])) + b"\n\n"
    payload = b"# Consumer\n\n" + block + block + b"## Custom\n- Keep.\n"
    report, after = precheck.plan_slimming(payload, catalog)
    assert report["status"] == "would_change"
    assert len(report["sections"]) == 2
    # Blank lines after a paired/bullet block are outside its owned span.
    separator = b"" if family == "memory_workflow" else b"\n"
    assert after == b"# Consumer\n\n" + block + separator + b"## Custom\n- Keep.\n"


@pytest.mark.parametrize("body", [
    "## AI Governance Update Intent Rule\n- Consumer-specific edit.\n",
    "## AI Governance Update Intent Rule\n- Old managed text.\n- Consumer addition.\n",
    "<!-- governance:key=f7_update_boundary -->\n- Consumer-specific boundary.\n",
    "<!-- AI Governance Framework: agent-contract BEGIN -->\n- Consumer edit.\n",
    "<!-- AI Governance Framework: agent-contract END -->\n",
])
def test_uncertain_ownership_refuses_all_writes(tmp_path: Path, body: str) -> None:
    block = (precheck.UPDATE_HEADING + "\n\n- Old managed text.\n\n").encode()
    payload = block + b"## Custom\n- Keep.\n\n" + body.encode()
    _write(tmp_path / "AGENTS.md", payload)
    report = precheck.slim_agents(tmp_path, tmp_path, apply=True, catalog=_catalog())
    assert report["status"] == "refused"
    assert report["errors"]
    assert report["changed_files"] == []
    assert (tmp_path / "AGENTS.md").read_bytes() == payload


def test_headings_in_fenced_examples_do_not_establish_ownership() -> None:
    payload = b"# Consumer\n\n```text\n## AI Governance Update Intent Rule\n- Example.\n```\n"
    report, after = precheck.plan_slimming(payload, _catalog())
    assert report["status"] == "unchanged"
    assert report["sections"] == []
    assert after == payload


def test_slimming_explicit_apply_writes_only_agents(tmp_path: Path) -> None:
    _write(tmp_path / "AGENTS.md", (precheck.UPDATE_HEADING + "\n\n- Old managed text.\n\n## Custom\n- Keep.\n").encode())
    _write(tmp_path / "AGENTS.base.md", b"protected\r\n")
    _write(tmp_path / "nested/data.txt", b"data\n")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    dry_run = precheck.slim_agents(tmp_path, tmp_path, catalog=_catalog())
    assert dry_run["mode"] == "dry_run"
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    applied = precheck.slim_agents(tmp_path, tmp_path, apply=True, catalog=_catalog())
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert applied["status"] == "applied"
    assert applied["changed_files"] == ["AGENTS.md"]
    assert before.keys() == after.keys()
    assert [str(p) for p in before if before[p] != after[p]] == ["AGENTS.md"]


def test_slimming_failed_atomic_replace_preserves_original(tmp_path: Path, monkeypatch) -> None:
    payload = (precheck.UPDATE_HEADING + "\n\n- Old managed text.\n\n## Custom\n- Keep.\n").encode()
    _write(tmp_path / "AGENTS.md", payload)

    def fail_replace(*_args):
        raise OSError("fixture cannot publish")

    monkeypatch.setattr(precheck.os, "replace", fail_replace)
    report = precheck.slim_agents(tmp_path, tmp_path, apply=True, catalog=_catalog())
    assert report["status"] == "refused"
    assert (tmp_path / "AGENTS.md").read_bytes() == payload
    assert list(tmp_path.iterdir()) == [tmp_path / "AGENTS.md"]


def test_slimming_refuses_link_and_invalid_utf8(tmp_path: Path) -> None:
    payload = (precheck.UPDATE_HEADING + "\n\n- Old managed text.\n\n").encode()
    _write(tmp_path / "AGENTS.md", payload)
    precheck.os.link(tmp_path / "AGENTS.md", tmp_path / "borrowed.md")
    report = precheck.slim_agents(tmp_path, tmp_path, apply=True, catalog=_catalog())
    assert report["status"] == "refused"
    assert (tmp_path / "borrowed.md").read_bytes() == payload
    invalid, result = precheck.plan_slimming(b"\xff", _catalog())
    assert invalid["status"] == "refused"
    assert result == b"\xff"


def test_slimming_detects_heading_and_headingless_router_duplicates() -> None:
    router = updater._memory_workflow_router_section().encode()
    headingless = router.split(b"\n\n", 1)[1]
    report, after = precheck.plan_slimming(router + headingless + b"## Custom\n- Keep.\n", _catalog())
    assert report["status"] == "would_change"
    assert after == router + b"## Custom\n- Keep.\n"


def test_slimming_refuses_differing_known_router_copies() -> None:
    first = updater._memory_workflow_router_section().encode()
    second = first.replace(b"--run-guard", b"--run-guard --format json")
    catalog = _catalog()
    catalog.add(second)
    payload = first + second
    report, after = precheck.plan_slimming(payload, catalog)
    assert report["status"] == "refused"
    assert after == payload


def test_catalog_recognizes_nested_framework_pairs_without_editing_the_parent() -> None:
    child = b"<!-- ai-governance:checkpoint-projection BEGIN version=1 -->\nCanonical.\n<!-- ai-governance:checkpoint-projection END -->\n"
    parent = installer.AGENT_CONTRACT_BLOCK_BEGIN.encode() + b"\n" + child + installer.AGENT_CONTRACT_BLOCK_END.encode() + b"\n"
    catalog = _catalog()
    catalog.add(parent)
    payload = child + child + b"## Custom\n- Keep.\n"
    report, after = precheck.plan_slimming(payload, catalog)
    assert report["status"] == "would_change"
    assert after == child + b"## Custom\n- Keep.\n"


def test_slimming_never_expands_a_known_short_section() -> None:
    payload = (precheck.UPDATE_HEADING + "\n- Old.\n\n## Custom\n- Keep.\n").encode()
    catalog = _catalog()
    catalog.add((precheck.UPDATE_HEADING + "\n- Old.\n").encode())
    report, after = precheck.plan_slimming(payload, catalog)
    assert report["status"] == "unchanged"
    assert after == payload


def test_catalog_uses_exact_historical_framework_text_without_execution(tmp_path: Path, framework: Path) -> None:
    old = (framework / precheck.SOURCE_PATHS[0]).read_bytes()
    _write(framework / precheck.SOURCE_PATHS[0], old.replace(b"Read the update protocol.", b"Read the short pointer."))
    _git(framework, "commit", "-am", "short pointer")
    catalog = precheck.load_managed_catalog(framework)
    old_section = next(s for s in precheck._sections(old)[0] if s.family == "update_intent")
    payload = old_section.payload + b"## Custom\n- Keep.\n"
    report, after = precheck.plan_slimming(payload, catalog)
    assert report["status"] == "would_change"
    assert b"Read the short pointer." in after
    assert b"Read the update protocol." not in after
    assert precheck._boundary_from_source(b'raise RuntimeError("must not execute")\nF7_UPDATE_BOUNDARY_BLOCK = "pointer"\n') == b"pointer"


def test_f7_observer_runs_before_backend_writes_and_keeps_final_budget_gate(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "c"
    _write(repo / "AGENTS.md", b"x" * 34000)
    monkeypatch.setattr(f7, "classify_repo", lambda *_a, **_kw: "external_contract_repo")
    called = []

    def backend(**kwargs):
        assert called == ["observed"]
        assert (repo / "AGENTS.md").read_bytes() == b"x" * 34000
        (repo / "AGENTS.md").write_bytes(b"x" * 34001)
        return f7.F7Result(ok=True, mode="apply", repo_root=str(repo), repo_role="external_contract_repo",
                           f7_final_status="partially_updated", stages={"instruction_context_budget": {"over_budget": True}})

    monkeypatch.setattr(f7, "_run_f7_full_update", backend)

    def observed(report):
        assert report["predicted"]["over_budget"]
        called.append("observed")

    result = f7.run_f7_full_update(repo_root=repo, framework_root=tmp_path / "absent", apply=True,
                                   precheck_observer=observed, precheck_scratch_dir=tmp_path)
    assert result.f7_final_status == "partially_updated"
    assert result.stages["instruction_budget_precheck"]["status"] == "over_budget"
    assert result.stages["instruction_context_budget"]["over_budget"]


def test_prediction_cli_overflow_returns_success_and_does_not_write(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "c"
    _write(repo / "AGENTS.md", b"x" * 34000)
    assert precheck.main(["predict", "--repo", str(repo), "--framework-root", str(tmp_path / "absent"),
                          "--repo-role", "external_contract_repo", "--scratch-dir", str(tmp_path), "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["drift_check_will_fail"]
    assert (repo / "AGENTS.md").read_bytes() == b"x" * 34000
