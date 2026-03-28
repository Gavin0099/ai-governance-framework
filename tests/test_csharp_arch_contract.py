"""
Integration tests for examples/csharp-arch-contract.

Covers:
  - DomainPinvokeValidator unit behaviour
  - contract.yaml loads via domain_contract_loader
  - run_validators.py CLI: compliant fixture passes, violation fixture advisory-warns
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Paths ─────────────────────────────────────────────────────────────────────

EXAMPLE_DIR = Path("examples/csharp-arch-contract")
CONTRACT_FILE = EXAMPLE_DIR / "contract.yaml"
VALIDATOR_PATH = EXAMPLE_DIR / "validators" / "domain_pinvoke_validator.py"
FIXTURE_COMPLIANT = EXAMPLE_DIR / "fixtures" / "pinvoke_compliant.checks.json"
FIXTURE_VIOLATION = EXAMPLE_DIR / "fixtures" / "pinvoke_violation.checks.json"
RUN_VALIDATORS = EXAMPLE_DIR / "run_validators.py"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_validator_class():
    """Load DomainPinvokeValidator.

    The project root is already on sys.path (see sys.path.insert above),
    so governance_tools is importable directly — no stubs needed.
    """
    spec = importlib.util.spec_from_file_location(
        "domain_pinvoke_validator", str(VALIDATOR_PATH.resolve())
    )
    mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    spec.loader.exec_module(mod)                         # type: ignore[union-attr]
    return mod.DomainPinvokeValidator


# ── Validator unit tests ──────────────────────────────────────────────────────

class TestDomainPinvokeValidator:
    @pytest.fixture(autouse=True)
    def validator(self):
        cls = _load_validator_class()
        self.v = cls()

    def _run(self, file_path, source_code, domain_roots=None):
        payload = {"file_path": file_path, "source_code": source_code}
        if domain_roots is not None:
            payload["domain_roots"] = domain_roots
        return self.v.validate(payload)

    # ── Files outside domain_roots ────────────────────────────────────────────

    def test_infrastructure_file_skipped(self):
        result = self._run(
            "src/Infrastructure/Adapters/OciNativeAdapter.cs",
            "[DllImport(\"oci.dll\")]\nprivate static extern int OciInit();",
        )
        assert result.ok is True
        assert result.violations == []
        assert result.metadata["in_domain"] is False

    def test_test_project_file_skipped(self):
        result = self._run(
            "tests/Unit/OciQueryServiceTests.cs",
            "[DllImport(\"oci.dll\")]\nprivate static extern int Stub();",
        )
        assert result.ok is True
        assert result.violations == []

    # ── Compliant domain files ────────────────────────────────────────────────

    def test_clean_domain_service_passes(self):
        source = (
            "namespace HP.OCI.Core.Services\n"
            "{\n"
            "    public sealed class OciQueryService\n"
            "    {\n"
            "        public string GetStatus() => \"ok\";\n"
            "    }\n"
            "}\n"
        )
        result = self._run("src/HP.OCI.Core/Services/OciQueryService.cs", source)
        assert result.ok is True
        assert result.violations == []
        assert result.metadata["in_domain"] is True

    def test_dllimport_in_line_comment_no_fp(self):
        """// [DllImport("oci.dll")] — in a comment line, must not trigger."""
        source = (
            "namespace HP.OCI.Core\n"
            "{\n"
            "    // Do NOT use [DllImport(\"oci.dll\")] in domain layer.\n"
            "    public class Marker {}\n"
            "}\n"
        )
        result = self._run("src/HP.OCI.Core/Marker.cs", source)
        assert result.ok is True
        assert result.violations == []

    def test_dllimport_in_block_comment_no_fp(self):
        """/* [DllImport("oci.dll")] */ — inside block comment, must not trigger."""
        source = (
            "/* [DllImport(\"oci.dll\")] — prohibited in domain */\n"
            "namespace HP.OCI.Core { public class Marker {} }\n"
        )
        result = self._run("src/HP.OCI.Core/Marker.cs", source)
        assert result.ok is True
        assert result.violations == []

    # ── Violation patterns ────────────────────────────────────────────────────

    def test_dllimport_in_domain_detected(self):
        source = (
            "using System.Runtime.InteropServices;\n"
            "namespace HP.OCI.Core.Services\n"
            "{\n"
            "    public class Bad\n"
            "    {\n"
            "        [DllImport(\"oci.dll\")]\n"
            "        private static extern int OciInit();\n"
            "    }\n"
            "}\n"
        )
        result = self._run("src/HP.OCI.Core/Services/Bad.cs", source)
        assert result.ok is False
        assert len(result.violations) >= 1
        assert any("ARCH_DOMAIN_PINVOKE" in v for v in result.violations)
        assert any("[DllImport" in v for v in result.violations)

    def test_libraryimport_in_domain_detected(self):
        source = (
            "using System.Runtime.InteropServices;\n"
            "namespace HP.OCI.Core\n"
            "{\n"
            "    public partial class NativeBridge\n"
            "    {\n"
            "        [LibraryImport(\"oci\")]\n"
            "        private static partial int OciQuery();\n"
            "    }\n"
            "}\n"
        )
        result = self._run("src/HP.OCI.Core/NativeBridge.cs", source)
        assert result.ok is False
        assert any("ARCH_DOMAIN_PINVOKE" in v for v in result.violations)
        assert any("[LibraryImport" in v for v in result.violations)

    def test_extern_static_in_domain_detected(self):
        source = (
            "namespace HP.OCI.Core\n"
            "{\n"
            "    public class Legacy\n"
            "    {\n"
            "        extern static int OciLegacyInit();\n"
            "    }\n"
            "}\n"
        )
        result = self._run("src/HP.OCI.Core/Legacy.cs", source)
        assert result.ok is False
        assert any("ARCH_DOMAIN_PINVOKE" in v for v in result.violations)
        assert any("extern" in v for v in result.violations)

    def test_multiple_patterns_each_reported_once(self):
        source = (
            "using System.Runtime.InteropServices;\n"
            "namespace HP.OCI.Core\n"
            "{\n"
            "    public partial class Multi\n"
            "    {\n"
            "        [DllImport(\"a.dll\")]\n"
            "        extern static int Foo();\n"
            "        [LibraryImport(\"b\")]\n"
            "        private static partial int Bar();\n"
            "    }\n"
            "}\n"
        )
        result = self._run("src/HP.OCI.Core/Multi.cs", source)
        assert result.ok is False
        # Each pattern appears at most once in violations
        dllimport_hits = [v for v in result.violations if "[DllImport" in v]
        lib_hits = [v for v in result.violations if "[LibraryImport" in v]
        extern_hits = [v for v in result.violations if "extern" in v]
        assert len(dllimport_hits) == 1
        assert len(lib_hits) == 1
        assert len(extern_hits) == 1

    def test_custom_domain_roots_respected(self):
        """Custom domain_roots overrides the default HP.OCI.Core path."""
        source = "[DllImport(\"oci.dll\")]\nprivate static extern int X();"
        # With default roots: src/MyDomain/ is outside → skip
        result_skip = self._run(
            "src/MyDomain/Svc.cs", source,
            domain_roots=["src/HP.OCI.Core/"]
        )
        assert result_skip.ok is True

        # With custom roots: src/MyDomain/ is inside → detect
        result_detect = self._run(
            "src/MyDomain/Svc.cs", source,
            domain_roots=["src/MyDomain/"]
        )
        assert result_detect.ok is False

    def test_windows_backslash_path_normalised(self):
        """Windows-style path separators must still match domain_roots."""
        source = "[DllImport(\"oci.dll\")]\nprivate static extern int X();"
        result = self._run(
            r"src\HP.OCI.Core\Services\Bad.cs", source
        )
        assert result.ok is False

    def test_rule_ids_always_present(self):
        result = self._run("src/HP.OCI.Core/Clean.cs", "public class Clean {}")
        assert "ARCH_DOMAIN_PINVOKE" in result.rule_ids

    def test_advisory_mode_in_metadata(self):
        result = self._run("src/HP.OCI.Core/Clean.cs", "public class Clean {}")
        assert result.metadata.get("mode") == "advisory"


