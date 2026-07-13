# C# / Avalonia Engineer Rule Classification Review

Status: review-only classification packet; first small import executed in
`93b4b28b`

Date: 2026-07-13

Source snapshot: `C:\Users\reiko\Desktop\0709\csharp`

Source grade: owner-commissioned, engineer-provided local snapshot; non-Git and
not consumer-commit-bound

## Decision Summary

The nine files are useful E2 adoption evidence and contain several portable
rules, but they are not suitable for a direct bulk copy into
`governance/rules/csharp/`.

Decision for direct import: `CHANGES_REQUESTED`.

Recommended treatment:

- extract a small portable C# subset;
- move Avalonia-specific rules into the existing `avalonia` pack;
- keep HostBridge, project lifecycle, package, style, and auto-remediation
  authority in the consumer contract;
- reject or rewrite rules that are unsafe, overly broad, or source-incomplete;
- make the first implementation slice only a narrow expansion of
  `governance/rules/csharp/threading.md` and
  `governance/rules/avalonia/ui_thread.md` after owner confirmation.

After owner approval and independent review, the first bounded import was
executed in commit `93b4b28b`. Within framework rule content, it changed only
the two approved rule files; the commit also added this classification packet
and the focused pack-boundary test. No other source rules were imported.
Neither the classification nor that framework commit proves that the source
rules were adopted by a consumer.

## Classification Vocabulary

| Classification | Meaning |
| --- | --- |
| `framework-csharp` | Portable C# rule that can apply across product repositories after wording and evidence review. |
| `framework-avalonia` | Avalonia-specific rule that belongs in the existing `avalonia` pack, not the language-wide `csharp` pack. |
| `consumer-only` | Project architecture, package choice, style, naming, HostBridge detail, or local authority that must stay in a consumer/domain contract. |
| `reject/rewrite` | Unsafe, contradictory, over-broad, duplicate, authority-incomplete, or source-incomplete rule that must not be imported as written. |

Examples, source lists, and explanatory prose inherit the classification of the
rule they support. They are not separate import candidates unless explicitly
listed below.

## Source Manifest

| File | Lines | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `architecture.md` | 15 | 2,341 | `AC6700CDC4AB224D60E1C14F8DCCD0BB05D510983F5C78BF9BC4DACFBE9B76DA` |
| `async.md` | 53 | 4,738 | `C87AC4181F0115250A78C600ACEFA3C7EA6E2DB05677C863205B89F0570D10E7` |
| `coding_conventions.md` | 145 | 10,089 | `58956F97C4B0E3C7C99DACBE380BA99267E7C54AF2C4219897F43033B2C091D9` |
| `exceptions.md` | 162 | 13,941 | `77704E08BFEFF9F6B3E997FA0B5126BDDCD15AF682C275F026C69BDB99EE704D` |
| `lifecycle.md` | 179 | 9,319 | `3B19ECCDF90B72F1427DFDF3FE96838A3519B5389B630F25E1E0B092978AF04B` |
| `logging.md` | 137 | 11,800 | `75F17541F257C5175A98EF418C3DB47D56850BCE487EA03E57C645D78B5769E1` |
| `memory_lifecycle.md` | 46 | 6,626 | `343A22EF40B3C25C7B7E750CAF17A79A2A13088C2E37080228E42EA07979F0DA` |
| `native_boundary.md` | 5 | 263 | `CB95F2CEFC94936BDC8FA731834160715161E0D49E6C619F32A98497B487ACC8` |
| `threading.md` | 8 | 600 | `BE9EA1A52BAE586AFF44864314915EEF32000F5391225B12F92844B367804CFE` |

Total: 9 files, 750 lines, 59,717 bytes.

## Detailed Classification

