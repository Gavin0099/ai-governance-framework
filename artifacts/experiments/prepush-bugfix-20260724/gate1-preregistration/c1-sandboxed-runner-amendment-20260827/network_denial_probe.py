from __future__ import annotations

import argparse
import ctypes
import json
import os
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable


SCHEMA = "c1-task-network-denial-probe.v1"
TIMEOUT_SECONDS = 1.0


def _attempt(call: Callable[[], object]) -> str:
    try:
        call()
    except OSError:
        return "denied"
    return "reachable"


def _tcp(family: socket.AddressFamily, address: tuple[object, ...]) -> None:
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(TIMEOUT_SECONDS)
        sock.connect(address)


def _dns() -> object:
    return socket.getaddrinfo("example.com", 443, type=socket.SOCK_STREAM)


def _https() -> object:
    request = urllib.request.Request(
        "https://example.com/", headers={"User-Agent": "c1-network-denial-probe/1"}
    )
    return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS).read(1)


def _sandbox_account_class() -> str:
    size = ctypes.c_ulong(256)
    buffer = ctypes.create_unicode_buffer(size.value)
    if os.name == "nt" and ctypes.windll.advapi32.GetUserNameW(buffer, ctypes.byref(size)):
        username = buffer.value
    else:
        username = os.environ.get("USERNAME", "")
    return "offline_sandbox" if username.endswith("CodexSandboxOffline") else "other"


def child_result() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "mode": "child",
        "public_ipv4_tcp": _attempt(
            lambda: _tcp(socket.AF_INET, ("1.1.1.1", 443))
        ),
    }


def parent_result() -> dict[str, object]:
    attempts = {
        "dns": _attempt(_dns),
        "public_ipv4_tcp": _attempt(
            lambda: _tcp(socket.AF_INET, ("1.1.1.1", 443))
        ),
        "https": _attempt(_https),
        "loopback_tcp": _attempt(
            lambda: _tcp(socket.AF_INET, ("127.0.0.1", 9))
        ),
        "private_tcp": _attempt(
            lambda: _tcp(socket.AF_INET, ("10.255.255.1", 9))
        ),
        "link_local_tcp": _attempt(
            lambda: _tcp(socket.AF_INET, ("169.254.169.254", 80))
        ),
    }
    if socket.has_ipv6:
        attempts["public_ipv6_tcp"] = _attempt(
            lambda: _tcp(socket.AF_INET6, ("2606:4700:4700::1111", 443, 0, 0))
        )
    else:
        attempts["public_ipv6_tcp"] = "not_applicable"
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child"],
        check=False,
        capture_output=True,
        timeout=5,
    )
    try:
        child = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        child = {"schema": SCHEMA, "mode": "child", "public_ipv4_tcp": "error"}
    return {
        "schema": SCHEMA,
        "mode": "parent",
        "sandbox_account_class": _sandbox_account_class(),
        "attempts": attempts,
        "child": child,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    value = child_result() if args.child else parent_result()
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    if args.child:
        sys.stdout.buffer.write(payload)
        return 0
    if not args.output:
        parser.error("--output is required for the parent probe")
    Path(args.output).write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
