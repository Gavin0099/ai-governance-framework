"""
Tests for governance_tools/exclusion_registry_tool.py — E2 exclusion governance.

Coverage strategy
-----------------
- load_registry parses all entries correctly
- generate_filter produces a valid -k expression from active entries
- inactive entries are excluded from filter
- expired entries appear in audit result
- integrity violations (missing justification, owner, expiry) are caught
- audit ok=True when registry is clean
- validate returns ok when clean
- ExclusionEntry.is_expired() boundary cases
"""

from __future__ import annotations

import textwrap
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from governance_tools.exclusion_registry_tool import (
    ExclusionEntry,
    load_registry,
    generate_filter,
    audit_registry,
)

# Path to the real registry
REAL_REGISTRY = Path(__file__).parent.parent / "governance" / "test_exclusion_registry.yaml"


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_entry(
    id="EX-TEST",
    pattern="some_pattern",
    failure_kind="external_exclusion",
    justification="valid justification",
    owner="Test",
    expiry=None,
    revalidation_trigger="when fixed",
    active=True,
) -> ExclusionEntry:
    if expiry is None:
        expiry = (date.today() + timedelta(days=180)).strftime("%Y-%m-%d")
    return ExclusionEntry(
        id=id,
        pattern=pattern,
        scope="test_name_contains",
        failure_kind=failure_kind,
        justification=justification,
        owner=owner,
        added_at="2026-04-10",
        expiry=expiry,
        revalidation_trigger=revalidation_trigger,
        active=active,
    )


# ── Real registry loads without error ────────────────────────────────────────

def test_real_registry_loads():
    entries = load_registry(REAL_REGISTRY)
    assert len(entries) >= 9, "Expected at least 9 entries in the real registry"


def test_real_registry_all_have_id():
    entries = load_registry(REAL_REGISTRY)
    for e in entries:
        assert e.id, f"Entry missing id: {e}"


def test_real_registry_all_have_justification():
    entries = load_registry(REAL_REGISTRY)
    for e in entries:
        assert e.justification.strip(), f"Entry {e.id} missing justification"


def test_real_registry_all_have_owner():
    entries = load_registry(REAL_REGISTRY)
    for e in entries:
        assert e.owner.strip(), f"Entry {e.id} missing owner"


def test_real_registry_audit_passes():
    """The real registry must pass integrity checks on commit."""
    entries = load_registry(REAL_REGISTRY)
    result = audit_registry(entries)
    assert result.ok, (
        f"Real exclusion registry has integrity issues:\n"
        f"  expired={result.expired}\n"
        f"  missing_justification={result.missing_justification}\n"
        f"  missing_owner={result.missing_owner}\n"
        f"  integrity_errors={result.integrity_errors}"
    )


# ── generate_filter ───────────────────────────────────────────────────────────

def test_generate_filter_includes_active_patterns():
    entries = [
        _make_entry(id="EX-A", pattern="trust_signal"),
        _make_entry(id="EX-B", pattern="reviewer_handoff"),
    ]
    k = generate_filter(entries, warn_expired=False)
    assert "trust_signal" in k
    assert "reviewer_handoff" in k


def test_generate_filter_excludes_inactive():
    entries = [
        _make_entry(id="EX-A", pattern="trust_signal", active=True),
        _make_entry(id="EX-B", pattern="inactive_pattern", active=False),
    ]
    k = generate_filter(entries, warn_expired=False)
    assert "inactive_pattern" not in k


def test_generate_filter_empty_when_no_active():
    entries = [_make_entry(active=False)]
    k = generate_filter(entries, warn_expired=False)
    assert k == ""


def test_generate_filter_uses_not_prefix():
    entries = [_make_entry(pattern="some_test")]
    k = generate_filter(entries, warn_expired=False)
    assert k.startswith("not ")


def test_real_registry_generates_non_empty_filter():
    entries = load_registry(REAL_REGISTRY)
    k = generate_filter(entries, warn_expired=False)
    assert k, "Real registry should produce a non-empty k expression"
    assert "trust_signal" in k


# ── audit_registry ────────────────────────────────────────────────────────────

def test_audit_ok_when_all_entries_valid():
    entries = [
        _make_entry(id="EX-A"),
        _make_entry(id="EX-B", pattern="reviewer_handoff"),
    ]
    result = audit_registry(entries)
    assert result.ok
    assert result.expired == []
    assert result.missing_justification == []
    assert result.missing_owner == []


def test_audit_detects_expired_entry():
    past = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    entries = [_make_entry(id="EX-EXPIRED", expiry=past)]
    result = audit_registry(entries)
    assert "EX-EXPIRED" in result.expired
    assert result.ok is False


def test_audit_detects_missing_justification():
    entries = [_make_entry(id="EX-NOJUST", justification="")]
    result = audit_registry(entries)
    assert "EX-NOJUST" in result.missing_justification
    assert result.ok is False


def test_audit_detects_missing_owner():
    entries = [_make_entry(id="EX-NOOWN", owner="")]
    result = audit_registry(entries)
    assert "EX-NOOWN" in result.missing_owner
    assert result.ok is False


def test_audit_counts_active_inactive():
    entries = [
        _make_entry(id="EX-A", active=True),
        _make_entry(id="EX-B", active=False),
        _make_entry(id="EX-C", active=True),
    ]
    result = audit_registry(entries)
    assert result.active == 2
    assert result.inactive == 1
    assert result.total == 3


# ── ExclusionEntry.is_expired ─────────────────────────────────────────────────

def test_entry_not_expired_future_date():
    future = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    e = _make_entry(expiry=future)
    assert e.is_expired() is False


def test_entry_expired_past_date():
    past = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    e = _make_entry(expiry=past)
    assert e.is_expired() is True


def test_entry_not_expired_today():
    today = date.today().strftime("%Y-%m-%d")
    e = _make_entry(expiry=today)
    # today == expiry: not yet expired
    assert e.is_expired() is False


def test_entry_unparseable_expiry_is_not_expired():
    e = _make_entry(expiry="not-a-date")
    # should not crash, returns False
    assert e.is_expired() is False


# ── integrity_errors ──────────────────────────────────────────────────────────

def test_integrity_errors_empty_for_valid_entry():
    e = _make_entry()
    assert e.integrity_errors() == []


def test_integrity_errors_detects_missing_justification():
    e = _make_entry(justification="")
    assert "missing justification" in e.integrity_errors()


def test_integrity_errors_detects_missing_owner():
    e = _make_entry(owner="")
    assert "missing owner" in e.integrity_errors()


def test_integrity_errors_detects_missing_revalidation_trigger():
    e = _make_entry(revalidation_trigger="")
    assert "missing revalidation_trigger" in e.integrity_errors()
