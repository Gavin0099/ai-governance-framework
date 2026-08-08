# Sprint heading decision table — 2026-08-07 (rev 2)

> **Read-only decision support.** No parser, template, `PLAN.md` or consumer
> repository was modified. Derived entirely from
> `artifacts/plan-census/plan-fleet-census-2026-08-07.json`
> (`method_version: census-3.3`, 45 rows, 38/38 assertions) — not from a fresh
> scan, so it cannot drift from the census it supports.
>
> **Handling boundary:** this table names internal repositories. It is local
> review evidence. Publication or external sharing requires owner review of the
> `source_id` values first, the same boundary the census carries.
>
> Purpose: settle open items 1–4 of
> `plan-lifecycle-contract-spec-v0.2-2026-08-07.md`. **This document proposes;
> it does not decide.**

## Findings

**1. Thirteen distinct heading strings, not 37.** The census counted 37
*occurrences*; they collapse to 13 unique texts. One form — `Active Sprint`,
what the adoption template emits — accounts for **24 of 37**. A closed
enumerated list is therefore small and tractable.

**2. Normalisation is required before matching, and reduces 13 to 12.**
`Active Sprint\r` (21) and `Active Sprint` (3) are the same heading in CRLF and
LF files. After stripping the trailing `\r`, **13 raw strings collapse to 12
logical ones**.

Matching must therefore happen **after normalisation**:

- strip trailing `\r` and trailing whitespace;
- normalise to Unicode NFC;
- compare the framework's central English headings case-insensitively.

*Correction.* Rev 1 said the same split "applies to `Current Sprint\r` vs
`Current Sprint`". It does not — only `Current Sprint\r` appears in the fleet;
no LF-only variant was observed. Normalisation is required as a **general rule**,
not because both forms were seen.

## Heading disposition is not `parse_status`

`parsed` / `empty` / `unparsed` / `unsupported` describe a **repository's
surface after selection**. A *heading* is never "unsupported". A repository
carrying `Active Sprint` **and** `Next Sprint` parses the first perfectly well;
declining to adopt the second says nothing about that repository.

| Heading disposition | Meaning |
|---|---|
| `canonical` | the name the framework guarantees to read |
| `framework legacy` | on the framework's closed legacy list |
| `repo-local alias candidate` | a repository may declare it in `contract.yaml` |
| `non-current-sprint candidate` | a real section, but not the current sprint |
| `malformed / non-candidate` | not usable as a heading at all |

Rev 1 wrongly used `unsupported` as a per-heading disposition. Withdrawn.

## Candidate table

Ordinal `(n/m)` = n-th of m Sprint-bearing H2 headings in that file, in document
order. Occurrence counts are pre-normalisation, matching the artifact.

| # | exact heading | occ | repos | classification | readable today | co-exists | proposed disposition |
|---:|---|---:|---:|---|:-:|:-:|---|
| 1 | `Active Sprint\r` | 21 | 21 | template_emitted | N | Y | `framework legacy` |
| 2 | `Active Sprint` | 3 | 3 | template_emitted | N | N | `framework legacy` — same logical string as #1 |
| 3 | `Current Sprint\r` | 2 | 2 | parser_readable | **Y** | Y | `canonical` |
| 4 | `Current Sprint - 2026-06-10\r` | 1 | 1 | parser_readable, dynamic_date | **Y** | N | `canonical` with a dated suffix |
| 5 | `🔥 本輪聚焦（Sprint 2026-05-23）\r` | 2 | 2 | localized, dynamic_date | N | N | `repo-local alias candidate` |
| 6 | `進行中任務（Sprint）\r` | 1 | 1 | localized | N | N | `repo-local alias candidate` |
| 7 | `Phase E Sprint（Current）\r` | 1 | 1 | localized | N | Y | `repo-local alias candidate` |
| 8 | `Phase F Sprint（Adoption Contract Repair）\r` | 1 | 1 | localized | N | Y | `repo-local alias candidate` |
| 9 | `Next Sprint — Slice 4 (thin-shim UPDATE wiring + P2 smoke baseline)\r` | 1 | 1 | localized (em dash) | N | Y | **`non-current-sprint candidate`** |
| 10 | `# Sprint 6.1（2026-03-12 起）\r` | 1 | 1 | localized, dynamic_date, malformed | N | Y | `malformed / non-candidate` |
| 11 | `# Sprint 6.1 已完成指標\r` | 1 | 1 | localized, malformed | N | Y | `malformed / non-candidate` |
| 12 | `# Verification (this sprint)\r` | 1 | 1 | malformed | N | Y | `malformed / non-candidate` |
| 13 | `# 已完成（本 Sprint）\r` | 1 | 1 | localized, malformed | N | N | `malformed / non-candidate` |

