#!/usr/bin/env python3
"""Fail-closed negative tests for redaction_runner.py.

Run: python test_redaction_runner.py  (exit 0 = all pass)
"""
import json, os, sys
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
        results.append((name, "PASS: rejected with FormatError"))
    except Exception as e:  # a crash (IndexError/KeyError/...) is a DEFECT, not a pass
        results.append((name, f"FAIL: unexpected {type(e).__name__}: {e}"))


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

    # CLI subprocess: malformed input -> exit 2 AND no output file written
    import subprocess, tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    bad = _write_tmp("=== FIX_DIFF ===\r\nx\r\n")  # CRLF + missing markers
    outp = os.path.join(tempfile.gettempdir(), "should_not_be_created.json")
    if os.path.exists(outp):
        os.remove(outp)
    cp = subprocess.run(
        [sys.executable, os.path.join(here, "redaction_runner.py"),
         "--contract", CONTRACT, "--raw", bad, "--out", outp],
        capture_output=True, text=True)
    results.append(("cli_exit2", "PASS" if cp.returncode == 2 else f"FAIL: exit {cp.returncode}"))
    results.append(("cli_no_output_on_reject",
                    "PASS" if not os.path.exists(outp) else "FAIL: output written on reject"))

    # receipt anonymization: arm dropped, packet name redacted, substance kept
    receipt = {"arm": "C", "command": "ran governance-packet.md steps",
               "results": {"regression": "PASS"}}
    rpath = _write_tmp(json.dumps(receipt))
    rout = os.path.join(tempfile.gettempdir(), "anon-receipt.json")
    cp2 = subprocess.run(
        [sys.executable, os.path.join(here, "redaction_runner.py"),
         "--contract", CONTRACT, "--raw", _write_tmp(VALID),
         "--out", os.path.join(tempfile.gettempdir(), "pk.json"),
         "--receipt", rpath, "--receipt-out", rout],
        capture_output=True, text=True)
    try:
        anon = json.load(open(rout))
        ok = ("arm" not in anon
              and "governance-packet" not in json.dumps(anon)
              and "[PACKET]" in json.dumps(anon)
              and anon["results"]["regression"] == "PASS")
        results.append(("receipt_anonymized", "PASS" if (cp2.returncode == 0 and ok) else "FAIL"))
    except Exception as e:
        results.append(("receipt_anonymized", f"FAIL: {e}"))

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