# ── Contract loader test ──────────────────────────────────────────────────────

def test_csharp_arch_contract_loads():
    from governance_tools.domain_contract_loader import load_domain_contract
    loaded = load_domain_contract(CONTRACT_FILE)
    assert loaded is not None
    assert loaded["name"] == "csharp-arch"
    assert len(loaded["validators"]) == 1
    assert loaded["validators"][0]["name"] == "domain_pinvoke_validator"


# ── run_validators.py CLI tests ───────────────────────────────────────────────

def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(RUN_VALIDATORS.resolve()), *args],
        cwd=Path(".").resolve(),
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
        check=False,
    )


def test_run_validators_compliant_fixture_exit_zero():
    """Compliant fixture — no violations → exit 0."""
    proc = _run_cli(str(FIXTURE_COMPLIANT.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    fixture_result = result["fixtures"][0]
    assert fixture_result["passed"] is True
    assert all(r["ok"] for r in fixture_result["results"])


def test_run_validators_violation_fixture_advisory_exit_zero():
    """Violation fixture raises advisory WARN but does NOT block (exit 0) while in advisory mode."""
    proc = _run_cli(str(FIXTURE_VIOLATION.resolve()), "--json")
    # Advisory rules never set hard_stop, so overall_pass stays True and exit code is 0.
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    fixture_result = result["fixtures"][0]
    # The validator itself reports ok=False (violation found)
    validator_result = fixture_result["results"][0]
    assert validator_result["ok"] is False
    assert len(validator_result["violations"]) >= 1
    assert any("ARCH_DOMAIN_PINVOKE" in v for v in validator_result["violations"])
    # But hard_stop is False because the rule is advisory
    assert validator_result["hard_stop"] is False


def test_run_validators_violation_fixture_text_stderr():
    """When --json is passed, human-readable text goes to stderr, not stdout."""
    proc = _run_cli(str(FIXTURE_VIOLATION.resolve()), "--json")
    assert "PASS" in proc.stderr or "FAIL" in proc.stderr or "WARN" in proc.stderr
    # stdout must be parseable JSON
    parsed = json.loads(proc.stdout)
    assert "overall_pass" in parsed


def test_run_validators_all_fixtures_pass():
    """Running against all fixtures exits 0 (all advisory, no hard-stops)."""
    proc = _run_cli(str(EXAMPLE_DIR.resolve() / "fixtures"), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    assert len(result["fixtures"]) == 2


def test_run_validators_no_fixtures_error():
    """Pointing at a directory with no fixtures returns exit code 2."""
    proc = _run_cli(str((EXAMPLE_DIR / "rules").resolve()))
    assert proc.returncode == 2
