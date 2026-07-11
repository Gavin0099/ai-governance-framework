# Census Unit Review — Runtime Smoke Test (2026-07-11)

Unit: `runtime_hooks/smoke_test.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| External verification and documented replay use it to establish integration compatibility. That is observed verification use, not evidence that governance altered a natural engineering decision. | Medium: examples, harness normalizers, dispatcher, and override semantics must remain coordinated. | It exercises adapter/dispatcher paths; it is not a duplicate policy engine. | Human output names harness, event, payload, warnings, and required evidence; useful to engineers, not a full adoption explanation. | `keep_observe` |

Evidence: native-example replay coverage for Claude, Codex, Gemini, and Hermes;
external-repo live-verification documentation; focused smoke tests. This does
not prove all harness installations or production event delivery.
