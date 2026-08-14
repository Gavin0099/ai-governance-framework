# PLAN.md fleet census — 2026-08-07 (Revision 3.2)

> Read-only. No repository was modified, no adoption or refresh was run, and no
> `PLAN.md` was edited. Input to the framework-wide **PLAN lifecycle contract
> review**; it is not that review and proposes no fix.
> **Row-level evidence:** `artifacts/plan-census/plan-fleet-census-2026-08-07.json`
> — 45 rows, each with `source_id`, `plan_relpath`, `sha256`,
> `summary_exit_code`, the parser's returned fields, and every raw count below,
> plus a `metadata` block recording schema version, method version, framework
> commit, parser source SHA-256, population rule, line-count convention and
> claim ceiling. **38 self-consistency assertions** are stored in the same file
> and all pass. Every headline number here — including the archive result, the
> size distribution and the deduplicated staleness count — is a sum or a
> recomputation over those rows.
> Row paths are recorded as `source_id` + `plan_relpath` under a
> `fleet_root` alias; the absolute local path is deliberately omitted so the
> artifact is portable and free of absolute local paths. **Publication still
> requires owner review of the 45 consumer source identifiers**, which may name
> internal projects.
> **Revisions 1 and 2 both had wrong numbers.** See "Corrections".

## The finding — the backlog parser cannot return non-zero for any well-formed PLAN

Revisions 1 and 2 said the adoption template and `parse_backlog_counts` disagree.
That is true but secondary. The primary defect is stronger:

**`parse_backlog_counts` cannot return a non-zero value for any well-formed
PLAN using the intended `## Backlog` → `### P0/P1/P2` grammar.**

Its section extraction is `##\s*Backlog(.*?)(?=\n##|\Z)`. The lookahead
`\n##` also matches `\n###`, so the captured body terminates at the first H3.
The function then searches that body for `###` headings containing `P0`/`P1`/`P2`
— headings the extraction has just guaranteed cannot be present.

Demonstrated against a PLAN written exactly the way the function documents it
wants:

```python
ideal = "## Backlog\n\n### P0\n- [ ] p0 item one\n- [ ] p0 item two\n\n### P1\n- [ ] p1 item\n\n## Next\n"
parse_backlog_counts(ideal)  ->  {'P0': 0, 'P1': 0, 'P2': 0}
captured body                ->  '\n'
```

Within the intended grammar, no template change, no consumer change and no
repository layout can make this function report a backlog item. Fleet result:
**0** — structurally inevitable under that grammar, and independently observed
across all 45 inputs.

**Scope, stated precisely.** The function is not unsatisfiable for arbitrary
strings. A malformed input that puts both headings on one line does produce a
count:

```python
parse_backlog_counts("## Backlog ### P0\n- [ ] x\n")  ->  {'P0': 1, 'P1': 0, 'P2': 0}
```

That is not supported grammar, and no PLAN in the fleet uses it. Both probes —
**their input strings as well as their results** — are stored in the evidence
artifact, so the boundary is reconstructable. The generating script is not
retained, so these are captured evidence rather than a continuously executable
test.

### The same truncation silently degrades the sprint parser

`parse_sprint_tasks` uses the same `(?=\n##|\Z)` lookahead. It does not require
H3 sub-headings, so it works — until a sprint section contains one, at which
point everything after the first H3 is invisible:

```
## Current Sprint
- [ ] before subheading
### Group A
- [ ] after subheading one
- [ ] after subheading two
```

returns **1 item**, not 3.

## Measured state — all sums reproduce from the evidence rows

Population: **45 PLAN-bearing directories**, **41 unique PLAN contents**
(3 duplicate groups: the `CFU` trio, the two `Enumd` copies,
`lenovo_isp_tool` = `Standard_ISP_Tool`). "45 repositories" is avoided: these
are checkouts, including trial copies and one recovery snapshot.

