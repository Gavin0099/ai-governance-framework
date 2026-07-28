# Live canary `20260726-180935`

This directory preserves the revision-6/7 boundary run that stopped before
the first tool call. The producer rejected the low-level batch-call
requirement, so the run correctly created **no** `transcript.jsonl` and no
`adapter-log.jsonl`; empty substitutes have not been fabricated.

The files here are byte-exact copies from:

`D:\gate2-live-run-evidence\live-canary-20260726-180935`

The useful terminal evidence is:

- `claude-stream.jsonl` — the producer interaction record;
- `operator-closeout.json` — the operator disposition;
- `batch-request-check.json` — the observed batch-request condition;
- the before/after baseline and prompt-identity preflight artifacts.

Before copying, the selected files were scanned for credential field names.
The only `apiKey` match was Claude metadata with
`apiKeySource: "none"`; no API key, bearer credential, access token, or
refresh token was found.

This archive preserves execution history. It does not turn the stopped run
into a passing admission or a formal Gate 2 arm.
