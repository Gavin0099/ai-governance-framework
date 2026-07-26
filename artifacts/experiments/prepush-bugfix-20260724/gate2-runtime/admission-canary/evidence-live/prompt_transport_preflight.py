#!/usr/bin/env python3
"""Validate the frozen prompt before an OS-level binary stdin redirect.

This check intentionally does not pipe text through PowerShell.  It proves the
source file is strict, BOM-free UTF-8 and records the exact bytes that the
launcher must redirect to Claude's stdin.  The session-side identity check is a
separate, immediate post-submit check because no session message exists before
submission.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from evidence_io import atomic_write_json


UTF8_BOM = b"\xef\xbb\xbf"


def inspect_prompt(path: str) -> dict:
    raw = Path(path).read_bytes()
    errors: list[str] = []
    if not raw:
        errors.append("prompt is empty")
    if raw.startswith(UTF8_BOM):
        errors.append("prompt begins with a UTF-8 BOM")

    text = None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"prompt is not strict UTF-8: {exc}")

    if text is not None and text.encode("utf-8") != raw:
        errors.append("UTF-8 decode/encode round trip changed the source bytes")

    return {
        "status": "NO-GO" if errors else "GO",
        "prompt_path": path,
        "prompt_bytes": len(raw),
        "prompt_sha256": hashlib.sha256(raw).hexdigest(),
        "utf8_valid": text is not None,
        "utf8_bom": raw.startswith(UTF8_BOM),
        "unicode_codepoints": len(text) if text is not None else None,
        "non_ascii_codepoints": (
            sum(ord(char) > 127 for char in text) if text is not None else None
        ),
        "required_transport": {
            "kind": "os_binary_stdin_redirect",
            "powershell_text_pipeline_forbidden": True,
            "source_bytes_must_be_redirected_unchanged": True,
        },
        "errors": errors,
        "claim_boundary": (
            "This preflight validates the source bytes and transport contract. "
            "Only prompt_identity_check.py can prove what the session received."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    result = inspect_prompt(args.prompt)
    atomic_write_json(args.out, result)
    print(
        f"{result['status']}: {result['prompt_bytes']} bytes, "
        f"sha256={result['prompt_sha256']}"
    )
    for error in result["errors"]:
        print(f"  - {error}")
    return 0 if result["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
