"""Inactive candidate: verify pinned inputs before dispatching frozen v5 bytes."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def checked(root, item):
    relative = Path(item["path"])
    if relative.is_absolute():
        raise ValueError("artifact path must be relative")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("artifact escapes its pinned root")
    expected = item["sha256"]
    if not isinstance(expected, str) or not re.fullmatch(r"[A-F0-9]{64}", expected):
        raise ValueError("expected SHA must be a pinned uppercase SHA-256")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != expected:
        raise ValueError("SHA mismatch: " + item["path"])
    return path, raw


def run(binding):
    try:
        if binding["event"] not in ("stop", "post-tool-use"):
            raise ValueError("unsupported hook event")
        for key in ("delivery_root", "repo_root"):
            if not Path(binding[key]).is_absolute():
                raise ValueError(key + " must be absolute")
        delivery = Path(binding["delivery_root"]).resolve(strict=True)
        repo = Path(binding["repo_root"]).resolve(strict=True)
        handler, code = checked(delivery, binding["handler"])
        checker, _ = checked(repo, binding["checker"])
        contract, _ = checked(repo, binding["contract"])
        raw_stdin = sys.stdin.buffer.read()
        # The child executes a verified in-memory image, not an unchecked reread.
        # A length-prefixed stdin image avoids Windows' command-line size limit.
        # The same buffered stream retains the subsequent untouched Hook payload.
        child = (
            "import sys; p=sys.argv.pop(1); sys.argv[0]=p; "
            "sys.stdout.reconfigure(encoding='utf-8'); "
            "n=int.from_bytes(sys.stdin.buffer.read(8),'big'); "
            "code=sys.stdin.buffer.read(n); "
            "exec(compile(code,p,'exec'),{'__name__':'__main__','__file__':p})"
        )
        process = subprocess.run(
            [sys.executable, "-I", "-B", "-c", child, str(handler),
             "--event", binding["event"], "--repo-root", str(repo),
             "--contract", str(contract.relative_to(repo)),
             "--approved-producer-path", str(checker.relative_to(repo)),
             "--approved-producer-sha256", binding["checker"]["sha256"]],
            input=len(code).to_bytes(8, "big") + code + raw_stdin,
            capture_output=True, cwd=repo, timeout=30,
        )
        if process.returncode != 0:
            raise ValueError("handler exited unsuccessfully: " + str(process.returncode))
        result = json.loads(process.stdout)
        if not isinstance(result, dict):
            raise ValueError("handler response must be an object")
        return result
    except Exception as exc:
        return {"decision": "block", "reason":
                "MEMORY_LAUNCHER_INTEGRITY_ERROR: " + type(exc).__name__ + ": " + str(exc)}