| Surface | Present in the file | `plan_summary` surfaces |
|---|---:|---:|
| `## Backlog` — unchecked `- [ ]` | **6** | — |
| `## Backlog` — inline `- P0/P1/P2:` rows | **49** | — |
| … of which explicit `(none)` placeholders | 7 | — |
| … candidate non-placeholder rows | **42** | — |
| **Backlog, any form** | **55 structural rows** | **0** |
| Sprint section — unchecked `- [ ]` | **140** | **4** |
| `open_phase_e_tasks` | — | 3 |
| `active_blockers` | — | 1 |

Whole-file counts, recorded as fleet scale and **not** as a miss count — the
summarizer was never designed to report every checkbox:

| | |
|---|---:|
| `- [x]` anywhere | 1100 |
| `- [ ]` anywhere | 360 |
| `- [>]` anywhere | 4 |

`hbplus.avalonia` alone holds **90** of the 140 sprint-section unchecked items.

## Sprint heading compatibility

`parse_sprint_tasks` accepts only `## Current Sprint`. Classification is per
**directory**, using the precedence rule: if any H2 heading containing "Sprint"
begins with "Current Sprint", the directory is compatible and that section is
measured; otherwise the first Sprint-bearing H2 is measured.

| | |
|---:|---|
| **3** | directories with a parser-compatible heading |
| 42 | directories without one |
| 37 | Sprint-bearing H2 headings across the fleet (some files have more than one) |
| 26 | directories with a `## Backlog` H2 |

Observed heading forms include the template's `## Active Sprint`, plus
`## 進行中任務（Sprint）`, `## 🔥 本輪聚焦（Sprint 2026-05-23）`, and one
malformed `## # 已完成（本 Sprint）`. Headings also carry `\r` in CRLF files.

## Silent zero is the wrong failure mode

When the structure is absent — or, as shown above, when it is present but
unreachable — `parse_backlog_counts` returns `{P0: 0, P1: 0, P2: 0}` and
`parse_sprint_tasks` returns `[]`. Neither is distinguishable from "there is
genuinely no open work".

Any lifecycle contract should require `unknown` / `unparsed`. This is the single
most consequential finding, because it is what keeps the defect invisible in
normal operation.

## Archive

Rule: an archive exists if (a) a file matching `*plan*archive*` or
`*archive*plan*` exists at depth ≤ 3 below the repo root, **or** (b) `PLAN.md`
contains a markdown link whose target contains `archive`.

**Result: 0 of 45**, recorded per row as `archive_file_matches`,
`archive_plan_links` and `archive_detected`, and asserted in the artifact.
Claim ceiling: this rules out that specific naming and
linking convention. It does **not** prove no historical preservation exists in
any other form.

## Staleness

Threshold: last-updated before `2026-07-01`.

| | |
|---|---:|
| Stale, per directory | **23** |
| Stale, deduplicated by PLAN content | **21** |
| No parsable last-updated field | **1** (`usb-logic-trace-correlator`) |

Oldest: `hearth-memory-check` 2026-03-31; `hp-oci-avalonia` and
`lenovo_isp_tool` 2026-04-14.

Date freshness does not measure whether content still describes current work.
This framework's own PLAN is the counterexample: updated 2026-07-30, largest
section titled "Current Sprint - 2026-06-10".

## PLANs outside any profile

`usb-logic-trace-correlator` (487 lines) has no `##` sections and no parsable
last-updated field. `Kernel-Driver-Contract` and
`USB-Hub-Firmware-Architecture-Contract` have zero `##` sections. A contract
must define what happens to a PLAN that does not match the profile; the answer
cannot be "silently score it as compliant".

## Scale

Recomputed from the evidence rows: **median 109 logical lines**, **38 of 45
under 262**, **5 of 45 over 600**.

The five over 600: the framework's recovery copy 1805, `ai-governance-framework`
1742, `usb-if-hub-spec-reference` 1127, `hbplus.avalonia` 835, `ZoneTruth` 634.
Revision 3.1 said "four" and omitted `ZoneTruth`.

A PLAN maintenance signal should be **threshold-triggered and report-only**, not
a mandatory gate on every consumer.

## Corrections

