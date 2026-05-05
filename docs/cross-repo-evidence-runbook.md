# Cross-Repo Evidence Runbook (2026-05-05)

## Objective
- Collect same-day `commit-level` evidence from target repos.
- Write the evidence into `memory/2026-05-05.md` with reproducible command output.

Target repos:
- `AITradeExecutor`
- `meiandraybook`
- `Bookstore-Scraper`
- `hp-firmware-stresstest-tool`
- `cli`
- `CFU`

## Scope Boundary
- This runbook only collects evidence (`git log` + `git status` snapshots).
- This runbook does not define enforcement, gating, or policy escalation.
- Missing evidence is reported as `blocked` or `pending`, not inferred.

## Step 1: Configure Git `safe.directory` (if blocked)
If git access is blocked by ownership checks, add trusted paths:

```powershell
git config --global --add safe.directory E:/BackUp/meiandraybook
git config --global --add safe.directory E:/BackUp/Git_EE/Bookstore-Scraper
git config --global --add safe.directory E:/BackUp/AITradeExecutor
git config --global --add safe.directory E:/BackUp/Git_EE/hp-firmware-stresstest-tool
git config --global --add safe.directory E:/BackUp/Git_EE/cli
git config --global --add safe.directory E:/BackUp/Git_EE/CFU
```

Verify:

```powershell
git config --global --get-all safe.directory
```

## Step 2: Collect commit/status evidence
Run `git log` and `git status` for each repo:

```powershell
git -C "E:\BackUp\AITradeExecutor" log --since="2026-05-05 00:00" --date=iso --pretty=format:"%h|%ad|%an|%s"
git -C "E:\BackUp\AITradeExecutor" status --short

git -C "E:\BackUp\meiandraybook" log --since="2026-05-05 00:00" --date=iso --pretty=format:"%h|%ad|%an|%s"
git -C "E:\BackUp\meiandraybook" status --short

git -C "E:\BackUp\Git_EE\Bookstore-Scraper" log --since="2026-05-05 00:00" --date=iso --pretty=format:"%h|%ad|%an|%s"
git -C "E:\BackUp\Git_EE\Bookstore-Scraper" status --short

git -C "E:\BackUp\Git_EE\hp-firmware-stresstest-tool" log --since="2026-05-05 00:00" --date=iso --pretty=format:"%h|%ad|%an|%s"
git -C "E:\BackUp\Git_EE\hp-firmware-stresstest-tool" status --short

git -C "E:\BackUp\Git_EE\cli" log --since="2026-05-05 00:00" --date=iso --pretty=format:"%h|%ad|%an|%s"
git -C "E:\BackUp\Git_EE\cli" status --short

git -C "E:\BackUp\Git_EE\CFU" log --since="2026-05-05 00:00" --date=iso --pretty=format:"%h|%ad|%an|%s"
git -C "E:\BackUp\Git_EE\CFU" status --short
```

## Step 3: Write evidence to memory
Append to `memory/2026-05-05.md` using structured facts:
- `today_commits` (raw log lines)
- `today_status_snapshot` (raw short status or `clean`)
- `evidence_level` (`commit-level` / `blocked` / `pending`)

If blocked, write explicit reason:
- `safe.directory not configured`
- `sandbox permissions denied`
- `path inaccessible`

## Step 4: Closeout criteria
Mark closeout complete only when each target repo has:
- `git log --since="2026-05-05 00:00"` evidence
- `git status --short` evidence
- memory record updated with exact snapshots

## Output template
Use this minimal output format:

```text
repo: <name>
today_commits:
  - <hash|date|author|subject>
today_status_snapshot: <clean or short-status lines>
evidence_level: commit-level
```
