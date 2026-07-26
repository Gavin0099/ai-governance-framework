#!/usr/bin/env python3
"""Snapshot the canary workspace to a JSON artifact, before and after a run.

The workspace state was previously reported in conversation, which a reviewer
without Docker cannot check and should not have to take on trust. This writes it
down: container identity, image digest, HEAD, porcelain status, the digest of
every tracked file, and the contents of /work/out.

    python capture_baseline.py --out D:/gate2-live-run-evidence/baseline-before.json

It talks to Docker directly rather than through the adapter, because it is the
host operator's record, not a producer action -- routing it through the adapter
would add lines to the very log it is supposed to describe.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone

from evidence_io import atomic_write_json

CONTAINER = os.environ.get("GATE2_CANARY_CONTAINER", "gate2-admission-canary")


def run(argv: list[str]) -> tuple[int, str]:
    cp = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        env={**os.environ, "MSYS_NO_PATHCONV": "1"})
    return cp.returncode, cp.stdout.decode("utf-8", "replace").strip()


def dexec(argv: list[str], workdir: str = "/work/repo") -> tuple[int, str]:
    return run(["docker", "exec", "-u", "65532:65532", "-e", "HOME=/work", "-w", workdir,
                CONTAINER] + argv)


def collect_out_artifacts(names: list[str]) -> dict:
    artifacts = {}
    for name in names:
        target = f"/work/out/{name}"
        sha_rc, sha_line = dexec(["sha256sum", target], workdir="/work")
        size_rc, size_line = dexec(["wc", "-c", target], workdir="/work")
        text_rc, text = dexec(["cat", target], workdir="/work")
        try:
            size = int(size_line.split()[0]) if size_rc == 0 else None
        except (IndexError, ValueError):
            size = None
        parsed_json = None
        if text_rc == 0:
            try:
                parsed_json = json.loads(text)
            except json.JSONDecodeError:
                pass
        artifacts[name] = {
            "bytes": size,
            "sha256": (
                sha_line.split()[0] if sha_rc == 0 and sha_line else None
            ),
            "utf8_text_trimmed": text if text_rc == 0 else None,
            "parsed_json": parsed_json,
        }
    return artifacts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="baseline")
    args = ap.parse_args()

    rc_state, state = run(["docker", "inspect", "-f", "{{.State.Status}}", CONTAINER])
    _, image = run(["docker", "inspect", "-f", "{{.Image}}", CONTAINER])
    _, cid = run(["docker", "inspect", "-f", "{{.Id}}", CONTAINER])
    _, head = dexec(["git", "log", "--oneline", "-1"])
    rc_status, status = dexec(["git", "status", "--porcelain"])
    _, files = dexec(["git", "ls-files"])
    _, out_dir = dexec(["ls", "-A", "/work/out"], workdir="/work")

    digests = {}
    for path in [f for f in files.splitlines() if f.strip()]:
        rc, line = dexec(["sha256sum", path])
        digests[path] = line.split()[0] if rc == 0 and line else f"<error: {line}>"

    out_names = [f for f in out_dir.splitlines() if f.strip()]
    out_artifacts = collect_out_artifacts(out_names)

    record = {
        "label": args.label,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "container": {"name": CONTAINER, "id": cid, "state": state, "image": image,
                      "reachable": rc_state == 0},
        "repo": {
            "head": head,
            "status_porcelain": status,
            "clean": rc_status == 0 and status == "",
            "tracked_files": sorted(digests),
            "file_sha256": digests,
        },
        "work_out": out_names,
        "work_out_artifacts": out_artifacts,
    }

    atomic_write_json(args.out, record)

    print(f"wrote {args.out}")
    print(f"  container : {CONTAINER} ({state})")
    print(f"  HEAD      : {head}")
    print(f"  clean     : {record['repo']['clean']}"
          + ("" if record["repo"]["clean"] else f"  <-- {status!r}"))
    print(f"  /work/out : {record['work_out'] or 'empty'}")
    for path in ("src/calc.py", "tests/test_calc.py"):
        if path in digests:
            print(f"  {path:<18}: {digests[path][:16]}...")
    return 0 if record["container"]["reachable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
