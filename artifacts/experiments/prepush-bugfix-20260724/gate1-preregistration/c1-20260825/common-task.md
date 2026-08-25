# C1 common producer task

## Product symptom

During one bulk catalog import, two distinct books that share the same title
and publisher can be linked to the same existing catalog book. The second book
then loses its distinct catalog identity. Existing imports that have no catalog
identifier and intentionally resolve by title and publisher must continue to
work.

## Reproduction

Start from the supplied baseline and run the supplied black-box bulk-import
reproducer. Its input contains an existing catalog book and a batch with two
same-title/same-publisher items: one represents that existing book and the
other represents a distinct catalog item. Observe that both results link to the
existing book, although the second item should remain distinct.

## Common boundary

- Diagnose and correct the product behavior within the supplied baseline.
- Use only the common permissions and budget declared by the preregistration.
- Do not access later history, historical fixes, scorer-only artifacts,
  coordinator analysis, or another arm's output.
- The task packet does not prescribe a regression-test workflow, root-cause
  method, defect reintroduction, sensitivity procedure, or evidence-claim
  method. Those are treatment differences, not common instructions.

