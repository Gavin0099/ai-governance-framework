"""Raw-byte budget measurements for the root Codex project instructions."""

from __future__ import annotations


# This is the default project_doc_max_bytes, independent of local overrides.
CODEX_PROJECT_DOC_DEFAULT_MAX_BYTES = 32_768


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
