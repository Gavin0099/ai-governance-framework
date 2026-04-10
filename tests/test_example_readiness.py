import shutil
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.example_readiness import assess_example, assess_examples, format_human_result


def _make_local_tmp(name: str) -> Path:
    path = Path("tests") / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_example_readiness_reports_expected_examples():
    result = assess_examples(Path(".").resolve())

    assert result["ok"] is True
    names = [item["name"] for item in result["examples"]]
    assert names == ["todo-app-demo", "chaos-demo", "starter-pack", "usb-hub-contract"]

    by_name = {item["name"]: item for item in result["examples"]}
    assert by_name["todo-app-demo"]["kind"] == "runnable-demo"
    assert by_name["chaos-demo"]["kind"] == "walkthrough"
    assert by_name["starter-pack"]["kind"] == "scaffold"
    assert by_name["usb-hub-contract"]["kind"] == "domain-contract"
    assert by_name["usb-hub-contract"]["runtime_ready"] is True


def test_example_readiness_human_output_surfaces_runtime_status():
    result = assess_examples(Path(".").resolve())
    output = format_human_result(result)

    assert "[example_readiness]" in output
    assert "summary=name=todo-app-demo | kind=runnable-demo | ok=True" in output
    assert "summary=name=usb-hub-contract | kind=domain-contract | ok=True | runtime_ready=True" in output
    assert "note[starter-pack]=Use governance_tools/upgrade_starter_pack.py for opt-in scaffold refresh" in output

    todo = next(item for item in result["examples"] if item["name"] == "todo-app-demo")
    if not todo["runtime_ready"]:
        assert any("fastapi" in warning.lower() for warning in todo["warnings"])


def test_example_readiness_can_validate_a_runnable_demo_without_fastapi():
    project_root = _make_local_tmp("_tmp_example_readiness")
    try:
        example_root = project_root / "examples" / "sample-demo"
        (example_root / "src").mkdir(parents=True)
        (example_root / "README.md").write_text("# Sample demo\n", encoding="utf-8")
        (example_root / "PLAN.md").write_text("> **?敺??*: 2026-03-15\n", encoding="utf-8")
        (example_root / "src" / "main.py").write_text(
            textwrap.dedent(
                """
                class _Route:
                    def __init__(self, path):
                        self.path = path

                class _App:
                    title = "Sample Demo"
                    routes = [_Route("/health")]

                app = _App()
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        result = assess_example(
            project_root,
            {
                "name": "sample-demo",
                "kind": "runnable-demo",
                "required_paths": ["README.md", "PLAN.md", "src/main.py"],
                "required_modules": [],
                "optional_modules": [],
                "run_command": "python examples/sample-demo/src/main.py",
            },
            strict_runtime=True,
        )

        assert result["ok"] is True
        assert result["runtime_ready"] is True
        assert result["runtime_details"]["module_import_ok"] is True
        assert result["runtime_details"]["health_route_present"] is True
    finally:
        shutil.rmtree(project_root, ignore_errors=True)
