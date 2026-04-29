# Next.js BYOK Architecture Rules

## BYOK_INGEST_KEY_PROPAGATION

**Category**: cost-safety
**Enforcement**: advisory (promote to hard_stop after 20 evaluations, FP-rate = 0.0)

### What it checks

Any file under `api_route_roots` whose path contains `ingest` and calls
`generateEmbedding()` must also reference a user-provided API key in the
same source unit.

Accepted user-key references:
- `userKey`
- `user.openaiKey` / `user?.openaiKey`
- `user.apiKey` / `user?.apiKey`
- `session?.user` (used as a proxy for session-bound key)
- `{ apiKey: <expr> }` object literal
- `openaiApiKey`

### Why it matters

If `generateEmbedding(text)` is called without a user key, the call uses
`process.env.OPENAI_API_KEY` (the app owner's key).  A user importing
500 diary entries will silently exhaust the app owner's quota at no cost
to themselves.

### False positive guidance

An embedding helper that accepts the key as a parameter and is located
_outside_ `api_route_roots` will not be flagged (path filter excludes it).
If a rate-limiting middleware already injects the key before the route
handler runs, add a triage record with `type: FP` and `root_cause: context`.

---

## ROUTE_RATE_LIMIT_COVERAGE

**Category**: abuse-prevention
**Enforcement**: advisory

### What it checks

Any file under `api_route_roots` that exports a mutation handler
(`POST`, `PUT`, `DELETE`, `PATCH`, or a Pages Router `export default function handler`)
must contain at least one rate-limiting pattern.

Accepted patterns:
- `Ratelimit` / `rateLimit` / `rateLimiter`
- `withRateLimit`
- `limiter.limit` / `limiter.check`
- `status: 429` / `Too Many Requests`

### Why it matters

Mutation routes without rate limits allow a single authenticated user to
trigger unbounded embedding, LLM inference, or database writes, leading to
cost amplification or denial-of-wallet attacks.

### False positive guidance

GET-only routes and read-only handlers are excluded (only mutation verbs
trigger the check).  If rate limiting is applied in a parent middleware layer
(e.g., Next.js middleware.ts), add a triage record with `type: FP` and
`root_cause: context` describing the middleware path.

---

## BUILD_EVIDENCE (informational)

**Category**: build-health
**Enforcement**: advisory (manual, via post_task evidence)

The post-task governance check should include evidence of a clean TypeScript
build (`tsc: 0 errors`) in the `diagnostics` field.  An absent or failing
build diagnostic is a blocking signal for any PR that touches `lib/` or `app/`.

This rule is not implemented as an automated validator (pattern-matching on
TypeScript AST is out of scope).  It is enforced through the post_task
`diagnostics` evidence field review.