### `architecture.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| Separate domain/application from infrastructure/presentation | `consumer-only` | Architecture policy is not C#-specific and requires the consumer's adopted boundary model. Do not add it to the language pack. |
| Separation of concerns and explicit dependencies | `consumer-only` | Useful design guidance, but belongs in a consumer architecture contract or a separately scoped common architecture pack. |
| Constructor must not perform blocking I/O, network, database, async wait, or external initialization | `framework-csharp` | Portable principle. Import only as a short rule; remove HostBridge examples and local auto-remediation authority. |
| Constructor may perform fast native-handle allocation | `reject/rewrite` | Too broad without ownership and failure semantics. Native allocation can still fail or establish lifetime obligations. |
| `Initialize` / `Connect` / `Start` must be explicit | `consumer-only` | Public lifecycle API and naming are consumer architecture decisions. |
| Set `_initialized=true` before initialization body (`mark-then-execute`) | `reject/rewrite` | A failing body can leave the object falsely marked initialized and prevent retry or cleanup. A state transition must represent success/failure explicitly. |
| `ctor-forbidden-ops-autoremediate` grants L1 automatic repair | `consumer-only` | The source snapshot contains no authorizing `AGENTS.md`; framework rules cannot manufacture consumer authority. |
| Do not introduce patterns for semantic elegance alone | `consumer-only` | Valid governance posture, but it is already covered by failure-driven governance and is not a C# language rule. |

### `async.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| Prefer async APIs for asynchronous I/O; avoid `.Result` / `.Wait()` in async call chains | `framework-csharp` | Portable and high-value after concise wording. |
| `async void` only at framework event-handler boundaries | `framework-csharp` | Portable; retain the event-handler exception. |
| Preserve async through the call chain | `framework-csharp` | Portable, but must allow explicit synchronous boundaries and legacy adapters. |
| Pass `CancellationToken` through cancelable or long-running operations | `framework-csharp` | Rewrite from universal wording to operation-based cooperative cancellation. |
| Use `CancelAfter` for cooperative timeout; do not block with `Thread.Sleep` / wait handles in async flows | `framework-csharp` | Portable when scoped to async operation timeout. |
| Use `ConfigureAwait(false)` on non-UI library paths | `framework-csharp` | Advisory only; require proof that continuation affinity is not part of the method contract. Do not call it semantics-free. |
| Preserve UI context when the continuation updates Avalonia state | `framework-avalonia` | Belongs in the Avalonia UI-thread rule. |
| DI construction must not contain asynchronous startup side effects | `consumer-only` | The boundary is consumer architecture; the portable constructor rule is classified separately. |
| Escape-hatch ordering for synchronous access to async operations | `consumer-only` | Keep as consumer/legacy guidance; do not normalize sync-over-async in the framework pack. |
| Missing `csharp-async-all-the-way-down.md` reference | `reject/rewrite` | Replace with durable official sources or ship the referenced evidence before import. |

### `coding_conventions.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| `.editorconfig` is canonical | `consumer-only` | Correct ownership model, but each consumer's actual `.editorconfig` must be read. The snapshot does not contain it. |
| Braces, indentation, whitespace, blank lines | `consumer-only` | Style and formatter policy. |
| `var` preferences | `consumer-only` | Style policy. |
| File-scoped namespace and using placement/order | `consumer-only` | Style and target-version policy. |
| `this.` qualification and language keyword preferences | `consumer-only` | Style policy. |
| Expression-bodied member preferences | `consumer-only` | Style policy. |
| Pattern matching, switch-expression, collection-expression preferences | `consumer-only` | Style and language-version policy. |
| Null checks and public API compatibility | `framework-csharp` | Extract only correctness/compatibility rules; leave syntax preference to `.editorconfig`. |
| Explicit access modifiers, readonly fields, naming/capitalization | `consumer-only` | Style/API convention. |
| C# 8-12 syntax warnings and optional syntax | `consumer-only` | Target-framework and analyzer configuration. |
| CA1815, CA1822, CA1806 severities | `consumer-only` | Analyzer severity belongs to the consumer build policy. |
| CA2007 exception for Avalonia UI continuation | `framework-avalonia` | The behavioral distinction is useful; do not import the source's global analyzer severity. |
| Google member ordering and access-level ordering | `consumer-only` | Style/organization preference. |
| Catch only handled exceptions and dispose owned resources | `framework-csharp` | Move to exception/resource rules rather than duplicating in a style document. |
| Missing editorconfig reference document | `reject/rewrite` | Remove the broken local reference or supply a durable source. |

