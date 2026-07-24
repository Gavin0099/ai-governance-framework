#!/usr/bin/env python3
"""Fail-closed negative tests for redaction_runner.py.

Run: python test_redaction_runner.py  (exit 0 = all pass)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import redaction_runner as R

CONTRACT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "scorer-handoff-contract.json")

VALID = (
    "=== FIX_DIFF ===\n--- a/x\n+++ b/x\n"
    "=== TEST_LOG ===\ntest_ok PASSED\n"
    "=== VALIDATOR_OUTPUT ===\nno findings\n"
    "=== COMPLETION_CLAIM ===\nI am Arm C; regression test passed.\n"
)


def parse(raw: str):
    return R.parse_canonical(raw.encode("utf-8"))


def expect_reject(name, raw, results):
    try:
        parse(raw)
        results.append((name, "FAIL: accepted bad input"))
    except R.FormatError:
        results.append((name, "PASS: rejected"))
    except Exception as e:  # any other error is also a rejection but note it
        results.append((name, f"PASS(other): {type(e).__name__}"))


def main() -> int:
    results = []

    # valid must be accepted and produce a redacted packet
    try:
        pkt = R.run(CONTRACT, _write_tmp(VALID))
        ok = (pkt["schema"] == "gate2-redacted-packet.v1"
              and "Arm C" not in pkt["redacted_output"]
              and "regression test passed" in pkt["redacted_output"]
              and "test_ok PASSED" in pkt["redacted_output"])
        results.append(("valid_accepted", "PASS" if ok else "FAIL: bad packet"))
    except Exception as e:
        results.append(("valid_accepted", f"FAIL: {e}"))

    # missing a marker
    expect_reject("missing_marker",
                  VALID.replace("=== VALIDATOR_OUTPUT ===\nno findings\n", ""), results)
    # duplicate COMPLETION_CLAIM
    expect_reject("duplicate_marker",
                  VALID + "=== COMPLETION_CLAIM ===\nextra\n", results)
    # out of order (swap FIX_DIFF and TEST_LOG blocks)
    ooo = ("=== TEST_LOG ===\ntest_ok PASSED\n"
           "=== FIX_DIFF ===\n--- a/x\n"
           "=== VALIDATOR_OUTPUT ===\nno findings\n"
           "=== COMPLETION_CLAIM ===\nclaim\n")
    expect_reject("out_of_order", ooo, results)
    # CRLF
    expect_reject("crlf", VALID.replace("\n", "\r\n"), results)
    # preamble before first marker
    expect_reject("preamble", "hello\n" + VALID, results)

    for name, r in results:
        print(f"[{name}] {r}")
    return 0 if all(r.startswith("PASS") for _, r in results) else 1


def _write_tmp(text: str) -> str:
    import tempfile
    fd, p = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return p


if __name__ == "__main__":
    sys.exit(main())
