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

    import subprocess, tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    RUNNER = os.path.join(here, "redaction_runner.py")
    G = tempfile.gettempdir()

    def cli(*args):
        return subprocess.run([sys.executable, RUNNER, *args],
                              capture_output=True, text=True)

    receipt = {"arm": "C", "command": "ran governance-packet.md steps",
               "results": {"regression": "PASS"}}
    rpath = _write_tmp(json.dumps(receipt))

    # valid full handoff: exit 0, packet + anonymized receipt, arm dropped, anon_id bound
    pk, rout = os.path.join(G, "pk.json"), os.path.join(G, "anon-receipt.json")
    for p in (pk, rout):
        if os.path.exists(p):
            os.remove(p)
    cp = cli("--contract", CONTRACT, "--raw", _write_tmp(VALID),
             "--out", pk, "--receipt", rpath, "--receipt-out", rout)
    try:
        anon = json.load(open(rout))
        pkt = json.load(open(pk))
        ok = (cp.returncode == 0 and "arm" not in anon
              and "governance-packet" not in json.dumps(anon)
              and "[PACKET]" in json.dumps(anon)
              and anon["results"]["regression"] == "PASS"
              and anon["anon_id"] == pkt["anon_id"])
        results.append(("full_handoff_receipt_anonymized_and_bound", "PASS" if ok else "FAIL"))
    except Exception as e:
        results.append(("full_handoff_receipt_anonymized_and_bound", f"FAIL: {e}"))

    # content-malformed WITH full receipt pair -> exit 2, NO packet, NO receipt
    pk2, rout2 = os.path.join(G, "pk2.json"), os.path.join(G, "r2.json")
    for p in (pk2, rout2):
        if os.path.exists(p):
            os.remove(p)
    cp = cli("--contract", CONTRACT, "--raw", _write_tmp("=== FIX_DIFF ===\nx\n"),
             "--out", pk2, "--receipt", rpath, "--receipt-out", rout2)
    results.append(("malformed_exit2_no_output",
                    "PASS" if (cp.returncode == 2 and not os.path.exists(pk2)
                               and not os.path.exists(rout2)) else "FAIL"))

    # missing --receipt (orphan --receipt-out) -> non-zero, no output
    pk3 = os.path.join(G, "pk3.json")
    if os.path.exists(pk3):
        os.remove(pk3)
    cp = cli("--contract", CONTRACT, "--raw", _write_tmp(VALID),
             "--out", pk3, "--receipt-out", os.path.join(G, "r3.json"))
    results.append(("orphan_receipt_out_rejected",
                    "PASS" if (cp.returncode != 0 and not os.path.exists(pk3)) else "FAIL"))

    # missing --receipt-out (orphan --receipt) -> non-zero
    cp = cli("--contract", CONTRACT, "--raw", _write_tmp(VALID),
             "--out", os.path.join(G, "pk4.json"), "--receipt", rpath)
    results.append(("orphan_receipt_rejected",
                    "PASS" if cp.returncode != 0 else "FAIL"))

    # partial-output: receipt-out is an existing DIRECTORY -> write fails, packet removed
    dpk = os.path.join(G, "pk5.json")
    if os.path.exists(dpk):
        os.remove(dpk)
    cp = cli("--contract", CONTRACT, "--raw", _write_tmp(VALID),
             "--out", dpk, "--receipt", rpath, "--receipt-out", G)  # G is a dir
    results.append(("partial_output_cleaned_up",
                    "PASS" if (cp.returncode == 2 and not os.path.exists(dpk)) else "FAIL"))

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
