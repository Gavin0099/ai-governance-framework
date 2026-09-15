"""Bounded adapter for Lenovo's committed install-time composition, not a plugin API.

Declaration/wiring/fragment fingerprints are from consumer commit
3a4278c4bd2a18548b4920f2e999372be1834d44. Never execute consumer installers.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile


DECLARATION = "scripts/hooks/install-governance-hooks.ps1"
WIRE = "wire-pre-push-memory-quality.ps1"
FRAGMENT = "scripts/hooks/pre-push.memory-quality.fragment.sh"
GATE = "validate-memory-quality.ps1"
FINGERPRINTS = {
    DECLARATION: "1769131bc7994f7883acd443dc5606cb243cb6c4831a0fd5bb0002ca289f4227",
    WIRE: "2b66d6b9a716f7290e10dc655a5cc843837af2b34527a2d593797ba3de50f685",
    FRAGMENT: "c24d1cd2d3c99b9a4e1de04de8db4c5031a5ec728bf4a11189a5006704ad3e85",
}
MARKER = b"# BEGIN LENOVO_ISP_MEMORY_QUALITY_GATE"
ANCHOR = b"# Fail-closed structured memory freshness gate."


class CompositionError(ValueError):
    pass


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _regular_source(repo: Path, relative: str) -> bytes:
    path = repo / relative
    if not path.resolve().is_relative_to(repo.resolve()) or not stat.S_ISREG(path.lstat().st_mode):
        raise CompositionError(f"composition source must be a regular in-repo file: {relative}")
    return normalized(path.read_bytes())


def _committed_source(repo: Path, relative: str) -> bytes:
    """HEAD, index and worktree must agree; a dirty declaration is not authority."""
    work = _regular_source(repo, relative)
    for revision in ("HEAD:", ":"):
        result = subprocess.run(
            ["git", "-C", str(repo), "show", revision + relative],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if result.returncode or normalized(result.stdout) != work:
            raise CompositionError(f"composition source missing, uncommitted or dirty: {relative}")
    return work


def declared_fragment(repo: Path) -> bytes | None:
    """Recognize only the existing tracked Lenovo profile. Partial profiles fail."""
    known_installer = False
    if (repo / DECLARATION).is_file():
        known_installer = hashlib.sha256(normalized((repo / DECLARATION).read_bytes())).hexdigest() == FINGERPRINTS[DECLARATION]
    if not known_installer and not (repo / WIRE).exists() and not (repo / FRAGMENT).exists():
        return None
    try:
        sources = {name: _committed_source(repo, name) for name in FINGERPRINTS}
        for name, data in sources.items():
            if hashlib.sha256(data).hexdigest() != FINGERPRINTS[name]:
                raise CompositionError(f"unsupported composition declaration revision: {name}")
        _committed_source(repo, GATE)
    except OSError as exc:
        raise CompositionError(f"incomplete composition declaration: {exc}") from exc
    return sources[FRAGMENT]


def compose(base: bytes, fragment: bytes) -> bytes:
    """Reproduce the declared insertion, rejecting ambiguous base layouts."""
    base = normalized(base)
    if MARKER in base:
        raise CompositionError("framework base already contains the consumer extension")
    if base.count(ANCHOR) == 1:
        return base.replace(ANCHOR, fragment + ANCHOR, 1)
    if ANCHOR in base:
        raise CompositionError("ambiguous framework memory-gate anchor")
    # The tracked wiring has a last-exit fallback. Only a standalone terminal
    # exit is admitted here, not a substring inside another shell expression.
    if base.rstrip().endswith(b"\nexit 0"):
        offset = base.rfind(b"exit 0")
        return base[:offset] + fragment.rstrip() + b"\n\n" + base[offset:]
    raise CompositionError("no supported composition insertion point in framework base")


def expected_hook(repo: Path, name: str, base: bytes) -> bytes:
    if name != "pre-push":
        return base
    fragment = declared_fragment(repo)
    return compose(base, fragment) if fragment is not None else base


def matches_prior_composition(framework: Path, installed: bytes, fragment: bytes) -> bool:
    """Admit exact compositions from this checkout's reachable hook history.

    No arbitrary refs, consumer-supplied base, or marker-only comparison. A
    source archive or shallow checkout without the old blob cannot prove it.
    The caller must have validated the committed consumer declaration first.
    """
    def git(*args: str) -> bytes:
        return subprocess.run(
            ["git", "-C", str(framework), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        ).stdout

    try:
        root = Path(os.fsdecode(git("rev-parse", "--show-toplevel")).strip())
        if root.resolve() != framework.resolve():
            return False
        revisions = git("log", "--format=%H", "HEAD", "--", "scripts/hooks/pre-push").splitlines()
        for revision in revisions:
            base = git("show", revision.decode("ascii") + ":scripts/hooks/pre-push")
            try:
                if normalized(installed) == compose(base, fragment):
                    return True
            except CompositionError:
                continue
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return False


def atomic_write_hook(path: Path, payload: bytes) -> bool:
    """Prepare the complete hook beside the target, then replace once.

    Never publish an intermediate raw hook. A failed write/chmod/replace keeps
    the old hook. This is a per-file guarantee, not an installer transaction.
    """
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o755
    fd, temporary = tempfile.mkstemp(prefix=".governance-hook-", dir=path.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            temp.chmod(mode | 0o111)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return True