### `exceptions.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| Use exceptions for exceptional failure, not normal control flow | `framework-csharp` | Portable principle. |
| Domain/application/infrastructure exception translation | `consumer-only` | Depends on the consumer's layer model and public error contract. |
| Public exception types are API contracts | `framework-csharp` | Portable compatibility rule. |
| Do not make public members switch between exception/no-exception behavior by option | `framework-csharp` | Portable predictability rule after concise wording. |
| Do not throw from exception filters | `framework-csharp` | Portable runtime rule. |
| Avalonia application unhandled-exception and unobserved-task reporting | `framework-avalonia` | Keep as last-resort observation guidance, not recovery proof. |
| ASP.NET Core handler and ProblemDetails guidance | `consumer-only` | Not applicable to the stated Avalonia consumer and not universal C#. |
| Catch from most-derived to base; no swallowing; use `using` / `await using` | `framework-csharp` | Portable. |
| Catch `OperationCanceledException`; preserve the associated token semantics | `framework-csharp` | Portable after wording review. |
| `throw;` versus `throw ex;`; preserve inner exceptions | `framework-csharp` | Portable. |
| Prefer standard exception types; do not expose CLR-reserved exceptions | `framework-csharp` | Portable, subject to current target-framework API review. |
| Exception filters for conditional handling | `framework-csharp` | Portable. |
| Custom exception inheritance and constructor template | `reject/rewrite` | Recheck against current .NET serialization and API guidance before making it mandatory. |
| Log an exception once at the handling boundary | `framework-csharp` | Useful principle; exact logging layer remains consumer-specific. |
| Missing exception reference document | `reject/rewrite` | Replace with durable official sources or include the referenced review artifact. |

### `lifecycle.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| Mandatory lifecycle verbs by component type | `consumer-only` | Public API/naming policy and migration cost are consumer decisions. |
| Async methods use an `Async` suffix | `framework-csharp` | Portable naming guidance, but renaming an existing API is not automatically mechanical. |
| Automatic L1 renaming authority | `consumer-only` | Requires consumer authorization and compatibility review. |
| All states must use enums | `consumer-only` | State representation depends on protocol, persistence, serialization, and compatibility boundaries. |
| Complex state machines must use Stateless or Appccelerate | `reject/rewrite` | Unjustified mandatory third-party dependency and architecture constraint. |
| Illegal transitions throw `InvalidOperationException` | `consumer-only` | Error behavior is part of the consumer state-machine contract. |
| Dispose/Stop/Close/Disconnect are idempotent | `framework-csharp` | Dispose idempotence is portable; other lifecycle verbs require consumer semantics. |
| Every lifecycle method is state-guarded and failure returns to a safe state | `consumer-only` | Requires a defined state model and rollback contract. |
| Every async method accepts `CancellationToken ct = default` | `reject/rewrite` | Apply only to genuinely cancelable operations; adding an unused token does not create cancellation behavior. |
| All state changes are observable and logged | `consumer-only` | Event/logging contract and data volume are consumer decisions. |
| Shared lifecycle operations name a synchronization strategy | `framework-csharp` | Keep principle-level wording; do not mandate one primitive globally. |
| `async void` only for event handlers | `framework-csharp` | Portable and already aligned with the existing pack. |
| All library/adapter awaits use `ConfigureAwait(false)` and this never changes semantics | `reject/rewrite` | Context affinity is behavioral. Replace with a conditional advisory. |
| All Dispose paths use `Interlocked.Exchange` as an automatic mechanical fix | `reject/rewrite` | Useful in some concurrent designs, but not universal and can alter observable cleanup ordering. |
| Owned async resources use `IAsyncDisposable`; native handles use `SafeHandle` | `framework-csharp` | Portable after ownership wording is made explicit. |
| Connect/Disconnect use a specific `SemaphoreSlim` state-machine implementation | `consumer-only` | Project behavior and concurrency design. |
| Native callback / `GCHandle` lifecycle is L2 | `consumer-only` | HostBridge-specific authority and evidence boundary. |
| HostedService start/stop/scoped-service rules | `consumer-only` | Applies only to Generic Host consumers, not every C# product. |
| Avalonia ViewModel activation/deactivation cancels background work and removes subscriptions | `framework-avalonia` | Useful after decoupling from a specific ViewModel framework. |
| ViewModel must not directly own connections | `consumer-only` | Depends on the adopted application architecture. |
| Use `volatile` or `Interlocked` for all state; never use locks on public methods | `reject/rewrite` | Synchronization must match the invariant; these primitives are not interchangeable universal fixes. |
| Exception mapping table | `consumer-only` | Public failure contract belongs to the consumer API. |
| Prefer `ValueTask` on hot paths | `reject/rewrite` | Requires measured allocation/performance evidence and API-lifetime review. |
| Retry with exponential backoff/jitter | `consumer-only` | Resilience policy requires operation idempotence and consumer-specific limits. |
| No hard-coded connection secrets and no TLS validation bypass | `consumer-only` | Important, but belongs in common security/consumer configuration, not a C# lifecycle pack. |
| Missing lifecycle standard reference | `reject/rewrite` | The named source is not present in the snapshot. |