**#10–13** are H2 headings whose *text* begins with a literal `#` — written
`## # …`. Almost certainly intended as H3, or formatting slips.

**#9 `Next Sprint`** names a *future* sprint. Treating it as a current-sprint
alias would surface planned-but-not-started work as active, which is why it is
classified `non-current-sprint candidate` rather than an alias candidate.

## Coverage arithmetic — where all 37 go

| Bucket | Occurrences |
|---|---:|
| `canonical` (`Current Sprint`, incl. dated suffix) | 3 |
| `framework legacy` (`Active Sprint`, both line endings) | 24 |
| **readable if items 1–2 settle as proposed** | **27** |
| `repo-local alias candidate` (localized, #5–8) | 5 |
| `non-current-sprint candidate` (#9) | 1 |
| `malformed / non-candidate` (#10–13) | 4 |
| **not covered by framework grammar** | **10** |

Rev 1 said only the 4 malformed would remain uncovered. That was wrong: **10**
occurrences fall outside the framework grammar, and 5 of them are legitimate
sections awaiting a repo-local declaration. Readable today: **3**.

## Repositories with more than one Sprint-bearing H2

| source_id | count | headings in document order | canonical present? |
|---|---:|---|:-:|
| `ai-governance-framework.recovered_20260424_184834` | 3 | `Current Sprint` → `Phase E Sprint（Current）` → `Phase F Sprint（Adoption Contract Repair）` | **Y** |
| `gl_electron_tool` | 2 | `Active Sprint` → `Next Sprint — Slice 4 …` | N |
| `hp-firmware-stresstest-tool` | 2 | `# Sprint 6.1（2026-03-12 起）` → `# Sprint 6.1 已完成指標` | N |
| `lenoveo-isp-tool-avalonia` | 2 | `Active Sprint` → `# Verification (this sprint)` | N |

In none of the four does a second heading compete for "current sprint" — the
second is always a *next* sprint, a *completed*-metrics section, or a
*verification* section.

**That is not a reason to resolve ambiguity by document order.** Four
repositories showing no conflict does not make "first" authoritative, and this
table states elsewhere that its classifications carry no evidence of owner
intent. Rev 1 proposed "first-in-document-order" as the tiebreak; **withdrawn**.
Selecting by position would let the parser decide semantics silently — the same
failure mode as the silent zero.

## Claim boundaries

- **Similar text is not evidence of alias intent.** `Next Sprint` contains
  "Sprint" and is probably not a current-sprint section; `# Verification (this
  sprint)` mentions a sprint and is a verification section. Aliases must be
  **declared**, never inferred.
- **Classification tags are mechanical**, derived from heading text alone.
  `localized` means non-ASCII — which is why #9 carries it, for an em dash.
  They do not encode intent.
- **Proposed dispositions are proposals.** No repository was contacted; no owner
  intent was confirmed.
- Every occurrence sits in a distinct repository; `occ` and `repos` differ only
  through the CRLF split.

## Recommended decisions — awaiting owner approval

These are the reviewer's recommendations, recorded here for decision. **None is
ratified.**

| # | Recommendation | Rationale |
|---|---|---|
| **1. Canonical** | **`Active Sprint`** | It is what the template emits and covers 24 of 37. A defective parser currently reads only `Current Sprint`; that defect should not be allowed to dictate what canonical *is* |
| **2. Legacy closed grammar** | `Current Sprint` and `Current Sprint - YYYY-MM-DD`, matched after normalisation. **No `*` wildcard** | Bounded grammar, not an open pattern. Rev 1's `Current Sprint*` reintroduced exactly the open-ended matching this contract forbids |
| **3. Precedence** | `canonical` > `framework legacy` > `repo-local declared alias`. If **more than one candidate sits at the highest present tier**, return `unparsed` with reason `ambiguous_sprint_sections` | Fails visibly instead of guessing. Document order never decides semantics |
| **4. Multi-heading** | Parse **only the single winning current-sprint section**. `Next Sprint`, verification, completed-metrics and malformed headings are not folded in. `unsupported` only when no valid candidate exists, subject to `applicability` | "Parse all" would merge future and completed work into current work |
| **5. Checkpoint reason code** | Fold into `plan_rollover_candidate` as a third trigger arm with `trigger_detail=checkpoint_overdue`; `plan_freshness_overdue` stays with document staleness | Keeps the four ratified codes; all three arms share one disposition — run a rollover |

Effect if all five are approved: the four ratified reason codes are unchanged,
the current template stays as-is and becomes canonical, **27 of 37 occurrences
become readable by framework grammar alone** (against 3 today), and the
remaining 10 are left to explicit repo-local declaration or to visible failure —
none of them guessed.
