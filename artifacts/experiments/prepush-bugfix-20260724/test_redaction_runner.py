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

    import subprocess, tempfile, contextlib
    here = os.path.dirname(os.path.abspath(__file__))
    RUNNER = os.path.join(here, "redaction_runner.py")

    def cli(*args, cwd=None):
        # each invocation gets a timeout so a hang never masquerades as a pass
        return subprocess.run([sys.executable, RUNNER, *args],
                              capture_output=True, text=True, timeout=60, cwd=cwd)

    def wpath(d, text):
        p = os.path.join(d, "in-" + str(abs(hash(text)) % 10**8) + ".txt")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return p

    receipt_obj = {"arm": "C", "command": "ran governance-packet.md steps",
                   "results": {"regression": "PASS"}}

    # valid full handoff (isolated dir): packet + anonymized receipt + marker,
    # and the scorer verifier accepts the set
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "producer-receipt.json")
        open(rpath, "w").write(json.dumps(receipt_obj))
        pk, rout = os.path.join(d, "pk.json"), os.path.join(d, "anon-receipt.json")
        mk = rout + ".handoff-complete"
        cp = cli("--contract", CONTRACT, "--raw", wpath(d, VALID),
                 "--out", pk, "--receipt", rpath, "--receipt-out", rout)
        try:
            anon, pkt, marker = json.load(open(rout)), json.load(open(pk)), json.load(open(mk))
            import hashlib as _h
            ok = (cp.returncode == 0 and "arm" not in anon
                  and "governance-packet" not in json.dumps(anon)
                  and "[PACKET]" in json.dumps(anon)
                  and anon["results"]["regression"] == "PASS"
                  and anon["anon_id"] == pkt["anon_id"]
                  and marker["packet_sha256"] == _h.sha256(open(pk, "rb").read()).hexdigest()
                  and marker["receipt_sha256"] == _h.sha256(open(rout, "rb").read()).hexdigest())
            results.append(("full_handoff_with_marker", "PASS" if ok else "FAIL"))
        except Exception as e:
            results.append(("full_handoff_with_marker", f"FAIL: {e}"))
        # verifier accepts the good set
        vp = cli("--verify-handoff", mk)
        results.append(("verify_handoff_accepts_good_set",
                        "PASS" if vp.returncode == 0 else f"FAIL: {vp.returncode}"))
        # verifier rejects a tampered packet
        open(pk, "a").write("tampered")
        vp = cli("--verify-handoff", mk)
        results.append(("verify_handoff_rejects_tamper",
                        "PASS" if vp.returncode == 2 else "FAIL"))

    # ALIAS: --out == --receipt-out -> exit 2, no output/marker (the reported fail-open)
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "r.json"); open(rpath, "w").write(json.dumps(receipt_obj))
        alias = os.path.join(d, "same.json")
        cp = cli("--contract", CONTRACT, "--raw", wpath(d, VALID),
                 "--out", alias, "--receipt", rpath, "--receipt-out", alias)
        results.append(("out_equals_receipt_out_rejected",
                        "PASS" if (cp.returncode == 2 and not os.path.exists(alias)
                                   and not os.path.exists(alias + ".handoff-complete")) else "FAIL"))

    # ALIAS: --out == --raw -> exit 2, input preserved
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "r.json"); open(rpath, "w").write(json.dumps(receipt_obj))
        rawf = wpath(d, VALID)
        cp = cli("--contract", CONTRACT, "--raw", rawf, "--out", rawf,
                 "--receipt", rpath, "--receipt-out", os.path.join(d, "ro.json"))
        results.append(("out_aliases_input_rejected",
                        "PASS" if (cp.returncode == 2 and open(rawf).read().startswith("=== FIX_DIFF ===")) else "FAIL"))

    # content-malformed with full pair -> exit 2, no packet/receipt/marker
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "r.json"); open(rpath, "w").write(json.dumps(receipt_obj))
        pk2, rout2 = os.path.join(d, "pk.json"), os.path.join(d, "ro.json")
        cp = cli("--contract", CONTRACT, "--raw", wpath(d, "=== FIX_DIFF ===\nx\n"),
                 "--out", pk2, "--receipt", rpath, "--receipt-out", rout2)
        results.append(("malformed_exit2_no_output",
                        "PASS" if (cp.returncode == 2 and not os.path.exists(pk2)
                                   and not os.path.exists(rout2)) else "FAIL"))

    # orphan --receipt-out / orphan --receipt -> non-zero, no output
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "r.json"); open(rpath, "w").write(json.dumps(receipt_obj))
        pk3 = os.path.join(d, "pk.json")
        cp = cli("--contract", CONTRACT, "--raw", wpath(d, VALID),
                 "--out", pk3, "--receipt-out", os.path.join(d, "ro.json"))
        results.append(("orphan_receipt_out_rejected",
                        "PASS" if (cp.returncode != 0 and not os.path.exists(pk3)) else "FAIL"))
        cp = cli("--contract", CONTRACT, "--raw", wpath(d, VALID),
                 "--out", os.path.join(d, "pk4.json"), "--receipt", rpath)
        results.append(("orphan_receipt_rejected", "PASS" if cp.returncode != 0 else "FAIL"))

    # PUBLISH FAILURE: receipt-out is an existing DIRECTORY -> exit 2, AND the
    # isolated dir has NO leftover output OR staging temp (the reviewer's finding).
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "producer-receipt.json"); open(rpath, "w").write(json.dumps(receipt_obj))
        rawf = wpath(d, VALID)
        adir = os.path.join(d, "adir"); os.mkdir(adir)  # force replace() failure
        dpk = os.path.join(d, "pk.json")
        before = set(os.listdir(d))
        cp = cli("--contract", CONTRACT, "--raw", rawf,
                 "--out", dpk, "--receipt", rpath, "--receipt-out", adir)
        after = set(os.listdir(d))
        leftovers = after - before  # anything the run added and failed to clean
        results.append(("publish_failure_no_temp_or_partial",
                        "PASS" if (cp.returncode == 2 and not os.path.exists(dpk)
                                   and leftovers == set()) else f"FAIL: leftovers={leftovers}"))

    # HOSTILE 1: --out == <receipt-out>.handoff-complete (the DERIVED marker path).
    # Previously the marker overwrote the packet and the producer exited 0.
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "r.json"); open(rpath, "w").write(json.dumps(receipt_obj))
        rout = os.path.join(d, "anon.json")
        cp = cli("--contract", CONTRACT, "--raw", wpath(d, VALID),
                 "--out", rout + ".handoff-complete", "--receipt", rpath, "--receipt-out", rout)
        results.append(("marker_aliases_packet_rejected",
                        "PASS" if (cp.returncode == 2 and not os.path.exists(rout)
                                   and not os.path.exists(rout + ".handoff-complete")) else "FAIL"))

    # HOSTILE 2: case-insensitive alias (Windows): Same.json vs same.json
    with tempfile.TemporaryDirectory() as d:
        rpath = os.path.join(d, "r.json"); open(rpath, "w").write(json.dumps(receipt_obj))
        cp = cli("--contract", CONTRACT, "--raw", wpath(d, VALID),
                 "--out", os.path.join(d, "Same.json"),
                 "--receipt", rpath, "--receipt-out", os.path.join(d, "same.json"))
        if os.path.normcase("A") == os.path.normcase("a"):   # case-insensitive host
            ok = cp.returncode == 2
        else:                                                 # case-sensitive host: distinct files, valid
            ok = cp.returncode == 0
        results.append(("case_insensitive_output_alias_rejected", "PASS" if ok else "FAIL"))

    # HOSTILE 3: packet anon_id != receipt/marker anon_id, all hashes consistent.
    with tempfile.TemporaryDirectory() as d:
        pkt = {"schema": "gate2-redacted-packet.v1", "anon_id": "OUT-aaaaaaaaaaaa",
               "raw_output_sha256": "a" * 64, "redacted_output": "x",
               "redacted_output_sha256": __import__("hashlib").sha256(b"x").hexdigest()}
        rcp = {"anon_id": "OUT-bbbbbbbbbbbb"}
        pp, rp = os.path.join(d, "p.json"), os.path.join(d, "r.json")
        open(pp, "w", newline="\n").write(json.dumps(pkt))
        open(rp, "w", newline="\n").write(json.dumps(rcp))
        import hashlib as _h
        mk = os.path.join(d, "r.json.handoff-complete")
        open(mk, "w", newline="\n").write(json.dumps({
            "handoff": "gate2-scorer-handoff-set.v1", "anon_id": "OUT-bbbbbbbbbbbb",
            "packet_path": "p.json", "receipt_path": "r.json",
            "packet_sha256": _h.sha256(open(pp, "rb").read()).hexdigest(),
            "receipt_sha256": _h.sha256(open(rp, "rb").read()).hexdigest()}))
        vp = cli("--verify-handoff", mk)
        results.append(("verify_rejects_packet_anon_mismatch",
                        "PASS" if vp.returncode == 2 else "FAIL"))

    # HOSTILE 4: marker member path escapes its directory (traversal / absolute)
    with tempfile.TemporaryDirectory() as d:
        mk = os.path.join(d, "r.json.handoff-complete")
        open(mk, "w", newline="\n").write(json.dumps({
            "handoff": "gate2-scorer-handoff-set.v1", "anon_id": "OUT-cccccccccccc",
            "packet_path": "../escape.json", "receipt_path": "r.json",
            "packet_sha256": "0" * 64, "receipt_sha256": "0" * 64}))
        vp = cli("--verify-handoff", mk)
        results.append(("verify_rejects_path_traversal_member",
                        "PASS" if vp.returncode == 2 else "FAIL"))

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