| Claim | Revision | Correct value |
|---|---|---|
| "0 of 360 visible" | r1 | Invalid comparison — whole-file checkboxes vs a backlog-only counter |
| hbplus "256 … reports 0", implying backlog loss | r1 | hbplus's `## Backlog` holds 3 inline rows; the 256 are elsewhere |
| Fleet-wide verification implied | r1 | r1 ran the real tool on 4 repos; r2 and r3 run it on all 45 |
| stale = 14 | r1 | 23 per directory / 21 deduplicated / 1 unknown |
| archive 38 / 5 / 2 | r1 | Unstated loose rule. Under a documented rule: **0 of 45** |
| Backlog "1 checkbox + 49 inline" | r2 | **6** checkboxes + 49 inline; 7 of the inline rows are `(none)` placeholders |
| Sprint items = 32, "82 in scope", "4 of 82" | r2 | **140**. The 32 came from the same `(?=\n##)` truncation bug documented above |

**The census tooling reproduced the defect it was measuring — twice.**
Revision 2's first run reported "sprint open = 0" fleet-wide because the
extraction tested `isinstance(item, dict)` against a list of strings. Revision
2's published sprint denominator was 32 because its section extraction used the
framework's own truncating lookahead. Both are silent-zero failures produced by
unvalidated assumptions — the same class of defect this census documents.
Revision 3 therefore ships row-level evidence and machine-checked assertions
instead of narrative totals.

## Method — reproducible

Real tool, per PLAN, exit code recorded per row:

```bash
python -X utf8 scripts/plan_summary.py --plan <repo>/PLAN.md --format json
```

Fields read: `backlog_open` (summed), `open_sprint_items` (length; already
filtered to open), `open_phase_e_tasks`, `active_blockers`.

Section bodies are extracted with an **H2-only** terminator — this is the fix
for the truncation bug:

```
^##[ \t]*<name>[^\n]*\n(.*?)(?=^##[^#]|\Z)     DOTALL | IGNORECASE | MULTILINE
```

| Purpose | Pattern |
|---|---|
| unchecked | `^\s*-\s*\[ \]` |
| checked | `^\s*-\s*\[[xX]\]` |
| in progress | `^\s*-\s*\[>\]` |
| inline priority | `^\s*-\s*P[012]\s*:` |
| placeholder | `^\s*-\s*P[012]\s*:\s*\(?\s*(none\|n/?a\|tbd\|待定)\s*\)?\s*$` |
| sprint H2 | `^##[ \t]*([^\n]*Sprint[^\n]*)$` |

Input set: every immediate subdirectory of `E:\BackUp\Git_EE\` containing
`PLAN.md`. Deduplication by SHA-256 of the file bytes.

Assertions stored in the artifact and passing: hbplus sprint = 90; framework
`open_sprint_items` = 4; framework three-state = 175 / 16 / 1; row sums equal
the sprint and inline totals; all 45 `plan_summary` invocations exited 0;
placeholders ≤ inline total.

The census script remains a one-off in scratchpad and was deliberately **not**
added to the repository, per the tool admission stop rule. The **data** is
retained as a repository-scoped evidence candidate and is intended to be
committed together with this census — the stop rule restricts new tooling, not
evidence retention. At the time of writing the artifact is still untracked.

Line counts use one convention throughout: `logical_lines =
len(text.splitlines())`. For the captured framework PLAN, which ends in LF, this
equals `wc -l` at 1742. The two differ by one for a file with no final newline,
so the identity is not universal. Revision 3 mixed this convention with
`count("
") + 1`, which is why the framework PLAN appeared as both 1742 and
1743.

## Explicitly not claimed

- **No fix is proposed.** This is census input for the contract review.
- **Item quality was not assessed.** An unchecked box is counted as open work
  regardless of whether it is a task, a standing constraint, or a status note.
  This framework's own rollover pilot found 11 of its 16 unchecked items are
  standing constraints, so raw counts are upper bounds on real open work.
  Semantic work-item counts are `NOT ASSESSED`.
- **26 directories having a `## Backlog` that reports zero does not mean 26 are
  under-reported.** Some may genuinely have no open backlog. What is established
  is that none of the observed well-formed PLAN structures can produce a
  non-zero backlog count.
- **No consumer was contacted**, and no conclusion is drawn about any
  consumer's practices. Where a divergence exists, the evidence points at the
  parser first and the template second, not at the adopter.
