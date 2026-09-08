# C1 Gate 1 preregistration freeze

Status: `PREREGISTRATION_FROZEN_NOT_ARM_AUTHORIZED`.

This directory freezes the owner-approved D1-D7 decisions for the C1 Bug Fix
Safety study. It is an exact-byte preregistration input, not permission to
create or run a producer, scorer, or A/B/C/D arm.

The historical known fix and attempt-06 mutation outcome are qualification
inputs only. They are excluded from producer inputs, thresholds, sample counts,
task-winner logic, and mutation-target selection.

The manifest binds existing task, baseline, oracle, treatment, model, harness,
rubric, randomization, evidence-chain, validator, permissions, and budget
surfaces. It binds this directory's files by bytes and SHA-256 while excluding
itself to avoid a self-referential digest.

Claim ceiling: these bytes make the preregistration decisions reviewable and
machine-checkable. They do not establish Gate 1 readiness, Gate 3
effectiveness, Skill effectiveness, producer independence, or arm execution.

