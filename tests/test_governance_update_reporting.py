from __future__ import annotations

from governance_tools.governance_update_reporting import (
    build_ai_governance_update_result,
    build_final_report_requirement,
    format_ai_governance_update_result,
)


def _maturity_summary(
    *,
    status: str,
    lock: str = "consistent",
    missing: list[str] | None = None,
    rows: list[str] | None = None,
) -> dict[str, object]:
    return {
        "report_only": True,
        "user_facing_status": {"value": status},
        "lock_consistency": {"value": lock},
        "missing_surfaces": list(missing or []),
        "human_readable_adoption_summary": rows
        if rows is not None
        else [
            "[human_readable_adoption_summary]",
            "| Feature | Status | Meaning |",
            "| --- | --- | --- |",
            "| Repo governance instructions | available | Agents can read repo rules. |",
        ],
        "cannot_claim": ["full governance adoption"],
    }


def test_operator_report_for_updated_payload_has_repo_owner_decision_fields() -> None:
    maturity = _maturity_summary(status="full_candidate")
    requirement = build_final_report_requirement(maturity)

    payload = build_ai_governance_update_result(
        framework_update_status="updated",
        framework_update_source="f7_full_update",
        governance_maturity_summary=maturity,
        final_report_requirement=requirement,
        evidence_refs=[{"kind": "receipt", "path": "artifacts/update.json"}],
        cannot_claim=["domain correctness"],
    )

    report = payload["operator_facing_report"]
    assert report["report_only"] is True
    assert report["repo_update_state"] == "updated"
    assert report["adoption_status"] == "full_candidate"
    assert "full candidate" in report["operator_decision_summary"]
    assert "runtime enforcement" in report["highest_trust_claim"]
    assert report["blocking_or_attention_items"] == []
    assert report["evidence_refs"] == [{"kind": "receipt", "path": "artifacts/update.json"}]
    assert report["next_action"] == "Proceed with normal governed work within the listed non-claims."
    assert "domain correctness" in report["cannot_claim"]
    assert "full governance adoption" in report["cannot_claim"]

    rendered = "\n".join(format_ai_governance_update_result(payload))
    assert "[operator_facing_report]" in rendered
    assert "repo_update_state=updated" in rendered
    assert "operator_decision_summary=Visible AI Governance surfaces are present" in rendered


def test_operator_report_for_partial_payload_surfaces_missing_items() -> None:
    maturity = _maturity_summary(
        status="partial",
        lock="consistent",
        missing=["validator_surface", "runtime_self_contained_governance"],
    )
    requirement = build_final_report_requirement(maturity)

    payload = build_ai_governance_update_result(
        framework_update_status="already_current",
        framework_update_source="updater",
        governance_maturity_summary=maturity,
        final_report_requirement=requirement,
    )

    report = payload["operator_facing_report"]
    assert report["repo_update_state"] == "already_current"
    assert report["adoption_status"] == "partial"
    assert "missing or unverified surfaces" in report["operator_decision_summary"]
    assert report["blocking_or_attention_items"] == [
        "validator_surface",
        "runtime_self_contained_governance",
    ]
    assert report["next_action"] == (
        "Fix the highest-impact missing surface, or record why it is intentionally out of scope."
    )

    rendered = "\n".join(format_ai_governance_update_result(payload))
    assert "blocking_or_attention_items:" in rendered
    assert "- validator_surface" in rendered


def test_operator_report_for_manual_update_inconsistent_payload_downgrades_claim() -> None:
    maturity = _maturity_summary(
        status="unknown",
        lock="inconsistent",
        missing=["framework_lock_consistency"],
        rows=[],
    )
    requirement = build_final_report_requirement(maturity)

    payload = build_ai_governance_update_result(
        framework_update_status="manual_update",
        framework_update_source="manual_update_advisory",
        governance_maturity_summary=maturity,
        final_report_requirement=requirement,
        cannot_claim=["completed AI Governance update"],
    )

    report = payload["operator_facing_report"]
    assert report["repo_update_state"] == "manual_update"
    assert report["adoption_status"] == "unknown"
    assert "not verified" in report["operator_decision_summary"]
    assert "completed governed update is not proven" in report["highest_trust_claim"]
    assert report["blocking_or_attention_items"] == [
        "manual update path observed; governed updater/F-7 evidence is missing",
        "lock-vs-checkout consistency is inconsistent",
        "operator-facing adoption table was not reported",
        "framework_lock_consistency",
        "adoption status is unknown",
    ]
    assert report["next_action"] == (
        "Run the governed updater/F-7 path, or report manual_update with the missing evidence explicitly."
    )
    assert "completed AI Governance update" in report["cannot_claim"]

    rendered = "\n".join(format_ai_governance_update_result(payload))
    assert "repo_update_state=manual_update" in rendered
    assert "lock-vs-checkout consistency is inconsistent" in rendered
