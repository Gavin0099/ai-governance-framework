# Framework gap — the official first-import workflow is not one-shot

> Recorded 2026-08-07 against `main = f3c9f28e`.
> Status: **candidate admission**, pending one directly traceable consumer
> record or replay. **Not an implementation authorization.**
> Supersedes an earlier draft titled *"adoption is not atomic"*, whose framing
> was wrong — see "What the earlier draft got wrong".

## The observation

`docs/ai-governance-first-import-sop.md` defines first import as a multi-step
workflow. Step 3 runs `adopt_governance.py`; **step 4, "Resolve common
first-import gaps", separately requires three files** and calls them MVGB
requirements, not optional improvements:

- `.governance/version_manifest.yaml`
- `governance/framework.lock.json`
- `governance/gate_policy.yaml`

`adopt_governance.py` does not emit them. Verified on `f3c9f28e`:

```
$ grep -c "version_manifest\|gate_policy\|framework\.lock" governance_tools/adopt_governance.py
0
```

**This is by design, not by accident.** The tool declares its own boundary in
`_COPY_ADOPTION_BOUNDARY_LINES` (`governance_tools/adopt_governance.py:74`):

> Adoption class: copy-based audit surface
> Runtime capability: not self-contained
> Not included by this copy-based adopt path: governance_tools, runtime_hooks,
> runtime injection snapshot
> This repo is not runtime self-contained from copy-based adoption alone.

So the gap is not that a tool fails or lies. **The gap is that the designed
workflow requires a manual step that is separate from the tool run.** The
reported observations suggest that consumers may leave step 4 incomplete until a
downstream refusal exposes the gap; **recurrence is not established by this
record** — see the evidence boundary below.

## What the earlier draft got wrong

The earlier draft called this an atomicity / false-completeness defect. That was
wrong on three counts, and the corrections matter because they change what
should be built:

| Earlier claim | Why it was wrong |
|---|---|
| "adopt silently claims complete success" | It explicitly declares `Runtime capability: not self-contained` and lists what it does not include |
| "adopt does not produce what the SOP requires" | The SOP never assigns those files to adopt. It assigns them to step 4 |
| "correctness / false-completeness defect; clears the admission bar" | On this evidence it is a **workflow convergence gap**, and admission is candidate-grade at best |

The draft reached those conclusions by grepping `adopt_governance.py` for the
three filenames and reading the SOP's requirement list, without reading either
the tool's declared adoption class or the SOP's step structure.

## Observed occurrences — three, all from one analysis pass

| # | Repository | Date | Form |
|---|---|---|---|
| 1 | Zephyr | 2026-08-05 | adopt completed → smoke entered `controlled_refusal` → agent read the SOP → hand-filled `version_manifest.yaml` → then passed |
| 2 | CFU / Zephyr | 2026-08-06 | `.governance/version_manifest.yaml` added by hand as part of "the minimum surface" |
| 3 | gl_sdk | 2026-08-06 | adopt completed, 18/18 drift PASS, then *"first-import SOP 所要求的版本 lock、manifest、gate policy 尚未由 adopt 自動建立"* — three files added by hand |

**Evidence boundary — read this before citing the table.** All three are
reported by the 2026-08-06 three-repo analysis. They are independent as
*repositories*; they are **not** independent as *observers*. None was
re-verified in this record, and **no traceable log path, commit or artifact
reference is recorded here for any of them.** Recurrence and cost are therefore
reported, not established.

### HBPlus is deliberately excluded

The earlier draft counted HBPlus.Avalonia's 2026-06-25 verification report as a
fourth, independent record of this gap. It is not. That report's §6 records:

- `governance_tools` is not invocable from a consumer root
- `runtime_hooks/core/*.py` cannot execute standalone
- drift passing 17/17 while the runtime layer is non-functional
- `framework_version` reporting `<unknown>`

