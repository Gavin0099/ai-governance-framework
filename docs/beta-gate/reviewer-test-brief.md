# Beta Gate Condition 2 — Reviewer Test Brief

> Status: **ready for use**
> Created: 2026-03-30
> Gate condition: independent reviewer completes onboarding without author guidance

---

## Purpose

This brief defines the test condition, not the framework.
Do not give this document to the reviewer before they start.
Use it to set up the test and debrief afterward.

---

## Reviewer starting point

The reviewer receives exactly:
- The GitHub repo URL: https://github.com/Gavin0099/ai-governance-framework
- One sentence: "This is a governance framework for AI-assisted development. See if you can figure out how to use it."

Nothing else. No verbal context. No pointer to a starting file.

---

## What the reviewer is allowed to do

- Read any file in the repo
- Run any tool they find
- Spend as much time as they need (target: 30–60 minutes)
- Stop early and report where they got stuck

---

## What the author is not allowed to do

- Answer questions before the session ends
- Point to a file or section
- Explain what anything is for
- Confirm or deny whether the reviewer is on the right track

The author may only say: "Keep going, record what you're thinking."

---

## Success condition

The reviewer is considered to have passed if they can, without prompting:

1. Identify the main entry point for adopting the framework
2. Run or describe the minimum adoption flow (what commands, in what order)
3. Explain what `session_start → pre_task → post_task` means in their own words
4. Know what to do if governance drift is detected
5. Produce one governance-compliant artifact (any of: a session start, a drift check output, a contract, a change proposal)

Not all five are required. Passing 3 of 5 counts as a pass.

---

## Failure indicators to watch for

Record these if they occur:

- Reviewer opens README.md and immediately closes it
- Reviewer cannot find the entry point after 10 minutes
- Reviewer conflates framework governance with project governance
- Reviewer concludes the framework "is just documentation"
- Reviewer cannot distinguish `governance_tools/` from `runtime_hooks/`
- Reviewer asks "where do I start?" (counts as one navigation failure)

---

## Debrief questions (asked after the session)

1. What was the first file you opened? Why?
2. Where did you first understand what this is for?
3. What was the first thing that confused you?
4. If you had to describe this to a colleague in one sentence, what would you say?
5. What would you change about the entry path?

---

## What to record

- Time to first meaningful action (not README skimming, but purposeful exploration)
- First file that produced understanding (not confusion)
- First blocker: the exact file, section, and what was unclear
- Whether the reviewer reached the minimum adoption flow unprompted
- Debrief responses verbatim (or close)

---

## After the test

File findings at: `docs/beta-gate/reviewer-run-<date>.md`

Use the findings to answer: was the blocker conceptual, structural, or naming?
That answer determines the next onboarding change, if any.
