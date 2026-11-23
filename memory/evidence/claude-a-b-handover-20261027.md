# Claude A-to-B handover evidence

Historical acceptance date **2026-10-27**. The original sources are preserved on [PR #259](https://github.com/Gavin0099/ai-governance-framework/pull/259) at [the recorded evidence commit](https://github.com/Gavin0099/ai-governance-framework/commit/70eab0e73bdfa34a72200cc7be913d78cd1e4140). Both the daily record and test receipt identify [framework ba12d21c](https://github.com/Gavin0099/ai-governance-framework/commit/ba12d21c22aa07e7ed016c64abcd2d9bf2122328), the tested revision in the ancestry of main.

| Preserved source | SHA-256 of the original Git blob bytes |
| --- | --- |
| [Daily record](../2026-10-27.md) | 8f616ce5aca9381411e791d9828e1be94c53a13a74f6fbf35abef25425527f48 |
| [Test receipt](../../artifacts/evidence/test-results/step3-acceptance-focused-20261027.json) | 4d7676224faf1362a513748fe833209644cbb1c219e20d4bf0b62ae5bf21041b |
| [Test output](../../artifacts/evidence/test-results/step3-acceptance-focused-20261027.txt) | b26758eabc45bcf5e838ac1a604f20d052b64d359428a6d2f097c3e9ecf57d4f |

The daily record identity is
d60bd6d5ed926e3a2a2dda3614713db84f54c9eed2c5740626b7fc832f50f390. Its status and next action describe the situation at evidence capture.

## What the recorded run observed

- The actual Claude CLI and SessionStart hook established root-bound identities for A and B in disposable Consumer repositories. An operator issued the governance commands.
- R2 recorded A as OWNED at generation 1. B's attempt while A owned the work was rejected. With the generation-1 attestation, A finalized and R2 recorded RELEASED (R1 through R7 in the daily record).
- B then acquired generation 2. A's earlier attestation was rejected for B and B remained OWNED (R8 and R9).
- The model request did not complete successfully in either session. This evidence supports the observed operator-driven lifecycle and ordered handover. Autonomous model delivery and a successful formal closeout by B remain unverified.
- The report-only receipt records exit code 0 for the focused pytest run, with 92 passed in the retained output. The daily record is the source for the native observations.
