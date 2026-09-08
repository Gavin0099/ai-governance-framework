# Three-task real Lite benchmark — terminal summary

Result: 0 completed comparisons / 3 BLOCKED. Every task stopped during CONTROL collection. All three CONTROL model processes returned exit 0. No TREATMENT or scorer invocation occurred; no scores were frozen or unblinded.

| Task | CONTROL model time | Oracle | Regression / terminal blocker |
|---|---:|---|---|
| Easy queue-range | 48,969 ms | 12/12 PASS | exit 5, Ran 0 tests, test-count.json absent; FileNotFoundError |
| Medium interval merge | 39,234 ms | NOT RUN | AST admission: Unsupported call |
| Hard dependency cycle | 36,203 ms | NOT RUN | AST admission: Unsupported Python operation |

Read-only context for the receipts: Easy submitted an unconditional unittest.main() at module end. The adapter executes that test module before its host-authored test-count write. Medium test source contains zip and assertIsInstance, outside the current admitted calls/methods. Hard test source contains With/subTest, DictComp and IfExp, outside the admitted subset. These are observed compatibility boundaries, not conclusions about repair correctness or Skill efficacy. No remediation or validation replay was performed.

The whole one-shot benchmark wrapper took 126,375 ms. Three successful model turns, two host Python commands (Easy oracle + regression), zero observed model tool calls, four known runtime warnings per CONTROL model. Exact argv/environment/stdout/stderr are retained in per-task request/result files; raw warnings are preserved unchanged. No automatic adapter retry or manual execution/config/data repair. Monitoring and the initial native execution approval are not counted as manual evaluation intervention; no ChatGPT shutdown or external PowerShell handoff was required.

Failure independence: each subsequent task used a fresh root/context, the same unchanged runtime/Skill identities and its pre-frozen materials; no prior output was added to its prompt. Each task and CONTROL invocation was called once. Later arms of a blocked task were not called.

Claim ceiling: NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY. No quality total, tie, Treatment advantage, generalized Skill efficacy, Formal/counting evidence or average cost reduction is established. Only Easy CONTROL oracle correctness was evaluated. Prior successful single-task Lite result and historical rounds are unchanged.

STOP. No runner/fixture/Skill changes, rescoring, retry, new task, commit or push. Any compatibility repair requires a separate implementation slice; preserve these failed runs unchanged.
