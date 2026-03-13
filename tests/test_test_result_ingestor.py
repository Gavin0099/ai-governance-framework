import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.test_result_ingestor import (
    ingest_msbuild_warning_text,
    ingest_junit_xml,
    ingest_pytest_text,
    ingest_sarif,
    ingest_sdv_text,
)


def test_ingest_pytest_text_success_summary():
    payload = ingest_pytest_text(
        """
============================= test session starts =============================
collected 3 items

tests/test_demo.py::test_invalid_input_rejected .
tests/test_demo.py::test_boundary_max_size .
tests/test_demo.py::test_dependency_failure_timeout .                   [100%]

============================== 3 passed in 0.12s ==============================
""".strip()
    )
    assert payload["ok"] is True
    assert payload["summary"]["passed"] == 3
    assert payload["summary"]["failed"] == 0
    assert len(payload["test_names"]) == 3
    assert payload["failure_test_validation"]["ok"] is True


def test_ingest_pytest_text_failures_and_warnings():
    payload = ingest_pytest_text(
        """
FAILED tests/test_demo.py::test_refactor_guard - AssertionError: behavior changed
tests/test_demo.py::test_invalid_payload_rejected .
tests/test_demo.py::test_boundary_min_value .
warning: something noisy
PytestCacheWarning: cache write skipped
========================= 1 failed, 2 passed in 0.50s =========================
""".strip()
    )
    assert payload["ok"] is False
    assert payload["summary"]["failed"] == 1
    assert any("FAILED tests/test_demo.py::test_refactor_guard" in e for e in payload["errors"])
    assert len(payload["warnings"]) >= 2
    assert payload["failure_test_validation"]["ok"] is False
    assert any("failure_path" in e for e in payload["errors"])


def test_ingest_junit_xml_collects_failures():
    payload = ingest_junit_xml(
        """
<testsuite name="pytest" tests="4" failures="1" errors="0" skipped="0">
  <testcase classname="tests.test_demo" name="test_invalid_payload" />
  <testcase classname="tests.test_demo" name="test_boundary_max_value" />
  <testcase classname="tests.test_demo" name="test_dependency_failure_timeout">
    <failure message="behavior changed">assert 1 == 2</failure>
  </testcase>
  <testcase classname="tests.test_demo" name="test_other" />
</testsuite>
""".strip()
    )
    assert payload["ok"] is False
    assert payload["summary"]["passed"] == 3
    assert payload["summary"]["failed"] == 1
    assert any("tests.test_demo::test_dependency_failure_timeout - behavior changed" == e for e in payload["errors"])
    assert "tests.test_demo::test_invalid_payload" in payload["test_names"]
    assert payload["failure_test_validation"]["ok"] is True


def test_ingest_sdv_text_emits_driver_analysis_signals():
    payload = ingest_sdv_text(
        """
Static Driver Verifier: rule set completed successfully
SAL analysis: pageable code not reachable from DISPATCH_LEVEL path
""".strip()
    )
    assert payload["ok"] is True
    assert payload["sdv_verified"] is True
    assert payload["driver_analysis_verified"] is True
    assert len(payload["diagnostics"]) == 2


def test_ingest_msbuild_warning_text_collects_driver_related_diagnostics():
    payload = ingest_msbuild_warning_text(
        """
driver.c(42): warning C28167: IRQL mismatch detected for dispatch path
driver.c(50): warning C6387: user buffer length may be null
Build succeeded.
""".strip()
    )
    assert payload["ok"] is True
    assert len(payload["warnings"]) == 2
    assert payload["irql_verified"] is True
    assert payload["ioctl_boundary_verified"] is True


def test_ingest_sarif_collects_diagnostics_and_driver_signals():
    payload = ingest_sarif(
        """
{
  "version": "2.1.0",
  "runs": [
    {
      "results": [
        {
          "ruleId": "SDV001",
          "level": "warning",
          "message": {"text": "Static Driver Verifier reports IRQL contract for dispatch path."}
        },
        {
          "ruleId": "SAL100",
          "level": "note",
          "message": {"text": "SAL analysis confirmed invalid input buffer length validation."}
        }
      ]
    }
  ]
}
""".strip()
    )
    assert payload["ok"] is True
    assert len(payload["diagnostics"]) == 2
    assert payload["driver_analysis_verified"] is True
    assert payload["irql_verified"] is True
    assert payload["ioctl_boundary_verified"] is True
