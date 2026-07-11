# Census Unit Review — Report/Record Templates Trio (2026-07-11)

Units: `templates/gate-c-decision-set-report-template.yaml`,
`templates/memory-candidate-template.yaml`,
`templates/retrieval-authority-advisory-template.yaml`.

These three units are reviewed together because they share one situation,
but each keeps its own row and disposition.

| Unit | Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- | --- |
| gate-c-decision-set-report-template.yaml (44 loc) | None current: **no tool consumer found**; referenced only by the census manifest and a 2026-05-11 memory record. Belongs to the frozen Gate C line. | Minimal; inert YAML. | — | Machine/template-facing. | `keep_observe` as a frozen-line record; any retirement belongs to a Gate C line disposition, not to census |
| memory-candidate-template.yaml (36 loc) | None current: **no tool consumer found**; referenced by the memory-significance-v0.2 design doc and the census manifest only. | Minimal; inert YAML. | — | Machine/template-facing. | `keep_observe`; tied to the memory-significance design line |
| retrieval-authority-advisory-template.yaml (21 loc) | None current: **no reference outside the census manifest at all**; its retrieval-authority line is frozen and its source notes were consolidated and removed in the 2026-07-10 diet. | Minimal; inert YAML. | — | Machine/template-facing. | `keep_observe`; strongest orphan signal in the census — if a future diet slice opens, this is the first template candidate, gated on the frozen line's summary coverage |

Evidence: all three parse as valid YAML (receipt); consumer searches over
tracked py/md files found no tool reader for any of them. None of this
proves the templates useless: frozen-line records legitimately sit unused
until their line reopens or is formally dispositioned.
