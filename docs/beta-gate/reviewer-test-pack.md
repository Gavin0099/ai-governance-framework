# Reviewer Test Pack — Beta Gate Condition 2

> Version: 1.0
> Created: 2026-03-30
> For: external reviewer (cold start, no author guidance)

---

## Part 1 — What you are testing

You are testing an open-source governance framework for AI-assisted development.

**Your job is not to learn it. Your job is to try to use it, and record what happens.**

Starting point: https://github.com/Gavin0099/ai-governance-framework

You have 30–60 minutes. Start whenever you are ready.

---

## Part 2 — Task

Try to do this, in order:

1. Figure out what this framework is for
2. Figure out how you would adopt it in a project
3. Run or describe the minimum flow you would follow when starting an AI-assisted work session
4. Find out how to check if your governance is drifting

Stop when you finish, or when you are stuck and cannot continue.

---

## Part 3 — Failure Log

Fill this in as you go. Do not wait until the end.
Honest, messy notes are more valuable than clean summaries.

### 3.1 First confusion point

The first moment something was unclear:

```
File or page I was looking at:

What I expected to find there:

What I actually saw:

How long I had been going at this point (approximate):
```

---

### 3.2 First blockage

The first point where I could not move forward:

```
What I was trying to do:

What I tried:

Why it didn't work (as best as I can tell):

Did I find a workaround? (Y/N)
If yes, what was it:
```

---

### 3.3 Concept confusion

Any term or concept that I encountered and didn't understand:

```
Term / concept:
Where I saw it:
What I thought it meant:
What I think it actually means (if I figured it out):
```

*(Copy this block for each confusing concept. Leave blank if none.)*

---

### 3.4 Navigation confusion

Any point where I didn't know where to look next:

```
I was trying to find:
I looked in:
I eventually found it at (or: I never found it):
```

*(Copy this block for each navigation failure. Leave blank if none.)*

---

### 3.5 Final state

```
Did you complete Task 1 (understand what this is for)?  Y / N / Partial
Did you complete Task 2 (understand adoption)?          Y / N / Partial
Did you complete Task 3 (describe minimum session flow)? Y / N / Partial
Did you complete Task 4 (find drift check)?             Y / N / Partial

If you stopped early: what was the last thing you tried before stopping?

One sentence describing what this framework is, in your own words:
```

---

## Part 4 — Debrief questions

Answer these after you are done:

1. What was the first file you opened, and why?

2. At what point (if any) did things start to make sense?

3. What was the single biggest obstacle?

4. If you had to tell a colleague whether to adopt this, what would you say?

5. What one change would most reduce the friction you experienced?

---

## Part 5 — For the author (not for the reviewer)

### How to interpret failure log entries

| Symptom | Failure type | Do not do | Do instead |
|---------|-------------|-----------|------------|
| Cannot find entry point after 10 min | Structural | Rewrite README | Add one clearer pointer at repo root |
| Finds correct file but misreads purpose | Naming | Add more explanation | Change the heading or first sentence |
| Understands concept but cannot execute | Friction | Add more docs | Fix the command or add one example |
| Understands nothing after 20 min | Conceptual | Restructure everything | Identify the one concept that unlocks the rest |
| Conflates framework repo with project repo | Conceptual | Add a warning | Make the distinction the first thing README states |

### Scoring (from onboarding-pass-criteria.md)

3 of 5 checkpoints passed = Beta Gate condition 2 met.
Record which failed. Each failure maps to one targeted fix, not a refactor.

### After receiving the log

File the raw log at: `docs/beta-gate/reviewer-run-<YYYY-MM-DD>.md`

Do not fix anything until you have read the full log.
Do not fix more than the lowest-level cause of each failure.
