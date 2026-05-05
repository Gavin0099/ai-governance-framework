# Classification Binding Contract v0.1

## Intent

Convert signal classification from static documentation into governed, machine-readable control metadata.

## Core Rule

Signal classification defines how a signal may be consumed, not just what the signal is.

## Machine-Readable Binding Shape

Minimum binding payload:

```json
{
  "signal": "token_count",
  "classification": "non_authoritative",
  "misuse_risk": "low",
  "classification_source": "docs/signal-classification-spec-v0.1.md",
  "classification_version": "v0.1",
  "classification_locked": true
}
```

## Binding Constraints

1. `classification_locked=true` is default.
2. Runtime or per-consumer logic must not override classification.
3. Classification is governance state, not annotation.

## Reclassification Policy

Reclassification requires a separate governance path with all of:
- reviewer confirmation
- explicit rationale
- audit trail
- classification spec version bump

Without all conditions above, reclassification is invalid.

## Override Prohibition

The following are forbidden:
- runtime override by feature flags
- consumer-local override by convenience
- inferred reclassification from usage frequency

## Scope

This contract does not add runtime enforcement behavior.
It governs classification integrity and change control semantics only.