### `logging.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| Logging abstractions in libraries and provider configuration at the app composition root | `consumer-only` | Assumes Microsoft.Extensions.Logging and a specific DI architecture. |
| Domain/application/infrastructure logger ownership | `consumer-only` | Layer model and dependencies are consumer architecture. |
| Log meaningful boundary events, not every method entry | `consumer-only` | Useful operational guidance, but not a C# language rule. |
| Never check `IsEnabled` before logging | `reject/rewrite` | Too absolute; expensive argument construction and hot paths can require an enabled check or source-generated logging. |
| Log-level definitions and deployment filters | `consumer-only` | Operational policy. |
| Structured message templates; no interpolated log messages | `consumer-only` | Provider/analyzer-dependent; suitable for a consumer logging pack. |
| EventId requirement | `consumer-only` | Operational correlation scheme. |
| Source-generated high-performance logging | `consumer-only` | Performance/toolchain policy requiring measured need. |
| Logging calls must not synchronously block on slow storage | `framework-csharp` | Portable failure-prevention principle after removing provider-specific implementation detail. |
| Record exception objects and log once at the handling boundary | `framework-csharp` | Portable, with consumer-defined redaction and handling boundaries. |
| BeginScope / TraceId / SpanId policy | `consumer-only` | Observability architecture. |
| Provider implementation constraints | `consumer-only` | Only relevant to custom provider authors. |
| Do not log secrets, tokens, passwords, or PII | `consumer-only` | Critical policy, but should live in common security or the consumer's data-classification rules rather than the C# language pack. |
| Missing logging reference documents | `reject/rewrite` | Replace with durable sources or provide the referenced artifacts. |

### `memory_lifecycle.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| Ban every raw `+=` / `-=` event subscription across components | `reject/rewrite` | Over-broad architecture mandate; symmetric lifecycle can be safe. |
| Channels are the default replacement for cross-component events | `consumer-only` | Communication architecture and backpressure policy. |
| Rx / `IObservable<T>` is the alternate replacement | `consumer-only` | External dependency and architecture choice. |
| Event subscriptions require symmetric unsubscription when the source outlives the listener | `framework-csharp` | Portable ownership/lifetime rule. |
| Unsubscription must use the same delegate instance | `framework-csharp` | Portable correctness rule. |
| Long-lived event subscription owners implement deterministic cleanup | `framework-csharp` | Portable after ownership and lifetime scope are explicit. |
| Avalonia weak-event / ViewModel activation guidance | `framework-avalonia` | Keep Avalonia-only wording in the framework pack; CommunityToolkit-specific choices remain consumer-only. |
| CommunityToolkit Messenger selection | `consumer-only` | Package-specific architecture. |
| Avalonia binding, timer, View/ViewModel retention cleanup | `framework-avalonia` | Portable Avalonia lifetime guidance after source verification. |
| Use `using` / `await using` for owned disposable resources | `framework-csharp` | Portable. |
| Wrap unmanaged handles in `SafeHandle` | `framework-csharp` | Portable. |
| HostBridge `GCHandle` callback lifecycle and L2 authority | `consumer-only` | Native consumer-specific rule. |
| Cache/collection size limits and expiration | `consumer-only` | Workload and resource-budget policy. |
| ArrayPool, Span, object pooling, LOH guidance | `consumer-only` | Performance policy requiring measurement and ownership checks. |
| Do not use `GC.Collect()` as a production leak fix | `framework-csharp` | Portable, but diagnostic/test exceptions must remain explicit. |
| dotMemory, PerfView, counter and GC test procedure | `consumer-only` | Consumer validation/tooling procedure. |
| Missing memory-research references | `reject/rewrite` | The three named local research files are absent. |

