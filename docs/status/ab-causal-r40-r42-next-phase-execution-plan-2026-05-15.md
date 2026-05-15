# AB Causal Next-Phase Execution Plan (r40-r42, 2026-05-15)

As-of: 2026-05-15  
Prior closeout state: r39 `threshold_dependent_persists`, `close_case=True`  
Goal: move from "conditional behavioral effect" to stronger causal clarity without claim inflation.

## Phase Framing

- r40: reasoning-separation experiment (A)
- r41: ecological strictness audit (B)
- r42: causal decomposition via component ablation (C)

## Non-Negotiables

- keep strict gate semantics unchanged
- seed policy unchanged: `350101`, `350102`, `350103`
- `max_retry=3`
- checkpoint + resume mandatory
- unsupported and mechanism failure must remain explicitly separated

## Global Gate (Unchanged)

- `mechanism_stable_candidate`: any arm `pass_count=3/3` and `unsupported_count=0`
- `threshold_dependent_persists`: no arm reaches 3/3 pass and all required arms `unsupported_count=0`
- `inconclusive`: any required arm `unsupported_count>0`

## Expected Deliverables

- r40 status + checkpoint + blinded artifacts
- r41 status + strictness-validity scorecard
- r42 status + component-effect ranking table
- one final synthesis page: what changed in claim boundary after r40-r42

## Stop Conditions

- if r40-r42 all end in `threshold_dependent_persists`, freeze mechanism-family iteration and open a fresh lineage
- if any run is `inconclusive`, fix harness/measurement contract before further interpretation