**None of those is the three-missing-files gap.** G4 case 002 already states, in
its own words, that these adoption-surface findings "do not represent four
independent observers, and they are not one identical defect". Counting HBPlus
here would contradict a document this project already accepted.

HBPlus remains relevant as **related adoption-topology background**, and it is
the only observation on record from a non-author. It is not recurrence evidence
for this gap.

## Downstream effect: correct refusals read as tool failures

A consumer that has not completed step 4 later meets tools that refuse. Observed
2026-08-07 in a parent repo running the submodule updater dry-run.

Both refusal conditions are narrow and correct:

| Condition | Names the offending files? |
|---|---|
| `_require_clean_apply_overlap` — dirty files overlapping the F-7 apply allowlist | **Yes.** The message interpolates the overlapping path list |
| `_require_no_initial_staged_files` — any pre-existing staged file | **No.** It says "refusing to mix scopes" and stops there |

Dirty files *outside* the allowlist are deliberately tolerated.

Neither condition is "adoption is incomplete". But because an incomplete step 4
normally leaves uncommitted governance files behind, operators reasonably but
incorrectly read the refusal as *"the updater cannot handle incomplete
adoption"*.

**Secondary gap, scoped narrowly:** only `_require_no_initial_staged_files`
withholds the file list. The earlier draft claimed both messages did; that was
half wrong.

## What this is not

- **Not** a bug in `adopt_governance.py`. It does what it declares.
- **Not** a bug in the updater. Both refusals are justified fail-closed
  behaviour.
- **Not** a bug in `memory_record`. Memory guards pass in every observed case.
- **Not** closed by PR #24, #25 or #26.

## Admission assessment

Against the tool admission rule in `memory/00_long_term.md`:

| Criterion | Status |
|---|---|
| Repeated failure | **Reported, not established.** Three repository observations from one analysis pass, none re-verified, no traceable references |
| Measured cost | **Not measured.** "One agent round per repo" is an estimate. No human minutes, tokens, or recorded intervention counts exist |
| Independent consumer evidence | **Absent for this gap.** The only non-author record (HBPlus) is a different problem |
| Clear caller and acceptance condition | **PARTIAL.** Workflow owner and acceptance outcome are clear — a clean-clone first import reaches MVGB without hand-authoring the three files. The **implementation caller is intentionally undecided**, because "`adopt_governance.py` or the SOP" is not one caller and the candidates imply different fixes: (a) extend `adopt_governance.py`, which changes its declared adoption class; (b) change the SOP or add an orchestration step, which preserves adopt's bounded contract; (c) improve refusal remediation only, which is a third surface. Design review decides |

**Verdict: candidate admission, pending one directly traceable consumer record
or replay.** Not "clears the admission bar" — the earlier draft said that and it
was not supported.

The cheapest way to convert this to established: on the next real first import,
record the log path, the commit that added the three files, and the wall-clock
time spent. One such record would do more than three re-told ones.

A consumer replay can establish real occurrence and cost. It does **not**
pre-authorize modifying `adopt_governance.py`; which surface to change remains
the design review's decision.

## Related hypothesis — requires its own inventory

`baselines/repo-min/.github/workflows/governance-drift.yml:37` hardcodes
`governance/governance_tools/...` as the framework path, and its `paths:` filter
covers only governance files, so product source changes do not trigger it. Both
are verified static facts.

The claim that *"every observed consumer uses a differently named submodule
directory"*, and therefore that this shares a root cause with the gap above, is
**a hypothesis with no fleet inventory behind it in this record**. It must not
be folded into this gap's confirmed root cause until a consumer-path inventory
exists.

## Why this is being written down

G4 case 002 records that the 2026-07-01/03 adoption-reporting work has no
durable record naming the consumer case that prompted it, so its causal chain
had to be reconstructed from owner memory six weeks later.

`memory/00_long_term.md` step 2 of the consumer-driven loop requires recording
the observed problem and its practical impact before proposing a fix. This
document is that step — including, deliberately, the parts where the evidence
does not yet support the conclusion someone might want to draw from it.
