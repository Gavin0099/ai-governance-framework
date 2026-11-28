"""Raw-byte budget measurements and advisories for root project instructions."""

from __future__ import annotations


# This is the default project_doc_max_bytes, independent of local overrides.
CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES = 32_768

# M4 observed this clipping point in one Antigravity IDE session. It is not a
# universal Antigravity specification or a replacement for the Codex budget.
OBSERVED_ANTIGRAVITY_SESSION_TRUNCATION_BYTES = 23_877


def antigravity_truncation_advisories(payload: bytes) -> list[str]:
    """Return non-blocking warnings about the observed session truncation point.

    This separate, opt-in check leaves the Codex measurement's return shape,
    callers and pass/fail semantics unchanged. Count raw bytes, including any
    BOM and CRLF; an exact-threshold payload has no tail beyond that point.
    """
    size = len(payload)
    if size <= OBSERVED_ANTIGRAVITY_SESSION_TRUNCATION_BYTES:
        return []
    return [
        f"Instruction payload is {size} bytes on disk, exceeding the observed "
        "Antigravity session truncation threshold of "
        f"{OBSERVED_ANTIGRAVITY_SESSION_TRUNCATION_BYTES} bytes; tail instructions "
        "may be omitted. This is an observed session threshold, not a universal "
        f"Antigravity specification. Advisory only; Codex's {CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES}-byte budget "
        "and pass/fail results are unchanged."
    ]


def measure_codex_project_doc(payload: bytes) -> dict[str, object]:
    """Count all on-disk bytes, including BOM and CR, without text decoding.

    Only existing CRLF pairs are normalized for the CRLF estimate, so mixed
    endings cannot double-count CR. An exact-budget file fits in either form.
    """
    on_disk = len(payload)
    lf_only = payload.replace(b"\r\n", b"\n")
    crlf_worst_case = len(lf_only) + lf_only.count(b"\n")
    overflow = max(0, on_disk - CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES)
    crlf_overflow = max(0, crlf_worst_case - CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES)
    return {
        "budget_bytes": CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES,
        "budget_source": "codex_default_project_doc_max_bytes",
        "on_disk_bytes": on_disk,
        "crlf_worst_case_bytes": crlf_worst_case,
        "overflow_bytes": overflow,
        "crlf_worst_case_overflow_bytes": crlf_overflow,
        "over_budget": overflow > 0,
        "over_budget_with_crlf": crlf_overflow > 0,
    }
