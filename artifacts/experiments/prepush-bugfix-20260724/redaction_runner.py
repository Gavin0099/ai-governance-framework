#!/usr/bin/env python3
"""Canonical redaction runner for gate2-scorer-handoff.v2 (fail-closed).

Answer-safe: operates only on a producer's raw-output.txt. It never reads the
Gate 0 analysis, the fix, or the answer. It redacts ONLY the COMPLETION_CLAIM
section and receipt metadata per the frozen literal map; FIX_DIFF / TEST_LOG /
VALIDATOR_OUTPUT are copied verbatim.

FAIL-CLOSED: rejects out-of-order / duplicate / missing / preamble / CRLF inputs
and any input/output path aliasing. On any publish failure it removes every
partial output AND staging temp. The receipt pair is mandatory.

Usage (produce a handoff set = packet + anonymized receipt + completeness marker):
    python redaction_runner.py --contract scorer-handoff-contract.json \\
        --raw raw-output.txt --out redacted-packet.json \\
        --receipt producer-receipt.json --receipt-out redacted-receipt.json

Verify a handoff set (scorer's mechanical acceptance entry point):
    python redaction_runner.py --verify-handoff redacted-receipt.json.handoff-complete
    (exit 0 = packet + receipt + marker all present and sha256 match; 2 = reject)
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


def verify_handoff(marker_path: str, contract_path: str | None = None) -> int:
    """Scorer's mechanical acceptance: a handoff set is acceptable ONLY if the
    marker + packet + receipt all exist, the marker's sha256 match the files, all
    three anon_ids agree, and (when --contract is given) the packet was produced
    with that exact contract. Returns 0 (accept) or 2 (reject); never raises."""
    try:
        marker = json.loads(open(marker_path, "rb").read())
        if not isinstance(marker, dict):
            raise FormatError("marker must be a JSON object")
        if marker.get("handoff") != "gate2-scorer-handoff-set.v1":
            raise FormatError("marker is not a gate2-scorer-handoff-set.v1")
        base = os.path.dirname(os.path.abspath(marker_path))
        # member paths must be plain basenames in the marker's own directory:
        # no absolute paths, no traversal, no subdirectories.
        for key in ("packet_path", "receipt_path"):
            name = marker[key]
            if (os.path.isabs(name) or os.path.basename(name) != name
                    or name in (".", "..") or not name):
                raise FormatError(f"{key} must be a plain basename in the marker directory")
        pkt = os.path.join(base, marker["packet_path"])
        rcp = os.path.join(base, marker["receipt_path"])
        if os.path.normcase(os.path.realpath(pkt)) == os.path.normcase(os.path.realpath(rcp)):
            raise FormatError("packet and receipt must be distinct files")
        if not (os.path.isfile(pkt) and os.path.isfile(rcp)):
            raise FormatError("packet or receipt file missing")
        pkt_bytes, rcp_bytes = open(pkt, "rb").read(), open(rcp, "rb").read()
        if sha256_hex(pkt_bytes) != marker["packet_sha256"]:
            raise FormatError("packet sha256 mismatch")
        if sha256_hex(rcp_bytes) != marker["receipt_sha256"]:
            raise FormatError("receipt sha256 mismatch")
        packet, receipt = json.loads(pkt_bytes), json.loads(rcp_bytes)
        if not isinstance(packet, dict) or not isinstance(receipt, dict):
            raise FormatError("packet and receipt must be JSON objects")
        if packet.get("schema") != "gate2-redacted-packet.v1":
            raise FormatError("packet is not a gate2-redacted-packet.v1")
        # when the expected contract is supplied, prove the packet was produced
        # with THAT redaction map (internal consistency alone is not enough)
        if contract_path is not None:
            expected = sha256_hex(open(contract_path, "rb").read())
            if packet.get("contract_sha256") != expected:
                raise FormatError("packet contract_sha256 does not match the expected contract")
        # all three anon_ids must agree (the packet's was previously unchecked)
        anon = marker.get("anon_id")
        if not anon:
            raise FormatError("marker has no anon_id")
        if packet.get("anon_id") != anon:
            raise FormatError("packet anon_id does not match marker")
        if receipt.get("anon_id") != anon:
            raise FormatError("receipt anon_id does not match marker")
        # anon_id must actually derive from the recorded raw output hash
        raw_sha = packet.get("raw_output_sha256", "")
        if anon != "OUT-" + raw_sha[:12]:
            raise FormatError("anon_id does not derive from raw_output_sha256")
        # the redacted text must hash to the recorded digest
        if sha256_hex(packet.get("redacted_output", "").encode("utf-8")) != \
                packet.get("redacted_output_sha256"):
            raise FormatError("redacted_output_sha256 does not match redacted_output")
    except (FormatError, KeyError, ValueError, TypeError, OSError) as e:
        print(f"HANDOFF REJECTED: {e}", file=sys.stderr)
        return 2
    print(f"HANDOFF OK: anon_id={marker['anon_id']} packet+receipt+marker consistent")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-handoff", metavar="MARKER",
                    help="scorer mode: verify a handoff set from its completeness marker")
    ap.add_argument("--contract")
    ap.add_argument("--raw")
    ap.add_argument("--out")
    ap.add_argument("--receipt", help="producer receipt JSON to anonymize")
    ap.add_argument("--receipt-out", help="anonymized receipt output path")
    a = ap.parse_args()
    if a.verify_handoff:
        # --contract is optional in verify mode; when given, the packet's
        # contract_sha256 must match it exactly.
        return verify_handoff(a.verify_handoff, a.contract)
    # produce mode: the receipt pair is mandatory (fail-closed): all five required.
    missing = [n for n in ("contract", "raw", "out", "receipt", "receipt_out")
               if getattr(a, n) is None]
    if missing:
        print(f"REJECTED (fail-closed): produce mode requires "
              f"{', '.join('--' + m.replace('_','-') for m in missing)}", file=sys.stderr)
        return 2
    marker = a.receipt_out + ".handoff-complete"
    try:
        # (1) reject ALL path aliasing BEFORE doing anything. This must cover the
        # DERIVED marker path too (--out == <receipt-out>.handoff-complete let the
        # marker overwrite the packet), and must use host path semantics
        # (normcase, so Same.json == same.json on Windows) plus samefile() for
        # paths that already exist (hardlinks / 8.3 names / symlinks).
        members = {"out": a.out, "receipt_out": a.receipt_out, "marker": marker,
                   "raw": a.raw, "contract": a.contract, "receipt": a.receipt}
        outputs, inputs = ("out", "receipt_out", "marker"), ("raw", "contract", "receipt")
        ident = {k: os.path.normcase(os.path.realpath(v)) for k, v in members.items()}

        def _same(k1: str, k2: str) -> bool:
            if ident[k1] == ident[k2]:
                return True
            p1, p2 = members[k1], members[k2]
            if os.path.exists(p1) and os.path.exists(p2):
                try:
                    return os.path.samefile(p1, p2)
                except OSError:
                    return False
            return False

        def _label(k: str) -> str:
            return "<receipt-out>.handoff-complete" if k == "marker" else "--" + k.replace("_", "-")

        for i, k1 in enumerate(outputs):          # outputs pairwise distinct
            for k2 in outputs[i + 1:]:
                if _same(k1, k2):
                    raise FormatError(f"{_label(k1)} and {_label(k2)} must be distinct paths")
        for outk in outputs:                      # no output may clobber an input
            for ink in inputs:
                if _same(outk, ink):
                    raise FormatError(f"{_label(outk)} must not alias {_label(ink)}")
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
    t1 = t2 = None
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
        os.replace(t1, a.out); t1 = None; published.append(a.out)
        os.replace(t2, a.receipt_out); t2 = None; published.append(a.receipt_out)
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
        # remove EVERY partial output: published finals, the marker, AND any
        # staging temp that was not yet consumed by os.replace.
        for p in published + [marker, t1, t2]:
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass
        print(f"REJECTED (fail-closed): publish failed, all outputs+temps removed: {e}", file=sys.stderr)
        return 2
    if contract.get("frozen") is not True:
        print("NOTICE: contract frozen=false (pending owner re-sign) — "
              "NOT Gate-2-authorized; this run is for testing only.", file=sys.stderr)
    print(f"anon_id={packet['anon_id']} redactions={packet['total_redactions']} "
          f"receipt_anonymized(arm dropped, bound to anon_id); handoff set + marker published")
    return 0


if __name__ == "__main__":
    sys.exit(main())
