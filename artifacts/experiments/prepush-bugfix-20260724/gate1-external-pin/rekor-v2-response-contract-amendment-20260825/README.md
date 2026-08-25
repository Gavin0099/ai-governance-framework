# Rekor v2 response-contract amendment freeze

This immutable pre-run freeze reconciles the observed HTTP 201 response with
the pinned Rekor v2 implementation.  At upstream commit
`69e7f80810e3468a3a656094c5308560d1fd224f`, the server and official Go client
use `201 Created`; the generated OpenAPI still declares 200 and is retained as
a conflicting generated surface rather than the response authority.

The previous authorized execution remains immutable: freeze
`4d68eaf50f7255f4fc3e9b2331d84ee415013ffb` produced terminal SHA-256
`2ca13d0e5149d8b23e879d6e7e8686da2d4f68edd792780032051b6d1b6a8039`
after one POST returned 201.  That attempt may have created a public entry and
must not be repaired or retried.

This executor accepts only the bounded candidate status set `{200, 201}`.  It
always parses the bounded response in memory before selecting a terminal.
`WRITE_PROBE_PASSED` requires checkpoint-signature verification, inclusion
proof verification, and request/body binding.  A fully verified response with
any other status produces
`WRITE_PROBE_UNEXPECTED_STATUS_WITH_VERIFIED_LOCATOR`; locator availability
does not upgrade the response contract to PASS.

Retained evidence is aggregate and digest-only.  Raw response bytes, request
body, signature, public key, canonicalized body, checkpoint envelope, proof
hash array, and normalized proof receipt are never written.  The terminal may
retain the HTTP status, response byte count and digest, hashed log-key ID, and
proof-derived locator fields.

This tranche performs no POST, retry, public append, admission wiring,
randomization, D5 resolution, or A/B/C/D arm execution.  A later execution
requires separate owner authority bound to the reviewed commit.
