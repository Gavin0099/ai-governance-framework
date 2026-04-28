"""
Integration tests for examples/cpp-userspace-contract.

Covers:
  - CppMutexSafetyValidator unit behaviour
  - CppRawMemoryValidator unit behaviour
  - CppReinterpretCastValidator unit behaviour
  - contract.yaml loads via domain_contract_loader
  - run_validators.py CLI: fixture pass/advisory-warn behaviour
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Paths ─────────────────────────────────────────────────────────────────────

EXAMPLE_DIR = Path("examples/cpp-userspace-contract")
CONTRACT_FILE = EXAMPLE_DIR / "contract.yaml"
MUTEX_VALIDATOR_PATH = EXAMPLE_DIR / "validators" / "cpp_mutex_safety_validator.py"
RAW_MEM_VALIDATOR_PATH = EXAMPLE_DIR / "validators" / "cpp_raw_memory_validator.py"
REINTERPRET_VALIDATOR_PATH = EXAMPLE_DIR / "validators" / "cpp_reinterpret_cast_validator.py"
FIXTURE_MUTEX_COMPLIANT = EXAMPLE_DIR / "fixtures" / "mutex_compliant.checks.json"
FIXTURE_MUTEX_VIOLATION = EXAMPLE_DIR / "fixtures" / "mutex_violation.checks.json"
FIXTURE_RAW_COMPLIANT = EXAMPLE_DIR / "fixtures" / "raw_memory_compliant.checks.json"
FIXTURE_RAW_VIOLATION = EXAMPLE_DIR / "fixtures" / "raw_memory_violation.checks.json"
FIXTURE_CAST_COMPLIANT = EXAMPLE_DIR / "fixtures" / "reinterpret_cast_compliant.checks.json"
FIXTURE_CAST_VIOLATION = EXAMPLE_DIR / "fixtures" / "reinterpret_cast_violation.checks.json"
RUN_VALIDATORS = EXAMPLE_DIR / "run_validators.py"


# ── Loader helpers ────────────────────────────────────────────────────────────

def _load_class(module_path: Path, class_name: str):
    spec = importlib.util.spec_from_file_location(module_path.stem, str(module_path.resolve()))
    mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    spec.loader.exec_module(mod)                         # type: ignore[union-attr]
    return getattr(mod, class_name)


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(RUN_VALIDATORS.resolve()), *args],
        cwd=Path(".").resolve(),
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )


# ── CppMutexSafetyValidator ───────────────────────────────────────────────────

class TestCppMutexSafetyValidator:
    @pytest.fixture(autouse=True)
    def validator(self):
        cls = _load_class(MUTEX_VALIDATOR_PATH, "CppMutexSafetyValidator")
        self.v = cls()

    def _run(self, file_path, source_code):
        return self.v.validate({"file_path": file_path, "source_code": source_code})

    # ── Non-C++ files skipped ─────────────────────────────────────────────

    def test_py_file_skipped(self):
        result = self._run("scripts/build.py", "import subprocess")
        assert result.ok is True
        assert result.metadata["is_cpp"] is False

    def test_yaml_file_skipped(self):
        result = self._run("config/settings.yaml", "mutex: enabled")
        assert result.ok is True
        assert result.metadata["is_cpp"] is False

    # ── Compliant patterns ────────────────────────────────────────────────

    def test_scoped_lock_passes(self):
        source = (
            "std::mutex m_mutex;\n"
            "void DoWork() {\n"
            "    std::scoped_lock lock(m_mutex);\n"
            "    Process();\n"
            "}\n"
        )
        result = self._run("src/Worker.cpp", source)
        assert result.ok is True

    def test_lock_guard_passes(self):
        source = (
            "void DoWork() {\n"
            "    std::lock_guard<std::mutex> guard(m_mutex);\n"
            "    Process();\n"
            "}\n"
        )
        result = self._run("src/Worker.cpp", source)
        assert result.ok is True

    def test_unique_lock_passes(self):
        source = (
            "void Wait() {\n"
            "    std::unique_lock<std::mutex> lk(m_mutex);\n"
            "    m_cv.wait(lk, [this] { return m_ready; });\n"
            "}\n"
        )
        result = self._run("src/Worker.cpp", source)
        assert result.ok is True

    def test_no_mutex_passes(self):
        source = (
            "int add(int a, int b) { return a + b; }\n"
        )
        result = self._run("src/Math.cpp", source)
        assert result.ok is True

    # ── Violations ────────────────────────────────────────────────────────

    def test_bare_lock_detected(self):
        source = (
            "void DoWork() {\n"
            "    m_mutex.lock();\n"
            "    Process();\n"
            "    m_mutex.unlock();\n"
            "}\n"
        )
        result = self._run("src/Worker.cpp", source)
        assert result.ok is False
        assert len(result.violations) >= 1
        assert "CPP_MUTEX_BARE_LOCK" in result.violations[0]
        assert result.metadata["lock_count"] == 1
        assert result.metadata["unlock_count"] == 1

    def test_bare_lock_only_also_detected(self):
        """Missing unlock is also a violation (deadlock on second entry)."""
        source = "void DoWork() { m_cs.lock(); Process(); }\n"
        result = self._run("src/Worker.cpp", source)
        assert result.ok is False

    def test_bare_unlock_only_also_detected(self):
        source = "void Release() { m_mutex.unlock(); }\n"
        result = self._run("src/Worker.cpp", source)
        assert result.ok is False

    def test_windows_path_normalised(self):
        source = "void f() { m_mutex.lock(); }\n"
        result = self._run(r"src\app\Worker.cpp", source)
        assert result.ok is False

    # ── Comment stripping ─────────────────────────────────────────────────

    def test_bare_lock_in_line_comment_no_fp(self):
        source = (
            "// m_mutex.lock(); — old pattern, replaced by scoped_lock\n"
            "void DoWork() { std::scoped_lock lock(m_mutex); }\n"
        )
        result = self._run("src/Worker.cpp", source)
        assert result.ok is True

    def test_bare_lock_in_block_comment_no_fp(self):
        source = (
            "/* m_mutex.lock();\n"
            "   m_mutex.unlock(); */\n"
            "void DoWork() { std::scoped_lock lock(m_mutex); }\n"
        )
        result = self._run("src/Worker.cpp", source)
        assert result.ok is True

    # ── Metadata ─────────────────────────────────────────────────────────

    def test_rule_ids_always_present(self):
        result = self._run("scripts/build.py", "import os")
        assert "CPP_MUTEX_BARE_LOCK" in result.rule_ids

    def test_advisory_mode_in_metadata(self):
        result = self._run("src/Worker.cpp", "void f() {}")
        assert result.metadata.get("mode") == "advisory"


# ── CppRawMemoryValidator ─────────────────────────────────────────────────────

class TestCppRawMemoryValidator:
    @pytest.fixture(autouse=True)
    def validator(self):
        cls = _load_class(RAW_MEM_VALIDATOR_PATH, "CppRawMemoryValidator")
        self.v = cls()

    def _run(self, file_path, source_code):
        return self.v.validate({"file_path": file_path, "source_code": source_code})

    # ── Non-impl files skipped ────────────────────────────────────────────

    def test_py_file_skipped(self):
        result = self._run("scripts/build.py", "ptr = object()")
        assert result.ok is True
        assert result.metadata["is_cpp_impl"] is False

    def test_header_file_skipped(self):
        result = self._run("include/Buffer.h", "T* p = new T();")
        assert result.ok is True
        assert result.metadata["is_cpp_impl"] is False

    def test_hpp_skipped(self):
        result = self._run("include/Buffer.hpp", "T* p = new T();")
        assert result.ok is True

    # ── Compliant patterns ────────────────────────────────────────────────

    def test_make_unique_passes(self):
        source = "auto buf = std::make_unique<uint8_t[]>(size);\n"
        result = self._run("src/Buffer.cpp", source)
        assert result.ok is True

    def test_make_shared_passes(self):
        source = "auto dev = std::make_shared<DeviceContext>(handle);\n"
        result = self._run("src/Device.cpp", source)
        assert result.ok is True

    def test_vector_allocation_passes(self):
        source = "std::vector<uint8_t> buffer(size);\n"
        result = self._run("src/Buffer.cpp", source)
        assert result.ok is True

    # ── Violations ────────────────────────────────────────────────────────

    def test_raw_new_assignment_detected(self):
        source = "uint8_t* pBuf = new uint8_t[dwSize];\n"
        result = self._run("src/Buffer.cpp", source)
        assert result.ok is False
        assert "CPP_RAW_MEMORY_ALLOC" in result.violations[0]
        assert result.metadata["raw_new_count"] >= 1

    def test_raw_new_class_detected(self):
        source = "SomeType* p = new SomeType();\n"
        result = self._run("src/Worker.cpp", source)
        assert result.ok is False

    def test_return_new_detected(self):
        source = "SomeType* create() { return new SomeType(); }\n"
        result = self._run("src/Factory.cpp", source)
        assert result.ok is False

    def test_windows_path_normalised(self):
        source = "uint8_t* p = new uint8_t[n];\n"
        result = self._run(r"src\app\Buffer.cpp", source)
        assert result.ok is False

    # ── Comment stripping ─────────────────────────────────────────────────

    def test_raw_new_in_line_comment_no_fp(self):
        source = (
            "// uint8_t* p = new uint8_t[n]; — replaced by make_unique\n"
            "auto p = std::make_unique<uint8_t[]>(n);\n"
        )
        result = self._run("src/Buffer.cpp", source)
        assert result.ok is True

    def test_raw_new_in_block_comment_no_fp(self):
        source = (
            "/* SomeType* p = new SomeType(); */\n"
            "auto p = std::make_unique<SomeType>();\n"
        )
        result = self._run("src/Worker.cpp", source)
        assert result.ok is True

    # ── Metadata ─────────────────────────────────────────────────────────

    def test_rule_ids_always_present(self):
        result = self._run("scripts/build.py", "import os")
        assert "CPP_RAW_MEMORY_ALLOC" in result.rule_ids


# ── CppReinterpretCastValidator ───────────────────────────────────────────────

class TestCppReinterpretCastValidator:
    @pytest.fixture(autouse=True)
    def validator(self):
        cls = _load_class(REINTERPRET_VALIDATOR_PATH, "CppReinterpretCastValidator")
        self.v = cls()

    def _run(self, file_path, source_code):
        return self.v.validate({"file_path": file_path, "source_code": source_code})

    # ── Non-impl files skipped ────────────────────────────────────────────

    def test_py_file_skipped(self):
        result = self._run("scripts/build.py", "x = int(y)")
        assert result.ok is True
        assert result.metadata["is_cpp_impl"] is False

    def test_header_file_skipped(self):
        result = self._run("include/Callback.h", "T* p = reinterpret_cast<T*>(x);")
        assert result.ok is True
        assert result.metadata["is_cpp_impl"] is False

    # ── Compliant patterns ────────────────────────────────────────────────

    def test_no_cast_passes(self):
        source = "void DoWork() { int x = 42; }\n"
        result = self._run("src/Worker.cpp", source)
        assert result.ok is True

    def test_static_cast_passes(self):
        source = (
            "CDialog* pBase = GetDialog();\n"
            "CMyDialog* pDlg = static_cast<CMyDialog*>(pBase);\n"
        )
        result = self._run("src/Callback.cpp", source)
        assert result.ok is True

    # ── Violations ────────────────────────────────────────────────────────

    def test_reinterpret_cast_detected(self):
        source = (
            "CMyDlg* pDlg = reinterpret_cast<CMyDlg*>(lParamContext);\n"
            "pDlg->OnEvent(lParam);\n"
        )
        result = self._run("src/Callback.cpp", source)
        assert result.ok is False
        assert "CPP_REINTERPRET_CAST_CALLBACK" in result.violations[0]
        assert result.metadata["cast_count"] >= 1

    def test_multiple_reinterpret_casts_counted(self):
        source = (
            "auto* p1 = reinterpret_cast<TypeA*>(a);\n"
            "auto* p2 = reinterpret_cast<TypeB*>(b);\n"
        )
        result = self._run("src/Callback.cpp", source)
        assert result.ok is False
        assert result.metadata["cast_count"] == 2

    def test_windows_path_normalised(self):
        source = "auto* p = reinterpret_cast<CMyDlg*>(lParam);\n"
        result = self._run(r"src\app\Callback.cpp", source)
        assert result.ok is False

    # ── Comment stripping ─────────────────────────────────────────────────

    def test_reinterpret_cast_in_line_comment_no_fp(self):
        source = (
            "// auto* p = reinterpret_cast<CMyDlg*>(lParam); — unsafe, use static\n"
            "CMyDlg* p = static_cast<CMyDlg*>(CWnd::FromHandlePermanent(hwnd));\n"
        )
        result = self._run("src/Callback.cpp", source)
        assert result.ok is True

    def test_reinterpret_cast_in_block_comment_no_fp(self):
        source = (
            "/* CMyDlg* p = reinterpret_cast<CMyDlg*>(lParam); */\n"
            "CMyDlg* p = static_cast<CMyDlg*>(GetDlg());\n"
        )
        result = self._run("src/Callback.cpp", source)
        assert result.ok is True

    # ── Metadata ─────────────────────────────────────────────────────────

    def test_rule_ids_always_present(self):
        result = self._run("scripts/build.py", "x = 1")
        assert "CPP_REINTERPRET_CAST_CALLBACK" in result.rule_ids


# ── Contract loader ───────────────────────────────────────────────────────────

def test_cpp_userspace_contract_loads():
    from governance_tools.domain_contract_loader import load_domain_contract
    loaded = load_domain_contract(CONTRACT_FILE)
    assert loaded is not None
    assert loaded["name"] == "cpp-userspace"
    assert len(loaded["validators"]) == 3
    names = {v["name"] for v in loaded["validators"]}
    assert "cpp_mutex_safety_validator" in names
    assert "cpp_raw_memory_validator" in names
    assert "cpp_reinterpret_cast_validator" in names


# ── CLI integration tests ─────────────────────────────────────────────────────

def test_mutex_compliant_fixture_exit_zero():
    proc = _run_cli(str(FIXTURE_MUTEX_COMPLIANT.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True


def test_mutex_violation_fixture_advisory_exit_zero():
    """Violation detected but advisory — exit 0, ok=False, hard_stop=False."""
    proc = _run_cli(str(FIXTURE_MUTEX_VIOLATION.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    mutex_results = [
        r for f in result["fixtures"]
        for r in f["results"]
        if r["validator"] == "cpp_mutex_safety_validator"
    ]
    assert mutex_results[0]["ok"] is False
    assert mutex_results[0]["hard_stop"] is False
    assert any("CPP_MUTEX_BARE_LOCK" in v for v in mutex_results[0]["violations"])


def test_raw_memory_compliant_fixture_passes():
    proc = _run_cli(str(FIXTURE_RAW_COMPLIANT.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True


def test_raw_memory_violation_fixture_advisory():
    proc = _run_cli(str(FIXTURE_RAW_VIOLATION.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    raw_results = [
        r for f in result["fixtures"]
        for r in f["results"]
        if r["validator"] == "cpp_raw_memory_validator"
    ]
    assert raw_results[0]["ok"] is False
    assert raw_results[0]["hard_stop"] is False


def test_reinterpret_cast_compliant_fixture_passes():
    proc = _run_cli(str(FIXTURE_CAST_COMPLIANT.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True


def test_reinterpret_cast_violation_fixture_advisory():
    proc = _run_cli(str(FIXTURE_CAST_VIOLATION.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    cast_results = [
        r for f in result["fixtures"]
        for r in f["results"]
        if r["validator"] == "cpp_reinterpret_cast_validator"
    ]
    assert cast_results[0]["ok"] is False
    assert cast_results[0]["hard_stop"] is False


def test_all_fixtures_advisory_exit_zero():
    proc = _run_cli(str((EXAMPLE_DIR / "fixtures").resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    assert len(result["fixtures"]) == 6


def test_json_flag_routes_text_to_stderr():
    proc = _run_cli(str(FIXTURE_MUTEX_VIOLATION.resolve()), "--json")
    assert proc.stderr  # text output goes to stderr
    json.loads(proc.stdout)  # stdout is valid JSON


def test_no_fixtures_error():
    proc = _run_cli(str((EXAMPLE_DIR / "rules").resolve()))
    assert proc.returncode == 2


# ── Agent integration file checks ────────────────────────────────────────────

def test_copilot_instructions_file_exists():
    path = EXAMPLE_DIR / ".github" / "copilot-instructions.md"
    assert path.exists(), "copilot-instructions.md missing"
    content = path.read_text(encoding="utf-8")
    assert "CPP_MUTEX_BARE_LOCK" in content
    assert "CPP_RAW_MEMORY_ALLOC" in content
    assert "CPP_REINTERPRET_CAST_CALLBACK" in content
    assert "Governance Contract" in content


def test_copilot_instructions_contains_red_lines():
    path = EXAMPLE_DIR / ".github" / "copilot-instructions.md"
    content = path.read_text(encoding="utf-8")
    assert "Red Lines" in content


def test_copilot_instructions_contains_pressure_field():
    path = EXAMPLE_DIR / ".github" / "copilot-instructions.md"
    content = path.read_text(encoding="utf-8")
    assert "PRESSURE" in content


def test_copilot_instructions_contains_risk_field():
    path = EXAMPLE_DIR / ".github" / "copilot-instructions.md"
    content = path.read_text(encoding="utf-8")
    assert "RISK" in content
    assert "L1" in content
    assert "L2" in content
    assert "L3" in content


def test_copilot_instructions_risk_l3_red_line():
    """RISK = L3 must appear in Red Lines section."""
    path = EXAMPLE_DIR / ".github" / "copilot-instructions.md"
    content = path.read_text(encoding="utf-8")
    assert "L3" in content
    red_lines_idx = content.index("Red Lines")
    assert "L3" in content[red_lines_idx:]


def test_agents_md_contains_risk_gate_policy():
    path = EXAMPLE_DIR / "AGENTS.md"
    content = path.read_text(encoding="utf-8")
    assert "Risk Gate Policy" in content
    assert "L1" in content
    assert "L2" in content
    assert "L3" in content


def test_codex_pre_task_hook_exists():
    path = EXAMPLE_DIR / "hooks" / "codex_pre_task.py"
    assert path.exists(), "codex_pre_task.py missing"
    content = path.read_text(encoding="utf-8")
    assert "plan_freshness" in content
    assert "validator_preflight" in content
    assert "harness=codex" in content
    assert "memory_pressure" in content


def test_codex_pre_task_hook_runs():
    """codex_pre_task.py must exit 0 and output key=value lines."""
    proc = subprocess.run(
        [sys.executable, str((EXAMPLE_DIR / "hooks" / "codex_pre_task.py").resolve())],
        cwd=Path(".").resolve(),
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert proc.returncode == 0
    assert "harness=codex" in proc.stdout
    assert "plan_freshness=" in proc.stdout
    assert "validator_preflight_ok=" in proc.stdout
    assert "memory_pressure=" in proc.stdout


def test_agents_md_contains_header_format():
    path = EXAMPLE_DIR / "AGENTS.md"
    content = path.read_text(encoding="utf-8")
    assert "PRESSURE" in content
    assert "Governance Contract Header Format" in content
