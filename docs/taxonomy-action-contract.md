# Taxonomy Expansion Signal — Action Contract

> **Scope:** `failure_disposition.taxonomy_expansion_signal` in
> `governance_tools/failure_disposition.py`.  This note defines what the signal
> means, when it fires, and what the prescribed operator response is.  It does
> not restrict how the signal is consumed downstream.

---

## What the signal is

`taxonomy_expansion_signal` is a Boolean field on `BatchDispositionResult`.  It
fires when the number of unclassifiable ("unknown") test failures in a batch
meets or exceeds `unknown_threshold`.

```
taxonomy_expansion_signal = (unknown_count >= unknown_threshold)
```

Both `unknown_count` and `unknown_threshold` are present in the serialised
artifact (`BatchDispositionResult.to_dict()`), so a reviewer can verify the
judgment basis without reading source code.

Current default: `unknown_threshold = 3` (defined as
`UNKNOWN_ESCALATION_THRESHOLD` in `failure_disposition.py`).

---

## What it does NOT mean

- It does **not** block the gate by itself.  The signal is advisory and auditable
  only; gate blocking is determined by `verdict_blocked`, which fires on
  `production_fix_required` and `escalate` actions, not on `unknown` count alone.
- It does **not** imply that the unknown failures are regressions.  They may be
  new test IDs that simply have no classification pattern yet.
- It does **not** mean the classifier is broken.  A high unknown count in a new
  repo is expected when the failure taxonomy has not been seeded.

---

## Prescribed operator response

When `taxonomy_expansion_signal = True`:

1. **Inspect the unknown failures.**
   - Are the test IDs genuinely new failure modes, or are they aliased forms of
     known patterns?
   - If the IDs match a known pattern but the classifier missed them, fix the
     classification pattern in `_CLASSIFICATION_RULES`
     (`failure_disposition.py`).

2. **If genuinely new failure modes are confirmed:**
   - Add representative corpus entries to
     `governance/data/failure_disposition_corpus.json`.
   - Add or extend classification rules in `_CLASSIFICATION_RULES`.
   - Re-run the corpus calibration test
     (`test_corpus_case_classifies_correctly`) to verify new rules do not
     regress existing classification.

3. **Until the taxonomy is updated:**
   - The signal remains advisory.  Do not escalate to gate block based on
     `taxonomy_expansion_signal` alone.
   - Log the signal as a `taxonomy_maintenance` backlog item.  The signal is
     a *required review* trigger, not an immediate stop.

4. **Do not suppress the unknown count** by widening existing classification
   patterns beyond their documented scope.  A tight classifier with visible
   unknowns is safer than a loose classifier that silently absorbs misclassified
   failures.

---

## Artifact observability

The gate warning string (emitted by `gate_policy._add_advisory_warnings()`) and
the ingestor warning string (emitted by `test_result_ingestor._apply_failure_disposition()`)
both include the threshold value:

```
[gate_policy:signal] taxonomy_expansion_signal: 4 unknown failures >= escalation threshold (3)
[failure_disposition] taxonomy_expansion_signal: 4 unknown failures >= threshold (3)
```

This ensures the reviewer always sees both the observed count and the threshold
that triggered the signal, without needing to open source code.

---

## Tuning the threshold

The threshold is a single integer constant.  Raising it reduces signal noise at
the cost of later detection; lowering it increases sensitivity.

Do **not** tune the threshold to silence a specific run.  Adjust it only when
there is evidence that the default produces consistent false positives across
multiple repos or across repeated runs of the same repo.  Any threshold change
should be accompanied by a note in this file explaining the evidence basis.
