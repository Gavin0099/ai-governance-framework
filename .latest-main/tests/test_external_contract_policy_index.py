from __future__ import annotations

from pathlib import Path

from governance_tools.external_contract_policy_index import (
    build_external_contract_policy_index,
    format_human,
    format_markdown,
)


def _write_contract(repo_root: Path, contract_text: str, *, validator_names: list[str] | None = None) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "contract.yaml").write_text(contract_text, encoding="utf-8")
    if validator_names:
        validators_root = repo_root / "validators"
        validators_root.mkdir(parents=True, exist_ok=True)
        for name in validator_names:
            (validators_root / name).write_text("# validator\n", encoding="utf-8")


def test_build_external_contract_policy_index_classifies_profiles(tmp_path: Path) -> None:
    advisory_repo = tmp_path / "advisory-repo"
    mixed_repo = tmp_path / "mixed-repo"

    _write_contract(
        advisory_repo,
        "\n".join(
            [
                "name: advisory-contract",
                "domain: firmware",
                "validators:",
                "  - validators/foo.py",
            ]
        ),
        validator_names=["foo.py"],
    )
    _write_contract(
        mixed_repo,
        "\n".join(
            [
                "name: mixed-contract",
                "domain: kernel-driver",
                "validators:",
                "  - validators/bar.py",
                "hard_stop_rules:",
                "  - KD-002",
            ]
        ),
        validator_names=["bar.py"],
    )

    result = build_external_contract_policy_index([advisory_repo, mixed_repo])

    assert result["ok"] is True
    assert result["indexed_count"] == 2
    assert result["entries"][0]["enforcement_profile"] == "mixed"
    assert result["entries"][0]["hard_stop_rules"] == ["KD-002"]
    assert result["entries"][1]["enforcement_profile"] == "advisory-only"


def test_build_external_contract_policy_index_tracks_missing_contract(tmp_path: Path) -> None:
    missing_repo = tmp_path / "missing-repo"
    missing_repo.mkdir()

    result = build_external_contract_policy_index([missing_repo])

    assert result["ok"] is False
    assert result["entries"][0]["error"] == "contract.yaml not found"


def test_formatters_include_enforcement_details(tmp_path: Path) -> None:
    repo = tmp_path / "ic-repo"
    _write_contract(
        repo,
        "\n".join(
            [
                "name: ic-verification-contract",
                "domain: ic-verification",
                "validators:",
                "  - validators/signal_map_validator.py",
                "hard_stop_rules:",
                "  - ICV-001",
            ]
        ),
        validator_names=["signal_map_validator.py"],
    )

    result = build_external_contract_policy_index([repo])
    human = format_human(result)
    markdown = format_markdown(result)

    assert "[external_contract_policy_index]" in human
    assert "profile=mixed" in human
    assert "hard_stop_rules=ICV-001" in human
    assert "# Domain Enforcement Matrix" in markdown
    assert "`mixed`" in markdown
    assert "`ICV-001`" in markdown
