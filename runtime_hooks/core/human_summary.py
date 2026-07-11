#!/usr/bin/env python3
"""
Shared helpers for compact reviewer-first human summaries.
"""

from __future__ import annotations

from governance_tools.human_summary import build_summary_line


def format_contract_summary_label(contract_label: str | None, risk_tier: str | None) -> str | None:
    if not contract_label:
        return None
    if risk_tier and risk_tier != "unknown":
        return f"{contract_label}/{risk_tier}"
    return contract_label
