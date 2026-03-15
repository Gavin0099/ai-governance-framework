import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.trust_signal_snapshot import (
    build_trust_signal_snapshot,
    format_published_status_page,
    format_published_index,
    format_publication_index,
    format_index,
    resolve_publication_paths,
    write_publication_manifest,
    write_published_status,
    write_snapshot_bundle,
)


def _write_contract(repo_root: Path, contract_text: str, *, validator_names: list[str] | None = None) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "contract.yaml").write_text(contract_text, encoding="utf-8")
    if validator_names:
        validators_root = repo_root / "validators"
        validators_root.mkdir(parents=True, exist_ok=True)
        for name in validator_names:
            (validators_root / name).write_text("# validator\n", encoding="utf-8")


def test_build_trust_signal_snapshot_passes_on_repo_root():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    assert snapshot["ok"] is True
    assert snapshot["overview"]["release"]["ok"] is True
    assert snapshot["overview"]["auditor"]["ok"] is True


def test_build_trust_signal_snapshot_can_include_external_contract_repos(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    repo = tmp_path / "ic-contract"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: ic-verification-contract",
                "domain: ic-verification",
                "validators:",
                "  - validators/signal_map.py",
                "hard_stop_rules:",
                "  - ICV-001",
            ]
        ),
        validator_names=["signal_map.py"],
    )

    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        external_contract_repos=[repo],
    )

    assert snapshot["external_contract_repos"] == [str(repo.resolve())]
    assert snapshot["overview"]["external_contract_policy"]["ok"] is True


