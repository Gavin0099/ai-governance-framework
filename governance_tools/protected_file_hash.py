"""Cross-platform hashing for governance baseline integrity files.

Git may materialize the same tracked text as LF or CRLF depending on checkout
configuration.  Baseline hashes therefore normalize line endings to LF before
hashing so a newline-only checkout conversion is not reported as governance
drift.  For repositories that store text blobs with LF, the digest is identical
to hashing the Git blob bytes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_lf_bytes(data: bytes) -> bytes:
    """Return *data* with CRLF and bare CR line endings normalized to LF."""

    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_canonical_lf_bytes(data: bytes) -> str:
    """Return the SHA-256 digest of LF-canonicalized bytes."""

    return hashlib.sha256(canonical_lf_bytes(data)).hexdigest()


def sha256_canonical_lf_file(path: Path) -> str:
    """Return the LF-canonical SHA-256 digest for *path*."""

    return sha256_canonical_lf_bytes(path.read_bytes())


def compatible_worktree_hashes(path: Path) -> set[str]:
    """Return canonical and legacy newline hashes accepted during migration.

    Canonical LF is authoritative for newly written baselines.  Raw and CRLF
    digests keep existing baselines readable until a governed refresh rewrites
    them with the canonical digest.
    """

    raw = path.read_bytes()
    canonical = canonical_lf_bytes(raw)
    crlf = canonical.replace(b"\n", b"\r\n")
    return {
        hashlib.sha256(canonical).hexdigest(),
        hashlib.sha256(raw).hexdigest(),
        hashlib.sha256(crlf).hexdigest(),
    }
