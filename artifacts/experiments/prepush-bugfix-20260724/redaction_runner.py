#!/usr/bin/env python3
"""Canonical redaction runner for gate2-scorer-handoff.v1.

Answer-safe: operates only on a producer's raw-output.txt. It never reads the
Gate 0 analysis, the fix, or the answer. It redacts ONLY the COMPLETION_CLAIM
section and receipt metadata per the frozen literal map; FIX_DIFF / TEST_LOG /
VALIDATOR_OUTPUT are copied verbatim. It emits a redacted packet with full
provenance so the handoff is auditable and mechanically replayable.

Usage:
    python redaction_runner.py --contract scorer-handoff-contract.json \\
        --raw raw-output.txt --out redacted-packet.json

Section markers in raw-output.txt (exact lines):
    === FIX_DIFF ===
    === TEST_LOG ===
    === VALIDATOR_OUTPUT ===
    === COMPLETION_CLAIM ===
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys

MARKERS = ["=== FIX_DIFF ===", "=== TEST_LOG ===",
           "=== VALIDATOR_OUTPUT ===", "=== COMPLETION_CLAIM ==="]


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def split_sections(raw: str) -> dict[str, str]:
    idx = []
    for m in MARKERS:
        pos = raw.find(m)
        if pos < 0:
            raise SystemExit(f"missing required section marker: {m}")
        idx.append((m, pos))
    idx.sort(key=lambda x: x[1])
    sections = {}
    for i, (m, pos) in enumerate(idx):
        start = pos + len(m)
        end = idx[i + 1][1] if i + 1 < len(idx) else len(raw)
        sections[m.strip("= ").strip()] = raw[start:end]
    return sections


def redact(text: str, rules: list[dict]) -> tuple[str, dict[str, int]]:
    counts = {}
    for r in rules:
        pat, repl = r["pattern"], r["placeholder"]
        text, n = re.subn(pat, repl, text, flags=re.IGNORECASE)
        counts[pat] = counts.get(pat, 0) + n
    return text, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    contract_bytes = open(a.contract, "rb").read()
    contract = json.loads(contract_bytes)
    rules = contract["redaction"]["literal_map"]

    raw_bytes = open(a.raw, "rb").read()
    raw_text = raw_bytes.decode("utf-8")
    sections = split_sections(raw_text)

    # Redaction touches ONLY COMPLETION_CLAIM. Others are verbatim (never redacted).
    redacted_claim, match_counts = redact(sections["COMPLETION_CLAIM"], rules)
    redacted_sections = dict(sections)
    redacted_sections["COMPLETION_CLAIM"] = redacted_claim

    redacted_text = "".join(
        f"{m}{redacted_sections[m.strip('= ').strip()]}" for m in MARKERS
    )
    raw_sha = sha256_hex(raw_bytes)
    anon_id = "OUT-" + raw_sha[:12]

    packet = {
        "schema": "gate2-redacted-packet.v1",
        "anon_id": anon_id,
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
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(packet, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"anon_id={anon_id} redactions={packet['total_redactions']} "
          f"raw_sha256={raw_sha[:12]}.. redacted_sha256={packet['redacted_output_sha256'][:12]}..")
    return 0


if __name__ == "__main__":
    sys.exit(main())