def test_write_snapshot_bundle_creates_latest_history_and_index(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    bundle = write_snapshot_bundle(snapshot, tmp_path / "status")

    assert Path(bundle["latest_json"]).is_file()
    assert Path(bundle["latest_txt"]).is_file()
    assert Path(bundle["latest_md"]).is_file()
    assert Path(bundle["history_json"]).is_file()
    assert Path(bundle["history_txt"]).is_file()
    assert Path(bundle["history_md"]).is_file()
    assert Path(bundle["index_md"]).is_file()
    assert Path(bundle["manifest_json"]).is_file()

    latest_payload = json.loads(Path(bundle["latest_json"]).read_text(encoding="utf-8"))
    assert latest_payload["ok"] is True
    index_text = Path(bundle["index_md"]).read_text(encoding="utf-8")
    assert "[trust_signal_snapshot_index]" in index_text
    assert "release_version=v1.0.0-alpha" in index_text
    manifest_payload = json.loads(Path(bundle["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest_payload["release_version"] == "v1.0.0-alpha"
    assert "latest" in manifest_payload


def test_write_snapshot_bundle_can_emit_external_policy_artifacts(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    repo = tmp_path / "kernel-contract"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: kernel-driver-contract",
                "domain: kernel-driver",
                "validators:",
                "  - validators/irql.py",
                "hard_stop_rules:",
                "  - KD-002",
            ]
        ),
        validator_names=["irql.py"],
    )

    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        external_contract_repos=[repo],
    )

    bundle = write_snapshot_bundle(snapshot, tmp_path / "status")

    assert Path(bundle["external_policy_latest_md"]).is_file()
    assert Path(bundle["external_policy_latest_json"]).is_file()
    assert Path(bundle["external_policy_history_md"]).is_file()
    assert Path(bundle["external_policy_history_json"]).is_file()
    assert "# Domain Enforcement Matrix" in Path(bundle["external_policy_latest_md"]).read_text(encoding="utf-8")


def test_format_index_handles_empty_history(tmp_path):
    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    rendered = format_index(history_dir)

    assert "[trust_signal_snapshot_index]" in rendered
    assert "reports=0" in rendered


def test_resolve_publication_paths_can_default_to_docs_status_generated(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)

    bundle_path, published_path, publication_root = resolve_publication_paths(
        project_root=project_root,
        publish_docs_status=True,
    )

    assert bundle_path == project_root / "docs" / "status" / "generated" / "bundle"
    assert published_path == project_root / "docs" / "status" / "generated" / "site"
    assert publication_root == project_root / "docs" / "status" / "generated"


def test_resolve_publication_paths_keeps_explicit_overrides(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)
    explicit_bundle = tmp_path / "bundle-out"
    explicit_published = tmp_path / "published-out"
    explicit_root = tmp_path / "root-out"

    bundle_path, published_path, publication_root = resolve_publication_paths(
        project_root=project_root,
        write_bundle=str(explicit_bundle),
        publish_status_dir=str(explicit_published),
        publication_root=str(explicit_root),
        publish_docs_status=True,
    )

    assert bundle_path == explicit_bundle.resolve()
    assert published_path == explicit_published.resolve()
    assert publication_root == explicit_root.resolve()


def test_resolve_publication_paths_defaults_publication_root_to_bundle_dir(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)
    bundle_dir = tmp_path / "bundle-out"
    published_dir = bundle_dir / "published"

    bundle_path, published_path, publication_root = resolve_publication_paths(
        project_root=project_root,
        write_bundle=str(bundle_dir),
        publish_status_dir=str(published_dir),
    )

    assert bundle_path == bundle_dir.resolve()
    assert published_path == published_dir.resolve()
    assert publication_root == bundle_dir.resolve()


def test_resolve_publication_paths_defaults_publication_root_to_published_parent(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)
    published_dir = tmp_path / "published-out"

    bundle_path, published_path, publication_root = resolve_publication_paths(
        project_root=project_root,
        publish_status_dir=str(published_dir),
    )

    assert bundle_path is None
    assert published_path == published_dir.resolve()
    assert publication_root == published_dir.resolve().parent


def test_write_published_status_creates_latest_pages(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    published = write_published_status(snapshot, tmp_path / "published")

    assert Path(published["latest_md"]).is_file()
    assert Path(published["latest_json"]).is_file()
    assert Path(published["readme_md"]).is_file()
    assert Path(published["history_md"]).is_file()
    assert Path(published["history_json"]).is_file()
    assert Path(published["index_md"]).is_file()
    assert Path(published["manifest_json"]).is_file()
    assert "# Published Trust Signal Snapshot" in Path(published["latest_md"]).read_text(encoding="utf-8")
    index_text = Path(published["index_md"]).read_text(encoding="utf-8")
    assert "# Published Trust Signal Index" in index_text
    manifest_payload = json.loads(Path(published["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest_payload["release_version"] == "v1.0.0-alpha"
    assert "history" in manifest_payload


def test_write_published_status_can_emit_domain_enforcement_matrix(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    repo = tmp_path / "ic-contract"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: ic-verification-contract",
                "domain: ic-verification",
                "validators:",
                "  - validators/signal_map.py",
                "hard_stop_rules:",
                "  - ICV-001",
            ]
        ),
        validator_names=["signal_map.py"],
    )
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        external_contract_repos=[repo],
    )

    published = write_published_status(snapshot, tmp_path / "published")

    assert Path(published["external_policy_md"]).is_file()
    assert Path(published["external_policy_json"]).is_file()
    assert "# Domain Enforcement Matrix" in Path(published["external_policy_md"]).read_text(encoding="utf-8")


def test_format_published_status_page_wraps_markdown_overview():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    rendered = format_published_status_page(snapshot)

    assert "# Published Trust Signal Snapshot" in rendered
    assert "# Trust Signal Overview" in rendered


def test_format_published_index_handles_empty_history(tmp_path):
    history_dir = tmp_path / "published-history"
    history_dir.mkdir(parents=True, exist_ok=True)

    rendered = format_published_index(history_dir)

    assert "# Published Trust Signal Index" in rendered
    assert "- Reports: `0`" in rendered


def test_write_publication_manifest_links_bundle_and_published(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    bundle = write_snapshot_bundle(snapshot, tmp_path / "status")
    published = write_published_status(snapshot, tmp_path / "status" / "published")

    publication = write_publication_manifest(
        snapshot,
        tmp_path / "status",
        bundle_paths=bundle,
        published_paths=published,
    )

    assert Path(publication["manifest_json"]).is_file()
    assert Path(publication["index_md"]).is_file()
    assert Path(publication["readme_md"]).is_file()
    manifest_payload = json.loads(Path(publication["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest_payload["ok"] is True
    assert manifest_payload["bundle_published"] is True
    assert manifest_payload["status_pages_published"] is True
    assert manifest_payload["project_root"] == str(project_root)
    assert manifest_payload["bundle"]["latest_json"].endswith("latest.json")
    assert manifest_payload["published"]["latest_md"].endswith("trust-signal-latest.md")
    readme_text = Path(publication["readme_md"]).read_text(encoding="utf-8")
    assert "# Generated Trust Signal Status" in readme_text
    assert "- Summary: `" in readme_text
    assert "- [Publication Index](PUBLICATION_INDEX.md)" in readme_text
    assert "- Site readme: `published/README.md`" in readme_text


def test_write_publication_manifest_tracks_external_contract_policy(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    repo = tmp_path / "kernel-contract"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: kernel-driver-contract",
                "domain: kernel-driver",
                "validators:",
                "  - validators/irql.py",
                "hard_stop_rules:",
                "  - KD-002",
            ]
        ),
        validator_names=["irql.py"],
    )
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
        external_contract_repos=[repo],
    )

    bundle = write_snapshot_bundle(snapshot, tmp_path / "status")
    publication = write_publication_manifest(snapshot, tmp_path / "status", bundle_paths=bundle)
    manifest_payload = json.loads(Path(publication["manifest_json"]).read_text(encoding="utf-8"))

    assert manifest_payload["external_contract_repo_count"] == 1
    assert manifest_payload["external_contract_policy_ok"] is True
    assert manifest_payload["external_contract_profile_counts"] == {"mixed": 1}
    assert manifest_payload["external_contract_policies"][0]["domain"] == "kernel-driver"
    assert manifest_payload["external_contract_policies"][0]["hard_stop_rules"] == ["KD-002"]
    assert manifest_payload["bundle"]["external_policy_latest_md"].endswith("external-contract-policy-latest.md")
    assert manifest_payload["published"] is None


def test_format_publication_index_is_summary_like():
    rendered = format_publication_index(
        {
            "generated_at": "2026-03-15T00:00:00+00:00",
            "release_version": "v1.0.0-alpha",
            "contract_path": "example/contract.yaml",
            "strict_runtime": True,
        },
        bundle_paths={"latest_json": "a.json", "latest_txt": "a.txt", "latest_md": "a.md", "history_json": "h.json", "history_txt": "h.txt", "history_md": "h.md", "index_md": "INDEX.md", "manifest_json": "MANIFEST.json"},
        published_paths={"latest_md": "p.md", "latest_json": "p.json", "readme_md": "README.md", "history_md": "ph.md", "history_json": "ph.json", "index_md": "PINDEX.md", "manifest_json": "pmanifest.json"},
    )

    assert "# Trust Signal Publication Index" in rendered
    assert "- Bundle published: `True`" in rendered
    assert "- Status pages published: `True`" in rendered
    assert "- External contract profiles: `none`" in rendered
