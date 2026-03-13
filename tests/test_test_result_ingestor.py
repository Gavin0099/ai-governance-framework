import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.test_result_ingestor import (
    ingest_junit_xml,
    ingest_pytest_text,
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
