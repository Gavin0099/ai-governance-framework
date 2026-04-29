#!/usr/bin/env python3
"""
Advisory validator for ISR safety patterns.
"""

from governance_tools.validator_interface import DomainValidator, ValidatorResult


class InterruptSafetyValidator(DomainValidator):
    FORBIDDEN_IN_ISR = ["printf", "malloc", "free", "HAL_Delay", "osDelay"]

    @property
    def rule_ids(self) -> list[str]:
        return ["hub-firmware", "HUB-004"]

    def validate(self, payload: dict) -> ValidatorResult:
        isr_code = payload.get("isr_code", "")
        changed_functions = payload.get("changed_functions", [])
        interrupt_functions = payload.get("interrupt_functions", [])
        if not interrupt_functions and not isr_code:
            return ValidatorResult(
                ok=True,
                rule_ids=self.rule_ids,
                evidence_summary="No interrupt-context function changes detected",
                metadata={
                    "mode": "advisory",
                    "changed_functions": changed_functions,
                    "interrupt_functions": interrupt_functions,
                },
            )

        warnings = [
            f"HUB-ISR-001: '{fn}' called inside ISR"
            for fn in self.FORBIDDEN_IN_ISR
            if fn in isr_code
        ]
        return ValidatorResult(
            ok=len(warnings) == 0,
            rule_ids=self.rule_ids,
            warnings=warnings,
            evidence_summary=f"Checked {len(self.FORBIDDEN_IN_ISR)} forbidden patterns in ISR code",
            metadata={
                "mode": "advisory",
                "changed_functions": changed_functions,
                "interrupt_functions": interrupt_functions,
            },
        )