### `native_boundary.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| Keep native interop behind an adapter/boundary | `framework-csharp` | Already present verbatim in the framework. No import needed. |
| Keep DllImport and native handles out of domain logic | `framework-csharp` | Already present verbatim in the framework. No import needed. |
| Make ownership, disposal, and error translation reviewable | `framework-csharp` | Already present verbatim in the framework. No import needed. |

Source and framework SHA-256 are identical:
`CB95F2CEFC94936BDC8FA731834160715161E0D49E6C619F32A98497B487ACC8`.

### `threading.md`

| Rule or rule cluster | Classification | Review disposition |
| --- | --- | --- |
| UI state mutation occurs on the UI thread or dispatcher boundary | `framework-avalonia` | Already represented in `avalonia/ui_thread.md`; enrich there rather than duplicating in `csharp`. |
| `async void` only at event-handler boundaries | `framework-csharp` | Already represented in the current C# threading rule. |
| Cross-thread shared-state mutation is a correctness/governance issue | `framework-csharp` | Keep as principle-level wording. |
| Every async lifecycle critical section uses `SemaphoreSlim(1,1)` | `reject/rewrite` | Rewrite as conditional async-compatible mutual exclusion; not every operation needs serialization. |
| Shared state must use `volatile` or `Interlocked`; Dispose must use `Interlocked.Exchange` | `reject/rewrite` | These primitives do not replace invariant-specific synchronization and are not universal mechanical fixes. |
| Link all concurrency behavior to consumer `lifecycle.md` | `consumer-only` | The lifecycle file is not accepted as a framework dependency. |

## First Small Import — Executed in `93b4b28b`

After owner approval, the first implementation checkpoint comprised:

- this classification packet;
- `governance/rules/csharp/threading.md`
- `governance/rules/avalonia/ui_thread.md`
- the focused `tests/test_rule_pack_loader.py` assertions needed to lock the
  changed wording and pack boundary

Imported C# additions:

1. When an async operation genuinely requires mutual exclusion, use an
   async-compatible synchronization mechanism; do not hold a monitor/`lock`
   across `await`.
2. Shared mutable state must name the invariant and synchronization strategy;
   `volatile`, `Interlocked`, and locks are not interchangeable universal fixes.

Imported Avalonia additions:

1. Avalonia control access must remain on the UI thread.
2. Use `Post` only when completion is not required; use `InvokeAsync` when the
   caller must observe completion or a result.
3. Avoid unnecessary dispatcher hops when already on the UI thread; use
   `CheckAccess`/`VerifyAccess` or an object dispatcher when appropriate.

The Avalonia candidates align with the official threading model:
<https://docs.avaloniaui.net/docs/app-development/threading>.

The implementation slice did not add lifecycle, logging, exception, memory,
style, HostBridge, package, analyzer-severity, or automatic-remediation rules.
The focused test also locks the pack boundary by requiring Avalonia dispatcher
terms to remain outside the C# pack.

## Why Too Many Rules Are a Problem

### 1. Rule-selection loses meaning

The framework has separate language and framework packs. Putting Avalonia,
HostBridge, logging packages, style, security, lifecycle, and architecture into
`csharp` makes context-aware selection ineffective: selecting C# silently
selects unrelated project policy too.

### 2. High-salience safety rules compete with low-value preferences

Rare but consequential constraints such as UI-thread affinity, native ownership,
and exception preservation become harder to notice when mixed with member
ordering, blank lines, naming preferences, and package choices. More text does
not prove more compliance.

