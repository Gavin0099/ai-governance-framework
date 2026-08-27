# C1 NEW_EXPERIMENT_COHORT amendment freeze

This directory freezes the owner-selected general rule for closing an
infrastructure-invalid execution cohort before any outcome-bearing unit becomes
observable. It preserves the original preregistration decisions and binds the
two prior C1 attempts without copying the private mapping reveal.

The new cohort identity is `C1-skill-primary-cohort-02`. No pair identity,
randomization record, mapping, nonce, producer output, scorer judgment, or
evidence-chain event is created here.

The amendment is eligible only because the bounded prior-evidence inventory
proves zero producer dispatches, zero sealed outcomes, zero scorer submissions,
and no mapping release. Any one of those observations makes reset ineligible.

The original D1-D7 decision packet, decision rules, attempt-06 quarantine, and
claim ceiling remain immutable through exact source bindings and field-by-field
validation. A future admission surface must resolve
`governing_rule_decision_commit` from the exact reviewed executing freeze
commit; this directory cannot self-reference its own Git commit SHA.

Execution authority remains closed. Machine-policy setup, randomization,
producer, scorer, A/B/C/D arms, mapping release, and Rekor POST are outside this
freeze.
