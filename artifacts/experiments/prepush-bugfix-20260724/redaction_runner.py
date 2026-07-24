#!/usr/bin/env python3
"""Canonical redaction runner for gate2-scorer-handoff.v1 (fail-closed).

Answer-safe: operates only on a producer's raw-output.txt. It never reads the
Gate 0 analysis, the fix, or the answer. It redacts ONLY the COMPLETION_CLAIM
section and receipt metadata per the frozen literal map; FIX_DIFF / TEST_LOG /
VALIDATOR_OUTPUT are copied verbatim.

FAIL-CLOSED: the parser rejects any input that is not in the frozen canonical
format. It does NOT accept out-of-order, duplicate, missing, preamble, or
CRLF inputs. Structural validity is enforced before any redaction runs.

Usage:
    python redaction_runner.py --contract scorer-handoff-contract.json \\
        --raw raw-output.txt --out redacted-packet.json
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys

MARKERS = ["=== FIX_DIFF ===", "=== TEST_LOG ===",
           "=== VALIDATOR_OUTPUT ===", "=== COMPLETION_CLAIM ==="]


class FormatError(Exception):
    pass


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


CONTRACT_ID = "gate2-scorer-handoff.v2"


def validate_contract(contract: dict) -> None:
    """Parse-level validity only. Governance authorization (owner-re-signed
    frozen=true) is a SEPARATE gate: a contract may be parse-valid yet not yet
    Gate-2-authorized. main() prints a notice when frozen is not true."""
    if contract.get("contract") != CONTRACT_ID:
        raise FormatError(f"contract id != {CONTRACT_ID}")
    if not isinstance(contract.get("frozen"), bool):
        raise FormatError("contract 'frozen' must be a boolean governance flag")
    if contract.get("producer_output_artifact", {}).get("section_markers") != MARKERS:
        raise FormatError("contract section_markers do not match the canonical markers")


def parse_canonical(raw_bytes: bytes) -> dict[str, str]:
    """Strict, fail-closed parse. Raises FormatError on any deviation."""
    if b"\r" in raw_bytes:
        raise FormatError("CRLF (or CR) found; canonical format requires LF only")
    text = raw_bytes.decode("utf-8")
    lines = text.split("\n")

    # Marker lines = lines that exactly equal a marker. Must be standalone lines.
    marker_positions = [(i, ln) for i, ln in enumerate(lines) if ln in MARKERS]

    # exactly one of each, in fixed order, and no preamble before the first.
    seen = [ln for _, ln in marker_positions]
    if seen != MARKERS:
        raise FormatError(
            f"markers must appear exactly once each, standalone, in fixed order; got {seen}"
        )
    first_idx = marker_positions[0][0]
    if first_idx != 0:
        raise FormatError("undefined preamble before the first marker is not allowed")

    sections: dict[str, str] = {}
    for k, (idx, ln) in enumerate(marker_positions):
        start = idx + 1
        end = marker_positions[k + 1][0] if k + 1 < len(marker_positions) else len(lines)
        name = ln.strip("= ").strip()
        sections[name] = "\n".join(lines[start:end])
    return sections


def redact(text: str, rules: list[dict]) -> tuple[str, dict[str, int]]:
    counts = {}
    for r in rules:
        text, n = re.subn(r["pattern"], r["placeholder"], text, flags=re.IGNORECASE)
        counts[r["pattern"]] = counts.get(r["pattern"], 0) + n
    return text, counts


def anonymize_receipt(receipt: dict, rules: list[dict], drop_fields: list[str]) -> dict:
    """Fail-closed receipt anonymization: drop identity fields, redact string
    values through the literal map. Non-string leaves are passed through."""
    dropped = {k: v for k, v in receipt.items() if k not in drop_fields}

    def walk(x):
        if isinstance(x, str):
            return redact(x, rules)[0]
        if isinstance(x, list):
            return [walk(i) for i in x]
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        return x

    return walk(dropped)


def run(contract_path: str, raw_path: str) -> dict:
    contract_bytes = open(contract_path, "rb").read()
    contract = json.loads(contract_bytes)
    validate_contract(contract)
    rules = contract["redaction"]["literal_map"]

    raw_bytes = open(raw_path, "rb").read()
    sections = parse_canonical(raw_bytes)

    redacted_claim, match_counts = redact(sections["COMPLETION_CLAIM"], rules)
    redacted = dict(sections)
    redacted["COMPLETION_CLAIM"] = redacted_claim
    # rebuild with LF and the canonical marker order
    redacted_text = ""
    for m in MARKERS:
        redacted_text += m + "\n" + redacted[m.strip("= ").strip()]
        if not redacted_text.endswith("\n"):
            redacted_text += "\n"

    raw_sha = sha256_hex(raw_bytes)
    return {
        "schema": "gate2-redacted-packet.v1",
        "anon_id": "OUT-" + raw_sha[:12],
        "contract_sha256": sha256_hex(contract_bytes),
        "raw_output_sha256": raw_sha,
        "redacted_output_sha256": sha256_hex(redacted_text.encode("utf-8")),
        "per_rule_match_count": match_counts,
        "total_redactions": sum(match_counts.values()),
        "redacted_output": redacted_text,
        "blinding_compromised": None,
        "blinding_compromised_reason": None,
        "note": "blinding_compromised is set by the experimenter (not this runner) "
                "when a non-label feature unavoidably signals the treatment; the "
                "revealing evidence is flagged, never deleted.",
    }


def _dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    # Gate 2 scorer handoff mandates the receipt pair (fail-closed): both or neither.
    ap.add_argument("--receipt", required=True,
                    help="producer receipt JSON to anonymize (required in handoff mode)")
    ap.add_argument("--receipt-out", required=True,
                    help="anonymized receipt output path (required in handoff mode)")
    a = ap.parse_args()
    marker = a.receipt_out + ".handoff-complete"
    try:
        # (1) reject any input/output path aliasing BEFORE doing anything —
        # --out == --receipt-out silently produced a half set (only the receipt).
        real = {name: os.path.realpath(p) for name, p in
                [("out", a.out), ("receipt_out", a.receipt_out),
                 ("raw", a.raw), ("contract", a.contract), ("receipt", a.receipt)]}
        if real["out"] == real["receipt_out"]:
            raise FormatError("--out and --receipt-out must be distinct paths")
        for outk in ("out", "receipt_out"):
            for ink in ("raw", "contract", "receipt"):
                if real[outk] == real[ink]:
                    raise FormatError(f"--{outk.replace('_','-')} must not alias --{ink}")
        contract = json.loads(open(a.contract, "rb").read())
        validate_contract(contract)
        packet = run(a.contract, a.raw)
        receipt = json.loads(open(a.receipt, "rb").read())
        drop = contract["redaction"].get("receipt_field_drop", ["arm"])
        anon_receipt = anonymize_receipt(receipt, contract["redaction"]["literal_map"], drop)
        for f in drop:
            if f in anon_receipt:
                raise FormatError(f"drop field {f} still present after anonymization")
        anon_receipt["anon_id"] = packet["anon_id"]
        packet_text, receipt_text = _dump(packet), _dump(anon_receipt)
    except FormatError as e:
        print(f"REJECTED (fail-closed): {e}", file=sys.stderr)
        return 2

    # (2) staged publish: write both to temp files, replace into place, then write
    # a completeness marker. A handoff is scorer-acceptable ONLY if all three exist
    # and the marker's sha256 match. On ANY failure, remove every partial output.
    published = []
    try:
        import tempfile
        out_dir = os.path.dirname(os.path.abspath(a.out)) or "."
        rcp_dir = os.path.dirname(os.path.abspath(a.receipt_out)) or "."
        fd1, t1 = tempfile.mkstemp(dir=out_dir); os.close(fd1)
        fd2, t2 = tempfile.mkstemp(dir=rcp_dir); os.close(fd2)
        with open(t1, "w", encoding="utf-8", newline="\n") as f:
            f.write(packet_text)
        with open(t2, "w", encoding="utf-8", newline="\n") as f:
            f.write(receipt_text)
        os.replace(t1, a.out); published.append(a.out)
        os.replace(t2, a.receipt_out); published.append(a.receipt_out)
        marker_obj = {
            "handoff": "gate2-scorer-handoff-set.v1",
            "anon_id": packet["anon_id"],
            "packet_path": os.path.basename(a.out),
            "receipt_path": os.path.basename(a.receipt_out),
            "packet_sha256": sha256_hex(packet_text.encode("utf-8")),
            "receipt_sha256": sha256_hex(receipt_text.encode("utf-8")),
        }
        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write(_dump(marker_obj))
        published.append(marker)
    except Exception as e:
        for p in published + [marker]:
            try:
                os.remove(p)
            except OSError:
                pass
        print(f"REJECTED (fail-closed): publish failed, all outputs removed: {e}", file=sys.stderr)
        return 2
    if contract.get("frozen") is not True:
        print("NOTICE: contract frozen=false (pending owner re-sign) — "
              "NOT Gate-2-authorized; this run is for testing only.", file=sys.stderr)
    print(f"anon_id={packet['anon_id']} redactions={packet['total_redactions']} "
          f"receipt_anonymized(arm dropped, bound to anon_id); handoff set + marker published")
    return 0


if __name__ == "__main__":
    sys.exit(main())