### 3. Contradictions and authority leakage increase

Global rules can conflict with consumer `.editorconfig`, architecture, public
API compatibility, UI continuation semantics, or local approval levels. A
framework pack must not grant L1 auto-remediation that only a consumer
`AGENTS.md` can authorize.

### 4. False positives create governance bypass pressure

Universal requirements such as a token on every async method, a specific state
machine library, or `SemaphoreSlim` on every lifecycle method flag legitimate
code. Repeated low-value warnings train operators to ignore the pack, including
its real safety signals.

### 5. Validation debt grows faster than rule count

Each mandatory rule needs scope, exceptions, examples, failure cases, ownership,
and a review/test seam. Importing 750 lines without those boundaries creates a
large claim surface with little enforceable or reproducible evidence.

### 6. Consumer upgrades become semantically expensive

Changing one global C# pack changes the guidance seen by every adopted C#
product. A local HostBridge decision can therefore become an unintended fleet
policy change.

### 7. Payload and review cost increase

`rule_pack_loader.py` reads every `*.md` file in the selected pack. L2 uses the
Tier 3 output path, which preserves full rule content in `active_rules`. The
source snapshot would add 59,717 bytes before other active packs and task
context. This is a runtime/reviewer payload increase, not proof that a model
read, understood, or obeyed every rule.

### 8. Root-cause attribution becomes weaker

When agent behavior changes under a large mixed pack, reviewers cannot easily
tell whether the cause was threading, lifecycle, style, package guidance, or an
authority conflict. Small pack-specific slices preserve observable causality and
rollback clarity.

### 9. Staleness and broken-source risk increase

The snapshot refers to missing `.editorconfig`, `AGENTS.md`, `TESTING.md`, and
multiple absent local reference documents. Bulk import would convert those
missing dependencies into framework-wide ambiguity.

### 10. Adoption readability regresses

The E2 observation already showed that an engineer could not tell what was
installed or complete. A large undifferentiated pack makes that failure mode
worse unless each rule's ownership, activation, and claim ceiling are visible.

## Technical Source Checks

- Microsoft states that CA2007 is generally suppressible for application code
  and that UI continuations commonly should return to their original context:
  <https://learn.microsoft.com/dotnet/fundamentals/code-analysis/quality-rules/ca2007>.
- Microsoft defines cancellation as cooperative behavior by a cancelable
  operation/listener, not as a signature-only property:
  <https://learn.microsoft.com/dotnet/standard/threading/cancellation-in-managed-threads>.
- Microsoft requires idempotent Dispose behavior and recommends `SafeHandle`
  for unmanaged handles:
  <https://learn.microsoft.com/dotnet/standard/garbage-collection/implementing-dispose>.
- Avalonia requires UI access on the UI thread and distinguishes `Post`,
  `InvokeAsync`, `CheckAccess`, and object dispatchers:
  <https://docs.avaloniaui.net/docs/app-development/threading>.

## Claim Ceiling

Can claim:

- the owner commissioned an engineer to provide this local rule snapshot;
- all nine source files were inventoried and classified;
- portable C#, Avalonia, consumer-only, and reject/rewrite boundaries are
  explicitly proposed;
- `native_boundary.md` is already identical to the framework copy;
- the owner approved the two-file first import, commit `93b4b28b` executed it,
  and focused rule-loader assertions cover the C# / Avalonia pack boundary.

Cannot claim:

- any source rule was adopted, enforced, or tested in the consumer repository;
- the source snapshot is commit-bound or author-attributed by Git evidence;
- all source rules are technically correct;
- all portable candidates should be imported;
- adding more rules improves agent correctness, delivery, or governance effect;
- the unnamed consumer loaded or followed the imported framework rules.

## Follow-Up State

The first small import is closed at `93b4b28b`. No additional rule import is
approved by this packet. Remaining E2 work belongs to the retrospective
adoption evidence chain: consumer identity or stable anonymized identifier,
the associated F-7 artifact, owner intervention count, consumer-local binding
of the nine-file snapshot, and a second independent onboarding record.
