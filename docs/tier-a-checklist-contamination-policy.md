# Tier A Checklist Contamination Policy

Purpose: prevent composition-level directional contamination on Tier A checklists
such as `KERNEL_DRIVER_CHECKLIST.md`.

## Scope

Applies to Tier A checklist-like governance surfaces that are intended to remain
fact-gated and non-directional.

## Policy

1. Tier A checklist files and their adjacent regions must not include directional
   progress language such as:
   - `improving`
   - `trending`
   - `most fields now resolved`
   - `near ready` / `close to ready`
2. Progress/status narratives must be placed in `STATUS.md` (or equivalent status
   surface), not embedded in or immediately adjacent to Tier A checklist text.
3. `STATUS.md` (or equivalent) must pass an independent noise test before being
   treated as safe for reviewer consumption.

## Detection Rule

If directional progress language appears in a Tier A checklist surface (including
adjacent explanatory prose), classify as:

- `directional_synthesis = yes`
- `directional_synthesis_type = directional_positive`
- `classification_outcome = fail`

No manual relaxation for Tier A.

## Interpretation

- `clean pass + noise fail` means checklist core structure is healthy, but
  presentation composition is unsafe.
- Remediation target is composition boundary, not checklist fact schema.

