from pathlib import Path

from runtime_hooks.runtime_path_overrides import apply_runtime_path_overrides


def test_apply_runtime_path_overrides_infers_project_root_and_plan_from_contract(tmp_path: Path):
    contract_file = tmp_path / "contract.yaml"
    plan_path = tmp_path / "PLAN.md"
    contract_file.write_text("name: example\n", encoding="utf-8")
    plan_path.write_text(
        "> **最後更新**: 2026-03-15\n"
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )

    updated = apply_runtime_path_overrides({}, contract_file=contract_file)

    assert updated["contract"] == str(contract_file.resolve())
    assert updated["project_root"] == str(tmp_path.resolve())
    assert updated["plan_path"] == str((tmp_path / "PLAN.md").resolve())


def test_apply_runtime_path_overrides_infers_plan_from_explicit_project_root(tmp_path: Path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)

    updated = apply_runtime_path_overrides({}, project_root=project_root)

    assert updated["project_root"] == str(project_root.resolve())
    assert updated["plan_path"] == str((project_root / "PLAN.md").resolve())
    assert "contract" not in updated


def test_apply_runtime_path_overrides_preserves_explicit_plan_path(tmp_path: Path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)
    explicit_plan = tmp_path / "custom-plan.md"

    updated = apply_runtime_path_overrides({}, project_root=project_root, plan_path=explicit_plan)

    assert updated["project_root"] == str(project_root.resolve())
    assert updated["plan_path"] == str(explicit_plan.resolve())
