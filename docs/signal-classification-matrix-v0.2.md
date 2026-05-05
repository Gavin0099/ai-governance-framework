# Signal Classification Matrix v0.2

## Purpose

Add misuse-risk dimension to authority classification so governance can decide:
- what must be isolated
- what can be conditionally consumed
- what needs stronger misuse monitoring

## Dimensions

1. **Authority Eligibility**
- `non_authoritative`
- `semi_authoritative`
- `decision_authoritative`

2. **Misuse Risk**
- `low`
- `medium`
- `high`

3. **Derivation Sensitivity**
- `low`
- `medium`
- `high`

## Matrix (Current Baseline)

| Signal | Authority Eligibility | Misuse Risk | Derivation Sensitivity | Notes |
|---|---|---|---|---|
| `token_count` | non_authoritative | low | medium | diagnostic source; derived cost heuristics are bypass-sensitive |
| `token_observability_level` | non_authoritative | low | low | visibility signal, not authority |
| `token_source_summary` | non_authoritative | low | low | provenance context only |
| `provenance_warning` | non_authoritative | low | low | warning context only |
| `latency` | semi_authoritative | medium | medium | may be operationally relevant, needs bounded policy |
| `cost` | semi_authoritative | medium | high | derived budget/routing signals can easily become soft gating |
| `confidence` | decision_authoritative | high | high | decision-relevant but high misuse risk (calibration/shift risk) |
| `risk` | decision_authoritative | high | high | decision-relevant, requires strict policy ownership |

## Governance Interpretation

- Authority eligibility alone is insufficient.
- High misuse risk requires stronger consumption visibility and constraint discipline.
- High derivation sensitivity requires stronger transformation governance.
- No signal becomes enforceable without explicit governance path.

## Change Control

Any matrix edit that changes authority eligibility or misuse risk must reference:
- reviewer decision
- rationale
- audit evidence
- classification version update

## Scope Note

This matrix is governance metadata.
It does not itself authorize runtime enforcement or gate behavior.
