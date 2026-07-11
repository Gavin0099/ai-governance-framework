# Census Unit Review — Shared Normalizer (2026-07-11)

Unit: `runtime_hooks/adapters/shared_normalizer.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| A prior alias-miss mutation exposed silent loss of gate-relevant input; the report-only unmapped-key signal is a failure-driven correction. No current broad behavioral-effect claim is available. | Medium-high: all four harnesses share aliases/defaults, so a mapping omission weakens downstream visibility. | It intentionally replaces four duplicate normalization implementations; platform files are thin harness stamps. | Metadata exposes source key and unmapped gate-relevant keys to engineers; it is not a plain-language operator explanation. | `keep_observe` |

Evidence: all four platform normalizers delegate to it; parity tests pin equal
normalized output except harness identity; alias-miss mutation contract covers
the report-only blind-spot detector. No claim that all native payload variants
are covered.
